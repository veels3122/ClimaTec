# Punto 5 — Tres iteraciones del tratamiento en SSIS

Paquete: `ssis/ClimaTec_ETL/ClimaTec_ETL.dtsx` (1 Abrir lote → 2 Extraccion a staging → 3 Limpieza →
4 Verificar lote → 5 Cerrar lote). Base: `ClimaTec_ETL` en SQL Server 2022. Fecha de ejecución: 29-sep-2026.
Evidencias (capturas) en `ssis/evidencias/`.

Las tres iteraciones se ejecutaron **seguidas y sin limpiar entre ellas** (lotes 1, 2 y 3), partiendo de la base
vacía (`02_limpiar_lotes.sql`). Solo se cambiaron los parámetros del proyecto (`RutaCSV`, `Iteracion`,
`DescripcionLote`); el paquete es el mismo en las tres.

## Resumen de conteos (`dbo.etl_lote`)

| Lote | Iteración | Archivo | Recibidas | Aceptadas | Duplicadas | Revisión | Balance | Estado |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 — datos reales | `climate-mining-app/data/raw/clima_consolidado.csv` | 21.369 | 21.369 | 0 | 0 | ✔ (1) | OK |
| 2 | 2 — prueba controlada con errores | `ssis/pruebas/clima_pruebas_limpieza.csv` | 26 | 12 | 2 | 12 | ✔ (1) | OK |
| 3 | 3 — recarga del mismo archivo | `ssis/pruebas/clima_pruebas_limpieza.csv` | 26 | 0 | 14 | 12 | ✔ (1) | OK |

Balance verificado por la tarea 4 en cada lote: **recibidas = aceptadas + duplicadas + revisión**.

## Iteración 1 — datos reales (línea base)

- **Objetivo:** aplicar todas las reglas al dataset consolidado de la Etapa 2 y medir la línea base.
- **Resultado:** las 21.369 filas se aceptan (el consolidado ya venía limpio desde la Etapa 2). Ninguna fila va a revisión.
- **Atípicos:** 2.640 filas marcadas con `atipico = 1` (regla 1.5·IQR por indicador) y 18.729 con `atipico = 0`.
  Se **marcan y se cargan**, no se eliminan, porque muchos extremos son reales (agregado mundial, grandes emisores).
- Evidencias: `iteracion1_dataflow.png`, `iteracion1_sql.png`.

## Iteración 2 — prueba controlada con errores

- **Objetivo:** comprobar que cada regla envía la fila al destino correcto, con un archivo de 26 filas con errores
  introducidos a propósito (diapositiva 21: *prueba controlada*).
- **Resultado:** 26 = 12 aceptadas + 2 duplicadas + 12 a revisión (11 REVISION_NEGOCIO + 1 ERROR_CONVERSION).

| Fila (CSV) | Qué trae | Destino | Regla / corrección |
|---|---|---|---|
| 1 | Pais Prueba A 2021, 15.25 | Aceptada | — (se conserva frente a sus duplicados) |
| 2 | Copia idéntica de la fila 1 | DUPLICADO | duplicado exacto |
| 3 | Misma clave que la fila 1, valor 14.90 | DUPLICADO | duplicado por clave lógica |
| 4 | `valor` vacío | REVISION_NEGOCIO | nulo en campo obligatorio (no se imputa) |
| 5 | `valor = abc` | ERROR_CONVERSION | tipo de dato no convertible |
| 6 | `anio = 2019` | REVISION_NEGOCIO | anio fuera de dominio (2020-2026) |
| 7 | `valor = -5.00` en Emisiones de CO2 | REVISION_NEGOCIO | valor negativo no permitido |
| 8 | `-3.20` en Variación anual de CO2 | Aceptada | el indicador admite negativos |
| 9 | `"  Pais Prueba B  "`, `" zzb "`, `" Terciaria "` | **Aceptada y corregida** | TRIM → `Pais Prueba B`; `ZZB`; `Terciaria` |
| 10 | `TERCIARIA`, `NACIONAL`, `anual` | **Aceptada y corregida** | homologado a `Terciaria`, `Nacional`, `Anual` |
| 11 | Serie nacional sin `iso_code` | REVISION_NEGOCIO | iso_code nulo en serie nacional |
| 12 | Unidad `kt CO2` | REVISION_NEGOCIO | unidad inconsistente con el indicador |
| 13 | Indicador "Emisiones de azufre" | REVISION_NEGOCIO | indicador fuera de catálogo |
| 14 | Fecha `2023/12/31` | **Aceptada y corregida** | `/` → `-` → `2023-12-31` |
| 15 | `anio 2024` con fecha 2023-12-31 | REVISION_NEGOCIO | fecha inconsistente con anio |
| 16 | `mes = 13` | REVISION_NEGOCIO | mes fuera de dominio |
| 17 | Serie mensual sin `mes` | REVISION_NEGOCIO | mes nulo en serie mensual |
| 18 | `mes = 10.0` | **Aceptada y corregida** | `10.0` → `10` |
| 19 | `fuente_tipo = Cuaternaria` | REVISION_NEGOCIO | fuente_tipo fuera de catálogo |
| 20 | `iso_code = ABCD` | REVISION_NEGOCIO | iso_code con formato inválido |
| 21 | `anio = 2023.0`, `valor = " 7.50 "` | **Aceptada y corregida** | `2023`, `7.5000` |
| 22-26 | Población E1…E5 | Aceptadas | E5 (9.999.999) queda marcada `atipico = 1` |

