# --- engine.py ---
from google import genai
from google.genai import types
from google.cloud import storage
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
import os

class InspeccionEngine:
    # EL CAMBIO ESTÁ AQUÍ: Agregamos , creds=None
    def __init__(self, api_key, creds=None): 
        self.client = genai.Client(api_key=api_key)
        self.creds = creds  # <--- Esto es lo que faltaba guardar
        self.model_id = "gemini-2.5-flash"
        self.bucket_name = "invap-asistente-normas"
        os.environ["GOOGLE_API_KEY"] = api_key

    # ... (El resto de tus funciones: clasificar_norma_ia, consultar_normativa_rag, etc.)
    # Asegurate de que consultar_normativa_rag use: storage.Client(credentials=self.creds)

    # =========================================================
    # CLASIFICADOR INTELIGENTE
    # =========================================================
    def clasificar_norma_ia(self, hallazgo, lista_normas):
        """Analiza el hallazgo y elige la mejor norma del bucket."""
        prompt = (
            f"Actúa como clasificador experto de INVAP. De la siguiente lista de rutas de PDFs, "
            f"elige la ruta exacta del archivo más relevante para el hallazgo: '{hallazgo}'. "
            f"\nLISTA: {lista_normas[:100]}\n\n"
            "Responde únicamente con el nombre o ruta del archivo."
        )
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=prompt)
            seleccion = res.text.strip()
            return seleccion if seleccion in lista_normas else lista_normas[0]
        except Exception:
            return lista_normas[0]

    # =========================================================
    # MOTOR RAG (CON CREDENCIALES EN MEMORIA)
    # =========================================================
    def consultar_normativa_rag(self, norma_path, hallazgo):
        """Descarga el PDF usando credenciales directas y procesa el RAG."""
        
        # PASO CLAVE: Pasamos las credenciales al cliente de Storage
        storage_client = storage.Client(credentials=self.creds)
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob(norma_path)
        
        tmp_path = f"temp_{norma_path.split('/')[-1]}".replace(" ", "_")
        
        try:
            blob.download_to_filename(tmp_path)
            
            # Procesamiento RAG
            loader = PyPDFLoader(tmp_path)
            pages = loader.load_and_split()
            
            # Modelo de embeddings validado anteriormente
            embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
            
            vectorstore = FAISS.from_documents(pages, embeddings)
            docs = vectorstore.similarity_search(hallazgo, k=5)
            contexto = "\n\n".join([doc.page_content for doc in docs])

            # Generación de respuesta técnica
            prompt = (
                f"Eres un Inspector Senior de INVAP. Basado ÚNICAMENTE en el contexto "
                f"extraído de la norma '{norma_path}':\n\n{contexto}\n\n"
                f"Responde de forma técnica y profesional a: {hallazgo}"
            )
            response = self.client.models.generate_content(model=self.model_id, contents=prompt)
            return response.text, norma_path
            
        finally:
            # Limpieza de archivos temporales
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # =========================================================
    # FUNCIONES ORIGINALES (PRESERVADAS)
    # =========================================================
    def procesar_hallazgo(self, sistema, observacion):
        prompt = f"Actúa como Inspector Senior de INVAP. SISTEMA: {sistema}. HALLAZGO: {observacion}. TAREA: Clasifica según API RP 4G y sugiere acción correctiva técnica."
        try:
            response = self.client.models.generate_content(model=self.model_id, contents=prompt)
            return response.text
        except Exception as e:
            return f"❌ Error en el motor: {str(e)}"

    def transcribir_audio(self, audio_bytes, mime_type):
        prompt = "Actúa como inspector de INVAP. Transcribe este audio ignorando ruidos de fondo. Devuelve solo el texto técnico limpio."
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[prompt, types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)]
            )
            return response.text
        except Exception as e:
            return f"❌ Error en la IA al transcribir: {str(e)}"

    def analizar_pdf_qa(self, pdf_bytes, prompt_personalizado):
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"), prompt_personalizado]
            )
            return response.text
        except Exception as e:
            return f"❌ Error analizando el PDF: {str(e)}"

    def analizar_visual(self, imagen_bytes, mime_type, observacion, sistema):
        prompt = f"Inspector INVAP: Analiza daños en {sistema}. Hallazgo: {observacion}."
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type), prompt]
            )
            return response.text
        except Exception as e:
            return f"❌ Error Visual: {str(e)}"