import os
import base64
import datetime
import streamlit as st
import pandas as pd
import numpy as np

from google.cloud import storage
from google.oauth2 import service_account

from engine import InspeccionEngine


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
st.set_page_config(
    page_title="INVAP - Sistema Inteligente de Integridad",
    page_icon="⚙️",
    layout="wide"
)


# =========================================================
# ESTILOS BÁSICOS
# =========================================================
st.markdown("""
<style>
/* =========================================================
   ESTILO PROFESIONAL INVAP - MODO CAMPO
   Visual más limpio, sobrio y usable en campo.
   No modifica lógica de la app.
   ========================================================= */

:root {
    --invap-green: #007A3D;
    --invap-green-dark: #005E31;
    --invap-green-soft: #E8F4EE;
    --text-main: #0F172A;
    --text-muted: #64748B;
    --border-soft: #D9E2E8;
    --bg-app: #F6F8FA;
    --bg-card: #FFFFFF;
}

/* Fondo general */
.stApp {
    background-color: var(--bg-app) !important;
}

/* Contenedor principal */
.block-container {
    padding-top: 1.4rem !important;
    padding-bottom: 2rem !important;
    max-width: 1180px !important;
}

/* Tipografía base */
html, body, [class*="css"] {
    font-size: 16px !important;
    color: var(--text-main) !important;
}

/* Títulos */
h1 {
    font-size: 2.1rem !important;
    font-weight: 800 !important;
    color: var(--text-main) !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 0.8rem !important;
}

h2 {
    font-size: 1.55rem !important;
    font-weight: 750 !important;
    color: var(--text-main) !important;
}

h3 {
    font-size: 1.25rem !important;
    font-weight: 700 !important;
    color: var(--text-main) !important;
}

.big-section-title {
    font-size: 2rem !important;
    font-weight: 800 !important;
    color: var(--text-main) !important;
    margin-bottom: 1rem !important;
}

/* Texto secundario */
.small-muted,
[data-testid="stCaptionContainer"],
.stCaptionContainer {
    color: var(--text-muted) !important;
    font-size: 0.95rem !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #F0F8F4 0%, #E7F2EC 100%) !important;
    border-right: 1px solid #C9DAD1 !important;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: var(--text-main) !important;
}

section[data-testid="stSidebar"] [role="radiogroup"] label {
    font-size: 0.98rem !important;
    font-weight: 600 !important;
}

/* Labels */
label,
.stTextInput label,
.stTextArea label,
.stSelectbox label,
.stFileUploader label {
    font-size: 0.98rem !important;
    font-weight: 700 !important;
    color: #1E293B !important;
}

/* Inputs */
.stTextInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div,
.stDateInput input,
.stNumberInput input {
    font-size: 1rem !important;
    border-radius: 10px !important;
    border: 1.5px solid #CBD5E1 !important;
    background-color: #FFFFFF !important;
    color: var(--text-main) !important;
    box-shadow: none !important;
}

.stTextInput input:focus,
.stTextArea textarea:focus,
.stDateInput input:focus,
.stNumberInput input:focus {
    border: 1.5px solid var(--invap-green) !important;
    box-shadow: 0 0 0 3px rgba(0, 122, 61, 0.12) !important;
}

.stTextInput input,
.stDateInput input,
.stNumberInput input {
    min-height: 46px !important;
    padding-left: 14px !important;
}

.stTextArea textarea {
    min-height: 150px !important;
    padding: 14px !important;
    line-height: 1.45 !important;
}

/* Selectbox */
.stSelectbox div[data-baseweb="select"] > div {
    min-height: 48px !important;
    display: flex !important;
    align-items: center !important;
}

/* Botones */
.stButton > button {
    width: 100%;
    min-height: 48px !important;
    font-size: 0.98rem !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    border: 1px solid var(--invap-green) !important;
    background: var(--invap-green) !important;
    color: #FFFFFF !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.14) !important;
    transition: all 0.15s ease-in-out !important;
}

.stButton > button:hover {
    background: var(--invap-green-dark) !important;
    border-color: var(--invap-green-dark) !important;
    color: #FFFFFF !important;
    transform: translateY(-1px);
}

.stButton > button:active {
    transform: translateY(0px);
}

/* Botones HTML de descarga */
a button {
    min-height: 48px !important;
    font-size: 0.98rem !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.14) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px !important;
    border-bottom: 1px solid var(--border-soft) !important;
}

.stTabs [data-baseweb="tab"] {
    height: 48px !important;
    font-size: 0.98rem !important;
    font-weight: 700 !important;
    background-color: #EEF2F5 !important;
    color: #334155 !important;
    border-radius: 10px 10px 0 0 !important;
    padding-left: 18px !important;
    padding-right: 18px !important;
}

.stTabs [aria-selected="true"] {
    background-color: var(--invap-green) !important;
    color: #FFFFFF !important;
}

/* Cajas de aviso */
.camera-off-box {
    padding: 0.9rem 1rem !important;
    border-radius: 10px !important;
    background: var(--invap-green-soft) !important;
    border: 1px solid rgba(0, 122, 61, 0.28) !important;
    color: #064E2B !important;
    font-size: 0.98rem !important;
    font-weight: 650 !important;
    line-height: 1.45 !important;
}

.note-box {
    padding: 0.9rem !important;
    border-radius: 10px !important;
    background: #FFFFFF !important;
    border: 1px solid var(--border-soft) !important;
    margin-bottom: 0.7rem !important;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06) !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
    background-color: #FFFFFF !important;
    border: 1.5px dashed #94A3B8 !important;
    border-radius: 10px !important;
    padding: 0.9rem !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: var(--invap-green) !important;
}

/* Audio / cámara */
[data-testid="stCameraInput"],
[data-testid="stAudioInput"] {
    background-color: #FFFFFF !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 10px !important;
    padding: 0.9rem !important;
}

/* Alertas */
.stAlert {
    font-size: 0.96rem !important;
    border-radius: 10px !important;
    border: 1px solid var(--border-soft) !important;
}

/* Métricas */
[data-testid="metric-container"] {
    background-color: #FFFFFF !important;
    border: 1px solid var(--border-soft) !important;
    padding: 1rem !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 5px rgba(15,23,42,0.06) !important;
}

/* Evita que todo se vea exageradamente grande */
p, div, span {
    line-height: 1.45;
}

/* Responsive */
@media (max-width: 900px) {
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    h1 {
        font-size: 1.8rem !important;
    }

    .big-section-title {
        font-size: 1.7rem !important;
    }

    .stButton > button {
        min-height: 52px !important;
    }

    .stTextArea textarea {
        min-height: 140px !important;
    }
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================
def get_creds():
    creds = None
    project_id = None

    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
        creds = service_account.Credentials.from_service_account_info(info)
        project_id = info.get("project_id")
    elif os.path.exists("google-credentials.json"):
        creds = service_account.Credentials.from_service_account_file("google-credentials.json")

    return creds, project_id


def cargar_lista_normas(creds, project_id):
    try:
        client = storage.Client(credentials=creds, project=project_id)
        blobs = client.list_blobs("invap-asistente-normas")
        return [blob.name for blob in blobs if blob.name.lower().endswith(".pdf")]
    except Exception:
        return []


def nombre_norma_limpio(norma_path):
    """
    Limpia la ruta de la norma para mostrar solo el nombre del archivo.
    Ejemplo:
    API/API - 16D - 2005.pdf -> API - 16D - 2005.pdf
    """
    if not norma_path:
        return "No determinada"

    return str(norma_path).split("/")[-1]


def init_session_state():
    defaults = {
        # Base
        "lista_normas": [],
        "motor": None,
        "menu_principal": "Dashboard",

        # Reset global de widgets
        "reset_global_counter": 0,
        "camara_reset_counter": 0,
        "upload_reset_counter": 0,
        "audio_reset_counter": 0,
        "consulta_upload_reset_counter": 0,
        "consulta_reset_counter": 0,
        "anotacion_reset_counter": 0,
        "qa_reset_counter": 0,

        # Registro de Hallazgo
        "input_hallazgo_usuario": "",
        "audio_procesado": False,
        "ultimo_informe": None,
        "norma_actual": None,
        "hallazgo_actual": "",
        "imagenes_actuales": [],

        # Consultas Normativas
        "consulta_norma_input": "",
        "respuesta_consulta_norma": "",

        # Anotaciones
        "anotaciones": [],
        "texto_anotacion": "",
        "audio_anotacion_procesado": False,

        # QA
        "qa_resultado": "",
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def incrementar_resets():
    """
    Fuerza a Streamlit a reconstruir widgets que no se limpian solo con borrar texto:
    cámara, audio, file_uploader, inputs, etc.
    """
    st.session_state["reset_global_counter"] += 1
    st.session_state["camara_reset_counter"] += 1
    st.session_state["upload_reset_counter"] += 1
    st.session_state["audio_reset_counter"] += 1
    st.session_state["consulta_upload_reset_counter"] += 1
    st.session_state["consulta_reset_counter"] += 1
    st.session_state["anotacion_reset_counter"] += 1
    st.session_state["qa_reset_counter"] += 1


def limpiar_inspeccion_completa():
    """
    Resetea todo lo relacionado con el informe/inspección actual:
    texto, audio, informe, norma, imágenes y widgets.
    No borra anotaciones históricas; para eso está el botón específico.
    """
    st.session_state["input_hallazgo_usuario"] = ""
    st.session_state["audio_procesado"] = False
    st.session_state["ultimo_informe"] = None
    st.session_state["norma_actual"] = None
    st.session_state["hallazgo_actual"] = ""
    st.session_state["imagenes_actuales"] = []

    incrementar_resets()
    st.rerun()


def limpiar_consulta_normativa():
    """
    Limpia completamente la solapa Consultas Normativas.
    """
    st.session_state["consulta_norma_input"] = ""
    st.session_state["respuesta_consulta_norma"] = ""
    st.session_state["consulta_upload_reset_counter"] += 1
    st.session_state["consulta_reset_counter"] += 1
    st.rerun()


def limpiar_anotaciones_completas():
    """
    Borra todas las anotaciones y también limpia audio/texto de entrada.
    """
    st.session_state["anotaciones"] = []
    st.session_state["texto_anotacion"] = ""
    st.session_state["audio_anotacion_procesado"] = False
    st.session_state["anotacion_reset_counter"] += 1
    st.rerun()


def limpiar_entrada_anotacion():
    """
    Limpia solo el campo de nueva anotación y su audio.
    """
    st.session_state["texto_anotacion"] = ""
    st.session_state["audio_anotacion_procesado"] = False
    st.session_state["anotacion_reset_counter"] += 1
    st.rerun()


def generar_descarga_txt(nombre_base: str, contenido: str, label: str):
    if not contenido:
        st.warning("No hay contenido para descargar.")
        return

    b64 = base64.b64encode(contenido.encode("utf-8")).decode()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    href = f"""
    <a href="data:file/txt;base64,{b64}" download="{nombre_base}_{timestamp}.txt">
        <button style="width: 100%; height: 46px; background-color: #1f6feb; color: white;
        border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: bold;">
            {label}
        </button>
    </a>
    """
    st.markdown(href, unsafe_allow_html=True)


def generar_descarga_markdown(nombre_base: str, contenido_md: str, label: str):
    if not contenido_md:
        st.warning("No hay anotaciones para descargar.")
        return

    b64 = base64.b64encode(contenido_md.encode("utf-8")).decode()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    href = f"""
    <a href="data:text/markdown;base64,{b64}" download="{nombre_base}_{timestamp}.md">
        <button style="width: 100%; height: 46px; background-color: #198754; color: white;
        border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: bold;">
            {label}
        </button>
    </a>
    """
    st.markdown(href, unsafe_allow_html=True)


def anotaciones_a_markdown(anotaciones):
    if not anotaciones:
        return ""

    lineas = [
        "# Anotaciones de Inspección",
        "",
        f"Generado: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "---",
        ""
    ]

    for i, nota in enumerate(anotaciones, start=1):
        fecha = nota.get("fecha", "")
        texto = nota.get("texto", "").strip()
        lineas.extend([
            f"## Nota {i}",
            f"**Fecha:** {fecha}",
            "",
            texto,
            "",
            "---",
            ""
        ])

    return "\n".join(lineas)


# =========================================================
# INICIALIZACIÓN
# =========================================================
init_session_state()

creds, project_id = get_creds()

if "GEMINI_API_KEY" not in st.secrets:
    st.error("No se encontró GEMINI_API_KEY en los secrets de Streamlit.")
    st.stop()

if st.session_state["motor"] is None:
    st.session_state["motor"] = InspeccionEngine(
        api_key=st.secrets["GEMINI_API_KEY"],
        creds=creds,
        project_id=project_id
    )

if not st.session_state["lista_normas"]:
    st.session_state["lista_normas"] = cargar_lista_normas(creds, project_id)


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("## ⚙️ INVAP")
    st.markdown("### Navegación")

    menu = st.radio(
        "Ir a",
        ["Dashboard", "Asistente de Inspección", "QA / Auditoría"],
        index=["Dashboard", "Asistente de Inspección", "QA / Auditoría"].index(
            st.session_state["menu_principal"]
        ),
        label_visibility="collapsed"
    )
    st.session_state["menu_principal"] = menu

    st.write("---")
    st.caption("Sistema inteligente de apoyo técnico para inspecciones de campo.")


# =========================================================
# CABECERA
# =========================================================
col_logo, col_title = st.columns([1, 6])

with col_logo:
    st.image(
        "https://www.invap.com.ar/wp-content/uploads/2022/04/Logo-INVAP-Blanco.png",
        width=110
    )

with col_title:
    st.title("Sistema Inteligente de Gestión de Integridad")
    st.caption("Asistencia técnica para hallazgos, consultas normativas y auditoría documental")


# =========================================================
# MÓDULO: DASHBOARD
# =========================================================
if st.session_state["menu_principal"] == "Dashboard":
    st.markdown('<div class="big-section-title">📊 Dashboard</div>', unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Inspecciones Totales", "1.242", "+12%")
    m2.metric("Alertas Críticas", "14", "⚠️")
    m3.metric("Efectividad IA", "99,1%", "🎯")

    st.write("")

    st.subheader("Tendencias")
    df = pd.DataFrame(
        np.random.randn(20, 3),
        columns=["Mantenimiento", "Corrosión", "Soldadura"]
    )
    st.area_chart(df)

    st.write("")
    st.info("Este panel puede crecer después con métricas reales, histórico de hallazgos y KPIs de desvíos.")


# =========================================================
# MÓDULO: ASISTENTE DE INSPECCIÓN
# =========================================================
elif st.session_state["menu_principal"] == "Asistente de Inspección":
    st.markdown('<div class="big-section-title">🚀 Asistente de Inspección</div>', unsafe_allow_html=True)

    subtab1, subtab2, subtab3 = st.tabs([
        "📝 Registro de Hallazgo",
        "📚 Consultas Normativas",
        "🗒️ Anotaciones"
    ])

    # -----------------------------------------------------
    # SUBTAB 1: REGISTRO DE HALLAZGO
    # -----------------------------------------------------
    with subtab1:
        c1, c2 = st.columns([1, 2])

        with c1:
            st.subheader("Registro")

            audio_key = f"audio_hallazgo_{st.session_state['audio_reset_counter']}"
            audio = st.audio_input("Dictar hallazgo", key=audio_key)

            if audio and not st.session_state.get("audio_procesado", False):
                try:
                    audio_bytes = audio.getvalue()
                    st.session_state["input_hallazgo_usuario"] = st.session_state["motor"].transcribir_audio(
                        audio_bytes,
                        audio.type
                    )
                    st.session_state["audio_procesado"] = True
                    st.session_state["reset_global_counter"] += 1
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo transcribir el audio: {e}")

            hallazgo_key = f"hallazgo_text_area_{st.session_state['reset_global_counter']}"
            hallazgo = st.text_area(
                "Descripción técnica",
                value=st.session_state.get("input_hallazgo_usuario", ""),
                height=170,
                placeholder="Ej.: Se observa eslinga con alambres cortados en ojal...",
                key=hallazgo_key
            )

            st.session_state["input_hallazgo_usuario"] = hallazgo

            st.write("---")

            # ---------------------------
            # SWITCH DE CÁMARA
            # ---------------------------
            cam_toggle_key = f"activar_camara_{st.session_state['camara_reset_counter']}"
            usar_camara = st.toggle(
                "📷 Activar cámara para capturar evidencia",
                value=False,
                key=cam_toggle_key
            )

            cam_key = f"cam_input_{st.session_state['camara_reset_counter']}"
            up_key = f"file_uploader_{st.session_state['upload_reset_counter']}"

            foto_c = None

            if usar_camara:
                foto_c = st.camera_input("Capturar evidencia", key=cam_key)
            else:
                st.markdown(
                    """
                    <div class="camera-off-box">
                        Cámara apagada. Active el switch solo cuando necesite capturar una imagen.
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            foto_a = st.file_uploader(
                "O cargar imagen",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key=up_key
            )

            lista_imgs_motor = []

            if foto_c:
                try:
                    lista_imgs_motor.append((foto_c.getvalue(), foto_c.type))
                except Exception:
                    pass

            if foto_a:
                for f in foto_a:
                    try:
                        lista_imgs_motor.append((f.getvalue(), f.type))
                    except Exception:
                        pass

            st.session_state["imagenes_actuales"] = lista_imgs_motor

            if st.button("🚀 GENERAR INFORME TÉCNICO", width="stretch"):
                if not hallazgo and not lista_imgs_motor:
                    st.warning("⚠️ Proporcione descripción o imagen.")
                else:
                    try:
                        with st.spinner("Analizando hallazgo..."):
                            norma = st.session_state["motor"].clasificar_norma_ia(
                                hallazgo,
                                st.session_state["lista_normas"],
                                lista_imgs_motor
                            )

                            res, ref = st.session_state["motor"].consultar_normativa_rag(
                                norma,
                                hallazgo,
                                lista_imgs_motor
                            )

                            st.session_state["ultimo_informe"] = res
                            st.session_state["norma_actual"] = ref
                            st.session_state["hallazgo_actual"] = hallazgo

                    except Exception as e:
                        st.error(f"No se pudo generar el informe técnico: {e}")

            st.write("")
            st.write("")

            if st.button("🔄 NUEVA INSPECCIÓN", width="stretch"):
                limpiar_inspeccion_completa()

        with c2:
            st.subheader("Previsualización y Refinamiento")

            if st.session_state.get("ultimo_informe"):
                norma_visible = nombre_norma_limpio(st.session_state.get("norma_actual"))

                st.info(f"**Norma detectada:** {norma_visible}")
                st.markdown(st.session_state["ultimo_informe"])
                st.write("---")

                feedback = st.chat_input("💬 Corregir o mejorar el informe...")

                if feedback:
                    try:
                        with st.spinner("Refinando informe..."):
                            st.session_state["ultimo_informe"] = st.session_state["motor"].refinar_informe(
                                st.session_state["ultimo_informe"],
                                feedback
                            )
                            st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo refinar el informe: {e}")

                generar_descarga_txt(
                    nombre_base="Informe_INVAP",
                    contenido=st.session_state["ultimo_informe"],
                    label="💾 DESCARGAR INFORME"
                )
            else:
                st.info("El informe técnico aparecerá aquí luego de procesar el hallazgo.")

    # -----------------------------------------------------
    # SUBTAB 2: CONSULTAS NORMATIVAS
    # -----------------------------------------------------
    with subtab2:
        st.subheader("Consultas Normativas")
        st.caption("Realice una consulta libre para orientarse sobre en qué norma podría encuadrarse un caso.")

        pregunta_key = f"consulta_norma_text_area_{st.session_state['consulta_reset_counter']}"
        pregunta = st.text_area(
            "Escriba su consulta",
            value=st.session_state.get("consulta_norma_input", ""),
            height=130,
            placeholder="Ej.: ¿Qué norma podría aplicar si se detectan alambres cortados en una eslinga?",
            key=pregunta_key
        )

        st.session_state["consulta_norma_input"] = pregunta

        consulta_up_key = f"consulta_file_uploader_{st.session_state['consulta_upload_reset_counter']}"
        consulta_img = st.file_uploader(
            "Adjuntar imagen opcional para la consulta",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key=consulta_up_key
        )

        lista_imgs_consulta = []

        if consulta_img:
            for f in consulta_img:
                try:
                    lista_imgs_consulta.append((f.getvalue(), f.type))
                except Exception:
                    pass

        col_cons_1, col_cons_2 = st.columns([1, 1])

        with col_cons_1:
            if st.button("📚 CONSULTAR NORMA", width="stretch"):
                if not pregunta.strip():
                    st.warning("Ingrese una consulta.")
                else:
                    st.session_state["consulta_norma_input"] = pregunta
                    try:
                        with st.spinner("Consultando normativa..."):
                            respuesta = st.session_state["motor"].consultar_normas_chat(
                                pregunta=pregunta,
                                lista_normas=st.session_state["lista_normas"],
                                lista_imagenes=lista_imgs_consulta
                            )
                            st.session_state["respuesta_consulta_norma"] = respuesta
                    except Exception as e:
                        st.error(f"No se pudo resolver la consulta normativa: {e}")

        with col_cons_2:
            if st.button("🧹 LIMPIAR CONSULTA", width="stretch"):
                limpiar_consulta_normativa()

        st.write("")

        if st.session_state.get("respuesta_consulta_norma"):
            st.markdown("### Respuesta")
            st.markdown(st.session_state["respuesta_consulta_norma"])

            generar_descarga_txt(
                nombre_base="Consulta_Normativa",
                contenido=st.session_state["respuesta_consulta_norma"],
                label="💾 DESCARGAR RESPUESTA"
            )
        else:
            st.info("La respuesta de la consulta normativa aparecerá aquí.")

    # -----------------------------------------------------
    # SUBTAB 3: ANOTACIONES
    # -----------------------------------------------------
    with subtab3:
        st.subheader("Anotaciones")
        st.caption("Puede guardar múltiples anotaciones y descargarlas cuando quiera en formato Markdown.")

        st.markdown("#### Entrada por audio")

        audio_anotacion_key = f"audio_anotacion_{st.session_state['anotacion_reset_counter']}"
        audio_anotacion = st.audio_input(
            "Dictar anotación",
            key=audio_anotacion_key
        )

        if audio_anotacion and not st.session_state.get("audio_anotacion_procesado", False):
            try:
                with st.spinner("Transcribiendo anotación..."):
                    audio_bytes = audio_anotacion.getvalue()

                    texto_transcripto = st.session_state["motor"].transcribir_audio(
                        audio_bytes,
                        audio_anotacion.type
                    )

                    st.session_state["texto_anotacion"] = texto_transcripto
                    st.session_state["audio_anotacion_procesado"] = True

                    # Fuerza a reconstruir el text_area para que tome el texto transcripto
                    st.session_state["anotacion_reset_counter"] += 1

                    st.rerun()

            except Exception as e:
                st.error(f"No se pudo transcribir la anotación: {e}")

        st.markdown("#### Entrada manual")

        nota_key = f"nueva_anotacion_{st.session_state['anotacion_reset_counter']}"
        nueva_nota = st.text_area(
            "Nueva anotación",
            value=st.session_state.get("texto_anotacion", ""),
            height=140,
            placeholder="Escriba aquí observaciones, pendientes, ideas o notas de campo...",
            key=nota_key
        )

        st.session_state["texto_anotacion"] = nueva_nota

        col_note_1, col_note_2, col_note_3, col_note_4 = st.columns([1, 1, 1, 1])

        with col_note_1:
            if st.button("➕ AGREGAR ANOTACIÓN", width="stretch"):
                if not nueva_nota.strip():
                    st.warning("Escriba o dicte una anotación antes de agregar.")
                else:
                    st.session_state["anotaciones"].append({
                        "fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "texto": nueva_nota.strip()
                    })

                    st.session_state["texto_anotacion"] = ""
                    st.session_state["audio_anotacion_procesado"] = False
                    st.session_state["anotacion_reset_counter"] += 1
                    st.success("Anotación agregada.")
                    st.rerun()

        with col_note_2:
            if st.button("🧹 LIMPIAR ENTRADA", width="stretch"):
                limpiar_entrada_anotacion()

        with col_note_3:
            if st.button("🗑️ BORRAR TODAS", width="stretch"):
                limpiar_anotaciones_completas()

        with col_note_4:
            md = anotaciones_a_markdown(st.session_state["anotaciones"])
            generar_descarga_markdown(
                nombre_base="Anotaciones_Inspeccion",
                contenido_md=md,
                label="⬇️ DESCARGAR .MD"
            )

        st.write("")

        cantidad = len(st.session_state["anotaciones"])
        st.info(f"Cantidad de anotaciones: {cantidad}")

        if st.session_state["anotaciones"]:
            st.markdown("### Historial")

            for i, nota in enumerate(st.session_state["anotaciones"], start=1):
                with st.container():
                    st.markdown(
                        f"""
                        <div class="note-box">
                            <b>Nota {i}</b><br>
                            <span class="small-muted">{nota.get("fecha", "")}</span><br><br>
                            {nota.get("texto", "")}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
        else:
            st.info("Todavía no hay anotaciones cargadas.")


# =========================================================
# MÓDULO: QA / AUDITORÍA
# =========================================================
elif st.session_state["menu_principal"] == "QA / Auditoría":
    st.markdown('<div class="big-section-title">🔍 QA / Auditoría</div>', unsafe_allow_html=True)

    st.subheader("Agente de Auditoría QA")
    st.write("Cargue un reporte PDF para validar consistencia técnica.")

    pdf_qa_key = f"qa_pdf_{st.session_state['qa_reset_counter']}"
    pdf_qa = st.file_uploader(
        "Subir reporte PDF",
        type=["pdf"],
        key=pdf_qa_key
    )

    prompt_qa = st.text_area(
        "Instrucción de auditoría",
        value="Valida formato FE-44 y consistencia técnica del reporte.",
        height=120
    )

    if st.button("🔍 AUDITAR REPORTE", width="stretch"):
        if not pdf_qa:
            st.warning("Suba un PDF para auditar.")
        else:
            try:
                with st.spinner("Analizando calidad..."):
                    res_qa = st.session_state["motor"].analizar_pdf_qa(
                        pdf_qa.read(),
                        prompt_qa
                    )
                    st.session_state["qa_resultado"] = res_qa
            except Exception as e:
                st.error(f"No se pudo auditar el reporte: {e}")

    st.write("")

    if st.session_state.get("qa_resultado"):
        st.success("Auditoría completada")
        st.markdown(st.session_state["qa_resultado"])

        generar_descarga_txt(
            nombre_base="Auditoria_QA",
            contenido=st.session_state["qa_resultado"],
            label="💾 DESCARGAR AUDITORÍA"
        )
    else:
        st.info("El resultado de la auditoría aparecerá aquí.")


# =========================================================
# PIE
# =========================================================
st.divider()
st.caption(f"© {datetime.date.today().year} INVAP Ingeniería S.A. | Gabriel")