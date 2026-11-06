# Cambios en la aplicación Flask (Etapa 5)

## Menú
- `templates/base.html`: nueva opción **Análisis multidimensional** (barra de escritorio, menú móvil y riel de etapas del Inicio) con 12 apartados en la rueda de secciones. Ajustes de espaciado del menú en `static/css/etapa5.css` para que no se desborde entre 1024 y 1600 px.

## Rutas nuevas (`app.py`)
| Ruta | Página |
|---|---|
| `/etapa-5/proposito` | 1 · Propósito de la etapa |
| `/etapa-5/continuidad-del-proyecto` | 2 · Continuidad: registros, limitaciones, unidad de análisis |
| `/etapa-5/relacion-conocimiento-evidente` | 3 · Relación con el conocimiento evidente |
| `/etapa-5/preguntas-de-analisis` | 4 · Las cuatro preguntas |
| `/etapa-5/modelo-estrella` | 5 · Diseño y diagrama del modelo estrella |
| `/etapa-5/dimensiones-medidas-jerarquias` | 6 · Dimensiones, medidas y jerarquías |
| `/etapa-5/implementacion-y-carga` | 7 · Implementación y carga |
| `/etapa-5/verificacion-del-modelo` | 8 · Verificación del modelo |
| `/etapa-5/condiciones-del-analisis` | 9 · Condiciones del análisis |
| `/etapa-5/vistas-interactivas` y `/etapa-5/vistas-interactivas/<1-4>` | 10 · Vistas interactivas |
| `/etapa-5/operaciones-multidimensionales` | 11 · Operaciones OLAP con ejemplos en vivo |
| `/etapa-5/conocimientos-conclusiones` | 12 · Conocimientos, limitaciones y conclusiones |
| `/api/etapa5/olap` | API JSON: `filas`, `columnas`, `medida`, filtros `f=atributo=valor` (repetible) |

## Al arrancar
- `cargar_modelo.asegurar_modelo()` carga el almacén SQLite si no existe o si cambió `clima_limpio.csv` (huella MD5).
- Un `context_processor` muestra en todas las páginas de la etapa la fuente de los datos, el periodo y la cobertura.

## Archivos nuevos
- `scripts/multidimensional.py`, `scripts/cargar_modelo.py`, `scripts/olap.py`, `scripts/verificar_modelo.py`, `scripts/exportar_documentacion.py`
- `templates/etapa5/*.html`, `static/js/etapa5_vistas.js`, `static/css/etapa5.css`
- `data/raw/dim_pais_region.csv`

## Dependencias
- `requirements.txt`: se agregó `plotly` (la importaba la Etapa 4 y faltaba). La Etapa 5 no agrega dependencias: usa `sqlite3` de la biblioteca estándar.
