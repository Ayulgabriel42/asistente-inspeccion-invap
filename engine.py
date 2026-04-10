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
        """
        Inicializa el motor de IA de INVAP.
        Recibe la API Key de Gemini y el objeto de credenciales de Google Cloud.
        """
        self.client = genai.Client(api_key=api_key)
        self.creds = creds 
        self.model_id = "gemini-2.0-flash" # O la versión que estés usando actualmente
        self.bucket_name = "invap-asistente-normas"
        
        # Necesario para que las librerías de LangChain funcionen correctamente
        os.environ["GOOGLE_API_KEY"] = api_key

    # =========================================================
    # 1. CLASIFICADOR DE NORMAS
    # =========================================================
    def clasificar_norma_ia(self, hallazgo, lista_normas):
        """Analiza el contexto y elige el PDF correcto del bucket."""
        prompt = (
            f"Actúa como clasificador experto de INVAP. De la siguiente lista de rutas de PDFs, "
            f"elige la ruta exacta del archivo más relevante para el hallazgo: '{hallazgo}'. "
            f"\nLISTA DE NORMAS DISPONIBLES: {lista_normas[:100]}\n\n"
            "Responde únicamente con el nombre o ruta del archivo, sin texto adicional."
        )
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=prompt)
            seleccion = res.text.strip()
            # Validación: si la IA inventa un nombre, devolvemos la primera por defecto
            return seleccion if seleccion in lista_normas else lista_normas[0]
        except Exception:
            return lista_normas[0]

    # =========================================================
    # 2. MOTOR RAG MULTIMODAL (TEXTO + IMAGEN + PDF)
    # =========================================================
    def consultar_normativa_rag(self, norma_path, hallazgo, imagen_bytes=None, mime_type=None):
        """
        Genera un informe técnico cruzando el PDF de la norma, 
        la descripción del inspector y la evidencia visual.
        """
        # Captura de estampa de tiempo real
        ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        storage_client = storage.Client(credentials=self.creds)
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob(norma_path)
        
        # Nombre temporal único para evitar conflictos
        tmp_path = f"temp_{norma_path.split('/')[-1]}".replace(" ", "_")
        
        try:
            blob.download_to_filename(tmp_path)
            
            # Procesamiento de la normativa
            loader = PyPDFLoader(tmp_path)
            pages = loader.load_and_split()
            embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
            vectorstore = FAISS.from_documents(pages, embeddings)
            
            # Búsqueda semántica en el PDF
            query_rag = hallazgo if hallazgo else "requerimientos técnicos generales"
            docs = vectorstore.similarity_search(query_rag, k=5)
            contexto = "\n\n".join([doc.page_content for doc in docs])

            # Prompt Multimodal con Sello de Tiempo
            prompt_tecnico = f"""
            Actúa como Inspector Senior de INVAP. 
            FECHA Y HORA ACTUAL DEL SISTEMA: {ahora}

            Tu tarea es generar un informe técnico de integridad basado en:
            1. CONTEXTO DE LA NORMA ({norma_path}): {contexto}
            2. DESCRIPCIÓN DEL INSPECTOR: {hallazgo if hallazgo else "Analice la imagen para describir el desvío."}
            3. EVIDENCIA VISUAL: Se adjunta imagen de cámara/archivo (si existe).

            REGLAS CRÍTICAS:
            - Usa OBLIGATORIAMENTE la fecha y hora proporcionada: {ahora}.
            - El tono debe ser estrictamente profesional e ingenieril.
            - Clasifica la severidad del hallazgo según la normativa citada.
            """

            contenidos = [prompt_tecnico]
            if imagen_bytes:
                contenidos.append(types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type))

            response = self.client.models.generate_content(model=self.model_id, contents=contenidos)
            return response.text, norma_path
            
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # =========================================================
    # 3. CHATBOT DE REFINAMIENTO (HUMAN-IN-THE-LOOP)
    # =========================================================
    def refinar_informe(self, informe_previo, comentario):
        """Permite al inspector corregir datos del informe mediante diálogo."""
        ahora_edit = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        prompt = f"""
        Eres un Editor Técnico de INVAP. 
        HORA DE EDICIÓN: {ahora_edit}
        
        INFORME ORIGINAL:
        {informe_previo}
        
        SOLICITUD DE CAMBIO DEL INSPECTOR:
        "{comentario}"
        
        TAREA:
        - Reescribe el informe aplicando las correcciones solicitadas.
        - Si el inspector pide corregir nombres, fechas o valores técnicos, prioriza su comentario.
        - Mantén la estructura profesional del informe original.
        """
        try:
            res = self.client.models.generate_content(model=self.model_id, contents=prompt)
            return res.text
        except Exception as e:
            return f"❌ Error al refinar el informe: {str(e)}"

    # =========================================================
    # 4. FUNCIONES DE APOYO (TRANSCRIPCIÓN, VISIÓN, QA)
    # =========================================================
    def transcribir_audio(self, audio_bytes, mime_type):
        """Convierte dictado de voz a texto técnico."""
        prompt = "Actúa como inspector de INVAP. Transcribe este audio técnico ignorando ruidos de fondo."
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[prompt, types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)]
            )
            return response.text
        except Exception:
            return "❌ Error en la transcripción de audio."

    def analizar_pdf_qa(self, pdf_bytes, prompt_personalizado):
        """Audita reportes en PDF contra criterios de calidad."""
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    prompt_personalizado
                ]
            )
            return response.text
        except Exception as e:
            return f"❌ Error en auditoría QA: {str(e)}"

    def analizar_visual(self, imagen_bytes, mime_type, observacion, sistema):
        """Análisis visual rápido (legacy) si no se requiere RAG."""
        prompt = f"Inspector INVAP: Analiza daños en {sistema}. Observación previa: {observacion}."
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type), prompt]
            )
            return response.text
        except Exception:
            return "❌ Error en el análisis visual."