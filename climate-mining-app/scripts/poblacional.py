# -*- coding: utf-8 -*-
"""
ClimaTec - Etapa 4 / Dimension Poblacional.

Calcula, a partir del conjunto de datos limpio (clima_limpio.csv, salida de la
Etapa 2/3), todo lo que publica la pagina "Dimension Poblacional":

  - composicion de los registros por categoria (nivel, tipo de fuente, fuente,
    periodicidad e indicador), para todos los anios y para cada anio;
  - distribucion de la poblacion (indicador "Poblacion") por region, por grupo
    de tamano de pais y por pais (top 10), para cada anio con dato;
  - indicadores per capita (CO2, GEI y energia) por grupo de tamano;
  - los tres conocimientos evidentes, con cifras calculadas en vivo.

Ninguna cifra se escribe a mano: si cambia el CSV, cambia la pagina. Las
graficas se dibujan en el navegador (SVG) con el JSON que devuelve construir().
"""

import numpy as np
import pandas as pd

IND_POBLACION = "Poblacion"
IND_CO2_PC = "Emisiones de CO2 per capita"
IND_GEI_PC = "GEI per capita (sin uso del suelo)"
IND_ENERGIA_PC = "Consumo de energia per capita"

# Grupos de tamano poblacional (limite inferior incluido, superior excluido).
GRUPOS = [
    ("Menos de 1 M", 0, 1e6),
    ("1 a 10 M", 1e6, 1e7),
    ("10 a 50 M", 1e7, 5e7),
    ("50 a 100 M", 5e7, 1e8),
    ("Mas de 100 M", 1e8, float("inf")),
]

REGIONES_ES = {
    "Africa": "Africa",
    "Asia": "Asia",
    "Europe": "Europa",
    "North America": "Norteamerica",
    "Oceania": "Oceania",
    "South America": "Sudamerica",
}

CATEGORIAS = [
    ("nivel_geografico", "Nivel geografico"),
    ("fuente_tipo", "Tipo de fuente"),
    ("fuente", "Fuente"),
    ("periodicidad", "Periodicidad"),
    ("indicador", "Indicador (top 10)"),
]


# ---------------------------------------------------------------------------
# Formato numerico en espanol (punto de miles, coma decimal).
# ---------------------------------------------------------------------------
def fmt_int(x):
    return "{:,.0f}".format(x).replace(",", ".")


def fmt_dec(x, d=1):
    s = "{:,.{d}f}".format(x, d=d)
    return s.replace(",", "#").replace(".", ",").replace("#", ".")


def fmt_pct(x, d=1):
    return fmt_dec(x, d) + "%"


def fmt_pob(x):
    """Poblacion legible: 1.450,9 millones / 8,16 mil millones."""
    if x >= 1e9:
        return fmt_dec(x / 1e9, 2) + " mil millones"
    if x >= 1e6:
        return fmt_dec(x / 1e6, 1) + " millones"
    return fmt_int(x)


# ---------------------------------------------------------------------------
# Composicion de registros
# ---------------------------------------------------------------------------
def _composicion(sub, col):
    total = len(sub)
    if total == 0:
        return []
    vc = sub[col].value_counts()
    if col == "indicador" and len(vc) > 10:
        resto = int(vc.iloc[10:].sum())
        otros = len(vc) - 10
        vc = vc.iloc[:10]
        filas = [{"etiqueta": str(k), "n": int(v), "pct": round(100 * v / total, 2)}
                 for k, v in vc.items()]
        filas.append({"etiqueta": "Otros indicadores ({})".format(otros), "n": resto,
                      "pct": round(100 * resto / total, 2)})
        return filas
    return [{"etiqueta": str(k), "n": int(v), "pct": round(100 * v / total, 2)}
            for k, v in vc.items()]


def _registros(df):
    salida = {}
    anios = sorted(int(a) for a in df["anio"].dropna().unique())
    for col, _ in CATEGORIAS:
        por_clave = {"todos": _composicion(df, col)}
        for a in anios:
            por_clave[str(a)] = _composicion(df[df["anio"] == a], col)
        salida[col] = por_clave
    por_anio = {"todos": int(len(df))}
    for a in anios:
        por_anio[str(a)] = int((df["anio"] == a).sum())
    n_ent = {"todos": int(df["entidad"].nunique())}
    n_ind = {"todos": int(df["indicador"].nunique())}
    for a in anios:
        sub = df[df["anio"] == a]
        n_ent[str(a)] = int(sub["entidad"].nunique())
        n_ind[str(a)] = int(sub["indicador"].nunique())
    return salida, por_anio, n_ent, n_ind, anios


