# ClimaTec — Paquete ETL en SSIS

Paquete SSIS de la etapa ETL del proyecto ClimaTec. Extrae `climate-mining-app/data/raw/clima_consolidado.csv`
(21.369 filas), lo conserva sin cambios en una zona de staging y deja listos los destinos para la limpieza.

## Estructura

```
ssis/
├── LEEME.md                         <- este archivo
├── sql/
│   ├── 01_crear_base_climatec_etl.sql   <- crea la base ClimaTec_ETL (tablas + procedimientos)
│   ├── 02_limpiar_lotes.sql             <- borra todas las cargas y reinicia contadores
│   └── 03_limpieza_catalogo_y_vista.sql <- catalogo de indicadores + vista que lee "3 Limpieza"
├── pruebas/
│   └── clima_pruebas_limpieza.csv   <- 26 filas con errores a proposito para probar el Punto 4
└── ClimaTec_ETL/
    ├── ClimaTec_ETL.sln             <- abrir ESTE archivo en Visual Studio
    ├── ClimaTec_ETL.dtproj
    ├── ClimaTec_ETL.dtsx            <- el paquete
    ├── Project.params               <- parámetros (servidor, ruta del CSV, iteración)
    └── ClimaTec_ETL.database
```

## Cómo ponerlo a funcionar en tu PC (una sola vez)

Requisitos: SQL Server (Express o Developer), SSMS y Visual Studio Community con la extensión
**SQL Server Integration Services Projects**.

1. **Crear la base.** En SSMS, conectado a tu servidor: File → Open → `ssis/sql/01_crear_base_climatec_etl.sql` → F5.
   Debe salir una tabla con 4 filas en 0 (etl_lote, stg_clima, clima_limpio, clima_revision).
   Luego abre y ejecuta `ssis/sql/03_limpieza_catalogo_y_vista.sql` (F5): crea `cat_indicador` (24 filas)
   y la vista `vw_stg_limpieza`. **Sin este script la tarea 3 no valida.** Si vuelves a correr el 01,
   corre también el 03 después.
2. **Abrir el proyecto.** En Visual Studio: File → Open → Project/Solution → `ssis/ClimaTec_ETL/ClimaTec_ETL.sln`.
3. **Ajustar los parámetros a tu PC.** En Solution Explorer, doble clic en **Project.params** y cambia:
   - `Servidor` → el nombre de TU servidor SQL (el que usas para conectarte en SSMS, ej. `TU-PC` o `TU-PC\SQLEXPRESS`).
   - `RutaCSV` → la ruta completa de `clima_consolidado.csv` en TU copia del repo, por ejemplo
     `C:\...\GitHub\ClimaTec\climate-mining-app\data\raw\clima_consolidado.csv`.
   - Ctrl+S.
4. **Probar.** Abre `ClimaTec_ETL.dtsx`, pestaña Control Flow, ▶ Start. Las 5 cajas deben quedar en verde.
   En SSMS: `SELECT * FROM ClimaTec_ETL.dbo.etl_lote;` → el lote con `filas_recibidas = 21369`,
   `filas_aceptadas = 21369`, duplicadas y revisión en 0, `balance_ok = 1` y estado `OK`
   (el CSV consolidado ya viene limpio desde la Etapa 2; 2.640 filas quedan con `atipico = 1`).

No hay contraseñas en el proyecto: la conexión usa autenticación de Windows.

## Qué hace el paquete (Control Flow)

| # | Tarea | Tipo | Qué hace |
|---|---|---|---|
| 1 | Abrir Lote | Execute SQL | `EXEC dbo.usp_abrir_lote` → crea el lote en `etl_lote` y guarda su número en `User::IdLote` |
| 2 | Extraccion a staging | Data Flow | Leer CSV → Agregar lote y archivo (Derived Column) → Contar recibidas (Row Count) → Guardar en `stg_clima` |
| 3 | Limpieza | Data Flow | Estandariza, tipa y valida el lote: aceptadas → `clima_limpio`; duplicadas y para revisión → `clima_revision` (valor original + regla + motivo) — ver abajo |
| 4 | Verificar lote | Execute SQL | `EXEC dbo.usp_verificar_lote` → cuenta recibidas / aceptadas / duplicadas / revisión y comprueba el balance |
| 5 | Cerrar lote | Execute SQL | `EXEC dbo.usp_cerrar_lote` → estado final `OK` (balance cuadra) o `REVISAR_BALANCE` |


## "3 Limpieza" — Punto 4: limpieza de datos y excepciones

Ninguna fila se pierde: cada fila del lote termina en `clima_limpio` **o** en `clima_revision`, y
`stg_clima` no se modifica. Por eso el balance **recibidas = aceptadas + duplicadas + revisión** cuadra.

```
Leer staging del lote ─► Estandarizar formatos ─► Tipar columnas ─► Evaluar reglas ─► Registrar motivo ─► Separar registros
 (vw_stg_limpieza,                                   │ error (Redirect Row)                                 │ Aceptados ─► clima_limpio
  IdLote = ?)                                        ▼                                                      │ Para revision ─┐
                                            Motivo error de conversion ─────────────────────────────► Unir excepciones ─► clima_revision
```

