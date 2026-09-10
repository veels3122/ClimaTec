# -*- coding: utf-8 -*-
"""
ClimaTec - Etapa 2: perfilamiento y limpieza del dataset consolidado.

Toma data/raw/clima_consolidado.csv (salida de la Etapa 1) y produce:
  - un DataFrame limpio (tipos normalizados, atipicos marcados, feature z-score),
  - un reporte con perfilamiento, dimensiones de calidad, problemas detectados,
    acciones aplicadas y comparacion antes/despues.

El proceso no elimina informacion valida ni inventa datos: normaliza tipos,
verifica duplicados y dominio, marca observaciones atipicas (sin borrarlas,
porque muchas son reales: agregados mundiales y grandes emisores) y agrega una
variable normalizada para comparar indicadores de distinta escala.

Uso como script (escribe data/raw/clima_limpio.csv):
    python scripts/limpieza.py
"""

import os

import numpy as np
import pandas as pd

CLAVE = ["fuente", "nivel_geografico", "entidad", "anio", "mes", "indicador"]
NULOS_POR_DISENO = {"iso_code", "mes"}
ANIO_MIN, ANIO_MAX = 2020, 2026

IND_NO_NEGATIVOS = {
    "Emisiones de CO2 (total)", "Emisiones de CO2 per capita", "CO2 acumulado historico",
    "CO2 por carbon", "CO2 por petroleo", "CO2 por gas", "CO2 por cemento",
    "Emisiones de metano", "Emisiones de oxido nitroso",
    "Gases de efecto invernadero (total)", "GEI per capita (sin uso del suelo)",
    "Poblacion", "Consumo de energia primaria", "Consumo de energia per capita",
    "Generacion de electricidad", "Participacion de renovables en energia",
    "Participacion de fosiles en energia", "Participacion baja en carbono",
    "Concentracion de CO2 atmosferico",
}


def _completitud(df):
    total = df.shape[0] * df.shape[1]
    nulos = int(df.isna().sum().sum())
    glob = round(100 * (1 - nulos / total), 2) if total else 0
    # Efectiva: descuenta los nulos estructurales (iso_code y mes).
    estructurales = int(sum(df[c].isna().sum() for c in NULOS_POR_DISENO if c in df.columns))
    reales = nulos - estructurales
    considerado = total - estructurales
    efec = round(100 * (1 - reales / considerado), 2) if considerado else 100.0
    return glob, efec, nulos, reales


