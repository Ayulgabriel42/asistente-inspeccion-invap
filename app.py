import os
import re
import json
import uuid
import base64
import datetime
import unicodedata

import streamlit as st
import pandas as pd

from google.cloud import storage
from google.oauth2 import service_account

from engine import InspeccionEngine


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
BUCKET_NAME = "invap-asistente-normas"
REGISTROS_PREFIX = "registros_inspecciones"

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
    "Alto",
    "Medio",
    "Bajo"
]

ESTADOS_GESTION = [
    "Pendiente",
    "En análisis",
    "Cerrado"
]


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
:root {
    --invap-green: #007A3D;
    --invap-green-dark: #005E31;
    --invap-green-soft: #E8F4EE;
    --text-main: #0F172A;
    --text-muted: #64748B;
    --border-soft: #D9E2E8;
    --bg-app: #F6F8FA;
    --bg-card: #FFFFFF;
    --danger-soft: #FEE2E2;
    --danger-text: #7F1D1D;
    --warning-soft: #FEF3C7;
    --warning-text: #78350F;
}

.stApp {
    background-color: var(--bg-app) !important;
}

.block-container {
    padding-top: 1.4rem !important;
    padding-bottom: 2rem !important;
    max-width: 1180px !important;
}

html, body, [class*="css"] {
    font-size: 16px !important;
    color: var(--text-main) !important;
}

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

.small-muted,
[data-testid="stCaptionContainer"],
.stCaptionContainer {
    color: var(--text-muted) !important;
    font-size: 0.95rem !important;
}

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

label,
.stTextInput label,
.stTextArea label,
.stSelectbox label,
.stFileUploader label {
    font-size: 0.98rem !important;
    font-weight: 700 !important;
    color: #1E293B !important;
}

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

.stSelectbox div[data-baseweb="select"] > div {
    min-height: 48px !important;
    display: flex !important;
    align-items: center !important;
}

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

a button {
    min-height: 48px !important;
    font-size: 0.98rem !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.14) !important;
}

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

.attention-card {
    padding: 1rem !important;
    border-radius: 12px !important;
    background: #FFFFFF !important;
    border: 1px solid var(--border-soft) !important;
    box-shadow: 0 1px 5px rgba(15,23,42,0.06) !important;
    margin-bottom: 0.7rem !important;
}

.attention-critical {
    border-left: 6px solid #DC2626 !important;
}

.attention-warning {
    border-left: 6px solid #F59E0B !important;
}

.attention-ok {
    border-left: 6px solid var(--invap-green) !important;
}

.dashboard-box {
    padding: 1rem !important;
    border-radius: 12px !important;
    background: #FFFFFF !important;
    border: 1px solid var(--border-soft) !important;
    box-shadow: 0 1px 5px rgba(15,23,42,0.06) !important;
}

[data-testid="stFileUploader"] {
    background-color: #FFFFFF !important;
    border: 1.5px dashed #94A3B8 !important;
    border-radius: 10px !important;
    padding: 0.9rem !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: var(--invap-green) !important;
}

[data-testid="stCameraInput"],
[data-testid="stAudioInput"] {
    background-color: #FFFFFF !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 10px !important;
    padding: 0.9rem !important;
}

.stAlert {
    font-size: 0.96rem !important;
    border-radius: 10px !important;
    border: 1px solid var(--border-soft) !important;
}

[data-testid="metric-container"] {
    background-color: #FFFFFF !important;
    border: 1px solid var(--border-soft) !important;
    padding: 1rem !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 5px rgba(15,23,42,0.06) !important;
}

p, div, span {
    line-height: 1.45;
}

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
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    equipo_limpio = sanitizar_para_archivo(equipo)
    corto = uuid.uuid4().hex[:6].upper()
    return f"INS-{timestamp}-{equipo_limpio}-{corto}"


def guardar_registro_inspeccion(creds, project_id, registro):
    client = get_storage_client(creds, project_id)
    bucket = client.bucket(BUCKET_NAME)

    fecha = datetime.datetime.now()
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


