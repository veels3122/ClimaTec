# -*- coding: utf-8 -*-
"""
ClimaTec - Etapa 6 / Conocimiento oculto.

Prepara, a partir del conjunto limpio de las Etapas 2/3 (data/raw/clima_limpio.csv),
los dos archivos que se cargan en Orange Data Mining:

  data/etapa6/supervisado_paises.csv  -> clasificacion del nivel de emisiones de
                                          CO2 per capita (Bajo / Medio / Alto).
  data/etapa6/clustering_paises.csv   -> perfiles de paises SIN la variable objetivo
                                          (va como meta solo para describir grupos).

Unidad de analisis: UN PAIS (promedio 2020-2024). Se agrega por pais para que el
mismo pais no aparezca en entrenamiento y prueba con anios distintos (eso inflaria
las metricas: el modelo "reconoceria" el pais en vez de aprender el patron).

Encabezado con prefijos de Orange (una sola fila):
  cD#  -> variable objetivo discreta   C#  -> numerica   D# -> categorica
  m#   -> meta (no participa en el modelo)

Ejecucion:  python scripts/conocimiento_oculto.py
"""

import json
import os

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE_DIR, "data", "raw")
OUT = os.path.join(BASE_DIR, "data", "etapa6")

ANIO_INI, ANIO_FIN = 2020, 2024          # 2025-2026 casi no tienen datos por pais
UMBRAL_BAJO, UMBRAL_ALTO = 2.0, 6.0      # t CO2 por persona

REGIONES_ES = {"Africa": "Africa", "Asia": "Asia", "Europe": "Europa",
               "North America": "Norteamerica", "Oceania": "Oceania",
               "South America": "Sudamerica"}


def construir_tabla_paises():
    d = pd.read_csv(os.path.join(RAW, "clima_limpio.csv"))
    n = d[(d.nivel_geografico == "Nacional") & d.anio.between(ANIO_INI, ANIO_FIN)]
    p = n.pivot_table(index=["iso_code", "entidad"], columns="indicador",
                      values="valor", aggfunc="mean").reset_index()

    reg = pd.read_csv(os.path.join(RAW, "dim_pais_region.csv"))[["iso_code", "region"]]
    p = p.merge(reg, on="iso_code", how="left")
    p["region"] = p["region"].map(REGIONES_ES)

    pob = p["Poblacion"]
    t = pd.DataFrame({
        "pais": p["entidad"],
        "iso3": p["iso_code"],
        "region": p["region"],
        "log_poblacion": np.log10(pob),
        "energia_pc_kwh": p["Consumo de energia per capita"],
        "electricidad_pc_kwh": p["Generacion de electricidad"] * 1e9 / pob,
        "intensidad_red_tco2e_mwh": p["Emisiones GEI del sector electrico"] / p["Generacion de electricidad"],
        "metano_pc_tco2e": p["Emisiones de metano"] * 1e6 / pob,
        "oxido_nitroso_pc_tco2e": p["Emisiones de oxido nitroso"] * 1e6 / pob,
        "variacion_co2_pct": p["Variacion anual de CO2"],
        "co2_pc_t": p["Emisiones de CO2 per capita"],
    })
    t = t.replace([np.inf, -np.inf], np.nan)
    return t


