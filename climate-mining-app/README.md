# ClimaTec — Bitacora tecnica (Mineria de Datos)

Aplicacion web en **Flask** que funciona como bitacora tecnica y plataforma de
documentacion del proyecto de mineria de datos.

- **Tema:** Cambio climatico y eventos externos
- **Niveles de analisis:** Global / Regional (Sudamerica) / Nacional (Colombia)
- **Periodo:** 1950–2024
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

Las paginas 5 (Dataset) y 7 (Calidad inicial) calculan sus metricas **en vivo**
a partir del archivo real `data/raw/clima_consolidado.csv`, de modo que la
documentacion nunca se aleja del contenido del dataset.

## Dataset

- **Fuente principal:** Our World in Data — CO2 and Greenhouse Gas Emissions
  (https://github.com/owid/co2-data), fuente terciaria, licencia CC-BY.
- **Consolidado:** `data/raw/clima_consolidado.csv` — **16.875 registros**, 15 variables
  (11 numericas, 3 categoricas, 1 temporal, 3 geograficas).
  - Global: 75 filas (World) · Regional: 450 filas (6 continentes) · Nacional: 16.350 filas (218 paises).
- **Eventos externos:** `data/raw/eventos_externos_muestra.csv` (muestra documentada, se amplia en Etapa 2).

Cumple los minimos de la guia: >= 10.000 registros, >= 10 variables, >= 3 numericas,
>= 3 categoricas, >= 1 temporal y >= 1 geografica.

## Trazabilidad y reproducibilidad

1. Se descarga el archivo fuente original (owid-co2-data.csv) y se coloca en
   `data/processed/` (no se versiona por su tamano, ~14 MB — ver `.gitignore`).
   Descarga directa:
   `https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv`
2. Se ejecuta el script reproducible:
   ```bash
   python scripts/preparar_datos.py
   ```
   que aplica las transformaciones documentadas (filtro `year >= 1950`, seleccion de
   14 columnas, y mapeo de `nivel_geografico`) y genera `data/raw/clima_consolidado.csv`.
3. El archivo fuente nunca se edita a mano.
- **Fecha de consulta de la fuente:** 2026-08-25.

## Ejecutar en local

```bash
pip install -r requirements.txt
python app.py
# http://127.0.0.1:5000
```

## Despliegue

- `Procfile`: `web: gunicorn app:app`
- `render.yaml`: servicio web Python en Render (plan free).

## Estructura del proyecto

```
climate-mining-app/
├── app.py                     # Rutas + logica + contenido documental
├── requirements.txt
├── Procfile / render.yaml
├── data/
│   ├── raw/                   # datasets versionados (incl. clima_consolidado.csv)
│   └── processed/             # fuente original owid-co2-data.csv (ignorada)
├── scripts/preparar_datos.py  # generacion reproducible del dataset
├── static/css/style.css
└── templates/
    ├── base.html              # layout + menu "Etapa 1"
    ├── index.html
    └── etapa1/                # las 8 paginas del entregable
```
