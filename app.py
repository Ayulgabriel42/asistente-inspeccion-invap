import streamlit as st

st.set_page_config(page_title="Sistema IA - INVAP", layout="wide")

st.title("🛡️ Ecosistema de IA - INVAP Ingeniería S.A.")

# Creamos dos solapas independientes (Agentes separados)
tab1, tab2 = st.tabs(["🚀 Agente de Inspección (Campo)", "🔍 Agente de QA (Ingeniería)"])

# --- AGENTE 1: ASISTENTE DE CAMPO ---
with tab1:
    st.header("Asistente Inteligente de Campo")
    st.info("Objetivo: Agilizar el registro y consulta de normas en tiempo real.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎙️ Activar Comando de Voz"):
            st.write("Escuchando... (Integración con Speech-to-Text)")
    
    obs_campo = st.text_area("Registro de Observaciones:", 
                            help="Aquí se vuelca el dictado de voz a texto.")
    
    query_norma = st.text_input("Consultar Norma Técnica (RAG):")
    if query_norma:
        st.write(f"Buscando en manuales técnicos: {query_norma}")

# --- AGENTE 2: AGENTE DE CORRECCIÓN (QA) ---
with tab2:
    st.header("Agente de Revisión y QA")
    st.info("Objetivo: Corregir informes, verificar coherencia y cumplimiento normativo.")
    
    archivo_informe = st.file_uploader("Subir borrador de informe (PDF/Docx)", type=["pdf", "docx"])
    
    if archivo_informe:
        st.warning("Agente de QA analizando consistencia técnica...")
        # Aquí irá la lógica de corrección que mencionaste para los ingenieros
    
    st.text_area("Sugerencias de Corrección / Feedback de IA:")
    if st.button("✅ Aprobar para Emisión"):
        st.success("Informe validado técnicamente.")