| Componente | Tipo | Qué hace |
|---|---|---|
| Leer staging del lote | OLE DB Source | `vw_stg_limpieza WHERE IdLote = ?` (`User::IdLote`). Trae los 12 valores **originales** y, calculado en la vista: numeración de duplicados (`rn_clave`, `rn_exacto`), `lote_previo`, cruce con `cat_indicador` y cuartiles/media/desviación por indicador |
| Estandarizar formatos | Derived Column | Crea columnas `*_std` sin tocar las originales: TRIM, vacío → NULL, `fuente_tipo`/`nivel_geografico`/`periodicidad` en formato Nombre, `iso_code` en mayúsculas, `2021.0` → `2021`, coma decimal → punto, `/` → `-` en fecha. Detecta el primer campo obligatorio vacío |
| Tipar columnas | Data Conversion | anio SMALLINT, mes TINYINT, valor numérico, fecha DATE, iso_code CHAR(3). Error y truncamiento en **Redirect Row** |
| Evaluar reglas | Derived Column | Deja en `regla` la primera regla que incumple (tabla de abajo). Marca `atipico` (1.5·IQR por indicador) y calcula `valor_z` |
| Registrar motivo | Derived Column | `destino` (ACEPTADO / DUPLICADO / REVISION_NEGOCIO) y `motivo` legible |
| Motivo error de conversion | Derived Column | Filas no tipables → `ERROR_CONVERSION`, con los valores originales en el motivo |
| Separar registros | Conditional Split | `destino == "ACEPTADO"` → Aceptados; el resto → Para revision |
| Unir excepciones | Union All | Junta revisión/duplicados con errores de conversión |
| clima_limpio / clima_revision | OLE DB Destination | Carga rápida, conservando NULL (`iso_code` y `mes` vacíos por diseño) |

**Reglas, en orden de prioridad** (la primera que falla es la que se registra):

| Tratamiento | Regla (`regla`) | Destino |
|---|---|---|
| Duplicados | `clave ya cargada` (la clave ya está en `clima_limpio` de otro lote), `duplicado exacto`, `duplicado por clave logica` | DUPLICADO |
| Nulos | `nulo en campo obligatorio` (no se imputa); `iso_code nulo en serie nacional`; `mes nulo en serie mensual`; `mes informado en serie anual`. `iso_code` vacío en Global/Regional y `mes` vacío en series anuales son **nulos por diseño** y se aceptan | REVISION_NEGOCIO |
| Formatos inconsistentes | `fuente_tipo` / `nivel_geografico` / `periodicidad fuera de catalogo`, `indicador fuera de catalogo`, `unidad inconsistente con el indicador`, `iso_code con formato invalido`, `texto excede longitud del destino`; valores no tipables → `tipo de dato no convertible` | REVISION_NEGOCIO / ERROR_CONVERSION |
| Valores inválidos | `anio fuera de dominio` (2020-2026), `mes fuera de dominio` (1-12), `valor negativo no permitido` (según `cat_indicador.admite_negativos`), `valor excede la precision del destino`, `fecha inconsistente con anio` / `con mes` | REVISION_NEGOCIO |
| Atípicos | Se **marcan** (`atipico = 1`) y se cargan; no se separan, porque muchos son reales (agregado mundial, grandes emisores) | ACEPTADO |

Notas:
- De cada grupo de duplicados se conserva la fila con valor numérico válido y menor `IdStg`; el motivo dice cuál.
- La regla `clave ya cargada` evita que una segunda corrida viole el índice único de `clima_limpio`. Para repetir
  una iteración desde cero, ejecuta antes `02_limpiar_lotes.sql`.

### Probar las excepciones

Cambia el parámetro `RutaCSV` a `...\ClimaTec\ssis\pruebas\clima_pruebas_limpieza.csv` y ejecuta el paquete.
Resultado esperado del lote: **26 recibidas = 12 aceptadas + 2 duplicadas + 12 revisión** (11 REVISION_NEGOCIO
y 1 ERROR_CONVERSION), estado `OK`; la fila de "Pais Prueba E5" queda aceptada con `atipico = 1`. Después vuelve
a poner la ruta de `clima_consolidado.csv`. (Si corres la prueba dos veces, la segunda sale como `clave ya cargada`.)

## Consultas útiles (SSMS)

```sql
USE ClimaTec_ETL;
SELECT * FROM dbo.etl_lote ORDER BY IdLote DESC;                       -- resumen de cada ejecución
SELECT IdLote, COUNT(*) FROM dbo.stg_clima GROUP BY IdLote;             -- filas recibidas por lote
SELECT destino, regla, COUNT(*) FROM dbo.clima_revision GROUP BY destino, regla;  -- excepciones
SELECT IdStg, destino, regla, motivo, anio, mes, valor, fecha                     -- detalle con valor original
  FROM dbo.clima_revision WHERE IdLote = (SELECT MAX(IdLote) FROM dbo.etl_lote);
SELECT atipico, COUNT(*) FROM dbo.clima_limpio GROUP BY atipico;                  -- atipicos marcados
```

Para empezar de cero: ejecutar `ssis/sql/02_limpiar_lotes.sql`.