- **Dato corregido para la demostración:** fila 9 — llega `"  Pais Prueba B  "` / `zzb` / `" Terciaria "` y queda en
  `clima_limpio` como `Pais Prueba B` / `ZZB` / `Terciaria` (el original se conserva intacto en `stg_clima`).
- **Registro enviado a revisión para la demostración:** fila 5 (`valor = abc` → ERROR_CONVERSION) y fila 7
  (`-5.00` → REVISION_NEGOCIO, valor negativo no permitido); ambos conservan el valor original y el motivo en `clima_revision`.
- Evidencias: `iteracion2_dataflow.png`, `iteracion2_sql.png`.

## Iteración 3 — recarga del mismo archivo (segunda ejecución controlada)

- **Objetivo:** demostrar que volver a cargar el mismo lote **no duplica** eventos (diapositivas 19 y 23).
- **Resultado:** 26 = 0 aceptadas + 14 duplicadas + 12 revisión.
  - Las 12 filas que la iteración 2 había aceptado, más sus 2 duplicados, salen como **DUPLICADO — `clave ya cargada`**
    (14): la clave (fuente + nivel + entidad + año + mes + indicador) ya existe en `clima_limpio` desde el lote 2.
  - Las 12 filas inválidas vuelven a ir a revisión con las mismas reglas que en la iteración 2.
- **Comprobación:** `clima_limpio` recibió **0 filas nuevas** en el lote 3 y tiene **0 claves repetidas**.
- Evidencias: `iteracion3_dataflow.png`, `iteracion3_sql.png`.

## Ajustes realizados durante las iteraciones

| # | Problema detectado | Causa | Ajuste |
|---|---|---|---|
| 1 | *"The requested OLE DB provider MSOLEDBSQL19.1 is not registered"* | El paquete usa el driver OLE DB 19 y el equipo solo tenía la versión anterior | Se instaló *Microsoft OLE DB Driver 19 for SQL Server* (x64) |
| 2 | *"The literal 100000000000000 is too large to fit into type DT_I4"* en **Evaluar reglas** | En esa versión de SSIS el literal entero se interpreta como entero de 32 bits | Se cambió el literal a `100000000000000.0` (decimal) en las 4 expresiones que lo usan; la regla no cambia |
| 3 | El Data Flow **3 Limpieza** se quedaba detenido en 7.700 filas | Bloqueo: la vista `vw_stg_limpieza` lee `clima_limpio` (regla `clave ya cargada`) mientras el destino `clima_limpio` inserta con *Table lock* | `ALTER DATABASE ClimaTec_ETL SET READ_COMMITTED_SNAPSHOT ON`: las lecturas usan la última versión confirmada y no esperan a la escritura |
| 4 | Iteración 2: *"Cannot insert the value NULL into column 'fecha_registro'"* en **clima_revision** | El destino tenía *Keep nulls* activado, lo que anula el valor por defecto `SYSDATETIME()` de `fecha_registro` | Se desactivó *Keep nulls* en el destino `clima_revision`; se borró solo el lote fallido y se repitió la iteración 2 |

Evidencia del ajuste 4: `iteracion2_intento1_dataflow_error.png`, `iteracion2_intento1_progress_error.png`, `iteracion2_intento1_sql.png`.

## Reglas aplicadas (resumen)

Definidas en el Punto 1 e implementadas en *3 Limpieza* (ver `ssis/LEEME.md`), en orden de prioridad:
duplicados (`clave ya cargada`, `duplicado exacto`, `duplicado por clave logica`) → nulos en campos obligatorios →
formatos y catálogos (`fuente_tipo`, `nivel_geografico`, `periodicidad`, `indicador`, `unidad`, `iso_code`) →
dominio (`anio` 2020-2026, `mes` 1-12, negativos según `cat_indicador`, coherencia `fecha`–`anio`/`mes`) →
atípicos (se marcan, no se separan).

## Consultas usadas

```sql
USE ClimaTec_ETL;
SELECT IdLote, iteracion, descripcion, estado, filas_recibidas, filas_aceptadas,
       filas_duplicadas, filas_revision, balance_ok FROM dbo.etl_lote ORDER BY IdLote;
SELECT IdLote, destino, regla, COUNT(*) FROM dbo.clima_revision GROUP BY IdLote, destino, regla;
SELECT atipico, COUNT(*) FROM dbo.clima_limpio WHERE IdLote = 1 GROUP BY atipico;
SELECT COUNT(*) FROM dbo.clima_limpio WHERE IdLote = 3;                       -- 0: la recarga no duplica
SELECT COUNT(*) FROM (SELECT fuente, nivel_geografico, entidad, anio, mes, indicador
                      FROM dbo.clima_limpio GROUP BY fuente, nivel_geografico, entidad, anio, mes, indicador
                      HAVING COUNT(*) > 1) x;                                  -- 0 claves repetidas
```
