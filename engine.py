from google import genai
from google.genai import types

class InspeccionEngine:
    def __init__(self, api_key):
        # Inicialización del cliente con el SDK moderno
        self.client = genai.Client(api_key=api_key)
        # ID verificado en tu catálogo de modelos
        self.model_id = "gemini-2.5-flash"

    def procesar_hallazgo(self, sistema, observacion):
        prompt = f"""
        Actúa como Inspector Senior de INVAP.
        SISTEMA: {sistema}
        HALLAZGO: {observacion}
        TAREA: Clasifica según API RP 4G y sugiere acción correctiva técnica.
        Responde en español profesional.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"❌ Error en el motor: {str(e)}"

    def transcribir_audio(self, audio_bytes, mime_type):
        prompt = "Actúa como inspector de INVAP. Transcribe este audio ignorando ruidos de fondo. Devuelve solo el texto técnico limpio."
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
                ]
            )
            return response.text
        except Exception as e:
            return f"❌ Error en la IA al transcribir: {str(e)}"

    def analizar_pdf_qa(self, pdf_bytes, prompt_personalizado):
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
            return f"❌ Error analizando el PDF: {str(e)}"

    def analizar_visual(self, imagen_bytes, mime_type, observacion, sistema):
        prompt = f"Inspector INVAP: Analiza daños en {sistema}. Hallazgo: {observacion}."
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type),
                    prompt
                ]
            )
            return response.text
        except Exception as e:
            return f"❌ Error Visual: {str(e)}"