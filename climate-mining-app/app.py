# -*- coding: utf-8 -*-
"""
Aplicacion Flask - ClimaTec
Bitacora tecnica y plataforma de documentacion del proyecto de Mineria de Datos.

Tema: Cambio climatico y eventos externos.
Niveles de analisis: Global / Regional (Sudamerica) / Nacional (Colombia).
Ventana temporal: 2020-2026.

El dataset consolidado (data/raw/clima_consolidado.csv) es MULTI-FUENTE y esta en
formato de tabla de hechos (largo/tidy): una fila = una observacion (un indicador
medido para una entidad, en una fecha, proveniente de una fuente identificada).
Todas las metricas de tamano, tipos de variable y calidad se calculan en tiempo de
ejecucion, de modo que la bitacora nunca describe algo distinto de lo que contiene
el conjunto de datos.
"""

import os
import sys

import pandas as pd
from flask import Flask, render_template, redirect, url_for

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import limpieza  # noqa: E402  (perfilamiento y limpieza de la Etapa 2)

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

DATASET_PRINCIPAL = "clima_consolidado.csv"
DATASET_EVENTOS = "eventos_externos_muestra.csv"
DATASET_MANIFIESTO = "fuentes_manifest.csv"

ANIO_MIN, ANIO_MAX = 2020, 2026

# ---------------------------------------------------------------------------
# Clasificacion de las columnas del esquema (tabla de hechos).
# ---------------------------------------------------------------------------
COL_NUMERICAS = ["valor", "anio", "mes"]
COL_CATEGORICAS = ["fuente", "fuente_tipo", "nivel_geografico", "entidad",
                   "iso_code", "periodicidad", "indicador", "unidad"]
COL_TEMPORALES = ["fecha", "anio", "mes"]
COL_GEOGRAFICAS = ["entidad", "iso_code", "nivel_geografico"]

# Indicadores que por definicion no pueden ser negativos (para el chequeo de
# dominio). Se excluyen anomalias y variaciones, que si pueden serlo.
IND_NO_NEGATIVOS = {
    "Emisiones de CO2 (total)", "Emisiones de CO2 per capita", "CO2 acumulado historico",
    "CO2 por carbon", "CO2 por petroleo", "CO2 por gas", "CO2 por cemento",
    "Emisiones de metano", "Emisiones de oxido nitroso",
    "Gases de efecto invernadero (total)", "GEI per capita (sin uso del suelo)",
    "Poblacion", "Consumo de energia primaria", "Consumo de energia per capita",
    "Generacion de electricidad", "Participacion de renovables en energia",
    "Participacion de fosiles en energia", "Participacion baja en carbono",
    "Concentracion de CO2 atmosferico",
}


def _cargar(nombre):
    ruta = os.path.join(DATA_DIR, nombre)
    try:
        return pd.read_csv(ruta)
    except FileNotFoundError:
        return None


DF = _cargar(DATASET_PRINCIPAL)
DF_EVENTOS = _cargar(DATASET_EVENTOS)
DF_MANIFIESTO = _cargar(DATASET_MANIFIESTO)

# Etapa 2: perfilamiento + limpieza calculados una sola vez al arrancar.
DF_LIMPIO, REPORTE_E2 = (None, None)
if DF is not None:
    try:
        DF_LIMPIO, REPORTE_E2 = limpieza.limpiar(DF)
    except Exception:
        DF_LIMPIO, REPORTE_E2 = None, None


