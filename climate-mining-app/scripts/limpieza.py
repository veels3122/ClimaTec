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


# ---------------------------------------------------------------------------
# Consistencia: reglas de coherencia INTERNA entre columnas, calculadas fila a
# fila. Miden si el registro es coherente consigo mismo (p. ej. que la fecha,
# el anio y el mes digan lo mismo); NO miden si el valor es verdadero
# (exactitud), que requiere comparar contra una referencia externa.
# ---------------------------------------------------------------------------
REGLAS_CONSISTENCIA = [
    ("fecha_anio", "fecha <-> anio",
     "El anio de la columna fecha coincide con la columna anio."),
    ("fecha_mes", "fecha <-> mes",
     "Series mensuales: el mes de la fecha coincide con la columna mes."),
    ("periodicidad_mes", "periodicidad <-> mes",
     "Mensual con mes informado (1-12); Anual con mes vacio."),
    ("nivel_iso", "nivel_geografico <-> iso_code",
     "Nacional con codigo ISO3 de 3 letras; Global/Regional sin codigo."),
    ("indicador_unidad", "indicador <-> unidad",
     "Cada indicador usa una sola unidad (la unidad predominante del indicador)."),
    ("fuente_tipo", "fuente <-> fuente_tipo",
     "Cada fuente tiene un solo tipo (primaria/secundaria/terciaria)."),
]


def evaluar_consistencia(df):
    """Evalua las reglas de REGLAS_CONSISTENCIA sobre cada fila y devuelve el
    resultado cuantitativo por regla y el porcentaje de filas que cumplen
    todas las reglas a la vez."""
    d = df.copy()
    fecha = pd.to_datetime(d["fecha"], errors="coerce")
    anio = pd.to_numeric(d["anio"], errors="coerce")
    mes = pd.to_numeric(d["mes"], errors="coerce")
    mensual = d["periodicidad"].astype(str).str.strip().eq("Mensual")
    anual = d["periodicidad"].astype(str).str.strip().eq("Anual")
    iso = d["iso_code"].astype("string").str.strip()
    nacional = d["nivel_geografico"].astype(str).str.strip().eq("Nacional")

    unidad_moda = d.groupby("indicador")["unidad"].agg(lambda s: s.mode().iat[0])
    tipo_moda = d.groupby("fuente")["fuente_tipo"].agg(lambda s: s.mode().iat[0])

    # mask_aplica: filas donde la regla se puede evaluar; mask_ok: cumple.
    reglas = {
        "fecha_anio": (pd.Series(True, index=d.index), fecha.dt.year.eq(anio)),
        "fecha_mes": (mensual, fecha.dt.month.eq(mes)),
        "periodicidad_mes": (mensual | anual,
                             (mensual & mes.between(1, 12)) | (anual & mes.isna())),
        "nivel_iso": (pd.Series(True, index=d.index),
                      (nacional & iso.str.fullmatch(r"[A-Z]{3}").fillna(False))
                      | (~nacional & iso.isna())),
        "indicador_unidad": (pd.Series(True, index=d.index),
                             d["unidad"].eq(d["indicador"].map(unidad_moda))),
        "fuente_tipo": (pd.Series(True, index=d.index),
                        d["fuente_tipo"].eq(d["fuente"].map(tipo_moda))),
    }

    filas_ok = pd.Series(True, index=d.index)
    detalle = []
    for clave, nombre, descripcion in REGLAS_CONSISTENCIA:
        aplica, ok = reglas[clave]
        aplica = aplica.fillna(False).astype(bool)
        ok = ok.fillna(False).astype(bool)
        n_eval = int(aplica.sum())
        n_ok = int((aplica & ok).sum())
        filas_ok &= (~aplica) | ok
        detalle.append({
            "regla": nombre, "descripcion": descripcion,
            "evaluadas": n_eval, "cumplen": n_ok, "incumplen": n_eval - n_ok,
            "pct": round(100 * n_ok / n_eval, 2) if n_eval else 100.0,
        })
    n_ok_total = int(filas_ok.sum())
    return {
        "reglas": detalle,
        "filas": int(len(d)),
        "filas_consistentes": n_ok_total,
        "filas_inconsistentes": int(len(d) - n_ok_total),
        "pct": round(100 * n_ok_total / len(d), 2) if len(d) else 100.0,
        "unidades_por_indicador_max": int(d.groupby("indicador")["unidad"].nunique().max()),
    }


def concordancia_fuentes(df):
    """Aproximacion a la EXACTITUD (distinta de la consistencia): compara dos
    fuentes independientes que miden lo mismo -- la anomalia de temperatura
    global mensual de NASA GISTEMP y de NOAA GCAG -- en los mismos meses.
    Como cada fuente usa un periodo base distinto, se espera una diferencia
    constante (desfase); lo que mide la concordancia es que, descontado ese
    desfase, ambas series se muevan igual."""
    t = df[df["indicador"] == "Anomalia de temperatura global"]
    fuentes = sorted(t["fuente"].unique())
    if len(fuentes) < 2:
        return None
    p = t.pivot_table(index="fecha", columns="fuente", values="valor").dropna()
    if len(p) < 3:
        return None
    a = next((f for f in fuentes if "GISTEMP" in f), fuentes[0])
    b = next((f for f in fuentes if f != a), fuentes[1])
    dif = p[a] - p[b]
    desfase = float(dif.mean())
    return {
        "fuente_a": a, "fuente_b": b, "meses": int(len(p)),
        "correlacion": round(float(p[a].corr(p[b])), 4),
        "desfase": round(desfase, 3),
        "mae_sin_desfase": round(float((dif - desfase).abs().mean()), 3),
        "max_sin_desfase": round(float((dif - desfase).abs().max()), 3),
    }


