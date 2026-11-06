# -*- coding: utf-8 -*-
"""
ClimaTec - Etapa 5 / Implementacion y carga del modelo estrella.

Procedimiento reproducible que toma los datos TRATADOS (clima_limpio.csv, salida
de las Etapas 2 y 3) y los carga en un almacen SQLite consultable desde Flask:

    data/dw/climatec_dw.sqlite
        dim_tiempo, dim_geografia, dim_indicador, dim_fuente   (dimensiones)
        hechos_observacion                                     (tabla de hechos)
        etl_carga_modelo                                       (bitacora de cargas)

Pasos:
  1. Extraer   : leer clima_limpio.csv (o el DataFrame limpio que entregue la app).
  2. Transformar:
       - construir las dimensiones con claves sustitutas (multidimensional.construir_estrella);
       - agregar un miembro "Desconocido" (clave -1) en cada dimension;
       - reemplazar nulos estructurales por etiquetas explicitas ("No aplica");
       - resolver las claves foraneas de cada hecho; si una no se encuentra,
         el hecho apunta al miembro -1 en lugar de perderse.
  3. Cargar    : recrear las tablas con PK, FK, UNIQUE e indices, insertar y
                 registrar la carga (filas, huella MD5 del origen, duracion).

Uso:
    python scripts/cargar_modelo.py            # carga desde data/raw/clima_limpio.csv
La app llama a asegurar_modelo() al arrancar: si el almacen no existe o el
origen cambio (huella distinta), lo vuelve a cargar.
"""

import hashlib
import os
import sqlite3
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import multidimensional as md  # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_ORIGEN = os.path.join(BASE_DIR, "data", "raw", "clima_limpio.csv")
RUTA_DB = os.path.join(BASE_DIR, "data", "dw", "climatec_dw.sqlite")

DESCONOCIDO = -1
NO_APLICA = "No aplica"

DDL = """
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
"""

# Correspondencia variable original -> campo del modelo (se publica en Flask).
CORRESPONDENCIA = [
    ("anio", "dim_tiempo.anio", "Entero. Junto con mes forma la clave id_tiempo = anio × 100 + mes."),
    ("mes", "dim_tiempo.mes / semestre / trimestre / nombre_mes",
     "Vacio en series anuales → 0 (no aplica). Semestre y trimestre se derivan del mes."),
    ("periodicidad", "dim_tiempo.periodicidad / nivel_detalle", "Anual → nivel Anio; Mensual → nivel Mes."),
    ("fecha", "(no se carga)", "Redundante con anio y mes; la clave AAAAMM la reemplaza."),
    ("nivel_geografico", "dim_geografia.nivel_geografico", "Sin cambios: Global, Regional o Nacional."),
    ("entidad", "dim_geografia.entidad / pais", "pais = entidad solo en el nivel Nacional; en agregados, «No aplica»."),
    ("iso_code", "dim_geografia.iso_code / region",
     "Vacio en agregados → «No aplica». Para paises se cruza con dim_pais_region.csv para obtener la region."),
    ("(derivada)", "dim_geografia.region_es / es_foco", "Nombre de la region en espanol; es_foco = 1 para Colombia."),
    ("indicador", "dim_indicador.indicador", "Nombre homologado en la Etapa 3, sin cambios."),
    ("unidad", "dim_indicador.unidad", "Unidad homologada, una por indicador."),
    ("(derivada)", "dim_indicador.categoria / tipo_medida / agregacion",
     "Catalogo de scripts/multidimensional.py: tema del indicador y si se suma o se promedia."),
    ("fuente", "dim_fuente.fuente", "Sin cambios."),
    ("fuente_tipo", "dim_fuente.fuente_tipo", "Sin cambios: Primaria o Terciaria."),
    ("(derivada)", "dim_fuente.proveedor", "Institucion que publica, extraida del nombre de la fuente."),
    ("valor", "hechos_observacion.valor", "Numero real; medida principal."),
    ("valor_z", "hechos_observacion.valor_z", "Se conserva; NULL si el indicador no tuvo dispersion."),
    ("atipico", "hechos_observacion.atipico", "Booleano → 0/1 para poder sumarlo."),
    ("(derivada)", "hechos_observacion.n_registros", "Siempre 1: permite contar hechos con SUM."),
]