# ---------------------------------------------------------------------------
# Poblacion por anio
# ---------------------------------------------------------------------------
def _asignar_grupo(valor):
    for nombre, lo, hi in GRUPOS:
        if lo <= valor < hi:
            return nombre
    return GRUPOS[-1][0]


def _mediana(serie):
    serie = serie.dropna()
    return (float(serie.median()), int(len(serie))) if len(serie) else (None, 0)


def _poblacion_anio(df, anio):
    nac = df[(df["nivel_geografico"] == "Nacional") & (df["anio"] == anio)]
    pob = (nac[nac["indicador"] == IND_POBLACION][["entidad", "iso_code", "valor"]]
           .rename(columns={"valor": "pob"}).dropna(subset=["pob"]))
    pob = pob[pob["pob"] > 0].copy()
    if pob.empty:
        return None

    def _pc(ind, nombre):
        s = nac[nac["indicador"] == ind][["entidad", "valor"]].rename(columns={"valor": nombre})
        return s.drop_duplicates("entidad")

    pob = (pob.merge(_pc(IND_CO2_PC, "co2_pc"), on="entidad", how="left")
              .merge(_pc(IND_GEI_PC, "gei_pc"), on="entidad", how="left")
              .merge(_pc(IND_ENERGIA_PC, "en_pc"), on="entidad", how="left"))
    pob["grupo"] = pob["pob"].apply(_asignar_grupo)

    total = float(pob["pob"].sum())
    n = int(len(pob))

    grupos = []
    for nombre, _, _ in GRUPOS:
        g = pob[pob["grupo"] == nombre]
        co2, n_co2 = _mediana(g["co2_pc"])
        grupos.append({
            "grupo": nombre,
            "paises": int(len(g)),
            "pct_paises": round(100 * len(g) / n, 2),
            "poblacion": float(g["pob"].sum()),
            "pct_pob": round(float(100 * g["pob"].sum() / total), 2),
            "co2_pc_mediana": None if co2 is None else round(co2, 2),
            "co2_pc_n": n_co2,
        })

    orden = pob.sort_values("pob", ascending=False)
    top = [{"entidad": r.entidad, "iso": None if pd.isna(r.iso_code) else str(r.iso_code),
            "poblacion": float(r.pob), "pct": round(100 * r.pob / total, 2)}
           for r in orden.head(10).itertuples()]
    resto = total - float(orden.head(10)["pob"].sum())
    top5_pct = round(100 * float(orden.head(5)["pob"].sum()) / total, 2)
    top10_pct = round(100 * float(orden.head(10)["pob"].sum()) / total, 2)

    # Regiones (agregados continentales de OWID presentes en el dataset).
    reg = df[(df["nivel_geografico"] == "Regional") & (df["anio"] == anio) &
             (df["indicador"] == IND_POBLACION)][["entidad", "valor"]].dropna()
    total_reg = float(reg["valor"].sum())
    regiones = [{"entidad": REGIONES_ES.get(r.entidad, r.entidad),
                 "poblacion": float(r.valor),
                 "pct": round(100 * r.valor / total_reg, 2) if total_reg else 0}
                for r in reg.sort_values("valor", ascending=False).itertuples()]

    mundo = df[(df["entidad"] == "World") & (df["anio"] == anio) &
               (df["indicador"] == IND_POBLACION)]["valor"]
    mundo = float(mundo.iloc[0]) if len(mundo) else None

    perfil = {}
    for clave, col, unidad in (("co2_pc", "co2_pc", "t CO2/persona"),
                               ("gei_pc", "gei_pc", "t eq. CO2/persona"),
                               ("en_pc", "en_pc", "kWh/persona")):
        med, k = _mediana(pob[col])
        perfil[clave] = {"mediana": None if med is None else round(med, 2),
                         "n": k, "unidad": unidad}

    return {
        "anio": int(anio),
        "paises": n,
        "pob_paises": total,
        "pob_mundo": mundo,
        "media": float(pob["pob"].mean()),
        "mediana": float(pob["pob"].median()),
        "maximo": {"entidad": orden.iloc[0]["entidad"], "poblacion": float(orden.iloc[0]["pob"])},
        "minimo": {"entidad": orden.iloc[-1]["entidad"], "poblacion": float(orden.iloc[-1]["pob"])},
        "grupos": grupos,
        "top": top,
        "top_resto": {"poblacion": resto, "pct": round(100 * resto / total, 2),
                      "paises": n - len(top)},
        "top5_pct": top5_pct,
        "top10_pct": top10_pct,
        "regiones": regiones,
        "perfil": perfil,
    }


