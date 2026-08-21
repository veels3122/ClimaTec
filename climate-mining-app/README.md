# Cambio climatico y eventos externos: analisis global, regional y nacional

Bitacora tecnica del proyecto, construida en Flask. Documenta el proceso de
mineria de datos desde la definicion del problema hasta la evaluacion
inicial de calidad de los datos, en tres escalas: **global**, **regional
(Sudamerica)** y **nacional (Colombia)**.

Esta es la **version base (R1)** del proyecto: prioriza tener el contenido
completo y correcto sobre el diseno visual. Se ira mejorando en entregas
posteriores (limpieza avanzada, transformacion, analisis y
visualizaciones).

## Estructura de la aplicacion

- **R1 / Inicio** (`/`): resumen del proyecto.
- **Problema** (`/problema`): contexto, pregunta principal y preguntas secundarias.
- **Recoleccion** (`/recoleccion`): necesidades de informacion, fuentes evaluadas (pertinencia, confiabilidad, actualidad, cobertura), unidad de analisis/registro/variable y trazabilidad.
- **Dataset** (`/dataset`): vista previa de los datasets (global, regional, nacional, eventos externos) y diccionario de datos.
- **Calidad** (`/calidad`): metricas iniciales de completitud, unicidad y consistencia, calculadas automaticamente con pandas.

## Datos utilizados

| Dataset | Nivel | Fuente | Periodo |
|---|---|---|---|
| `global_climate_owid_1995_2024.csv` | Global | Our World in Data (Global Carbon Project) | 1995-2024 |
| `regional_sudamerica_owid_1995_2024.csv` | Regional (Sudamerica) | Our World in Data | 1995-2024 |
| `nacional_colombia_owid_1960_2024.csv` | Nacional (Colombia) | Our World in Data | 1960-2024 |
| `eventos_externos_muestra.csv` | Global/Regional/Nacional | Elaboracion propia con base en UNFCCC, NOAA, UNGRD, IDEAM | 2010-2023 (muestra inicial) |

Los tres primeros archivos son un recorte real, reproducible y sin
modificar del dataset publico de Our World in Data
(https://github.com/owid/co2-data), generado con `scripts/preparar_datos.py`.
El archivo de eventos es una muestra inicial documentada manualmente,
pensada para ampliarse con fuentes primarias (por ejemplo EM-DAT) en la
siguiente entrega.

**Trazabilidad:** el archivo original `owid-co2-data.csv` no se modifica ni
se sube al repositorio (pesa ~14 MB); se descarga aparte y se procesa con el
script `scripts/preparar_datos.py`, que documenta exactamente que filtros y
columnas se aplicaron.

## Como correr el proyecto en local

```bash
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Luego abre http://localhost:5000 en el navegador.

### (Opcional) Regenerar los datasets desde la fuente original

```bash
# 1. Descargar el CSV original de Our World in Data y guardarlo en:
#    data/processed/owid-co2-data.csv
# 2. Ejecutar:
python scripts/preparar_datos.py
```

## Despliegue en Render

Este repo incluye `render.yaml` y `Procfile`, listos para desplegar en
[Render](https://render.com):

1. Crear una cuenta en Render y conectar este repositorio de GitHub.
2. Crear un nuevo **Web Service** apuntando a este repo (Render detecta
   `render.yaml` automaticamente).
3. Render instalara `requirements.txt` y ejecutara `gunicorn app:app`.
4. Al finalizar el build, Render entrega una URL publica (ej.
   `https://cambio-climatico-eventos-externos.onrender.com`).

## Estructura de carpetas

```
climate-mining-app/
├── app.py                     # Aplicacion Flask (rutas + logica de la bitacora)
├── requirements.txt
├── Procfile
├── render.yaml
├── data/
│   └── raw/                   # Datasets usados por la app (csv)
├── scripts/
│   └── preparar_datos.py      # Script reproducible de preparacion de datos
├── templates/                 # Vistas Jinja2 (R1, Problema, Recoleccion, Dataset, Calidad)
└── static/css/style.css
```

## Proximos pasos (siguientes entregas)

- Ampliar el dataset de eventos externos con fuentes primarias (EM-DAT, UNGRD).
- Incorporar limpieza y transformacion de datos (normalizacion, manejo de outliers).
- Agregar visualizaciones (series de tiempo, comparacion entre escalas).
- Automatizar la actualizacion periodica de los datasets fuente.