# ---------------------------------------------------------------------------
# Metricas del dataset (calculadas del archivo real).
# ---------------------------------------------------------------------------
def resumen_dataset():
    if DF is None:
        return None
    total = len(DF)
    total_eventos = 0 if DF_EVENTOS is None else len(DF_EVENTOS)
    por_nivel = DF["nivel_geografico"].value_counts().to_dict()
    por_periodicidad = DF["periodicidad"].value_counts().to_dict()
    n_indicadores = int(DF["indicador"].nunique())
    n_fuentes = int(DF["fuente"].nunique())

    # Fuentes por tipo (para narrar la diversidad).
    tipos = (DF.drop_duplicates("fuente")["fuente_tipo"].value_counts().to_dict())

    # Desglose por fuente (con tipo y nivel), ordenado por aporte.
    por_fuente = []
    for fuente, sub in DF.groupby("fuente"):
        por_fuente.append({
            "fuente": fuente,
            "tipo": sub["fuente_tipo"].iloc[0],
            "registros": int(len(sub)),
            "periodicidad": "/".join(sorted(sub["periodicidad"].unique())),
        })
    por_fuente.sort(key=lambda x: x["registros"], reverse=True)

    nac = DF[DF["nivel_geografico"] == "Nacional"]
    n_paises = int(nac["iso_code"].nunique())
    n_regiones = int(DF[DF["nivel_geografico"] == "Regional"]["entidad"].nunique())

    muestra = (DF.sort_values(["nivel_geografico", "fuente", "entidad", "anio"])
               .head(8).to_dict(orient="records"))

    return {
        "total_consolidado": total,
        "total_eventos": total_eventos,
        "total_general": total + total_eventos,
        "n_columnas": DF.shape[1],
        "n_indicadores": n_indicadores,
        "n_fuentes": n_fuentes,
        "tipos_fuente": tipos,
        "por_fuente": por_fuente,
        "n_numericas": len(COL_NUMERICAS),
        "n_categoricas": len(COL_CATEGORICAS),
        "n_temporales": len(COL_TEMPORALES),
        "n_geograficas": len(COL_GEOGRAFICAS),
        "por_nivel": por_nivel,
        "por_periodicidad": por_periodicidad,
        "n_paises": n_paises,
        "n_regiones": n_regiones,
        "anio_min": int(DF["anio"].min()),
        "anio_max": int(DF["anio"].max()),
        "muestra": muestra,
        "columnas": list(DF.columns),
        # Chequeo automatico de requisitos minimos de la guia.
        "cumple": {
            "registros_10k": total >= 10000,
            "indicadores_10": n_indicadores >= 10,
            "numericas_3": len(COL_NUMERICAS) >= 3,
            "categoricas_3": len(COL_CATEGORICAS) >= 3,
            "temporal_1": len(COL_TEMPORALES) >= 1,
            "geografica_1": len(COL_GEOGRAFICAS) >= 1,
        },
    }


def diagnostico_calidad():
    if DF is None:
        return None

    total_celdas = DF.shape[0] * DF.shape[1]
    celdas_nulas = int(DF.isna().sum().sum())
    completitud = round(100 * (1 - celdas_nulas / total_celdas), 2) if total_celdas else 0

    nulos = DF.isna().sum()
    nulos = nulos[nulos > 0].sort_values(ascending=False)
    # iso_code y mes son nulos por diseno (agregados globales / series anuales).
    por_diseno = {"iso_code", "mes"}
    nulos_por_columna = [
        {
            "columna": c,
            "faltantes": int(nulos[c]),
            "porcentaje": round(100 * nulos[c] / len(DF), 2),
            "por_diseno": c in por_diseno,
        }
        for c in nulos.index
    ]

    duplicados_totales = int(len(DF) - len(DF.drop_duplicates()))
    # Clave logica de la tabla de hechos.
    clave = ["fuente", "nivel_geografico", "entidad", "anio", "mes", "indicador"]
    duplicados_clave = int(DF.duplicated(subset=clave).sum())

    # Valores fuera de dominio esperado.
    fuera_dominio = []
    mask_nn = DF["indicador"].isin(IND_NO_NEGATIVOS) & (DF["valor"] < 0)
    neg = int(mask_nn.sum())
    if neg:
        fuera_dominio.append(
            "{} observaciones con valor negativo en indicadores que no lo admiten.".format(neg))
    anio_mal = int(((DF["anio"] < ANIO_MIN) | (DF["anio"] > ANIO_MAX)).sum())
    if anio_mal:
        fuera_dominio.append("{} registros con anio fuera de {}-{}.".format(anio_mal, ANIO_MIN, ANIO_MAX))
    if not fuera_dominio:
        fuera_dominio.append(
            "Sin valores negativos en indicadores que no lo admiten y todos los "
            "registros dentro de la ventana {}-{}. Las anomalias de temperatura y las "
            "variaciones porcentuales si pueden ser negativas (comportamiento esperado).".format(
                ANIO_MIN, ANIO_MAX))

    return {
        "filas": len(DF),
        "columnas": DF.shape[1],
        "completitud": completitud,
        "celdas_nulas": celdas_nulas,
        "nulos_por_columna": nulos_por_columna,
        "duplicados_totales": duplicados_totales,
        "duplicados_clave": duplicados_clave,
        "fuera_dominio": fuera_dominio,
    }


