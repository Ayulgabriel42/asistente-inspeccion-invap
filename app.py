import streamlit as st
from PIL import Image
import requests
from io import BytesIO

# --- CONFIGURACIÓN DE PÁGINA Y BRANDING ---
st.set_page_config(page_title="IA Inspección - INVAP", layout="wide", page_icon="🛡️")

# Inyección de CSS para personalizar colores (Verde y Blanco INVAP)
st.markdown("""
    <style>
    /* Fondo principal blanco */
    .stApp {
        background-color: #FFFFFF;
    }
    
    /* Color de texto principal (Gris oscuro para legibilidad) */
    html, body, [class*="css"]  {
        color: #333333;
    }

    /* Personalización de Botones (Verde INVAP) */
    .stButton>button {
        background-color: #007D43; /* Verde Principal INVAP */
        color: white;
        border-radius: 5px;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #005A32; /* Verde más oscuro al pasar el mouse */
        color: white;
    }

    /* Personalización de Títulos y Subtítulos (Verde INVAP) */
    h1, h2, h3 {
        color: #007D43 !important;
    }

    /* Estilo para las Tabs (Solapas) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #F0F2F6;
        border-radius: 5px 5px 0px 0px;
        color: #333333;
    }
    .stTabs [aria-selected="true"] {
        background-color: #007D43;
        color: white !important;
    }
    
    /* Info boxes en gris claro */
    .stAlert {
        background-color: #F8F9FA;
        color: #333333;
        border: 1px solid #007D43;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BARRA LATERAL (SIDEBAR) CON LOGO ---
with st.sidebar:
    # Intentamos cargar el logo desde la web oficial para garantizar fidelidad
    try:
        response = requests.get("https://www.invapingenieria.com.ar/images/logo.png")
        img = Image.open(BytesIO(response.content))
        st.image(img, use_container_width=True)
    except:
        st.warning("No se pudo cargar el logo oficial. Usando texto.")
        st.write("**INVAP INGENIERÍA S.A.**")
    
    st.markdown("---")
    st.markdown("**Sistema de Gestión Integrado**")
    st.write("ISO 9001 | 14001 | 45001")

# --- CUERPO PRINCIPAL ---
st.title("🛡️ Ecosistema de Inteligencia Artificial")
st.write("Herramientas digitales avanzadas para operaciones y QA.")

# Creación de solapas independientes (Respetando arquitectura original)
tab1, tab2 = st.tabs(["🚀 Agente de Inspección (Campo)", "🔍 Agente de QA (Ingeniería)"])

# --- AGENTE 1: ASISTENTE DE CAMPO ---
with tab1:
    st.header("Asistente de Integridad Técnica (IIT)")
    st.info("Agilice el registro en yacimiento y consulte normativa API/ISO mediante voz.")
    
    # Categorías técnicas de INVAP
    sistema = st.selectbox("Sistema a Inspeccionar:", 
                         ["Elevación", "Potencia", "Rotación", "Circulación", 
                          "Control de Pozo", "Seguridad", "API RP 4G (Cat III)"])
    
    col_v1, col_v2 = st.columns([1, 2])
    with col_v1:
        # Requerimiento de diseño: Manos libres
        if st.button("🎙️ Iniciar Dictado de Voz"):
            st.info(f"Escuchando observaciones para {sistema}...")
    
    # Espacio para el Speech-to-Text
    obs_campo = st.text_area("Registro de Observaciones:", 
                            placeholder=f"Describa desvíos en el sistema de {sistema}...")
    
    # Motor RAG para normas
    query_norma = st.text_input("Consultar Norma Técnica Específica:")
    if query_norma:
        st.write(f"Buscando en manuales técnicos para: **{query_norma}**")

# --- AGENTE 2: AGENTE DE QA E INGENIERÍA ---
with tab2:
    st.header("Agente de Revisión y Control de Calidad")
    st.info("Validación de informes, corrección técnica y coherencia normativa (ISO).")
    
    # Auditoría documental
    archivo_informe = st.file_uploader("Subir borrador de informe para corrección (PDF)", type=["pdf"])
    
    if archivo_informe:
        st.warning("Ejecutando análisis de QA automatizado...")
        
        # Simulación de la revisión de coherencia
        col_qa1, col_qa2 = st.columns(2)
        with col_qa1:
            st.subheader("Borrador Original")
            st.write("Contenido del informe detectado...")
        with col_qa2:
            st.subheader("Sugerencias de Corrección")
            st.error("⚠️ Falta justificación técnica para el desvío en el Mástil.")
    
    st.text_area("Feedback final del Ingeniero:")
    if st.button("✅ Aprobar Informe para Emisión"):
        st.success("Informe validado técnicamente y listo para firma.")
    
    st.text_area("Espacio para feedback y correcciones manuales del Ingeniero:")
    if st.button("✅ Aprobar Informe"):
        st.success("Informe validado técnicamente y listo para su emisión final.")
