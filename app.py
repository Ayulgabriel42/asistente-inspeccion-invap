import streamlit as st

# --- 1. CONFIGURACIÓN DE TEMA (FORZAR MODO CLARO) ---
st.set_page_config(
    page_title="IA Inspección - INVAP", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)

# --- 2. ESTILOS CSS AVANZADOS (LIMPIEZA TOTAL) ---
st.markdown("""
    <style>
    /* Forzar fondo blanco y eliminar degradados oscuros */
    .stApp {
        background-color: #FFFFFF !important;
    }
    
    /* Barra lateral en gris muy claro profesional */
    [data-testid="stSidebar"] {
        background-color: #F8F9FA !important;
        border-right: 1px solid #E0E0E0;
    }

    /* Títulos en Verde INVAP */
    h1, h2, h3, .stMarkdown p {
        color: #007D43 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* Botones Profesionales */
    .stButton>button {
        background-color: #007D43 !important;
        color: white !important;
        border-radius: 4px !important;
        border: none !important;
        padding: 0.5rem 1rem !important;
        font-weight: bold !important;
        width: 100%;
    }

    /* Inputs y Selectors */
    .stSelectbox, .stTextArea, .stTextInput {
        background-color: #FFFFFF !important;
        border-radius: 4px !important;
    }

    /* Tabs (Solapas) Estilo Corporativo */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #FFFFFF;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #F1F3F4;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 20px;
        color: #5F6368;
    }
    .stTabs [aria-selected="true"] {
        background-color: #007D43 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_True=True)

# --- 3. BARRA LATERAL ---
with st.sidebar:
    # Logo mediante texto estilizado (más seguro que URL externa que falla)
    st.markdown(f"<h1 style='text-align: center; color: #007D43; font-size: 28px;'>INVAP</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; margin-top: -20px;'><b>INGENIERÍA S.A.</b></p>", unsafe_allow_html=True)
    st.markdown("---")
    st.write("**Sistema de Gestión Integrado**")
    st.caption("ISO 9001 | 14001 | 45001 [cite: 37]")
    st.markdown("---")
    st.info("Usuario: Inspector de Campo")

# --- 4. CUERPO PRINCIPAL ---
st.title("🛡️ Asistente Inteligente de Inspección")
st.write("Plataforma de IA para la integridad técnica de equipos[cite: 7, 15].")

# Tabs Independientes (Respetando la arquitectura original del proyecto)
tab1, tab2 = st.tabs(["🚀 Agente de Inspección (Campo)", "🔍 Agente de QA (Ingeniería)"])

with tab1:
    st.subheader("Registro de Integridad Técnica (IIT)")
    
    # Sistemas de Torre (Tu info técnica)
    sistemas = ["Elevación", "Potencia", "Rotación", "Circulación", "Control de Pozo", "Seguridad", "API RP 4G (Cat III)"]
    sistema_sel = st.selectbox("Seleccione el sistema a inspeccionar[cite: 16, 22]:", sistemas)
    
    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        if st.button("🎙️ INICIAR DICTADO POR VOZ"):
            st.toast(f"Micrófono activo para: {sistema_sel}") # Feedback visual rápido
            
    obs_campo = st.text_area(f"Notas para Sistema de {sistema_sel}[cite: 35]:", 
                            placeholder="Describa hallazgos, desvíos o estado general...",
                            height=150)
    
    st.markdown("---")
    st.subheader("Consultor Normativo")
    query = st.text_input("Pregunte a la IA sobre normas específicas (ej. API RP 4G)[cite: 36]:")

with tab2:
    st.subheader("Auditoría de Calidad y Coherencia")
    st.write("Agente independiente para la corrección de informes de ingeniería[cite: 10, 18].")
    
    uploaded_file = st.file_uploader("Cargar borrador de informe (PDF) para validación ISO[cite: 37]:", type="pdf")
    
    if uploaded_file:
        st.success("Documento cargado. El Agente de QA está analizando la completitud[cite: 18].")
        st.text_area("Sugerencias de corrección del Agente de QA:", height=200)
    
    if st.button("✅ APROBAR Y EMITIR INFORME FINAL"):
        st.balloons()