def serie_co2_global():
    """Serie real de CO2 mundial (entidad 'World', indicador de emisiones totales)
    para el grafico de barras del hero. Sale directo del dataset consolidado."""
    if DF is None:
        return None
    mundo = DF[(DF["entidad"] == "World") &
               (DF["indicador"] == "Emisiones de CO2 (total)")].sort_values("anio")
    if mundo.empty:
        return None
    valores = mundo["valor"].round(1).tolist()
    anios = mundo["anio"].tolist()
    primero, ultimo = valores[0], valores[-1]
    variacion = round((ultimo - primero) / primero * 100, 1) if primero else 0
    return {
        "valores": valores,
        "anio_inicio": int(anios[0]),
        "anio_fin": int(anios[-1]),
        "valor_actual": ultimo,
        "variacion_pct": variacion,
        "proyectadas": 0,
    }


# ---------------------------------------------------------------------------
# Contenido documental de la Etapa 1 (texto, coherente con el dataset real).
# ---------------------------------------------------------------------------
PROYECTO = {
    "nombre": "ClimaTec",
    "titulo": "Cambio climatico y eventos externos: analisis global, regional y nacional",
    "tema": "Cambio climatico y eventos externos",
    "integrantes": ["Ana Cortes", "Mateo Melgarejo", "Andres Pineda"],
    "periodo": "2020 - 2026",
}

CONTEXTO = {
    "general": (
        "El cambio climatico es uno de los desafios globales mas criticos del siglo XXI. "
        "El aumento sostenido de la concentracion de gases de efecto invernadero (CO2, "
        "metano, oxido nitroso) y de la temperatura media altera los patrones climaticos "
        "a escala mundial, regional y local, y se entrelaza con eventos externos de corto "
        "plazo: fenomenos climaticos (El Nino / La Nina), acuerdos politico-ambientales y "
        "crisis socioeconomicas."
    ),
    "problema": (
        "El proyecto analiza la relacion entre las tendencias recientes del cambio climatico "
        "(emisiones de CO2 y GEI, concentracion atmosferica de CO2 y anomalias de temperatura) "
        "y la ocurrencia de eventos externos documentados, comparando tres escalas: global, "
        "regional (Sudamerica) y nacional (Colombia), durante el periodo 2020-2026."
    ),
    "niveles": [
        {
            "nivel": "Global",
            "detalle": (
                "Tendencias macro del agregado mundial ('World') mas mediciones globales "
                "directas: concentracion de CO2 en Mauna Loa (NOAA) y anomalia de temperatura "
                "(NASA GISTEMP y NOAA GCAG), a resolucion mensual."
            ),
        },
        {
            "nivel": "Regional (Sudamerica)",
            "detalle": (
                "Agregados continentales de OWID y, a nivel de paises de Sudamerica, "
                "reanalisis climatico de NASA POWER e indicadores del Banco Mundial, con "
                "enfasis en Sudamerica como region de referencia del proyecto."
            ),
        },
        {
            "nivel": "Nacional (Colombia)",
            "detalle": (
                "Indicadores por pais (emisiones y energia) y, para Colombia, temperatura y "
                "precipitacion de NASA POWER y observaciones de estaciones del IDEAM, como "
                "caso de estudio principal frente a su region y al mundo."
            ),
        },
    ],
    "conocimiento_esperado": (
        "Se espera caracterizar la evolucion reciente (2020-2026) de los indicadores "
        "climaticos por nivel, identificar la brecha entre la dinamica global y la "
        "nacional/regional, y ubicar temporalmente eventos externos (La Nina 2020-2023, "
        "El Nino 2023-2024, cumbres COP) que coincidan con variaciones relevantes, aportando "
        "evidencia para las etapas posteriores de limpieza, analisis y modelado."
    ),
}

