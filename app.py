import streamlit as st

# 1. Configuración de página
st.set_page_config(
    page_title="IA Inspección - INVAP", 
    layout="wide", 
    page_icon="🛡️"
)

# 2. Estilos corregidos y optimizados (Blanco y Verde INVAP)
st.markdown("""
    <style>
    /* Forzar fondo blanco en toda la app */
    .stApp {
        background-color: #FFFFFF !important;
    }
    
    /* Títulos y textos en Verde INVAP */
    h1, h2, h3, p, span, label {
        color: #007D43 !important;
        font-family: 'Arial', sans-serif !important;
    }

    /* Botones profesionales */
    .stButton>button {
        background-color: #007D43 !important;
        color: white !important;
        border-radius: 4px !important;
        border: none !important;
        font-weight: bold !important;
        width: 100%;
        height: 3em;
    }

    /* Tabs (Solapas) corporativas */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #FFFFFF;
        border-bottom: 2px solid #007D43;
    }
    .stTabs [data-baseweb="tab"] {
        color: #333333 !important;
        padding: 10px 30px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #007D43 !important;
        color: white !important;
    }

    /* Quitar el menú oscuro de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 3. Barra Lateral Profesional
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>INVAP</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; margin-top: -20px;'>INGENIERÍA S.A.</p>", unsafe_allow_html=True)
    st.markdown("---")
    st.write("**Ecosistema de IA**")
    st.write("ISO 9001 | 14001 | 45001")

# 4. Cuerpo de la App - Los 2 Agentes Independientes
st.title("Asistente Inteligente de Inspección")

tab1, tab2 = st.tabs(["🚀 Agente de Campo", "🔍 Agente de QA"])

with tab1:
    st.subheader("Inspección de Integridad Técnica")
    
    # Sistemas según el documento técnico [cite: 16]
    sistema = st.selectbox("Seleccione el sistema:", 
                         ["Elevación", "Potencia", "Rotación", "Circulación", 
                          "Control de Pozo", "Seguridad", "API RP 4G (Cat III)"])
    
    if st.button("🎙️ ACTIVAR COMANDO DE VOZ"):
        st.info(f"Escuchando observaciones para: {sistema}")
            
    obs_campo = st.text_area("Notas de inspección:", 
                            placeholder="Describa desvíos o estado del equipo...",
                            height=200)

with tab2:
    st.subheader("Revisión de Informes (QA)")
    st.write("Análisis de coherencia y normativa ISO.")
    
    archivo = st.file_uploader("Cargar borrador (PDF)", type="pdf")
    
    if archivo:
        st.success("Informe cargado correctamente.")
        st.info("Agente de IA analizando cumplimiento normativo...")
    
    st.text_area("Feedback de Ingeniería:")
    if st.button("✅ VALIDAR INFORME FINAL"):
        st.balloons()
