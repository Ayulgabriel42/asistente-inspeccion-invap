import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import numpy as np
from PIL import Image
import io
import datetime

# =========================================================
# 1. MOTOR DE IA (InspeccionEngine)
# =========================================================
class InspeccionEngine:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.5-flash" 

    def procesar_hallazgo(self, sistema, observacion):
        prompt = f"""
        Actúa como Inspector Senior de INVAP.
        SISTEMA: {sistema}
        HALLAZGO: {observacion}
        TAREA: Clasifica según API RP 4G y sugiere acción técnica.
        Responde en español profesional.
        """
        try:
            response = self.client.models.generate_content(model=self.model_id, contents=prompt)
            return response.text
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def analizar_visual(self, imagen_bytes, mime_type, observacion_texto, sistema):
        prompt = f"""
        Actúa como Inspector Senior de INVAP Ingeniería S.A.
        SISTEMA: {sistema} | OBSERVACIÓN: {observacion_texto}
        TAREA: Analiza la imagen, identifica daños y cruza con normas ASME/API.
        Determina No Conformidad y acción (Reparar/Reemplazar).
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[prompt, types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type)]
            )
            return response.text
        except Exception as e:
            return f"❌ Error Visual: {str(e)}"

    def transcribir_audio(self, audio_bytes, mime_type):
        prompt = "Transcribe este audio técnico de inspección de INVAP. Solo el texto limpio."
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
        1. Secciones: 1. INTRODUCCIÓN, 2. DESARROLLO (2.1 Pozo, 2.2 Equipo, 2.3 Campo), 3. CONCLUSIÓN.
        2. Reporte Campo: Debe separar Documental (2.3.1) de Visual (2.3.2).
        3. Hallazgos: Requiere Descripción, Foto y Criticidad (Crítica/Mayor/Menor).
        4. Resumen: Debe incluir tabla de desvíos Relevados vs Solucionados.
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
# 2. INTERFAZ STREAMLIT
# =========================================================
st.set_page_config(page_title="INVAP - Ecosistema de IA", page_icon="⚙️", layout="wide")

# Estilos
st.markdown("<style>.stButton>button {width: 100%; font-weight: bold;}</style>", unsafe_allow_html=True)

# Inicialización
if 'GEMINI_API_KEY' not in st.secrets:
    st.error("Configura GEMINI_API_KEY en secrets.")
    st.stop()

if 'motor' not in st.session_state:
    st.session_state['motor'] = InspeccionEngine(api_key=st.secrets["GEMINI_API_KEY"])

# Cabecera
col_l, col_t = st.columns([1, 5])
with col_l: st.image("https://www.invap.com.ar/wp-content/uploads/2022/04/Logo-INVAP-Blanco.png", width=100)
with col_t: st.title("Sistema Inteligente de Gestión de Integridad")

tab_dash, tab_inspeccion, tab_qa = st.tabs(["📊 Dashboard", "🚀 Asistente de Inspección", "🔍 Agente QA FE-44"])

# --- TAB 1: DASHBOARD ---
with tab_dash:
    st.subheader("Estado Global de Activos")
    m1, m2, m3 = st.columns(3)
    m1.metric("Inspecciones", "142", "+5")
    m2.metric("Críticos", "12", "⚠️", delta_color="inverse")
    m3.metric("Conformidad", "94%")
    st.area_chart(pd.DataFrame(np.random.randn(20, 2), columns=['Mástiles', 'Bombas']))

# --- TAB 2: ASISTENTE ---
with tab_inspeccion:
    st.subheader("🚀 Nueva Inspección Técnica")
    
    # BOTÓN REFRESH
    if st.button("🔄 Iniciar Nueva Inspección (Limpiar)"):
        for key in ['input_hallazgo_usuario', 'ultimo_informe']:
            if key in st.session_state: del st.session_state[key]
        st.rerun()

    c1, c2 = st.columns([1, 2])
    with c1:
        sistema = st.selectbox("Sistema:", ["Mástil/Subestructura", "Izaje", "Piping", "Recipientes", "Bombas"])
        foto_c = st.camera_input("Cámara")
        foto_a = st.file_uploader("Archivo", type=["jpg", "png"])
        foto_f = foto_c if foto_c else foto_a
        
        audio = st.audio_input("Voz")
        if audio:
            with st.spinner("Transcribiendo..."):
                st.session_state['input_hallazgo_usuario'] = st.session_state['motor'].transcribir_audio(audio.read(), audio.type)
        
        hallazgo = st.text_area("Descripción:", height=150, key="input_hallazgo_usuario")
        
        if st.button("Generar Informe"):
            with st.spinner("Analizando..."):
                if foto_f:
                    res = st.session_state['motor'].analizar_visual(foto_f.read(), foto_f.type, hallazgo, sistema)
                else:
                    res = st.session_state['motor'].procesar_hallazgo(sistema, hallazgo)
                st.session_state['ultimo_informe'] = res

    with c2:
        if st.session_state.get('ultimo_informe'):
            st.info(st.session_state['ultimo_informe'])

# --- TAB 3: QA ---
with tab_qa:
    st.subheader("🔍 Auditoría de Formato FE-44")

    # BOTÓN REFRESH
    if st.button("🔄 Limpiar Auditoría"):
        if 'resultado_qa' in st.session_state: del st.session_state['resultado_qa']
        st.rerun()

    archivo_pdf = st.file_uploader("Subir PDF (FE-44)", type=["pdf"])
    texto_qa = st.text_area("O pegue el texto:")
    
    if st.button("Auditar Reporte"):
        with st.spinner("Validando..."):
            if archivo_pdf:
                st.session_state['resultado_qa'] = st.session_state['motor'].auditar_formato_invap(archivo_pdf.read(), es_pdf=True)
            else:
                st.session_state['resultado_qa'] = st.session_state['motor'].auditar_formato_invap(texto_qa, es_pdf=False)
    
    if st.session_state.get('resultado_qa'):
        st.success(st.session_state['resultado_qa'])

st.divider()
st.caption(f"© {datetime.date.today().year} INVAP Ingeniería S.A. | Gabriel A. | Formato FE-44 rev00")