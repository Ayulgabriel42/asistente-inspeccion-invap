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

# Lógica de credenciales híbrida (Secrets para Cloud / JSON para Local)
creds = None
if "gcp_service_account" in st.secrets:
    info = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(info)
elif os.path.exists("google-credentials.json"):
    creds = service_account.Credentials.from_service_account_file("google-credentials.json")

# Inicialización del Motor (Pasamos credenciales al motor)
if 'motor' not in st.session_state:
    if "GEMINI_API_KEY" in st.secrets:
        st.session_state['motor'] = InspeccionEngine(
            api_key=st.secrets["GEMINI_API_KEY"],
            creds=creds
        )
    else:
        st.error("Falta la GEMINI_API_KEY en los Secrets.")

# Cargar lista de normas del bucket al inicio
if 'lista_normas' not in st.session_state:
    try:
        client = storage.Client(credentials=creds)
        blobs = client.list_blobs("invap-asistente-normas")
        st.session_state['lista_normas'] = [blob.name for blob in blobs if blob.name.lower().endswith('.pdf')]
    except Exception as e:
        st.session_state['lista_normas'] = []

# =========================================================
# 2. INTERFAZ VISUAL (TU DISEÑO ORIGINAL)
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

# --- TAB 2: ASISTENTE MULTIMODAL ---
with tab_inspeccion:
    c1, c2 = st.columns([1, 2])
    
    with c1:
        sistema_sel = st.selectbox("Sistema:", ["Mástil/Subestructura", "Piping / Tuberías", "Recipientes a Presión", "Soldadura y Estructuras", "Izaje y Puentes Grúa", "Bombas y Equipos"])
        
        # Entrada de Audio
        audio = st.audio_input("Dictar Hallazgo")
        if audio and 'audio_procesado' not in st.session_state:
            with st.spinner("IA Transcribiendo..."):
                st.session_state['input_hallazgo_usuario'] = st.session_state['motor'].transcribir_audio(audio.read(), audio.type)
                st.session_state['audio_procesado'] = True
        
        # Descripción de texto
        hallazgo = st.text_area("Descripción:", value=st.session_state.get('input_hallazgo_usuario', ""), height=150)
        
        st.write("---")
        st.write("**Evidencia Visual:**")
        foto_c = st.camera_input("Capturar con Cámara")
        foto_a = st.file_uploader("O subir imagen", type=["jpg", "png", "jpeg"])
        foto_final = foto_c if foto_c else foto_a
        
        # BOTÓN GENERADOR MULTIMODAL
        if st.button("🚀 Generar Informe Técnico"):
            if not hallazgo and not foto_final:
                st.warning("⚠️ Agregue una descripción o imagen para analizar.")
            elif not st.session_state.get('lista_normas'):
                st.error("❌ No se detectaron normas en el bucket de INVAP.")
            else:
                with st.spinner("Agente Multimodal cruzando Norma + Texto + Imagen..."):
                    # 1. Clasificar norma (usamos texto o sistema como pista)
                    input_clasificacion = hallazgo if hallazgo else f"Inspección de {sistema_sel}"
                    norma_elegida = st.session_state['motor'].clasificar_norma_ia(input_clasificacion, st.session_state['lista_normas'])
                    
                    # 2. Leer datos de imagen
                    img_bytes = foto_final.read() if foto_final else None
                    img_mime = foto_final.type if foto_final else None
                    
                    # 3. Análisis RAG Multimodal
                    res, norma_ref = st.session_state['motor'].consultar_normativa_rag(
                        norma_path=norma_elegida,
                        hallazgo=hallazgo,
                        imagen_bytes=img_bytes,
                        mime_type=img_mime
                    )
                    
                    st.session_state['ultimo_informe'] = f"**Norma de Referencia:** {norma_ref}\n\n{res}"

    with c2:
        st.subheader("📋 Previsualización y Refinamiento")
        
        if st.session_state.get('ultimo_informe'):
            # Mostramos el informe actual
            informe_actual = st.session_state['ultimo_informe']
            st.info(informe_actual)
            
            # BLOQUE DE CHATBOT DE CORRECCIÓN
            st.write("---")
            st.markdown("💬 **Chat de Corrección:** (Pedí cambios en la fecha, nombres o datos)")
            
            if prompt_chat := st.chat_input("Ej: 'Cambiá la fecha a hoy' o 'El equipo es una bomba centrífuga'"):
                with st.spinner("Actualizando informe técnico..."):
                    nuevo_informe = st.session_state['motor'].refinar_informe(informe_actual, prompt_chat)
                    st.session_state['ultimo_informe'] = nuevo_informe
                    st.rerun()

            # BOTÓN DE DESCARGA
            st.markdown("---")
            b64 = base64.b64encode(st.session_state['ultimo_informe'].encode()).decode()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            nombre_archivo = f"Informe_Inspeccion_{timestamp}.txt"
            href = f'<a href="data:file/txt;base64,{b64}" download="{nombre_archivo}"><button style="width: 100%; height: 50px; background-color: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">💾 DESCARGAR INFORME FINAL</button></a>'
            st.markdown(href, unsafe_allow_html=True)
        else:
            st.light("El informe aparecerá aquí luego de procesar el hallazgo.")

# --- TAB 3: QA ---
with tab_qa:
    st.subheader("🔍 Auditoría FE-44")
    archivo_pdf = st.file_uploader("Subir PDF de reporte para auditoría", type=["pdf"])
    if archivo_pdf and st.button("Auditar Reporte"):
        with st.spinner("Analizando cumplimiento normativo..."):
            res_qa = st.session_state['motor'].analizar_pdf_qa(archivo_pdf.read(), "Valida formato FE-44 y consistencia técnica.")
            st.success(res_qa)

st.divider()
st.caption(f"© {datetime.date.today().year} INVAP Ingeniería S.A. - Usuario: Gabriel")