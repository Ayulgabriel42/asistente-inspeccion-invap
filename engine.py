import os
import io
import json
import re
import unicodedata
import datetime
import pandas as pd

from google import genai
from google.genai import types
from google.cloud import storage

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader


class InspeccionEngine:
    def __init__(self, api_key, creds=None, project_id=None):
        self.creds = creds
        self.project_id = project_id
        self.model_id = "gemini-3-flash-preview"
        self.bucket_name = "invap-asistente-normas"

        # Contexto operativo del MVP
        self.contexto_operativo = (
            "Inspección de campo INVAP Ingeniería S.A. en equipos petroleros "
            "de pulling, workover y perforación."
        )

        self.jerarquia_normativa = [
            "API",
            "ASME",
            "IRAM",
            "AWS",
            "ASTM",
            "ISO",
            "IAPG",
        ]

        self.ultima_clasificacion_normativa = None

        # Mantener una sola key activa para evitar advertencias/confusión
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ["GOOGLE_API_KEY"] = api_key

        self.client = genai.Client(api_key=api_key)

    # =========================================================
    # UTILIDADES DE NORMALIZACIÓN
    # =========================================================
    def normalizar_texto(self, texto):
        if not texto:
            return ""

        texto = str(texto)
        texto = unicodedata.normalize("NFKD", texto)
        texto = "".join(c for c in texto if not unicodedata.combining(c))
        texto = texto.lower()
        texto = texto.replace("°", " grados ")
        texto = texto.replace("º", " grados ")
        texto = re.sub(r"\s+", " ", texto)
        return texto.strip()

    def normalizar_nombre_archivo(self, nombre):
        if not nombre:
            return ""

        base = str(nombre).split("/")[-1]
        base = self.normalizar_texto(base)
        base = base.replace(".pdf", "")
        base = re.sub(r"\s*-\s*", "-", base)
        base = re.sub(r"\s+", "", base)
        return base

    def contiene_keywords(self, texto_norm, keywords):
        encontradas = []

        for kw in keywords:
            kw_norm = self.normalizar_texto(kw)
            if kw_norm and kw_norm in texto_norm:
                encontradas.append(kw)

        return encontradas

    def buscar_norma_exacta(self, lista_normas, nombre_objetivo):
        objetivo_norm = self.normalizar_nombre_archivo(nombre_objetivo)

        for norma in lista_normas:
            if self.normalizar_nombre_archivo(norma) == objetivo_norm:
                return norma

        return None

    def buscar_norma_por_codigo(self, lista_normas, codigos):
        """
        Busca por código evitando falsos positivos.
        Ejemplo:
        B30.1 no debe confundirse con B30.10.
        16D no debe confundirse con 16C.
        """
        if isinstance(codigos, str):
            codigos = [codigos]

        for codigo in codigos:
            codigo_norm = self.normalizar_texto(codigo)

            patron = re.compile(
                r"(?<![a-z0-9.])" + re.escape(codigo_norm) + r"(?![a-z0-9.])"
            )

            for norma in lista_normas:
                nombre = self.normalizar_texto(str(norma).split("/")[-1])
                if patron.search(nombre):
                    return norma

        return None

    def obtener_ente_normativo(self, norma):
        nombre = str(norma).split("/")[-1].upper()

        if nombre.startswith("API"):
            return "API"
        if nombre.startswith("ASME"):
            return "ASME"
        if nombre.startswith("IRAM"):
            return "IRAM"
        if nombre.startswith("AWS"):
            return "AWS"
        if nombre.startswith("ASTM"):
            return "ASTM"
        if nombre.startswith("ISO") or "ISO" in nombre:
            return "ISO"
        if nombre.startswith("IAPG"):
            return "IAPG"

        return "OTRO"

    def resolver_norma_de_regla(self, lista_normas, regla):
        """
        Intenta resolver primero la norma principal.
        Si no existe en el bucket, intenta normas relacionadas.
        """
        norma_resuelta = self.buscar_norma_exacta(
            lista_normas,
            regla.get("norma_principal", "")
        )

        if not norma_resuelta:
            norma_resuelta = self.buscar_norma_por_codigo(
                lista_normas,
                regla.get("codigos_principal", [])
            )

        if norma_resuelta:
            return norma_resuelta, "principal"

        for nr in regla.get("normas_relacionadas", []):
            encontrada = self.buscar_norma_exacta(lista_normas, nr)
            if encontrada:
                return encontrada, "relacionada"

        for codigo in regla.get("codigos_relacionados", []):
            encontrada = self.buscar_norma_por_codigo(lista_normas, codigo)
            if encontrada:
                return encontrada, "relacionada"

        return None, None

    # =========================================================
    # MATRIZ NORMATIVA BASE DEL MVP
    # =========================================================
    def obtener_matriz_normativa(self):
        """
        Matriz normativa inicial para inspección de campo petrolera.

        Criterio:
        1. Contexto principal: equipos petroleros pulling, workover y perforación.
        2. API tiene prioridad cuando el sistema es propio de la industria petrolera.
        3. ASME / IRAM prevalecen cuando el componente tiene norma específica:
           eslingas, grilletes, gatos/cilindros hidráulicos, accesorios de izaje.
        """

        return [
            # -------------------------------------------------
            # CONTROL DE POZO / ACUMULADORES / BOP
            # -------------------------------------------------
            {
                "dominio": "CONTROL_DE_POZO_ACUMULADOR",
                "familia": "API",
                "norma_principal": "API - 16D - 2005.pdf",
                "codigos_principal": ["16D"],
                "normas_relacionadas": [
                    "API - 53 - 2018.pdf",
                    "API - 16A - 2017.pdf"
                ],
                "codigos_relacionados": ["53", "16A"],
                "keywords_fuertes": [
                    "acumulador",
                    "unidad acumuladora",
                    "sistema acumulador",
                    "bomba neumática",
                    "bomba neumatica",
                    "bombas neumáticas",
                    "bombas neumaticas",
                    "control de pozo",
                    "bop control",
                    "bop",
                    "rams",
                    "preventor",
                    "esclusa"
                ],
                "keywords_falla": [
                    "válvula de alivio",
                    "valvula de alivio",
                    "válvula de seguridad",
                    "valvula de seguridad",
                    "no actúa",
                    "no actua",
                    "no abre",
                    "sin apertura",
                    "resultado no satisfactorio",
                    "mal funcionamiento",
                    "no retiene presión",
                    "no retiene presion",
                    "caída de presión",
                    "caida de presion",
                    "falla en su funcionamiento",
                    "3500 psi",
                    "3000 psi",
                    "2400 psi"
                ],
                "requiere_falla": False,
                "peso": 120
            },
            {
                "dominio": "BOP_RAM_ACCIONAMIENTO",
                "familia": "API",
                "norma_principal": "API - 16D - 2005.pdf",
                "codigos_principal": ["16D"],
                "normas_relacionadas": [
                    "API - 53 - 2018.pdf",
                    "API - 16A - 2017.pdf"
                ],
                "codigos_relacionados": ["53", "16A"],
                "keywords_fuertes": [
                    "bop",
                    "rams",
                    "ram",
                    "esclusa",
                    "preventor",
                    "cierre y apertura",
                    "accionamiento",
                    "vástago",
                    "vastago"
                ],
                "keywords_falla": [
                    "no completa carrera",
                    "no completa la carrera",
                    "no cierra",
                    "no abre",
                    "falla al accionar",
                    "falla en accionamiento",
                    "deficiencia en el sistema de accionamiento"
                ],
                "requiere_falla": False,
                "peso": 116
            },
            {
                "dominio": "CHOKE_KILL_MANIFOLD",
                "familia": "API",
                "norma_principal": "API - 16C - 2021.pdf",
                "codigos_principal": ["16C"],
                "normas_relacionadas": [
                    "API - 53 - 2018.pdf",
                    "API - 6A - 2021.pdf"
                ],
                "codigos_relacionados": ["53", "6A"],
                "keywords_fuertes": [
                    "choke line",
                    "kill line",
                    "choke manifold",
                    "manifold",
                    "check valve",
                    "hcr",
                    "super choke",
                    "línea ap",
                    "linea ap",
                    "presión de sondeo",
                    "presion de sondeo"
                ],
                "keywords_falla": [
                    "fuga",
                    "pérdida de estanqueidad",
                    "perdida de estanqueidad",
                    "no acusa presión",
                    "no acusa presion",
                    "sin certificado trazable",
                    "certificado trazable",
                    "falla en accionamiento"
                ],
                "requiere_falla": False,
                "peso": 112
            },

            # -------------------------------------------------
            # ESTRUCTURA DE EQUIPO PETROLERO
            # -------------------------------------------------
            {
                "dominio": "ESTRUCTURA_MASTIL_SUBESTRUCTURA",
                "familia": "API",
                "norma_principal": "API - 4G - 2020.pdf",
                "codigos_principal": ["4G"],
                "normas_relacionadas": [
                    "API - 4F - 2020.pdf",
                    "API - 8B.AD - 2021.pdf",
                    "AWS - D1.1 - 2020.pdf"
                ],
                "codigos_relacionados": ["4F", "8B", "D1.1"],
                "keywords_fuertes": [
                    "estructura",
                    "mástil",
                    "mastil",
                    "subestructura",
                    "bancada",
                    "soporte",
                    "corona",
                    "pasarela",
                    "bastidor",
                    "piso de enganche",
                    "larguero",
                    "chasis",
                    "unión soldada",
                    "union soldada",
                    "cordón de soldadura",
                    "cordon de soldadura",
                    "material base"
                ],
                "keywords_falla": [
                    "fisura",
                    "grieta",
                    "propagación longitudinal",
                    "propagacion longitudinal",
                    "fatiga",
                    "fatiga estructural",
                    "corrosión",
                    "corrosion",
                    "concentración de tensiones",
                    "concentracion de tensiones",
                    "cargas cíclicas",
                    "cargas ciclicas",
                    "discontinuidad"
                ],
                "requiere_falla": True,
                "peso": 118
            },

            # -------------------------------------------------
            # SISTEMA DE IZAJE / CABLE / CORONA / APAREJO
            # -------------------------------------------------
            {
                "dominio": "CABLE_POLEA_CORONA_TAMBOR",
                "familia": "API",
                "norma_principal": "API - 9B - 2012.pdf",
                "codigos_principal": ["9B"],
                "normas_relacionadas": [
                    "API - 7K - 2015.pdf",
                    "API - 8C - 2012.pdf"
                ],
                "codigos_relacionados": ["7K", "8C"],
                "keywords_fuertes": [
                    "cable de acero",
                    "cable",
                    "wire rope",
                    "polea",
                    "corona",
                    "tambor principal",
                    "garganta",
                    "aparejo",
                    "malacate"
                ],
                "keywords_falla": [
                    "desgaste",
                    "fuera de límites",
                    "fuera de limites",
                    "profundidad de garganta",
                    "incorrecto pasado",
                    "cruce",
                    "reducción de diámetro",
                    "reduccion de diametro",
                    "alambres cortados"
                ],
                "requiere_falla": True,
                "peso": 108
            },
            {
                "dominio": "GANCHO_APAREJO_ELEVADORES",
                "familia": "API",
                "norma_principal": "API - 8C - 2012.pdf",
                "codigos_principal": ["8C"],
                "normas_relacionadas": [
                    "API - 8B.AD - 2021.pdf",
                    "API - 7K - 2015.pdf"
                ],
                "codigos_relacionados": ["8B", "7K"],
                "keywords_fuertes": [
                    "gancho del aparejo",
                    "gancho",
                    "aparejo",
                    "elevador",
                    "elevadores",
                    "travelling block",
                    "hook block"
                ],
                "keywords_falla": [
                    "tolerancia",
                    "desvío",
                    "desvio",
                    "fuera de límites",
                    "fuera de limites",
                    "deformación",
                    "deformacion",
                    "fisura",
                    "desgaste"
                ],
                "requiere_falla": False,
                "peso": 104
            },

            # -------------------------------------------------
            # BOMBAS DE LODO / CUADRO DE MANIOBRAS / ROTARY
            # -------------------------------------------------
            {
                "dominio": "BOMBAS_LODO_CUADRO_MANIOBRAS",
                "familia": "API",
                "norma_principal": "API - 7K - 2015.pdf",
                "codigos_principal": ["7K"],
                "normas_relacionadas": [
                    "API - 7L - 1995.pdf"
                ],
                "codigos_relacionados": ["7L"],
                "keywords_fuertes": [
                    "bomba de lodo",
                    "bombas de lodo",
                    "fluid end",
                    "pistón de bomba",
                    "piston de bomba",
                    "brida",
                    "tapa de válvula",
                    "tapa de valvula",
                    "cuadro de maniobras",
                    "mesa rotary",
                    "rotary",
                    "tambor principal",
                    "piñón",
                    "pinon",
                    "cadena",
                    "campanas del tambor"
                ],
                "keywords_falla": [
                    "pérdida de fluido",
                    "perdida de fluido",
                    "fuga",
                    "fisura",
                    "golpe",
                    "bulón suelto",
                    "bulon suelto",
                    "no cumple ensayo",
                    "desprendimiento",
                    "certificado sin vigencia",
                    "certificación vencida",
                    "certificacion vencida"
                ],
                "requiere_falla": False,
                "peso": 106
            },

            # -------------------------------------------------
            # SEGURIDAD OPERATIVA PETROLERA
            # -------------------------------------------------
            {
                "dominio": "SEGURIDAD_OPERATIVA_GENERAL",
                "familia": "API",
                "norma_principal": "API - 54 - 2019.pdf",
                "codigos_principal": ["54"],
                "normas_relacionadas": [
                    "API - 510 - 2022.pdf"
                ],
                "codigos_relacionados": ["510"],
                "keywords_fuertes": [
                    "seguridad",
                    "puesta a tierra",
                    "medidor de gases",
                    "detector de gases",
                    "altair",
                    "espumígeno",
                    "espumigeno",
                    "sistema contra incendios",
                    "parada de emergencia",
                    "boquillas",
                    "cobertura"
                ],
                "keywords_falla": [
                    "vencido",
                    "obstruidas",
                    "sin montar",
                    "no cumple",
                    "falla en accionamiento",
                    "cobertura",
                    "pérdida de aire",
                    "perdida de aire"
                ],
                "requiere_falla": False,
                "peso": 98
            },

            # -------------------------------------------------
            # EXCEPCIONES POR NORMA ESPECÍFICA DE COMPONENTE
            # -------------------------------------------------
            {
                "dominio": "IZAJE_HIDRAULICO_CILINDROS",
                "familia": "ASME",
                "norma_principal": "ASME - B30.1 - 2020.pdf",
                "codigos_principal": ["B30.1"],
                "normas_relacionadas": [],
                "codigos_relacionados": [],
                "keywords_fuertes": [
                    "cilindro hidráulico",
                    "cilindro hidraulico",
                    "cilindro del mástil",
                    "cilindro del mastil",
                    "cilindro de izaje",
                    "pistón hidráulico",
                    "piston hidraulico",
                    "pistón",
                    "piston",
                    "primer tramo del mástil",
                    "primer tramo del mastil",
                    "sistema de izaje",
                    "izado",
                    "izaje",
                    "gato hidráulico",
                    "gato hidraulico"
                ],
                "keywords_falla": [
                    "fuga hidráulica",
                    "fuga hidraulica",
                    "pérdida de fluido",
                    "perdida de fluido",
                    "pérdida hidráulica",
                    "perdida hidraulica",
                    "pérdida de estanqueidad",
                    "perdida de estanqueidad",
                    "falla de potencia hidráulica",
                    "falla de potencia hidraulica",
                    "no supera los 30 grados",
                    "no supera los 30",
                    "sellos",
                    "conexiones"
                ],
                "requiere_falla": True,
                "peso": 115
            },
            {
                "dominio": "IZAJE_ESLINGAS",
                "familia": "ASME_IRAM",
                "norma_principal": "ASME - B30.9 - 2021.pdf",
                "codigos_principal": ["B30.9"],
                "normas_relacionadas": [
                    "IRAM - 3914-1 - 2019.pdf",
                    "IRAM - 3914-2 - 2020.pdf",
                    "IRAM - 3914-3 - 2023.pdf"
                ],
                "codigos_relacionados": ["3914-1", "3914-2", "3914-3"],
                "keywords_fuertes": [
                    "eslinga",
                    "eslingas",
                    "sling",
                    "ojal",
                    "alma expuesta",
                    "alambres cortados",
                    "cordones",
                    "tensor de carga",
                    "eslinga sintética",
                    "eslinga sintetica"
                ],
                "keywords_falla": [
                    "deformación",
                    "deformacion",
                    "aplastamiento",
                    "reducción de diámetro",
                    "reduccion de diametro",
                    "deterioro avanzado",
                    "malas condiciones",
                    "sobrecarga",
                    "exposición del alma",
                    "exposicion del alma",
                    "corte",
                    "alambres cortados"
                ],
                "requiere_falla": False,
                "peso": 114
            },
            {
                "dominio": "ACCESORIOS_IZAJE",
                "familia": "ASME",
                "norma_principal": "ASME - B30.26 - 2015.pdf",
                "codigos_principal": ["B30.26"],
                "normas_relacionadas": [],
                "codigos_relacionados": [],
                "keywords_fuertes": [
                    "grillete",
                    "grilletes",
                    "shackle",
                    "perno",
                    "seguro",
                    "ojal de anclaje",
                    "accesorio de izaje",
                    "rigging hardware",
                    "pernos vinculantes"
                ],
                "keywords_falla": [
                    "certificación vencida",
                    "certificacion vencida",
                    "ausencia de seguro",
                    "sin seguro",
                    "deformación",
                    "deformacion",
                    "corte mecánico",
                    "corte mecanico",
                    "daño significativo",
                    "dano significativo"
                ],
                "requiere_falla": False,
                "peso": 110
            }
        ]

    # =========================================================
    # CLASIFICADOR POR MATRIZ TÉCNICA
    # =========================================================
    def clasificar_por_matriz_normativa(self, hallazgo, lista_normas):
        texto_norm = self.normalizar_texto(hallazgo)

        if not texto_norm or not lista_normas:
            return None

        resultados = []

        for regla in self.obtener_matriz_normativa():
            fuertes = self.contiene_keywords(texto_norm, regla["keywords_fuertes"])
            fallas = self.contiene_keywords(texto_norm, regla["keywords_falla"])

            if not fuertes:
                continue

            if regla.get("requiere_falla", False) and not fallas:
                continue

            # Protección: si habla de fisura/soldadura/bancada, no mandar a ASME B30.1
            # solo porque aparece "cilindro" o "pistón".
            if regla["dominio"] == "IZAJE_HIDRAULICO_CILINDROS":
                indicadores_estructura = self.contiene_keywords(
                    texto_norm,
                    [
                        "fisura",
                        "grieta",
                        "soldadura",
                        "bancada",
                        "material base",
                        "cordón de soldadura",
                        "cordon de soldadura",
                        "propagación longitudinal",
                        "propagacion longitudinal"
                    ]
                )

                indicadores_hidraulicos = self.contiene_keywords(
                    texto_norm,
                    [
                        "fuga",
                        "hidráulica",
                        "hidraulica",
                        "fluido",
                        "estanqueidad",
                        "potencia hidráulica",
                        "potencia hidraulica",
                        "sellos",
                        "conexiones"
                    ]
                )

                if indicadores_estructura and not indicadores_hidraulicos:
                    continue

            norma_resuelta, tipo_resolucion = self.resolver_norma_de_regla(
                lista_normas,
                regla
            )

            if not norma_resuelta:
                continue

            score = regla["peso"] + len(fuertes) * 12 + len(fallas) * 8

            # Prioridad API para sistemas petroleros propios.
            if regla.get("familia") == "API":
                score += 12

            # Excepciones técnicas validadas: se respetan aunque no sean API.
            if regla["dominio"] in [
                "IZAJE_HIDRAULICO_CILINDROS",
                "IZAJE_ESLINGAS",
                "ACCESORIOS_IZAJE"
            ]:
                score += 10

            relacionadas_resueltas = []

            for nr in regla.get("normas_relacionadas", []):
                encontrada = self.buscar_norma_exacta(lista_normas, nr)
                if encontrada:
                    relacionadas_resueltas.append(encontrada)

            confianza = min(
                0.98,
                0.58 + (len(fuertes) * 0.06) + (len(fallas) * 0.04)
            )

            resultados.append({
                "dominio": regla["dominio"],
                "familia": regla.get("familia", ""),
                "norma_principal": norma_resuelta,
                "tipo_resolucion": tipo_resolucion,
                "normas_relacionadas": relacionadas_resueltas,
                "evidencias_fuertes": fuertes,
                "evidencias_falla": fallas,
                "score": score,
                "confianza": confianza
            })

        if not resultados:
            return None

        resultados.sort(key=lambda x: x["score"], reverse=True)
        return resultados[0]

    def resolver_respuesta_ia(self, respuesta_ia, lista_normas):
        if not respuesta_ia:
            return None

        limpia = (
            str(respuesta_ia)
            .strip()
            .replace("`", "")
            .replace("'", "")
            .replace('"', "")
        )

        if limpia in lista_normas:
            return limpia

        exacta = self.buscar_norma_exacta(lista_normas, limpia)
        if exacta:
            return exacta

        codigos = re.findall(
            r"\b(?:API|ASME|IRAM|AWS)?\s*[-]?\s*([A-Z]?\d+[A-Z]?(?:\.\d+)?(?:-[A-Z0-9]+)?)\b",
            limpia,
            flags=re.I
        )

        for codigo in codigos:
            encontrada = self.buscar_norma_por_codigo(lista_normas, codigo)
            if encontrada:
                return encontrada

        return None

    # =========================================================
    # CLASIFICADOR DE NORMA HÍBRIDO
    # =========================================================
    def clasificar_norma_ia(self, hallazgo, lista_normas, lista_imagenes=None):
        """
        Clasificador híbrido:
        1. Primero usa matriz normativa del contexto petrolero INVAP.
        2. API tiene prioridad para sistemas propios de pulling/workover/perforación.
        3. ASME/IRAM prevalecen cuando el componente tiene norma específica.
        4. Gemini solo se usa como respaldo/desempate.
        """
        self.ultima_clasificacion_normativa = None

        if not lista_normas:
            return None

        hallazgo_lower = self.normalizar_texto(hallazgo)

        # -----------------------------------------------------
        # 1) Matriz normativa determinística
        # -----------------------------------------------------
        resultado_matriz = self.clasificar_por_matriz_normativa(
            hallazgo,
            lista_normas
        )

        if resultado_matriz and resultado_matriz["confianza"] >= 0.74:
            self.ultima_clasificacion_normativa = resultado_matriz
            return resultado_matriz["norma_principal"]

        # -----------------------------------------------------
        # 2) Gemini como respaldo: detección de dominio
        # -----------------------------------------------------
        prompt_dominio = (
            "Analiza el hallazgo y las imágenes dentro del siguiente contexto:\n"
            "INVAP Ingeniería S.A. realiza inspecciones de campo en equipos petroleros "
            "de pulling, workover y perforación.\n\n"
            "Criterio jerárquico:\n"
            "1. Para sistemas propios de equipos petroleros, priorizar API.\n"
            "2. Para componentes específicos de izaje, rigging o hidráulica, pueden prevalecer ASME/IRAM.\n"
            "3. No elegir por similitud superficial de palabras; priorizar sistema + componente + modo de falla.\n\n"
            "Categorías posibles:\n"
            "- CONTROL_POZO: acumuladores, bombas neumáticas, válvulas de alivio, BOP, rams, preventores.\n"
            "- CHOKE_MANIFOLD: choke line, kill line, manifold, check valve, HCR.\n"
            "- ESTRUCTURA: fisuras, soldaduras, bancadas, mástiles, subestructuras, pasarelas.\n"
            "- CABLE_POLEA_TAMBOR: cable de acero, poleas, corona, garganta, tambor, malacate.\n"
            "- BOMBAS_LODO: bombas de lodo, fluid end, bridas, tapas, pistones.\n"
            "- SEGURIDAD: puesta a tierra, incendio, espumígeno, gas, parada de emergencia.\n"
            "- IZAJE_HIDRAULICO: cilindros hidráulicos, gatos hidráulicos, fugas hidráulicas, izado de mástil.\n"
            "- IZAJE_ESLINGAS: eslingas, alambres cortados, ojal, alma expuesta.\n"
            "- ACCESORIOS_IZAJE: grilletes, pernos, seguros, accesorios de rigging.\n"
            "- MECANICO: tanques, recipientes, tuberías, roscas, válvulas generales.\n\n"
            f"Hallazgo:\n{hallazgo}\n\n"
            "Responde SOLO el nombre de la categoría."
        )

        contenidos_v = [prompt_dominio]

        if lista_imagenes:
            for img_data, img_mime in lista_imagenes:
                contenidos_v.append(
                    types.Part.from_bytes(data=img_data, mime_type=img_mime)
                )

        try:
            res_v = self.client.models.generate_content(
                model=self.model_id,
                contents=contenidos_v
            )
            dominio = res_v.text.strip().upper()
        except Exception:
            dominio = "OTRO"

        # -----------------------------------------------------
        # 3) Prefiltro de normas por dominio
        # -----------------------------------------------------
        lista_final = lista_normas.copy()

        if "CONTROL_POZO" in dominio or any(x in hallazgo_lower for x in [
            "acumulador",
            "bomba neumatica",
            "bombas neumaticas",
            "valvula de alivio",
            "valvula de seguridad",
            "bop",
            "rams",
            "preventor",
            "esclusa"
        ]):
            lista_final = [
                n for n in lista_normas
                if any(x in self.normalizar_texto(n) for x in ["16d", "53", "16a"])
            ]

        elif "CHOKE" in dominio or any(x in hallazgo_lower for x in [
            "choke",
            "kill line",
            "manifold",
            "check valve",
            "hcr",
            "super choke"
        ]):
            lista_final = [
                n for n in lista_normas
                if any(x in self.normalizar_texto(n) for x in ["16c", "53", "6a"])
            ]

        elif "ESTRUCTURA" in dominio or any(x in hallazgo_lower for x in [
            "fisura",
            "grieta",
            "soldadura",
            "bancada",
            "mastil",
            "subestructura",
            "pasarela",
            "bastidor"
        ]):
            lista_final = [
                n for n in lista_normas
                if any(x in self.normalizar_texto(n) for x in ["4g", "4f", "8b", "d1.1"])
            ]

        elif "CABLE_POLEA" in dominio or any(x in hallazgo_lower for x in [
            "cable de acero",
            "polea",
            "corona",
            "garganta",
            "tambor principal",
            "malacate",
            "wire rope"
        ]):
            lista_final = [
                n for n in lista_normas
                if any(x in self.normalizar_texto(n) for x in ["9b", "7k", "8c"])
            ]

        elif "BOMBAS_LODO" in dominio or any(x in hallazgo_lower for x in [
            "bomba de lodo",
            "bombas de lodo",
            "fluid end",
            "mesa rotary",
            "cuadro de maniobras",
            "rotary",
            "piñon",
            "pinon",
            "cadena"
        ]):
            lista_final = [
                n for n in lista_normas
                if any(x in self.normalizar_texto(n) for x in ["7k", "7l"])
            ]

        elif "SEGURIDAD" in dominio or any(x in hallazgo_lower for x in [
            "espumigeno",
            "puesta a tierra",
            "altair",
            "medidor de gases",
            "incendio",
            "parada de emergencia"
        ]):
            lista_final = [
                n for n in lista_normas
                if any(x in self.normalizar_texto(n) for x in ["54", "510"])
            ]

        elif "IZAJE_HIDRAULICO" in dominio or any(x in hallazgo_lower for x in [
            "fuga hidraulica",
            "cilindro hidraulico",
            "perdida de fluido",
            "gato hidraulico",
            "primer tramo"
        ]):
            lista_final = [
                n for n in lista_normas
                if any(x in self.normalizar_texto(n) for x in ["b30.1"])
            ]

        elif "IZAJE_ESLINGAS" in dominio or any(x in hallazgo_lower for x in [
            "eslinga",
            "alambres cortados",
            "ojal",
            "alma expuesta",
            "cordones"
        ]):
            lista_final = [
                n for n in lista_normas
                if any(x in self.normalizar_texto(n) for x in ["b30.9", "3914"])
            ]

        elif "ACCESORIOS_IZAJE" in dominio or any(x in hallazgo_lower for x in [
            "grillete",
            "perno",
            "seguro",
            "ojal de anclaje"
        ]):
            lista_final = [
                n for n in lista_normas
                if any(x in self.normalizar_texto(n) for x in ["b30.26"])
            ]

        # Si no hay subset, priorizar API antes que todo el bucket.
        if not lista_final:
            normas_api = [
                n for n in lista_normas
                if self.obtener_ente_normativo(n) == "API"
            ]
            lista_final = normas_api if normas_api else lista_normas

        # -----------------------------------------------------
        # 4) Gemini elige sobre subset reducido
        # -----------------------------------------------------
        prompt_final = (
            "ERES UN EXPERTO TÉCNICO DE INVAP INGENIERÍA.\n\n"
            "Contexto obligatorio:\n"
            "- Inspección de campo en equipos petroleros de pulling, workover y perforación.\n"
            "- API es la familia normativa prioritaria para sistemas propios de la industria petrolera.\n"
            "- ASME/IRAM solo deben prevalecer cuando el componente tenga una norma específica "
            "de izaje, rigging, eslingas, grilletes o gatos/cilindros hidráulicos.\n\n"
            f"Categoría detectada: {dominio}\n\n"
            f"Hallazgo:\n{hallazgo}\n\n"
            f"Normas candidatas disponibles:\n{lista_final[:15]}\n\n"
            "CRITERIO OBLIGATORIO:\n"
            "- No elijas por similitud superficial de palabras.\n"
            "- Priorizá sistema afectado + componente + modo de falla.\n"
            "- Acumulador / bombas neumáticas / válvula de alivio / BOP => API 16D.\n"
            "- Choke line / kill line / manifold / HCR / check valve => API 16C.\n"
            "- Mástil / subestructura / bancada / soldadura / fisura => API 4G y API 4F.\n"
            "- Cable de acero / polea / corona / garganta / tambor => API 9B / API 7K.\n"
            "- Bomba de lodo / mesa rotary / cuadro de maniobras => API 7K / API 7L.\n"
            "- Fuga hidráulica en cilindro/gato del sistema de izaje => ASME B30.1.\n"
            "- Eslinga con alambres cortados/deformación/ojal => ASME B30.9 / IRAM 3914.\n"
            "- Grilletes/pernos/seguros/accesorios de rigging => ASME B30.26.\n\n"
            "Responde ÚNICAMENTE con el nombre exacto del archivo de la norma principal."
        )

        contenidos_f = [prompt_final]

        if lista_imagenes:
            for img_data, img_mime in lista_imagenes:
                contenidos_f.append(
                    types.Part.from_bytes(data=img_data, mime_type=img_mime)
                )

        try:
            res = self.client.models.generate_content(
                model=self.model_id,
                contents=contenidos_f
            )

            seleccion_resuelta = self.resolver_respuesta_ia(
                res.text,
                lista_normas
            )

            if seleccion_resuelta:
                self.ultima_clasificacion_normativa = {
                    "dominio": dominio,
                    "norma_principal": seleccion_resuelta,
                    "familia": self.obtener_ente_normativo(seleccion_resuelta),
                    "evidencias_fuertes": [],
                    "evidencias_falla": [],
                    "confianza": 0.70,
                    "origen": "gemini_respaldo"
                }
                return seleccion_resuelta

            if lista_final:
                self.ultima_clasificacion_normativa = {
                    "dominio": dominio,
                    "norma_principal": lista_final[0],
                    "familia": self.obtener_ente_normativo(lista_final[0]),
                    "evidencias_fuertes": [],
                    "evidencias_falla": [],
                    "confianza": 0.55,
                    "origen": "fallback_subset"
                }
                return lista_final[0]

            return None

        except Exception:
            if lista_final:
                return lista_final[0]
            return None

    # =========================================================
    # CONSULTA RAG SOBRE PDF ELEGIDO
    # =========================================================
    def consultar_normativa_rag(self, norma_path, hallazgo, lista_imagenes=None):
        if not norma_path:
            return (
                "No se pudo determinar una norma aplicable para el hallazgo. "
                "Se recomienda revisión técnica por ingeniería.",
                None
            )

        storage_client = storage.Client(credentials=self.creds, project=self.project_id)
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob(norma_path)

        tmp_path = f"temp_{norma_path.split('/')[-1]}".replace(" ", "_")

        try:
            blob.download_to_filename(tmp_path)

            pages = []
            contexto = ""

            try:
                loader = PyPDFLoader(tmp_path)
                pages = loader.load_and_split()
            except Exception as e:
                pages = []
                contexto = (
                    f"No se pudo extraer texto del PDF ({norma_path}). "
                    f"Error de lectura: {str(e)}"
                )

            if pages:
                try:
                    embeddings = GoogleGenerativeAIEmbeddings(
                        model="models/gemini-embedding-001"
                    )

                    vectorstore = FAISS.from_documents(pages, embeddings)

                    docs = vectorstore.similarity_search(
                        f"criterios rechazo descarte inspección {hallazgo}",
                        k=8
                    )

                    contexto = "\n\n".join([doc.page_content for doc in docs])

                except Exception as e:
                    contexto = f"Error al construir contexto semántico del PDF: {str(e)}"

            clasificacion = self.ultima_clasificacion_normativa or {}

            prompt_tecnico = (
                f"SISTEMA DE INTEGRIDAD INVAP | Norma: {norma_path}\n"
                "==========================================================\n"
                f"CONTEXTO OPERATIVO:\n{self.contexto_operativo}\n\n"
                f"CLASIFICACIÓN NORMATIVA PREVIA:\n{json.dumps(clasificacion, ensure_ascii=False, default=str)}\n"
                "==========================================================\n"
                f"CONTEXTO TÉCNICO RECUPERADO DEL PDF:\n{contexto}\n"
                "==========================================================\n\n"
                "INSTRUCCIONES CRÍTICAS:\n"
                "1. Tu informe debe basarse principalmente en el contexto técnico recuperado del PDF.\n"
                "2. No cites requerimientos de otras normas que no aparezcan en el texto recuperado.\n"
                "3. Si el texto no menciona criterios específicos para el hallazgo, indicá: "
                "'Criterio no encontrado en esta sección de la norma'.\n"
                "4. Redactá como asistente técnico de inspección, no como autoridad normativa final.\n"
                "5. Mantené trazabilidad entre componente, condición observada, evaluación y acción recomendada.\n\n"
                "### Estructura del Informe:\n"
                "**Componente:** [Nombre]\n"
                "**Condición:** [Descripción técnica del daño observado]\n"
                "**Norma de referencia:** [Norma usada]\n"
                "**Evaluación:** [Criterio recuperado o aclaración si no se encontró]\n"
                "**Acción recomendada:** [Acción técnica conservadora]\n"
                "**Observación:** [Indicar si requiere validación de ingeniería]\n\n"
                f"Hallazgo original del inspector:\n{hallazgo}"
            )

            contenidos = [prompt_tecnico]

            if not pages or not contexto or len(contexto) < 300:
                try:
                    with open(tmp_path, "rb") as f:
                        contenidos.append(
                            types.Part.from_bytes(
                                data=f.read(),
                                mime_type="application/pdf"
                            )
                        )
                except Exception:
                    pass

            if lista_imagenes:
                for img_data, img_mime in lista_imagenes:
                    contenidos.append(
                        types.Part.from_bytes(data=img_data, mime_type=img_mime)
                    )

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contenidos
            )

            return response.text, norma_path

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # =========================================================
    # CONSULTAS LIBRES SOBRE NORMAS
    # =========================================================
    def consultar_normas_chat(self, pregunta, lista_normas, lista_imagenes=None):
        if not pregunta:
            return "No se recibió ninguna pregunta."

        if not lista_normas:
            return "No hay normas disponibles cargadas en el sistema."

        pregunta_lower = self.normalizar_texto(pregunta)

        # Primero intentamos usar la misma matriz normativa.
        resultado_matriz = self.clasificar_por_matriz_normativa(
            pregunta,
            lista_normas
        )

        top_normas = []

        if resultado_matriz:
            top_normas.append(resultado_matriz["norma_principal"])
            for nr in resultado_matriz.get("normas_relacionadas", []):
                if nr not in top_normas:
                    top_normas.append(nr)

        # Si la matriz no detecta nada, usar preselección simple.
        if not top_normas:
            candidatas = []

            for norma in lista_normas:
                n = self.normalizar_texto(norma)
                score = 0

                if any(x in pregunta_lower for x in [
                    "acumulador",
                    "bomba neumatica",
                    "bombas neumaticas",
                    "valvula de alivio",
                    "bop",
                    "rams"
                ]):
                    if any(x in n for x in ["16d", "53", "16a"]):
                        score += 7

                if any(x in pregunta_lower for x in [
                    "choke",
                    "kill line",
                    "manifold",
                    "check valve",
                    "hcr"
                ]):
                    if any(x in n for x in ["16c", "53", "6a"]):
                        score += 6

                if any(x in pregunta_lower for x in [
                    "mastil",
                    "mástil",
                    "subestructura",
                    "estructura",
                    "derrick",
                    "bancada",
                    "fisura",
                    "soldadura"
                ]):
                    if any(x in n for x in ["4g", "4f", "8b", "d1.1"]):
                        score += 6

                if any(x in pregunta_lower for x in [
                    "cable",
                    "polea",
                    "corona",
                    "tambor",
                    "garganta",
                    "wire rope"
                ]):
                    if any(x in n for x in ["9b", "7k", "8c"]):
                        score += 5

                if any(x in pregunta_lower for x in [
                    "bomba de lodo",
                    "bombas de lodo",
                    "fluid end",
                    "mesa rotary",
                    "cuadro de maniobras"
                ]):
                    if any(x in n for x in ["7k", "7l"]):
                        score += 5

                if any(x in pregunta_lower for x in [
                    "cilindro hidraulico",
                    "fuga hidraulica",
                    "perdida de fluido",
                    "gato hidraulico"
                ]):
                    if "b30.1" in n:
                        score += 6

                if any(x in pregunta_lower for x in [
                    "eslinga",
                    "alambres",
                    "ojal",
                    "alma expuesta"
                ]):
                    if any(x in n for x in ["b30.9", "3914"]):
                        score += 6

                if any(x in pregunta_lower for x in [
                    "grillete",
                    "perno",
                    "seguro"
                ]):
                    if "b30.26" in n:
                        score += 6

                if any(x in pregunta_lower for x in [
                    "espumigeno",
                    "puesta a tierra",
                    "altair",
                    "medidor de gases",
                    "incendio"
                ]):
                    if any(x in n for x in ["54", "510"]):
                        score += 5

                if score > 0:
                    candidatas.append((norma, score))

            candidatas.sort(key=lambda x: x[1], reverse=True)
            top_normas = [x[0] for x in candidatas[:5]]

        if not top_normas:
            normas_api = [
                n for n in lista_normas
                if self.obtener_ente_normativo(n) == "API"
            ]
            top_normas = normas_api[:5] if normas_api else lista_normas[:5]

        prompt = (
            "Eres un asistente técnico experto en normativa industrial para inspecciones "
            "de campo petroleras de pulling, workover y perforación.\n\n"
            "Criterio jerárquico:\n"
            "1. API tiene prioridad para sistemas propios de la industria petrolera.\n"
            "2. ASME/IRAM prevalecen cuando el componente inspeccionado tiene norma específica.\n"
            "3. No inventes párrafos exactos ni requisitos que no hayan sido recuperados desde PDF.\n\n"
            f"Pregunta del usuario:\n{pregunta}\n\n"
            f"Normas candidatas disponibles en el sistema:\n{top_normas}\n\n"
            "Formato de respuesta:\n"
            "**Norma principal sugerida:** ...\n"
            "**Normas relacionadas:** ...\n"
            "**Fundamento técnico:** ...\n"
            "**Observación:** ...\n"
        )

        contenidos = [prompt]

        if lista_imagenes:
            for img_data, img_mime in lista_imagenes:
                contenidos.append(
                    types.Part.from_bytes(data=img_data, mime_type=img_mime)
                )

        try:
            res = self.client.models.generate_content(
                model=self.model_id,
                contents=contenidos
            )
            return res.text

        except Exception as e:
            return f"No se pudo responder la consulta normativa: {e}"

    # =========================================================
    # MEMORIA DE LARGO PLAZO
    # =========================================================
    def guardar_leccion_aprendida(self, hallazgo, informe_final, norma_usada):
        storage_client = storage.Client(credentials=self.creds, project=self.project_id)
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob("historial_lecciones/memoria_tecnica.parquet")

        nuevo_registro = pd.DataFrame([{
            "fecha": datetime.datetime.now(),
            "hallazgo_original": hallazgo,
            "informe_final": informe_final,
            "norma_referencia": norma_usada
        }])

        try:
            content = blob.download_as_bytes()
            df_historico = pd.read_parquet(io.BytesIO(content))
            df_final = pd.concat([df_historico, nuevo_registro], ignore_index=True)
        except Exception:
            df_final = nuevo_registro

        buffer = io.BytesIO()
        df_final.to_parquet(buffer, index=False)
        blob.upload_from_string(
            buffer.getvalue(),
            content_type="application/octet-stream"
        )

    # =========================================================
    # REFINAMIENTO DE INFORME
    # =========================================================
    def refinar_informe(self, informe_previo, comentario):
        prompt = (
            "Eres un editor técnico de informes industriales.\n\n"
            f"Informe actual:\n{informe_previo}\n\n"
            f"Cambio solicitado:\n{comentario}\n\n"
            "Mejora redacción, claridad y formato técnico, "
            "sin alterar el sentido del informe."
        )

        res = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt
        )

        return res.text

    # =========================================================
    # TRANSCRIPCIÓN DE AUDIO
    # =========================================================
    def transcribir_audio(self, audio_bytes, mime_type):
        """
        Transcribe audio de campo a texto.
        Fuerza al modelo a transcribir literalmente y evita que describa imágenes,
        videos o contexto visual asociado.
        """
        prompt = (
            "Transcribí literalmente el audio hablado por el usuario en español argentino.\n"
            "No describas el archivo.\n"
            "No describas imágenes ni video.\n"
            "No hagas resumen.\n"
            "No agregues timestamps.\n"
            "No traduzcas al inglés.\n"
            "No expliques lo que ocurre.\n"
            "No agregues interpretación técnica.\n"
            "Devolvé únicamente el texto hablado por el usuario.\n"
            "Si alguna palabra no se entiende, escribí [inaudible]."
        )

        res = self.client.models.generate_content(
            model=self.model_id,
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type=mime_type
                )
            ]
        )

        return res.text.strip()

    # =========================================================
    # QA SOBRE PDF
    # =========================================================
    def analizar_pdf_qa(self, pdf_bytes, prompt_p):
        res = self.client.models.generate_content(
            model=self.model_id,
            contents=[
                types.Part.from_bytes(
                    data=pdf_bytes,
                    mime_type="application/pdf"
                ),
                prompt_p
            ]
        )

        return res.text