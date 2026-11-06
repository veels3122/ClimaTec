-- ClimaTec - Etapa 5: creacion de tablas, claves y relaciones del modelo estrella (SQLite).
-- Es el DDL que ejecuta scripts/cargar_modelo.py. Version SQL Server: ssis/sql/04_modelo_estrella.sql

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS hechos_observacion;
DROP TABLE IF EXISTS dim_tiempo;
DROP TABLE IF EXISTS dim_geografia;
DROP TABLE IF EXISTS dim_indicador;
DROP TABLE IF EXISTS dim_fuente;

CREATE TABLE dim_tiempo (
    id_tiempo      INTEGER PRIMARY KEY,          -- AAAAMM; MM = 00 en series anuales; -1 desconocido
    anio           INTEGER NOT NULL,
    semestre       INTEGER NOT NULL,             -- 0 = no aplica (serie anual)
    trimestre      INTEGER NOT NULL,
    mes            INTEGER NOT NULL,
    nombre_mes     TEXT    NOT NULL,
    periodicidad   TEXT    NOT NULL,
    nivel_detalle  TEXT    NOT NULL              -- Anio | Mes
);

CREATE TABLE dim_geografia (
    id_geo            INTEGER PRIMARY KEY,
    nivel_geografico  TEXT NOT NULL,
    region            TEXT NOT NULL,
    region_es         TEXT NOT NULL,
    pais              TEXT NOT NULL,
    entidad           TEXT NOT NULL,
    iso_code          TEXT NOT NULL,             -- "No aplica" en agregados
    es_foco           INTEGER NOT NULL CHECK (es_foco IN (0, 1)),
    UNIQUE (entidad, nivel_geografico)
);

CREATE TABLE dim_indicador (
    id_indicador  INTEGER PRIMARY KEY,
    categoria     TEXT NOT NULL,
    indicador     TEXT NOT NULL UNIQUE,
    unidad        TEXT NOT NULL,
    tipo_medida   TEXT NOT NULL,
    agregacion    TEXT NOT NULL CHECK (agregacion IN ('suma', 'promedio'))
);

CREATE TABLE dim_fuente (
    id_fuente    INTEGER PRIMARY KEY,
    fuente_tipo  TEXT NOT NULL,
    proveedor    TEXT NOT NULL,
    fuente       TEXT NOT NULL UNIQUE
);

CREATE TABLE hechos_observacion (
    id_hecho      INTEGER PRIMARY KEY,
    id_tiempo     INTEGER NOT NULL REFERENCES dim_tiempo(id_tiempo),
    id_geo        INTEGER NOT NULL REFERENCES dim_geografia(id_geo),
    id_indicador  INTEGER NOT NULL REFERENCES dim_indicador(id_indicador),
    id_fuente     INTEGER NOT NULL REFERENCES dim_fuente(id_fuente),
    valor         REAL    NOT NULL,
    valor_z       REAL,                         -- NULL si no se pudo normalizar
    atipico       INTEGER NOT NULL CHECK (atipico IN (0, 1)),
    n_registros   INTEGER NOT NULL DEFAULT 1,
    UNIQUE (id_tiempo, id_geo, id_indicador, id_fuente)   -- granularidad del hecho
);

CREATE INDEX ix_hechos_tiempo    ON hechos_observacion(id_tiempo);
CREATE INDEX ix_hechos_geo       ON hechos_observacion(id_geo);
CREATE INDEX ix_hechos_indicador ON hechos_observacion(id_indicador);
CREATE INDEX ix_hechos_fuente    ON hechos_observacion(id_fuente);

CREATE TABLE IF NOT EXISTS etl_carga_modelo (
    id_carga        INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha           TEXT    NOT NULL,
    origen          TEXT    NOT NULL,
    huella_md5      TEXT    NOT NULL,
    filas_origen    INTEGER NOT NULL,
    filas_hechos    INTEGER NOT NULL,
    hechos_fk_desconocida INTEGER NOT NULL,
    duracion_seg    REAL    NOT NULL
);