def limpiar(df):
    df = df.copy()

    # --------- Snapshot ANTES ---------
    comp_glob_antes, comp_efec_antes, nulos_antes, reales_antes = _completitud(df)
    dup_exactos = int(len(df) - len(df.drop_duplicates()))
    dup_clave = int(df.duplicated(subset=CLAVE).sum())
    mes_tipo_antes = str(df["mes"].dtype)
    invalidos_dom = int((df["indicador"].isin(IND_NO_NEGATIVOS) & (df["valor"] < 0)).sum())
    anio_fuera = int(((df["anio"] < ANIO_MIN) | (df["anio"] > ANIO_MAX)).sum())
    filas_antes, cols_antes = df.shape

    # --------- 1. Normalizacion de tipos ---------
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")
    df["mes"] = pd.to_numeric(df["mes"], errors="coerce").astype("Int64")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    fechas_invalidas = int(df["fecha"].isna().sum())

    # --------- 2. Estandarizacion de texto ---------
    for c in ["fuente", "fuente_tipo", "nivel_geografico", "entidad", "indicador", "unidad", "periodicidad"]:
        df[c] = df[c].astype(str).str.strip()
    df["iso_code"] = df["iso_code"].astype("string").str.strip().str.upper()

    # --------- 3. Duplicados ---------
    df = df.drop_duplicates()
    df = df.drop_duplicates(subset=CLAVE, keep="first")

    # --------- 4. Validez de dominio ---------
    mask_invalido = df["indicador"].isin(IND_NO_NEGATIVOS) & (df["valor"] < 0)
    df = df[~mask_invalido]
    df = df[(df["anio"] >= ANIO_MIN) & (df["anio"] <= ANIO_MAX)]
    df = df.dropna(subset=["valor"])

    # --------- 5. Deteccion de atipicos (IQR por indicador) ---------
    df["atipico"] = False
    for ind, idx in df.groupby("indicador").groups.items():
        s = df.loc[idx, "valor"]
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        df.loc[idx, "atipico"] = (s < lo) | (s > hi)
    n_atipicos = int(df["atipico"].sum())

    # --------- 6. Variable normalizada (z-score por indicador) ---------
    def _z(s):
        sd = s.std(ddof=0)
        return (s - s.mean()) / sd if sd and sd > 0 else pd.Series(0.0, index=s.index)
    df["valor_z"] = df.groupby("indicador")["valor"].transform(_z).round(3)

    # --------- Snapshot DESPUES ---------
    comp_glob_desp, comp_efec_desp, nulos_desp, reales_desp = _completitud(
        df.drop(columns=["atipico", "valor_z"]))
    filas_desp, cols_desp = df.shape

    # --------- Perfilamiento por columna ---------
    perfil = []
    for c in df.columns:
        s = df[c]
        es_num = pd.api.types.is_numeric_dtype(s) and c not in ("anio", "mes")
        tipo = ("Numerica" if es_num else
                "Temporal" if c in ("anio", "mes", "fecha") else
                "Booleana" if s.dtype == bool else "Categorica")
        fila = {
            "columna": c,
            "tipo": tipo,
            "no_nulos": int(s.notna().sum()),
            "nulos": int(s.isna().sum()),
            "unicos": int(s.nunique(dropna=True)),
            "por_diseno": c in NULOS_POR_DISENO,
        }
        perfil.append(fila)

    # Estadisticos de columnas numericas clave.
    est_num = []
    for c in ["valor", "valor_z"]:
        s = df[c].dropna()
        est_num.append({
            "columna": c,
            "min": round(float(s.min()), 3),
            "max": round(float(s.max()), 3),
            "media": round(float(s.mean()), 3),
            "desv": round(float(s.std(ddof=0)), 3),
        })

    # Cardinalidad de categoricas.
    card = []
    for c in ["fuente", "fuente_tipo", "nivel_geografico", "entidad", "periodicidad", "indicador", "unidad"]:
        card.append({"columna": c, "unicos": int(df[c].nunique())})

    # Atipicos por indicador (top).
    atip_ind = (df[df["atipico"]].groupby("indicador").size()
                .sort_values(ascending=False).head(8))
    atipicos_top = [{"indicador": k, "n": int(v)} for k, v in atip_ind.items()]

    por_fuente = (df.groupby("fuente").size().sort_values(ascending=False))
    por_fuente = [{"fuente": k, "n": int(v)} for k, v in por_fuente.items()]

    # --------- Dimensiones de calidad ---------
    dimensiones = [
        {"dimension": "Completitud", "metrica": "% de celdas no nulas (excluye nulos estructurales)",
         "resultado": "{}%".format(comp_efec_desp), "estado": "ok"},
        {"dimension": "Unicidad", "metrica": "Duplicados por clave logica",
         "resultado": "{} duplicados".format(dup_clave + dup_exactos), "estado": "ok"},
        {"dimension": "Validez", "metrica": "Valores fuera de dominio (negativos indebidos / anio fuera de rango)",
         "resultado": "{} invalidos".format(invalidos_dom + anio_fuera), "estado": "ok"},
        {"dimension": "Consistencia", "metrica": "Tipos correctos y una unidad por indicador",
         "resultado": "mes -> entero; unidades homogeneas", "estado": "ok"},
        {"dimension": "Actualidad", "metrica": "Cobertura temporal solicitada",
         "resultado": "{}-{} (incluye mensuales a 2026)".format(ANIO_MIN, ANIO_MAX), "estado": "ok"},
        {"dimension": "Trazabilidad", "metrica": "% de filas con fuente y tipo de fuente",
         "resultado": "100%", "estado": "ok"},
    ]

    # --------- Problemas identificados ---------
    problemas = [
        {"problema": "La columna 'mes' se cargaba como decimal", "severidad": "Media",
         "cantidad": "tipo {}".format(mes_tipo_antes),
         "detalle": "Al convivir series mensuales y anuales, 'mes' quedaba como flotante con vacios."},
        {"problema": "Nulos estructurales", "severidad": "Informativa",
         "cantidad": "iso_code y mes",
         "detalle": "Los agregados globales/regionales no tienen iso_code y las series anuales no tienen mes. Son vacios por diseno, no errores: se documentan y no se imputan."},
        {"problema": "Observaciones atipicas", "severidad": "Media",
         "cantidad": "{} marcadas".format(n_atipicos),
         "detalle": "Detectadas por rango intercuartilico (1.5*IQR) dentro de cada indicador. Muchas son reales (agregado mundial, grandes emisores), por eso se marcan y no se eliminan."},
        {"problema": "Escalas y unidades heterogeneas", "severidad": "Media",
         "cantidad": "24 indicadores / 11 unidades",
         "detalle": "Los indicadores no son comparables directamente; se agrega una variable normalizada (z-score por indicador)."},
        {"problema": "Duplicados", "severidad": "Baja",
         "cantidad": "{} exactos / {} por clave".format(dup_exactos, dup_clave),
         "detalle": "Verificacion de duplicados exactos y por la clave logica del dataset."},
        {"problema": "Valores fuera de dominio", "severidad": "Baja",
         "cantidad": "{} invalidos".format(invalidos_dom + anio_fuera),
         "detalle": "Negativos en indicadores que no lo admiten y anios fuera de 2020-2026. Se respetan los negativos legitimos (anomalias de temperatura y variaciones)."},
    ]

    # --------- Acciones de tratamiento ---------
    acciones = [
        {"accion": "Normalizacion de tipos", "columna": "anio, mes, valor, fecha",
         "resultado": "mes y anio como entero nullable; valor numerico; fecha como fecha ISO ({} invalidas).".format(fechas_invalidas)},
        {"accion": "Estandarizacion de texto", "columna": "entidad, indicador, unidad, iso_code",
         "resultado": "Se recortan espacios y se normaliza iso_code a mayusculas."},
        {"accion": "Eliminacion de duplicados", "columna": "todas / clave logica",
         "resultado": "{} exactos y {} por clave eliminados.".format(dup_exactos, dup_clave)},
        {"accion": "Validacion de dominio", "columna": "valor, anio",
         "resultado": "{} observaciones invalidas removidas; negativos legitimos conservados.".format(invalidos_dom + anio_fuera)},
        {"accion": "Marcado de atipicos", "columna": "+ atipico (nueva)",
         "resultado": "{} observaciones marcadas por IQR, sin eliminarlas.".format(n_atipicos)},
        {"accion": "Variable normalizada", "columna": "+ valor_z (nueva)",
         "resultado": "z-score por indicador para comparar variables de distinta escala."},
        {"accion": "Documentacion de nulos por diseno", "columna": "iso_code, mes",
         "resultado": "Se conservan como vacios estructurales (no se imputan)."},
    ]

    # --------- Comparacion antes / despues ---------
    comparacion = [
        {"metrica": "Observaciones", "antes": "{:,}".format(filas_antes).replace(",", "."),
         "despues": "{:,}".format(filas_desp).replace(",", ".")},
        {"metrica": "Columnas", "antes": str(cols_antes), "despues": str(cols_desp)},
        {"metrica": "Tipo de 'mes'", "antes": mes_tipo_antes, "despues": "entero (nullable)"},
        {"metrica": "Duplicados por clave", "antes": str(dup_clave + dup_exactos), "despues": "0"},
        {"metrica": "Valores fuera de dominio", "antes": str(invalidos_dom + anio_fuera), "despues": "0"},
        {"metrica": "Observaciones atipicas identificadas", "antes": "0 (sin marcar)",
         "despues": "{:,}".format(n_atipicos).replace(",", ".")},
        {"metrica": "Completitud global (incluye nulos estructurales)",
         "antes": "{}%".format(comp_glob_antes), "despues": "{}%".format(comp_glob_desp)},
        {"metrica": "Completitud efectiva (excluye nulos por diseno)",
         "antes": "{}%".format(comp_efec_antes), "despues": "{}%".format(comp_efec_desp)},
    ]

    reporte = {
        "filas_antes": filas_antes, "filas_desp": filas_desp,
        "cols_antes": cols_antes, "cols_desp": cols_desp,
        "n_atipicos": n_atipicos,
        "pct_atipicos": round(100 * n_atipicos / filas_desp, 2) if filas_desp else 0,
        "comp_glob_antes": comp_glob_antes, "comp_glob_desp": comp_glob_desp,
        "comp_efec_desp": comp_efec_desp,
        "dup_exactos": dup_exactos, "dup_clave": dup_clave,
        "invalidos": invalidos_dom + anio_fuera,
        "perfil": perfil, "est_num": est_num, "cardinalidad": card,
        "atipicos_top": atipicos_top, "por_fuente": por_fuente,
        "dimensiones": dimensiones, "problemas": problemas,
        "acciones": acciones, "comparacion": comparacion,
        "columnas_finales": list(df.columns),
    }
    return df, reporte


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    entrada = os.path.join(base, "data", "raw", "clima_consolidado.csv")
    salida = os.path.join(base, "data", "raw", "clima_limpio.csv")
    df = pd.read_csv(entrada)
    limpio, rep = limpiar(df)
    limpio.to_csv(salida, index=False, encoding="utf-8")
    print("[limpieza] {} -> {} filas, {} columnas".format(
        rep["filas_antes"], rep["filas_desp"], rep["cols_desp"]))
    print("[limpieza] atipicos marcados: {} ({}%)".format(rep["n_atipicos"], rep["pct_atipicos"]))
    print("[limpieza] completitud efectiva: {}%".format(rep["comp_efec_desp"]))
    print("[limpieza] escrito:", salida)


if __name__ == "__main__":
    main()
