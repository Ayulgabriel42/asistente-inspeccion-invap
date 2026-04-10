from google import genai
from google.genai import types
from google.cloud import storage
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
import os
import datetime

class InspeccionEngine:
    def __init__(self, api_key, creds=None, project_id=None): 
        self.client = genai.Client(api_key=api_key)
        self.creds = creds 
        self.project_id = project_id
        self.model_id = "gemini-3-flash-preview" 
        self.bucket_name = "invap-asistente-normas"
        os.environ["GOOGLE_API_KEY"] = api_key

    # =========================================================
    # CLASIFICADOR CON PRIORIDAD VISUAL (IMAGEN > TEXTO)
    # =========================================================
    def clasificar_norma_ia(self, hallazgo, lista_normas, imagen_bytes=None, mime_type=None):
        hallazgo_lower = hallazgo.lower()
        lista_final = lista_normas.copy()

        # Pre-filtro lógico para asegurar que no elija normas estructurales en izaje
        palabras_izaje = ["eslinga", "cable", "gancho", "grillete", "izaje", "tensor"]
        if any(w in hallazgo_lower for w in palabras_izaje):
            lista_final = [n for n in lista_final if "4G" not in n and "4g" not in n]

        prompt = (
            "Actúa como Especialista en Normativa de INVAP. "
            "INSTRUCCIÓN CRÍTICA: La imagen adjunta es la PRIORIDAD ABSOLUTA. "
            "Identifica el objeto físico en la imagen. Si ves una eslinga o cable, "
            "ignora cualquier mención a estructuras mayores y elige la norma de izaje. "
            f"Hallazgo de apoyo: '{hallazgo}'. "
            f"Lista de PDFs autorizados: {lista_final[:50]}. "
            "Responde ÚNICAMENTE con el nombre exacto del archivo PDF."
        )
        
        contenidos = [prompt]
        if imagen_bytes:
            # Ponemos la imagen primero en la lista de contenidos para darle peso
            contenidos.insert(0, types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type))
        
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=contenidos)
            seleccion = res.text.strip().replace("`", "").replace("'", "")
            return seleccion if seleccion in lista_normas else lista_normas[0]
        except:
            return lista_normas[0]

    # =========================================================
    # MOTOR RAG (CONEXIÓN EXPLÍCITA AL PROYECTO)
    # =========================================================
    def consultar_normativa_rag(self, norma_path, hallazgo, imagen_bytes=None, mime_type=None):
        ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        storage_client = storage.Client(credentials=self.creds, project=self.project_id)
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob(norma_path)
        tmp_path = f"temp_{norma_path.split('/')[-1]}".replace(" ", "_")
        
        try:
            blob.download_to_filename(tmp_path)
            loader = PyPDFLoader(tmp_path)
            pages = loader.load_and_split()
            
            contexto = ""
            if pages and any(p.page_content.strip() for p in pages):
                try:
                    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
                    vectorstore = FAISS.from_documents(pages, embeddings)
                    query_rag = hallazgo if hallazgo else "criterios técnicos"
                    docs = vectorstore.similarity_search(query_rag, k=5)
                    contexto = "\n\n".join([doc.page_content for doc in docs])
                except:
                    contexto = "Analice visualmente el PDF."

            prompt_tecnico = f"Inspector INVAP S.A. | Fecha: {ahora} | Norma: {norma_path} | Contexto: {contexto} | Hallazgo: {hallazgo}"
            contenidos = [prompt_tecnico]
            
            if not contexto or "visualmente" in contexto:
                with open(tmp_path, "rb") as f:
                    contenidos.append(types.Part.from_bytes(data=f.read(), mime_type="application/pdf"))
            
            if imagen_bytes:
                contenidos.append(types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type))

            response = self.client.models.generate_content(model=self.model_id, contents=contenidos)
            return response.text, norma_path
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

    def refinar_informe(self, informe_previo, comentario):
        res = self.client.models.generate_content(model=self.model_id, contents=f"Editor INVAP: {informe_previo}. Cambio: {comentario}")
        return res.text

    def transcribir_audio(self, audio_bytes, mime_type):
        res = self.client.models.generate_content(model=self.model_id, contents=[types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)])
        return res.text

    def analizar_pdf_qa(self, pdf_bytes, prompt_p):
        res = self.client.models.generate_content(model=self.model_id, contents=[types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"), prompt_p])
        return res.text