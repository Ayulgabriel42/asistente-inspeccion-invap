import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import numpy as np
import datetime
import base64
from engine import InspeccionEngine

# =========================================================
# 1. CONFIGURACIÓN Y MAPEO
# =========================================================
st.set_page_config(page_title="INVAP - Ecosistema de IA", page_icon="⚙️", layout="wide")

MAPEO_NORMAS = {
    "Mástil/Subestructura": "API RP 4G (Inspección de Estructuras)",
    "Piping / Tuberías": "ASME B31.3 / API 570",
    "Recipientes a Presión": "ASME Sección VIII / API 510",
    "Soldadura y Estructuras": "AWS D1.1 (Structural Welding Code)",
    "Izaje y Puentes Grúa": "IRAM 2552 / ASME B30.5",
    "Bombas y Equipos": "API 610 / Normas específicas"
}

if 'motor' not in st.session_state:
    st.session_state['motor'] = InspeccionEngine(api_key=st.secrets["GEMINI_API_KEY"])

# =========================================================
# 2. CABECERA
# =========================================================
col_l, col_t = st.columns([1, 5])
with col_l: 
    st.image("https://www.invap.com.ar/wp-content/uploads/2022/04/Logo-INVAP-Blanco.png", width=100)
with col_t: 
    st.title("Sistema Inteligente de Gestión de Integridad")

tab_dash, tab_inspeccion, tab_qa = st.tabs(["📊 Dashboard", "🚀 Asistente de Inspección", "🔍 Agente QA FE-44"])

# --- TAB 1: DASHBOARD ---
with tab_dash:
    st.subheader("Estado Global de Activos")
    m1, m2, m3 = st.columns(3)
    m1.metric("Inspecciones", "142", "+5")
    m2.metric("Críticos", "12", "⚠️")
    st.area_chart(pd.DataFrame(np.random.randn(20, 2), columns=['Críticos', 'Preventivos']))

# --- TAB 2: ASISTENTE ---
with tab_inspeccion:
    c1, c2 = st.columns([1, 2])
    with c1:
        sistema_sel = st.selectbox("Sistema:", list(MAPEO_NORMAS.keys()))
        
        # Audio
        audio = st.audio_input("Dictar Hallazgo")
        if audio and 'audio_procesado' not in st.session_state:
            with st.spinner("IA Transcribiendo..."):
                st.session_state['input_hallazgo_usuario'] = st.session_state['motor'].transcribir_audio(audio.read(), audio.type)
                st.session_state['audio_procesado'] = True
        
        hallazgo = st.text_area("Descripción:", value=st.session_state.get('input_hallazgo_usuario', ""), height=150)
        
        # IMAGEN: Doble opción (Cámara o Subir Archivo)
        st.write("---")
        st.write("**Evidencia Visual:**")
        foto_c = st.camera_input("Capturar con Cámara")
        foto_a = st.file_uploader("O subir imagen desde galería/archivos", type=["jpg", "png", "jpeg"])
        
        # Prioridad a la cámara, si no hay cámara usa el archivo
        foto_final = foto_c if foto_c else foto_a
        
        if st.button("🚀 Generar Informe Técnico"):
            with st.spinner("Analizando con Gemini 2.5 Flash..."):
                if foto_final:
                    res = st.session_state['motor'].analizar_visual(foto_final.read(), foto_final.type, hallazgo, sistema_sel)
                else:
                    res = st.session_state['motor'].procesar_hallazgo(sistema_sel, hallazgo)
                st.session_state['ultimo_informe'] = res

    with c2:
        st.subheader("📋 Previsualización")
        if st.session_state.get('ultimo_informe'):
            informe_texto = st.session_state['ultimo_informe']
            st.info(informe_texto)
            
            # --- DESCARGA REFORZADA ---
            st.markdown("---")
            b64 = base64.b64encode(informe_texto.encode()).decode()
            nombre_archivo = f"Informe_{sistema_sel.replace('/', '_')}_{datetime.date.today()}.txt"
            
            href = f'<a href="data:file/txt;base64,{b64}" download="{nombre_archivo}" style="text-decoration: none;"><button style="width: 100%; height: 50px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">💾 DESCARGAR INFORME TÉCNICO</button></a>'
            st.markdown(href, unsafe_allow_html=True)
            # --------------------------

            if st.button("🔄 Nueva Inspección"):
                for key in ['input_hallazgo_usuario', 'ultimo_informe', 'audio_procesado']:
                    if key in st.session_state: st.session_state.pop(key, None)
                st.rerun()

# --- TAB 3: QA ---
with tab_qa:
    st.subheader("🔍 Auditoría FE-44")
    archivo_pdf = st.file_uploader("Subir PDF de reporte", type=["pdf"])
    if archivo_pdf and st.button("Auditar Reporte"):
        res_qa = st.session_state['motor'].analizar_pdf_qa(archivo_pdf.read(), "Valida formato FE-44")
        st.success(res_qa)

st.divider()
st.caption(f"© {datetime.date.today().year} INVAP Ingeniería S.A.")