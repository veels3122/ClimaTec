# ClimaTec — Bitacora tecnica (Mineria de Datos)

Aplicacion web en **Flask** que funciona como bitacora tecnica y plataforma de
documentacion del proyecto de mineria de datos.

- **Tema:** Cambio climatico y eventos externos
- **Niveles de analisis:** Global / Regional (Sudamerica) / Nacional (Colombia)
- **Periodo:** 2020–2026
- **App publicada:** https://climatec-ctrm.onrender.com
- **Repositorio:** https://github.com/veels3122/ClimaTec

## Integrantes
- Ana Cortes
- Mateo Melgarejo
- Andres Pineda

## Estructura de la aplicacion

Menu principal **Etapa 1** con los 8 apartados del entregable:

1. Problema y contexto
2. Pregunta principal y preguntas secundarias
3. Necesidades de informacion
4. Fuentes de datos
5. Dataset
6. Diccionario de datos
7. Calidad inicial de los datos
8. Limitaciones y consideraciones

Menu **Etapa 2** (perfilamiento y limpieza) con 7 apartados:

1. Descripcion del conjunto de datos
2. Resultados del perfilamiento
3. Dimensiones y metricas evaluadas
4. Problemas identificados
5. Acciones de tratamiento aplicadas
6. Comparacion antes y despues
7. Graficas, tablas e indicadores

La Etapa 2 se calcula en vivo con `scripts/limpieza.py` sobre
`clima_consolidado.csv`; el dataset limpio se guarda en `data/raw/clima_limpio.csv`
(tipos normalizados, columna `atipico` por IQR e `valor_z` por indicador).

Las paginas 5 (Dataset) y 7 (Calidad inicial) calculan sus metricas **en vivo**
a partir del archivo real `data/raw/clima_consolidado.csv`, de modo que la
documentacion nunca se aleja del contenido del dataset.

## Dataset (multi-fuente, formato de tabla de hechos)

El dataset consolidado esta en **formato largo/tidy**: una fila = una observacion
(un indicador medido para una entidad, en una fecha, desde una fuente identificada).
Este formato permite integrar fuentes heterogeneas —anuales y mensuales, de distintos
proveedores y niveles— bajo un mismo esquema, con la procedencia de cada dato en las
columnas `fuente` / `fuente_tipo`.

- **Archivo:** `data/raw/clima_consolidado.csv`
- **Volumen:** ~21.369 observaciones · 12 columnas · 24 indicadores climaticos
- **Cobertura:** Global, Regional y Nacional (231 paises con ISO3, incl. Colombia)
- **Periodicidades:** anual y mensual

### Fuentes integradas en el CSV (descargables desde GitHub)
| Fuente | Tipo | Nivel |
|---|---|---|
| Our World in Data — CO2 & GHG (Global Carbon Project) | Terciaria | Global/Regional/Nacional |
| Our World in Data — Energy (Energy Institute / Ember) | Terciaria | Nacional/Global |
| NOAA GML — Observatorio de Mauna Loa (CO2 in situ) | Primaria | Global |
| NASA GISS — GISTEMP (anomalia de temperatura) | Primaria | Global |
| NOAA NCEI — GlobalTemp/GCAG (anomalia de temperatura) | Primaria | Global |
| Eventos externos (COP, ENSO, emergencias) | Secundaria | Global/Nacional |

### Fuentes automatizadas en el pipeline (nivel nacional/regional)
Se descargan **al ejecutar el script con acceso a internet** (viven en portales
institucionales, no accesibles desde el entorno de build):

| Fuente | Tipo | Nivel |
|---|---|---|
| NASA POWER — reanalisis MERRA-2 (T2M, precipitacion) | Primaria | Nacional (Colombia) / Regional (Sudamerica) |
| Banco Mundial — World Development Indicators (clima) | Secundaria | Nacional / Regional |
| IDEAM — Datos abiertos de clima e hidrologia | Primaria | Nacional (Colombia) |

El manifiesto `data/raw/fuentes_manifest.csv` deja registrado el estado de cada
fuente (integrada u omitida por falta de red) en cada ejecucion.

## Regenerar el dataset

    pip install -r requirements.txt
    python scripts/preparar_datos.py

> **Importante:** ejecutalo en una maquina con **acceso abierto a internet** para
> que se integren tambien NASA POWER, Banco Mundial e IDEAM (fuentes primarias de
> nivel nacional/regional). El script descarga cada fuente, arma la tabla de hechos
> filtrada a 2020-2026, escribe clima_consolidado.csv y actualiza el manifiesto.
> Nunca inventa datos: solo consolida lo que descarga.

Para IDEAM se puede fijar el recurso de datos.gov.co con la variable de entorno
`IDEAM_DATASET_ID` (por defecto usa un recurso de temperatura por estacion).

## Etapa 2 — perfilamiento y limpieza

    python scripts/limpieza.py

Lee `data/raw/clima_consolidado.csv`, ejecuta el perfilamiento, aplica el
tratamiento (normalizacion de tipos, verificacion de duplicados y dominio, marcado
de atipicos por IQR y variable `valor_z`) y escribe `data/raw/clima_limpio.csv`.
La app tambien recalcula este reporte en vivo al arrancar, asi que las paginas de
la Etapa 2 siempre reflejan el dataset actual.

## Ejecutar la app localmente

    pip install -r requirements.txt
    python app.py
    # http://localhost:5000

## Despliegue (Render)
Procfile y render.yaml incluidos. El servicio arranca con gunicorn app:app.
