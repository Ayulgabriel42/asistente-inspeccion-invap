import streamlit as st
import pandas as pd
import numpy as np
import datetime
import base64
import os
from google.cloud import storage
from google.oauth2 import service_account
from engine import InspeccionEngine

# 1. CONFIGURACIÓN Y CREDENCIALES
st.set_page_config(page_title="INVAP - Ecosistema de IA", page_icon="⚙️", layout="wide")

creds = None
project_id = None
if "gcp_service_account" in st.secrets:
    info = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(info)
    project_id = info.get("project_id")
elif os.path.exists("google-credentials.json"):
    creds = service_account.Credentials.from_service_account_file("google-credentials.json")

if 'motor' not in st.session_state:
    # Agregamos project_id para que no falle la conexión al bucket
    st.session_state['motor'] = InspeccionEngine(api_key=st.secrets["GEMINI_API_KEY"], creds=creds, project_id=project_id)

if 'lista_normas' not in st.session_state:
    try:
        client = storage.Client(credentials=creds, project=project_id)
        blobs = client.list_blobs("invap-asistente-normas")
        st.session_state['lista_normas'] = [blob.name for blob in blobs if blob.name.lower().endswith('.pdf')]
    except: st.session_state['lista_normas'] = []

# 2. CABECERA
col_l, col_t = st.columns([1, 5])
with col_l: st.image("https://www.invap.com.ar/wp-content/uploads/2022/04/Logo-INVAP-Blanco.png", width=100)
with col_t: st.title("Sistema Inteligente de Gestión de Integridad")

# RESTAURADAS TUS TABS ORIGINALES
tab_dash, tab_inspeccion, tab_qa = st.tabs(["📊 Dashboard", "🚀 Asistente de Inspección", "🔍 Agente QA FE-44"])

# --- TAB 1: DASHBOARD ---
with tab_dash:
    st.subheader("Estado Global de Activos")
    m1, m2, m3 = st.columns(3)
    m1.metric("Inspecciones Totales", "1,242", "+12%")
    m2.metric("Alertas Críticas", "14", "⚠️")
    m3.metric("Efectividad IA", "99.1%", "🎯")
    st.area_chart(pd.DataFrame(np.random.randn(20, 3), columns=['Mantenimiento', 'Corrosión', 'Soldadura']))

# --- TAB 2: ASISTENTE ---
with tab_inspeccion:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("📝 Registro de Hallazgo")
        audio = st.audio_input("Dictar Hallazgo")
        if audio and 'audio_procesado' not in st.session_state:
            st.session_state['input_hallazgo_usuario'] = st.session_state['motor'].transcribir_audio(audio.read(), audio.type)
            st.session_state['audio_procesado'] = True
        
        hallazgo = st.text_area("Descripción técnica:", value=st.session_state.get('input_hallazgo_usuario', ""), height=150)
        st.write("---")
        foto_c = st.camera_input("Capturar Evidencia (Cámara)")
        foto_a = st.file_uploader("O cargar imagen", type=["jpg", "png", "jpeg"])
        foto_final = foto_c if foto_c else foto_a
        
        if st.button("🚀 GENERAR INFORME TÉCNICO"):
            if not hallazgo and not foto_final:
                st.warning("⚠️ Proporcione descripción o imagen.")
            else:
                with st.spinner("IA identificando norma y procesando..."):
                    img_data = foto_final.read() if foto_final else None
                    img_mime = foto_final.type if foto_final else None
                    norma = st.session_state['motor'].clasificar_norma_ia(hallazgo, st.session_state['lista_normas'], img_data, img_mime)
                    res, ref = st.session_state['motor'].consultar_normativa_rag(norma, hallazgo, img_data, img_mime)
                    st.session_state['ultimo_informe'] = f"**NORMA DETECTADA:** {ref}\n\n{res}"

    with c2:
        st.subheader("📋 Previsualización y Refinamiento")
        if st.session_state.get('ultimo_informe'):
            st.info(st.session_state['ultimo_informe'])
            st.write("---")
            if feedback := st.chat_input("💬 Corregir informe..."):
                with st.spinner("Actualizando..."):
                    st.session_state['ultimo_informe'] = st.session_state['motor'].refinar_informe(st.session_state['ultimo_informe'], feedback)
                    st.rerun()

            b64 = base64.b64encode(st.session_state['ultimo_informe'].encode()).decode()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            href = f'<a href="data:file/txt;base64,{b64}" download="Informe_INVAP_{timestamp}.txt"><button style="width: 100%; height: 50px; background-color: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">💾 DESCARGAR INFORME</button></a>'
            st.markdown(href, unsafe_allow_html=True)
        else:
            st.info("El informe aparecerá aquí luego de procesar el hallazgo.")

# --- TAB 3: QA AUDITORÍA ---
with tab_qa:
    st.subheader("🔍 Agente de Auditoría QA (Formato FE-44)")
    st.write("Cargue un informe en PDF para validar cumplimiento técnico.")
    pdf_qa = st.file_uploader("Subir Reporte PDF", type=["pdf"])
    if pdf_qa and st.button("Auditar Reporte"):
        with st.spinner("Analizando calidad..."):
            res_qa = st.session_state['motor'].analizar_pdf_qa(pdf_qa.read(), "Valida formato FE-44 y consistencia.")
            st.success("Auditoría Completada")
            st.markdown(res_qa)

st.divider()
st.caption(f"© {datetime.date.today().year} INVAP Ingeniería S.A. | Gabriel")