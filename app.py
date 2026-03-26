import streamlit as st
from engine import InspeccionEngine
import datetime
import pandas as pd
import numpy as np

# --- 1. CONFIGURACIÓN ORIGINAL ---
st.set_page_config(page_title="INVAP - Ecosistema de IA de Integridad", page_icon="⚙️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    h1 { color: #003366; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stButton>button { background-color: #008000; color: white; border-radius: 5px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INICIALIZACIÓN ---
CLAVE_IA = st.secrets["GEMINI_API_KEY"]
if 'motor' not in st.session_state:
    st.session_state['motor'] = InspeccionEngine(api_key=CLAVE_IA)

# --- 3. CABECERA ORIGINAL ---
col_logo, col_tit = st.columns([1, 5])
with col_logo:
    st.image("https://www.invap.com.ar/wp-content/uploads/2022/04/Logo-INVAP-Blanco.png", width=120)
with col_tit:
    st.title("Sistema Inteligente de Gestión de Integridad")
    st.write("Unidad de Inspección Estructural | Cumplimiento API RP 4G")

st.divider()

tab_dash, tab_inspeccion, tab_qa = st.tabs(["📊 Dashboard de Estado", "🚀 Asistente de Inspección", "🔍 Agente QA y Revisión"])

# --- SOLAPA 1: DASHBOARD (TUS DATOS ORIGINALES) ---
with tab_dash:
    st.subheader("Panel de Control de Activos")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Inspecciones Totales", "142", "+5 esta semana")
    m2.metric("Críticos (Cat IV)", "12", "⚠️ Acción Urgente", delta_color="inverse")
    m3.metric("En Reparación", "28", "-2")
    m4.metric("Conformidad Mensual", "94%", "Objetivo: 95%")
    st.divider()
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.write("📈 **Tendencia de Hallazgos (2026)**")
        chart_data = pd.DataFrame(np.random.randn(20, 3), columns=['Mástiles', 'Subestructuras', 'Bombas'])
        st.area_chart(chart_data)
    with col_g2:
        st.write("📋 **Últimos Informes Generados**")
        st.table(pd.DataFrame({
            "Fecha": ["20/03/2026", "19/03/2026", "18/03/2026"],
            "Activo": ["Rig 104 - Mástil", "Rig 201 - Subestructura", "Bomba Lodo #4"],
            "Resultado": ["Crítico", "Menor", "Conforme"],
            "Inspector": ["G. Ayul", "J. Doe", "A. Smith"]
        }))

# --- SOLAPA 2: ASISTENTE (TU LÓGICA ORIGINAL) ---
with tab_inspeccion:
    st.subheader("🚀 Generador de Informes Técnicos")
    c1, c2 = st.columns([1, 2])
    with c1:
        sistema = st.selectbox("Sistema:", ["Mástil/Subestructura", "Izaje", "Bombas", "Recipientes"])
        ref = st.text_input("Ubicación exacta:", "Ej: Tramo C, Lado A")
        audio_data = st.audio_input("Grabe la descripción")
        if audio_data:
            with st.spinner("Transcribiendo..."):
                texto_ia = st.session_state['motor'].transcribir_audio(audio_data.read(), audio_data.type)
                st.session_state['input_hallazgo_usuario'] = texto_ia
        
        hallazgo_final = st.text_area("Descripción del hallazgo:", height=200, key="input_hallazgo_usuario")
        
        if st.button("Generar Informe con IA"):
            with st.spinner("Analizando..."):
                st.session_state['ultimo_informe'] = st.session_state['motor'].procesar_hallazgo(sistema, hallazgo_final)

    with c2:
        if st.session_state.get('ultimo_informe'):
            st.markdown(st.session_state['ultimo_informe'])

# --- SOLAPA 3: QA (CON SUBIDA DE PDF AGREGADA) ---
with tab_qa:
    st.subheader("🔍 Agente de Revisión y QA de Informes")
    
    # Nuevo bloque de subida de PDF
    st.write("### 📂 Cargar Informe para Auditoría")
    archivo_pdf = st.file_uploader("Subir informe en PDF", type=["pdf"])
    
    st.write("--- o pegue el texto debajo ---")
    reporte_input = st.text_area("Texto del informe a auditar:", height=200)
    
    if st.button("Auditar Informe"):
        prompt_qa = """
        Actúa como un Auditor Senior de Calidad en INVAP. Revisa el reporte:
        1. ¿Menciona la normativa correcta? 2. ¿La clasificación es coherente?
        3. Sugiere mejoras y da un veredicto: APROBADO, OBSERVADO o RECHAZADO.
        """
        
        with st.spinner("El Agente QA está revisando..."):
            try:
                if archivo_pdf is not None:
                    # Si hay PDF, usamos la nueva función del engine
                    resultado = st.session_state['motor'].analizar_pdf_qa(archivo_pdf.read(), prompt_qa)
                elif reporte_input:
                    # Si no hay PDF, usamos el texto pegado
                    resultado = st.session_state['motor'].client.models.generate_content(
                        model=st.session_state['motor'].model_id,
                        contents=f"{prompt_qa}\n\nREPORTE:\n{reporte_input}"
                    ).text
                else:
                    st.error("Por favor suba un PDF o pegue el texto.")
                    resultado = None

                if resultado:
                    st.subheader("📋 Resultados de la Auditoría")
                    st.write(resultado)
            except Exception as e:
                st.error(f"Error: {e}")

st.divider()
st.caption("© 2026 INVAP Ingeniería S.A. - Desarrollado con Engine IA")