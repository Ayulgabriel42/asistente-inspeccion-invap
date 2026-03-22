import streamlit as st
from engine import InspeccionEngine
import datetime
import pandas as pd
import numpy as np

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="INVAP - Ecosistema de IA de Integridad",
    page_icon="⚙️",
    layout="wide"
)

# Estilos visuales para que parezca una herramienta oficial de INVAP
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    h1 { color: #003366; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stButton>button { background-color: #008000; color: white; border-radius: 5px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INICIALIZACIÓN DEL MOTOR (Asegurate que engine.py exista) ---
CLAVE_IA = "AIzaSyDHW2_iO36Mb77uICBVlDxDFgZ5N2hD1HA"
motor = InspeccionEngine(api_key=CLAVE_IA)

# --- 3. CABECERA ---
col_logo, col_tit = st.columns([1, 5])
with col_logo:
    st.image("https://www.invap.com.ar/wp-content/uploads/2022/04/Logo-INVAP-Blanco.png", width=120)
with col_tit:
    st.title("Sistema Inteligente de Gestión de Integridad")
    st.write("Unidad de Inspección Estructural | Cumplimiento API RP 4G")

st.divider()

# --- 4. NAVEGACIÓN POR SOLAPAS (TABS) ---
tab_dash, tab_inspeccion, tab_qa = st.tabs([
    "📊 Dashboard de Estado", 
    "🚀 Asistente de Inspección", 
    "🔍 Agente QA y Revisión"
])

# =========================================================
# SOLAPA 1: DASHBOARD (Resumen Ejecutivo)
# =========================================================
with tab_dash:
    st.subheader("Panel de Control de Activos")
    
    # Métricas principales
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Inspecciones Totales", "142", "+5 esta semana")
    m2.metric("Críticos (Cat IV)", "12", "⚠️ Acción Urgente", delta_color="inverse")
    m3.metric("En Reparación", "28", "-2")
    m4.metric("Conformidad Mensual", "94%", "Objetivo: 95%")
    
    st.divider()
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.write("📈 **Tendencia de Hallazgos (2026)**")
        chart_data = pd.DataFrame(
            np.random.randn(20, 3),
            columns=['Mástiles', 'Subestructuras', 'Bombas']
        )
        st.area_chart(chart_data)
        
    with col_g2:
        st.write("📋 **Últimos Informes Generados**")
        data_table = pd.DataFrame({
            "Fecha": ["20/03/2026", "19/03/2026", "18/03/2026"],
            "Activo": ["Rig 104 - Mástil", "Rig 201 - Subestructura", "Bomba Lodo #4"],
            "Resultado": ["Crítico", "Menor", "Conforme"],
            "Inspector": ["G. Ayul", "J. Doe", "A. Smith"]
        })
        st.table(data_table)

# =========================================================
# SOLAPA 2: ASISTENTE DE INSPECCIÓN (Generador)
# =========================================================
with tab_inspeccion:
    st.subheader("🚀 Generador de Informes Técnicos")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.info("Cargue los datos del hallazgo observado en campo.")
        sistema = st.selectbox("Sistema:", ["Mástil/Subestructura", "Izaje", "Bombas", "Recipientes"])
        ref = st.text_input("Ubicación exacta:", "Ej: Tramo C, Lado A")
        hallazgo = st.text_area("Descripción del hallazgo:", height=200, placeholder="Ej: Se observa fisura de...")
        
        if st.button("Generar Informe con IA"):
            if not hallazgo:
                st.error("Por favor, ingrese el hallazgo.")
            else:
                with st.spinner("Gemini 2.5 Flash analizando..."):
                    st.session_state['ultimo_informe'] = motor.procesar_hallazgo(sistema, hallazgo)
                    st.success("¡Informe generado con éxito!")

    with c2:
        if 'ultimo_informe' in st.session_state:
            st.markdown(st.session_state['ultimo_informe'])
            st.download_button("Descargar Informe (TXT)", st.session_state['ultimo_informe'], file_name="informe_invap.txt")
        else:
            st.write("Complete el formulario de la izquierda para ver el análisis aquí.")

# =========================================================
# SOLAPA 3: AGENTE QA Y REVISIÓN (Auditoría)
# =========================================================
with tab_qa:
    st.subheader("🔍 Agente de Revisión y QA de Informes")
    st.write("Pegue un informe redactado para que la IA verifique su consistencia técnica y normativa.")
    
    reporte_input = st.text_area("Texto del informe a auditar:", height=300)
    
    if st.button("Auditar Informe"):
        if reporte_input:
            with st.spinner("El Agente QA está revisando el documento..."):
                prompt_qa = f"""
                Actúa como un Auditor Senior de Calidad en INVAP. 
                Revisa el siguiente reporte de inspección:
                
                {reporte_input}
                
                Indica:
                1. ¿Se menciona la normativa correcta (API RP 4G u otras)?
                2. ¿La clasificación del daño es coherente con la descripción?
                3. Sugiere mejoras técnicas y de redacción.
                4. Da un veredicto: APROBADO, OBSERVADO o RECHAZADO.
                """
                
                # Llamada directa a la IA
                revision = motor.client.models.generate_content(
                    model=motor.model_id,
                    contents=prompt_qa
                )
                
                st.subheader("📋 Resultados de la Auditoría")
                st.warning("Análisis de Calidad Finalizado")
                st.write(revision.text)
        else:
            st.error("Por favor, pegue un informe para auditar.")

st.divider()
st.caption("© 2026 INVAP Ingeniería S.A. - Desarrollado con Gemini 2.5 Flash Engine")