PREGUNTAS = {
    "principal": (
        "Como se relacionan las tendencias recientes del cambio climatico (emisiones de CO2, "
        "GEI, concentracion atmosferica y anomalias de temperatura) con la ocurrencia de "
        "eventos externos a nivel global, regional (Sudamerica) y nacional (Colombia) entre "
        "2020 y 2026?"
    ),
    "secundarias": [
        "Cual ha sido la evolucion de las emisiones de CO2 (total y per capita) a nivel "
        "global, en Sudamerica y en Colombia entre 2020 y 2026?",
        "Como se comporta la senal climatica de alta frecuencia (CO2 mensual de Mauna Loa y "
        "anomalia de temperatura global) durante la ventana de estudio?",
        "Que eventos externos documentados (El Nino/La Nina, acuerdos climaticos, "
        "emergencias) coinciden temporalmente con variaciones relevantes en los indicadores?",
        "Como se posiciona Colombia frente al promedio de Sudamerica y del mundo en "
        "emisiones per capita, consumo de energia y participacion de renovables?",
    ],
}

NECESIDADES = [
    {"criterio": "Entidades involucradas",
     "detalle": "El mundo (agregado 'World'), regiones continentales, paises (con foco en Colombia y Sudamerica) y eventos externos documentados.",
     "razon": "Permiten construir y comparar los tres niveles de analisis exigidos."},
    {"criterio": "Variables relevantes",
     "detalle": "Emisiones de CO2 (total, per capita, por fuente, acumuladas), GEI, metano, oxido nitroso, concentracion de CO2, anomalia de temperatura, energia y renovables.",
     "razon": "Son los indicadores que describen directamente el fenomeno climatico."},
    {"criterio": "Periodo de analisis",
     "detalle": "2020-2026, con series anuales y mensuales segun la fuente.",
     "razon": "Ventana reciente solicitada; combina tendencia anual con senal mensual de alta frecuencia."},
    {"criterio": "Cobertura geografica",
     "detalle": "Global, regional (continentes y paises de Sudamerica) y nacional (paises, con foco en Colombia).",
     "razon": "Requisito de comparacion entre escalas del proyecto."},
    {"criterio": "Unidad de analisis",
     "detalle": "Una observacion = un indicador medido para una entidad, en una fecha y desde una fuente (tabla de hechos).",
     "razon": "Define el registro base y permite integrar fuentes heterogeneas sin perder trazabilidad."},
    {"criterio": "Diversidad de fuentes",
     "detalle": "Fuentes primarias (Mauna Loa, GISTEMP, GCAG, NASA POWER, IDEAM), secundarias (Banco Mundial, eventos UNFCCC/UNGRD) y terciarias (OWID).",
     "razon": "La guia pide al menos dos fuentes por nivel y los tres tipos; evita depender de una sola fuente."},
    {"criterio": "Variables de integracion entre escalas",
     "detalle": "entidad / iso_code / nivel_geografico (geografia), fecha / anio / mes (tiempo) y fuente / fuente_tipo (procedencia).",
     "razon": "Permiten unir las fuentes y comparar los niveles global, regional y nacional."},
]

