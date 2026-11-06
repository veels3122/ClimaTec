# Checklist de cumplimiento · Etapa 5 (Análisis multidimensional)

Revisión de cada punto del enunciado contra el repositorio y la aplicación (`main`, 6-nov-2026).
Se ejecutó `scripts/cargar_modelo.py` y `scripts/verificar_modelo.py`, y se recorrieron las 16 páginas de la sección en el Flask local con Playwright: no hubo errores de consola y todas las páginas respondieron 200.

| # | Punto del enunciado | Estado | Dónde se cumple |
|---|---|---|---|
| 1 | Continuidad: mismo tema, población y datos; registros usados; limitaciones; conocimientos evidentes a profundizar; unidad de análisis vs. granularidad | ✅ | `/etapa-5/continuidad-del-proyecto` (21.369 registros, 6 limitaciones, 7 conocimientos de la Etapa 4, unidad = territorio-año; grano = indicador × territorio × periodo × fuente) |
| 2 | Cuatro preguntas, cada una con ≥2 dimensiones y 1 medida; entre todas usan las 4 dimensiones; cómo profundizan la Etapa 4 | ✅ | `/etapa-5/preguntas-de-analisis` (tabla de cobertura: Tiempo, Geografía, Indicador y Fuente) |
| 3 | Modelo estrella: hechos + ≥4 dimensiones, granularidad, atributos, PK/FK, relaciones, ≥3 medidas con fórmula y agregación, ≥2 jerarquías válidas | ✅ | `/etapa-5/modelo-estrella`, `/etapa-5/dimensiones-medidas-jerarquias`, `docs/etapa5/modelo_estrella.md` (4 dimensiones, 7 medidas, 4 jerarquías) |
| 4 | Implementación consultable desde Flask, carga reproducible, correspondencia de variables, validaciones y ≥3 comparaciones con los datos tratados | ✅ | SQLite `data/dw/climatec_dw.sqlite`; `scripts/cargar_modelo.py`; `scripts/verificar_modelo.py`; `/etapa-5/verificacion-del-modelo` (5 bloques de integridad y 5 comparaciones, todas con diferencia 0) |
| 5 | Drill-down, roll-up, slice, dice y pivot desde Flask, con un ejemplo cada uno y recálculo correcto | ✅ | `/etapa-5/operaciones-multidimensionales` (6 ejemplos con SQL ejecutado) y controles en las 4 vistas. Probado: drill-down Sudamérica 37.398 → 1.110 Mt; roll-up Mes → Año; slice de indicador; dice de territorios; pivot de la matriz |
| 6 | Cuatro vistas con título, pregunta, dimensiones/medidas/jerarquías, 3 indicadores, 2 visualizaciones, 1 matriz, 2 filtros de dimensiones distintas, controles, interpretación, 2 conocimientos, 1 limitación y 1 decisión | ✅ | `/etapa-5/vistas-interactivas/1` a `/4` (total: 12 indicadores, 8 visualizaciones, 4 matrices, 8 conocimientos) |
| 7 | Ocho conocimientos con sus 8 elementos | ✅ | `/etapa-5/conocimientos-conclusiones` (pregunta, dimensiones y medidas, procedimiento, evidencia con SQL, hallazgo, interpretación, utilidad, limitación) |
| 8 | Condiciones del análisis (granularidad, no multiplicar valores, denominadores, recálculo de %, periodos equivalentes, asociación ≠ causalidad, hipótesis) | ✅ | `/etapa-5/condiciones-del-analisis` (11 condiciones con su evidencia) |
| 9 | Opción "Análisis multidimensional" en el menú con propósito, relación, diagrama, dimensiones, vistas, operaciones, conocimientos; fuente y periodo visibles | ✅ | Barra superior, menú móvil y riel de Inicio; ficha de fuente, periodo y cobertura en cada página |
| 10 | Repositorio: diagrama y diccionario, scripts DDL, carga, consultas, datos, cambios en Flask, dependencias, URL | ✅ | `docs/etapa5/` (README, `modelo_estrella.md`, `sql/01-03`, `cambios_flask.md`), `ssis/sql/04_modelo_estrella.sql`, `climate-mining-app/README.md` |
| 10 | ≥3 commits por integrante y pull requests | ⚠️ Pendiente | Hasta el 6-nov los commits de la etapa son de Ana Cortés (PR #38 a #43). Faltan los de Mateo Melgarejo y Andrés Pineda |
| 11 | Informe técnico en PDF | ⚠️ En elaboración | `docs/etapa5/informe/` |
| 12 | Cada integrante sube el mismo PDF; la app publicada muestra la sección | ⚠️ Al entregar | https://climatec-ctrm.onrender.com |

## Corrección encontrada en la revisión

- Vista 2, indicador 3: con un solo continente el texto decía "1 continentes reunen la mitad del total". Se corrigió la concordancia en `static/js/etapa5_vistas.js` (singular cuando el valor es 1).
