/* ==========================================================================
   ClimaTec - Etapa 3 (SSIS) - Punto 4: Limpieza de datos y excepciones
   Script 03: objetos de apoyo que usa el Data Flow "3 Limpieza".

     1) dbo.cat_indicador       catalogo de indicadores: unidad esperada y si
                                admite valores negativos (homologacion).
     2) dbo.vw_stg_limpieza     lectura de staging por lote, con la marca de
                                duplicados, el cruce con el catalogo y los
                                estadisticos por indicador para los atipicos.

   NO modifica stg_clima, clima_limpio ni clima_revision, y no borra datos.
   Se puede ejecutar las veces que se quiera (idempotente).
   Ejecutar DESPUES de 01_crear_base_climatec_etl.sql.
   ========================================================================== */
USE ClimaTec_ETL;
GO

/* 1) Catalogo de indicadores ------------------------------------------------ */
IF OBJECT_ID(N'dbo.cat_indicador', N'U') IS NULL
    CREATE TABLE dbo.cat_indicador (
        indicador         NVARCHAR(100) NOT NULL PRIMARY KEY,
        unidad            NVARCHAR(50)  NOT NULL,   -- unidad homologada del indicador
        admite_negativos  BIT           NOT NULL    -- 0 = un valor < 0 es invalido
    );
GO

MERGE dbo.cat_indicador AS d
USING (VALUES
    (N'Anomalia de temperatura global',          N'grados C (vs. base)', 1),
    (N'CO2 acumulado historico',                 N'Mt CO2',              0),
    (N'CO2 por carbon',                          N'Mt CO2',              0),
    (N'CO2 por cemento',                         N'Mt CO2',              0),
    (N'CO2 por gas',                             N'Mt CO2',              0),
    (N'CO2 por petroleo',                        N'Mt CO2',              0),
    (N'Concentracion de CO2 atmosferico',        N'ppm',                 0),
    (N'Consumo de energia per capita',           N'kWh/persona',         0),
    (N'Consumo de energia primaria',             N'TWh',                 0),
    (N'Contribucion de GEI a la temperatura',    N'grados C',            1),
    (N'Contribucion del CO2 a la temperatura',   N'grados C',            1),
    (N'Emisiones GEI del sector electrico',      N'Mt eq. CO2',          1),
    (N'Emisiones de CO2 (total)',                N'Mt CO2',              0),
    (N'Emisiones de CO2 per capita',             N't CO2/persona',       0),
    (N'Emisiones de metano',                     N'Mt eq. CO2',          0),
    (N'Emisiones de oxido nitroso',              N'Mt eq. CO2',          0),
    (N'GEI per capita (sin uso del suelo)',      N't eq. CO2/persona',   0),
    (N'Gases de efecto invernadero (total)',     N'Mt eq. CO2',          0),
    (N'Generacion de electricidad',              N'TWh',                 0),
    (N'Participacion baja en carbono',           N'%',                   0),
    (N'Participacion de fosiles en energia',     N'%',                   0),
    (N'Participacion de renovables en energia',  N'%',                   0),
    (N'Poblacion',                               N'personas',            0),
    (N'Variacion anual de CO2',                  N'%',                   1)
) AS o (indicador, unidad, admite_negativos)
ON d.indicador = o.indicador
WHEN MATCHED THEN UPDATE SET unidad = o.unidad, admite_negativos = o.admite_negativos
WHEN NOT MATCHED THEN INSERT (indicador, unidad, admite_negativos)
                      VALUES (o.indicador, o.unidad, o.admite_negativos);
GO

/* 2) Vista de lectura para "3 Limpieza" --------------------------------------
   Devuelve las filas de staging TAL CUAL (valores originales en texto) y le
   agrega columnas de apoyo. No cambia ningun valor: la estandarizacion, el
   tipado y las reglas se aplican dentro del Data Flow de SSIS.

   - rn_clave / rn_exacto: numeran las filas que comparten la clave logica
     (fuente, nivel_geografico, entidad, anio, mes, indicador) o que son
     identicas en las 12 columnas. La fila 1 se conserva; las demas son
     DUPLICADO. Se prefiere conservar la que trae un valor numerico valido.
     (Se hace aqui porque el Sort de SSIS con "quitar duplicados" las
     descarta sin dejar rastro, y la regla pide conservarlas con su motivo.)
   - IdStg_conservado: la fila que se quedo con la clave (para el motivo).
   - lote_previo: la clave ya existe en clima_limpio desde otro lote (regla
     preventiva ante recargas; evita violar el indice unico UX_limpio_clave).
   - unidad_catalogo / admite_negativos: cruce con dbo.cat_indicador
     (NULL = indicador fuera de catalogo).
   - q1, q3, media, desv: estadisticos de 'valor' por indicador dentro del
     lote, solo con filas candidatas a aceptarse, para marcar atipicos
     (1.5*IQR) y calcular valor_z en SSIS.
   ------------------------------------------------------------------------- */
