from google import genai
from google.genai import types

class InspeccionEngine:
    def __init__(self, api_key):
        # Cliente conectado a tu cuenta usando el SDK moderno
        self.client = genai.Client(api_key=api_key)
        # Modelo estándar para proyectos en 2026
        self.model_id = "gemini-2.5-flash"

    def procesar_hallazgo(self, sistema, observacion):
        """Genera el informe final y clasifica el daño."""
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
        """Convierte audio en texto técnico para el MVP de INVAP."""
        prompt = "Actúa como inspector de INVAP. Transcribe este audio ignorando ruidos de fondo de la industria o viento. Devuelve solo el texto técnico limpio."
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    prompt,
                    # Usamos el formato correcto del nuevo SDK para enviar el audio
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
                ]
            )
            return response.text
        except Exception as e:
            return f"❌ Error en la IA al transcribir: {str(e)}"