"""
Aplicacion Flask - ClimaTec
Bitacora tecnica y plataforma de documentacion del proyecto de Mineria de Datos.

Tema: Cambio climatico y eventos externos.
Niveles de analisis: Global / Regional (continentes, incl. Sudamerica) / Nacional
(paises, con foco en Colombia).

Toda la seccion "Etapa 1" se documenta a partir del dataset REAL
(data/raw/clima_consolidado.csv). Las metricas de tamano, tipos de variable y
calidad inicial se calculan en tiempo de ejecucion, de modo que la bitacora
nunca describe algo distinto de lo que contiene el conjunto de datos.
"""

import os
from datetime import date

import pandas as pd
from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

DATASET_PRINCIPAL = "clima_consolidado.csv"
DATASET_EVENTOS = "eventos_externos_muestra.csv"

# ---------------------------------------------------------------------------
# Clasificacion de variables del dataset consolidado.
# ---------------------------------------------------------------------------
VARIABLES_NUMERICAS = [
    "population", "co2", "co2_per_capita", "co2_growth_prct", "cumulative_co2",
    "ghg_excluding_lucf_per_capita", "temperature_change_from_ghg",
    "temperature_change_from_co2", "methane", "nitrous_oxide",
    "primary_energy_consumption",
]
VARIABLES_CATEGORICAS = ["country", "iso_code", "nivel_geografico"]
VARIABLES_TEMPORALES = ["year"]
VARIABLES_GEOGRAFICAS = ["country", "iso_code", "nivel_geografico"]


def _cargar(nombre):
    ruta = os.path.join(DATA_DIR, nombre)
    try:
        return pd.read_csv(ruta)
    except FileNotFoundError:
        return None


# Se cargan una sola vez al arrancar (rendimiento en Render free tier).
DF = _cargar(DATASET_PRINCIPAL)
DF_EVENTOS = _cargar(DATASET_EVENTOS)


