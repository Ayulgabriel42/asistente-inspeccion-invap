import streamlit as st
import pandas as pd
import numpy as np
import datetime
import base64
import os
import json
from google.cloud import storage
from google.oauth2 import service_account
from engine import InspeccionEngine

# =========================================================
# 1. CONFIGURACIÓN Y GESTIÓN DE CREDENCIALES
# =========================================================
st.set_page_config(page_title="INVAP - Ecosistema de IA", page_icon="⚙️", layout="wide")

# Gestión de credenciales para Google Cloud Storage
creds = None
if "gcp_service_account" in st.secrets:
    info = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(info)
elif os.path.exists("google-credentials.json"):
    creds = service_account.Credentials.from_service_account_file("google-credentials.json")

# Inicialización del Motor de IA
if 'motor' not in st.session_state:
    if "GEMINI_API_KEY" in st.secrets:
        st.session_state['motor'] = InspeccionEngine(
            api_key=st.secrets["GEMINI_API_KEY"],
            creds=creds
        )
    else:
        st.error("⚠️ Falta la GEMINI_API_KEY en los Secrets de Streamlit.")

# Carga inicial de la biblioteca de normas desde el Bucket
if 'lista_normas' not in st.session_state:
    try:
        client = storage.Client(credentials=creds)
        blobs = client.list_blobs("invap-asistente-normas")
        st.session_state['lista_normas'] = [blob.name for blob in blobs if blob.name.lower().endswith('.pdf')]
    except Exception as e:
        st.session_state['lista_normas'] = []

# =========================================================
# 2. CABECERA (Logo y Título)
# =========================================================
col_l, col_t = st.columns([1, 5])
with col_l: 
    st.image("https://www.invap.com.ar/wp-content/uploads/2022/04/Logo-INVAP-Blanco.png", width=100)
with col_t: 
    st.title("Sistema Inteligente de Gestión de Integridad")

tab_dash, tab_inspeccion, tab_qa = st.tabs(["📊 Dashboard", "🚀 Asistente de Inspección", "🔍 Agente QA FE-44"])

# --- TAB 1: DASHBOARD DE GESTIÓN ---
with tab_dash:
    st.subheader("Estado Global de Activos y Criticidad")
    m1, m2, m3 = st.columns(3)
    m1.metric("Inspecciones Totales", "1,242", "+12% esta semana")
    m2.metric("Alertas Críticas", "14", "⚠️ Requiere Acción")
    m3.metric("Efectividad IA", "98.4%", "🎯")
    
    st.write("---")
    st.markdown("### Tendencia de Hallazgos")
    # Gráfico de ejemplo para el reporte de gerencia
    chart_data = pd.DataFrame(
        np.random.randn(20, 3),
        columns=['Mantenimiento', 'Corrosión', 'Soldadura']
    )
    st.area_chart(chart_data)