CREATE OR ALTER VIEW dbo.vw_stg_limpieza
AS
WITH base AS (
    SELECT
        s.IdStg, s.IdLote,
        s.fuente, s.fuente_tipo, s.nivel_geografico, s.entidad, s.iso_code,
        s.anio, s.mes, s.periodicidad, s.indicador, s.valor, s.unidad, s.fecha,
        -- versiones normalizadas SOLO para comparar (no se cargan)
        NULLIF(LTRIM(RTRIM(s.fuente)), N'')           AS k_fuente,
        NULLIF(LTRIM(RTRIM(s.nivel_geografico)), N'') AS k_nivel,
        NULLIF(LTRIM(RTRIM(s.entidad)), N'')          AS k_entidad,
        NULLIF(LTRIM(RTRIM(s.indicador)), N'')        AS k_indicador,
        TRY_CONVERT(SMALLINT, TRY_CONVERT(DECIMAL(9,2), NULLIF(LTRIM(RTRIM(s.anio)), N''))) AS k_anio,
        TRY_CONVERT(TINYINT,  TRY_CONVERT(DECIMAL(9,2), NULLIF(LTRIM(RTRIM(s.mes)),  N''))) AS k_mes,
        NULLIF(LTRIM(RTRIM(s.anio)), N'') AS t_anio,
        NULLIF(LTRIM(RTRIM(s.mes)),  N'') AS t_mes,
        TRY_CONVERT(FLOAT, REPLACE(NULLIF(LTRIM(RTRIM(s.valor)), N''), N',', N'.')) AS k_valor
    FROM dbo.stg_clima AS s
),
cruce AS (
    SELECT b.*,
           c.unidad           AS unidad_catalogo,
           c.admite_negativos,
           p.IdLote           AS lote_previo
    FROM base AS b
    LEFT JOIN dbo.cat_indicador AS c
           ON c.indicador = b.k_indicador
    OUTER APPLY (
        SELECT TOP (1) l.IdLote
        FROM dbo.clima_limpio AS l
        WHERE l.IdLote <> b.IdLote
          AND l.fuente = b.k_fuente
          AND l.nivel_geografico = b.k_nivel
          AND l.entidad = b.k_entidad
          AND l.anio = b.k_anio
          AND (l.mes = b.k_mes OR (l.mes IS NULL AND b.k_mes IS NULL))
          AND l.indicador = b.k_indicador
        ORDER BY l.IdLote
    ) AS p
),
numerado AS (
    SELECT c.*,
           ROW_NUMBER() OVER (
               PARTITION BY c.IdLote, c.k_fuente, c.k_nivel, c.k_entidad,
                            COALESCE(CONVERT(NVARCHAR(50), c.k_anio), c.t_anio),
                            COALESCE(CONVERT(NVARCHAR(50), c.k_mes),  c.t_mes),
                            c.k_indicador
               ORDER BY CASE WHEN c.k_valor IS NULL THEN 1 ELSE 0 END, c.IdStg) AS rn_clave,
           FIRST_VALUE(c.IdStg) OVER (
               PARTITION BY c.IdLote, c.k_fuente, c.k_nivel, c.k_entidad,
                            COALESCE(CONVERT(NVARCHAR(50), c.k_anio), c.t_anio),
                            COALESCE(CONVERT(NVARCHAR(50), c.k_mes),  c.t_mes),
                            c.k_indicador
               ORDER BY CASE WHEN c.k_valor IS NULL THEN 1 ELSE 0 END, c.IdStg) AS IdStg_conservado,
           ROW_NUMBER() OVER (
               PARTITION BY c.IdLote, c.fuente, c.fuente_tipo, c.nivel_geografico, c.entidad,
                            c.iso_code, c.anio, c.mes, c.periodicidad, c.indicador,
                            c.valor, c.unidad, c.fecha
               ORDER BY c.IdStg) AS rn_exacto
    FROM cruce AS c
),
candidato AS (
    -- valor que entra al calculo de estadisticos (NULL = no participa)
    SELECT n.*,
           CASE WHEN n.rn_clave = 1
                 AND n.lote_previo IS NULL
                 AND n.k_valor IS NOT NULL
                 AND n.k_anio BETWEEN 2020 AND 2026
                 AND n.admite_negativos IS NOT NULL
                 AND NOT (n.admite_negativos = 0 AND n.k_valor < 0)
                THEN n.k_valor END AS v_stat
    FROM numerado AS n
)
SELECT
    CAST(IdStg  AS BIGINT) AS IdStg,
    CAST(IdLote AS INT)    AS IdLote,
    fuente, fuente_tipo, nivel_geografico, entidad, iso_code,
    anio, mes, periodicidad, indicador, valor, unidad, fecha,
    CAST(unidad_catalogo  AS NVARCHAR(50)) AS unidad_catalogo,
    CAST(admite_negativos AS BIT)          AS admite_negativos,
    CAST(rn_clave         AS BIGINT)       AS rn_clave,
    CAST(rn_exacto        AS BIGINT)       AS rn_exacto,
    CAST(IdStg_conservado AS BIGINT)       AS IdStg_conservado,
    CAST(lote_previo      AS INT)          AS lote_previo,
    CAST(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY v_stat) OVER (PARTITION BY IdLote, k_indicador) AS FLOAT) AS q1,
    CAST(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY v_stat) OVER (PARTITION BY IdLote, k_indicador) AS FLOAT) AS q3,
    CAST(AVG(v_stat)    OVER (PARTITION BY IdLote, k_indicador) AS FLOAT) AS media,
    CAST(STDEVP(v_stat) OVER (PARTITION BY IdLote, k_indicador) AS FLOAT) AS desv
FROM candidato;
GO

/* Comprobacion rapida */
SELECT 'cat_indicador' AS objeto, COUNT(*) AS filas FROM dbo.cat_indicador
UNION ALL
SELECT 'vw_stg_limpieza (todas las filas de staging)', COUNT(*) FROM dbo.vw_stg_limpieza;
GO
