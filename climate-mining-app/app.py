"""
Aplicacion Flask - Bitacora Tecnica del Proyecto
Mineria de datos: Cambio climatico y eventos externos
Niveles de analisis: Global / Regional (Sudamerica) / Nacional (Colombia)

Este archivo es la version base (R1) del proyecto. Sirve como bitacora
tecnica que documenta el problema, el proceso de recoleccion, el dataset
y la calidad inicial de los datos, tal como lo pide la guia de la
actividad. Se ira ampliando en entregas posteriores con limpieza,
transformacion, analisis y visualizaciones.
"""

import os
import pandas as pd
from flask import Flask, render_template

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

DATASETS = {
    "global": {
        "nombre": "Indicadores climaticos - Global (World)",
        "archivo": "global_climate_owid_1995_2024.csv",
        "nivel": "Global",
    },
    "regional": {
        "nombre": "Indicadores climaticos - Sudamerica",
        "archivo": "regional_sudamerica_owid_1995_2024.csv",
        "nivel": "Regional",
    },
    "nacional": {
        "nombre": "Indicadores climaticos - Colombia",
        "archivo": "nacional_colombia_owid_1960_2024.csv",
        "nivel": "Nacional",
    },
    "eventos": {
        "nombre": "Eventos externos (muestra documentada)",
        "archivo": "eventos_externos_muestra.csv",
        "nivel": "Global / Regional / Nacional",
    },
}


def cargar_dataset(clave):
    """Carga un dataset desde data/raw a partir de su clave en DATASETS."""
    info = DATASETS.get(clave)
    if info is None:
        return None, None
    ruta = os.path.join(DATA_DIR, info["archivo"])
    try:
        df = pd.read_csv(ruta)
    except FileNotFoundError:
        return None, info
    return df, info


def calcular_calidad(df):
    """Calcula metricas iniciales de calidad de datos sobre un DataFrame:
    completitud, unicidad y consistencia basica de tipos."""
    if df is None or df.empty:
        return None

    total_celdas = df.shape[0] * df.shape[1]
    celdas_nulas = int(df.isna().sum().sum())
    completitud = round(100 * (1 - celdas_nulas / total_celdas), 2) if total_celdas else 0

    filas_totales = len(df)
    filas_unicas = len(df.drop_duplicates())
    unicidad = round(100 * filas_unicas / filas_totales, 2) if filas_totales else 0

    columnas_numericas = df.select_dtypes(include="number").columns.tolist()
    columnas_texto = [c for c in df.columns if c not in columnas_numericas]

    nulos_por_columna = (
        df.isna().sum()[df.isna().sum() > 0]
        .sort_values(ascending=False)
        .to_dict()
    )

    return {
        "filas": filas_totales,
        "columnas": df.shape[1],
        "completitud": completitud,
        "unicidad": unicidad,
        "duplicados": filas_totales - filas_unicas,
        "columnas_numericas": len(columnas_numericas),
        "columnas_texto": len(columnas_texto),
        "nulos_por_columna": nulos_por_columna,
    }


# ---------------------------------------------------------------------------
# Contenido de la bitacora (documentacion del proyecto)
# Editar aqui a medida que el equipo defina/ajuste su problema.
# ---------------------------------------------------------------------------

