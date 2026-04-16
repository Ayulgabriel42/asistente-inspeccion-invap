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
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 1.5rem;
}
.big-section-title {
    font-size: 1.35rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}
.small-muted {
    color: #777;
    font-size: 0.92rem;
}
.note-box {
    padding: 0.7rem;
    border-radius: 0.5rem;
    background: rgba(120,120,120,0.08);
    margin-bottom: 0.6rem;
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


def init_session_state():
    defaults = {
        # Base
        "lista_normas": [],
        "motor": None,
        "menu_principal": "Dashboard",

        # Registro de Hallazgo
        "input_hallazgo_usuario": "",
        "audio_procesado": False,
        "ultimo_informe": None,
        "norma_actual": None,
        "hallazgo_actual": "",

        # Reset de widgets visuales
        "camara_reset_counter": 0,
        "upload_reset_counter": 0,
        "consulta_upload_reset_counter": 0,

        # Consultas Normativas
        "consulta_norma_input": "",
        "respuesta_consulta_norma": "",

        # Anotaciones
        "anotaciones": [],

        # QA
        "qa_resultado": "",
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def limpiar_inspeccion_completa():
    """
    Resetea todo lo relacionado con la inspección actual:
    texto, audio, informe, norma, imágenes, consulta y resultados.
    """
    st.session_state["input_hallazgo_usuario"] = ""
    st.session_state["audio_procesado"] = False
    st.session_state["ultimo_informe"] = None
    st.session_state["norma_actual"] = None
    st.session_state["hallazgo_actual"] = ""

    st.session_state["consulta_norma_input"] = ""
    st.session_state["respuesta_consulta_norma"] = ""

    st.session_state["camara_reset_counter"] += 1
    st.session_state["upload_reset_counter"] += 1
    st.session_state["consulta_upload_reset_counter"] += 1

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

            audio_key = f"audio_hallazgo_{st.session_state['camara_reset_counter']}"
            audio = st.audio_input("Dictar hallazgo", key=audio_key)

            if audio and not st.session_state.get("audio_procesado", False):
                try:
                    st.session_state["input_hallazgo_usuario"] = st.session_state["motor"].transcribir_audio(
                        audio.read(),
                        audio.type
                    )
                    st.session_state["audio_procesado"] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo transcribir el audio: {e}")

            hallazgo = st.text_area(
                "Descripción técnica",
                value=st.session_state.get("input_hallazgo_usuario", ""),
                height=170,
                placeholder="Ej.: Se observa eslinga con alambres cortados en ojal..."
            )

            st.write("---")

            cam_key = f"cam_input_{st.session_state['camara_reset_counter']}"
            up_key = f"file_uploader_{st.session_state['upload_reset_counter']}"

            foto_c = st.camera_input("Capturar evidencia", key=cam_key)
            foto_a = st.file_uploader(
                "O cargar imagen",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key=up_key
            )

            lista_imgs_motor = []

            if foto_c:
                try:
                    lista_imgs_motor.append((foto_c.read(), foto_c.type))
                except Exception:
                    pass

            if foto_a:
                for f in foto_a:
                    try:
                        lista_imgs_motor.append((f.read(), f.type))
                    except Exception:
                        pass

            if st.button("🚀 GENERAR INFORME TÉCNICO", use_container_width=True):
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

            if st.button("🔄 NUEVA INSPECCIÓN", use_container_width=True):
                limpiar_inspeccion_completa()

        with c2:
            st.subheader("Previsualización y Refinamiento")

            if st.session_state.get("ultimo_informe"):
                st.info(f"**Norma detectada:** {st.session_state.get('norma_actual') or 'No determinada'}")
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

        pregunta = st.text_area(
            "Escriba su consulta",
            value=st.session_state.get("consulta_norma_input", ""),
            height=130,
            placeholder="Ej.: ¿Qué norma podría aplicar si se detectan alambres cortados en una eslinga?"
        )

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
                    lista_imgs_consulta.append((f.read(), f.type))
                except Exception:
                    pass

        col_cons_1, col_cons_2 = st.columns([1, 1])

        with col_cons_1:
            if st.button("📚 CONSULTAR NORMA", use_container_width=True):
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
            if st.button("🧹 LIMPIAR CONSULTA", use_container_width=True):
                st.session_state["consulta_norma_input"] = ""
                st.session_state["respuesta_consulta_norma"] = ""
                st.session_state["consulta_upload_reset_counter"] += 1
                st.rerun()

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

        nueva_nota = st.text_area(
            "Nueva anotación",
            height=140,
            placeholder="Escriba aquí observaciones, pendientes, ideas o notas de campo..."
        )

        col_note_1, col_note_2, col_note_3 = st.columns([1, 1, 1])

        with col_note_1:
            if st.button("➕ AGREGAR ANOTACIÓN", use_container_width=True):
                if not nueva_nota.strip():
                    st.warning("Escriba una anotación antes de agregar.")
                else:
                    st.session_state["anotaciones"].append({
                        "fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "texto": nueva_nota.strip()
                    })
                    st.success("Anotación agregada.")

        with col_note_2:
            if st.button("🗑️ BORRAR TODAS", use_container_width=True):
                st.session_state["anotaciones"] = []
                st.rerun()

        with col_note_3:
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

    pdf_qa = st.file_uploader("Subir reporte PDF", type=["pdf"], key="qa_pdf")

    prompt_qa = st.text_area(
        "Instrucción de auditoría",
        value="Valida formato FE-44 y consistencia técnica del reporte.",
        height=120
    )

    if st.button("🔍 AUDITAR REPORTE", use_container_width=True):
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