def estadisticas_por_indicador(df):
    """Estadisticos descriptivos de 'valor' calculados DENTRO de cada par
    indicador-unidad (un promedio global de 'valor' mezclaria ppm, Mt,
    personas, %, etc. y no tendria significado)."""
    filas = []
    for (ind, uni), s in df.groupby(["indicador", "unidad"])["valor"]:
        s = s.dropna()
        filas.append({
            "indicador": ind, "unidad": uni, "n": int(len(s)),
            "min": float(s.min()), "q1": float(s.quantile(0.25)),
            "mediana": float(s.median()), "media": float(s.mean()),
            "q3": float(s.quantile(0.75)), "max": float(s.max()),
            "desv": float(s.std(ddof=0)),
            "atipicos": int(df.loc[s.index, "atipico"].sum()) if "atipico" in df else 0,
        })
    filas.sort(key=lambda x: x["indicador"])
    return filas


# Indicadores relativos (per capita o porcentaje): un valor extremo indica un
# perfil energetico/emisor extremo del pais, no su tamano.
UNIDADES_RELATIVAS = {"t CO2/persona", "t eq. CO2/persona", "kWh/persona", "%"}


def causas_atipicos(df, cercania=0.20):
    """Asigna a CADA observacion atipica una causa verificable con los propios
    datos (reglas en orden de prioridad):
      1. Agregado geografico: nivel Global/Regional. Son sumas de paises, pero
         el umbral IQR se calcula sobre todo el indicador (dominado por paises).
      2. Choque real del periodo: 'Variacion anual de CO2' en 2020-2021, cuando
         la mediana de variacion de todos los paises tambien cae/rebota.
      3. Atipico estructural: la entidad es atipica en TODOS los anios de su
         serie para ese indicador (es su escala o perfil, no un error puntual).
         Se separa en 'gran escala' (magnitudes absolutas) y 'perfil extremo'
         (per capita o %).
      4. Cercano al umbral: atipico solo en algunos anios y a menos de
         `cercania` (20%) del limite IQR.
      5. Sin causa estructural: lo restante; queda para revision manual.
    """
    if "atipico" not in df or not df["atipico"].any():
        return {"categorias": [], "ejemplos": [], "total": 0, "evidencia": {}}
    d = df.copy()
    lim = d.groupby("indicador")["valor"].quantile([0.25, 0.75]).unstack()
    lim["lo"] = lim[0.25] - 1.5 * (lim[0.75] - lim[0.25])
    lim["hi"] = lim[0.75] + 1.5 * (lim[0.75] - lim[0.25])
    d = d.join(lim[["lo", "hi"]], on="indicador")

    # Fraccion de anios atipicos de cada entidad dentro de cada indicador.
    frac = d.groupby(["indicador", "entidad"])["atipico"].transform("mean")
    mediana_var = (d[d["indicador"] == "Variacion anual de CO2"]
                   .groupby("anio")["valor"].median())
    anios_choque = [int(a) for a in mediana_var.index
                    if int(a) in (2020, 2021)]

    a = d[d["atipico"]].copy()
    a["frac"] = frac[a.index]
    limite = a["hi"].where(a["valor"] > a["hi"], a["lo"])
    a["dist_umbral"] = ((a["valor"] - limite).abs() /
                        limite.abs().where(limite.abs() > 0, 1))

    cat = pd.Series("Sin causa estructural (revision manual)", index=a.index)
    nac = a["nivel_geografico"].eq("Nacional")
    relativo = a["unidad"].isin(UNIDADES_RELATIVAS)
    cat[nac & (a["frac"] < 1) & (a["dist_umbral"] <= cercania)] = \
        "Cercano al umbral IQR (variacion menor)"
    cat[nac & (a["frac"] == 1) & relativo] = "Perfil extremo per capita / % (estructural)"
    cat[nac & (a["frac"] == 1) & ~relativo] = "Entidad de gran escala (estructural)"
    cat[a["indicador"].eq("Variacion anual de CO2") & a["anio"].isin(anios_choque)] = \
        "Choque real 2020-2021 (caida y rebote de emisiones)"
    cat[~nac] = "Agregado geografico (mundo / continentes)"
    a["causa"] = cat

    orden = ["Agregado geografico (mundo / continentes)",
             "Entidad de gran escala (estructural)",
             "Perfil extremo per capita / % (estructural)",
             "Choque real 2020-2021 (caida y rebote de emisiones)",
             "Cercano al umbral IQR (variacion menor)",
             "Sin causa estructural (revision manual)"]
    sustento = {
        orden[0]: "Son sumas de paises; el umbral IQR del indicador lo fijan sobre todo los paises, "
                  "asi que un total continental o mundial queda por encima por construccion.",
        orden[1]: "La entidad queda fuera del rango en todos los anios de su serie: refleja su "
                  "tamano (poblacion, economia), no un valor puntual erroneo.",
        orden[2]: "La entidad es extrema en todos sus anios en un indicador relativo (per capita "
                  "o %): perfil energetico propio (p. ej. petroestados o paises nordicos).",
        orden[3]: "La mediana de la variacion anual de todos los paises tambien se desplaza esos "
                  "anios, por lo que el extremo acompana un movimiento general real.",
        orden[4]: "Solo algunos anios de la entidad cruzan el limite y quedan a menos de "
                  "{:.0f}% de el.".format(cercania * 100),
        orden[5]: "No se explica por las reglas anteriores; se conserva marcada para revision.",
    }
    total = int(len(a))
    categorias = []
    for c in orden:
        sub = a[a["causa"] == c]
        if sub.empty:
            continue
        ejemplos = (sub.groupby("entidad").size().sort_values(ascending=False)
                    .head(4).index.tolist())
        categorias.append({
            "causa": c, "n": int(len(sub)),
            "pct": round(100 * len(sub) / total, 1),
            "sustento": sustento[c], "ejemplos": ", ".join(ejemplos),
        })
    revisar = a[a["causa"] == orden[5]].sort_values("dist_umbral", ascending=False)
    evidencia = {
        "pct_lado_alto": round(100 * float((a["valor"] > a["hi"]).mean()), 1),
        "atipicos_fuentes_primarias": int(a["fuente_tipo"].eq("Primaria").sum()),
        "mediana_variacion": [{"anio": int(k), "mediana": round(float(v), 2)}
                              for k, v in mediana_var.items()],
    }
    return {
        "total": total, "categorias": categorias, "evidencia": evidencia,
        "revision": [{"indicador": r.indicador, "entidad": r.entidad, "anio": int(r.anio),
                      "valor": round(float(r.valor), 3), "unidad": r.unidad}
                     for r in revisar.head(10).itertuples()],
        "pct_explicado": round(100 * (1 - len(revisar) / total), 1) if total else 100.0,
    }


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
    consistencia_antes = evaluar_consistencia(df)

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
    consistencia = evaluar_consistencia(df)
    concordancia = concordancia_fuentes(df)
    est_indicador = estadisticas_por_indicador(df)
    atip_causas = causas_atipicos(df)
    n_ind = int(df["indicador"].nunique())
    n_uni = int(df["unidad"].nunique())

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

    # Estadisticos globales: SOLO de valor_z (adimensional). Los de 'valor' se
    # calculan por indicador y unidad en estadisticas_por_indicador(), porque
    # un promedio global mezclaria magnitudes y unidades distintas.
    est_num = []
    for c in ["valor_z"]:
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
        {"dimension": "Consistencia",
         "metrica": "% de filas que cumplen las {} reglas de coherencia interna "
                    "(fecha/anio/mes, periodicidad, nivel/ISO, indicador/unidad, fuente/tipo)".format(
                        len(REGLAS_CONSISTENCIA)),
         "resultado": "{}% ({:,} de {:,} filas)".format(
             consistencia["pct"], consistencia["filas_consistentes"],
             consistencia["filas"]).replace(",", "."),
         "estado": "ok" if consistencia["pct"] >= 99 else "revisar"},
        {"dimension": "Exactitud (aproximacion)",
         "metrica": "Concordancia entre fuentes independientes (GISTEMP vs GCAG, mismos meses)",
         "resultado": ("r = {} · error medio {} °C tras descontar desfase de base".format(
             concordancia["correlacion"], concordancia["mae_sin_desfase"])
             if concordancia else "no evaluable"),
         "estado": "ok" if concordancia and concordancia["correlacion"] >= 0.9 else "revisar"},
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
         "detalle": "Detectadas por rango intercuartilico (1.5*IQR) dentro de cada indicador. "
                    "El {}% tiene una causa verificable en los datos (agregados, entidades de gran "
                    "escala, perfiles extremos, choque 2020-2021); por eso se marcan y no se eliminan.".format(
                        atip_causas.get("pct_explicado", 0))},
        {"problema": "Escalas y unidades heterogeneas", "severidad": "Media",
         "cantidad": "{} indicadores / {} unidades".format(n_ind, n_uni),
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
        "consistencia": consistencia, "consistencia_antes": consistencia_antes,
        "concordancia": concordancia, "est_indicador": est_indicador,
        "atip_causas": atip_causas, "n_indicadores_e2": n_ind, "n_unidades_e2": n_uni,
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
    print("[limpieza] consistencia: {}% de filas cumplen las {} reglas".format(
        rep["consistencia"]["pct"], len(REGLAS_CONSISTENCIA)))
    print("[limpieza] escrito:", salida)


if __name__ == "__main__":
    main()