# --- TAB 2: ASISTENTE DE INSPECCIÓN MULTIMODAL ---
with tab_inspeccion:
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("📝 Registro de Campo")
        sistema_sel = st.selectbox("Sistema a Inspeccionar:", 
                                 ["Mástil/Subestructura", "Piping / Tuberías", "Recipientes a Presión", 
                                  "Soldadura y Estructuras", "Izaje y Puentes Grúa", "Bombas y Equipos"])
        
        # Entrada por VOZ
        audio = st.audio_input("Dictar Hallazgo (Voz a Texto)")
        if audio and 'audio_procesado' not in st.session_state:
            with st.spinner("IA Transcribiendo audio técnico..."):
                st.session_state['input_hallazgo_usuario'] = st.session_state['motor'].transcribir_audio(audio.read(), audio.type)
                st.session_state['audio_procesado'] = True
        
        # Entrada por TEXTO
        hallazgo = st.text_area("Descripción detallada del hallazgo:", 
                               value=st.session_state.get('input_hallazgo_usuario', ""), 
                               height=150)
        
        st.write("---")
        st.write("**Evidencia Visual:**")
        foto_c = st.camera_input("Capturar Evidencia")
        foto_a = st.file_uploader("O cargar archivo de imagen", type=["jpg", "png", "jpeg"])
        foto_final = foto_c if foto_c else foto_a
        
        # PROCESAMIENTO MULTIMODAL
        if st.button("🚀 GENERAR INFORME TÉCNICO"):
            if not hallazgo and not foto_final:
                st.warning("⚠️ Debe proporcionar una descripción o una imagen para el análisis.")
            elif not st.session_state.get('lista_normas'):
                st.error("❌ Error: No se pudo acceder a la biblioteca de normas en el Bucket.")
            else:
                with st.spinner("Cruzando datos: Norma + Texto + Imagen..."):
                    # 1. IA decide qué norma abrir
                    input_clasificacion = hallazgo if hallazgo else f"Inspección de {sistema_sel}"
                    norma_elegida = st.session_state['motor'].clasificar_norma_ia(input_clasificacion, st.session_state['lista_normas'])
                    
                    # 2. Captura de imagen
                    img_bytes = foto_final.read() if foto_final else None
                    img_mime = foto_final.type if foto_final else None
                    
                    # 3. Análisis RAG Multimodal
                    res, norma_ref = st.session_state['motor'].consultar_normativa_rag(
                        norma_path=norma_elegida,
                        hallazgo=hallazgo,
                        imagen_bytes=img_bytes,
                        mime_type=img_mime
                    )
                    
                    st.session_state['ultimo_informe'] = f"**NORMATIVA APLICADA:** {norma_ref}\n\n{res}"

    with c2:
        st.subheader("📋 Previsualización y Refinamiento")
        
        if st.session_state.get('ultimo_informe'):
            # Informe generado en pantalla
            st.info(st.session_state['ultimo_informe'])
            
            # BLOQUE INTERACTIVO DE CHAT
            st.write("---")
            st.markdown("💬 **Chat con el Asistente:** (Refine el informe o corrija datos)")
            
            if prompt_chat := st.chat_input("Ej: 'Cambia la fecha de inspección a hoy' o 'Agrega que el material es ASTM A36'"):
                with st.spinner("Refinando informe técnico..."):
                    nuevo_informe = st.session_state['motor'].refinar_informe(st.session_state['ultimo_informe'], prompt_chat)
                    st.session_state['ultimo_informe'] = nuevo_informe
                    st.rerun()

            # BOTÓN DE DESCARGA
            st.markdown("---")
            b64 = base64.b64encode(st.session_state['ultimo_informe'].encode()).decode()
            st_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            nombre_archivo = f"Informe_INVAP_{st_timestamp}.txt"
            href = f'<a href="data:file/txt;base64,{b64}" download="{nombre_archivo}"><button style="width: 100%; height: 50px; background-color: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">💾 DESCARGAR INFORME TÉCNICO FINAL</button></a>'
            st.markdown(href, unsafe_allow_html=True)
        else:
            st.info("El informe técnico se previsualizará en este sector una vez procesado el hallazgo.")

# --- TAB 3: AUDITORÍA QA FE-44 ---
with tab_qa:
    st.subheader("🔍 Agente de Auditoría de Reportes (QA)")
    st.write("Cargue un informe final en PDF para validar el cumplimiento del formato FE-44 y la consistencia técnica.")
    
    archivo_pdf = st.file_uploader("Cargar PDF de reporte", type=["pdf"])
    if archivo_pdf and st.button("Auditar Reporte"):
        with st.spinner("Analizando cumplimiento normativo y de calidad..."):
            res_qa = st.session_state['motor'].analizar_pdf_qa(archivo_pdf.read(), "Valide el cumplimiento del formato FE-44 y detecte inconsistencias técnicas.")
            st.success("Auditoría Completada")
            st.markdown(res_qa)

# --- PIE DE PÁGINA ---
st.divider()
st.caption(f"© {datetime.date.today().year} INVAP Ingeniería S.A. | Desarrollado por Gabriel - Universidad Siglo 21")