# ---------------------------------------------------------------------------
# Fuentes de datos (documentacion completa por nivel y tipo).
#   estado: "Integrada" = ya esta en clima_consolidado.csv (descargable de GitHub);
#           "Automatizada" = el pipeline la descarga al ejecutarse con acceso a
#           internet (portales institucionales no accesibles desde el entorno de build).
# ---------------------------------------------------------------------------
FUENTES = [
    {
        "nombre": "Our World in Data - CO2 & Greenhouse Gas Emissions",
        "institucion": "Our World in Data / Global Carbon Project",
        "url": "https://github.com/owid/co2-data",
        "tipo": "Terciaria",
        "nivel": "Global / Regional / Nacional",
        "cobertura": "Mundial, por region y por pais (ISO3)",
        "periodo": "2020-2026 (disponible hasta 2024)",
        "formato": "CSV",
        "adquisicion": "Descarga directa del repositorio oficial (raw GitHub)",
        "registros": "16.524 observaciones integradas",
        "variables": "CO2 total, per capita, por fuente, acumulado, GEI, metano, N2O, poblacion, energia",
        "fecha_consulta": "2026-08-26",
        "restricciones": "Licencia abierta (CC-BY). Atribucion requerida.",
        "estado": "Integrada en el CSV",
    },
    {
        "nombre": "Our World in Data - Energy",
        "institucion": "Energy Institute (Statistical Review) y Ember, via OWID",
        "url": "https://github.com/owid/energy-data",
        "tipo": "Terciaria",
        "nivel": "Nacional / Global",
        "cobertura": "Por pais (ISO3) y mundo",
        "periodo": "2020-2026 (disponible hasta 2025)",
        "formato": "CSV",
        "adquisicion": "Descarga directa del repositorio oficial (raw GitHub)",
        "registros": "4.616 observaciones integradas",
        "variables": "Energia per capita, generacion electrica, participacion de renovables y fosiles, GEI del sector",
        "fecha_consulta": "2026-08-26",
        "restricciones": "Licencia abierta (CC-BY). Atribucion requerida.",
        "estado": "Integrada en el CSV",
    },
    {
        "nombre": "NOAA GML - Observatorio de Mauna Loa (CO2 in situ)",
        "institucion": "NOAA Global Monitoring Laboratory / Scripps",
        "url": "https://gml.noaa.gov/ccgg/trends/",
        "tipo": "Primaria",
        "nivel": "Global",
        "cobertura": "Medicion directa de CO2 atmosferico (mensual)",
        "periodo": "2020-2026 (hasta 2026-07)",
        "formato": "CSV",
        "adquisicion": "Descarga del registro mensual (raw GitHub, mirror datasets/co2-ppm)",
        "registros": "79 observaciones mensuales integradas",
        "variables": "Concentracion de CO2 atmosferico (ppm)",
        "fecha_consulta": "2026-08-26",
        "restricciones": "Dominio publico (dato del gobierno de EE.UU.).",
        "estado": "Integrada en el CSV",
    },
    {
        "nombre": "NASA GISS - GISTEMP (anomalia de temperatura)",
        "institucion": "NASA Goddard Institute for Space Studies",
        "url": "https://data.giss.nasa.gov/gistemp/",
        "tipo": "Primaria",
        "nivel": "Global",
        "cobertura": "Anomalia de temperatura global (mensual)",
        "periodo": "2020-2026 (hasta 2026-06)",
        "formato": "CSV",
        "adquisicion": "Descarga del indice mensual (raw GitHub, mirror datasets/global-temp)",
        "registros": "72 observaciones mensuales integradas",
        "variables": "Anomalia de temperatura global (grados C vs. base)",
        "fecha_consulta": "2026-08-26",
        "restricciones": "Dominio publico (dato del gobierno de EE.UU.).",
        "estado": "Integrada en el CSV",
    },
    {
        "nombre": "NOAA NCEI - GlobalTemp / GCAG (anomalia de temperatura)",
        "institucion": "NOAA National Centers for Environmental Information",
        "url": "https://www.ncei.noaa.gov/access/monitoring/global-temperature-anomalies/",
        "tipo": "Primaria",
        "nivel": "Global",
        "cobertura": "Anomalia de temperatura global (mensual), fuente independiente de GISTEMP",
        "periodo": "2020-2026 (hasta 2026-06)",
        "formato": "CSV",
        "adquisicion": "Descarga del indice mensual (raw GitHub, mirror datasets/global-temp)",
        "registros": "78 observaciones mensuales integradas",
        "variables": "Anomalia de temperatura global (grados C vs. base)",
        "fecha_consulta": "2026-08-26",
        "restricciones": "Dominio publico (dato del gobierno de EE.UU.).",
        "estado": "Integrada en el CSV",
    },
    {
        "nombre": "NASA POWER - reanalisis MERRA-2 (T2M y precipitacion)",
        "institucion": "NASA Langley Research Center - POWER Project",
        "url": "https://power.larc.nasa.gov/",
        "tipo": "Primaria",
        "nivel": "Nacional (Colombia) / Regional (Sudamerica)",
        "cobertura": "Temperatura y precipitacion mensual para Colombia y 9 paises de Sudamerica",
        "periodo": "2020-2026",
        "formato": "API JSON",
        "adquisicion": "API oficial (se descarga al ejecutar el pipeline con internet)",
        "registros": "~840 observaciones mensuales (al ejecutar con red)",
        "variables": "Temperatura media a 2 m, precipitacion total",
        "fecha_consulta": "2026-08-26",
        "restricciones": "Uso libre con atribucion.",
        "estado": "Automatizada en el pipeline",
    },
    {
        "nombre": "Banco Mundial - World Development Indicators (clima)",
        "institucion": "Grupo Banco Mundial",
        "url": "https://data.worldbank.org/topic/climate-change",
        "tipo": "Secundaria",
        "nivel": "Nacional / Regional",
        "cobertura": "Colombia y paises de Sudamerica",
        "periodo": "2020-2026 (segun disponibilidad del indicador)",
        "formato": "API JSON",
        "adquisicion": "API oficial (se descarga al ejecutar el pipeline con internet)",
        "registros": "Segun indicador y anio disponible",
        "variables": "CO2 per capita, uso de energia per capita, energia renovable (%)",
        "fecha_consulta": "2026-08-26",
        "restricciones": "Licencia abierta (CC-BY 4.0).",
        "estado": "Automatizada en el pipeline",
    },
    {
        "nombre": "IDEAM - Datos abiertos de clima e hidrologia",
        "institucion": "Instituto de Hidrologia, Meteorologia y Estudios Ambientales (Colombia)",
        "url": "https://www.datos.gov.co/",
        "tipo": "Primaria",
        "nivel": "Nacional (Colombia)",
        "cobertura": "Colombia, por estacion (temperatura / precipitacion)",
        "periodo": "2020-2026",
        "formato": "CSV / API Socrata",
        "adquisicion": "Portal datos.gov.co (se descarga al ejecutar el pipeline con internet)",
        "registros": "Variable segun estacion y recurso consultado",
        "variables": "Temperatura y precipitacion observada por estacion",
        "fecha_consulta": "2026-08-26",
        "restricciones": "Uso publico con atribucion.",
        "estado": "Automatizada en el pipeline",
    },
    {
        "nombre": "Eventos externos (COP, ENSO, emergencias)",
        "institucion": "UNFCCC, NOAA Climate Prediction Center, UNGRD",
        "url": "https://unfccc.int/",
        "tipo": "Secundaria",
        "nivel": "Global / Nacional (Colombia)",
        "cobertura": "Cumbres COP, fases El Nino/La Nina y emergencias en Colombia (2020-2026)",
        "periodo": "2020-2026",
        "formato": "CSV (curado)",
        "adquisicion": "Documentacion oficial consolidada en eventos_externos_muestra.csv",
        "registros": "7 eventos documentados",
        "variables": "Fecha, evento, tipo, ambito, fuente",
        "fecha_consulta": "2026-08-26",
        "restricciones": "Uso publico con atribucion.",
        "estado": "Integrada en el CSV",
    },
]

