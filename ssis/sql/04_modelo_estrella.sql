/* ==========================================================================
   ClimaTec - Etapa 5 / Analisis multidimensional
   04_modelo_estrella.sql

   Crea el modelo estrella en el esquema dw de ClimaTec_ETL y lo carga desde
   dbo.clima_limpio (destino del paquete SSIS de la Etapa 3).

     dw.dim_tiempo       Anio > Semestre > Trimestre > Mes   (clave AAAAMM; MM=00 anual)
     dw.dim_geografia    Mundo > Region > Pais
     dw.dim_indicador    Categoria > Indicador (+ regla de agregacion)
     dw.dim_fuente       Tipo de fuente > Proveedor > Fuente
     dw.hechos_observacion  granularidad: indicador x entidad x fecha x fuente

   Es el mismo modelo que arma en memoria scripts/multidimensional.py.
   Se puede ejecutar varias veces: borra y recarga el esquema dw.
   ========================================================================== */
USE ClimaTec_ETL;
GO

IF SCHEMA_ID(N'dw') IS NULL EXEC(N'CREATE SCHEMA dw');
GO

DROP TABLE IF EXISTS dw.hechos_observacion;
DROP TABLE IF EXISTS dw.dim_tiempo;
DROP TABLE IF EXISTS dw.dim_geografia;
DROP TABLE IF EXISTS dw.dim_indicador;
DROP TABLE IF EXISTS dw.dim_fuente;
DROP TABLE IF EXISTS dw.map_pais_region;
DROP TABLE IF EXISTS dw.map_indicador;
GO

