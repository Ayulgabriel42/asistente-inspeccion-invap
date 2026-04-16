import os
import datetime
import io
import pandas as pd
from google import genai
from google.genai import types
from google.cloud import storage
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader

class InspeccionEngine:
    def __init__(self, api_key, creds=None, project_id=None): 
        self.client = genai.Client(api_key=api_key)
        self.creds = creds 
        self.project_id = project_id
        self.model_id = "gemini-3-flash-preview" 
        self.bucket_name = "invap-asistente-normas"
        os.environ["GOOGLE_API_KEY"] = api_key

    # =========================================================
    # CLASIFICADOR UNIVERSAL POR DOMINIOS
    # =========================================================
    def clasificar_norma_ia(self, hallazgo, lista_normas, lista_imagenes=None):
        hallazgo_lower = hallazgo.lower()
        
        # PASO 1: Identificar la "familia" del equipo para filtrar la lista de PDFs
        prompt_dominio = (
            "Analiza el hallazgo y las imágenes. Determina la categoría técnica:\n"
            "- IZAJE: Eslingas, cables, ganchos, grilletes.\n"
            "- ESTRUCTURA: Mástiles, subestructuras, bancadas, API 4G/4F.\n"
            "- GRÚA MÓVIL: Chasis, pluma telescopica, ASME B30.5.\n"
            "- MECÁNICO: Tanques, recipientes, tuberías.\n"
            "Responde SOLO la palabra de la categoría."
        )
        
        contenidos_v = [prompt_dominio]
        if lista_imagenes:
            for img_data, img_mime in lista_imagenes:
                contenidos_v.append(types.Part.from_bytes(data=img_data, mime_type=img_mime))
        
        try:
            res_v = self.client.models.generate_content(model=self.model_id, contents=contenidos_v)
            dominio = res_v.text.strip().upper()
        except: dominio = "OTRO"

        # PASO 2: Filtrado lógico (Agnóstico a la norma específica)
        lista_final = lista_normas.copy()
        if "ESTRUCTURA" in dominio or "MÁSTIL" in hallazgo_lower:
            lista_final = [n for n in lista_final if any(x in n.upper() for x in ["4G", "4F", "ESTRUCTURA"])]
        elif "IZAJE" in dominio or "ESLINGA" in hallazgo_lower:
            lista_final = [n for n in lista_final if any(x in n.upper() for x in ["B30.9", "ESLINGA", "3914", "B30.10", "B30.26"])]
        
        if not lista_final: lista_final = lista_normas

        # PASO 3: Selección final del PDF
        prompt_final = (
            f"ERES UN EXPERTO DE INVAP. Categoría detectada: {dominio}.\n"
            f"Hallazgo: '{hallazgo}'.\n"
            f"Selecciona el PDF correcto de esta lista: {lista_final[:40]}.\n"
            "Responde ÚNICAMENTE con el nombre exacto del archivo."
        )
        
        contenidos_f = [prompt_final]
        if lista_imagenes:
            for img_data, img_mime in lista_imagenes:
                contenidos_f.append(types.Part.from_bytes(data=img_data, mime_type=img_mime))

        try:
            res = self.client.models.generate_content(model=self.model_id, contents=contenidos_f)
            seleccion = res.text.strip().replace("`", "").replace("'", "")
            return seleccion if seleccion in lista_normas else lista_normas[0]
        except: return lista_normas[0]

    # =========================================================
    # MOTOR RAG CON MURO DE CONTENCIÓN (FIDELIDAD AL PDF)
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
                    # Aumentamos k para capturar más criterios técnicos
                    docs = vectorstore.similarity_search(f"criterios rechazo descarte inspección {hallazgo}", k=8)
                    contexto = "\n\n".join([doc.page_content for doc in docs])
                except: contexto = "Error al extraer texto. Analice el PDF visualmente si está adjunto."

            # PROMPT CON MURO DE CONTENCIÓN
            prompt_tecnico = (
                f"SISTEMA DE INTEGRIDAD INVAP | Norma: {norma_path}\n"
                "==========================================================\n"
                f"CONTEXTO TÉCNICO RECUPERADO DEL PDF:\n{contexto}\n"
                "==========================================================\n\n"
                "INSTRUCCIONES CRÍTICAS:\n"
                "1. Tu informe debe basarse EXCLUSIVAMENTE en el 'CONTEXTO TÉCNICO RECUPERADO' arriba.\n"
                "2. PROHIBIDO citar requerimientos de otras normas que no aparezcan en el texto anterior.\n"
                "3. Si el texto no menciona criterios para el hallazgo, indica 'Criterio no encontrado en esta sección de la norma'.\n\n"
                "### Estructura del Informe:\n"
                "**Componente:** [Nombre]\n"
                "**Condición:** [Descripción técnica del daño visto]\n"
                "**Evaluación:** [Citar específicamente el párrafo o tabla del contexto que se incumple]\n"
                "**Acción:** [Protocolo de seguridad según la norma]\n\n"
                f"Hallazgo original del inspector: {hallazgo}"
            )
            
            contenidos = [prompt_tecnico]
            # Si el contexto es pobre, le mandamos el PDF entero como binario (Multimodal)
            if not contexto or len(contexto) < 500:
                with open(tmp_path, "rb") as f:
                    contenidos.append(types.Part.from_bytes(data=f.read(), mime_type="application/pdf"))
            
            if lista_imagenes:
                for img_data, img_mime in lista_imagenes:
                    contenidos.append(types.Part.from_bytes(data=img_data, mime_type=img_mime))

            response = self.client.models.generate_content(model=self.model_id, contents=contenidos)
            return response.text, norma_path
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

    # =========================================================
    # MEMORIA DE LARGO PLAZO (HISTORIAL)
    # =========================================================
    def guardar_leccion_aprendida(self, hallazgo, informe_final, norma_usada):
        storage_client = storage.Client(credentials=self.creds, project=self.project_id)
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob("historial_lecciones/memoria_tecnica.parquet")
        
        nuevo_registro = pd.DataFrame([{
            "fecha": datetime.datetime.now(),
            "hallazgo_original": hallazgo,
            "informe_final": informe_final,
            "norma_referencia": norma_usada
        }])

        try:
            content = blob.download_as_bytes()
            df_historico = pd.read_parquet(io.BytesIO(content))
            df_final = pd.concat([df_historico, nuevo_registro], ignore_index=True)
        except:
            df_final = nuevo_registro

        buffer = io.BytesIO()
        df_final.to_parquet(buffer, index=False)
        blob.upload_from_string(buffer.getvalue(), content_type="application/octet-stream")

    def refinar_informe(self, informe_previo, comentario):
        res = self.client.models.generate_content(model=self.model_id, contents=f"Editor INVAP: {informe_previo}. Cambio solicitado: {comentario}")
        return res.text

    def transcribir_audio(self, audio_bytes, mime_type):
        res = self.client.models.generate_content(model=self.model_id, contents=[types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)])
        return res.text

    def analizar_pdf_qa(self, pdf_bytes, prompt_p):
        res = self.client.models.generate_content(model=self.model_id, contents=[types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"), prompt_p])
        return res.text