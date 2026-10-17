/* ==========================================================================
   ClimaTec - Etapa ETL (SSIS)
   Script 01: crea la base ClimaTec_ETL, sus 4 tablas y los procedimientos
   que usa el Control Flow del paquete (abrir, verificar y cerrar lote).

   Ejecutar en SSMS conectado a tu instancia local. Se puede volver a correr:
   ATENCION -> recrea las tablas VACIAS (borra lo cargado antes).
   ========================================================================== */

IF DB_ID(N'ClimaTec_ETL') IS NULL
    CREATE DATABASE ClimaTec_ETL;
GO
-- Lecturas sin bloqueo: "3 Limpieza" lee clima_limpio (vista vw_stg_limpieza)
-- mientras el destino clima_limpio inserta con Table lock. Sin esto el Data Flow
-- se queda detenido (ajuste 3 de ITERACIONES.md).
ALTER DATABASE ClimaTec_ETL SET READ_COMMITTED_SNAPSHOT ON WITH ROLLBACK IMMEDIATE;
GO
USE ClimaTec_ETL;
GO

DROP PROCEDURE IF EXISTS dbo.usp_abrir_lote;
DROP PROCEDURE IF EXISTS dbo.usp_verificar_lote;
DROP PROCEDURE IF EXISTS dbo.usp_cerrar_lote;
DROP TABLE IF EXISTS dbo.clima_revision;
DROP TABLE IF EXISTS dbo.clima_limpio;
DROP TABLE IF EXISTS dbo.stg_clima;
DROP TABLE IF EXISTS dbo.etl_lote;
GO

/* 1) Registro de ejecuciones: una fila por cada corrida del paquete ---------- */
CREATE TABLE dbo.etl_lote (
    IdLote            INT IDENTITY(1,1) PRIMARY KEY,
    iteracion         INT            NOT NULL,          -- 1, 2 o 3
    descripcion       NVARCHAR(200)  NULL,              -- que cambio en esta corrida
    archivo           NVARCHAR(260)  NULL,              -- CSV que se cargo
    estado            NVARCHAR(20)   NOT NULL DEFAULT N'EN_CURSO', -- EN_CURSO / OK / FALLIDO
    inicio            DATETIME2(0)   NOT NULL DEFAULT SYSDATETIME(),
    fin               DATETIME2(0)   NULL,
    filas_recibidas   INT NULL,
    filas_aceptadas   INT NULL,
    filas_duplicadas  INT NULL,
    filas_revision    INT NULL,
    balance_ok        BIT NULL                          -- recibidas = aceptadas + duplicadas + revision
);
GO

/* 2) Staging: copia CRUDA del CSV, todo como texto, nunca se modifica ------ */
CREATE TABLE dbo.stg_clima (
    IdStg             BIGINT IDENTITY(1,1) PRIMARY KEY, -- clave de fila estable
    IdLote            INT            NOT NULL REFERENCES dbo.etl_lote(IdLote),
    archivo_origen    NVARCHAR(260)  NULL,
    fecha_carga       DATETIME2(0)   NOT NULL DEFAULT SYSDATETIME(),
    -- las 12 columnas del CSV, tal cual llegan
    fuente            NVARCHAR(255)  NULL,
    fuente_tipo       NVARCHAR(100)  NULL,
    nivel_geografico  NVARCHAR(100)  NULL,
    entidad           NVARCHAR(255)  NULL,
    iso_code          NVARCHAR(50)   NULL,
    anio              NVARCHAR(50)   NULL,
    mes               NVARCHAR(50)   NULL,
    periodicidad      NVARCHAR(100)  NULL,
    indicador         NVARCHAR(255)  NULL,
    valor             NVARCHAR(100)  NULL,
    unidad            NVARCHAR(100)  NULL,
    fecha             NVARCHAR(50)   NULL
);
CREATE INDEX IX_stg_lote ON dbo.stg_clima(IdLote);
GO

/* 3) Destino de registros ACEPTADOS, con tipos correctos -------------------- */
CREATE TABLE dbo.clima_limpio (
    IdLimpio          BIGINT IDENTITY(1,1) PRIMARY KEY,
    IdLote            INT            NOT NULL REFERENCES dbo.etl_lote(IdLote),
    IdStg             BIGINT         NOT NULL,          -- de que fila de staging salio
    fuente            NVARCHAR(150)  NOT NULL,
    fuente_tipo       NVARCHAR(20)   NOT NULL,
    nivel_geografico  NVARCHAR(20)   NOT NULL,
    entidad           NVARCHAR(100)  NOT NULL,
    iso_code          CHAR(3)        NULL,              -- vacio por diseno en agregados
    anio              SMALLINT       NOT NULL,
    mes               TINYINT        NULL,              -- vacio por diseno en series anuales
    periodicidad      NVARCHAR(20)   NOT NULL,
    indicador         NVARCHAR(100)  NOT NULL,
    valor             DECIMAL(18,4)  NOT NULL,
    unidad            NVARCHAR(50)   NOT NULL,
    fecha             DATE           NOT NULL,
    atipico           BIT            NULL,
    valor_z           DECIMAL(10,4)  NULL
);
-- Clave logica (regla de duplicados de Ana): impide que una 2a carga duplique
CREATE UNIQUE INDEX UX_limpio_clave ON dbo.clima_limpio
    (fuente, nivel_geografico, entidad, anio, mes, indicador);
