import os
import re
import json
import uuid
import base64
from pathlib import Path
import datetime
import unicodedata
import textwrap
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from PIL import Image

from google.cloud import storage
from google.oauth2 import service_account

from engine import InspeccionEngine


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
BUCKET_NAME = "invap-asistente-normas"
REGISTROS_PREFIX = "registros_inspecciones"
MEMORIA_NORMATIVA_PREFIX = "memoria_normativa"
MEMORIA_NORMATIVA_FILE = f"{MEMORIA_NORMATIVA_PREFIX}/memoria_normativa_validada.json"
APP_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

LOGO_SIDEBAR_CANDIDATES = [
    "assets/Logo 1.jpg",
    "assets/logo_1.jpg",
    "assets/logo_invap_sidebar.jpg",
    "assets/logo_invap_sidebar.png",
    "assets/logo_invap_ingenieria.png",
]

LOGO_HEADER_CANDIDATES = [
    "assets/Logo 2.jpg",
    "assets/logo_2.jpg",
    "assets/logo_invap_header.jpg",
    "assets/logo_invap_header.png",
    "assets/logo_invap_ingenieria.png",
]

FOOTER_LOGO_CANDIDATES = [
    "assets/Logo 2.jpg",
    "assets/logo_footer_invap.png",
    "assets/logo_invap_footer.png",
    "assets/logo_invap_ingenieria.png",
]


def ahora_argentina():
    """
    Devuelve fecha y hora oficial de Argentina.
    Evita que Streamlit/servidor guarde horarios UTC o de otra zona.
    """
    return datetime.datetime.now(APP_TZ).replace(tzinfo=None)



def buscar_logo(candidatos):
    for path in candidatos:
        if os.path.exists(path):
            return path
    return None


def render_logo_invap_sidebar(width=245):
    logo = buscar_logo(LOGO_SIDEBAR_CANDIDATES)
    if logo:
        st.image(logo, width=width)
    else:
        st.markdown(
            """
            <div style="
                background:#0C5A43;
                color:white;
                border-radius:16px;
                padding:16px;
                font-weight:900;
                text-align:center;
                border:1px solid rgba(255,255,255,0.18);
            ">
                INVAP<br>INGENIERÍA S.A.
            </div>
            """,
            unsafe_allow_html=True
        )


def render_logo_invap_header(width=190):
    logo = buscar_logo(LOGO_HEADER_CANDIDATES)
    if logo:
        st.image(logo, width=width)
    else:
        st.markdown(
            """
            <div style="
                background:#FFFFFF;
                color:#0C5A43;
                border-radius:16px;
                padding:16px;
                font-weight:900;
                text-align:center;
                border:1px solid #CFE3DA;
            ">
                INVAP<br>INGENIERÍA S.A.
            </div>
            """,
            unsafe_allow_html=True
        )



# =========================================================
# HELPERS FOOTER INVAP
# =========================================================
def _file_to_data_uri(path):
    if not path or not os.path.exists(path):
        return None
    ext = os.path.splitext(path)[1].lower()
    mime = "image/png"
    if ext in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    elif ext == ".svg":
        mime = "image/svg+xml"

    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def render_footer_invap():
    footer_logo = buscar_logo(FOOTER_LOGO_CANDIDATES)
    logo_uri = _file_to_data_uri(footer_logo)

    if logo_uri:
        html = f"""
        <div class="invap-fixed-footer">
            <img src="{logo_uri}" alt="INVAP Ingeniería S.A." />
        </div>
        """
    else:
        html = """
        <div class="invap-fixed-footer invap-fixed-footer-text">
            INVAP INGENIERÍA S.A.
        </div>
        """

    st.markdown(html, unsafe_allow_html=True)


CLIENTES_COMODORO = [
    "DLS - Nova Energy",
    "Clear Petrolum",
    "San Antonio International",
    "AESA",
    "Pan American Energy",
    "Halliburton",
    "Tecpetrol",
    "Venver",
    "Otro"
]

REGIONES = [
    "Comodoro Rivadavia",
    "Neuquén",
    "Bariloche",
    "Otra"
]

TIPOS_EQUIPO = [
    "Pulling",
    "Workover",
    "Perforación",
    "Carretón",
    "BOP",
    "Acumulador",
    "Bomba de lodo",
    "Otro"
]

SISTEMAS_AFECTADOS = [
    "Estructura",
    "Sistema de izaje",
    "Control de pozo",
    "Bombas de lodo",
    "Seguridad",
    "Cuadro de maniobras",
    "Mesa rotary",
    "Sistema de potencia",
    "Otro"
]

CRITICIDADES = [
    "Crítico",
    "Mayor",
    "Menor"
]

TIPOS_INSPECCION = [
    "Documental",
    "Visual",
    "Funcional"
]

ESTADOS_GESTION = [
    "Pendiente",
    "En análisis",
    "Cerrado"
]

MENU_ITEMS = [
    "Dashboard operativo",
    "Consultas Normativas",
    "Anotaciones",
    "Registro de hallazgo",
    "Corrección Informes FE-44",
]


favicon_file = Path("assets/favicon_invap_logo1.png")
if not favicon_file.exists():
    favicon_file = Path("assets/Logo 1.jpg")

page_icon_invap = Image.open(favicon_file) if favicon_file.exists() else "🟩"

st.set_page_config(
    page_title="INVAP - Sistema Inteligente de Integridad",
    page_icon=page_icon_invap,
    layout="wide"
)


