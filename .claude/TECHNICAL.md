# Asistente de Inspección INVAP — Documentación Técnica y Funcional

**Última actualización:** 2026-06-24  
**Repo:** `Ayulgabriel42/asistente-inspeccion-invap` (rama `main`)  
**Desplegado en:** Streamlit Cloud — `/mount/src/asistente-inspeccion-invap/`

---

## Propósito de la app

Sistema inteligente de gestión de integridad para inspectores de campo de **INVAP Ingeniería S.A.**.  
Asiste en la inspección de equipos petroleros (pulling, workover, perforación) en la cuenca del Golfo San Jorge, principalmente Comodoro Rivadavia.

Funciones principales:
- Registrar hallazgos técnicos con clasificación normativa automática
- Consultar normas técnicas usando RAG sobre PDFs almacenados en GCS
- Verificar vigencia de normas en tiempo real mediante búsqueda web
- Gestionar anotaciones de campo con entrada por audio
- Corregir informes técnicos FE-44 con IA
- Dashboard operativo con KPIs de inspección

---

## Stack tecnológico

| Componente | Tecnología |
|-----------|-----------|
| Frontend / UI | Streamlit |
| IA generativa | Google Gemini (`gemini-3-flash-preview`) via `google-genai` SDK |
| Web search | Google Search Grounding (nativo en Gemini) |
| Embeddings | `models/gemini-embedding-001` via LangChain |
| Vector store | FAISS (local, cargado desde GCS) |
| Almacenamiento | Google Cloud Storage — bucket `invap-asistente-normas` |
| PDF | PyPDF, ReportLab |
| Auth | `google.oauth2.service_account` — `st.secrets["gcp_service_account"]` |
| Zona horaria | `America/Argentina/Buenos_Aires` |

---

## Archivos principales

```
app.py          — UI Streamlit, router de secciones, helpers de GCS (3594 líneas)
engine.py       — Clase InspeccionEngine, toda la lógica IA (2477 líneas)
requirements.txt
assets/
  Logo 1.jpg          — logo sidebar
  Logo 2.jpg          — logo header/footer
  favicon_invap_logo1.png
vectorstore_normas/   — índice FAISS local (si existe)
google-credentials.json — credenciales locales (NO está en git)
.claude/TECHNICAL.md  — este archivo
```

---

## Credenciales y configuración

**Streamlit Cloud:** `st.secrets["gcp_service_account"]` → dict con JSON de service account GCP.  
**Local:** archivo `google-credentials.json` en la raíz del proyecto.  
**API key Gemini:** `st.secrets["GEMINI_API_KEY"]` (o variable de entorno).

El `project_id` se extrae del JSON de la service account.

---

## Estructura de GCS (`invap-asistente-normas`)

```
registros_inspecciones/     — JSONs de hallazgos registrados
memoria_normativa/
  memoria_normativa_validada.json   — aprendizaje normativo validado por usuario
<norma>.pdf                 — PDFs de normas técnicas indexables
```

---

## Módulos / Menú (sidebar)

### 1. Dashboard operativo
- KPIs: total hallazgos, críticos, normas únicas, clientes activos
- Tabla filtrable por cliente, equipo, criticidad, estado, fecha
- Gráficos de distribución

**Función:** `render_dashboard(df)`

---

### 2. Consultas Normativas
Sección principal de consulta a normas. Flujo:

1. **Consulta puntual** — el usuario ingresa pregunta (texto, foto, audio)
2. Sistema busca en memoria normativa validada → si hay match, usa RAG sobre el PDF
3. Si no hay match, usa `consultar_normas_chat()` (sin PDF específico)
4. **Norma detectada** se muestra con `st.info()`
5. **Badge de vigencia** — llama a `verificar_vigencia_norma()` via Google Search Grounding
   - Verde: `✅ Norma VIGENTE — Última actualización: XXXX`
   - Amarillo: `⚠️ Norma REVISADA / REEMPLAZADA`
   - Gris: `ℹ️ Vigencia no determinada`
   - Resultado cacheado en `st.session_state[f"vigencia_{norma}"]`