GO

/* 4) Destino de EXCEPCIONES: duplicados y registros enviados a revision ---- */
CREATE TABLE dbo.clima_revision (
    IdRevision        BIGINT IDENTITY(1,1) PRIMARY KEY,
    IdLote            INT            NOT NULL REFERENCES dbo.etl_lote(IdLote),
    IdStg             BIGINT         NULL,
    destino           NVARCHAR(30)   NOT NULL,          -- DUPLICADO / REVISION_NEGOCIO / ERROR_CONVERSION
    regla             NVARCHAR(100)  NOT NULL,          -- que regla incumplio
    motivo            NVARCHAR(400)  NULL,              -- explicacion legible
    fecha_registro    DATETIME2(0)   NOT NULL DEFAULT SYSDATETIME(),
    -- valores ORIGINALES (texto), para no perder nada
    fuente            NVARCHAR(255)  NULL,
    fuente_tipo       NVARCHAR(100)  NULL,
    nivel_geografico  NVARCHAR(100)  NULL,
    entidad           NVARCHAR(255)  NULL,
    iso_code          NVARCHAR(50)   NULL,
    anio              NVARCHAR(50)   NULL,
    mes               NVARCHAR(50)   NULL,
    periodicidad      NVARCHAR(100)  NULL,
    indicador         NVARCHAR(255)  NULL,
    valor             NVARCHAR(100)  NULL,
    unidad            NVARCHAR(100)  NULL,
    fecha             NVARCHAR(50)   NULL
);
GO

/* ==========================================================================
   Procedimientos para el Control Flow (diapositiva 10 del docente)
   ========================================================================== */

-- Paso 1. Inicio: abre un lote y devuelve su IdLote
CREATE PROCEDURE dbo.usp_abrir_lote
    @iteracion   INT,
    @descripcion NVARCHAR(200),
    @archivo     NVARCHAR(260)
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO dbo.etl_lote (iteracion, descripcion, archivo)
    VALUES (@iteracion, @descripcion, @archivo);
    SELECT CAST(SCOPE_IDENTITY() AS INT) AS IdLote;
END
GO

-- Paso 4. Verificacion: cuenta cada destino y comprueba el balance
CREATE PROCEDURE dbo.usp_verificar_lote
    @IdLote INT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @rec INT = (SELECT COUNT(*) FROM dbo.stg_clima      WHERE IdLote = @IdLote);
    DECLARE @ace INT = (SELECT COUNT(*) FROM dbo.clima_limpio   WHERE IdLote = @IdLote);
    DECLARE @dup INT = (SELECT COUNT(*) FROM dbo.clima_revision WHERE IdLote = @IdLote AND destino = N'DUPLICADO');
    DECLARE @rev INT = (SELECT COUNT(*) FROM dbo.clima_revision WHERE IdLote = @IdLote AND destino <> N'DUPLICADO');

    UPDATE dbo.etl_lote
       SET filas_recibidas  = @rec,
           filas_aceptadas  = @ace,
           filas_duplicadas = @dup,
           filas_revision   = @rev,
           balance_ok       = CASE WHEN @rec = @ace + @dup + @rev THEN 1 ELSE 0 END
     WHERE IdLote = @IdLote;
END
GO

-- Paso 5. Cierre: marca el estado final del lote
CREATE PROCEDURE dbo.usp_cerrar_lote
    @IdLote INT
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.etl_lote
       SET fin    = SYSDATETIME(),
           estado = CASE WHEN balance_ok = 1 THEN N'OK' ELSE N'REVISAR_BALANCE' END
     WHERE IdLote = @IdLote;
END
GO

/* Comprobacion rapida: deben salir las 4 tablas vacias */
SELECT 'etl_lote' AS tabla, COUNT(*) AS filas FROM dbo.etl_lote
UNION ALL SELECT 'stg_clima',      COUNT(*) FROM dbo.stg_clima
UNION ALL SELECT 'clima_limpio',   COUNT(*) FROM dbo.clima_limpio
UNION ALL SELECT 'clima_revision', COUNT(*) FROM dbo.clima_revision;
GO
