import streamlit as st

# Configuración de pantalla ancha para visualización de informes y datos técnicos
st.set_page_config(page_title="IA Inspección - INVAP", layout="wide")

st.title("🛡️ Sistema de Inteligencia Artificial - INVAP Ingeniería S.A.")

# Creación de solapas independientes para garantizar que no haya cruce de información
tab1, tab2 = st.tabs(["🚀 Agente de Campo (Inspectores)", "🔍 Agente de QA (Ingenieros)"])

# --- AGENTE 1: ASISTENTE DE CAMPO ---
with tab1:
    st.header("Asistente de Integridad Técnica (IIT)")
    st.info("Herramienta para agilizar el registro en campo y consulta de normativa técnica.")
    
    # Categorías técnicas extraídas de los requerimientos de INVAP
    sistema = st.selectbox("Sistema a Inspeccionar:", 
                         ["Elevación", "Potencia", "Rotación", "Circulación", 
                          "Control de Pozo", "Seguridad", "API RP 4G (Categoría III)"])
    
    col_v1, col_v2 = st.columns([1, 2])
    with col_v1:
        # Simulación de comando de voz para manos libres
        if st.button("🎙️ Iniciar Dictado de Voz"):
            st.info(f"Escuchando observaciones para el Sistema de {sistema}...")
    
    # Espacio para el texto procesado por Speech-to-Text
    obs_campo = st.text_area("Registro de Observaciones:", 
                            placeholder="Describa el estado del equipo o desvíos detectados...")
    
    # Motor de consulta RAG para normas API e ISO
    query_norma = st.text_input("Consultar Norma Técnica Específica:")
    if query_norma:
        st.write(f"Buscando en manuales técnicos y normas aplicables para: **{query_norma}**")

# --- AGENTE 2: AGENTE DE QA E INGENIERÍA ---
with tab2:
    st.header("Agente de Revisión y Control de Calidad")
    st.info("Validación de informes, corrección técnica y verificación de coherencia normativa.")
    
    # Carga de archivos para el proceso de auditoría documental
    archivo_informe = st.file_uploader("Subir informe para revisión (PDF)", type=["pdf"])
    
    if archivo_informe:
        st.warning("Ejecutando análisis de QA sobre el documento...")
        
        # Simulación de la revisión de coherencia y completitud
        col_qa1, col_qa2 = st.columns(2)
        with col_qa1:
            st.subheader("Análisis de Coherencia")
            st.write("Verificando cumplimiento de normas ISO 9001, 45001 y 14001...")
        with col_qa2:
            st.subheader("Sugerencias de Corrección")
            st.error("⚠️ El informe carece de la justificación técnica necesaria para el desvío en el Mástil.")
    
    st.text_area("Espacio para feedback y correcciones manuales del Ingeniero:")
    if st.button("✅ Aprobar Informe"):
        st.success("Informe validado técnicamente y listo para su emisión final.")
