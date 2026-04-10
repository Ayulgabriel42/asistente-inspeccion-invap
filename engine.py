from google import genai
from google.genai import types
from google.cloud import storage
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
import os
import datetime

class InspeccionEngine:
    def __init__(self, api_key, creds=None): 
        self.client = genai.Client(api_key=api_key)
        self.creds = creds 
        self.model_id = "gemini-2.0-flash" 
        self.bucket_name = "invap-asistente-normas"
        os.environ["GOOGLE_API_KEY"] = api_key

    def clasificar_norma_ia(self, hallazgo, lista_normas):
        prompt = (
            f"Actúa como clasificador experto de INVAP. De la lista de PDFs, "
            f"elige la ruta exacta para el hallazgo: '{hallazgo}'. "
            f"\nLISTA: {lista_normas[:100]}\nResponde solo con la ruta."
        )
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=prompt)
            seleccion = res.text.strip()
            return seleccion if seleccion in lista_normas else lista_normas[0]
        except:
            return lista_normas[0]

    def consultar_normativa_rag(self, norma_path, hallazgo, imagen_bytes=None, mime_type=None):
        ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        storage_client = storage.Client(credentials=self.creds)
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob(norma_path)
        tmp_path = f"temp_{norma_path.split('/')[-1]}".replace(" ", "_")
        
        try:
            blob.download_to_filename(tmp_path)
            loader = PyPDFLoader(tmp_path)
            pages = loader.load_and_split()
            embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
            vectorstore = FAISS.from_documents(pages, embeddings)
            
            query_rag = hallazgo if hallazgo else "especificaciones técnicas"
            docs = vectorstore.similarity_search(query_rag, k=5)
            contexto = "\n\n".join([doc.page_content for doc in docs])

            prompt_tecnico = f"""
            Actúa como Inspector Senior de INVAP. 
            FECHA Y HORA ACTUAL: {ahora}
            NORMA: {norma_path}
            CONTEXTO: {contexto}
            HALLAZGO: {hallazgo}
            TAREA: Genera informe multimodal profesional usando la fecha {ahora}.
            """
            contenidos = [prompt_tecnico]
            if imagen_bytes:
                contenidos.append(types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type))

            response = self.client.models.generate_content(model=self.model_id, contents=contenidos)
            return response.text, norma_path
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

    def refinar_informe(self, informe_previo, comentario):
        ahora_edit = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        prompt = f"Editor INVAP (Hora:{ahora_edit}). Corregí este informe: {informe_previo}. Pedido: {comentario}"
        res = self.client.models.generate_content(model=self.model_id, contents=prompt)
        return res.text

    def transcribir_audio(self, audio_bytes, mime_type):
        res = self.client.models.generate_content(
            model=self.model_id,
            contents=["Transcribe este audio técnico:", types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)]
        )
        return res.text

    def analizar_pdf_qa(self, pdf_bytes, prompt_p):
        res = self.client.models.generate_content(
            model=self.model_id,
            contents=[types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"), prompt_p]
        )
        return res.text