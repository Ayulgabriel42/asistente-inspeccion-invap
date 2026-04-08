import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import numpy as np
import datetime

# =========================================================
# 1. MOTOR DE IA (InspeccionEngine) - INTEGRADO CON NORMAS
# =========================================================

# Diccionario de normas según listados de INVAP
MAPEO_NORMAS = {
    "Mástil/Subestructura": "API RP 4G (Inspección de Estructuras)",
    "Piping / Tuberías": "ASME B31.3 / API 570",
    "Recipientes a Presión": "ASME Sección VIII / API 510",
    "Soldadura y Estructuras": "AWS D1.1 (Structural Welding Code)",
    "Izaje y Puentes Grúa": "IRAM 2552 / ASME B30.5",
    "Bombas y Equipos": "API 610 / Normas específicas"
}

class InspeccionEngine:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-1.5-flash-001"

    def procesar_hallazgo(self, sistema, observacion):
        norma = MAPEO_NORMAS.get(sistema, "Normas de referencia INVAP")
        prompt = f"""
        Actúa como Inspector Senior de INVAP.
        SISTEMA: {sistema} | NORMA: {norma}
        HALLAZGO: {observacion}
        TAREA: Clasifica criticidad y sugiere acción técnica profesional.
        """
        try:
            response = self.client.models.generate_content(model=self.model_id, contents=prompt)
            return response.text
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def analizar_visual(self, imagen_bytes, mime_type, observacion, sistema):
        norma = MAPEO_NORMAS.get(sistema, "API/ASME")
        prompt = f"Inspector INVAP: Analiza daños en {sistema} según {norma}. Hallazgo: {observacion}"
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[prompt, types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type)]
            )
            return response.text
        except Exception as e:
            return f"❌ Error Visual: {str(e)}"

    def transcribir_audio(self, audio_bytes, mime_type):
        # Prompt optimizado para ambientes ruidosos (Bases de diseño INVAP)
        prompt = "Transcribe audio técnico de inspección. Ignora ruido de fondo, viento y motores. Solo texto técnico limpio."
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[prompt, types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)]
            )
            return response.text
        except Exception as e:
            return f"❌ Error Audio: {str(e)}"

    def auditar_formato_invap(self, contenido_reporte, es_pdf=False):
        reglas_invap = """
        ESTÁNDAR FE-44 rev00:
        1. Secciones: 1. INTRODUCCIÓN, 2. DESARROLLO, 3. CONCLUSIÓN.
        2. Hallazgos: Requiere Descripción, Foto y Criticidad.
        """
        prompt = f"{reglas_invap}\n\nAnaliza si el reporte cumple el formato FE-44 de INVAP:"
        try:
            if es_pdf:
                c = [prompt, types.Part.from_bytes(data=contenido_reporte, mime_type="application/pdf")]
            else:
                c = f"{prompt}\n\nREPORTE:\n{contenido_reporte}"
            return self.client.models.generate_content(model=self.model_id, contents=c).text
        except Exception as e:
            return f"❌ Error QA: {str(e)}"

# =========================================================
# 2. INTERFAZ STREAMLIT (Recuperando Dashboard y Tabs)
# =========================================================
st.set_page_config(page_title="INVAP - Ecosistema de IA", page_icon="⚙️", layout="wide")

if 'motor' not in st.session_state:
    st.session_state['motor'] = InspeccionEngine(api_key=st.secrets["GEMINI_API_KEY"])

# Cabecera original
col_l, col_t = st.columns([1, 5])
with col_l: st.image("https://www.invap.com.ar/wp-content/uploads/2022/04/Logo-INVAP-Blanco.png", width=100)
with col_t: st.title("Sistema Inteligente de Gestión de Integridad")

# Recuperamos los 3 Tabs originales
tab_dash, tab_inspeccion, tab_qa = st.tabs(["📊 Dashboard", "🚀 Asistente de Inspección", "🔍 Agente QA FE-44"])

# --- TAB 1: DASHBOARD (Recuperado) ---
with tab_dash:
    st.subheader("Estado Global de Activos")
    m1, m2, m3 = st.columns(3)
    m1.metric("Inspecciones", "142", "+5")
    m2.metric("Críticos", "12", "⚠️", delta_color="inverse")
    m3.metric("Conformidad", "94%")
    st.area_chart(pd.DataFrame(np.random.randn(20, 2), columns=['Mástiles', 'Bombas']))

# --- TAB 2: ASISTENTE (Con lógica de normas agregada) ---
with tab_inspeccion:
    st.subheader("🚀 Nueva Inspección Técnica")
    
    if st.button("🔄 Iniciar Nueva Inspección (Limpiar)"):
        for key in ['input_hallazgo_usuario', 'ultimo_informe']:
            if key in st.session_state: del st.session_state[key]
        st.rerun()

    c1, c2 = st.columns([1, 2])
    with c1:
        sistema_sel = st.selectbox("Sistema:", list(MAPEO_NORMAS.keys()))
        st.info(f"📚 Norma Aplicada: **{MAPEO_NORMAS[sistema_sel]}**")
        
        foto_c = st.camera_input("Cámara")
        foto_a = st.file_uploader("Archivo", type=["jpg", "png"])
        foto_f = foto_c if foto_c else foto_a
        
        audio = st.audio_input("Voz")
        if audio:
            with st.spinner("Transcribiendo en ambiente ruidoso..."):
                st.session_state['input_hallazgo_usuario'] = st.session_state['motor'].transcribir_audio(audio.read(), audio.type)
        
        hallazgo = st.text_area("Descripción:", value=st.session_state.get('input_hallazgo_usuario', ""), height=150)
        
        if st.button("Generar Informe"):
            with st.spinner("Analizando bajo normativa..."):
                if foto_f:
                    res = st.session_state['motor'].analizar_visual(foto_f.read(), foto_f.type, hallazgo, sistema_sel)
                else:
                    res = st.session_state['motor'].procesar_hallazgo(sistema_sel, hallazgo)
                st.session_state['ultimo_informe'] = res

    with c2:
        if st.session_state.get('ultimo_informe'):
            st.info(st.session_state['ultimo_informe'])

# --- TAB 3: QA (Recuperado) ---
with tab_qa:
    st.subheader("🔍 Auditoría de Formato FE-44")
    if st.button("🔄 Limpiar Auditoría"):
        if 'resultado_qa' in st.session_state: del st.session_state['resultado_qa']
        st.rerun()

    archivo_pdf = st.file_uploader("Subir PDF (FE-44)", type=["pdf"])
    texto_qa = st.text_area("O pegue el texto:")
    
    if st.button("Auditar Reporte"):
        with st.spinner("Validando cumplimiento..."):
            if archivo_pdf:
                st.session_state['resultado_qa'] = st.session_state['motor'].auditar_formato_invap(archivo_pdf.read(), es_pdf=True)
            else:
                st.session_state['resultado_qa'] = st.session_state['motor'].auditar_formato_invap(texto_qa, es_pdf=False)
    
    if st.session_state.get('resultado_qa'):
        st.success(st.session_state['resultado_qa'])

st.divider()
st.caption(f"© {datetime.date.today().year} INVAP Ingeniería S.A. | Gabriel A. | Formato FE-44 rev00")