def huella(ruta):
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def huella_df(df):
    return hashlib.md5(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()


def _miembros_desconocidos(dt, dg, di, dfu):
    dt = pd.concat([pd.DataFrame([{"id_tiempo": DESCONOCIDO, "anio": 0, "semestre": 0, "trimestre": 0, "mes": 0,
                                   "nombre_mes": "Desconocido", "periodicidad": "Desconocida",
                                   "nivel_detalle": "Desconocido"}]), dt], ignore_index=True)
    dg = pd.concat([pd.DataFrame([{"id_geo": DESCONOCIDO, "nivel_geografico": "Desconocido", "region": "Desconocida",
                                   "region_es": "Desconocida", "pais": "Desconocido", "entidad": "Desconocida",
                                   "iso_code": NO_APLICA, "es_foco": 0}]), dg], ignore_index=True)
    di = pd.concat([pd.DataFrame([{"id_indicador": DESCONOCIDO, "categoria": "Desconocida",
                                   "indicador": "Desconocido", "unidad": NO_APLICA, "tipo_medida": "Desconocido",
                                   "agregacion": "promedio"}]), di], ignore_index=True)
    dfu = pd.concat([pd.DataFrame([{"id_fuente": DESCONOCIDO, "fuente_tipo": "Desconocido",
                                    "proveedor": "Desconocido", "fuente": "Desconocida"}]), dfu], ignore_index=True)
    return dt, dg, di, dfu


def transformar(df):
    """Devuelve las cinco tablas listas para cargar (con miembros -1)."""
    hechos, dt, dg, di, dfu = md.construir_estrella(df)

    dt = dt[["id_tiempo", "anio", "semestre", "trimestre", "mes", "nombre_mes", "periodicidad", "nivel_detalle"]].copy()
    dg = dg[["id_geo", "nivel_geografico", "region", "region_es", "pais", "entidad", "iso_code", "es_foco"]].copy()
    dg["iso_code"] = dg["iso_code"].fillna(NO_APLICA).replace("", NO_APLICA)
    dg["pais"] = dg["pais"].replace("", NO_APLICA).fillna(NO_APLICA)
    dg["es_foco"] = dg["es_foco"].astype(int)
    di = di[["id_indicador", "categoria", "indicador", "unidad", "tipo_medida", "agregacion"]].copy()
    dfu = dfu[["id_fuente", "fuente_tipo", "proveedor", "fuente"]].copy()
    dt, dg, di, dfu = _miembros_desconocidos(dt, dg, di, dfu)

    h = hechos.copy()
    claves = ["id_tiempo", "id_geo", "id_indicador", "id_fuente"]
    validas = {"id_tiempo": set(dt["id_tiempo"]), "id_geo": set(dg["id_geo"]),
               "id_indicador": set(di["id_indicador"]), "id_fuente": set(dfu["id_fuente"])}
    for k in claves:
        h[k] = pd.to_numeric(h[k], errors="coerce")
        h.loc[~h[k].isin(validas[k]), k] = DESCONOCIDO
        h[k] = h[k].fillna(DESCONOCIDO).astype(int)
    h["atipico"] = h["atipico"].astype(bool).astype(int)
    h["valor_z"] = h["valor_z"].astype(float)
    h["n_registros"] = 1
    h = h.reset_index(drop=True)
    h.insert(0, "id_hecho", np.arange(1, len(h) + 1))
    return h, dt, dg, di, dfu


def _insertar(con, tabla, df):
    cols = list(df.columns)
    filas = [tuple(None if (isinstance(v, float) and np.isnan(v)) else (v.item() if hasattr(v, "item") else v)
                   for v in fila) for fila in df.itertuples(index=False, name=None)]
    con.executemany("INSERT INTO {} ({}) VALUES ({})".format(tabla, ", ".join(cols), ", ".join("?" * len(cols))), filas)


def cargar(df, ruta_db=RUTA_DB, origen=RUTA_ORIGEN, huella_origen=None):
    """Transforma df (datos tratados) y lo carga en SQLite. Devuelve un resumen."""
    t0 = time.time()
    os.makedirs(os.path.dirname(ruta_db), exist_ok=True)
    h, dt, dg, di, dfu = transformar(df)
    con = sqlite3.connect(ruta_db)
    try:
        con.executescript(DDL)
        with con:
            _insertar(con, "dim_tiempo", dt)
            _insertar(con, "dim_geografia", dg)
            _insertar(con, "dim_indicador", di)
            _insertar(con, "dim_fuente", dfu)
            _insertar(con, "hechos_observacion", h)
            desconocidas = int((h[["id_tiempo", "id_geo", "id_indicador", "id_fuente"]] == DESCONOCIDO).any(axis=1).sum())
            con.execute(
                "INSERT INTO etl_carga_modelo (fecha, origen, huella_md5, filas_origen, filas_hechos, "
                "hechos_fk_desconocida, duracion_seg) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(timespec="seconds"), os.path.relpath(origen, BASE_DIR) if origen else "memoria",
                 huella_origen or huella_df(df), int(len(df)), int(len(h)), desconocidas, round(time.time() - t0, 2)))
    finally:
        con.close()
    return {"filas_origen": int(len(df)), "filas_hechos": int(len(h)), "duracion": round(time.time() - t0, 2)}