6. **Chatbot normativo** — permite repreguntas sobre la última consulta
7. **Memoria normativa** — el usuario puede validar o corregir la norma detectada para aprendizaje futuro

**Función:** `render_consultas_normativas()`

---

### 3. Anotaciones
- Entrada por **audio** (micrófono o archivo) → transcripción con Gemini
- Entrada **manual** por texto
- Lista de anotaciones de sesión, descargable en Markdown

**Función:** `render_anotaciones()`

---

### 4. Registro de hallazgo
Flujo completo de inspección:

1. Contexto: cliente, equipo, sistema afectado, tipo inspección, región, criticidad
2. Hallazgo: texto libre + evidencia fotográfica (upload o cámara) + audio
3. Gemini clasifica la norma aplicable (híbrido: matriz determinística + IA)
4. Genera informe técnico estructurado
5. Permite refinamiento con comentarios del inspector
6. Guarda registro en GCS como JSON
7. Descarga en TXT, Markdown o PDF

**Función:** `render_registro_hallazgo(creds, project_id)`

---

### 5. Corrección Informes FE-44
- Carga de informe: PDF, DOCX, o texto pegado
- Instrucción específica del inspector
- Gemini analiza y corrige: estructura FE-44, consistencia técnica, redacción
- Resultado descargable

**Función:** `render_qa()`

---

## Constantes del dominio

```python
CLIENTES_COMODORO = [
    "DLS - Nova Energy", "Clear Petrolum", "San Antonio International",
    "AESA", "Pan American Energy", "Halliburton", "Tecpetrol", "Venver", "Otro"
]

TIPOS_EQUIPO = [
    "Pulling", "Workover", "Perforación", "Carretón",
    "BOP", "Acumulador", "Bomba de lodo", "Otro"
]

SISTEMAS_AFECTADOS = [
    "Estructura", "Sistema de izaje", "Control de pozo", "Bombas de lodo",
    "Seguridad", "Cuadro de maniobras", "Mesa rotary", "Sistema de potencia", "Otro"
]

CRITICIDADES = ["Crítico", "Mayor", "Menor"]
TIPOS_INSPECCION = ["Documental", "Visual", "Funcional"]
ESTADOS_GESTION = ["Pendiente", "En análisis", "Cerrado"]
REGIONES = ["Comodoro Rivadavia", "Neuquén", "Bariloche", "Otra"]
```

**Jerarquía normativa en el motor:**
`API > ASME > IRAM > AWS > ASTM > ISO > IAPG`

---

## InspeccionEngine — métodos por categoría

### Utilidades
- `normalizar_texto(texto)` — lowercase, sin tildes, sin caracteres especiales
- `normalizar_nombre_archivo(nombre)` — para comparación de nombres de normas
- `contiene_keywords(texto_norm, keywords)` — búsqueda de palabras clave
- `buscar_norma_exacta(lista, nombre)` — match exacto normalizado
- `buscar_norma_por_codigo(lista, codigos)` — match por regex de código
- `obtener_ente_normativo(norma)` — extrae organismo (API, ASME, etc.)
- `resolver_norma_de_regla(lista, regla)` — resuelve norma principal o alternativa

### Matriz normativa
- `buscar_referencia_interna_coiled_tubing(lista)` — caso especial coiled tubing
- `obtener_matriz_normativa()` — devuelve dict completo con reglas por equipo/sistema
- `clasificar_por_matriz_normativa(hallazgo, lista)` — clasificación determinística
- `resolver_respuesta_ia(respuesta_ia, lista)` — parsea respuesta de Gemini en clasificación