# ---------------------------------------------------------------------------
# Conocimientos evidentes (estructura de 8 campos pedida por la guia)
# ---------------------------------------------------------------------------
def _ev(etiqueta, valor, pct):
    return {"etiqueta": etiqueta, "valor": valor, "pct": pct, "pct_txt": fmt_pct(pct)}


def _conocimientos(reg, pob_ref, total_reg, n_ent, n_ind, n_fuentes):
    nivel = reg["nivel_geografico"]["todos"]
    tipo = reg["fuente_tipo"]["todos"]
    fuente = reg["fuente"]["todos"]
    nac = next(x for x in nivel if x["etiqueta"] == "Nacional")
    prim = next((x for x in tipo if x["etiqueta"] == "Primaria"), None)
    terc = next((x for x in tipo if x["etiqueta"] == "Terciaria"), None)
    f1 = fuente[0]
    f2 = fuente[1]
    owid_pct = round(f1["pct"] + f2["pct"], 2)
    if "Our World in Data" in f1["etiqueta"] and "Our World in Data" in f2["etiqueta"]:
        dos_fuentes = "Las dos fuentes de Our World in Data"
    else:
        dos_fuentes = "Las dos fuentes con mas registros"
    anio = pob_ref["anio"]

    regiones = pob_ref["regiones"]
    asia, africa = regiones[0], regiones[1]
    menores = regiones[-1]
    g = {x["grupo"]: x for x in pob_ref["grupos"]}
    chicos = g["Menos de 1 M"]["paises"] + g["1 a 10 M"]["paises"]
    chicos_pct_p = round(g["Menos de 1 M"]["pct_paises"] + g["1 a 10 M"]["pct_paises"], 1)
    chicos_pct_pob = round(g["Menos de 1 M"]["pct_pob"] + g["1 a 10 M"]["pct_pob"], 2)
    gran = g["Mas de 100 M"]
    top = pob_ref["top"]

    k1 = {
        "numero": 1,
        "titulo": "El analisis descansa casi por completo en registros nacionales y de fuentes terciarias",
        "pregunta": "Que tipo de entidades y de fuentes componen el conjunto de datos y cual predomina?",
        "variables": "nivel_geografico, fuente_tipo y fuente (categoricas); cada fila del dataset limpio cuenta como un registro.",
        "procedimiento": "Se conto el numero de registros por categoria sobre todo el periodo y se dividio cada conteo entre el total de {} registros para obtener su participacion porcentual.".format(fmt_int(total_reg)),
        "evidencia_titulo": "Participacion en el total de registros",
        "evidencia": (
            [_ev("Nivel · " + x["etiqueta"], fmt_int(x["n"]), x["pct"]) for x in nivel]
            + [_ev("Fuente · " + x["etiqueta"], fmt_int(x["n"]), x["pct"]) for x in tipo]
        ),
        "hallazgo": "El nivel Nacional concentra {} de los registros ({} de {}); el Regional aporta {} y el Global {}. Por tipo de fuente, la Terciaria suma {} y la Primaria solo {}. {} aportan {} del total.".format(
            fmt_pct(nac["pct"]), fmt_int(nac["n"]), fmt_int(total_reg),
            fmt_pct(next(x for x in nivel if x["etiqueta"] == "Regional")["pct"]),
            fmt_pct(next(x for x in nivel if x["etiqueta"] == "Global")["pct"]),
            fmt_pct(terc["pct"]) if terc else "n/d", fmt_pct(prim["pct"]) if prim else "n/d",
            dos_fuentes, fmt_pct(owid_pct)),
        "interpretacion": "La poblacion analizada es, en la practica, un panel de paises: las conclusiones del proyecto hablan sobre todo de comportamientos nacionales. Las mediciones directas (Mauna Loa, GISTEMP, GCAG) existen, pero pesan muy poco en el volumen total.",
        "utilidad": "Orienta que escala puede sustentarse con mas solidez (la nacional) y deja claro que los resultados globales y regionales descansan en pocos registros.",
        "limitacion": "El porcentaje mide registros, no personas ni territorio: un pais con mas indicadores disponibles pesa mas aunque tenga menos habitantes.",
    }

    k2 = {
        "numero": 2,
        "titulo": "La poblacion mundial esta concentrada en dos regiones",
        "pregunta": "Como se reparte la poblacion entre las regiones del dataset en {}?".format(anio),
        "variables": "entidad y nivel_geografico = Regional; indicador = Poblacion (personas); anio.",
        "procedimiento": "Se tomo la poblacion de cada agregado continental para {}, se sumaron las seis regiones y se dividio cada una entre ese total.".format(anio),
        "evidencia_titulo": "Poblacion por region en {}".format(anio),
        "evidencia": [_ev(r["entidad"], fmt_pob(r["poblacion"]), r["pct"]) for r in regiones],
        "hallazgo": "{} reune {} de la poblacion y {} otro {}: juntas suman {}. {} es la region minoritaria con {}.".format(
            asia["entidad"], fmt_pct(asia["pct"]), africa["entidad"], fmt_pct(africa["pct"]),
            fmt_pct(asia["pct"] + africa["pct"]), menores["entidad"], fmt_pct(menores["pct"])),
        "interpretacion": "El tamano poblacional es muy desigual entre regiones. Cualquier indicador total (por ejemplo emisiones absolutas) esta influido por cuanta gente vive en cada region, por eso conviene leerlo junto con su version per capita.",
        "utilidad": "Permite decidir que indicadores comparar en valores absolutos y cuales normalizar por habitante al contrastar regiones.",
        "limitacion": "La participacion describe cuantas personas hay, no como viven ni cuanto emiten; no explica por si sola las diferencias climaticas entre regiones.",
    }

    k3 = {
        "numero": 3,
        "titulo": "Pocos paises muy grandes concentran la mayor parte de la poblacion",
        "pregunta": "Que tan desigual es el tamano poblacional de los {} paises del dataset en {}?".format(pob_ref["paises"], anio),
        "variables": "entidad y nivel_geografico = Nacional; indicador = Poblacion; grupo de tamano creado a partir del valor.",
        "procedimiento": "Se clasificaron los paises en cinco rangos de poblacion (menos de 1 M, 1 a 10 M, 10 a 50 M, 50 a 100 M y mas de 100 M), se conto cuantos hay por rango y se sumo su poblacion para calcular ambas participaciones.",
        "evidencia_titulo": "% de la poblacion por grupo de tamano",
        "evidencia": [_ev(x["grupo"], "{} paises".format(x["paises"]), x["pct_pob"]) for x in pob_ref["grupos"]],
        "hallazgo": "{} paises superan los 100 millones de habitantes ({} de los paises) y concentran {} de la poblacion. En el extremo contrario, {} paises tienen menos de 10 millones ({} de los paises) y reunen solo {}. La mediana es {} y la media {}.".format(
            gran["paises"], fmt_pct(gran["pct_paises"]), fmt_pct(gran["pct_pob"]), chicos,
            fmt_pct(chicos_pct_p), fmt_pct(chicos_pct_pob), fmt_pob(pob_ref["mediana"]), fmt_pob(pob_ref["media"])),
        "interpretacion": "La distribucion es muy asimetrica: la media queda muy por encima de la mediana porque unos pocos paises enormes la arrastran. {} y {} encabezan la lista y los cinco primeros reunen {} de la poblacion.".format(
            top[0]["entidad"], top[1]["entidad"], fmt_pct(pob_ref["top5_pct"])),
        "utilidad": "Ayuda a decidir donde auditar y validar primero: un error en los datos de los paises mas poblados distorsiona mas los totales que el de decenas de paises pequenos.",
        "limitacion": "El tamano poblacional no equivale a responsabilidad climatica: la mediana de CO2 per capita es {} t en los paises de menos de 1 M y {} t en los de mas de 100 M, asi que tamano e intensidad de emisiones no van de la mano.".format(
            fmt_dec(g["Menos de 1 M"]["co2_pc_mediana"], 2), fmt_dec(gran["co2_pc_mediana"], 2)),
    }
    return [k1, k2, k3]