/* 0) Tablas de apoyo -------------------------------------------------------- */
CREATE TABLE dw.map_pais_region (
    iso_code CHAR(3)       NOT NULL PRIMARY KEY,
    region   NVARCHAR(50)  NOT NULL
);
INSERT INTO dw.map_pais_region (iso_code, region) VALUES
    (N'AFG', N'Asia'),
    (N'ALB', N'Europe'),
    (N'DZA', N'Africa'),
    (N'ASM', N'Oceania'),
    (N'AND', N'Europe'),
    (N'AGO', N'Africa'),
    (N'AIA', N'North America'),
    (N'ATA', N'Antarctica'),
    (N'ATG', N'North America'),
    (N'ARG', N'South America'),
    (N'ARM', N'Asia'),
    (N'ABW', N'North America'),
    (N'AUS', N'Oceania'),
    (N'AUT', N'Europe'),
    (N'AZE', N'Asia'),
    (N'BHS', N'North America'),
    (N'BHR', N'Asia'),
    (N'BGD', N'Asia'),
    (N'BRB', N'North America'),
    (N'BLR', N'Europe'),
    (N'BEL', N'Europe'),
    (N'BLZ', N'North America'),
    (N'BEN', N'Africa'),
    (N'BMU', N'North America'),
    (N'BTN', N'Asia'),
    (N'BOL', N'South America'),
    (N'BES', N'North America'),
    (N'BIH', N'Europe'),
    (N'BWA', N'Africa'),
    (N'BRA', N'South America'),
    (N'VGB', N'North America'),
    (N'BRN', N'Asia'),
    (N'BGR', N'Europe'),
    (N'BFA', N'Africa'),
    (N'BDI', N'Africa'),
    (N'KHM', N'Asia'),
    (N'CMR', N'Africa'),
    (N'CAN', N'North America'),
    (N'CPV', N'Africa'),
    (N'CYM', N'North America'),
    (N'CAF', N'Africa'),
    (N'TCD', N'Africa'),
    (N'CHL', N'South America'),
    (N'CHN', N'Asia'),
    (N'CXR', N'Asia'),
    (N'COL', N'South America'),
    (N'COM', N'Africa'),
    (N'COG', N'Africa'),
    (N'COK', N'Oceania'),
    (N'CRI', N'North America'),
    (N'CIV', N'Africa'),
    (N'HRV', N'Europe'),
    (N'CUB', N'North America'),
    (N'CUW', N'North America'),
    (N'CYP', N'Asia'),
    (N'CZE', N'Europe'),
    (N'COD', N'Africa'),
    (N'DNK', N'Europe'),
    (N'DJI', N'Africa'),
    (N'DMA', N'North America'),
    (N'DOM', N'North America'),
    (N'TLS', N'Asia'),
    (N'ECU', N'South America'),
    (N'EGY', N'Africa'),
    (N'SLV', N'North America'),
    (N'GNQ', N'Africa'),
    (N'ERI', N'Africa'),
    (N'EST', N'Europe'),
    (N'SWZ', N'Africa'),
    (N'ETH', N'Africa'),
    (N'FLK', N'South America'),
    (N'FRO', N'Europe'),
    (N'FJI', N'Oceania'),
    (N'FIN', N'Europe'),
    (N'FRA', N'Europe'),
    (N'GUF', N'South America'),
    (N'PYF', N'Oceania'),
    (N'GAB', N'Africa'),
    (N'GMB', N'Africa'),
    (N'GEO', N'Asia'),
    (N'DEU', N'Europe'),
    (N'GHA', N'Africa'),
    (N'GIB', N'Europe'),
    (N'GRC', N'Europe'),
    (N'GRL', N'North America'),
    (N'GRD', N'North America'),
    (N'GLP', N'North America'),
    (N'GUM', N'Oceania'),
    (N'GTM', N'North America'),
    (N'GIN', N'Africa'),
    (N'GNB', N'Africa'),
    (N'GUY', N'South America'),
    (N'HTI', N'North America'),
    (N'HND', N'North America'),
    (N'HKG', N'Asia'),
    (N'HUN', N'Europe'),
    (N'ISL', N'Europe'),
    (N'IND', N'Asia'),
    (N'IDN', N'Asia'),
    (N'IRN', N'Asia'),
    (N'IRQ', N'Asia'),
    (N'IRL', N'Europe'),
    (N'ISR', N'Asia'),
    (N'ITA', N'Europe'),
    (N'JAM', N'North America'),
    (N'JPN', N'Asia'),
    (N'JOR', N'Asia'),
    (N'KAZ', N'Asia'),
    (N'KEN', N'Africa'),
    (N'KIR', N'Oceania'),
    (N'KWT', N'Asia'),
    (N'KGZ', N'Asia'),
    (N'LAO', N'Asia'),
    (N'LVA', N'Europe'),
    (N'LBN', N'Asia'),
    (N'LSO', N'Africa'),
    (N'LBR', N'Africa'),
    (N'LBY', N'Africa'),
    (N'LIE', N'Europe'),
    (N'LTU', N'Europe'),
    (N'LUX', N'Europe'),
    (N'MAC', N'Asia'),
    (N'MDG', N'Africa'),
    (N'MWI', N'Africa'),
    (N'MYS', N'Asia'),
    (N'MDV', N'Asia'),
    (N'MLI', N'Africa'),
    (N'MLT', N'Europe'),
    (N'MHL', N'Oceania'),
    (N'MTQ', N'North America'),
    (N'MRT', N'Africa'),
    (N'MUS', N'Africa'),
    (N'MEX', N'North America'),
    (N'FSM', N'Oceania'),
    (N'MDA', N'Europe'),
    (N'MCO', N'Europe'),
    (N'MNG', N'Asia'),
    (N'MNE', N'Europe'),
    (N'MSR', N'North America'),
    (N'MAR', N'Africa'),
    (N'MOZ', N'Africa'),
    (N'MMR', N'Asia'),
    (N'NAM', N'Africa'),
    (N'NRU', N'Oceania'),
    (N'NPL', N'Asia'),
    (N'NLD', N'Europe'),
    (N'NCL', N'Oceania'),
    (N'NZL', N'Oceania'),
    (N'NIC', N'North America'),
    (N'NER', N'Africa'),
    (N'NGA', N'Africa'),
    (N'NIU', N'Oceania'),
    (N'PRK', N'Asia'),
    (N'MKD', N'Europe'),
    (N'MNP', N'Oceania'),
    (N'NOR', N'Europe'),
    (N'OMN', N'Asia'),
    (N'PAK', N'Asia'),
    (N'PLW', N'Oceania'),
    (N'PSE', N'Asia'),
    (N'PAN', N'North America'),
    (N'PNG', N'Oceania'),
    (N'PRY', N'South America'),
    (N'PER', N'South America'),
    (N'PHL', N'Asia'),
    (N'POL', N'Europe'),
    (N'PRT', N'Europe'),
    (N'PRI', N'North America'),
    (N'QAT', N'Asia'),
    (N'REU', N'Africa'),
    (N'ROU', N'Europe'),
    (N'RUS', N'Europe'),
    (N'RWA', N'Africa'),
    (N'SHN', N'Africa'),
    (N'KNA', N'North America'),
    (N'LCA', N'North America'),
    (N'SPM', N'North America'),
    (N'VCT', N'North America'),
    (N'WSM', N'Oceania'),
    (N'SMR', N'Europe'),
    (N'STP', N'Africa'),
    (N'SAU', N'Asia'),
    (N'SEN', N'Africa'),
    (N'SRB', N'Europe'),
    (N'SYC', N'Africa'),
    (N'SLE', N'Africa'),
    (N'SGP', N'Asia'),
    (N'SXM', N'North America'),
    (N'SVK', N'Europe'),
    (N'SVN', N'Europe'),
    (N'SLB', N'Oceania'),
    (N'SOM', N'Africa'),
    (N'ZAF', N'Africa'),
    (N'KOR', N'Asia'),
    (N'SSD', N'Africa'),
    (N'ESP', N'Europe'),
    (N'LKA', N'Asia'),
    (N'SDN', N'Africa'),
    (N'SUR', N'South America'),
    (N'SWE', N'Europe'),
    (N'CHE', N'Europe'),
    (N'SYR', N'Asia'),
    (N'TWN', N'Asia'),
    (N'TJK', N'Asia'),
    (N'TZA', N'Africa'),
    (N'THA', N'Asia'),
    (N'TGO', N'Africa'),
    (N'TON', N'Oceania'),
    (N'TTO', N'North America'),
    (N'TUN', N'Africa'),
    (N'TUR', N'Asia'),
    (N'TKM', N'Asia'),
    (N'TCA', N'North America'),
    (N'TUV', N'Oceania'),
    (N'UGA', N'Africa'),
    (N'UKR', N'Europe'),
    (N'ARE', N'Asia'),
    (N'GBR', N'Europe'),
    (N'USA', N'North America'),
    (N'VIR', N'North America'),
    (N'URY', N'South America'),
    (N'UZB', N'Asia'),
    (N'VUT', N'Oceania'),
    (N'VAT', N'Europe'),
    (N'VEN', N'South America'),
    (N'VNM', N'Asia'),
    (N'WLF', N'Oceania'),
    (N'ESH', N'Africa'),
    (N'YEM', N'Asia'),
    (N'ZMB', N'Africa'),
    (N'ZWE', N'Africa');