### Consulta y RAG
- `extraer_codigos_norma_de_pregunta(pregunta)` — extrae códigos de norma mencionados
- `resolver_norma_mencionada_en_pregunta(pregunta, lista)` — resuelve norma mencionada
- `descargar_pdf_norma_desde_gcs(norma_path)` — descarga PDF desde bucket
- `extraer_texto_pdf_bytes(pdf_bytes)` — extrae texto plano de PDF
- `recortar_contexto_pdf(texto, pregunta, limite=18000)` — recorta contexto relevante
- `consultar_pdf_norma_directo(pregunta, norma_path, lista_imagenes)` — consulta directa al PDF
- `clasificar_norma_ia(hallazgo, lista, lista_imagenes)` — clasificador híbrido
- `es_referencia_interna_invap(norma_path)` — detecta si es referencia interna INVAP
- `consultar_normativa_rag(norma_path, hallazgo, lista_imagenes)` — RAG completo
- `consultar_normas_chat(pregunta, lista_normas, lista_imagenes)` — chat sin norma específica
- `responder_chatbot_normativo(pregunta, lista_normas, historial, contexto_consulta)` — chatbot con memoria de sesión

### Informes y aprendizaje
- `guardar_leccion_aprendida(hallazgo, informe_final, norma_usada)` — guarda en GCS
- `refinar_informe(informe_previo, comentario)` — refinamiento con comentario del inspector

### Multimedia
- `transcribir_audio(audio_bytes, mime_type)` — transcripción con Gemini
- `extraer_texto_docx_bytes(docx_bytes)` — extrae texto de DOCX

### QA / Corrección
- `analizar_texto_qa(texto_informe, prompt_p)` — análisis de texto
- `analizar_docx_qa(docx_bytes, prompt_p)` — análisis de DOCX
- `analizar_pdf_qa(pdf_bytes, prompt_p)` — análisis de PDF

### Vigencia normativa (nuevo — 2026-06-24)
- `verificar_vigencia_norma(codigo_norma)` — consulta vigencia via Google Search Grounding
  - Retorna: `{estado, ultima_actualizacion, reemplazada_por, detalle, norma}`
  - `estado`: `"VIGENTE"` | `"REVISADA"` | `"REEMPLAZADA"` | `"NO DETERMINADO"`

---

## Fuentes de normas configuradas (verificación de vigencia)

Sin membresía, acceso público. Usadas como referencia conceptual para el buscador web:

| Organismo | URL |
|-----------|-----|
| ACCURIS (genérico) | store.accuristech.com |
| ASME | asme.org/codes-standards/find-codes-standards |
| ASTM | astm.org |
| IRAM | iram.org.ar/normalizacion/busca-tu-norma/ |
| ISO | iso.org/es/search.html |
| ANSI | webstore.ansi.org |
| AWS | aws.org/standards-and-publications/codes-and-standards/a30m/ |
| API | apiwebstore.org |

La verificación **no** hace scraping directo — usa Google Search Grounding de Gemini.

---

## Memoria normativa

Archivo JSON en GCS (`memoria_normativa/memoria_normativa_validada.json`).  
Estructura por ítem: `{texto_hallazgo, norma_validada, fecha, confirmado_por_usuario}`.

Flujo:
1. Cuando el usuario valida/corrige la norma detectada → se guarda en memoria
2. En consultas futuras → `sugerir_norma_desde_memoria()` busca match por tokens antes de ir a Gemini
3. Si hay match con suficiente confianza → va directo a RAG con esa norma

---

## Notas técnicas importantes

- **Zona horaria:** siempre usar `ahora_argentina()` (no `datetime.now()` sin zona)
- **Session state:** el `motor` (InspeccionEngine) vive en `st.session_state["motor"]`. En Streamlit Cloud, después de un redespliegue, la sesión puede tener el motor viejo — el usuario debe hacer reboot o limpiar sesión
- **Cache de vigencia:** `st.session_state[f"vigencia_{norma}"]` — se resetea al limpiar consulta
- **Modelo:** `gemini-3-flash-preview` — si cambia, actualizar en `engine.py` línea 22
- **`google-genai >= 1.0.0`** requerido para `types.GoogleSearch()` y `types.GenerateContentConfig(tools=...)`
- Los PDFs de normas en GCS pueden tener páginas escaneadas → el engine lo detecta y activa modo visual