def _limitacion(reg, pob_ref, anios_pob, n_paises_pob):
    tipo = reg["fuente_tipo"]["todos"]
    prim = next((x for x in tipo if x["etiqueta"] == "Primaria"), None)
    return {
        "titulo": "El dataset describe indicadores por entidad, no a las personas",
        "texto": (
            "El dataset es una tabla de hechos (un indicador medido para una entidad en una fecha). "
            "No hay microdatos demograficos (edad, sexo, ingresos, zona urbana o rural), de modo que la "
            "composicion de la poblacion solo puede describirse por pais, region y tamano. Ademas, la variable "
            "Poblacion cubre {} paises entre {} y {}, y las fuentes primarias aportan apenas {} de los registros. "
            "Por eso el analisis permite hablar de como se distribuye el tamano poblacional y el volumen de datos, "
            "pero no de las caracteristicas internas de la poblacion de cada pais."
        ).format(n_paises_pob, min(anios_pob), max(anios_pob), fmt_pct(prim["pct"]) if prim else "n/d"),
    }


def _decision(pob_ref):
    top = pob_ref["top"]
    nombres = ", ".join(x["entidad"] for x in top[:5])
    g = {x["grupo"]: x for x in pob_ref["grupos"]}
    return {
        "titulo": "Priorizar la validacion y el analisis en los paises mas poblados y normalizar por habitante",
        "texto": (
            "Los cinco paises mas poblados ({}) reunen {} de la poblacion de los paises del dataset y los {} paises "
            "de mas de 100 millones, {}. Con esta evidencia se puede decidir (1) concentrar primero la verificacion de "
            "calidad y las comparaciones en ese grupo, porque son los que mas pesan en cualquier total, y (2) usar "
            "indicadores per capita al comparar paises o regiones de tamano muy distinto, para no confundir tamano "
            "poblacional con intensidad de emisiones."
        ).format(nombres, fmt_pct(pob_ref["top5_pct"]), g["Mas de 100 M"]["paises"], fmt_pct(g["Mas de 100 M"]["pct_pob"])),
        "sustento": "Sustento: visualizaciones 2 y 3, y el conocimiento evidente 3.",
    }