PROYECTO = {
    "titulo": "Cambio climatico y eventos externos: un analisis global, regional y nacional",
    "problema_contexto": (
        "El cambio climatico se manifiesta en tendencias de largo plazo "
        "(temperatura, emisiones de gases de efecto invernadero, "
        "concentracion de CO2) que interactuan con eventos externos de "
        "corto plazo, tanto climaticos (El Nino / La Nina, olas de calor, "
        "temporadas de lluvias extremas) como socioeconomicos y politicos "
        "(acuerdos internacionales, crisis economicas, pandemias). "
        "El proyecto busca describir y relacionar estas dos dimensiones "
        "en tres escalas de analisis: global, regional (Sudamerica) y "
        "nacional (Colombia)."
    ),
    "pregunta_principal": (
        "Como se relacionan las tendencias del cambio climatico "
        "(emisiones de CO2, temperatura, gases de efecto invernadero) con "
        "la ocurrencia de eventos externos (climaticos, politicos y "
        "socioeconomicos) a nivel global, regional y nacional entre 1995 "
        "y 2024?"
    ),
    "preguntas_secundarias": [
        (
            "Cual ha sido la evolucion de los indicadores climaticos clave "
            "(CO2, CO2 per capita, cambio de temperatura atribuible a GEI) "
            "en el periodo disponible, a nivel global, en Sudamerica y en "
            "Colombia?"
        ),
        (
            "Que eventos externos documentados (fenomenos El Nino/La Nina, "
            "acuerdos climaticos internacionales, emergencias nacionales) "
            "coinciden temporalmente con variaciones relevantes en los "
            "indicadores climaticos?"
        ),
        (
            "Existen diferencias significativas en la magnitud y velocidad "
            "del cambio climatico entre el nivel global, el regional "
            "(Sudamerica) y el nacional (Colombia)?"
        ),
    ],
    "necesidades_informacion": [
        {
            "pregunta": "Evolucion de indicadores climaticos",
            "entidades": "Paises / regiones / el mundo, anios (serie temporal)",
            "atributos": (
                "co2, co2_per_capita, cumulative_co2, "
                "temperature_change_from_co2, temperature_change_from_ghg, "
                "metano, oxido nitroso, poblacion"
            ),
            "cobertura": "Global 1995-2024, Sudamerica 1995-2024, Colombia 1960-2024",
        },
        {
            "pregunta": "Eventos externos relevantes",
            "entidades": "Eventos (climaticos, politicos, socioeconomicos)",
            "atributos": (
                "fecha de inicio y fin, tipo de evento, escala geografica, "
                "pais/region, descripcion, fuente"
            ),
            "cobertura": "Muestra inicial 2010-2023 (a ampliar en siguientes entregas)",
        },
        {
            "pregunta": "Comparacion entre escalas",
            "entidades": "Global vs. Sudamerica vs. Colombia",
            "atributos": "Mismos indicadores climaticos, mismo periodo comun",
            "cobertura": "1995-2024 (interseccion de los tres niveles)",
        },
    ],
    "fuentes": [
        {
            "nombre": "Our World in Data - CO2 and Greenhouse Gas Emissions",
            "nivel": "Global / Regional / Nacional",
            "tipo_recoleccion": "Terciaria (compilacion curada de multiples fuentes primarias: Global Carbon Project, NOAA, etc.)",
            "url": "https://github.com/owid/co2-data",
            "pertinencia": "Alta - variables directamente relacionadas con emisiones y temperatura",
            "confiabilidad": "Alta - mantenida por Our World in Data / Global Carbon Project, uso academico extendido",
            "actualidad": "Actualizada anualmente, incluye datos hasta 2024",
            "cobertura": "Global, por pais y por region agregada, desde 1750 (variable segun indicador)",
        },
        {
            "nombre": "IDEAM (Instituto de Hidrologia, Meteorologia y Estudios Ambientales)",
            "nivel": "Nacional (Colombia)",
            "tipo_recoleccion": "Primaria (estaciones meteorologicas e hidrologicas)",
            "url": "http://www.ideam.gov.co",
            "pertinencia": "Alta - autoridad oficial de clima e hidrologia en Colombia",
            "confiabilidad": "Alta - entidad oficial del Estado colombiano",
            "actualidad": "Datos historicos y boletines periodicos",
            "cobertura": "Nacional, por estacion/departamento",
        },
        {
            "nombre": "UNGRD (Unidad Nacional para la Gestion del Riesgo de Desastres)",
            "nivel": "Nacional (Colombia)",
            "tipo_recoleccion": "Primaria/Secundaria (registros administrativos de emergencias)",
            "url": "https://www.gestiondelriesgo.gov.co",
            "pertinencia": "Alta - registro oficial de desastres y emergencias asociadas a eventos climaticos",
            "confiabilidad": "Alta - entidad oficial del Estado colombiano",
            "actualidad": "Actualizacion continua",
            "cobertura": "Nacional, por evento/municipio",
        },
        {
            "nombre": "NOAA - National Oceanic and Atmospheric Administration",
            "nivel": "Global / Regional",
            "tipo_recoleccion": "Primaria (mediciones satelitales y oceanicas)",
            "url": "https://www.noaa.gov",
            "pertinencia": "Alta - fuente de referencia mundial para El Nino/La Nina y clima",
            "confiabilidad": "Alta - agencia cientifica oficial de EE.UU.",
            "actualidad": "Actualizacion continua",
            "cobertura": "Global, con foco en el Pacifico para ENSO",
        },
        {
            "nombre": "UNFCCC (acuerdos y cumbres climaticas)",
            "nivel": "Global",
            "tipo_recoleccion": "Secundaria (documentacion oficial de eventos/politicas)",
            "url": "https://unfccc.int",
            "pertinencia": "Media-alta - contextualiza eventos politicos relevantes (COP, acuerdos)",
            "confiabilidad": "Alta - organismo oficial de Naciones Unidas",
            "actualidad": "Eventos historicos documentados",
            "cobertura": "Global",
        },
    ],
    "unidad_analisis": {
        "unidad_de_analisis": "Pais / region / el mundo, para un anio determinado",
        "unidad_de_registro": "Una fila = una combinacion pais-anio (o evento individual en el dataset de eventos)",
        "variables": "Ver diccionario de datos en la seccion Dataset",
    },
    "trazabilidad": [
        "Se conserva el archivo original descargado (owid-co2-data.csv) sin modificar.",
        "Fecha de descarga registrada en el nombre/metadatos de los archivos procesados.",
        "Los datasets usados por la aplicacion son copias filtradas (por anio y pais/region), generadas con un script reproducible, nunca el archivo fuente editado a mano.",
        "El dataset de eventos externos es una muestra inicial documentada manualmente con fuente citada por evento; se ampliara con fuentes primarias (EM-DAT, UNGRD) en siguientes entregas.",
        "Todo filtro aplicado (rango de anios, paises seleccionados, columnas elegidas) queda documentado en esta bitacora y en scripts/preparar_datos.py.",
    ],
}