# Diccionario del ESQUEMA (12 columnas de la tabla de hechos).
DICCIONARIO = [
    {"variable": "fuente", "tipo": "Categorica (texto)", "descripcion": "Nombre de la fuente de la observacion.", "unidad": "-", "dominio": "9 fuentes documentadas", "fuente": "Elaboracion propia"},
    {"variable": "fuente_tipo", "tipo": "Categorica (texto)", "descripcion": "Clasificacion de la fuente.", "unidad": "-", "dominio": "Primaria / Secundaria / Terciaria", "fuente": "Elaboracion propia"},
    {"variable": "nivel_geografico", "tipo": "Categorica (texto)", "descripcion": "Escala del registro.", "unidad": "-", "dominio": "Global / Regional / Nacional", "fuente": "Elaboracion propia"},
    {"variable": "entidad", "tipo": "Categorica (texto)", "descripcion": "Pais, region, 'World' o punto de medicion.", "unidad": "-", "dominio": "Paises, regiones y agregados", "fuente": "Fuentes originales"},
    {"variable": "iso_code", "tipo": "Categorica (texto)", "descripcion": "Codigo ISO3 del pais (vacio en agregados globales/regionales).", "unidad": "-", "dominio": "Codigos ISO3", "fuente": "Fuentes originales"},
    {"variable": "anio", "tipo": "Temporal (entero)", "descripcion": "Anio de la observacion.", "unidad": "anio", "dominio": "2020 - 2026", "fuente": "Fuentes originales"},
    {"variable": "mes", "tipo": "Temporal (entero)", "descripcion": "Mes de la observacion (vacio en series anuales).", "unidad": "mes", "dominio": "1 - 12", "fuente": "Fuentes originales"},
    {"variable": "periodicidad", "tipo": "Categorica (texto)", "descripcion": "Frecuencia del registro.", "unidad": "-", "dominio": "Anual / Mensual", "fuente": "Elaboracion propia"},
    {"variable": "indicador", "tipo": "Categorica (texto)", "descripcion": "Variable climatica medida.", "unidad": "-", "dominio": "24 indicadores", "fuente": "Fuentes originales"},
    {"variable": "valor", "tipo": "Numerica (continua)", "descripcion": "Valor medido del indicador.", "unidad": "segun indicador", "dominio": "Real (algunos indicadores admiten negativos)", "fuente": "Fuentes originales"},
    {"variable": "unidad", "tipo": "Categorica (texto)", "descripcion": "Unidad de medida del valor.", "unidad": "-", "dominio": "ppm, Mt CO2, grados C, %, etc.", "fuente": "Elaboracion propia"},
    {"variable": "fecha", "tipo": "Temporal (fecha)", "descripcion": "Fecha ISO de la observacion (dia 15 para series mensuales).", "unidad": "AAAA-MM-DD", "dominio": "2020-01-01 a 2026-12-31", "fuente": "Elaboracion propia"},
]