# ---------------------------------------------------------------------------
# Metricas del dataset (calculadas del archivo real).
# ---------------------------------------------------------------------------
def resumen_dataset():
    if DF is None:
        return None
    total_consolidado = len(DF)
    total_eventos = 0 if DF_EVENTOS is None else len(DF_EVENTOS)
    por_nivel = DF["nivel_geografico"].value_counts().to_dict()
    paises = int(DF[DF["nivel_geografico"] == "Nacional"]["country"].nunique())
    regiones = int(DF[DF["nivel_geografico"] == "Regional"]["country"].nunique())

    return {
        "total_consolidado": total_consolidado,
        "total_eventos": total_eventos,
        "total_general": total_consolidado + total_eventos,
        "n_variables": DF.shape[1],
        "n_numericas": len(VARIABLES_NUMERICAS),
        "n_categoricas": len(VARIABLES_CATEGORICAS),
        "n_temporales": len(VARIABLES_TEMPORALES),
        "n_geograficas": len(VARIABLES_GEOGRAFICAS),
        "por_nivel": por_nivel,
        "n_paises": paises,
        "n_regiones": regiones,
        "anio_min": int(DF["year"].min()),
        "anio_max": int(DF["year"].max()),
        "muestra": DF.sort_values(["nivel_geografico", "country", "year"])
        .head(8)
        .to_dict(orient="records"),
        "columnas": list(DF.columns),
        # Chequeo automatico de requisitos minimos de la guia.
        "cumple": {
            "registros_10k": total_consolidado >= 10000,
            "variables_10": DF.shape[1] >= 10,
            "numericas_3": len(VARIABLES_NUMERICAS) >= 3,
            "categoricas_3": len(VARIABLES_CATEGORICAS) >= 3,
            "temporal_1": len(VARIABLES_TEMPORALES) >= 1,
            "geografica_1": len(VARIABLES_GEOGRAFICAS) >= 1,
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
    nulos_por_columna = [
        {
            "columna": c,
            "faltantes": int(nulos[c]),
            "porcentaje": round(100 * nulos[c] / len(DF), 2),
        }
        for c in nulos.index
    ]

    duplicados_totales = int(len(DF) - len(DF.drop_duplicates()))
    # Clave logica del dataset: nivel + pais + anio.
    clave = ["nivel_geografico", "country", "year"]
    duplicados_clave = int(DF.duplicated(subset=clave).sum())

    # Valores fuera de dominio esperado.
    anio_actual = date.today().year
    fuera_dominio = []
    neg_co2 = int((DF["co2"] < 0).sum())
    if neg_co2:
        fuera_dominio.append("{} registros con co2 < 0 (no valido).".format(neg_co2))
    neg_pc = int((DF["co2_per_capita"] < 0).sum())
    if neg_pc:
        fuera_dominio.append("{} registros con co2_per_capita < 0 (no valido).".format(neg_pc))
    anio_mal = int(((DF["year"] < 1950) | (DF["year"] > anio_actual)).sum())
    if anio_mal:
        fuera_dominio.append("{} registros con year fuera de 1950-{}.".format(anio_mal, anio_actual))
    if not fuera_dominio:
        fuera_dominio.append(
            "No se detectaron valores negativos en co2 / co2_per_capita ni anios "
            "fuera del rango 1950-{}.".format(anio_actual)
        )

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
    """Serie real de CO2 mundial (fila 'World'), anio a anio, para el
    grafico de barras del hero de inicio. Nunca son numeros inventados:
    salen directo del dataset consolidado."""
    if DF is None:
        return None
    mundo = DF[DF["country"] == "World"].sort_values("year")
    if mundo.empty:
        return None

    valores = mundo["co2"].round(1).tolist()
    anios = mundo["year"].tolist()
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
    "periodo": "1950 - 2024",
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
        "El proyecto delimita el analisis a la relacion entre las tendencias de largo plazo "
        "del cambio climatico (emisiones de CO2, GEI y su contribucion al calentamiento) y la "
        "ocurrencia de eventos externos documentados, comparando tres escalas: global, "
        "regional (continentes, con enfasis en Sudamerica) y nacional (paises, con foco en "
        "Colombia), durante el periodo 1950-2024."
    ),
    "niveles": [
        {
            "nivel": "Global",
            "detalle": (
                "Tendencias macro de emisiones de CO2, GEI y contribucion al cambio de "
                "temperatura para el agregado mundial ('World')."
            ),
        },
        {
            "nivel": "Regional (Sudamerica)",
            "detalle": (
                "Comportamiento de los agregados continentales (Africa, Asia, Europa, "
                "Norteamerica, Oceania y Sudamerica), con enfasis en Sudamerica como region "
                "de referencia del proyecto."
            ),
        },
        {
            "nivel": "Nacional (Colombia)",
            "detalle": (
                "Indicadores por pais (218 paises con codigo ISO3), con Colombia como caso "
                "de estudio principal comparado frente a su region y al mundo."
            ),
        },
    ],
    "conocimiento_esperado": (
        "Se espera caracterizar la evolucion de los indicadores climaticos por nivel, "
        "identificar la brecha entre la dinamica global y la nacional/regional, y ubicar "
        "temporalmente eventos externos que coincidan con variaciones relevantes, aportando "
        "evidencia para las etapas posteriores de limpieza, analisis y modelado."
    ),
}

PREGUNTAS = {
    "principal": (
        "Como se relacionan las tendencias del cambio climatico (emisiones de CO2, GEI y su "
        "contribucion a la temperatura) con la ocurrencia de eventos externos a nivel global, "
        "regional (Sudamerica) y nacional (Colombia) entre 1950 y 2024?"
    ),
    "secundarias": [
        "Cual ha sido la evolucion de las emisiones de CO2 (total y per capita) a nivel "
        "global, en Sudamerica y en Colombia dentro del periodo disponible?",
        "Existen diferencias significativas en la magnitud y velocidad del cambio de "
        "temperatura atribuible a GEI entre el nivel global, el regional y el nacional?",
        "Que eventos externos documentados (El Nino/La Nina, acuerdos climaticos, "
        "emergencias) coinciden temporalmente con variaciones relevantes en los indicadores?",
        "Como se posiciona Colombia frente al promedio de Sudamerica y del mundo en "
        "emisiones per capita y consumo de energia primaria?",
    ],
}

