# ClimaTec — Paquete ETL en SSIS

Paquete SSIS de la etapa ETL del proyecto ClimaTec. Extrae `climate-mining-app/data/raw/clima_consolidado.csv`
(21.369 filas), lo conserva sin cambios en una zona de staging y deja listos los destinos para la limpieza.

## Estructura

```
ssis/
├── LEEME.md                         <- este archivo
├── sql/
│   ├── 01_crear_base_climatec_etl.sql   <- crea la base ClimaTec_ETL (tablas + procedimientos)
│   └── 02_limpiar_lotes.sql             <- borra todas las cargas y reinicia contadores
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
2. **Abrir el proyecto.** En Visual Studio: File → Open → Project/Solution → `ssis/ClimaTec_ETL/ClimaTec_ETL.sln`.
3. **Ajustar los parámetros a tu PC.** En Solution Explorer, doble clic en **Project.params** y cambia:
   - `Servidor` → el nombre de TU servidor SQL (el que usas para conectarte en SSMS, ej. `TU-PC` o `TU-PC\SQLEXPRESS`).
   - `RutaCSV` → la ruta completa de `clima_consolidado.csv` en TU copia del repo, por ejemplo
     `C:\...\GitHub\ClimaTec\climate-mining-app\data\raw\clima_consolidado.csv`.
   - Ctrl+S.
4. **Probar.** Abre `ClimaTec_ETL.dtsx`, pestaña Control Flow, ▶ Start. Las 5 cajas deben quedar en verde.
   En SSMS: `SELECT * FROM ClimaTec_ETL.dbo.etl_lote;` → el lote con `filas_recibidas = 21369`.

No hay contraseñas en el proyecto: la conexión usa autenticación de Windows.

## Qué hace el paquete (Control Flow)

| # | Tarea | Tipo | Qué hace |
|---|---|---|---|
| 1 | Abrir Lote | Execute SQL | `EXEC dbo.usp_abrir_lote` → crea el lote en `etl_lote` y guarda su número en `User::IdLote` |
| 2 | Extraccion a staging | Data Flow | Leer CSV → Agregar lote y archivo (Derived Column) → Contar recibidas (Row Count) → Guardar en `stg_clima` |
| 3 | Limpieza | Data Flow | **Por construir (componentes de transformación y tratamiento)** — ver abajo |
| 4 | Verificar lote | Execute SQL | `EXEC dbo.usp_verificar_lote` → cuenta recibidas / aceptadas / duplicadas / revisión y comprueba el balance |
| 5 | Cerrar lote | Execute SQL | `EXEC dbo.usp_cerrar_lote` → estado final `OK` (balance cuadra) o `REVISAR_BALANCE` |

Mientras "3 Limpieza" esté vacía, el lote termina en `REVISAR_BALANCE` (entran 21.369 y no sale ninguna). Es lo esperado.

## Para quien construya "3 Limpieza" (componentes y tratamiento)

- **Origen:** leer de `dbo.stg_clima` **filtrando por el lote actual** (OLE DB Source, modo *SQL command*):
  `SELECT * FROM dbo.stg_clima WHERE IdLote = ?` con el parámetro `User::IdLote`.
  No leer el CSV otra vez ni modificar `stg_clima`: staging se conserva intacto.
- **Filas aceptadas → `dbo.clima_limpio`**, ya tipadas (anio SMALLINT, mes TINYINT, valor DECIMAL(18,4), fecha DATE,
  iso_code CHAR(3)), con `IdLote` e `IdStg` para la trazabilidad. Tiene un índice único por
  (fuente, nivel_geografico, entidad, anio, mes, indicador): una fila repetida no entra dos veces.
- **Duplicados y registros para revisión → `dbo.clima_revision`**, con los valores ORIGINALES (texto) más:
  - `destino`: `DUPLICADO`, `REVISION_NEGOCIO` o `ERROR_CONVERSION`
  - `regla`: qué regla incumplió (ej. `anio fuera de dominio`)
  - `motivo`: explicación legible
  - `IdLote` e `IdStg`
- Con eso, las tareas 4 y 5 cuentan y cierran el lote solas. El balance que se verifica es:
  **recibidas = aceptadas + duplicadas + revisión**.
- Las reglas a aplicar son las del Punto 1 (página "Diagnóstico y Reglas de Tratamiento" de la app Flask).

## Consultas útiles (SSMS)

```sql
USE ClimaTec_ETL;
SELECT * FROM dbo.etl_lote ORDER BY IdLote DESC;                       -- resumen de cada ejecución
SELECT IdLote, COUNT(*) FROM dbo.stg_clima GROUP BY IdLote;             -- filas recibidas por lote
SELECT destino, regla, COUNT(*) FROM dbo.clima_revision GROUP BY destino, regla;  -- excepciones
```

Para empezar de cero: ejecutar `ssis/sql/02_limpiar_lotes.sql`.
