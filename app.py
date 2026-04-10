import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import numpy as np
import datetime
import base64
import os
from google.cloud import storage
from engine import InspeccionEngine

# =========================================================
# 1. CONFIGURACIÓN Y MAPEO
# =========================================================
st.set_page_config(page_title="INVAP - Ecosistema de IA", page_icon="⚙️", layout="wide")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google-credentials.json"

if 'motor' not in st.session_state:
    st.session_state['motor'] = InspeccionEngine(api_key=st.secrets["GEMINI_API_KEY"])

# NUEVO: Cargar lista de normas del bucket al inicio
if 'lista_normas' not in st.session_state:
    client = storage.Client()
    blobs = client.list_blobs("invap-asistente-normas")
    st.session_state['lista_normas'] = [blob.name for blob in blobs if blob.name.lower().endswith('.pdf')]

# =========================================================
# 2. CABECERA (TU DISEÑO ORIGINAL)
# =========================================================
col_l, col_t = st.columns([1, 5])
with col_l: 
    st.image("https://www.invap.com.ar/wp-content/uploads/2022/04/Logo-INVAP-Blanco.png", width=100)
with col_t: 
    st.title("Sistema Inteligente de Gestión de Integridad")

tab_dash, tab_inspeccion, tab_qa = st.tabs(["📊 Dashboard", "🚀 Asistente de Inspección", "🔍 Agente QA FE-44"])

# --- TAB 1: DASHBOARD (INTACTO) ---
with tab_dash:
    st.subheader("Estado Global de Activos")
    m1, m2, m3 = st.columns(3)
    m1.metric("Inspecciones", "142", "+5")
    m2.metric("Críticos", "12", "⚠️")
    st.area_chart(pd.DataFrame(np.random.randn(20, 2), columns=['Críticos', 'Preventivos']))

# --- TAB 2: ASISTENTE (TU ESTRUCTURA + AGENTE RAG) ---
with tab_inspeccion:
    c1, c2 = st.columns([1, 2])
    with c1:
        sistema_sel = st.selectbox("Sistema:", ["Mástil/Subestructura", "Piping / Tuberías", "Recipientes a Presión", "Soldadura y Estructuras", "Izaje y Puentes Grúa", "Bombas y Equipos"])
        
        audio = st.audio_input("Dictar Hallazgo")
        if audio and 'audio_procesado' not in st.session_state:
            with st.spinner("IA Transcribiendo..."):
                st.session_state['input_hallazgo_usuario'] = st.session_state['motor'].transcribir_audio(audio.read(), audio.type)
                st.session_state['audio_procesado'] = True
        
        hallazgo = st.text_area("Descripción:", value=st.session_state.get('input_hallazgo_usuario', ""), height=150)
        
        st.write("---")
        st.write("**Evidencia Visual:**")
        foto_c = st.camera_input("Capturar con Cámara")
        foto_a = st.file_uploader("O subir imagen", type=["jpg", "png", "jpeg"])
        foto_final = foto_c if foto_c else foto_a
        
        # EL BOTÓN AHORA USA EL AGENTE CLASIFICADOR + RAG
        if st.button("🚀 Generar Informe Técnico"):
            with st.spinner("Agente clasificando norma y analizando con RAG..."):
                if hallazgo:
                    # 1. La IA elige la norma del bucket automáticamente
                    norma_elegida = st.session_state['motor'].clasificar_norma_ia(hallazgo, st.session_state['lista_normas'])
                    # 2. Realiza el RAG sobre esa norma
                    res, norma_ref = st.session_state['motor'].consultar_normativa_rag(norma_elegida, hallazgo)
                    st.session_state['ultimo_informe'] = f"**Norma de Referencia:** {norma_ref}\n\n{res}"
                elif foto_final:
                    st.session_state['ultimo_informe'] = st.session_state['motor'].analizar_visual(foto_final.read(), foto_final.type, hallazgo, sistema_sel)

    with c2:
        st.subheader("📋 Previsualización")
        if st.session_state.get('ultimo_informe'):
            informe_texto = st.session_state['ultimo_informe']
            st.info(informe_texto)
            
            st.markdown("---")
            b64 = base64.b64encode(informe_texto.encode()).decode()
            nombre_archivo = f"Informe_{datetime.date.today()}.txt"
            href = f'<a href="data:file/txt;base64,{b64}" download="{nombre_archivo}"><button style="width: 100%; background-color: #007bff; color: white;">💾 DESCARGAR INFORME</button></a>'
            st.markdown(href, unsafe_allow_html=True)

# --- TAB 3: QA (INTACTO) ---
with tab_qa:
    st.subheader("🔍 Auditoría FE-44")
    archivo_pdf = st.file_uploader("Subir PDF de reporte", type=["pdf"])
    if archivo_pdf and st.button("Auditar Reporte"):
        res_qa = st.session_state['motor'].analizar_pdf_qa(archivo_pdf.read(), "Valida formato FE-44")
        st.success(res_qa)