NECESIDADES = [
    {"criterio": "Entidades involucradas",
     "detalle": "El mundo (agregado 'World'), 6 regiones continentales y 218 paises; ademas, eventos externos documentados.",
     "razon": "Permiten construir y comparar los tres niveles de analisis exigidos."},
    {"criterio": "Variables relevantes",
     "detalle": "Emisiones de CO2 (total, per capita, crecimiento, acumuladas), GEI y su contribucion a la temperatura, metano, oxido nitroso, poblacion y energia primaria.",
     "razon": "Son los indicadores que describen directamente el fenomeno climatico."},
    {"criterio": "Periodo de analisis",
     "detalle": "1950-2024 (serie temporal anual).",
     "razon": "Rango con buena completitud que cubre la aceleracion moderna de emisiones."},
    {"criterio": "Cobertura geografica",
     "detalle": "Global, regional (continentes) y nacional (paises), con enfasis en Sudamerica y Colombia.",
     "razon": "Requisito de comparacion entre escalas del proyecto."},
    {"criterio": "Poblacion / unidad de analisis",
     "detalle": "Una combinacion entidad-anio (pais/region/mundo en un anio dado).",
     "razon": "Define el registro base sobre el que se miden todas las variables."},
    {"criterio": "Granularidad",
     "detalle": "Anual por entidad; no se trabaja solo con agregados: el nivel nacional aporta ~16.350 registros pais-anio.",
     "razon": "La guia pide evitar datos excesivamente agregados."},
    {"criterio": "Variables de integracion entre escalas",
     "detalle": "country / iso_code / nivel_geografico (geografia) y year (tiempo).",
     "razon": "Permiten unir las fuentes y comparar los niveles global, regional y nacional."},
]

