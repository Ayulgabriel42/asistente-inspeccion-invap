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
    # CLASIFICADOR MULTIMODAL - CORRECCIÓN DE TIPADO BYTES
    # =========================================================
    def clasificar_norma_ia(self, hallazgo, lista_normas, lista_imagenes=None):
        hallazgo_lower = hallazgo.lower()
        
        # PASO 1: Identificación Visual
        contenidos_vision = ["Analiza las imágenes adjuntas e identifica el componente. Responde solo: ESLINGA, ESTRUCTURA, MECÁNICO o INSTRUMENTACIÓN."]
        
        if lista_imagenes:
            for img_tuple in lista_imagenes:
                # Aseguramos el desempaquetado manual para evitar que Pydantic reciba la tupla o lista
                img_data = img_tuple[0]
                img_mime = img_tuple[1]
                contenidos_vision.append(types.Part.from_bytes(data=img_data, mime_type=img_mime))
        
        categoria_visual = "OTRO"
        try:
            res_v = self.client.models.generate_content(model=self.model_id, contents=contenidos_vision)
            categoria_visual = res_v.text.strip().upper()
        except: pass

        # PASO 2: Filtrado de lista (Mantenemos tu lógica de negocio INVAP)
        lista_final = lista_normas.copy()
        es_izaje = "ESLINGA" in categoria_visual or any(w in hallazgo_lower for w in ["eslinga", "cable", "izaje", "grillete"])
        
        if es_izaje:
            lista_final = [n for n in lista_final if any(x in n.upper() for x in ["B30", "3914", "ESLINGA"])]
            lista_final = [n for n in lista_final if all(x not in n.upper() for x in ["11E", "4G", "ACI"])]
            if not lista_final: 
                lista_final = [n for n in lista_normas if "B30" in n or "3914" in n]

        # PASO 3: Selección final
        prompt_final = (
            f"ERES UN EXPERTO EN INTEGRIDAD DE INVAP. Visión detectó: {categoria_visual}. "
            f"Inspector dictó: '{hallazgo}'. Selecciona el PDF correcto: {lista_final[:30]}. "
            "Responde ÚNICAMENTE con el nombre del archivo."
        )
        
        contenidos_final = [prompt_final]
        if lista_imagenes:
            for img_tuple in lista_imagenes:
                # Desempaquetado explícito
                img_data = img_tuple[0]
                img_mime = img_tuple[1]
                contenidos_final.append(types.Part.from_bytes(data=img_data, mime_type=img_mime))

        try:
            res = self.client.models.generate_content(model=self.model_id, contents=contenidos_final)
            seleccion = res.text.strip().replace("`", "").replace("'", "")
            return seleccion if seleccion in lista_normas else lista_normas[0]
        except: return lista_normas[0]

    # =========================================================
    # MOTOR RAG MULTIMODAL - CORRECCIÓN DE TIPADO BYTES
    # =========================================================
    def consultar_normativa_rag(self, norma_path, hallazgo, lista_imagenes=None):
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
            if pages:
                try:
                    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
                    vectorstore = FAISS.from_documents(pages, embeddings)
                    docs = vectorstore.similarity_search(f"criterios rechazo descarte {hallazgo}", k=6)
                    contexto = "\n\n".join([doc.page_content for doc in docs])
                except: contexto = "Análisis visual directo."

            prompt_tecnico = (
                f"SISTEMA INVAP | Fecha: {ahora} | Norma: {norma_path}\n"
                f"CONTEXTO RAG: {contexto}\n\n"
                "### Análisis del Hallazgo\n"
                "**Componente:** [Identificar]\n"
                "**Condición observada:** [Daño visto]\n\n"
                "### Evaluación Técnica\n"
                "[Citar norma e incumplimiento]\n\n"
                "### Pasos a Seguir (Protocolo de Desvío)\n"
                "1. [Seguridad] | 2. [Registro] | 3. [Remediación]\n\n"
                f"Hallazgo original: {hallazgo}"
            )
            
            contenidos = [prompt_tecnico]
            if not contexto or len(contexto) < 300:
                with open(tmp_path, "rb") as f:
                    contenidos.append(types.Part.from_bytes(data=f.read(), mime_type="application/pdf"))
            
            if lista_imagenes:
                for img_tuple in lista_imagenes:
                    # Desempaquetado explícito
                    img_data = img_tuple[0]
                    img_mime = img_tuple[1]
                    contenidos.append(types.Part.from_bytes(data=img_data, mime_type=img_mime))

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