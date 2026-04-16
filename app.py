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

# --- NUEVA FUNCIÓN DE BARRIDO ---
def limpiar_datos():
    for key in ['input_hallazgo_usuario', 'ultimo_informe', 'audio_procesado', 'norma_actual']:
        if key in st.session_state:
            st.session_state[key] = "" if isinstance(st.session_state[key], str) else None
    st.rerun()

creds = None
project_id = None
if "gcp_service_account" in st.secrets:
    info = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(info)
    project_id = info.get("project_id")
elif os.path.exists("google-credentials.json"):
    creds = service_account.Credentials.from_service_account_file("google-credentials.json")

if 'motor' not in st.session_state:
    st.session_state['motor'] = InspeccionEngine(api_key=st.secrets["GEMINI_API_KEY"], creds=creds, project_id=project_id)

if 'lista_normas' not in st.session_state:
    try:
        client = storage.Client(credentials=creds, project=project_id)
        blobs = client.list_blobs("invap-asistente-normas")
        st.session_state['lista_normas'] = [blob.name for blob in blobs if blob.name.lower().endswith('.pdf')]
    except: st.session_state['lista_normas'] = []

# 2. CABECERA
col_l, col_t, col_btn = st.columns([1, 4, 1])
with col_l: st.image("https://www.invap.com.ar/wp-content/uploads/2022/04/Logo-INVAP-Blanco.png", width=100)
with col_t: st.title("Sistema Inteligente de Gestión de Integridad")
with col_btn: 
    # Botón de barrido solicitado
    if st.button("🔄 NUEVA INSPECCIÓN", use_container_width=True):
        limpiar_datos()

# TABS ORIGINALES
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
        
        # Soporte para múltiples imágenes según lo hablado
        foto_c = st.camera_input("Capturar Evidencia")
        foto_a = st.file_uploader("O cargar imagen", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        
        # Consolidación de imágenes para el motor
        lista_imgs_motor = []
        if foto_c: lista_imgs_motor.append((foto_c.read(), foto_c.type))
        if foto_a:
            for f in foto_a: lista_imgs_motor.append((f.read(), f.type))
        
        if st.button("🚀 GENERAR INFORME TÉCNICO"):
            if not hallazgo and not lista_imgs_motor:
                st.warning("⚠️ Proporcione descripción o imagen.")
            else:
                with st.spinner("IA identificando norma y procesando..."):
                    # Llamada actualizada al motor con lista de imágenes
                    norma = st.session_state['motor'].clasificar_norma_ia(hallazgo, st.session_state['lista_normas'], lista_imgs_motor)
                    res, ref = st.session_state['motor'].consultar_normativa_rag(norma, hallazgo, lista_imgs_motor)
                    st.session_state['ultimo_informe'] = res
                    st.session_state['norma_actual'] = ref

    with c2:
        st.subheader("📋 Previsualización y Refinamiento")
        if st.session_state.get('ultimo_informe'):
            st.info(f"**NORMA DETECTADA:** {st.session_state.get('norma_actual')}")
            st.markdown(st.session_state['ultimo_informe'])
            st.write("---")
            
            if feedback := st.chat_input("💬 Corregir informe..."):
                with st.spinner("Actualizando..."):
                    st.session_state['ultimo_informe'] = st.session_state['motor'].refinar_informe(st.session_state['ultimo_informe'], feedback)
                    st.rerun()

            # Botones de Acción
            col_down, col_mem = st.columns(2)
            with col_down:
                b64 = base64.b64encode(st.session_state['ultimo_informe'].encode()).decode()
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                href = f'<a href="data:file/txt;base64,{b64}" download="Informe_INVAP_{timestamp}.txt"><button style="width: 100%; height: 50px; background-color: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; font-weight: bold;">💾 DESCARGAR INFORME</button></a>'
                st.markdown(href, unsafe_allow_html=True)
            
            with col_mem:
                if st.button("🧠 GUARDAR EN MEMORIA TÉCNICA", use_container_width=True):
                    st.session_state['motor'].guardar_leccion_aprendida(hallazgo, st.session_state['ultimo_informe'], st.session_state['norma_actual'])
                    st.success("Conocimiento guardado.")
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