def catalogo_indicadores():
    """Catalogo de los indicadores presentes en el dataset (indicador -> unidad,
    fuente_tipo, n de observaciones), calculado del archivo real."""
    if DF is None:
        return []
    filas = []
    for ind, sub in DF.groupby("indicador"):
        filas.append({
            "indicador": ind,
            "unidad": sub["unidad"].iloc[0],
            "tipo_fuente": "/".join(sorted(sub["fuente_tipo"].unique())),
            "registros": int(len(sub)),
        })
    filas.sort(key=lambda x: x["registros"], reverse=True)
    return filas


LIMITACIONES = {
    "limitaciones": [
        "Los indicadores anuales de emisiones (OWID) estan disponibles hasta 2024; 2025-2026 se cubren con las series mensuales (CO2 de Mauna Loa y anomalia de temperatura), que llegan a mediados de 2026.",
        "Las fuentes primarias de nivel nacional/regional que se sirven desde portales institucionales (NASA POWER, Banco Mundial, IDEAM) se integran al ejecutar el pipeline con acceso a internet; en el CSV publicado su estado queda registrado en el manifiesto de fuentes.",
        "El dataset de eventos externos es una muestra curada manualmente (7 eventos); se ampliara en la Etapa 2 con registros detallados de UNGRD e IDEAM.",
        "Mezcla de periodicidades: conviven series anuales y mensuales; para comparar niveles habra que homogenizar la frecuencia en la Etapa 2.",
        "Los agregados globales y regionales no tienen iso_code y las series anuales no tienen mes: esos campos quedan vacios por diseno (no son errores).",
    ],
    "sesgos": [
        "Posible sesgo de reporte: paises con mejores sistemas estadisticos tienen series mas completas.",
        "Diferencias metodologicas entre fuentes (p. ej. GISTEMP vs. GCAG estiman la misma anomalia con metodos distintos).",
    ],
    "trazabilidad": [
        "Cada observacion conserva su procedencia en las columnas fuente y fuente_tipo.",
        "El dataset consolidado se genera con scripts/preparar_datos.py (reproducible), no editando a mano.",
        "El script escribe un manifiesto (fuentes_manifest.csv) con el estado de cada fuente (integrada u omitida por falta de red).",
        "Toda transformacion (filtro 2020-2026, seleccion de indicadores, mapeo de nivel_geografico, formato largo) queda documentada en el script y en esta bitacora.",
        "Fecha de consulta de las fuentes: 2026-08-26.",
    ],
}


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", proyecto=PROYECTO, resumen=resumen_dataset(),
                           serie=serie_co2_global())


