import os
import io
import json
import datetime
import pandas as pd

from google import genai
from google.genai import types
from google.cloud import storage

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader


class InspeccionEngine:
    def __init__(self, api_key, creds=None, project_id=None):
        self.creds = creds
        self.project_id = project_id
        self.model_id = "gemini-3-flash-preview"
        self.bucket_name = "invap-asistente-normas"

        # Mantener una sola key activa para evitar advertencias/confusión
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ["GOOGLE_API_KEY"] = api_key

        self.client = genai.Client(api_key=api_key)

    # =========================================================
    # CLASIFICADOR DE NORMA (manteniendo estructura original)
    # =========================================================
    def clasificar_norma_ia(self, hallazgo, lista_normas, lista_imagenes=None):
        """
        Mantiene la lógica original:
        1. intenta detectar dominio
        2. filtra lista
        3. elige un PDF candidato
        """
        if not lista_normas:
            return None

        hallazgo_lower = hallazgo.lower() if hallazgo else ""

        prompt_dominio = (
            "Analiza el hallazgo y las imágenes. Determina la categoría técnica:\n"
            "- IZAJE: Eslingas, cables, ganchos, grilletes.\n"
            "- ESTRUCTURA: Mástiles, subestructuras, bancadas, API 4G/4F.\n"
            "- GRÚA MÓVIL: Chasis, pluma telescópica, ASME B30.5.\n"
            "- MECÁNICO: Tanques, recipientes, tuberías.\n"
            "Responde SOLO la palabra de la categoría."
        )

        contenidos_v = [prompt_dominio]
        if lista_imagenes:
            for img_data, img_mime in lista_imagenes:
                contenidos_v.append(
                    types.Part.from_bytes(data=img_data, mime_type=img_mime)
                )

        try:
            res_v = self.client.models.generate_content(
                model=self.model_id,
                contents=contenidos_v
            )
            dominio = res_v.text.strip().upper()
        except Exception:
            dominio = "OTRO"

        lista_final = lista_normas.copy()

        # Reglas originales + pequeños refuerzos
        if "ESTRUCTURA" in dominio or "MÁSTIL" in hallazgo_lower or "MASTIL" in hallazgo_lower:
            lista_final = [
                n for n in lista_final
                if any(x in n.upper() for x in ["4G", "4F", "ESTRUCTURA"])
            ]

        elif (
            "IZAJE" in dominio
            or "ESLINGA" in hallazgo_lower
            or "GRILLETE" in hallazgo_lower
            or "GANCHO" in hallazgo_lower
            or "CABLE" in hallazgo_lower
            or "ALAMBRES" in hallazgo_lower
            or "OJAL" in hallazgo_lower
        ):
            lista_final = [
                n for n in lista_final
                if any(
                    x in n.upper()
                    for x in ["B30.9", "ESLINGA", "3914", "B30.10", "B30.26", "SLING", "HOOK", "RIGGING"]
                )
            ]

        elif (
            "GRÚA" in hallazgo_lower
            or "GRUA" in hallazgo_lower
            or "PLUMA" in hallazgo_lower
            or "TELESCOP" in hallazgo_lower
            or "GRÚA MÓVIL" in dominio
            or "GRUA MÓVIL" in dominio
        ):
            lista_final = [
                n for n in lista_final
                if any(x in n.upper() for x in ["B30.5", "CRANE", "GRUA"])
            ]

        elif (
            "ROSCA" in hallazgo_lower
            or "THREAD" in hallazgo_lower
            or "CASING" in hallazgo_lower
            or "TUBING" in hallazgo_lower
        ):
            lista_final = [
                n for n in lista_final
                if any(x in n.upper() for x in ["5A5", "5B", "CASING", "TUBING", "THREAD"])
            ]

        if not lista_final:
            lista_final = lista_normas

        prompt_final = (
            f"ERES UN EXPERTO TÉCNICO DE INVAP.\n"
            f"Categoría detectada: {dominio}.\n"
            f"Hallazgo: '{hallazgo}'.\n"
            f"Selecciona el PDF más probable de esta lista: {lista_final[:40]}.\n"
            "Responde ÚNICAMENTE con el nombre exacto del archivo."
        )

        contenidos_f = [prompt_final]
        if lista_imagenes:
            for img_data, img_mime in lista_imagenes:
                contenidos_f.append(
                    types.Part.from_bytes(data=img_data, mime_type=img_mime)
                )

        try:
            res = self.client.models.generate_content(
                model=self.model_id,
                contents=contenidos_f
            )
            seleccion = (
                res.text.strip()
                .replace("`", "")
                .replace("'", "")
                .replace('"', "")
            )
            return seleccion if seleccion in lista_normas else lista_normas[0]
        except Exception:
            return lista_normas[0]

    # =========================================================
    # CONSULTA RAG SOBRE PDF ELEGIDO (estructura original)
    # =========================================================
    def consultar_normativa_rag(self, norma_path, hallazgo, lista_imagenes=None):
        """
        Mantiene la arquitectura actual:
        1. descarga el PDF elegido
        2. arma embeddings de ese PDF
        3. recupera contexto
        4. genera informe técnico controlado
        """
        storage_client = storage.Client(credentials=self.creds, project=self.project_id)
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob(norma_path)

        tmp_path = f"temp_{norma_path.split('/')[-1]}".replace(" ", "_")

        try:
            blob.download_to_filename(tmp_path)

            pages = []
            contexto = ""

            # Lectura protegida del PDF
            try:
                loader = PyPDFLoader(tmp_path)
                pages = loader.load_and_split()
            except Exception as e:
                pages = []
                contexto = f"No se pudo extraer texto del PDF ({norma_path}). Error de lectura: {str(e)}"

            if pages:
                try:
                    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
                    vectorstore = FAISS.from_documents(pages, embeddings)

                    docs = vectorstore.similarity_search(
                        f"criterios rechazo descarte inspección {hallazgo}",
                        k=8
                    )

                    contexto = "\n\n".join([doc.page_content for doc in docs])
                except Exception as e:
                    contexto = f"Error al construir contexto semántico del PDF: {str(e)}"

            prompt_tecnico = (
                f"SISTEMA DE INTEGRIDAD INVAP | Norma: {norma_path}\n"
                "==========================================================\n"
                f"CONTEXTO TÉCNICO RECUPERADO DEL PDF:\n{contexto}\n"
                "==========================================================\n\n"
                "INSTRUCCIONES CRÍTICAS:\n"
                "1. Tu informe debe basarse EXCLUSIVAMENTE en el 'CONTEXTO TÉCNICO RECUPERADO'.\n"
                "2. PROHIBIDO citar requerimientos de otras normas que no aparezcan en el texto anterior.\n"
                "3. Si el texto no menciona criterios para el hallazgo, indica: "
                "'Criterio no encontrado en esta sección de la norma'.\n\n"
                "### Estructura del Informe:\n"
                "**Componente:** [Nombre]\n"
                "**Condición:** [Descripción técnica del daño visto]\n"
                "**Evaluación:** [Citar específicamente el párrafo o criterio recuperado]\n"
                "**Acción:** [Protocolo de seguridad según la norma]\n\n"
                f"Hallazgo original del inspector: {hallazgo}"
            )

            contenidos = [prompt_tecnico]

            # Fallback multimodal si hay poco contexto o falla el parser
            if not pages or not contexto or len(contexto) < 300:
                try:
                    with open(tmp_path, "rb") as f:
                        contenidos.append(
                            types.Part.from_bytes(data=f.read(), mime_type="application/pdf")
                        )
                except Exception:
                    pass

            if lista_imagenes:
                for img_data, img_mime in lista_imagenes:
                    contenidos.append(
                        types.Part.from_bytes(data=img_data, mime_type=img_mime)
                    )

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contenidos
            )

            return response.text, norma_path

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # =========================================================
    # CONSULTAS LIBRES SOBRE NORMAS (versión robusta)
    # =========================================================
    def consultar_normas_chat(self, pregunta, lista_normas, lista_imagenes=None):
        """
        Consulta libre para la solapa 'Consultas Normativas'.

        Versión robusta y liviana:
        - no depende de parsear JSON
        - no abre múltiples PDFs
        - no hace RAG pesado
        - responde con orientación técnica sobre qué norma podría aplicar
        """
        if not pregunta:
            return "No se recibió ninguna pregunta."

        if not lista_normas:
            return "No hay normas disponibles cargadas en el sistema."

        pregunta_lower = pregunta.lower()

        # -----------------------------------------------------
        # 1) Preselección simple por palabras clave
        # -----------------------------------------------------
        candidatas = []

        for norma in lista_normas:
            n = norma.lower()
            score = 0

            if any(x in pregunta_lower for x in ["eslinga", "grillete", "gancho", "cable", "alambres", "ojal", "izaje"]):
                if any(x in n for x in ["b30.9", "b30.10", "b30.26", "sling", "hook", "rigging"]):
                    score += 5

            if any(x in pregunta_lower for x in ["mastil", "mástil", "subestructura", "estructura", "derrick"]):
                if any(x in n for x in ["4g", "4f", "estructura"]):
                    score += 4

            if any(x in pregunta_lower for x in ["grua", "grúa", "pluma", "boom", "mobile crane"]):
                if any(x in n for x in ["b30.5", "crane"]):
                    score += 4

            if any(x in pregunta_lower for x in ["winche", "tambor", "drum", "spooling"]):
                if any(x in n for x in ["b30.7", "winch"]):
                    score += 4

            if any(x in pregunta_lower for x in ["rosca", "thread", "casing", "tubing", "pipe"]):
                if any(x in n for x in ["5b", "5a5", "casing", "tubing", "thread"]):
                    score += 4

            if score > 0:
                candidatas.append((norma, score))

        candidatas.sort(key=lambda x: x[1], reverse=True)
        top_normas = [x[0] for x in candidatas[:5]]

        if not top_normas:
            top_normas = lista_normas[:5]

        # -----------------------------------------------------
        # 2) Respuesta IA orientativa
        # -----------------------------------------------------
        prompt = (
            "Eres un asistente técnico experto en normativa industrial.\n\n"
            f"Pregunta del usuario:\n{pregunta}\n\n"
            f"Normas candidatas disponibles en el sistema:\n{top_normas}\n\n"
            "INSTRUCCIONES:\n"
            "1. Responde de forma técnica y clara.\n"
            "2. Indica cuál sería la norma principal sugerida.\n"
            "3. Indica normas relacionadas si corresponde.\n"
            "4. Explica brevemente por qué podrían aplicar.\n"
            "5. Si no hay certeza completa, indícalo.\n"
            "6. No inventes párrafos exactos ni requisitos específicos que no fueron recuperados del PDF.\n\n"
            "Formato de respuesta:\n"
            "**Norma principal sugerida:** ...\n"
            "**Normas relacionadas:** ...\n"
            "**Fundamento técnico:** ...\n"
            "**Observación:** ...\n"
        )

        contenidos = [prompt]

        if lista_imagenes:
            for img_data, img_mime in lista_imagenes:
                contenidos.append(
                    types.Part.from_bytes(data=img_data, mime_type=img_mime)
                )

        try:
            res = self.client.models.generate_content(
                model=self.model_id,
                contents=contenidos
            )
            return res.text
        except Exception as e:
            return f"No se pudo responder la consulta normativa: {e}"

    # =========================================================
    # MEMORIA DE LARGO PLAZO
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
        except Exception:
            df_final = nuevo_registro

        buffer = io.BytesIO()
        df_final.to_parquet(buffer, index=False)
        blob.upload_from_string(buffer.getvalue(), content_type="application/octet-stream")

    # =========================================================
    # REFINAMIENTO DE INFORME
    # =========================================================
    def refinar_informe(self, informe_previo, comentario):
        prompt = (
            "Eres un editor técnico de informes industriales.\n\n"
            f"Informe actual:\n{informe_previo}\n\n"
            f"Cambio solicitado:\n{comentario}\n\n"
            "Mejora redacción, claridad y formato técnico, "
            "sin alterar el sentido del informe."
        )

        res = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt
        )
        return res.text

    # =========================================================
    # TRANSCRIPCIÓN DE AUDIO
    # =========================================================
    def transcribir_audio(self, audio_bytes, mime_type):
        res = self.client.models.generate_content(
            model=self.model_id,
            contents=[types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)]
        )
        return res.text

    # =========================================================
    # QA SOBRE PDF
    # =========================================================
    def analizar_pdf_qa(self, pdf_bytes, prompt_p):
        res = self.client.models.generate_content(
            model=self.model_id,
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                prompt_p
            ]
        )
        return res.text