def preparar():
    os.makedirs(OUT, exist_ok=True)
    t = construir_tabla_paises()
    total_inicial = len(t)
    traza = {"paises_iniciales": total_inicial}

    # 1) sin objetivo no se puede entrenar ni evaluar
    t = t[t.co2_pc_t.notna()]
    traza["sin_objetivo"] = total_inicial - len(t)
    # 2) sin poblacion no hay per capita -> se excluye
    antes = len(t)
    t = t[t.log_poblacion.notna() & t.region.notna()]
    traza["sin_poblacion_o_region"] = antes - len(t)
    # 3) se exige al menos 4 de los 6 predictores numericos (el resto lo imputa Orange)
    pred = ["energia_pc_kwh", "electricidad_pc_kwh", "intensidad_red_tco2e_mwh",
            "metano_pc_tco2e", "oxido_nitroso_pc_tco2e", "log_poblacion"]
    antes = len(t)
    t = t[t[pred].notna().sum(axis=1) >= 4]
    traza["predictores_insuficientes"] = antes - len(t)
    traza["faltantes_por_predictor"] = {c: int(t[c].isna().sum()) for c in pred}

    t["nivel_co2_pc"] = pd.cut(t.co2_pc_t, [-np.inf, UMBRAL_BAJO, UMBRAL_ALTO, np.inf],
                               labels=["Bajo", "Medio", "Alto"], right=False).astype(str)
    traza["paises_finales"] = len(t)
    traza["clases"] = t.nivel_co2_pc.value_counts().to_dict()
    t = t.round(4)

    # ---- archivo supervisado (encabezado con prefijos Orange) ----
    sup = t[["pais", "iso3", "region"] + pred[:-1] + ["log_poblacion", "co2_pc_t", "nivel_co2_pc"]].copy()
    sup.columns = ["m#pais", "m#iso3", "D#region", "C#energia_pc_kwh", "C#electricidad_pc_kwh",
                   "C#intensidad_red_tco2e_mwh", "C#metano_pc_tco2e", "C#oxido_nitroso_pc_tco2e",
                   "C#log_poblacion", "m#co2_pc_t", "cD#nivel_co2_pc"]
    sup.to_csv(os.path.join(OUT, "supervisado_paises.csv"), index=False, encoding="utf-8")

    # ---- archivo clustering: sin objetivo; co2 solo como meta descriptiva ----
    # Las variables per capita son muy asimetricas (unos pocos petro-estados e
    # islas pequenas concentran los valores extremos). Sin transformacion, k-Means
    # separa solo a esos atipicos (k=2 -> 20 vs 173 paises). Se usa log10 para
    # energia, electricidad, metano y N2O; la intensidad de la red ya esta acotada
    # (0-1,3 t/MWh) y se deja igual. Orange estandariza despues (Normalize columns).
    clu = t.dropna(subset=["energia_pc_kwh", "electricidad_pc_kwh", "intensidad_red_tco2e_mwh",
                           "metano_pc_tco2e", "oxido_nitroso_pc_tco2e"]).copy()
    for c in ["energia_pc_kwh", "electricidad_pc_kwh", "metano_pc_tco2e", "oxido_nitroso_pc_tco2e"]:
        clu["log_" + c] = np.log10(clu[c].clip(lower=1e-3)).round(4)
    clu = clu[["pais", "iso3", "region",
               "log_energia_pc_kwh", "log_electricidad_pc_kwh", "intensidad_red_tco2e_mwh",
               "log_metano_pc_tco2e", "log_oxido_nitroso_pc_tco2e",
               "energia_pc_kwh", "electricidad_pc_kwh", "metano_pc_tco2e", "oxido_nitroso_pc_tco2e",
               "variacion_co2_pct", "co2_pc_t", "nivel_co2_pc"]]
    traza["paises_clustering"] = len(clu)
    clu.columns = ["m#pais", "m#iso3", "m#region",
                   "C#log_energia_pc", "C#log_electricidad_pc", "C#intensidad_red_tco2e_mwh",
                   "C#log_metano_pc", "C#log_oxido_nitroso_pc",
                   "m#energia_pc_kwh", "m#electricidad_pc_kwh", "m#metano_pc_tco2e",
                   "m#oxido_nitroso_pc_tco2e", "m#variacion_co2_pct", "m#co2_pc_t", "m#nivel_co2_pc"]
    clu.to_csv(os.path.join(OUT, "clustering_paises.csv"), index=False, encoding="utf-8")

    with open(os.path.join(OUT, "traza_preparacion.json"), "w", encoding="utf-8") as f:
        json.dump(traza, f, ensure_ascii=False, indent=2)
    return traza


if __name__ == "__main__":
    print(json.dumps(preparar(), ensure_ascii=False, indent=2))