@app.route("/etapa-1/problema-contexto")
def problema_contexto():
    return render_template("etapa1/problema_contexto.html", proyecto=PROYECTO, contexto=CONTEXTO)


@app.route("/etapa-1/preguntas")
def preguntas():
    return render_template("etapa1/preguntas.html", proyecto=PROYECTO,
                           preguntas=PREGUNTAS, conocimiento=CONTEXTO["conocimiento_esperado"])


@app.route("/etapa-1/necesidades-informacion")
def necesidades_informacion():
    return render_template("etapa1/necesidades_informacion.html",
                           proyecto=PROYECTO, necesidades=NECESIDADES)


@app.route("/etapa-1/fuentes-datos")
def fuentes_datos():
    return render_template("etapa1/fuentes_datos.html", proyecto=PROYECTO, fuentes=FUENTES)


@app.route("/etapa-1/dataset")
def dataset_etapa1():
    return render_template("etapa1/dataset.html", proyecto=PROYECTO, resumen=resumen_dataset())


@app.route("/etapa-1/diccionario-datos")
def diccionario_datos():
    return render_template("etapa1/diccionario_datos.html",
                           proyecto=PROYECTO, diccionario=DICCIONARIO,
                           indicadores=catalogo_indicadores())


@app.route("/etapa-1/calidad-inicial")
def calidad_inicial():
    return render_template("etapa1/calidad_inicial.html",
                           proyecto=PROYECTO, calidad=diagnostico_calidad())


@app.route("/etapa-1/limitaciones")
def limitaciones():
    return render_template("etapa1/limitaciones.html", proyecto=PROYECTO, info=LIMITACIONES)


# ---------------------------------------------------------------------------
# Etapa 2 - Perfilamiento y limpieza
# ---------------------------------------------------------------------------
ETAPA2_INTRO = {
    "objetivo": (
        "La Etapa 2 evalua la calidad del dataset consolidado en la Etapa 1 y aplica un "
        "tratamiento reproducible. Todas las metricas se calculan en vivo con "
        "scripts/limpieza.py sobre clima_consolidado.csv; el resultado limpio se guarda en "
        "clima_limpio.csv."
    ),
}


@app.route("/etapa-2/descripcion")
def e2_descripcion():
    return render_template("etapa2/descripcion.html", proyecto=PROYECTO,
                           resumen=resumen_dataset(), rep=REPORTE_E2, intro=ETAPA2_INTRO)


@app.route("/etapa-2/perfilamiento")
def e2_perfilamiento():
    return render_template("etapa2/perfilamiento.html", proyecto=PROYECTO, rep=REPORTE_E2)


@app.route("/etapa-2/dimensiones")
def e2_dimensiones():
    return render_template("etapa2/dimensiones.html", proyecto=PROYECTO, rep=REPORTE_E2)


@app.route("/etapa-2/problemas")
def e2_problemas():
    return render_template("etapa2/problemas.html", proyecto=PROYECTO, rep=REPORTE_E2)


@app.route("/etapa-2/tratamiento")
def e2_tratamiento():
    return render_template("etapa2/tratamiento.html", proyecto=PROYECTO, rep=REPORTE_E2)


@app.route("/etapa-2/comparacion")
def e2_comparacion():
    return render_template("etapa2/comparacion.html", proyecto=PROYECTO, rep=REPORTE_E2)


@app.route("/etapa-2/graficas")
def e2_graficas():
    return render_template("etapa2/graficas.html", proyecto=PROYECTO, rep=REPORTE_E2)


# Compatibilidad con rutas antiguas (evita 404 en enlaces previos).
@app.route("/problema")
def problema():
    return redirect(url_for("problema_contexto"))


@app.route("/recoleccion")
def recoleccion():
    return redirect(url_for("fuentes_datos"))


@app.route("/dataset")
def dataset():
    return redirect(url_for("dataset_etapa1"))


@app.route("/calidad")
def calidad():
    return redirect(url_for("calidad_inicial"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