FUENTES = [
    {
        "nombre": "Our World in Data - CO2 and Greenhouse Gas Emissions",
        "institucion": "Our World in Data / Global Carbon Project",
        "url": "https://github.com/owid/co2-data",
        "tipo": "Terciaria (compilacion curada de multiples fuentes primarias)",
        "nivel": "Global / Regional / Nacional",
        "cobertura": "Mundial, por pais y por region",
        "periodo": "1750-2024 (usado 1950-2024)",
        "formato": "CSV",
        "adquisicion": "Descarga directa del repositorio oficial (raw GitHub)",
        "registros": "50.411 filas originales -> 16.875 tras filtro/mapeo",
        "variables": "79 columnas originales -> 14 seleccionadas + nivel_geografico",
        "fecha_consulta": "2026-08-25",
        "restricciones": "Licencia abierta (CC-BY). Atribucion requerida.",
    },
    {
        "nombre": "IDEAM - Datos abiertos de clima e hidrologia",
        "institucion": "Instituto de Hidrologia, Meteorologia y Estudios Ambientales (Colombia)",
        "url": "http://www.ideam.gov.co",
        "tipo": "Primaria (red de estaciones meteorologicas e hidrologicas)",
        "nivel": "Nacional (Colombia)",
        "cobertura": "Colombia, por estacion / departamento",
        "periodo": "Historico y boletines periodicos",
        "formato": "CSV / Excel / servicios web",
        "adquisicion": "Portal de datos abiertos (a integrar en Etapa 2)",
        "registros": "Variable segun estacion y variable consultada",
        "variables": "Temperatura, precipitacion, humedad, nivel de rios",
        "fecha_consulta": "2026-08-25",
        "restricciones": "Uso publico con atribucion.",
    },
    {
        "nombre": "NOAA - Climate / ENSO (El Nino - La Nina)",
        "institucion": "National Oceanic and Atmospheric Administration (EE.UU.)",
        "url": "https://www.noaa.gov",
        "tipo": "Primaria (mediciones satelitales y oceanicas)",
        "nivel": "Global / Regional",
        "cobertura": "Global, con foco en el Pacifico para ENSO",
        "periodo": "Series historicas continuas",
        "formato": "CSV / NetCDF / servicios web",
        "adquisicion": "Descarga de indices oficiales (a integrar en Etapa 2)",
        "registros": "Indices mensuales/anuales de ENSO",
        "variables": "ONI, SST, indices de temperatura del oceano",
        "fecha_consulta": "2026-08-25",
        "restricciones": "Dominio publico (dato del gobierno de EE.UU.).",
    },
    {
        "nombre": "UNGRD - Registros de emergencias y desastres",
        "institucion": "Unidad Nacional para la Gestion del Riesgo de Desastres (Colombia)",
        "url": "https://www.gestiondelriesgo.gov.co",
        "tipo": "Secundaria (registros administrativos)",
        "nivel": "Nacional (Colombia)",
        "cobertura": "Colombia, por evento / municipio",
        "periodo": "Actualizacion continua",
        "formato": "CSV / Excel / tableros",
        "adquisicion": "Portal institucional (a integrar en Etapa 2)",
        "registros": "Miles de registros de eventos",
        "variables": "Tipo de evento, fecha, ubicacion, afectacion",
        "fecha_consulta": "2026-08-25",
        "restricciones": "Uso publico con atribucion.",
    },
    {
        "nombre": "UNFCCC - Acuerdos y cumbres climaticas (COP)",
        "institucion": "Convencion Marco de las Naciones Unidas sobre el Cambio Climatico",
        "url": "https://unfccc.int",
        "tipo": "Secundaria (documentacion oficial de politicas/eventos)",
        "nivel": "Global",
        "cobertura": "Global",
        "periodo": "Eventos historicos documentados",
        "formato": "Documentos / web",
        "adquisicion": "Consulta documental (base del dataset de eventos)",
        "registros": "Eventos discretos (COP, acuerdos)",
        "variables": "Nombre del acuerdo, fecha, alcance",
        "fecha_consulta": "2026-08-25",
        "restricciones": "Uso publico con atribucion.",
    },
]