CREATE TABLE dw.map_indicador (
    indicador   NVARCHAR(100) NOT NULL PRIMARY KEY,
    categoria   NVARCHAR(60)  NOT NULL,
    tipo_medida NVARCHAR(40)  NOT NULL,
    agregacion  NVARCHAR(10)  NOT NULL   -- suma | promedio
);
INSERT INTO dw.map_indicador (indicador, categoria, tipo_medida, agregacion) VALUES
    (N'Emisiones de CO2 (total)', N'Emisiones de CO2', N'Absoluto', N'suma'),
    (N'CO2 por carbon', N'Emisiones de CO2', N'Absoluto', N'suma'),
    (N'CO2 por petroleo', N'Emisiones de CO2', N'Absoluto', N'suma'),
    (N'CO2 por gas', N'Emisiones de CO2', N'Absoluto', N'suma'),
    (N'CO2 por cemento', N'Emisiones de CO2', N'Absoluto', N'suma'),
    (N'CO2 acumulado historico', N'Emisiones de CO2', N'Absoluto (acumulado)', N'suma'),
    (N'Emisiones de CO2 per capita', N'Emisiones de CO2', N'Per capita', N'promedio'),
    (N'Variacion anual de CO2', N'Emisiones de CO2', N'Porcentaje', N'promedio'),
    (N'Emisiones de metano', N'Otros gases de efecto invernadero', N'Absoluto', N'suma'),
    (N'Emisiones de oxido nitroso', N'Otros gases de efecto invernadero', N'Absoluto', N'suma'),
    (N'Gases de efecto invernadero (total)', N'Otros gases de efecto invernadero', N'Absoluto', N'suma'),
    (N'GEI per capita (sin uso del suelo)', N'Otros gases de efecto invernadero', N'Per capita', N'promedio'),
    (N'Emisiones GEI del sector electrico', N'Otros gases de efecto invernadero', N'Absoluto', N'suma'),
    (N'Consumo de energia primaria', N'Energia', N'Absoluto', N'suma'),
    (N'Consumo de energia per capita', N'Energia', N'Per capita', N'promedio'),
    (N'Generacion de electricidad', N'Energia', N'Absoluto', N'suma'),
    (N'Participacion de renovables en energia', N'Energia', N'Porcentaje', N'promedio'),
    (N'Participacion de fosiles en energia', N'Energia', N'Porcentaje', N'promedio'),
    (N'Participacion baja en carbono', N'Energia', N'Porcentaje', N'promedio'),
    (N'Anomalia de temperatura global', N'Clima y atmosfera', N'Anomalia', N'promedio'),
    (N'Concentracion de CO2 atmosferico', N'Clima y atmosfera', N'Concentracion', N'promedio'),
    (N'Contribucion del CO2 a la temperatura', N'Clima y atmosfera', N'Absoluto', N'suma'),
    (N'Contribucion de GEI a la temperatura', N'Clima y atmosfera', N'Absoluto', N'suma'),
    (N'Poblacion', N'Demografia', N'Absoluto', N'suma');
