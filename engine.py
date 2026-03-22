from google import genai

class InspeccionEngine:
    def __init__(self, api_key):
        # Cliente conectado a tu cuenta Nivel 1
        self.client = genai.Client(api_key=api_key)
        # 2.5-flash es el modelo obligatorio para proyectos nuevos en 2026
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
            # Esta llamada usa el motor más moderno de Google
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"❌ Error en el motor: {str(e)}"