DICCIONARIO = [
    {"variable": "country", "tipo": "Categorica (texto)", "descripcion": "Pais, region agregada o 'World'.", "unidad": "-", "dominio": "218 paises + 6 regiones + World", "fuente": "OWID"},
    {"variable": "year", "tipo": "Temporal (entero)", "descripcion": "Anio de referencia del registro.", "unidad": "anio", "dominio": "1950 - 2024", "fuente": "OWID"},
    {"variable": "iso_code", "tipo": "Categorica (texto)", "descripcion": "Codigo ISO3 del pais (vacio en agregados regionales y World).", "unidad": "-", "dominio": "Codigos ISO3", "fuente": "OWID"},
    {"variable": "nivel_geografico", "tipo": "Categorica (texto)", "descripcion": "Escala del registro: Global, Regional o Nacional (variable creada por el equipo).", "unidad": "-", "dominio": "Global / Regional / Nacional", "fuente": "Elaboracion propia"},
    {"variable": "population", "tipo": "Numerica (entero)", "descripcion": "Poblacion total estimada.", "unidad": "personas", "dominio": ">= 0", "fuente": "OWID / ONU"},
    {"variable": "co2", "tipo": "Numerica (continua)", "descripcion": "Emisiones anuales totales de CO2 (produccion).", "unidad": "millones de toneladas", "dominio": ">= 0", "fuente": "Global Carbon Project via OWID"},
    {"variable": "co2_per_capita", "tipo": "Numerica (continua)", "descripcion": "Emisiones de CO2 por habitante.", "unidad": "t / persona", "dominio": ">= 0", "fuente": "OWID"},
    {"variable": "co2_growth_prct", "tipo": "Numerica (continua)", "descripcion": "Variacion porcentual anual de las emisiones de CO2.", "unidad": "%", "dominio": "puede ser negativa", "fuente": "OWID"},
    {"variable": "cumulative_co2", "tipo": "Numerica (continua)", "descripcion": "Emisiones acumuladas historicas de CO2.", "unidad": "millones de toneladas", "dominio": ">= 0", "fuente": "OWID"},
    {"variable": "ghg_excluding_lucf_per_capita", "tipo": "Numerica (continua)", "descripcion": "GEI per capita (excluye uso del suelo).", "unidad": "t eq. CO2 / persona", "dominio": ">= 0", "fuente": "OWID"},
    {"variable": "temperature_change_from_ghg", "tipo": "Numerica (continua)", "descripcion": "Contribucion de todos los GEI al cambio de temperatura.", "unidad": "grados Celsius", "dominio": ">= 0", "fuente": "OWID"},
    {"variable": "temperature_change_from_co2", "tipo": "Numerica (continua)", "descripcion": "Contribucion del CO2 al cambio de temperatura.", "unidad": "grados Celsius", "dominio": ">= 0", "fuente": "OWID"},
    {"variable": "methane", "tipo": "Numerica (continua)", "descripcion": "Emisiones de metano.", "unidad": "Mt eq. CO2", "dominio": ">= 0", "fuente": "OWID"},
    {"variable": "nitrous_oxide", "tipo": "Numerica (continua)", "descripcion": "Emisiones de oxido nitroso.", "unidad": "Mt eq. CO2", "dominio": ">= 0", "fuente": "OWID"},
    {"variable": "primary_energy_consumption", "tipo": "Numerica (continua)", "descripcion": "Consumo de energia primaria.", "unidad": "TWh", "dominio": ">= 0", "fuente": "OWID"},
]

LIMITACIONES = {
    "limitaciones": [
        "Cobertura historica desigual: los indicadores mas completos empiezan hacia 1950; anios previos se excluyeron para no arrastrar vacios.",
        "Nulos en variables especificas (energia primaria, GEI) para paises pequenos o con reporte tardio.",
        "El dataset de eventos externos es aun una muestra documentada manualmente; se ampliara con IDEAM, NOAA y UNGRD en la Etapa 2.",
        "Granularidad anual: no permite analizar estacionalidad intra-anual (eventos como El Nino se veran a escala anual).",
        "Los agregados regionales y 'World' no tienen iso_code, por lo que ese campo queda vacio por diseno en esos registros.",
    ],
    "sesgos": [
        "Posible sesgo de reporte: paises con mejores sistemas estadisticos tienen series mas completas.",
        "Cambios metodologicos en la estimacion de emisiones a lo largo del tiempo.",
    ],
    "trazabilidad": [
        "Se conserva el archivo fuente original (owid-co2-data.csv) sin modificar, fuera del control de versiones por su tamano.",
        "El dataset consolidado se genera con scripts/preparar_datos.py (reproducible), no editando a mano.",
        "Toda transformacion (filtro year>=1950, seleccion de 14 columnas, mapeo de nivel_geografico) queda documentada en el script y en esta bitacora.",
        "Fecha de consulta de la fuente: 2026-08-25.",
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
                           proyecto=PROYECTO, diccionario=DICCIONARIO)


@app.route("/etapa-1/calidad-inicial")
def calidad_inicial():
    return render_template("etapa1/calidad_inicial.html",
                           proyecto=PROYECTO, calidad=diagnostico_calidad())


@app.route("/etapa-1/limitaciones")
def limitaciones():
    return render_template("etapa1/limitaciones.html", proyecto=PROYECTO, info=LIMITACIONES)


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