DICCIONARIO_DATOS = [
    {"variable": "country", "tipo": "Categorica (texto)", "descripcion": "Pais, region agregada o 'World'", "unidad": "-", "fuente": "OWID"},
    {"variable": "year", "tipo": "Temporal (entero)", "descripcion": "Anio de referencia del registro", "unidad": "anio", "fuente": "OWID"},
    {"variable": "iso_code", "tipo": "Categorica (texto)", "descripcion": "Codigo ISO3 del pais (vacio para agregados regionales)", "unidad": "-", "fuente": "OWID"},
    {"variable": "population", "tipo": "Numerica (entero)", "descripcion": "Poblacion total estimada", "unidad": "personas", "fuente": "OWID / Naciones Unidas"},
    {"variable": "co2", "tipo": "Numerica (continua)", "descripcion": "Emisiones anuales totales de CO2 (produccion)", "unidad": "millones de toneladas", "fuente": "Global Carbon Project via OWID"},
    {"variable": "co2_per_capita", "tipo": "Numerica (continua)", "descripcion": "Emisiones de CO2 por habitante", "unidad": "toneladas / persona", "fuente": "OWID"},
    {"variable": "co2_growth_prct", "tipo": "Numerica (continua)", "descripcion": "Variacion porcentual anual de las emisiones de CO2", "unidad": "%", "fuente": "OWID"},
    {"variable": "cumulative_co2", "tipo": "Numerica (continua)", "descripcion": "Emisiones acumuladas historicas de CO2", "unidad": "millones de toneladas", "fuente": "OWID"},
    {"variable": "temperature_change_from_co2", "tipo": "Numerica (continua)", "descripcion": "Contribucion del CO2 al cambio de temperatura global", "unidad": "grados Celsius", "fuente": "OWID / Global Carbon Project"},
    {"variable": "temperature_change_from_ghg", "tipo": "Numerica (continua)", "descripcion": "Contribucion de todos los GEI al cambio de temperatura global", "unidad": "grados Celsius", "fuente": "OWID"},
    {"variable": "methane", "tipo": "Numerica (continua)", "descripcion": "Emisiones de metano", "unidad": "millones de toneladas eq. CO2", "fuente": "OWID"},
    {"variable": "nitrous_oxide", "tipo": "Numerica (continua)", "descripcion": "Emisiones de oxido nitroso", "unidad": "millones de toneladas eq. CO2", "fuente": "OWID"},
    {"variable": "primary_energy_consumption", "tipo": "Numerica (continua)", "descripcion": "Consumo de energia primaria", "unidad": "TWh", "fuente": "OWID"},
    {"variable": "evento (dataset eventos)", "tipo": "Categorica (texto)", "descripcion": "Nombre del evento externo documentado", "unidad": "-", "fuente": "Elaboracion propia / UNFCCC / NOAA / UNGRD"},
    {"variable": "tipo (dataset eventos)", "tipo": "Categorica (texto)", "descripcion": "Clasificacion del evento: climatico, politico/ambiental, socioeconomico, desastre", "unidad": "-", "fuente": "Elaboracion propia"},
    {"variable": "escala (dataset eventos)", "tipo": "Categorica (texto)", "descripcion": "Nivel geografico del evento (global, regional, nacional)", "unidad": "-", "fuente": "Elaboracion propia"},
]


@app.route("/")
def index():
    """R1 - Pagina de inicio / resumen de la bitacora."""
    return render_template("index.html", proyecto=PROYECTO)


@app.route("/problema")
def problema():
    return render_template("problema.html", proyecto=PROYECTO)


@app.route("/recoleccion")
def recoleccion():
    return render_template("recoleccion.html", proyecto=PROYECTO)


@app.route("/dataset")
def dataset():
    resumenes = {}
    for clave, info in DATASETS.items():
        df, meta = cargar_dataset(clave)
        if df is not None:
            resumenes[clave] = {
                "info": info,
                "filas": len(df),
                "columnas": list(df.columns),
                "muestra": df.head(5).to_dict(orient="records"),
            }
        else:
            resumenes[clave] = {"info": info, "filas": 0, "columnas": [], "muestra": []}
    return render_template(
        "dataset.html",
        proyecto=PROYECTO,
        resumenes=resumenes,
        diccionario=DICCIONARIO_DATOS,
    )


@app.route("/calidad")
def calidad():
    metricas = {}
    for clave, info in DATASETS.items():
        df, meta = cargar_dataset(clave)
        metricas[clave] = {"info": info, "calidad": calcular_calidad(df)}
    return render_template("calidad.html", proyecto=PROYECTO, metricas=metricas)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