GO

/* 1) Dimension Tiempo ------------------------------------------------------- */
CREATE TABLE dw.dim_tiempo (
    id_tiempo     INT          NOT NULL PRIMARY KEY,   -- AAAAMM
    anio          SMALLINT     NOT NULL,
    semestre      TINYINT      NOT NULL,               -- 0 en series anuales
    trimestre     TINYINT      NOT NULL,
    mes           TINYINT      NOT NULL,
    periodicidad  NVARCHAR(20) NOT NULL
);
INSERT INTO dw.dim_tiempo (id_tiempo, anio, semestre, trimestre, mes, periodicidad)
SELECT DISTINCT
    anio * 100 + ISNULL(mes, 0),
    anio,
    CASE WHEN mes IS NULL THEN 0 ELSE (mes - 1) / 6 + 1 END,
    CASE WHEN mes IS NULL THEN 0 ELSE (mes - 1) / 3 + 1 END,
    ISNULL(mes, 0),
    CASE WHEN mes IS NULL THEN N'Anual' ELSE N'Mensual' END
FROM dbo.clima_limpio;
GO

/* 2) Dimension Geografia ---------------------------------------------------- */
CREATE TABLE dw.dim_geografia (
    id_geo            INT IDENTITY(1,1) PRIMARY KEY,
    nivel_geografico  NVARCHAR(20)  NOT NULL,
    region            NVARCHAR(50)  NOT NULL,
    entidad           NVARCHAR(100) NOT NULL,
    iso_code          CHAR(3)       NULL,
    es_foco           BIT           NOT NULL,
    CONSTRAINT UX_dim_geo UNIQUE (entidad, nivel_geografico)
);
INSERT INTO dw.dim_geografia (nivel_geografico, region, entidad, iso_code, es_foco)
SELECT DISTINCT
    c.nivel_geografico,
    CASE c.nivel_geografico
        WHEN N'Nacional' THEN ISNULL(m.region, N'Sin region')
        WHEN N'Regional' THEN c.entidad
        ELSE N'Mundo' END,
    c.entidad,
    c.iso_code,
    CASE WHEN c.entidad = N'Colombia' THEN 1 ELSE 0 END
FROM dbo.clima_limpio c
LEFT JOIN dw.map_pais_region m ON m.iso_code = c.iso_code;
GO

/* 3) Dimension Indicador ---------------------------------------------------- */
CREATE TABLE dw.dim_indicador (
    id_indicador INT IDENTITY(1,1) PRIMARY KEY,
    categoria    NVARCHAR(60)  NOT NULL,
    indicador    NVARCHAR(100) NOT NULL UNIQUE,
    unidad       NVARCHAR(50)  NOT NULL,
    tipo_medida  NVARCHAR(40)  NOT NULL,
    agregacion   NVARCHAR(10)  NOT NULL
);
INSERT INTO dw.dim_indicador (categoria, indicador, unidad, tipo_medida, agregacion)
SELECT ISNULL(m.categoria, N'Otros'), i.indicador, i.unidad,
       ISNULL(m.tipo_medida, N'Otro'), ISNULL(m.agregacion, N'promedio')
FROM (SELECT indicador, MAX(unidad) AS unidad FROM dbo.clima_limpio GROUP BY indicador) i
LEFT JOIN dw.map_indicador m ON m.indicador = i.indicador;
GO

/* 4) Dimension Fuente ------------------------------------------------------- */
CREATE TABLE dw.dim_fuente (
    id_fuente   INT IDENTITY(1,1) PRIMARY KEY,
    fuente_tipo NVARCHAR(20)  NOT NULL,
    proveedor   NVARCHAR(60)  NOT NULL,
    fuente      NVARCHAR(150) NOT NULL UNIQUE
);
INSERT INTO dw.dim_fuente (fuente_tipo, proveedor, fuente)
SELECT DISTINCT fuente_tipo,
    CASE WHEN fuente LIKE N'Our World in Data%' THEN N'Our World in Data'
         WHEN fuente LIKE N'NOAA%' THEN N'NOAA'
         WHEN fuente LIKE N'NASA%' THEN N'NASA'
         ELSE LEFT(fuente, CHARINDEX(N' - ', fuente + N' - ') - 1) END,
    fuente