def registros_a_dataframe(registros):
    columnas = [
        "id_informe",
        "fecha_hora",
        "region",
        "cliente",
        "equipo",
        "tipo_equipo",
        "sistema_afectado",
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
        "criticidad_inspeccion": "Medio",
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

        # Consultas Normativas
        "consulta_norma_input": "",
        "respuesta_consulta_norma": "",
        "audio_consulta_procesado": False,

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

    incrementar_resets()
    st.rerun()


def limpiar_consulta_normativa():
    st.session_state["consulta_norma_input"] = ""
    st.session_state["respuesta_consulta_norma"] = ""
    st.session_state["audio_consulta_procesado"] = False

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


def render_dashboard(df):
    st.markdown('<div class="big-section-title">📊 Dashboard operativo</div>', unsafe_allow_html=True)
    st.caption(
        "Indicadores construidos únicamente a partir de informes archivados por los usuarios. "
        "No se utilizan datos simulados."
    )

    if df.empty:
        st.info(
            "Todavía no hay informes archivados. Genere un informe desde "
            "'Asistente de Inspección' y presione 'ARCHIVAR INFORME' para comenzar a construir el Dashboard."
        )
        return

    st.markdown("### Filtros")

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
    criticos_abiertos = len(df_f[(df_f["criticidad"] == "Crítico") & (df_f["estado"] != "Cerrado")])
    pendientes = len(df_f[df_f["estado"] != "Cerrado"])
    equipos_afectados = df_f["equipo"].nunique()
    regiones_activas = df_f["region"].nunique()

    st.write("")
    st.markdown("### Indicadores principales")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Informes archivados", total)
    m2.metric("Críticos abiertos", criticos_abiertos)
    m3.metric("Pendientes / análisis", pendientes)
    m4.metric("Equipos afectados", equipos_afectados)
    m5.metric("Regiones activas", regiones_activas)

    st.write("")
    st.markdown("### 🔴 Atención hoy")

    if criticos_abiertos > 0:
        st.markdown(
            f"""
            <div class="attention-card attention-critical">
                <strong>Hallazgos críticos abiertos</strong><br>
                Existen <strong>{criticos_abiertos}</strong> hallazgos críticos sin cierre.
                Se recomienda priorizar revisión técnica y seguimiento documental.
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
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("### Hallazgos por sistema")
        sistema_counts = df_f["sistema_afectado"].value_counts()
        if not sistema_counts.empty:
            st.bar_chart(sistema_counts, height=280)
        else:
            st.info("Sin datos de sistema.")

    with col_g2:
        st.markdown("### Hallazgos por región")
        region_counts = df_f["region"].value_counts()
        if not region_counts.empty:
            st.bar_chart(region_counts, height=280)
        else:
            st.info("Sin datos de región.")

    col_g3, col_g4 = st.columns(2)

    with col_g3:
        st.markdown("### Estado de gestión")
        estado_counts = df_f["estado"].value_counts()
        if not estado_counts.empty:
            st.bar_chart(estado_counts, height=260)
        else:
            st.info("Sin datos de estado.")

    with col_g4:
        st.markdown("### Normas más utilizadas")
        normas_counts = df_f["norma_detectada"].dropna().apply(nombre_norma_limpio).value_counts().head(10)
        if not normas_counts.empty:
            st.bar_chart(normas_counts, height=260)
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

    if st.button("🔄 Actualizar datos", width="stretch"):
        st.rerun()


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
    st.caption("Asistencia técnica para hallazgos, consultas normativas, archivo de informes y auditoría documental")


# =========================================================
# MÓDULO: DASHBOARD
# =========================================================
if st.session_state["menu_principal"] == "Dashboard":
    registros = cargar_registros_inspeccion(creds, project_id)
    df_registros = registros_a_dataframe(registros)
    render_dashboard(df_registros)


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
            st.subheader("Datos de inspección")

            region = st.selectbox(
                "Región / Base",
                REGIONES,
                index=index_seguro(REGIONES, st.session_state.get("region_inspeccion", "Comodoro Rivadavia")),
                key="region_inspeccion"
            )

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
                st.caption("Para Neuquén, Bariloche u otra región, el cliente se ingresa manualmente hasta cargar catálogos reales.")
                cliente_final = st.text_input(
                    "Cliente",
                    key="cliente_manual_inspeccion",
                    placeholder="Ej.: YPF, PAE, empresa local..."
                ).strip()

            equipo = st.text_input(
                "Equipo / Identificación",
                key="equipo_inspeccion",
                placeholder="Ej.: DLS-343, PAE-007, SAI-212"
            ).strip()

            tipo_equipo = st.selectbox(
                "Tipo de equipo",
                TIPOS_EQUIPO,
                index=index_seguro(TIPOS_EQUIPO, st.session_state.get("tipo_equipo_inspeccion", "Workover")),
                key="tipo_equipo_inspeccion"
            )

            sistema_afectado = st.selectbox(
                "Sistema afectado",
                SISTEMAS_AFECTADOS,
                index=index_seguro(SISTEMAS_AFECTADOS, st.session_state.get("sistema_afectado_inspeccion", "Estructura")),
                key="sistema_afectado_inspeccion"
            )

            criticidad = st.selectbox(
                "Criticidad",
                CRITICIDADES,
                index=index_seguro(CRITICIDADES, st.session_state.get("criticidad_inspeccion", "Medio")),
                key="criticidad_inspeccion"
            )

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
                "criticidad": criticidad,
                "estado": estado
            }

            st.write("---")
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
                            st.session_state["ruta_ultimo_archivo"] = ""

                    except Exception as e:
                        st.error(f"No se pudo generar el informe técnico: {e}")

            st.write("")

            if st.button("🔄 NUEVA INSPECCIÓN", width="stretch"):
                limpiar_inspeccion_completa()

        with c2:
            st.subheader("Previsualización, Refinamiento y Archivo")

            if st.session_state.get("ultimo_informe"):
                norma_visible = nombre_norma_limpio(st.session_state.get("norma_actual"))

                contexto = st.session_state.get("contexto_inspeccion_actual", {})

                st.info(
                    f"**Norma detectada:** {norma_visible}  \n"
                    f"**Región:** {contexto.get('region', '')} | "
                    f"**Cliente:** {contexto.get('cliente', '')} | "
                    f"**Equipo:** {contexto.get('equipo', '')} | "
                    f"**Criticidad:** {contexto.get('criticidad', '')}"
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

                col_down, col_archive = st.columns([1, 1])

                with col_down:
                    generar_descarga_txt(
                        nombre_base="Informe_INVAP",
                        contenido=st.session_state["ultimo_informe"],
                        label="💾 DESCARGAR INFORME"
                    )

                with col_archive:
                    if st.button("📁 ARCHIVAR INFORME", width="stretch"):
                        contexto = st.session_state.get("contexto_inspeccion_actual", {})
                        hallazgo_final = st.session_state.get("hallazgo_actual") or st.session_state.get("input_hallazgo_usuario", "")
                        informe_final = st.session_state.get("ultimo_informe", "")
                        norma_final = st.session_state.get("norma_actual", "")

                        faltantes = validar_contexto_archivo(
                            contexto=contexto,
                            hallazgo=hallazgo_final,
                            informe=informe_final,
                            norma=norma_final
                        )

                        if faltantes:
                            st.warning(
                                "Antes de archivar complete: "
                                + ", ".join(faltantes)
                            )
                        else:
                            try:
                                with st.spinner("Archivando informe en Google Cloud Storage..."):
                                    ahora = datetime.datetime.now()
                                    id_informe = generar_id_informe(contexto.get("equipo", ""))

                                    registro = {
                                        "id_informe": id_informe,
                                        "fecha_hora": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                                        "region": contexto.get("region", ""),
                                        "cliente": contexto.get("cliente", ""),
                                        "equipo": contexto.get("equipo", ""),
                                        "tipo_equipo": contexto.get("tipo_equipo", ""),
                                        "sistema_afectado": contexto.get("sistema_afectado", ""),
                                        "criticidad": contexto.get("criticidad", ""),
                                        "estado": contexto.get("estado", ""),
                                        "hallazgo_original": hallazgo_final,
                                        "norma_detectada": nombre_norma_limpio(norma_final),
                                        "informe_generado": informe_final,
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
                st.info("El informe técnico aparecerá aquí luego de procesar el hallazgo.")

    # -----------------------------------------------------
    # SUBTAB 2: CONSULTAS NORMATIVAS
    # -----------------------------------------------------
    with subtab2:
        st.subheader("Consultas Normativas")
        st.caption(
            "Realice una consulta libre por texto, audio o imagen para orientarse "
            "sobre en qué norma podría encuadrarse un caso."
        )

        st.markdown("#### Entrada por audio")

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

        st.markdown("#### Entrada manual")

        pregunta_key = f"consulta_norma_text_area_{st.session_state['consulta_reset_counter']}"
        pregunta = st.text_area(
            "Escriba o revise su consulta",
            value=st.session_state.get("consulta_norma_input", ""),
            height=130,
            placeholder="Ej.: ¿Qué norma podría aplicar si se detectan alambres cortados en una eslinga?",
            key=pregunta_key
        )

        st.session_state["consulta_norma_input"] = pregunta

        st.markdown("#### Evidencia visual opcional")

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
                if not pregunta.strip() and not lista_imgs_consulta:
                    st.warning("Ingrese una consulta por texto/audio o adjunte una imagen.")
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


# =========================================================
# MÓDULO: QA / AUDITORÍA
# =========================================================
elif st.session_state["menu_principal"] == "QA / Auditoría":
    st.markdown('<div class="big-section-title">🧪 QA / Auditoría</div>', unsafe_allow_html=True)

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

    if st.button("🧪 AUDITAR REPORTE", width="stretch"):
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