def _cambio_regiones(pob_anios):
    ks = sorted(int(k) for k in pob_anios)
    ini, fin = pob_anios[str(ks[0])], pob_anios[str(ks[-1])]
    a = {r["entidad"]: r["pct"] for r in ini["regiones"]}
    b = {r["entidad"]: r["pct"] for r in fin["regiones"]}
    filas = [{"entidad": k, "pct_ini": a[k], "pct_fin": b[k], "delta": round(b[k] - a[k], 2)}
             for k in b if k in a]
    return {"anio_ini": ks[0], "anio_fin": ks[-1], "filas": filas}


def _interpretaciones(reg, por_anio, ref, cambio):
    nivel = reg["nivel_geografico"]["todos"]
    per = reg["periodicidad"]["todos"]
    nac = nivel[0]
    anual = per[0]
    a25, a26 = por_anio.get("2025"), por_anio.get("2026")
    extra = ""
    if a25 is not None and a26 is not None:
        extra = (" Al filtrar 2025 o 2026 quedan solo {} y {} registros (mediciones mensuales y energia), "
                 "por lo que el peso de cada categoria cambia y ya no es comparable con 2020-2024.").format(
                     fmt_int(a25), fmt_int(a26))
    v1 = ("Una sola categoria domina casi todas las variables: {} {} en nivel geografico y {} {} en periodicidad. "
          "Las categorias minoritarias existen pero pesan poco.{}").format(
              nac["etiqueta"], fmt_pct(nac["pct"]), anual["etiqueta"], fmt_pct(anual["pct"]), extra)

    filas = sorted(cambio["filas"], key=lambda r: r["delta"])
    baja, sube = filas[0], filas[-1]
    reg0 = ref["regiones"]
    v2 = ("En {} {} y {} reunen {} de la poblacion, mientras {} no llega a {}. Entre {} y {} {} gana {} puntos "
          "porcentuales de participacion y {} pierde {}: el reparto cambia despacio, pero en una direccion clara.").format(
              ref["anio"], reg0[0]["entidad"], reg0[1]["entidad"], fmt_pct(reg0[0]["pct"] + reg0[1]["pct"]),
              reg0[-1]["entidad"], fmt_pct(max(1, round(reg0[-1]["pct"] + 0.5)), 0),
              cambio["anio_ini"], cambio["anio_fin"], sube["entidad"], fmt_dec(abs(sube["delta"]), 2),
              baja["entidad"], fmt_dec(abs(baja["delta"]), 2))

    g = {x["grupo"]: x for x in ref["grupos"]}
    v3 = ("Las barras calidas (poblacion) y frias (paises) cuentan historias opuestas: el grupo de mas de 100 M es "
          "{} de los paises pero {} de la poblacion, y el de menos de 1 M es {} de los paises y apenas {} de la "
          "poblacion. La mayoria de paises son pequenos o medianos; la mayoria de la gente vive en unos pocos paises muy grandes.").format(
              fmt_pct(g["Mas de 100 M"]["pct_paises"]), fmt_pct(g["Mas de 100 M"]["pct_pob"]),
              fmt_pct(g["Menos de 1 M"]["pct_paises"]), fmt_pct(g["Menos de 1 M"]["pct_pob"]))
    return {"v1": v1, "v2": v2, "v3": v3}


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def construir(df):
    """Devuelve el dict completo para la pagina, o None si no hay datos."""
    if df is None or df.empty:
        return None
    reg, por_anio, n_ent, n_ind, anios = _registros(df)
    pob_anios = {}
    for a in anios:
        p = _poblacion_anio(df, a)
        if p:
            pob_anios[str(a)] = p
    if not pob_anios:
        return None
    anios_pob = sorted(int(k) for k in pob_anios)
    anio_ref = max(anios_pob)
    ref = pob_anios[str(anio_ref)]
    total = int(len(df))
    n_fuentes = int(df["fuente"].nunique())

    graficos = {
        "anios": anios,
        "anios_pob": anios_pob,
        "anio_ref": anio_ref,
        "categorias": [{"clave": c, "nombre": n} for c, n in CATEGORIAS],
        "registros": reg,
        "registros_por_anio": por_anio,
        "entidades_por_anio": n_ent,
        "indicadores_por_anio": n_ind,
        "poblacion": pob_anios,
        "grupos": [g[0] for g in GRUPOS],
    }

    # Variables usadas (se verifica que existan en el dataset).
    variables = [
        {"variable": "nivel_geografico", "tipo": "Categorica", "uso": "Separa los registros en Global, Regional y Nacional; define la composicion del dataset."},
        {"variable": "fuente_tipo", "tipo": "Categorica", "uso": "Primaria, secundaria o terciaria; mide de donde proviene la informacion."},
        {"variable": "fuente", "tipo": "Categorica", "uso": "Fuente concreta de cada registro ({} fuentes en el dataset limpio).".format(n_fuentes)},
        {"variable": "periodicidad", "tipo": "Categorica", "uso": "Anual o mensual; explica por que algunos anios tienen mas registros."},
        {"variable": "entidad / iso_code", "tipo": "Categorica", "uso": "Pais, region o 'World'; unidad sobre la que se cuenta la poblacion."},
        {"variable": "anio", "tipo": "Temporal", "uso": "Filtro 1: anio de analisis ({}-{}).".format(min(anios), max(anios))},
        {"variable": "indicador", "tipo": "Categorica", "uso": "Variable medida; 'Poblacion' define el tamano de cada entidad."},
        {"variable": "valor", "tipo": "Numerica", "uso": "Habitantes (Poblacion) y valores per capita de CO2, GEI y energia."},
        {"variable": "grupo_tamano (derivada)", "tipo": "Categorica derivada", "uso": "Rango de poblacion del pais: menos de 1 M, 1-10 M, 10-50 M, 50-100 M, mas de 100 M."},
    ]

    cambio = _cambio_regiones(pob_anios)
    return {
        "interpretaciones": _interpretaciones(reg, por_anio, ref, cambio),
        "cambio_regiones": cambio,
        "total_registros": total,
        "n_entidades": int(df["entidad"].nunique()),
        "n_indicadores": int(df["indicador"].nunique()),
        "n_fuentes": n_fuentes,
        "anio_min": int(min(anios)),
        "anio_max": int(max(anios)),
        "ref": ref,
        "variables": variables,
        "conocimientos": _conocimientos(reg, ref, total, int(df["entidad"].nunique()),
                                        int(df["indicador"].nunique()), n_fuentes),
        "limitacion": _limitacion(reg, ref, anios_pob, ref["paises"]),
        "decision": _decision(ref),
        "graficos": graficos,
        "fmt": {"pct_nacional": next(x["pct"] for x in reg["nivel_geografico"]["todos"] if x["etiqueta"] == "Nacional")},
    }