FROM dbo.clima_limpio;
GO

/* 5) Tabla de hechos -------------------------------------------------------- */
CREATE TABLE dw.hechos_observacion (
    id_hecho      BIGINT IDENTITY(1,1) PRIMARY KEY,
    id_tiempo     INT           NOT NULL REFERENCES dw.dim_tiempo(id_tiempo),
    id_geo        INT           NOT NULL REFERENCES dw.dim_geografia(id_geo),
    id_indicador  INT           NOT NULL REFERENCES dw.dim_indicador(id_indicador),
    id_fuente     INT           NOT NULL REFERENCES dw.dim_fuente(id_fuente),
    valor         DECIMAL(18,4) NOT NULL,
    valor_z       DECIMAL(10,4) NULL,
    atipico       BIT           NULL,
    n_registros   INT           NOT NULL DEFAULT 1,
    IdLimpio      BIGINT        NOT NULL,     -- trazabilidad con dbo.clima_limpio
    CONSTRAINT UX_hechos_grano UNIQUE (id_tiempo, id_geo, id_indicador, id_fuente)
);
INSERT INTO dw.hechos_observacion (id_tiempo, id_geo, id_indicador, id_fuente, valor, valor_z, atipico, IdLimpio)
SELECT c.anio * 100 + ISNULL(c.mes, 0), g.id_geo, i.id_indicador, f.id_fuente,
       c.valor, c.valor_z, c.atipico, c.IdLimpio
FROM dbo.clima_limpio c
JOIN dw.dim_geografia g ON g.entidad = c.entidad AND g.nivel_geografico = c.nivel_geografico
JOIN dw.dim_indicador i ON i.indicador = c.indicador
JOIN dw.dim_fuente    f ON f.fuente = c.fuente;
GO

/* 6) Verificacion: los hechos deben ser tantos como las filas limpias ------- */
SELECT (SELECT COUNT(*) FROM dbo.clima_limpio)        AS filas_clima_limpio,
       (SELECT COUNT(*) FROM dw.hechos_observacion)   AS hechos_cargados,
       (SELECT COUNT(*) FROM dw.dim_tiempo)           AS dim_tiempo,
       (SELECT COUNT(*) FROM dw.dim_geografia)        AS dim_geografia,
       (SELECT COUNT(*) FROM dw.dim_indicador)        AS dim_indicador,
       (SELECT COUNT(*) FROM dw.dim_fuente)           AS dim_fuente;
GO

/* 7) Ejemplos de operaciones OLAP ------------------------------------------- */
-- Roll-up: CO2 por region y anio (suma de paises)
SELECT g.region, t.anio, SUM(h.valor) AS co2_mt
FROM dw.hechos_observacion h
JOIN dw.dim_tiempo t    ON t.id_tiempo = h.id_tiempo
JOIN dw.dim_geografia g ON g.id_geo = h.id_geo
JOIN dw.dim_indicador i ON i.id_indicador = h.id_indicador
WHERE i.indicador = N'Emisiones de CO2 (total)' AND g.nivel_geografico = N'Nacional'
GROUP BY ROLLUP (g.region, t.anio);

-- Drill-down: paises de Sudamerica en 2024
SELECT g.entidad, h.valor AS co2_mt
FROM dw.hechos_observacion h
JOIN dw.dim_tiempo t    ON t.id_tiempo = h.id_tiempo
JOIN dw.dim_geografia g ON g.id_geo = h.id_geo
JOIN dw.dim_indicador i ON i.id_indicador = h.id_indicador
WHERE i.indicador = N'Emisiones de CO2 (total)' AND g.region = N'South America'
  AND g.nivel_geografico = N'Nacional' AND t.anio = 2024
ORDER BY h.valor DESC;

-- Pivot: % de atipicos por nivel geografico (filas) y categoria (columnas)
SELECT nivel_geografico, [Emisiones de CO2], [Otros gases de efecto invernadero], [Energia], [Clima y atmosfera], [Demografia]
FROM (
    SELECT g.nivel_geografico, i.categoria, CAST(h.atipico AS FLOAT) * 100 AS pct
    FROM dw.hechos_observacion h
    JOIN dw.dim_geografia g ON g.id_geo = h.id_geo
    JOIN dw.dim_indicador i ON i.id_indicador = h.id_indicador
) s
PIVOT (AVG(pct) FOR categoria IN ([Emisiones de CO2], [Otros gases de efecto invernadero], [Energia], [Clima y atmosfera], [Demografia])) p;
GO