def ultima_carga(ruta_db=RUTA_DB):
    if not os.path.isfile(ruta_db):
        return None
    con = sqlite3.connect(ruta_db)
    try:
        fila = con.execute("SELECT fecha, origen, huella_md5, filas_origen, filas_hechos, hechos_fk_desconocida, "
                           "duracion_seg FROM etl_carga_modelo ORDER BY id_carga DESC LIMIT 1").fetchone()
        n = con.execute("SELECT COUNT(*) FROM etl_carga_modelo").fetchone()[0]
    except sqlite3.Error:
        return None
    finally:
        con.close()
    if not fila:
        return None
    claves = ["fecha", "origen", "huella_md5", "filas_origen", "filas_hechos", "hechos_fk_desconocida", "duracion_seg"]
    r = dict(zip(claves, fila))
    r["n_cargas"] = n
    return r


def asegurar_modelo(df_respaldo=None, ruta_db=RUTA_DB):
    """Carga el modelo si no existe o si el origen cambio. Devuelve la ruta del almacen."""
    if os.path.isfile(RUTA_ORIGEN):
        h = huella(RUTA_ORIGEN)
        u = ultima_carga(ruta_db)
        if u is None or u["huella_md5"] != h:
            cargar(pd.read_csv(RUTA_ORIGEN), ruta_db, RUTA_ORIGEN, h)
    elif df_respaldo is not None:
        u = ultima_carga(ruta_db)
        h = huella_df(df_respaldo)
        if u is None or u["huella_md5"] != h:
            cargar(df_respaldo, ruta_db, None, h)
    return ruta_db


def leer_estrella(ruta_db=RUTA_DB):
    """Lee las cinco tablas desde el almacen (lo que consulta Flask)."""
    con = sqlite3.connect(ruta_db)
    try:
        h = pd.read_sql_query("SELECT * FROM hechos_observacion", con)
        dt = pd.read_sql_query("SELECT * FROM dim_tiempo", con)
        dg = pd.read_sql_query("SELECT * FROM dim_geografia", con)
        di = pd.read_sql_query("SELECT * FROM dim_indicador", con)
        dfu = pd.read_sql_query("SELECT * FROM dim_fuente", con)
    finally:
        con.close()
    return h, dt, dg, di, dfu


if __name__ == "__main__":
    datos = pd.read_csv(RUTA_ORIGEN)
    r = cargar(datos, RUTA_DB, RUTA_ORIGEN, huella(RUTA_ORIGEN))
    print("Almacen:", os.path.relpath(RUTA_DB, BASE_DIR))
    print("Filas origen: {filas_origen} · hechos cargados: {filas_hechos} · {duracion} s".format(**r))