# =========================================================
# ESTILOS BÁSICOS
# =========================================================
st.markdown("""
<style>
:root {
    --invap-green-dark: #004B35;
    --invap-green-main: #007A3D;
    --invap-green-mid: #0F7A59;
    --invap-green-light: #EAF6F0;
    --invap-green-soft: #DDF2E8;
    --invap-white: #FFFFFF;
    --text-main: #0F241C;
    --text-muted: #60756D;
    --border-soft: #CFE3DA;
    --bg-app: #F4F8F6;
    --bg-card: #FFFFFF;
}

.stApp {
    background: var(--bg-app) !important;
}

.block-container {
    padding-top: 1.4rem !important;
    padding-bottom: 2.2rem !important;
    max-width: 1250px !important;
}

/* Tipografía */
html, body, [class*="css"] {
    font-size: 16px !important;
    color: var(--text-main) !important;
}

h1, h2, h3 {
    color: var(--text-main) !important;
}

h1 {
    font-size: 2.15rem !important;
    font-weight: 900 !important;
    letter-spacing: -0.03em !important;
}

h2 {
    font-size: 1.55rem !important;
    font-weight: 850 !important;
}

h3 {
    font-size: 1.20rem !important;
    font-weight: 800 !important;
}

.big-section-title {
    font-size: 2rem !important;
    font-weight: 900 !important;
    color: var(--text-main) !important;
    margin-bottom: 0.6rem !important;
}

.small-muted,
[data-testid="stCaptionContainer"],
.stCaptionContainer {
    color: var(--text-muted) !important;
    font-size: 0.96rem !important;
}

/* Sidebar INVAP */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #003D2B 0%, #004B35 48%, #006B49 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.10) !important;
}

section[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}

section[data-testid="stSidebar"] [data-testid="stImage"] {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 18px;
    padding: 12px;
    margin-bottom: 12px;
    box-shadow: 0 8px 18px rgba(0,0,0,0.12);
}

section[data-testid="stSidebar"] [role="radiogroup"] label {
    font-size: 1.04rem !important;
    font-weight: 750 !important;
    padding: 0.42rem 0 !important;
}

section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.18) !important;
}

.sidebar-brand {
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.16);
    border-radius: 18px;
    padding: 16px 16px;
    margin: 12px 0 18px 0;
    box-shadow: 0 8px 18px rgba(0,0,0,0.10);
}

.sidebar-brand-title {
    font-size: 1.12rem;
    font-weight: 900;
    color: #FFFFFF;
    margin-bottom: 5px;
}

.sidebar-brand-sub {
    font-size: 0.92rem;
    color: #E8F7F0;
    line-height: 1.38;
}

/* Cabecera institucional */
.invap-header-card {
    background: linear-gradient(135deg, #007A3D 0%, #004B35 74%, #003D2B 100%);
    border-radius: 24px;
    padding: 26px 30px;
    border: 1px solid rgba(207, 227, 218, 0.95);
    box-shadow: 0 10px 26px rgba(0, 75, 53, 0.18);
    margin-bottom: 1.3rem;
}

.invap-header-title {
    font-size: 2.08rem;
    font-weight: 950;
    color: #FFFFFF;
    letter-spacing: -0.03em;
    margin-bottom: 7px;
}

.invap-header-subtitle {
    font-size: 1.03rem;
    color: #EAF6F0;
    line-height: 1.45;
}

/* Inputs */
label,
.stTextInput label,
.stTextArea label,
.stSelectbox label,
.stFileUploader label {
    font-size: 1rem !important;
    font-weight: 800 !important;
    color: var(--text-main) !important;
}

.stTextInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div,
.stDateInput input,
.stNumberInput input {
    font-size: 1rem !important;
    border-radius: 14px !important;
    border: 1.5px solid var(--border-soft) !important;
    background-color: #FFFFFF !important;
    color: var(--text-main) !important;
    box-shadow: none !important;
}

.stTextInput input:focus,
.stTextArea textarea:focus,
.stDateInput input:focus,
.stNumberInput input:focus {
    border: 1.5px solid var(--invap-green-main) !important;
    box-shadow: 0 0 0 3px rgba(0, 122, 61, 0.14) !important;
}

.stTextInput input,
.stDateInput input,
.stNumberInput input {
    min-height: 52px !important;
    padding-left: 15px !important;
}

.stTextArea textarea {
    min-height: 170px !important;
    padding: 15px !important;
    line-height: 1.45 !important;
}

.stSelectbox div[data-baseweb="select"] > div {
    min-height: 52px !important;
    display: flex !important;
    align-items: center !important;
}

/* Botones grandes */
.stButton > button {
    width: 100%;
    min-height: 60px !important;
    font-size: 1.06rem !important;
    font-weight: 900 !important;
    border-radius: 16px !important;
    border: 1px solid #004B35 !important;
    background: linear-gradient(135deg, #007A3D 0%, #004B35 100%) !important;
    color: #FFFFFF !important;
    box-shadow: 0 6px 15px rgba(0, 75, 53, 0.22) !important;
    transition: all 0.18s ease-in-out !important;
    padding: 0.82rem 1rem !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #008F4B 0%, #004B35 100%) !important;
    border-color: #003D2B !important;
    color: #FFFFFF !important;
    transform: translateY(-1px);
    box-shadow: 0 9px 22px rgba(0, 75, 53, 0.28) !important;
}

.stButton > button:active {
    transform: translateY(0px);
}

/* Botones HTML de descarga */
a button {
    width: 100%;
    min-height: 58px !important;
    background: linear-gradient(135deg, #007A3D 0%, #004B35 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 16px !important;
    cursor: pointer !important;
    font-size: 15px !important;
    font-weight: 900 !important;
    box-shadow: 0 6px 15px rgba(0, 75, 53, 0.22) !important;
}

/* Cards */
.camera-off-box,
.note-box,
.attention-card,
.dashboard-box,
.form-box,
[data-testid="metric-container"] {
    border-radius: 18px !important;
    background: var(--bg-card) !important;
    border: 1px solid var(--border-soft) !important;
    box-shadow: 0 4px 12px rgba(15, 36, 28, 0.07) !important;
}

.camera-off-box {
    padding: 1rem !important;
    background: var(--invap-green-light) !important;
    color: var(--text-main) !important;
    font-weight: 750 !important;
    line-height: 1.45 !important;
}

.note-box,
.attention-card,
.dashboard-box,
.form-box {
    padding: 1rem !important;
    margin-bottom: 0.85rem !important;
}

.attention-critical {
    border-left: 7px solid #C62828 !important;
}

.attention-warning {
    border-left: 7px solid #D79A16 !important;
}

.attention-ok {
    border-left: 7px solid var(--invap-green-main) !important;
}

[data-testid="stFileUploader"] {
    background-color: #FFFFFF !important;
    border: 1.7px dashed #A8CDBD !important;
    border-radius: 16px !important;
    padding: 1rem !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: var(--invap-green-main) !important;
}

[data-testid="stCameraInput"],
[data-testid="stAudioInput"] {
    background-color: #FFFFFF !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 16px !important;
    padding: 1rem !important;
}

.stAlert {
    font-size: 0.98rem !important;
    border-radius: 16px !important;
    border: 1px solid var(--border-soft) !important;
}

[data-testid="metric-container"] {
    padding: 1rem !important;
}

[data-testid="stDataFrame"] {
    border-radius: 16px !important;
    overflow: hidden !important;
}

p, div, span {
    line-height: 1.45;
}

@media (max-width: 900px) {
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    .big-section-title {
        font-size: 1.65rem !important;
    }

    .invap-header-title {
        font-size: 1.55rem;
    }

    .stButton > button {
        min-height: 62px !important;
    }
}

/* =========================================================
   CHATBOT NORMATIVO - UI TIPO CHAT MODERNO INVAP
   ========================================================= */
.invap-chat-hero {
    background: linear-gradient(135deg, #FFFFFF 0%, #F4F8F6 100%);
    border: 1px solid #CFE3DA;
    border-radius: 22px;
    padding: 18px 20px;
    margin: 12px 0 18px 0;
    box-shadow: 0 6px 18px rgba(15, 36, 28, 0.07);
}

.invap-chat-hero-title {
    font-size: 1.25rem;
    font-weight: 900;
    color: #0F241C;
    margin-bottom: 6px;
}

.invap-chat-hero-sub {
    font-size: 0.98rem;
    color: #60756D;
    line-height: 1.45;
}

.invap-chat-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 8px 0 14px 0;
}

.invap-chat-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    border-radius: 999px;
    padding: 7px 11px;
    background: #EAF6F0;
    color: #004B35;
    border: 1px solid #CFE3DA;
    font-size: 0.88rem;
    font-weight: 800;
}

.invap-chat-tip {
    background: #FFFFFF;
    border: 1px solid #CFE3DA;
    border-left: 5px solid #007A3D;
    border-radius: 16px;
    padding: 13px 15px;
    color: #60756D;
    margin: 10px 0 14px 0;
    box-shadow: 0 4px 12px rgba(15, 36, 28, 0.05);
}

.invap-chat-empty {
    background: #FFFFFF;
    border: 1px dashed #CFE3DA;
    border-radius: 20px;
    padding: 22px;
    color: #60756D;
    text-align: center;
}

.invap-chat-empty strong {
    color: #004B35;
}

[data-testid="stChatMessage"] {
    border-radius: 20px !important;
    border: 1px solid #CFE3DA !important;
    background: #FFFFFF !important;
    box-shadow: 0 4px 14px rgba(15, 36, 28, 0.06) !important;
    padding: 0.75rem 1rem !important;
    margin: 0.65rem 0 !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: #F4F8F6 !important;
    border-color: #DDEBE4 !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: #FFFFFF !important;
    border-left: 5px solid #007A3D !important;
}

.invap-chat-input-label {
    font-size: 1rem;
    font-weight: 900;
    color: #0F241C;
    margin: 14px 0 6px 0;
}

.invap-chat-input-help {
    font-size: 0.92rem;
    color: #60756D;
    margin-top: -4px;
    margin-bottom: 8px;
}

/* Botones compactos exclusivos del chatbot */
.st-key-chat_normativo_send_compacto button,
.st-key-chat_normativo_clear_compacto button {
    min-height: 46px !important;
    height: 46px !important;
    border-radius: 14px !important;
    font-size: 0.96rem !important;
    padding: 0.45rem 0.85rem !important;
    box-shadow: 0 4px 12px rgba(0, 75, 53, 0.16) !important;
}

.st-key-chat_normativo_send_compacto button {
    background: linear-gradient(135deg, #007A3D 0%, #004B35 100%) !important;
    border: 1px solid #004B35 !important;
    color: #FFFFFF !important;
}

.st-key-chat_normativo_clear_compacto button {
    background: #FFFFFF !important;
    color: #004B35 !important;
    border: 1px solid #CFE3DA !important;
}

.st-key-chat_normativo_clear_compacto button:hover {
    background: #EAF6F0 !important;
    color: #004B35 !important;
    border-color: #007A3D !important;
}

@media (max-width: 768px) {
    .invap-chat-hero {
        padding: 15px;
        border-radius: 18px;
    }

    .invap-chat-hero-title {
        font-size: 1.1rem;
    }

    [data-testid="stChatMessage"] {
        padding: 0.65rem 0.8rem !important;
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


def get_storage_client(creds, project_id):
    if creds:
        return storage.Client(credentials=creds, project=project_id)

    if project_id:
        return storage.Client(project=project_id)

    return storage.Client()


def cargar_lista_normas(creds, project_id):
    try:
        client = get_storage_client(creds, project_id)
        blobs = client.list_blobs(BUCKET_NAME)
        return [blob.name for blob in blobs if blob.name.lower().endswith(".pdf")]
    except Exception:
        return []


def nombre_norma_limpio(norma_path):
    if not norma_path:
        return "No determinada"

    return str(norma_path).split("/")[-1]


def sanitizar_para_archivo(texto):
    if not texto:
        return "sin_equipo"

    texto = str(texto)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.upper()
    texto = re.sub(r"[^A-Z0-9]+", "_", texto)
    texto = texto.strip("_")

    return texto[:40] if texto else "sin_equipo"


def generar_id_informe(equipo):
    timestamp = ahora_argentina().strftime("%Y%m%d_%H%M%S")
    equipo_limpio = sanitizar_para_archivo(equipo)
    corto = uuid.uuid4().hex[:6].upper()
    return f"INS-{timestamp}-{equipo_limpio}-{corto}"


def guardar_registro_inspeccion(creds, project_id, registro):
    client = get_storage_client(creds, project_id)
    bucket = client.bucket(BUCKET_NAME)

    fecha = ahora_argentina()
    id_informe = registro["id_informe"]

    ruta = (
        f"{REGISTROS_PREFIX}/"
        f"{fecha.strftime('%Y')}/"
        f"{fecha.strftime('%m')}/"
        f"{fecha.strftime('%d')}/"
        f"{id_informe}.json"
    )

    blob = bucket.blob(ruta)
    blob.upload_from_string(
        json.dumps(registro, ensure_ascii=False, indent=2),
        content_type="application/json"
    )

    return ruta


def cargar_registros_inspeccion(creds, project_id):
    registros = []

    try:
        client = get_storage_client(creds, project_id)
        blobs = client.list_blobs(BUCKET_NAME, prefix=f"{REGISTROS_PREFIX}/")

        for blob in blobs:
            if not blob.name.lower().endswith(".json"):
                continue

            try:
                contenido = blob.download_as_text(encoding="utf-8")
                item = json.loads(contenido)
                item["_ruta_gcs"] = blob.name
                registros.append(item)
            except Exception:
                continue

    except Exception:
        return []

    return registros




# =========================================================
# MEMORIA NORMATIVA VALIDADA
# =========================================================
def normalizar_memoria_texto(texto):
    if not texto:
        return ""

    texto = str(texto)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9áéíóúñü\s\.\-]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def extraer_tokens_memoria(texto):
    texto_norm = normalizar_memoria_texto(texto)

    stopwords = {
        "se", "de", "del", "la", "el", "los", "las", "un", "una", "en", "con",
        "por", "para", "que", "y", "o", "al", "su", "sus", "a", "no",
        "presenta", "observa", "evidencia", "detecta", "realiza", "durante",
        "sistema", "equipo", "condicion", "condición", "inspeccion", "inspección",
        "caso", "norma", "aplica", "aplicar"
    }

    tokens = []
    for t in texto_norm.split():
        if len(t) < 4:
            continue
        if t in stopwords:
            continue
        tokens.append(t)

    vistos = set()
    salida = []
    for t in tokens:
        if t not in vistos:
            vistos.add(t)
            salida.append(t)

    return salida[:30]


def cargar_memoria_normativa(creds, project_id):
    try:
        client = get_storage_client(creds, project_id)
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(MEMORIA_NORMATIVA_FILE)

        if not blob.exists():
            return []

        contenido = blob.download_as_text(encoding="utf-8")
        data = json.loads(contenido)

        if isinstance(data, list):
            return data

        return []
    except Exception:
        return []


def guardar_memoria_normativa(creds, project_id, memoria):
    """
    Guarda la memoria normativa validada por el usuario en Google Cloud Storage.

    Importante:
    - Si la service account no tiene permisos de escritura sobre el bucket,
      Google Cloud puede devolver Forbidden / 403.
    - En ese caso no se debe romper toda la app: se informa el problema
      para poder seguir usando Consultas Normativas.
    """
    try:
        client = get_storage_client(creds, project_id)
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(MEMORIA_NORMATIVA_FILE)

        blob.upload_from_string(
            json.dumps(memoria, ensure_ascii=False, indent=2),
            content_type="application/json"
        )

        return True, MEMORIA_NORMATIVA_FILE

    except Exception as e:
        msg_error = str(e)

        if "403" in msg_error or "Forbidden" in msg_error:
            return (
                False,
                "No se pudo guardar la memoria normativa: la cuenta de servicio "
                "no tiene permisos de escritura sobre el bucket de Google Cloud Storage."
            )

        return (
            False,
            f"No se pudo guardar la memoria normativa: {type(e).__name__}"
        )


def buscar_norma_por_nombre_limpio(lista_normas, nombre_norma):
    if not nombre_norma:
        return None

    objetivo = normalizar_memoria_texto(nombre_norma).replace(" ", "")

    for norma in lista_normas:
        base = str(norma).split("/")[-1]
        base_norm = normalizar_memoria_texto(base).replace(" ", "")

        if base_norm == objetivo:
            return norma

    objetivo_simple = objetivo.replace(".pdf", "")

    for norma in lista_normas:
        base = str(norma).split("/")[-1]
        base_norm = normalizar_memoria_texto(base).replace(" ", "").replace(".pdf", "")

        if objetivo_simple and objetivo_simple in base_norm:
            return norma

    return None


def sugerir_norma_desde_memoria(hallazgo, lista_normas, memoria):
    if not hallazgo or not memoria:
        return None, None

    texto_actual = normalizar_memoria_texto(hallazgo)
    tokens_actuales = set(extraer_tokens_memoria(hallazgo))

    mejor_item = None
    mejor_score = 0

    for item in memoria:
        norma_validada = item.get("norma_validada", "")
        if not norma_validada:
            continue

        palabras = item.get("palabras_clave", [])
        if not palabras:
            palabras = extraer_tokens_memoria(item.get("hallazgo_base", ""))

        palabras_norm = set(normalizar_memoria_texto(p) for p in palabras if p)

        score = 0
        score += len(tokens_actuales.intersection(palabras_norm)) * 2

        for p in palabras_norm:
            if p and len(p) >= 4 and p in texto_actual:
                score += 2

        sistema_item = normalizar_memoria_texto(item.get("sistema_afectado", ""))
        if sistema_item and sistema_item in texto_actual:
            score += 1

        if score > mejor_score:
            mejor_score = score
            mejor_item = item

    if mejor_item and mejor_score >= 4:
        norma_resuelta = buscar_norma_por_nombre_limpio(
            lista_normas,
            mejor_item.get("norma_validada", "")
        )

        if norma_resuelta:
            return norma_resuelta, {
                "score": mejor_score,
                "caso": mejor_item
            }

    return None, None


def registrar_aprendizaje_normativo(
    creds,
    project_id,
    hallazgo,
    norma_detectada,
    norma_validada,
    contexto=None,
    origen="validacion_usuario"
):
    memoria = cargar_memoria_normativa(creds, project_id)
    contexto = contexto or {}

    norma_validada_limpia = nombre_norma_limpio(norma_validada)
    norma_detectada_limpia = nombre_norma_limpio(norma_detectada)

    item = {
        "id": f"MEM-{ahora_argentina().strftime('%Y%m%d_%H%M%S')}-{uuid.uuid4().hex[:6].upper()}",
        "fecha_hora": ahora_argentina().strftime("%Y-%m-%d %H:%M:%S"),
        "hallazgo_base": hallazgo or "",
        "palabras_clave": extraer_tokens_memoria(hallazgo),
        "norma_detectada": norma_detectada_limpia,
        "norma_validada": norma_validada_limpia,
        "region": contexto.get("region", ""),
        "cliente": contexto.get("cliente", ""),
        "equipo": contexto.get("equipo", ""),
        "tipo_equipo": contexto.get("tipo_equipo", ""),
        "sistema_afectado": contexto.get("sistema_afectado", ""),
        "tipo_inspeccion": contexto.get("tipo_inspeccion", ""),
        "criticidad": contexto.get("criticidad", ""),
        "origen": origen,
        "validado_por_usuario": True
    }

    firma_nueva = (
        normalizar_memoria_texto(item["hallazgo_base"])[:120],
        item["norma_validada"]
    )

    for existente in memoria:
        firma_existente = (
            normalizar_memoria_texto(existente.get("hallazgo_base", ""))[:120],
            existente.get("norma_validada", "")
        )
        if firma_existente == firma_nueva:
            return False, "Este aprendizaje ya estaba registrado."

    memoria.append(item)

    guardado_ok, mensaje_guardado = guardar_memoria_normativa(creds, project_id, memoria)

    if not guardado_ok:
        return False, mensaje_guardado

    return True, f"Aprendizaje guardado: {norma_validada_limpia}"


def registros_a_dataframe(registros):
    columnas = [
        "id_informe",
        "fecha_hora",
        "region",
        "cliente",
        "equipo",
        "tipo_equipo",
        "sistema_afectado",
        "tipo_inspeccion",
        "criticidad",
        "estado",
        "norma_detectada",
        "hallazgo_original",
        "informe_generado",
        "cantidad_imagenes",
        "_ruta_gcs"
    ]

    if not registros:
        return pd.DataFrame(columns=columnas)

    df = pd.DataFrame(registros)

    for col in columnas:
        if col not in df.columns:
            df[col] = None

    df["fecha_dt"] = pd.to_datetime(df["fecha_hora"], errors="coerce")
    df = df.sort_values("fecha_dt", ascending=False, na_position="last")

    return df


def index_seguro(opciones, valor, defecto=0):
    try:
        return opciones.index(valor)
    except Exception:
        return defecto


def validar_contexto_archivo(contexto, hallazgo, informe, norma):
    faltantes = []

    if not contexto.get("region"):
        faltantes.append("Región / Base")

    if not contexto.get("cliente"):
        faltantes.append("Cliente")

    if not contexto.get("equipo"):
        faltantes.append("Equipo")

    if not contexto.get("tipo_equipo"):
        faltantes.append("Tipo de equipo")

    if not contexto.get("sistema_afectado"):
        faltantes.append("Sistema afectado")

    if not contexto.get("tipo_inspeccion"):
        faltantes.append("Tipo de inspección")

    if not contexto.get("criticidad"):
        faltantes.append("Criticidad")

    if not contexto.get("estado"):
        faltantes.append("Estado")

    if not hallazgo:
        faltantes.append("Hallazgo original")

    if not informe:
        faltantes.append("Informe generado")

    if not norma:
        faltantes.append("Norma detectada")

    return faltantes


def markdown_informe(contexto, norma, hallazgo, informe):
    fecha = ahora_argentina().strftime("%d/%m/%Y %H:%M")
    return f"""# Informe técnico de inspección

**Fecha de generación:** {fecha}

## Datos de inspección

- **Región / Base:** {contexto.get('region', '')}
- **Cliente:** {contexto.get('cliente', '')}
- **Equipo / Identificación:** {contexto.get('equipo', '')}
- **Tipo de equipo:** {contexto.get('tipo_equipo', '')}
- **Sistema afectado:** {contexto.get('sistema_afectado', '')}
- **Tipo de inspección:** {contexto.get('tipo_inspeccion', '')}
- **Criticidad:** {contexto.get('criticidad', '')}
- **Estado de gestión:** {contexto.get('estado', '')}
- **Norma detectada:** {nombre_norma_limpio(norma)}

## Hallazgo original

{hallazgo}

## Informe generado

{informe}
"""


def limpiar_markdown_para_pdf(texto):
    texto = texto or ""
    reemplazos = {
        "#": "",
        "**": "",
        "•": "-",
        "–": "-",
        "—": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "✅": "",
        "⚠️": "ATENCION:",
        "🔴": "",
        "🟡": "",
        "🟢": "",
        "📌": "",
        "📁": "",
        "🧠": "",
        "💾": "",
    }

    for a, b in reemplazos.items():
        texto = texto.replace(a, b)

    return texto


def pdf_escape(texto):
    texto = texto.replace("\\", "\\\\")
    texto = texto.replace("(", "\\(")
    texto = texto.replace(")", "\\)")
    return texto



def crear_pdf_simple_bytes(titulo, contenido):
    """
    Genera un PDF profesional con soporte correcto de acentos.
    Requiere reportlab en requirements.txt.
    """
    import io
    import re
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
    )

    buffer = io.BytesIO()
    width, height = A4

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.7 * cm,
        leftMargin=1.7 * cm,
        topMargin=2.5 * cm,
        bottomMargin=1.6 * cm,
        title=titulo,
        author="INVAP Ingeniería S.A.",
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="InvapTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=12,
    ))

    styles.add(ParagraphStyle(
        name="InvapSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
        spaceAfter=14,
    ))

    styles.add(ParagraphStyle(
        name="InvapHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#007A3D"),
        spaceBefore=10,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name="InvapBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=12.5,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#111827"),
        spaceAfter=5,
    ))

    styles.add(ParagraphStyle(
        name="InvapBullet",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=12.5,
        leftIndent=12,
        firstLineIndent=-8,
        textColor=colors.HexColor("#111827"),
        spaceAfter=4,
    ))

    def header_footer(canvas, doc_obj):
        canvas.saveState()

        # Header
        canvas.setFillColor(colors.HexColor("#007A3D"))
        canvas.rect(0, height - 1.65 * cm, width, 1.65 * cm, fill=1, stroke=0)

        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(1.7 * cm, height - 1.0 * cm, "INVAP Ingeniería S.A.")

        canvas.setFont("Helvetica", 8.5)
        canvas.drawRightString(
            width - 1.7 * cm,
            height - 1.0 * cm,
            "Sistema Inteligente de Gestión de Integridad"
        )

        # Footer
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(1.7 * cm, 1.0 * cm, "Informe generado por Asistente de Inspección")
        canvas.drawRightString(width - 1.7 * cm, 1.0 * cm, f"Página {doc_obj.page}")

        canvas.restoreState()

    def md_inline(text):
        text = escape(text)
        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
        text = text.replace("✅", "")
        text = text.replace("⚠️", "ATENCIÓN:")
        text = text.replace("🔴", "")
        text = text.replace("🟡", "")
        text = text.replace("🟢", "")
        text = text.replace("📌", "")
        text = text.replace("📁", "")
        text = text.replace("🧠", "")
        text = text.replace("💾", "")
        return text

    story = []

    story.append(Paragraph("Informe Técnico de Inspección", styles["InvapTitle"]))
    story.append(Paragraph(
        "Documento generado a partir del registro de hallazgo, análisis asistido por IA, "
        "consulta normativa y validación del usuario.",
        styles["InvapSubTitle"]
    ))

    lines = contenido.splitlines()

    for raw in lines:
        line = raw.strip()

        if not line:
            story.append(Spacer(1, 5))
            continue

        if line.startswith("# "):
            continue

        if line.startswith("## "):
            story.append(Paragraph(md_inline(line.replace("## ", "")), styles["InvapHeading"]))
            continue

        if line.startswith("- "):
            story.append(Paragraph("• " + md_inline(line[2:]), styles["InvapBullet"]))
            continue

        story.append(Paragraph(md_inline(line), styles["InvapBody"]))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)

    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def generar_descarga_txt(nombre_base: str, contenido: str, label: str):
    if not contenido:
        st.warning("No hay contenido para descargar.")
        return

    b64 = base64.b64encode(contenido.encode("utf-8")).decode()
    timestamp = ahora_argentina().strftime("%Y%m%d_%H%M")
    href = f"""
    <a href="data:file/txt;base64,{b64}" download="{nombre_base}_{timestamp}.txt">
        <button style="width: 100%; height: 58px; background: linear-gradient(135deg, #007A3D 0%, #004B35 100%); color: white;
        border: none; border-radius: 16px; cursor: pointer; font-size: 15px; font-weight: 900;">
            {label}
        </button>
    </a>
    """
    st.markdown(href, unsafe_allow_html=True)


def generar_descarga_markdown(nombre_base: str, contenido_md: str, label: str):
    if not contenido_md:
        st.warning("No hay contenido para descargar.")
        return

    b64 = base64.b64encode(contenido_md.encode("utf-8")).decode()
    timestamp = ahora_argentina().strftime("%Y%m%d_%H%M")
    href = f"""
    <a href="data:text/markdown;base64,{b64}" download="{nombre_base}_{timestamp}.md">
        <button style="width: 100%; height: 58px; background: linear-gradient(135deg, #007A3D 0%, #004B35 100%); color: white;
        border: none; border-radius: 16px; cursor: pointer; font-size: 15px; font-weight: 900;">
            {label}
        </button>
    </a>
    """
    st.markdown(href, unsafe_allow_html=True)


def generar_descarga_pdf(nombre_base: str, contenido_md: str, label: str):
    if not contenido_md:
        st.warning("No hay contenido para descargar.")
        return

    pdf_bytes = crear_pdf_simple_bytes("Informe técnico INVAP", contenido_md)
    b64 = base64.b64encode(pdf_bytes).decode()
    timestamp = ahora_argentina().strftime("%Y%m%d_%H%M")
    href = f"""
    <a href="data:application/pdf;base64,{b64}" download="{nombre_base}_{timestamp}.pdf">
        <button style="width: 100%; height: 58px; background: linear-gradient(135deg, #007A3D 0%, #004B35 100%); color: white;
        border: none; border-radius: 16px; cursor: pointer; font-size: 15px; font-weight: 900;">
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
        f"Generado: {ahora_argentina().strftime('%d/%m/%Y %H:%M')}",
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


def init_session_state():
    defaults = {
        # Base
        "lista_normas": [],
        "motor": None,
        "menu_principal": "Dashboard operativo",

        # Reset global de widgets
        "reset_global_counter": 0,
        "camara_reset_counter": 0,
        "upload_reset_counter": 0,
        "audio_reset_counter": 0,
        "consulta_upload_reset_counter": 0,
        "consulta_audio_reset_counter": 0,
        "consulta_reset_counter": 0,
        "anotacion_reset_counter": 0,
        "qa_reset_counter": 0,

        # Datos de inspección
        "region_inspeccion": "Comodoro Rivadavia",
        "cliente_inspeccion": "DLS - Nova Energy",
        "cliente_manual_inspeccion": "",
        "cliente_otro_inspeccion": "",
        "equipo_inspeccion": "",
        "tipo_equipo_inspeccion": "Workover",
        "sistema_afectado_inspeccion": "Estructura",
        "tipo_inspeccion": "Visual",
        "criticidad_inspeccion": "Mayor",
        "estado_inspeccion": "Pendiente",
        "contexto_inspeccion_actual": {},
        "ruta_ultimo_archivo": "",

        # Registro de Hallazgo
        "input_hallazgo_usuario": "",
        "audio_procesado": False,
        "ultimo_informe": None,
        "norma_actual": None,
        "hallazgo_actual": "",
        "imagenes_actuales": [],
        "memoria_normativa_aplicada": False,
        "memoria_normativa_detalle": None,
        "aprendizaje_normativo_msg": "",

        # Consultas Normativas
        "consulta_norma_input": "",
        "respuesta_consulta_norma": "",
        "audio_consulta_procesado": False,
        "chat_normativo_mensajes": [],
        "contexto_ultima_consulta_normativa": {},
        "consulta_norma_detectada": None,
        "consulta_memoria_normativa_aplicada": False,
        "consulta_memoria_normativa_detalle": None,
        "consulta_aprendizaje_normativo_msg": "",
        "chat_normativo_reset_counter": 0,
        "chat_normativo_ui_version": "",

        # Anotaciones
        "anotaciones": [],
        "texto_anotacion": "",
        "audio_anotacion_procesado": False,

        # QA
        "qa_resultado": "",

        # Sincronización manual
        "sync_msg": "",
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if st.session_state.get("menu_principal") == "Dashboard":
        st.session_state["menu_principal"] = "Dashboard operativo"
    if st.session_state.get("menu_principal") == "Asistente de Inspección":
        st.session_state["menu_principal"] = "Registro de hallazgo"

    # Compatibilidad con criticidades usadas en versiones anteriores
    if st.session_state.get("criticidad_inspeccion") not in CRITICIDADES:
        mapa_criticidad = {
            "Alto": "Mayor",
            "Medio": "Menor",
            "Bajo": "Menor"
        }
        st.session_state["criticidad_inspeccion"] = mapa_criticidad.get(
            st.session_state.get("criticidad_inspeccion"),
            "Mayor"
        )

    if st.session_state.get("tipo_inspeccion") not in TIPOS_INSPECCION:
        st.session_state["tipo_inspeccion"] = "Visual"


def incrementar_resets():
    st.session_state["reset_global_counter"] += 1
    st.session_state["camara_reset_counter"] += 1
    st.session_state["upload_reset_counter"] += 1
    st.session_state["audio_reset_counter"] += 1
    st.session_state["consulta_upload_reset_counter"] += 1
    st.session_state["consulta_audio_reset_counter"] += 1
    st.session_state["consulta_reset_counter"] += 1
    st.session_state["anotacion_reset_counter"] += 1
    st.session_state["qa_reset_counter"] += 1


def limpiar_inspeccion_completa():
    st.session_state["input_hallazgo_usuario"] = ""
    st.session_state["audio_procesado"] = False
    st.session_state["ultimo_informe"] = None
    st.session_state["norma_actual"] = None
    st.session_state["hallazgo_actual"] = ""
    st.session_state["imagenes_actuales"] = []
    st.session_state["ruta_ultimo_archivo"] = ""
    st.session_state["memoria_normativa_aplicada"] = False
    st.session_state["memoria_normativa_detalle"] = None
    st.session_state["aprendizaje_normativo_msg"] = ""

    incrementar_resets()
    st.rerun()



def limpiar_consulta_y_analisis():
    """
    Limpia información temporal de todas las pestañas operativas,
    sin borrar registros archivados ni datos del Dashboard.
    """
    # Registro de hallazgo
    st.session_state["input_hallazgo_usuario"] = ""
    st.session_state["audio_procesado"] = False
    st.session_state["ultimo_informe"] = None
    st.session_state["norma_actual"] = None
    st.session_state["hallazgo_actual"] = ""
    st.session_state["imagenes_actuales"] = []
    st.session_state["ruta_ultimo_archivo"] = ""

    # Consultas Normativas
    st.session_state["consulta_norma_input"] = ""
    st.session_state["respuesta_consulta_norma"] = ""
    st.session_state["audio_consulta_procesado"] = False
    st.session_state["consulta_norma_detectada"] = None
    st.session_state["consulta_memoria_normativa_aplicada"] = False
    st.session_state["consulta_memoria_normativa_detalle"] = None
    st.session_state["consulta_aprendizaje_normativo_msg"] = ""
    st.session_state["chat_normativo_mensajes"] = []
    st.session_state["contexto_ultima_consulta_normativa"] = {}
    st.session_state["chat_normativo_ui_version"] = ""

    # Anotaciones
    st.session_state["anotaciones"] = []
    st.session_state["texto_anotacion"] = ""
    st.session_state["audio_anotacion_procesado"] = False

    # Corrección FE-44 / QA
    st.session_state["qa_resultado"] = ""

    # Reset de widgets
    st.session_state["reset_global_counter"] += 1
    st.session_state["camara_reset_counter"] += 1
    st.session_state["upload_reset_counter"] += 1
    st.session_state["audio_reset_counter"] += 1
    st.session_state["consulta_upload_reset_counter"] += 1
    st.session_state["consulta_audio_reset_counter"] += 1
    st.session_state["consulta_reset_counter"] += 1
    st.session_state["anotacion_reset_counter"] += 1
    st.session_state["qa_reset_counter"] += 1
    st.session_state["chat_normativo_reset_counter"] = st.session_state.get("chat_normativo_reset_counter", 0) + 1

    # Cámara normativa si existe
    if "consulta_usar_camara_normativa" in st.session_state:
        st.session_state["consulta_usar_camara_normativa"] = False
    if "consulta_camara_reset_counter" in st.session_state:
        st.session_state["consulta_camara_reset_counter"] += 1

    st.session_state["sync_msg"] = "Consulta y análisis limpiados correctamente."
    st.rerun()


def limpiar_consulta_normativa():
    st.session_state["consulta_norma_input"] = ""
    st.session_state["respuesta_consulta_norma"] = ""
    st.session_state["audio_consulta_procesado"] = False
    st.session_state["consulta_norma_detectada"] = None
    st.session_state["consulta_memoria_normativa_aplicada"] = False
    st.session_state["consulta_memoria_normativa_detalle"] = None
    st.session_state["consulta_aprendizaje_normativo_msg"] = ""

    st.session_state["consulta_upload_reset_counter"] += 1
    st.session_state["consulta_audio_reset_counter"] += 1
    st.session_state["consulta_reset_counter"] += 1

    st.rerun()


def limpiar_anotaciones_completas():
    st.session_state["anotaciones"] = []
    st.session_state["texto_anotacion"] = ""
    st.session_state["audio_anotacion_procesado"] = False
    st.session_state["anotacion_reset_counter"] += 1
    st.rerun()


def limpiar_entrada_anotacion():
    st.session_state["texto_anotacion"] = ""
    st.session_state["audio_anotacion_procesado"] = False
    st.session_state["anotacion_reset_counter"] += 1
    st.rerun()



def render_dashboard(df):
    st.markdown('<div class="big-section-title">📊 Dashboard operativo</div>', unsafe_allow_html=True)
    st.caption(
        "Tablero construido únicamente con informes archivados por los usuarios. "
        "No utiliza datos simulados."
    )

    if df.empty:
        st.info(
            "Todavía no hay informes archivados. Genere un informe desde "
            "'Registro de hallazgo' y presione 'Archivar informe para Dashboard' para comenzar a construir indicadores reales."
        )
        return

    st.markdown("### Filtros operativos")

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

    regiones = ["Todas"] + sorted([x for x in df["region"].dropna().unique().tolist() if x])
    clientes = ["Todos"] + sorted([x for x in df["cliente"].dropna().unique().tolist() if x])
    sistemas = ["Todos"] + sorted([x for x in df["sistema_afectado"].dropna().unique().tolist() if x])
    criticidades = ["Todas"] + sorted([x for x in df["criticidad"].dropna().unique().tolist() if x])

    with col_f1:
        filtro_region = st.selectbox("Región / Base", regiones)

    with col_f2:
        filtro_cliente = st.selectbox("Cliente", clientes)

    with col_f3:
        filtro_sistema = st.selectbox("Sistema", sistemas)

    with col_f4:
        filtro_criticidad = st.selectbox("Criticidad", criticidades)

    df_f = df.copy()

    if filtro_region != "Todas":
        df_f = df_f[df_f["region"] == filtro_region]

    if filtro_cliente != "Todos":
        df_f = df_f[df_f["cliente"] == filtro_cliente]

    if filtro_sistema != "Todos":
        df_f = df_f[df_f["sistema_afectado"] == filtro_sistema]

    if filtro_criticidad != "Todas":
        df_f = df_f[df_f["criticidad"] == filtro_criticidad]

    if df_f.empty:
        st.warning("No hay registros para los filtros seleccionados.")
        return

    total = len(df_f)
    criticos = len(df_f[df_f["criticidad"] == "Crítico"])
    altos = len(df_f[df_f["criticidad"] == "Alto"])
    criticos_abiertos = len(df_f[(df_f["criticidad"] == "Crítico") & (df_f["estado"] != "Cerrado")])
    pendientes = len(df_f[df_f["estado"] != "Cerrado"])
    cerrados = len(df_f[df_f["estado"] == "Cerrado"])
    equipos_afectados = df_f["equipo"].nunique()
    regiones_activas = df_f["region"].nunique()
    clientes_activos = df_f["cliente"].nunique()
    normas_usadas = df_f["norma_detectada"].nunique()

    tasa_cierre = round((cerrados / total) * 100, 1) if total else 0
    tasa_pendiente = round((pendientes / total) * 100, 1) if total else 0
    tasa_critica = round((criticos / total) * 100, 1) if total else 0

    def kpi_card(titulo, valor, detalle, color="#007A3D"):
        st.markdown(
            f"""
            <div style="
                background:#FFFFFF;
                border:1px solid #D9E2E8;
                border-left:7px solid {color};
                border-radius:14px;
                padding:16px 18px;
                box-shadow:0 1px 6px rgba(15,23,42,0.08);
                min-height:118px;
            ">
                <div style="font-size:0.86rem;color:#64748B;font-weight:700;">{titulo}</div>
                <div style="font-size:2rem;font-weight:850;color:#0F172A;margin-top:4px;">{valor}</div>
                <div style="font-size:0.86rem;color:#475569;margin-top:4px;">{detalle}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.write("")
    st.markdown("### KPIs principales")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi_card("Informes archivados", total, "Registros reales en GCS", "#007A3D")
    with k2:
        kpi_card("Críticos abiertos", criticos_abiertos, "Prioridad operativa inmediata", "#DC2626")
    with k3:
        kpi_card("Pendientes / análisis", pendientes, f"{tasa_pendiente}% del total filtrado", "#F59E0B")
    with k4:
        kpi_card("Tasa de cierre", f"{tasa_cierre}%", f"{cerrados} informes cerrados", "#2563EB")

    st.write("")

    k5, k6, k7, k8 = st.columns(4)
    with k5:
        kpi_card("Equipos afectados", equipos_afectados, "Identificaciones únicas", "#7C3AED")
    with k6:
        kpi_card("Clientes activos", clientes_activos, "Clientes con registros", "#0EA5E9")
    with k7:
        kpi_card("Regiones activas", regiones_activas, "Bases con informes", "#059669")
    with k8:
        kpi_card("Normas utilizadas", normas_usadas, "Normas aplicadas en informes", "#334155")

    st.write("")
    st.markdown("### 🔴 Atención hoy")

    if criticos_abiertos > 0:
        st.markdown(
            f"""
            <div class="attention-card attention-critical">
                <strong>Hallazgos críticos abiertos</strong><br>
                Existen <strong>{criticos_abiertos}</strong> hallazgos críticos sin cierre.
                Se recomienda priorizar revisión técnica, validación documental y seguimiento del estado de gestión.
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div class="attention-card attention-ok">
                <strong>Sin críticos abiertos</strong><br>
                No se registran hallazgos críticos pendientes bajo los filtros seleccionados.
            </div>
            """,
            unsafe_allow_html=True
        )

    if pendientes > 0:
        sistema_top = df_f[df_f["estado"] != "Cerrado"]["sistema_afectado"].value_counts()
        if not sistema_top.empty:
            st.markdown(
                f"""
                <div class="attention-card attention-warning">
                    <strong>Sistema con mayor carga pendiente</strong><br>
                    El sistema con más hallazgos sin cierre es
                    <strong>{sistema_top.index[0]}</strong>, con <strong>{int(sistema_top.iloc[0])}</strong> registros.
                </div>
                """,
                unsafe_allow_html=True
            )

    region_top = df_f["region"].value_counts()
    if not region_top.empty:
        st.markdown(
            f"""
            <div class="attention-card">
                <strong>Mayor concentración por región/base</strong><br>
                La mayor cantidad de registros corresponde a
                <strong>{region_top.index[0]}</strong>, con <strong>{int(region_top.iloc[0])}</strong> informes archivados.
            </div>
            """,
            unsafe_allow_html=True
        )

    st.write("")
    st.markdown("### Resumen ejecutivo")

    col_res1, col_res2, col_res3 = st.columns(3)

    with col_res1:
        resumen_criticidad = df_f["criticidad"].value_counts().rename_axis("Criticidad").reset_index(name="Cantidad")
        st.dataframe(resumen_criticidad, width="stretch", hide_index=True)

    with col_res2:
        resumen_estado = df_f["estado"].value_counts().rename_axis("Estado").reset_index(name="Cantidad")
        st.dataframe(resumen_estado, width="stretch", hide_index=True)

    with col_res3:
        resumen_sistemas = df_f["sistema_afectado"].value_counts().head(6).rename_axis("Sistema").reset_index(name="Cantidad")
        st.dataframe(resumen_sistemas, width="stretch", hide_index=True)

    st.write("")
    st.markdown("### Distribución operativa")

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("#### Hallazgos por sistema")
        sistema_counts = df_f["sistema_afectado"].value_counts()
        if not sistema_counts.empty:
            st.bar_chart(sistema_counts, height=300)
        else:
            st.info("Sin datos de sistema.")

    with col_g2:
        st.markdown("#### Hallazgos por criticidad")
        criticidad_counts = df_f["criticidad"].value_counts()
        if not criticidad_counts.empty:
            st.bar_chart(criticidad_counts, height=300)
        else:
            st.info("Sin datos de criticidad.")

    col_g3, col_g4 = st.columns(2)

    with col_g3:
        st.markdown("#### Estado de gestión")
        estado_counts = df_f["estado"].value_counts()
        if not estado_counts.empty:
            st.bar_chart(estado_counts, height=280)
        else:
            st.info("Sin datos de estado.")

    with col_g4:
        st.markdown("#### Normas más utilizadas")
        normas_counts = df_f["norma_detectada"].dropna().apply(nombre_norma_limpio).value_counts().head(10)
        if not normas_counts.empty:
            st.bar_chart(normas_counts, height=280)
        else:
            st.info("Sin datos de normas.")

    st.write("")
    st.markdown("### Últimos informes archivados")

    tabla = df_f[[
        "fecha_hora",
        "region",
        "cliente",
        "equipo",
        "tipo_equipo",
        "sistema_afectado",
        "tipo_inspeccion",
        "criticidad",
        "estado",
        "norma_detectada"
    ]].copy()

    tabla["norma_detectada"] = tabla["norma_detectada"].apply(nombre_norma_limpio)

    st.dataframe(
        tabla.head(30),
        width="stretch",
        hide_index=True
    )

    st.write("")
    with st.expander("Ver detalle técnico de registros filtrados"):
        detalle = df_f[[
            "id_informe",
            "fecha_hora",
            "region",
            "cliente",
            "equipo",
            "hallazgo_original",
            "informe_generado",
            "_ruta_gcs"
        ]].copy()

        st.dataframe(
            detalle,
            width="stretch",
            hide_index=True
        )



def render_registro_hallazgo(creds, project_id):
    st.markdown("""
    <style>
    /* Ajustes específicos para Registro de hallazgo */

    /* Textarea de descripción técnica más compacto */
    div[data-testid="stVerticalBlock"]:has(textarea[aria-label="Descripción técnica"]) textarea {
        min-height: 150px !important;
    }

    /* Botones principales de generación más compactos */
    div[data-testid="stVerticalBlock"]:has(textarea[aria-label="Descripción técnica"]) .stButton > button {
        min-height: 50px !important;
        height: 50px !important;
        font-size: 0.95rem !important;
        padding: 0.45rem 0.85rem !important;
        border-radius: 14px !important;
    }

    /* Caja de cámara apagada más compacta */
    .camera-off-box {
        padding: 0.85rem 1rem !important;
        min-height: 72px !important;
        display: flex !important;
        align-items: center !important;
    }

    /* Upload de evidencia visual más compacto */
    section[data-testid="stFileUploaderDropzone"] {
        min-height: 96px !important;
        padding-top: 0.55rem !important;
        padding-bottom: 0.55rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="big-section-title">🛠️ Registro de hallazgo</div>', unsafe_allow_html=True)
    st.markdown('<div class="big-section-title">📝 Registro de hallazgo</div>', unsafe_allow_html=True)
    st.caption("Carga de datos de inspección, registro técnico, generación de informe asistido por IA y archivo para Dashboard.")

    st.markdown("### 1. Datos de inspección")

    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col1:
        region = st.selectbox(
            "Región / Base",
            REGIONES,
            index=index_seguro(REGIONES, st.session_state.get("region_inspeccion", "Comodoro Rivadavia")),
            key="region_inspeccion"
        )

    with col2:
        if region == "Comodoro Rivadavia":
            if st.session_state.get("cliente_inspeccion") not in CLIENTES_COMODORO:
                st.session_state["cliente_inspeccion"] = "DLS - Nova Energy"

            cliente_seleccionado = st.selectbox(
                "Cliente",
                CLIENTES_COMODORO,
                index=index_seguro(CLIENTES_COMODORO, st.session_state.get("cliente_inspeccion", "DLS - Nova Energy")),
                key="cliente_inspeccion"
            )

            if cliente_seleccionado == "Otro":
                cliente_final = st.text_input(
                    "Especificar cliente",
                    key="cliente_otro_inspeccion",
                    placeholder="Ingrese cliente"
                ).strip()
            else:
                cliente_final = cliente_seleccionado
        else:
            cliente_final = st.text_input(
                "Cliente",
                key="cliente_manual_inspeccion",
                placeholder="Ej.: YPF, PAE, empresa local..."
            ).strip()

    with col3:
        equipo = st.text_input(
            "Equipo / Identificación",
            key="equipo_inspeccion",
            placeholder="Ej.: DLS-343, PAE-007, SAI-212"
        ).strip()

    col4, col5, col6, col7, col8 = st.columns([1, 1.15, 1, 0.9, 1])

    with col4:
        tipo_equipo = st.selectbox(
            "Tipo de equipo",
            TIPOS_EQUIPO,
            index=index_seguro(TIPOS_EQUIPO, st.session_state.get("tipo_equipo_inspeccion", "Workover")),
            key="tipo_equipo_inspeccion"
        )

    with col5:
        sistema_afectado = st.selectbox(
            "Sistema afectado",
            SISTEMAS_AFECTADOS,
            index=index_seguro(SISTEMAS_AFECTADOS, st.session_state.get("sistema_afectado_inspeccion", "Estructura")),
            key="sistema_afectado_inspeccion"
        )

    with col6:
        tipo_inspeccion = st.selectbox(
            "Tipo de inspección",
            TIPOS_INSPECCION,
            index=index_seguro(TIPOS_INSPECCION, st.session_state.get("tipo_inspeccion", "Visual")),
            key="tipo_inspeccion"
        )

    with col7:
        criticidad = st.selectbox(
            "Criticidad",
            CRITICIDADES,
            index=index_seguro(CRITICIDADES, st.session_state.get("criticidad_inspeccion", "Mayor")),
            key="criticidad_inspeccion"
        )

    with col8:
        estado = st.selectbox(
            "Estado de gestión",
            ESTADOS_GESTION,
            index=index_seguro(ESTADOS_GESTION, st.session_state.get("estado_inspeccion", "Pendiente")),
            key="estado_inspeccion"
        )

    st.session_state["contexto_inspeccion_actual"] = {
        "region": region,
        "cliente": cliente_final,
        "equipo": equipo,
        "tipo_equipo": tipo_equipo,
        "sistema_afectado": sistema_afectado,
        "tipo_inspeccion": tipo_inspeccion,
        "criticidad": criticidad,
        "estado": estado
    }

    st.write("")
    st.divider()

    st.markdown("### 2. Registro técnico")

    col_audio, col_texto = st.columns([1, 1.6])

    with col_audio:
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

    with col_texto:
        hallazgo_key = f"hallazgo_text_area_{st.session_state['reset_global_counter']}"
        hallazgo = st.text_area(
            "Descripción técnica",
            value=st.session_state.get("input_hallazgo_usuario", ""),
            height=160,
            placeholder="Ej.: Se observa eslinga con alambres cortados en ojal...",
            key=hallazgo_key,
            label_visibility="collapsed"
        )

        st.session_state["input_hallazgo_usuario"] = hallazgo

    st.write("")
    st.markdown("### 3. Evidencia visual")

    col_cam, col_upload = st.columns([1, 1])

    with col_cam:
        cam_toggle_key = f"activar_camara_{st.session_state['camara_reset_counter']}"
        usar_camara = st.toggle(
            "📷 Activar cámara",
            value=False,
            key=cam_toggle_key
        )

        cam_key = f"cam_input_{st.session_state['camara_reset_counter']}"
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

    with col_upload:
        up_key = f"file_uploader_{st.session_state['upload_reset_counter']}"
        foto_a = st.file_uploader(
            "O cargar imagen",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key=up_key,
            label_visibility="collapsed"
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
    st.caption(f"Imágenes cargadas: {len(lista_imgs_motor)}")

    st.write("")
    st.markdown("### 4. Generación del informe")

    col_gen_spacer1, col_gen1, col_gen2, col_gen_spacer2 = st.columns([0.18, 1, 1, 0.18])

    with col_gen1:
        if st.button("🧠 Generar informe con IA", width="stretch"):
            if not hallazgo and not lista_imgs_motor:
                st.warning("⚠️ Proporcione descripción o imagen.")
            else:
                try:
                    with st.spinner("Analizando hallazgo..."):
                        memoria_normativa = cargar_memoria_normativa(creds, project_id)
                        norma_memoria, detalle_memoria = sugerir_norma_desde_memoria(
                            hallazgo,
                            st.session_state["lista_normas"],
                            memoria_normativa
                        )

                        if norma_memoria:
                            norma = norma_memoria
                            st.session_state["memoria_normativa_aplicada"] = True
                            st.session_state["memoria_normativa_detalle"] = detalle_memoria
                        else:
                            norma = st.session_state["motor"].clasificar_norma_ia(
                                hallazgo,
                                st.session_state["lista_normas"],
                                lista_imgs_motor
                            )
                            st.session_state["memoria_normativa_aplicada"] = False
                            st.session_state["memoria_normativa_detalle"] = None

                        res, ref = st.session_state["motor"].consultar_normativa_rag(
                            norma,
                            hallazgo,
                            lista_imgs_motor
                        )

                        st.session_state["ultimo_informe"] = res
                        st.session_state["norma_actual"] = ref
                        st.session_state["hallazgo_actual"] = hallazgo
                        st.session_state["ruta_ultimo_archivo"] = ""

                except Exception as e:
                    st.error(f"No se pudo generar el informe técnico: {e}")

    with col_gen2:
        if st.button("🔄 Nueva inspección", width="stretch"):
            limpiar_inspeccion_completa()

    if st.session_state.get("ultimo_informe"):
        st.write("")
        st.divider()
        st.markdown("### 5. Informe generado")

        norma_visible = nombre_norma_limpio(st.session_state.get("norma_actual"))
        contexto = st.session_state.get("contexto_inspeccion_actual", {})
        hallazgo_final = st.session_state.get("hallazgo_actual") or st.session_state.get("input_hallazgo_usuario", "")
        informe_final = st.session_state.get("ultimo_informe", "")
        informe_md = markdown_informe(
            contexto=contexto,
            norma=st.session_state.get("norma_actual"),
            hallazgo=hallazgo_final,
            informe=informe_final
        )

        st.info(
            f"**Norma detectada:** {norma_visible}  \n"
            f"**Región:** {contexto.get('region', '')} | "
            f"**Cliente:** {contexto.get('cliente', '')} | "
            f"**Equipo:** {contexto.get('equipo', '')} | "
            f"**Tipo de inspección:** {contexto.get('tipo_inspeccion', '')} | "
            f"**Criticidad:** {contexto.get('criticidad', '')}"
        )

        if st.session_state.get("memoria_normativa_aplicada"):
            detalle_mem = st.session_state.get("memoria_normativa_detalle") or {}
            st.caption(
                f"🧠 Norma priorizada por memoria validada. "
                f"Coincidencia técnica: {detalle_mem.get('score', 'N/D')}"
            )

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

        st.markdown("### 6. Descarga y archivo")
        col_down1, col_down2, col_down3, col_archive = st.columns([1, 1, 1, 1.25])

        with col_down1:
            generar_descarga_txt(
                nombre_base="Informe_INVAP",
                contenido=st.session_state["ultimo_informe"],
                label="💾 Descargar TXT"
            )

        with col_down2:
            generar_descarga_markdown(
                nombre_base="Informe_INVAP",
                contenido_md=informe_md,
                label="⬇️ Descargar MD"
            )

        with col_down3:
            generar_descarga_pdf(
                nombre_base="Informe_INVAP",
                contenido_md=informe_md,
                label="📄 Descargar PDF"
            )

        with col_archive:
            if st.button("📁 Archivar informe para Dashboard", width="stretch"):
                contexto = st.session_state.get("contexto_inspeccion_actual", {})
                hallazgo_archivo = st.session_state.get("hallazgo_actual") or st.session_state.get("input_hallazgo_usuario", "")
                informe_archivo = st.session_state.get("ultimo_informe", "")
                norma_archivo = st.session_state.get("norma_actual", "")

                faltantes = validar_contexto_archivo(
                    contexto=contexto,
                    hallazgo=hallazgo_archivo,
                    informe=informe_archivo,
                    norma=norma_archivo
                )

                if faltantes:
                    st.warning(
                        "Antes de archivar complete: "
                        + ", ".join(faltantes)
                    )
                else:
                    try:
                        with st.spinner("Archivando informe en Google Cloud Storage..."):
                            ahora = ahora_argentina()
                            id_informe = generar_id_informe(contexto.get("equipo", ""))

                            registro = {
                                "id_informe": id_informe,
                                "fecha_hora": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                                "region": contexto.get("region", ""),
                                "cliente": contexto.get("cliente", ""),
                                "equipo": contexto.get("equipo", ""),
                                "tipo_equipo": contexto.get("tipo_equipo", ""),
                                "sistema_afectado": contexto.get("sistema_afectado", ""),
                                "tipo_inspeccion": contexto.get("tipo_inspeccion", ""),
                                "criticidad": contexto.get("criticidad", ""),
                                "estado": contexto.get("estado", ""),
                                "hallazgo_original": hallazgo_archivo,
                                "norma_detectada": nombre_norma_limpio(norma_archivo),
                                "informe_generado": informe_archivo,
                                "cantidad_imagenes": len(st.session_state.get("imagenes_actuales", [])),
                                "origen": "Asistente de Inspección INVAP",
                                "validado_por_usuario": True,
                                "usuario": "No identificado"
                            }

                            ruta = guardar_registro_inspeccion(creds, project_id, registro)
                            st.session_state["ruta_ultimo_archivo"] = ruta

                        st.success(f"Informe archivado correctamente: {ruta}")

                    except Exception as e:
                        st.error(f"No se pudo archivar el informe: {e}")

        if st.session_state.get("ruta_ultimo_archivo"):
            st.success(f"Último archivo guardado: {st.session_state['ruta_ultimo_archivo']}")
    else:
        st.write("")
        st.info("El informe técnico aparecerá debajo de esta pantalla luego de procesar el hallazgo.")


def render_consultas_normativas():
    st.markdown("""
    <style>
    /* Botones más compactos en Consulta Normativa */
    div[data-testid="stVerticalBlock"]:has(textarea[aria-label="Escriba o revise su consulta"]) .stButton > button {
        min-height: 50px !important;
        height: 50px !important;
        font-size: 0.95rem !important;
        padding: 0.45rem 0.85rem !important;
        border-radius: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="big-section-title">📚 Consultas Normativas</div>', unsafe_allow_html=True)
    st.write("")
    # =========================================================
    # BLOQUE 1 - CONSULTA PUNTUAL
    # =========================================================
    st.markdown("### 1. Consulta puntual normativa")
    st.write("")
    with st.expander("🎙️ Entrada por audio e imagen opcional", expanded=False):
        col_audio, col_img = st.columns([1, 1])

        with col_audio:
            audio_consulta_key = f"audio_consulta_{st.session_state['consulta_audio_reset_counter']}"
            audio_consulta = st.audio_input(
                "Dictar consulta normativa",
                key=audio_consulta_key
            )

            if audio_consulta and not st.session_state.get("audio_consulta_procesado", False):
                try:
                    with st.spinner("Transcribiendo consulta normativa..."):
                        audio_bytes = audio_consulta.getvalue()

                        texto_transcripto = st.session_state["motor"].transcribir_audio(
                            audio_bytes,
                            audio_consulta.type
                        )

                        st.session_state["consulta_norma_input"] = texto_transcripto
                        st.session_state["audio_consulta_procesado"] = True
                        st.session_state["consulta_reset_counter"] += 1

                        st.rerun()

                except Exception as e:
                    st.error(f"No se pudo transcribir la consulta normativa: {e}")

        with col_img:
            consulta_up_key = f"consulta_file_uploader_{st.session_state['consulta_upload_reset_counter']}"
            consulta_img = st.file_uploader(
                "Adjuntar imagen opcional para la consulta",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key=consulta_up_key
            )

            # Cámara opcional para consulta normativa
            if "consulta_usar_camara_normativa" not in st.session_state:
                st.session_state["consulta_usar_camara_normativa"] = False

            if "consulta_camara_reset_counter" not in st.session_state:
                st.session_state["consulta_camara_reset_counter"] = 0

            usar_camara_normativa = st.toggle(
                "📷 Activar cámara para consulta normativa",
                value=st.session_state.get("consulta_usar_camara_normativa", False),
                key=f"consulta_usar_camara_normativa_{st.session_state['consulta_camara_reset_counter']}"
            )

            st.session_state["consulta_usar_camara_normativa"] = usar_camara_normativa

            consulta_img_camara = None

            if usar_camara_normativa:
                consulta_img_camara = st.camera_input(
                    "Tomar imagen para la consulta normativa",
                    key=f"consulta_normativa_camera_input_{st.session_state['consulta_camara_reset_counter']}"
                )

                if consulta_img_camara is not None:
                    st.image(
                        consulta_img_camara,
                        caption="Imagen capturada con cámara",
                        width=350
                    )

            if st.button("🧹 Limpiar cámara normativa", key="btn_limpiar_camara_normativa"):
                st.session_state["consulta_usar_camara_normativa"] = False
                st.session_state["consulta_camara_reset_counter"] += 1
                st.rerun()

    lista_imgs_consulta = []

    try:
        if "consulta_img" in locals() and consulta_img:
            for f in consulta_img:
                try:
                    lista_imgs_consulta.append((f.getvalue(), f.type))
                except Exception:
                    pass
    except Exception:
        lista_imgs_consulta = []

    pregunta_key = f"consulta_norma_text_area_{st.session_state['consulta_reset_counter']}"
    pregunta = st.text_area(
        "Escriba o revise su consulta",
        value=st.session_state.get("consulta_norma_input", ""),
        height=170,
        placeholder="Ej.: ¿Qué norma podría aplicar si se detectan alambres cortados en una eslinga?",
        key=pregunta_key
    )

    st.session_state["consulta_norma_input"] = pregunta

    col_cons_spacer1, col_cons_1, col_cons_2, col_cons_spacer2 = st.columns([0.18, 1, 1, 0.18])

    with col_cons_1:
        if st.button("📚 Consultar normativa", width="stretch"):
            if not pregunta.strip() and not lista_imgs_consulta:
                st.warning("Ingrese una consulta por texto/audio o adjunte una imagen.")
            else:
                st.session_state["consulta_norma_input"] = pregunta

                try:
                    with st.spinner("Consultando base normativa..."):
                        memoria_normativa = cargar_memoria_normativa(creds, project_id)
                        norma_memoria, detalle_memoria = sugerir_norma_desde_memoria(
                            pregunta,
                            st.session_state["lista_normas"],
                            memoria_normativa
                        )

                        if norma_memoria:
                            respuesta, ref_norma = st.session_state["motor"].consultar_normativa_rag(
                                norma_memoria,
                                pregunta,
                                lista_imgs_consulta
                            )

                            st.session_state["consulta_norma_detectada"] = ref_norma or norma_memoria
                            st.session_state["consulta_memoria_normativa_aplicada"] = True
                            st.session_state["consulta_memoria_normativa_detalle"] = detalle_memoria

                        else:
                            respuesta = st.session_state["motor"].consultar_normas_chat(
                                pregunta=pregunta,
                                lista_normas=st.session_state["lista_normas"],
                                lista_imagenes=lista_imgs_consulta
                            )

                            st.session_state["consulta_norma_detectada"] = None
                            st.session_state["consulta_memoria_normativa_aplicada"] = False
                            st.session_state["consulta_memoria_normativa_detalle"] = None

                        st.session_state["respuesta_consulta_norma"] = respuesta

                        # consulta_norma_detectada_auto_fix_v1
                        # Si la consulta no vino desde memoria validada, igual intentamos
                        # determinar una norma principal para poder confirmar aprendizaje.
                        if not st.session_state.get("consulta_norma_detectada"):
                            try:
                                norma_auto_consulta = st.session_state["motor"].clasificar_norma_ia(
                                    pregunta,
                                    st.session_state["lista_normas"],
                                    lista_imgs_consulta
                                )
                                st.session_state["consulta_norma_detectada"] = norma_auto_consulta
                            except Exception:
                                st.session_state["consulta_norma_detectada"] = None

                        # Contexto oculto para el chatbot normativo.
                        # No se muestra como mensaje inicial, pero permite repreguntas sobre la última consulta puntual.
                        st.session_state["contexto_ultima_consulta_normativa"] = {
                            "pregunta": pregunta.strip(),
                            "respuesta": respuesta,
                            "norma_detectada": nombre_norma_limpio(st.session_state.get("consulta_norma_detectada"))
                        }

                except Exception as e:
                    st.error(f"No se pudo resolver la consulta normativa: {e}")

    with col_cons_2:
        if st.button("🧹 Limpiar consulta puntual", width="stretch"):
            limpiar_consulta_normativa()

    if st.session_state.get("respuesta_consulta_norma"):
        st.write("")
        st.markdown("#### Respuesta de consulta puntual")

        norma_sistema = nombre_norma_limpio(st.session_state.get("consulta_norma_detectada"))
        if norma_sistema and norma_sistema != "No determinada":
            st.info(f"**Norma detectada por el sistema:** {norma_sistema}")

        st.markdown(st.session_state["respuesta_consulta_norma"])

        st.markdown('<div class="memoria-normativa-title">🧠 Memoria normativa</div>', unsafe_allow_html=True)
        st.markdown('<div class="memoria-normativa-help">Validación opcional para mejorar futuras clasificaciones.</div>', unsafe_allow_html=True)


        st.markdown("""
        <style>
        /* Memoria normativa compacta */
        .memoria-normativa-title {
            font-size: 1rem !important;
            font-weight: 850 !important;
            color: #0F241C !important;
            margin-top: 0.65rem !important;
            margin-bottom: 0.1rem !important;
        }

        .memoria-normativa-help {
            font-size: 0.82rem !important;
            color: #60756D !important;
            margin-bottom: 0.35rem !important;
        }

        .st-key-btn_confirmar_norma_consulta button,
        .st-key-btn_guardar_correccion_consulta button {
            min-height: 40px !important;
            height: 40px !important;
            font-size: 0.84rem !important;
            padding: 0.30rem 0.55rem !important;
            border-radius: 11px !important;
            box-shadow: 0 3px 8px rgba(0, 75, 53, 0.12) !important;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 40px !important;
            height: 40px !important;
            font-size: 0.88rem !important;
            border-radius: 11px !important;
        }
        </style>
        """, unsafe_allow_html=True)

        col_apr_sp1, col_cons_apr_1, col_cons_apr_2, col_cons_apr_3, col_apr_sp2 = st.columns([0.18, 0.72, 1.15, 0.72, 0.18])

        with col_cons_apr_1:
            if st.button("✅ Confirmar norma", width="stretch", key="btn_confirmar_norma_consulta"):
                norma_consulta = st.session_state.get("consulta_norma_detectada")

                # Si por algún motivo todavía no hay norma guardada, se intenta resolver
                # automáticamente con el mismo motor de clasificación normativa.
                if not norma_consulta:
                    try:
                        memoria_normativa = cargar_memoria_normativa(creds, project_id)
                        norma_memoria, _ = sugerir_norma_desde_memoria(
                            st.session_state.get("consulta_norma_input", ""),
                            st.session_state.get("lista_normas", []),
                            memoria_normativa
                        )

                        if norma_memoria:
                            norma_consulta = norma_memoria
                        else:
                            norma_consulta = st.session_state["motor"].clasificar_norma_ia(
                                st.session_state.get("consulta_norma_input", ""),
                                st.session_state.get("lista_normas", []),
                                []
                            )

                        st.session_state["consulta_norma_detectada"] = norma_consulta

                    except Exception:
                        norma_consulta = None

                if not norma_consulta:
                    st.warning("No se pudo determinar una norma automática para confirmar. Use la corrección normativa.")
                else:
                    guardado, msg = registrar_aprendizaje_normativo(
                        creds=creds,
                        project_id=project_id,
                        hallazgo=st.session_state.get("consulta_norma_input", ""),
                        norma_detectada=norma_consulta,
                        norma_validada=norma_consulta,
                        contexto={"origen_funcional": "Consultas Normativas"},
                        origen="confirmacion_consulta_normativa"
                    )
                    st.session_state["consulta_aprendizaje_normativo_msg"] = msg
                    st.rerun()

        with col_cons_apr_2:
            opciones_norma_consulta = sorted([nombre_norma_limpio(n) for n in st.session_state.get("lista_normas", [])])
            norma_corregida_consulta = st.selectbox(
                "Corregir norma de consulta",
                ["Seleccionar norma correcta..."] + opciones_norma_consulta,
                key="select_norma_corregida_consulta",
                label_visibility="collapsed"
            )

        with col_cons_apr_3:
            if st.button("💾 Guardar corrección", width="stretch", key="btn_guardar_correccion_consulta"):
                if norma_corregida_consulta == "Seleccionar norma correcta...":
                    st.warning("Seleccione una norma correcta antes de guardar.")
                else:
                    norma_corregida_path = buscar_norma_por_nombre_limpio(
                        st.session_state.get("lista_normas", []),
                        norma_corregida_consulta
                    )

                    guardado, msg = registrar_aprendizaje_normativo(
                        creds=creds,
                        project_id=project_id,
                        hallazgo=st.session_state.get("consulta_norma_input", ""),
                        norma_detectada=st.session_state.get("consulta_norma_detectada"),
                        norma_validada=norma_corregida_path or norma_corregida_consulta,
                        contexto={"origen_funcional": "Consultas Normativas"},
                        origen="correccion_consulta_normativa"
                    )
                    st.session_state["consulta_aprendizaje_normativo_msg"] = msg
                    st.rerun()

        if st.session_state.get("consulta_aprendizaje_normativo_msg"):
            msg_aprendizaje = st.session_state["consulta_aprendizaje_normativo_msg"]

            if str(msg_aprendizaje).startswith("No se pudo guardar"):
                st.warning(msg_aprendizaje)
            elif str(msg_aprendizaje).startswith("Este aprendizaje ya estaba registrado"):
                st.info(msg_aprendizaje)
            else:
                st.caption(f"✅ {msg_aprendizaje}")

        generar_descarga_txt(
            nombre_base="Consulta_Normativa",
            contenido=st.session_state["respuesta_consulta_norma"],
            label="💾 Descargar respuesta"
        )

    st.divider()

    # =========================================================
    # BLOQUE 2 - CHATBOT NORMATIVO
    # =========================================================

    # Limpieza única de historial visible heredado.
    # La consulta puntual queda como contexto oculto, pero no aparece en el chat.
    if st.session_state.get("chat_normativo_ui_version") != "chat_invap_moderno_v5":
        st.session_state["chat_normativo_mensajes"] = []
        st.session_state["chat_normativo_reset_counter"] = st.session_state.get("chat_normativo_reset_counter", 0) + 1
        st.session_state["chat_normativo_ui_version"] = "chat_invap_moderno_v5"

    st.markdown("### 2. Chatbot normativo")
    st.write("")
    st.write("")
    st.write("")
    chat_input_key = f"chat_normativo_input_{st.session_state.get('chat_normativo_reset_counter', 0)}"

    pregunta_chat = st.text_area(
        "Consulta técnica",
        value="",
        height=92,
        label_visibility="collapsed",
        placeholder="Escriba una consulta o repregunta técnica..." ,
        key=chat_input_key
    )
    col_chat_spacer, col_chat_send = st.columns([6.5, 1.25])

    with col_chat_send:
        enviar_chat = st.button(
            "Enviar",
            width="stretch",
            key="chat_normativo_send_compacto"
        )

    if enviar_chat:
        pregunta_chat_limpia = pregunta_chat.strip()

        if not pregunta_chat_limpia:
            st.warning("Escriba una consulta antes de enviar.")
        else:
            st.session_state["chat_normativo_mensajes"].append({
                "role": "user",
                "content": pregunta_chat_limpia
            })

            try:
                with st.spinner("Analizando consulta normativa..."):
                    respuesta_chat = st.session_state["motor"].responder_chatbot_normativo(
                        pregunta=pregunta_chat_limpia,
                        lista_normas=st.session_state["lista_normas"],
                        historial=st.session_state["chat_normativo_mensajes"],
                        contexto_consulta=st.session_state.get("contexto_ultima_consulta_normativa", {})
                    )

                    st.session_state["chat_normativo_mensajes"].append({
                        "role": "assistant",
                        "content": respuesta_chat
                    })

                    st.session_state["chat_normativo_reset_counter"] = st.session_state.get("chat_normativo_reset_counter", 0) + 1
                    st.rerun()

            except Exception as e:
                st.error(f"No se pudo responder desde el chatbot normativo: {e}")

    st.write("")

    st.markdown("#### Conversación técnica")

    mensajes = st.session_state.get("chat_normativo_mensajes", [])

    with st.container(height=500, border=False):
        if not mensajes:
            st.markdown(
                """
                <div class="invap-chat-empty">
                    <strong>Chat listo.</strong><br>
                    Escriba una consulta técnica para iniciar la conversación.
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            for msg in mensajes[-20:]:
                rol = msg.get("role", "assistant")
                avatar = "👷" if rol == "user" else "🤖"
                nombre = "user" if rol == "user" else "assistant"

                with st.chat_message(nombre, avatar=avatar):
                    st.markdown(msg.get("content", ""))

    st.write("")
    col_clear_left, col_clear_mid, col_clear_right = st.columns([2.2, 1.15, 2.2])

    with col_clear_mid:
        if st.button(
            "Limpiar chat",
            width="stretch",
            key="chat_normativo_clear_compacto"
        ):
            st.session_state["chat_normativo_mensajes"] = []
            st.session_state["chat_normativo_reset_counter"] = st.session_state.get("chat_normativo_reset_counter", 0) + 1
            st.rerun()

def render_anotaciones():
    st.markdown("""
    <style>
    /* Ajustes específicos para la sección Anotaciones */
    div[data-testid="stVerticalBlock"]:has(textarea[aria-label="Nueva anotación"]) textarea {
        min-height: 132px !important;
    }

    div[data-testid="stVerticalBlock"]:has(textarea[aria-label="Nueva anotación"]) .stButton > button {
        min-height: 48px !important;
        height: 48px !important;
        font-size: 0.92rem !important;
        padding: 0.45rem 0.75rem !important;
        border-radius: 14px !important;
    }

    div[data-testid="stVerticalBlock"]:has(textarea[aria-label="Nueva anotación"]) [data-testid="column"] {
        padding-left: 0.25rem !important;
        padding-right: 0.25rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="big-section-title">🗒️ Anotaciones</div>', unsafe_allow_html=True)
    st.caption("Puede guardar múltiples anotaciones y descargarlas cuando quiera en formato Markdown.")

    col_audio, col_manual = st.columns([1, 1.5])

    with col_audio:
        st.markdown("### Entrada por audio")

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
                    st.session_state["anotacion_reset_counter"] += 1

                    st.rerun()

            except Exception as e:
                st.error(f"No se pudo transcribir la anotación: {e}")

    with col_manual:
        st.markdown("### Entrada manual")

        nota_key = f"nueva_anotacion_{st.session_state['anotacion_reset_counter']}"
        nueva_nota = st.text_area(
            "Nueva anotación",
            value=st.session_state.get("texto_anotacion", ""),
            height=170,
            placeholder="Escriba aquí observaciones, pendientes, ideas o notas de campo...",
            key=nota_key,
            label_visibility="collapsed"
        )

        st.session_state["texto_anotacion"] = nueva_nota

        col_note_1, col_note_2, col_note_3 = st.columns([0.9, 0.9, 0.9])

        with col_note_1:
            if st.button("➕ Agregar anotación", width="stretch"):
                if not nueva_nota.strip():
                    st.warning("Escriba o dicte una anotación antes de agregar.")
                else:
                    st.session_state["anotaciones"].append({
                        "fecha": ahora_argentina().strftime("%d/%m/%Y %H:%M"),
                        "texto": nueva_nota.strip()
                    })
                    st.session_state["texto_anotacion"] = ""
                    st.session_state["audio_anotacion_procesado"] = False
                    st.session_state["anotacion_reset_counter"] += 1
                    st.success("Anotación agregada.")
                    st.rerun()

        with col_note_2:
            if st.button("🧹 Limpiar entrada", width="stretch"):
                limpiar_entrada_anotacion()

        with col_note_3:
            if st.button("🗑️ Borrar todas", width="stretch"):
                limpiar_anotaciones_completas()

    st.write("")

    cantidad = len(st.session_state["anotaciones"])
    st.info(f"Cantidad de anotaciones: {cantidad}")

    if st.session_state["anotaciones"]:
        col_desc1, col_desc2 = st.columns([1, 3])
        with col_desc1:
            md = anotaciones_a_markdown(st.session_state["anotaciones"])
            generar_descarga_markdown(
                nombre_base="Anotaciones_Inspeccion",
                contenido_md=md,
                label="⬇️ Descargar MD"
            )

        st.markdown("### Historial")
        for i, nota in enumerate(st.session_state["anotaciones"], start=1):
            fecha_nota = nota.get("fecha", "")
            texto_nota = nota.get("texto", "")
            st.markdown(
                f"""
                <div class="note-box">
                    <strong>Nota {i}</strong><br>
                    <span class="small-muted">{fecha_nota}</span>
                    <p>{texto_nota}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("Todavía no hay anotaciones cargadas.")


def render_qa():
    st.markdown("""
    <style>
    /* Ajustes específicos para Corrección de informes FE-44 / QA */
    div[data-testid="stVerticalBlock"]:has(textarea[aria-label="O pegar texto del informe manualmente"]) textarea {
        min-height: 150px !important;
    }

    div[data-testid="stVerticalBlock"]:has(textarea[aria-label="Instrucción específica para este informe"]) textarea {
        min-height: 120px !important;
    }

    div[data-testid="stVerticalBlock"]:has(textarea[aria-label="Instrucción específica para este informe"]) .stButton > button {
        min-height: 50px !important;
        height: 50px !important;
        font-size: 0.95rem !important;
        padding: 0.45rem 0.85rem !important;
        border-radius: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="big-section-title">✍️ Corrección de informes FE-44 / QA</div>', unsafe_allow_html=True)

    st.subheader("Agente corrector de informes técnicos")
    st.write(
        "Cargue un informe PDF o Word, o pegue texto manualmente, para validar estructura FE-44, "
        "consistencia técnica y redacción profesional."
    )

    modo_revision = st.selectbox(
        "Modo de análisis",
        [
            "Revisión técnica completa",
            "Auditoría estructural FE-44",
            "Corrección de redacción",
            "Consistencia técnica",
            "Resumen ejecutivo y datos faltantes"
        ]
    )

    archivo_key = f"qa_archivo_{st.session_state['qa_reset_counter']}"
    archivo_qa = st.file_uploader(
        "Subir informe PDF o Word",
        type=["pdf", "docx"],
        key=archivo_key
    )

    texto_manual = st.text_area(
        "O pegar texto del informe manualmente",
        value="",
        height=150,
        placeholder="Pegue aquí el texto del informe si no desea subir un archivo...",
        label_visibility="collapsed"
    )

    prompt_qa = st.text_area(
        "Instrucción específica para este informe",
        value=(
            "Indicar qué aspecto específico querés revisar. Por ejemplo: validar formato FE-44, consistencia técnica, redacción formal, "
            "ortografía, datos faltantes y coherencia entre introducción, desarrollo y conclusión."
        ),
        height=115,
        label_visibility="collapsed"
    )

    col_qa_spacer1, col_qa_btn, col_qa_spacer2 = st.columns([0.18, 1, 0.18])

    with col_qa_btn:
        analizar_qa = st.button("✍️ Analizar / corregir informe", width="stretch")

    if analizar_qa:
        if not archivo_qa and not texto_manual.strip():
            st.warning("Suba un PDF/DOCX o pegue texto del informe para analizar.")
        else:
            try:
                with st.spinner("Analizando informe FE-44..."):
                    instruccion_final = (
                        f"Modo de revisión seleccionado: {modo_revision}.\n"
                        f"Instrucción adicional: {prompt_qa}"
                    )

                    if texto_manual.strip():
                        res_qa = st.session_state["motor"].analizar_texto_qa(
                            texto_manual.strip(),
                            instruccion_final
                        )

                    elif archivo_qa:
                        nombre_archivo = archivo_qa.name.lower()
                        contenido = archivo_qa.read()

                        if nombre_archivo.endswith(".pdf"):
                            res_qa = st.session_state["motor"].analizar_pdf_qa(
                                contenido,
                                instruccion_final
                            )

                        elif nombre_archivo.endswith(".docx"):
                            res_qa = st.session_state["motor"].analizar_docx_qa(
                                contenido,
                                instruccion_final
                            )

                        else:
                            res_qa = "Formato de archivo no soportado. Use PDF o DOCX."

                    st.session_state["qa_resultado"] = res_qa

            except Exception as e:
                st.error(f"No se pudo analizar/corregir el informe: {e}")

    st.write("")

    if st.session_state.get("qa_resultado"):
        st.success("Análisis completado")
        st.markdown(st.session_state["qa_resultado"])

        generar_descarga_txt(
            nombre_base="Correccion_Informe_FE44",
            contenido=st.session_state["qa_resultado"],
            label="💾 Descargar corrección"
        )
    else:
        st.info("El resultado de la corrección aparecerá aquí.")




# =========================================================
# AJUSTE FINO SIDEBAR INVAP
# =========================================================
st.markdown("""
<style>
/* Logo limpio, sin tarjeta ni borde redondeado */
section[data-testid="stSidebar"] [data-testid="stImage"] {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0 !important;
    margin: 0 0 26px 0 !important;
    box-shadow: none !important;
}

section[data-testid="stSidebar"] [data-testid="stImage"] img {
    border-radius: 0 !important;
    box-shadow: none !important;
}

/* Separadores más sutiles */
section[data-testid="stSidebar"] hr {
    border: none !important;
    border-top: 1px solid rgba(255,255,255,0.18) !important;
    margin: 20px 0 !important;
}

/* Contenedor del listado */
section[data-testid="stSidebar"] [role="radiogroup"] {
    display: flex !important;
    flex-direction: column !important;
    gap: 10px !important;
}

/* Cada opción del menú como tarjeta/botón */
section[data-testid="stSidebar"] [role="radiogroup"] label {
    background: rgba(255,255,255,0.085) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 16px !important;
    padding: 13px 14px !important;
    margin: 0 !important;
    min-height: 50px !important;
    display: flex !important;
    align-items: center !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
    transition: all 0.16s ease-in-out !important;
}

/* Hover de opciones */
section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background: rgba(255,255,255,0.16) !important;
    border-color: rgba(255,255,255,0.32) !important;
    transform: translateY(-1px);
}

/* Texto del menú */
section[data-testid="stSidebar"] [role="radiogroup"] label p,
section[data-testid="stSidebar"] [role="radiogroup"] label span,
section[data-testid="stSidebar"] [role="radiogroup"] label div {
    font-size: 1.02rem !important;
    font-weight: 780 !important;
    color: #FFFFFF !important;
}

/* Radio button más integrado visualmente */
section[data-testid="stSidebar"] [role="radiogroup"] label [data-testid="stMarkdownContainer"] {
    margin-left: 4px !important;
}

/* Botón actualizar como acción inferior */
section[data-testid="stSidebar"] .stButton > button {
    min-height: 58px !important;
    border-radius: 18px !important;
    background: linear-gradient(135deg, #007A3D 0%, #004B35 100%) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    box-shadow: 0 8px 18px rgba(0,0,0,0.16) !important;
}

/* Quita restos del recuadro anterior si quedó definido */
.sidebar-brand {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)



# =========================================================
# AJUSTES FINOS UI INVAP
# =========================================================
st.markdown("""
<style>
/* =========================
   CORRECCIÓN HEADER SUPERIOR
   ========================= */
[data-testid="stAppViewContainer"] .main .block-container {
    padding-top: 2.85rem !important;
}

.invap-header-card {
    margin-top: 0.75rem !important;
}

/* =========================
   SIDEBAR - LOGO MEJORADO
   ========================= */
section[data-testid="stSidebar"] [data-testid="stImage"] {
    background: rgba(221,242,232,0.06) !important;
    border: 1.6px solid rgba(221,242,232,0.30) !important;
    border-radius: 22px !important;
    padding: 12px !important;
    margin: 4px 0 22px 0 !important;
    box-shadow: none !important;
}

section[data-testid="stSidebar"] [data-testid="stImage"] img {
    border-radius: 16px !important;
    display: block !important;
}

/* Sidebar un poco más prolija */
section[data-testid="stSidebar"] {
    padding-top: 0.2rem !important;
}

/* =========================
   FOOTER FIJO INFERIOR DERECHO
   ========================= */
.invap-fixed-footer {
    position: fixed;
    right: 22px;
    bottom: 10px;
    z-index: 999999;
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
    opacity: 0.98;
}

.invap-fixed-footer img {
    max-width: 190px;
    height: auto;
    display: block;
    filter: drop-shadow(0 3px 8px rgba(0,0,0,0.18));
}

.invap-fixed-footer-text {
    color: #FFFFFF;
    background: rgba(0, 75, 53, 0.88);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 14px;
    padding: 8px 14px;
    font-size: 0.88rem;
    font-weight: 900;
    letter-spacing: 0.02em;
    box-shadow: 0 6px 14px rgba(0,0,0,0.18);
}

/* Responsive del footer */
@media (max-width: 900px) {
    .invap-fixed-footer {
        right: 12px;
        bottom: 8px;
    }
    .invap-fixed-footer img {
        max-width: 135px;
    }
}

/* Un poco más de aire debajo para que nada quede muy justo */
.block-container {
    padding-bottom: 3.5rem !important;
}
</style>
""", unsafe_allow_html=True)



# =========================================================
# CONTROLADOR VISUAL FOOTER / SIDEBAR
# =========================================================
def render_footer_visibility_controller():
    components.html(
        """
        <script>
        (function() {
            function isVisible(el) {
                if (!el) return false;
                const rect = el.getBoundingClientRect();
                const style = window.parent.getComputedStyle(el);
                return rect.width > 0 && rect.height > 0 &&
                       style.display !== "none" &&
                       style.visibility !== "hidden" &&
                       style.opacity !== "0";
            }

            function updateFooterVisibility() {
                try {
                    const doc = window.parent.document;
                    const footer = doc.querySelector(".invap-fixed-footer");
                    if (!footer) return;

                    const sidebar = doc.querySelector('section[data-testid="stSidebar"]');

                    const buttons = Array.from(doc.querySelectorAll("button, [role='button']"));
                    const openSidebarButton = buttons.find(btn => {
                        const aria = (btn.getAttribute("aria-label") || "").toLowerCase();
                        const title = (btn.getAttribute("title") || "").toLowerCase();
                        const txt = (btn.textContent || "").trim();

                        return (
                            aria.includes("open sidebar") ||
                            aria.includes("expand sidebar") ||
                            aria.includes("show sidebar") ||
                            title.includes("open sidebar") ||
                            title.includes("expand sidebar") ||
                            txt === "»" ||
                            txt === ">>" ||
                            txt.includes("»")
                        );
                    });

                    let sidebarCollapsed = false;

                    if (!sidebar) {
                        sidebarCollapsed = true;
                    } else {
                        const rect = sidebar.getBoundingClientRect();
                        const style = window.parent.getComputedStyle(sidebar);

                        sidebarCollapsed =
                            rect.width < 80 ||
                            style.display === "none" ||
                            style.visibility === "hidden" ||
                            sidebar.getAttribute("aria-expanded") === "false";
                    }

                    const hasOpenButtonVisible = openSidebarButton && isVisible(openSidebarButton);

                    if (sidebarCollapsed || hasOpenButtonVisible) {
                        footer.style.setProperty("display", "flex", "important");
                    } else {
                        footer.style.setProperty("display", "none", "important");
                    }
                } catch (e) {
                    console.log("Footer/sidebar visibility controller:", e);
                }
            }

            updateFooterVisibility();

            const doc = window.parent.document;
            const observer = new MutationObserver(updateFooterVisibility);
            observer.observe(doc.body, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ["style", "class", "aria-expanded", "aria-label", "title"]
            });

            setInterval(updateFooterVisibility, 600);
        })();
        </script>
        """,
        height=0,
        width=0,
    )



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
    render_logo_invap_sidebar(width=255)

    st.write("---")

    current_menu = st.session_state.get("menu_principal", "Dashboard operativo")
    if current_menu not in MENU_ITEMS:
        current_menu = "Dashboard operativo"

    menu = st.radio(
        "Navegación",
        MENU_ITEMS,
        index=MENU_ITEMS.index(current_menu),
        label_visibility="collapsed"
    )
    st.session_state["menu_principal"] = menu

    st.write("---")


    if st.button("🧹 Limpiar consulta y análisis", width="stretch"):
        limpiar_consulta_y_analisis()

    if st.session_state.get("sync_msg"):
        st.success(st.session_state["sync_msg"])


# =========================================================
# CABECERA
# =========================================================
if st.session_state["menu_principal"] == "Dashboard operativo":
    st.markdown("""
    <div class="invap-header-card">
        <div class="invap-header-title">
            Sistema Inteligente de Gestión de Integridad
        </div>
        <div class="invap-header-subtitle">
            Asistente de Inspección | Hallazgos técnicos, consulta normativa, trazabilidad documental y QA de informes
        </div>
    </div>
    """, unsafe_allow_html=True)


# =========================================================
# ROUTER PRINCIPAL
# =========================================================
if st.session_state["menu_principal"] == "Dashboard operativo":
    registros = cargar_registros_inspeccion(creds, project_id)
    df_registros = registros_a_dataframe(registros)
    render_dashboard(df_registros)

elif st.session_state["menu_principal"] == "Consultas Normativas":
    render_consultas_normativas()

elif st.session_state["menu_principal"] == "Anotaciones":
    render_anotaciones()

elif st.session_state["menu_principal"] == "Registro de hallazgo":
    render_registro_hallazgo(creds, project_id)

elif st.session_state["menu_principal"] == "Corrección Informes FE-44":
    render_qa()



# =========================================================
# AJUSTE FOOTER LOGO INVAP CORRECTO
# =========================================================
st.markdown("""
<style>
/* Footer inferior derecho con logo verde sobre fondo blanco */
.invap-fixed-footer {
    position: fixed !important;
    right: 22px !important;
    bottom: 14px !important;
    z-index: 999999 !important;
    pointer-events: none !important;

    background: #FFFFFF !important;
    border: 1px solid rgba(207, 227, 218, 0.95) !important;
    border-radius: 12px !important;
    padding: 8px 12px !important;

    display: flex !important;
    align-items: center !important;
    justify-content: center !important;

    box-shadow: 0 6px 18px rgba(0, 75, 53, 0.14) !important;
    opacity: 0.98 !important;
}

.invap-fixed-footer img {
    max-width: 180px !important;
    height: auto !important;
    display: block !important;
    filter: none !important;
    border-radius: 0 !important;
}

.invap-fixed-footer-text {
    color: #0C5A43 !important;
    background: #FFFFFF !important;
    font-size: 0.88rem !important;
    font-weight: 900 !important;
    letter-spacing: 0.02em !important;
}

/* Evita que el contenido tape el footer */
.block-container {
    padding-bottom: 4rem !important;
}

@media (max-width: 900px) {
    .invap-fixed-footer {
        right: 12px !important;
        bottom: 10px !important;
        padding: 6px 9px !important;
    }

    .invap-fixed-footer img {
        max-width: 135px !important;
    }
}
</style>
""", unsafe_allow_html=True)



# =========================================================
# FOOTER INVAP CONTROLADO POR JS
# =========================================================
st.markdown("""
<style>
.invap-fixed-footer {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# PIE
# =========================================================
render_footer_invap()
render_footer_visibility_controller()

# =========================================================
# FOOTER SOLO CON SIDEBAR OCULTA
# =========================================================
st.markdown("""
<style>
/* 
   El logo inferior derecho queda oculto cuando la sidebar está visible.
   Se muestra únicamente cuando Streamlit deja visible el control de sidebar colapsada.
*/
.invap-fixed-footer {
    display: none !important;
}

/* Sidebar colapsada: Streamlit muestra el control para volver a abrirla */
body:has([data-testid="stSidebarCollapsedControl"]) .invap-fixed-footer,
body:has(button[title="Open sidebar"]) .invap-fixed-footer,
body:has(button[aria-label="Open sidebar"]) .invap-fixed-footer,
body:has(button[aria-label="Expand sidebar"]) .invap-fixed-footer {
    display: flex !important;
}

/* Compatibilidad extra por si cambia el nombre del control */
body:has([data-testid*="Collapsed"]) .invap-fixed-footer,
body:has([aria-label*="sidebar" i]) .invap-fixed-footer {
    display: flex !important;
}
</style>
""", unsafe_allow_html=True)

st.divider()
st.caption(f"© {ahora_argentina().year} INVAP Ingeniería S.A. | Gabriel")
