# -*- coding: utf-8 -*-
"""
ClimaTec - Etapa 5 / Analisis multidimensional.

Construye, a partir del conjunto de datos limpio (clima_limpio.csv, salida de las
Etapas 2/3), un MODELO ESTRELLA en memoria y todo lo que publican las paginas de
la Etapa 5:

  - cuatro dimensiones (Tiempo, Geografia, Indicador, Fuente) y una tabla de
    hechos con la granularidad "un indicador, para una entidad, en una fecha,
    desde una fuente";
  - las jerarquias de cada dimension (Anio > Semestre > Trimestre > Mes;
    Mundo > Region > Pais; Categoria > Indicador; Tipo de fuente > Proveedor >
    Fuente) y las medidas del cubo con su regla de agregacion;
  - los datos (JSON) de las cuatro vistas interactivas, sobre los que el
    navegador aplica slice, dice, roll-up, drill-down y pivot;
  - los conocimientos descubiertos con el cubo, con cifras calculadas en vivo.

La region de cada pais sale de data/raw/dim_pais_region.csv (ISO3 -> continente).
Ninguna cifra se escribe a mano: si cambia el CSV, cambia la pagina.
"""

import os

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_REGIONES = os.path.join(BASE_DIR, "data", "raw", "dim_pais_region.csv")

PAIS_FOCO = "Colombia"
REGION_FOCO = "South America"

REGIONES_ES = {
    "Africa": "Africa",
    "Asia": "Asia",
    "Europe": "Europa",
    "North America": "Norteamerica",
    "Oceania": "Oceania",
    "South America": "Sudamerica",
    "Antarctica": "Antartida",
}
ORDEN_REGIONES = ["Asia", "North America", "Europe", "Africa", "South America", "Oceania"]

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

# ---------------------------------------------------------------------------
# Dimension Indicador: categoria (nivel superior de la jerarquia), tipo de
# medida y regla de agregacion. "suma" = aditivo entre territorios (flujos y
# poblaciones absolutas); "promedio" = no aditivo (per capita, %, anomalias, ppm).
# ---------------------------------------------------------------------------
CATALOGO_INDICADORES = {
    "Emisiones de CO2 (total)": ("Emisiones de CO2", "Absoluto", "suma"),
    "CO2 por carbon": ("Emisiones de CO2", "Absoluto", "suma"),
    "CO2 por petroleo": ("Emisiones de CO2", "Absoluto", "suma"),
    "CO2 por gas": ("Emisiones de CO2", "Absoluto", "suma"),
    "CO2 por cemento": ("Emisiones de CO2", "Absoluto", "suma"),
    "CO2 acumulado historico": ("Emisiones de CO2", "Absoluto (acumulado)", "suma"),
    "Emisiones de CO2 per capita": ("Emisiones de CO2", "Per capita", "promedio"),
    "Variacion anual de CO2": ("Emisiones de CO2", "Porcentaje", "promedio"),
    "Emisiones de metano": ("Otros gases de efecto invernadero", "Absoluto", "suma"),
    "Emisiones de oxido nitroso": ("Otros gases de efecto invernadero", "Absoluto", "suma"),
    "Gases de efecto invernadero (total)": ("Otros gases de efecto invernadero", "Absoluto", "suma"),
    "GEI per capita (sin uso del suelo)": ("Otros gases de efecto invernadero", "Per capita", "promedio"),
    "Emisiones GEI del sector electrico": ("Otros gases de efecto invernadero", "Absoluto", "suma"),
    "Consumo de energia primaria": ("Energia", "Absoluto", "suma"),
    "Consumo de energia per capita": ("Energia", "Per capita", "promedio"),
    "Generacion de electricidad": ("Energia", "Absoluto", "suma"),
    "Participacion de renovables en energia": ("Energia", "Porcentaje", "promedio"),
    "Participacion de fosiles en energia": ("Energia", "Porcentaje", "promedio"),
    "Participacion baja en carbono": ("Energia", "Porcentaje", "promedio"),
    "Anomalia de temperatura global": ("Clima y atmosfera", "Anomalia", "promedio"),
    "Concentracion de CO2 atmosferico": ("Clima y atmosfera", "Concentracion", "promedio"),
    "Contribucion del CO2 a la temperatura": ("Clima y atmosfera", "Absoluto", "suma"),
    "Contribucion de GEI a la temperatura": ("Clima y atmosfera", "Absoluto", "suma"),
    "Poblacion": ("Demografia", "Absoluto", "suma"),
}
ORDEN_CATEGORIAS = ["Emisiones de CO2", "Otros gases de efecto invernadero", "Energia",
                    "Clima y atmosfera", "Demografia"]

# Indicadores que se ofrecen en el drill-down territorial (aditivos entre paises).
IND_TERRITORIALES = [
    "Emisiones de CO2 (total)", "Gases de efecto invernadero (total)", "Emisiones de metano",
    "Emisiones de oxido nitroso", "Consumo de energia primaria", "Generacion de electricidad",
    "CO2 por carbon", "Poblacion",
]
IND_BASE = "Emisiones de CO2 (total)"

# Indicadores del mapa de calor (se leen los agregados de OWID tal como vienen).
IND_MAPA = [
    "Emisiones de CO2 (total)", "Emisiones de CO2 per capita", "Emisiones de metano",
    "Gases de efecto invernadero (total)", "Consumo de energia per capita",
    "Participacion de renovables en energia", "Participacion de fosiles en energia",
    "Participacion baja en carbono", "Variacion anual de CO2", "Poblacion",
]


def proveedor(fuente):
    f = str(fuente)
    if f.startswith("Our World in Data"):
        return "Our World in Data"
    if f.startswith("NOAA"):
        return "NOAA"
    if f.startswith("NASA"):
        return "NASA"
    return f.split(" - ")[0]


def nombre_fuente_corto(fuente):
    f = str(fuente)
    return f.split(" (")[0]


# ---------------------------------------------------------------------------
# Formato numerico en espanol (punto de miles, coma decimal).
# ---------------------------------------------------------------------------
def fmt_dec(x, d=1):
    s = "{:,.{d}f}".format(x, d=d)
    return s.replace(",", "#").replace(".", ",").replace("#", ".")


def fmt_int(x):
    return fmt_dec(x, 0)


def fmt_pct(x, d=1):
    return fmt_dec(x, d) + "%"


def fmt_signo(x, d=1):
    return ("+" if x > 0 else "") + fmt_pct(x, d)


def nombre_geo(entidad):
    if entidad == "World":
        return "Mundo"
    return REGIONES_ES.get(entidad, entidad)


# ---------------------------------------------------------------------------
# 1. Modelo estrella
# ---------------------------------------------------------------------------
def _regiones():
    if not os.path.isfile(RUTA_REGIONES):
        return pd.DataFrame(columns=["iso_code", "entidad", "region"])
    return pd.read_csv(RUTA_REGIONES)


def construir_estrella(df):
    """Devuelve (hechos, dim_tiempo, dim_geo, dim_ind, dim_fuente)."""
    d = df.copy()
    d["mes"] = pd.to_numeric(d["mes"], errors="coerce")
    d["anio"] = pd.to_numeric(d["anio"], errors="coerce").astype(int)
    d["valor"] = pd.to_numeric(d["valor"], errors="coerce")
    d["valor_z"] = pd.to_numeric(d.get("valor_z"), errors="coerce") if "valor_z" in d else np.nan
    if "atipico" in d:
        d["atipico"] = d["atipico"].astype(str).str.lower().isin(["true", "1", "si"])
    else:
        d["atipico"] = False

    # --- Dimension Tiempo (clave AAAAMM; MM = 00 en las series anuales) -------
    d["id_tiempo"] = d["anio"] * 100 + d["mes"].fillna(0).astype(int)
    t = d[["id_tiempo", "anio", "mes", "periodicidad"]].drop_duplicates("id_tiempo").copy()
    t["mes"] = t["mes"].fillna(0).astype(int)
    t["trimestre"] = np.where(t["mes"] > 0, (t["mes"] - 1) // 3 + 1, 0)
    t["semestre"] = np.where(t["mes"] > 0, (t["mes"] - 1) // 6 + 1, 0)
    t["nombre_mes"] = t["mes"].map(lambda m: MESES[m - 1] if m > 0 else "")
    t["nivel_detalle"] = np.where(t["mes"] > 0, "Mes", "Anio")
    dim_tiempo = t.sort_values("id_tiempo").reset_index(drop=True)

    # --- Dimension Geografia (Mundo > Region > Pais) --------------------------
    reg = _regiones()
    mapa_reg = dict(zip(reg["iso_code"], reg["region"]))
    g = d[["entidad", "iso_code", "nivel_geografico"]].drop_duplicates(["entidad", "nivel_geografico"]).copy()

    def region_de(fila):
        if fila["nivel_geografico"] == "Nacional":
            return mapa_reg.get(fila["iso_code"], "Sin region")
        if fila["nivel_geografico"] == "Regional":
            return fila["entidad"]
        return "Mundo"

    g["region"] = g.apply(region_de, axis=1)
    g["region_es"] = g["region"].map(lambda r: REGIONES_ES.get(r, r))
    g["pais"] = np.where(g["nivel_geografico"] == "Nacional", g["entidad"], "")
    g["es_foco"] = g["entidad"] == PAIS_FOCO
    g = g.sort_values(["nivel_geografico", "region", "entidad"]).reset_index(drop=True)
    g["id_geo"] = np.arange(1, len(g) + 1)
    dim_geo = g

    # --- Dimension Indicador (Categoria > Indicador) --------------------------
    i = d[["indicador", "unidad"]].drop_duplicates("indicador").copy()
    i["categoria"] = i["indicador"].map(lambda x: CATALOGO_INDICADORES.get(x, ("Otros", "", ""))[0])
    i["tipo_medida"] = i["indicador"].map(lambda x: CATALOGO_INDICADORES.get(x, ("", "Otro", ""))[1])
    i["agregacion"] = i["indicador"].map(lambda x: CATALOGO_INDICADORES.get(x, ("", "", "promedio"))[2])
    i["orden_cat"] = i["categoria"].map(lambda c: ORDEN_CATEGORIAS.index(c) if c in ORDEN_CATEGORIAS else 99)
    i = i.sort_values(["orden_cat", "indicador"]).reset_index(drop=True)
    i["id_indicador"] = np.arange(1, len(i) + 1)
    dim_ind = i.drop(columns="orden_cat")

    # --- Dimension Fuente (Tipo > Proveedor > Fuente) -------------------------
    f = d[["fuente", "fuente_tipo"]].drop_duplicates("fuente").copy()
    f["proveedor"] = f["fuente"].map(proveedor)
    f = f.sort_values(["fuente_tipo", "proveedor", "fuente"]).reset_index(drop=True)
    f["id_fuente"] = np.arange(1, len(f) + 1)
    dim_fuente = f

    # --- Tabla de hechos ------------------------------------------------------
    h = d.merge(dim_geo[["entidad", "nivel_geografico", "id_geo"]], on=["entidad", "nivel_geografico"], how="left")
    h = h.merge(dim_ind[["indicador", "id_indicador"]], on="indicador", how="left")
    h = h.merge(dim_fuente[["fuente", "id_fuente"]], on="fuente", how="left")
    hechos = h[["id_tiempo", "id_geo", "id_indicador", "id_fuente", "valor", "valor_z", "atipico"]].copy()
    return hechos, dim_tiempo, dim_geo, dim_ind, dim_fuente


# ---------------------------------------------------------------------------
# 2. Descripcion del modelo (paginas 3 y 4)
# ---------------------------------------------------------------------------
def _ejemplos(serie, n=3):
    vals = [str(v) for v in serie.dropna().unique()[:n]]
    return ", ".join(vals)


def describir_modelo(hechos, dim_tiempo, dim_geo, dim_ind, dim_fuente):
    n_paises = int((dim_geo["nivel_geografico"] == "Nacional").sum())
    n_regiones = int((dim_geo["nivel_geografico"] == "Regional").sum())
    meses = dim_tiempo[dim_tiempo["mes"] > 0]
    dims = [
        {
            "clave": "tiempo",
            "nombre": "Dimension Tiempo",
            "tabla": "dim_tiempo",
            "pk": "id_tiempo",
            "filas": int(len(dim_tiempo)),
            "pregunta": "¿Cuando se midio el dato?",
            "atributos": [
                ("id_tiempo", "Clave AAAAMM; MM = 00 en las series anuales", "202409"),
                ("anio", "Anio de la observacion", "{}–{}".format(int(dim_tiempo["anio"].min()), int(dim_tiempo["anio"].max()))),
                ("semestre", "1 o 2 (solo series mensuales)", "1, 2"),
                ("trimestre", "1 a 4 (solo series mensuales)", "1, 2, 3, 4"),
                ("mes / nombre_mes", "1 a 12 y su abreviatura", "9 · Sep"),
                ("periodicidad", "Anual o Mensual", "Anual, Mensual"),
            ],
            "jerarquia": ["Anio", "Semestre", "Trimestre", "Mes"],
            "nota": "{} miembros: {} anios completos y {} meses con dato. La jerarquia completa solo existe en las "
                    "series mensuales; las anuales se detienen en el nivel Anio.".format(
                        len(dim_tiempo), int((dim_tiempo["mes"] == 0).sum()), len(meses)),
        },
        {
            "clave": "geografia",
            "nombre": "Dimension Geografia",
            "tabla": "dim_geografia",
            "pk": "id_geo",
            "filas": int(len(dim_geo)),
            "pregunta": "¿Donde?",
            "atributos": [
                ("id_geo", "Clave sustituta", "1, 2, 3…"),
                ("nivel_geografico", "Global, Regional o Nacional", "Nacional"),
                ("region", "Continente (para paises, via ISO3)", "South America"),
                ("pais / entidad", "Pais o agregado tal como viene de la fuente", "Colombia"),
                ("iso_code", "Codigo ISO3 del pais", "COL"),
                ("es_foco", "Marca el pais foco del proyecto", "Colombia = si"),
            ],
            "jerarquia": ["Mundo", "Region", "Pais"],
            "nota": "{} paises, {} regiones y {} entidades globales. Los paises se asignan a su continente con "
                    "data/raw/dim_pais_region.csv; las regiones y el Mundo son agregados de la propia fuente.".format(
                        n_paises, n_regiones, int((dim_geo["nivel_geografico"] == "Global").sum())),
        },
        {
            "clave": "indicador",
            "nombre": "Dimension Indicador",
            "tabla": "dim_indicador",
            "pk": "id_indicador",
            "filas": int(len(dim_ind)),
            "pregunta": "¿Que se midio?",
            "atributos": [
                ("id_indicador", "Clave sustituta", "1, 2, 3…"),
                ("categoria", "Tema del indicador", "Emisiones de CO2"),
                ("indicador", "Nombre homologado (Etapa 3)", "Emisiones de CO2 (total)"),
                ("unidad", "Unidad homologada", "Mt CO2"),
                ("tipo_medida", "Absoluto, Per capita, Porcentaje…", "Absoluto"),
                ("agregacion", "Regla al subir de nivel: suma o promedio", "suma"),
            ],
            "jerarquia": ["Categoria", "Indicador"],
            "nota": "{} indicadores en {} categorias. El atributo agregacion evita sumar lo que no se puede sumar "
                    "(per capita, porcentajes, anomalias).".format(len(dim_ind), dim_ind["categoria"].nunique()),
        },
        {
            "clave": "fuente",
            "nombre": "Dimension Fuente",
            "tabla": "dim_fuente",
            "pk": "id_fuente",
            "filas": int(len(dim_fuente)),
            "pregunta": "¿Quien lo reporta?",
            "atributos": [
                ("id_fuente", "Clave sustituta", "1, 2, 3…"),
                ("fuente_tipo", "Primaria o Terciaria", "Primaria"),
                ("proveedor", "Institucion que publica", "NOAA"),
                ("fuente", "Producto de datos concreto", "NOAA GML - Mauna Loa"),
            ],
            "jerarquia": ["Tipo de fuente", "Proveedor", "Fuente"],
            "nota": "{} fuentes de {} proveedores. Permite comparar la misma medida segun quien la publica "
                    "(por ejemplo, GISTEMP frente a NOAA).".format(len(dim_fuente), dim_fuente["proveedor"].nunique()),
        },
    ]
    medidas = [
        {"nombre": "Valor", "columna": "valor", "formula": "valor observado del indicador",
         "agregacion": "SUM si agregacion = suma; AVG si agregacion = promedio",
         "aditividad": "Semiaditiva: se suma entre territorios solo en indicadores absolutos; en el tiempo se promedia"},
        {"nombre": "Numero de registros", "columna": "COUNT(*)", "formula": "cantidad de hechos en la celda",
         "agregacion": "SUM", "aditividad": "Aditiva en todas las dimensiones"},
        {"nombre": "Registros atipicos", "columna": "atipico", "formula": "SUM(atipico)",
         "agregacion": "SUM", "aditividad": "Aditiva"},
        {"nombre": "% de atipicos", "columna": "derivada", "formula": "SUM(atipico) / COUNT(*) × 100",
         "agregacion": "Se recalcula en cada celda (no se suma)", "aditividad": "No aditiva"},
        {"nombre": "Valor z promedio", "columna": "valor_z", "formula": "AVG(valor_z)",
         "agregacion": "AVG", "aditividad": "No aditiva"},
        {"nombre": "Participacion %", "columna": "derivada", "formula": "valor de la celda / total del nivel × 100",
         "agregacion": "Se recalcula en cada nivel de la jerarquia", "aditividad": "No aditiva"},
    ]
    categorias = []
    for c in ORDEN_CATEGORIAS:
        sub = dim_ind[dim_ind["categoria"] == c]
        if len(sub):
            categorias.append({
                "categoria": c,
                "indicadores": [{"nombre": r.indicador, "unidad": r.unidad, "tipo": r.tipo_medida,
                                 "agregacion": r.agregacion} for r in sub.itertuples()],
            })
    regiones = []
    for r in ORDEN_REGIONES:
        n = int(((dim_geo["region"] == r) & (dim_geo["nivel_geografico"] == "Nacional")).sum())
        regiones.append({"region": REGIONES_ES[r], "paises": n})
    fuentes = [{"tipo": r.fuente_tipo, "proveedor": r.proveedor, "fuente": r.fuente}
               for r in dim_fuente.itertuples()]
    return {
        "dimensiones": dims,
        "medidas": medidas,
        "categorias": categorias,
        "regiones": regiones,
        "fuentes": fuentes,
        "n_hechos": int(len(hechos)),
        "n_dim": 4,
    }


# ---------------------------------------------------------------------------
# 3. Datos de las cuatro vistas
# ---------------------------------------------------------------------------
def _plano(hechos, dim_tiempo, dim_geo, dim_ind, dim_fuente):
    """Une la tabla de hechos con sus dimensiones (consulta en estrella)."""
    p = hechos.merge(dim_tiempo, on="id_tiempo").merge(dim_geo, on="id_geo")
    p = p.merge(dim_ind, on="id_indicador").merge(dim_fuente, on="id_fuente")
    return p


def vista_temporal(p):
    """Vista 1: series mensuales (drill-down Anio > Semestre > Trimestre > Mes)
    y series anuales de Mundo, Sudamerica y Colombia (slice por entidad)."""
    mensuales = []
    m = p[p["periodicidad"] == "Mensual"]
    for (ind, fte), g in m.groupby(["indicador", "fuente"]):
        g = g.sort_values(["anio", "mes"])
        mensuales.append({
            "indicador": ind,
            "fuente": nombre_fuente_corto(fte),
            "proveedor": proveedor(fte),
            "unidad": g["unidad"].iloc[0],
            "puntos": [[int(r.anio), int(r.mes), round(float(r.valor), 4)] for r in g.itertuples()],
        })
    anuales = {}
    ents = {"World": "Mundo", REGION_FOCO: "Sudamerica", PAIS_FOCO: "Colombia"}
    a = p[(p["periodicidad"] == "Anual") & (p["entidad"].isin(ents.keys()))]
    for ind, g in a.groupby("indicador"):
        series = {}
        for ent, gg in g.groupby("entidad"):
            series[ents[ent]] = [[int(r.anio), round(float(r.valor), 4)] for r in gg.sort_values("anio").itertuples()]
        if len(series):
            anuales[ind] = {"unidad": g["unidad"].iloc[0], "series": series}
    return {"mensuales": mensuales, "anuales": anuales, "meses": MESES}


def _anio_ref(nac):
    """Ultimo anio en que el indicador base tiene cobertura amplia de paises
    (evita tomar un anio parcial, como 2025, como referencia)."""
    base = nac[nac["indicador"] == IND_BASE].groupby("anio")["entidad"].nunique()
    if base.empty:
        return int(nac["anio"].max()) if len(nac) else None
    amplios = base[base >= base.max() * 0.8]
    return int(amplios.index.max())


def vista_territorial(p):
    """Vista 2: Mundo > Region > Pais para indicadores aditivos."""
    nac = p[(p["nivel_geografico"] == "Nacional") & (p["indicador"].isin(IND_TERRITORIALES))
            & (p["periodicidad"] == "Anual")]
    paises = (nac[["entidad", "iso_code", "region"]].drop_duplicates("entidad")
              .sort_values("entidad").reset_index(drop=True))
    idx = {e: k for k, e in enumerate(paises["entidad"])}
    anios = sorted(int(a) for a in nac["anio"].unique())
    valores = {}
    unidades = {}
    for ind, g in nac.groupby("indicador"):
        unidades[ind] = g["unidad"].iloc[0]
        valores[ind] = {}
        for an, gg in g.groupby("anio"):
            fila = [None] * len(paises)
            for r in gg.itertuples():
                fila[idx[r.entidad]] = round(float(r.valor), 3)
            valores[ind][str(int(an))] = fila
    reg = p[(p["nivel_geografico"].isin(["Regional", "Global"])) & (p["indicador"].isin(IND_TERRITORIALES))
            & (p["entidad"].isin(ORDEN_REGIONES + ["World"]))]
    oficiales = {}
    for (ind, an), g in reg.groupby(["indicador", "anio"]):
        oficiales.setdefault(ind, {})[str(int(an))] = {r.entidad: round(float(r.valor), 3) for r in g.itertuples()}
    return {
        "indicadores": [{"clave": i, "unidad": unidades.get(i, "")} for i in IND_TERRITORIALES if i in valores],
        "anios": anios,
        "anio_ref": _anio_ref(nac),
        "paises": [{"n": r.entidad, "iso": r.iso_code, "r": r.region} for r in paises.itertuples()],
        "valores": valores,
        "oficiales": oficiales,
        "regiones": [{"clave": r, "nombre": REGIONES_ES[r]} for r in ORDEN_REGIONES],
        "foco": PAIS_FOCO,
    }


def vista_mapa(p):
    """Vista 3: matriz Territorio x Anio (slice por indicador, dice por
    territorios y anios)."""
    ents = ORDEN_REGIONES + ["World", PAIS_FOCO]
    sub = p[(p["indicador"].isin(IND_MAPA)) & (p["entidad"].isin(ents)) & (p["periodicidad"] == "Anual")]
    datos = {}
    unidades = {}
    for ind, g in sub.groupby("indicador"):
        unidades[ind] = g["unidad"].iloc[0]
        datos[ind] = {}
        for r in g.itertuples():
            datos[ind].setdefault(nombre_geo(r.entidad), {})[str(int(r.anio))] = round(float(r.valor), 4)
    anios = sorted({int(a) for a in sub["anio"].unique()})
    filas = [nombre_geo(e) for e in ents]
    return {
        "indicadores": [{"clave": i, "unidad": unidades[i], "agregacion": CATALOGO_INDICADORES[i][2]}
                        for i in IND_MAPA if i in datos],
        "territorios": filas,
        "anios": anios,
        "datos": datos,
    }


def vista_pivot(p):
    """Vista 4: cubo agregado para la tabla dinamica. Cada celda guarda las
    medidas base (n, atipicos, suma z, suma valor) para poder recalcular
    cualquier medida derivada en cualquier combinacion de dimensiones."""
    q = p.copy()
    q["region_es"] = q["region"].map(lambda r: REGIONES_ES.get(r, r))
    q["z"] = q["valor_z"].fillna(0.0)
    q["nz"] = q["valor_z"].notna().astype(int)
    q["at"] = q["atipico"].astype(int)
    claves = ["anio", "region_es", "nivel_geografico", "categoria", "indicador", "fuente_tipo", "proveedor"]
    g = q.groupby(claves, dropna=False).agg(n=("valor", "size"), at=("at", "sum"), z=("z", "sum"),
                                              nz=("nz", "sum"), v=("valor", "sum")).reset_index()
    # Codificacion compacta: cada dimension como lista de miembros + indices.
    dims = {}
    filas = []
    for c in claves:
        miembros = sorted(str(x) for x in g[c].unique())
        if c == "categoria":
            miembros = [m for m in ORDEN_CATEGORIAS if m in miembros] + [m for m in miembros if m not in ORDEN_CATEGORIAS]
        dims[c] = miembros
    pos = {c: {m: k for k, m in enumerate(dims[c])} for c in claves}
    for r in g.itertuples(index=False):
        rr = r._asdict()
        filas.append([pos[c][str(rr[c])] for c in claves]
                     + [int(rr["n"]), int(rr["at"]), round(float(rr["z"]), 3), int(rr["nz"]), round(float(rr["v"]), 3)])
    agr = {i: CATALOGO_INDICADORES.get(i, ("", "", "promedio"))[2] for i in dims["indicador"]}
    unidades = dict(p[["indicador", "unidad"]].drop_duplicates("indicador").values)
    return {
        "claves": claves,
        "etiquetas": {"anio": "Anio", "region_es": "Region", "nivel_geografico": "Nivel geografico",
                      "categoria": "Categoria de indicador", "indicador": "Indicador",
                      "fuente_tipo": "Tipo de fuente", "proveedor": "Proveedor"},
        "miembros": dims,
        "celdas": filas,
        "agregacion": agr,
        "unidades": unidades,
    }



# ---------------------------------------------------------------------------
# 3b. Continuidad: registros usados, limitaciones de calidad y unidad de analisis
# ---------------------------------------------------------------------------
def registros_por_vista(p):
    mens = p["periodicidad"] == "Mensual"
    anual_foco = (p["periodicidad"] == "Anual") & p["entidad"].isin(["World", REGION_FOCO, PAIS_FOCO])
    v2 = (p["nivel_geografico"] == "Nacional") & p["indicador"].isin(IND_TERRITORIALES) & (p["periodicidad"] == "Anual")
    v3 = p["indicador"].isin(IND_MAPA) & p["entidad"].isin(ORDEN_REGIONES + ["World", PAIS_FOCO]) & (p["periodicidad"] == "Anual")
    return {1: int((mens | anual_foco).sum()), 2: int(v2.sum()), 3: int(v3.sum()), 4: int(len(p))}


EJEMPLO_IND = ["Emisiones de CO2 (total)", "Emisiones de CO2 per capita", "Emisiones de metano",
               "Participacion de renovables en energia", "Poblacion", "Consumo de energia primaria"]


def continuidad(p, n_consolidado=None):
    total = int(len(p))
    n_at = int(p["atipico"].sum())
    por_anio = p.groupby("anio").size()
    mx = int(por_anio.max())
    anios = [{"anio": int(a), "n": int(n), "pct": round(n / mx * 100, 1), "parcial": bool(n < mx * 0.5)}
             for a, n in por_anio.items()]
    parciales = [a["anio"] for a in anios if a["parcial"]]
    nivel = p["nivel_geografico"].value_counts()
    tipo = p["fuente_tipo"].value_counts()
    cob = p[p["nivel_geografico"] == "Nacional"].groupby("indicador").size().sort_values()
    mens = int((p["periodicidad"] == "Mensual").sum())
    owid = int(p["fuente"].astype(str).str.startswith("Our World in Data").sum())

    # Unidad de analisis: territorio en un anio. Granularidad: un indicador por
    # territorio, fecha y fuente.
    nac = p[p["nivel_geografico"] == "Nacional"]
    unidades = nac.groupby(["entidad", "anio"]).size()
    col = p[(p["entidad"] == PAIS_FOCO) & (p["anio"] == 2024)]
    ejemplo = [{"indicador": r.indicador, "valor": fmt_dec(r.valor, 2 if abs(r.valor) < 100 else 0), "unidad": r.unidad,
                "fuente": nombre_fuente_corto(r.fuente)} for r in col[col["indicador"].isin(EJEMPLO_IND)].sort_values("indicador").itertuples()]

    limitaciones = [
        {"titulo": "Atipicos marcados, no eliminados",
         "detalle": "{} registros ({}) estan marcados como atipicos por 1,5 × IQR. Se conservan porque casi todos tienen "
                    "una causa real (agregados, paises muy grandes, rebote 2020-2021), pero el IQR se calculo mezclando "
                    "niveles geograficos.".format(fmt_int(n_at), fmt_pct(n_at / total * 100)),
         "efecto": "Una medida de atipicos sin separar por nivel exagera los problemas de regiones y mundo (pregunta 4)."},
        {"titulo": "Anios con cobertura parcial",
         "detalle": "{} tienen {} registros frente a {} de un anio completo.".format(
             " y ".join(str(a) for a in parciales), " y ".join(fmt_int(int(por_anio[a])) for a in parciales), fmt_int(mx))
         if parciales else "Todos los anios tienen cobertura similar.",
         "efecto": "Las comparaciones entre territorios se hacen hasta el ultimo anio con cobertura amplia (2024)."},
        {"titulo": "Indicadores con cobertura desigual",
         "detalle": "Entre paises, {} tiene {} registros y {} tiene {}: no todos los paises reportan todos los gases ni la mezcla energetica.".format(
             cob.index[0], fmt_int(int(cob.iloc[0])), cob.index[-1], fmt_int(int(cob.iloc[-1]))),
         "efecto": "Un total por region puede cambiar segun el indicador porque cambia el numero de paises que suman."},
        {"titulo": "Solo tres series llegan al mes",
         "detalle": "{} registros son mensuales (anomalia de temperatura de NASA y NOAA, CO2 de Mauna Loa); el resto es anual.".format(fmt_int(mens)),
         "efecto": "El drill-down temporal hasta el mes solo es posible para el clima global (pregunta 3)."},
        {"titulo": "Predominio de una fuente terciaria",
         "detalle": "{} de los registros vienen de Our World in Data; las fuentes primarias aportan {}.".format(
             fmt_pct(owid / total * 100), fmt_pct(tipo.get("Primaria", 0) / total * 100)),
         "efecto": "La dimension Fuente solo permite comparar proveedores en las series climaticas globales."},
        {"titulo": "Niveles geograficos superpuestos",
         "detalle": "Conviven {} registros nacionales, {} regionales y {} globales que miden lo mismo a distinta escala.".format(
             fmt_int(int(nivel.get("Nacional", 0))), fmt_int(int(nivel.get("Regional", 0))), fmt_int(int(nivel.get("Global", 0)))),
         "efecto": "Sumar niveles distintos cuenta dos veces la misma emision; el cubo filtra o advierte."},
    ]
    return {
        "n_consolidado": int(n_consolidado) if n_consolidado is not None else total,
        "n_limpio": total,
        "n_eliminados": int(n_consolidado - total) if n_consolidado is not None else 0,
        "n_atipicos": n_at,
        "pct_atipicos": fmt_pct(n_at / total * 100),
        "n_mensuales": mens,
        "anios": anios,
        "niveles": [{"nivel": k, "n": int(v), "pct": fmt_pct(v / total * 100)} for k, v in nivel.items()],
        "limitaciones": limitaciones,
        "por_vista": registros_por_vista(p),
        "unidad": {
            "n_paises": int(nac["entidad"].nunique()),
            "n_pais_anio": int(len(unidades)),
            "hechos_por_pais_anio": fmt_dec(float(unidades.mean()), 1),
            "max_hechos": int(unidades.max()),
            "n_col_2024": int(len(col)),
            "ejemplo": ejemplo,
        },
    }

# ---------------------------------------------------------------------------
# 4. Ejemplos de operaciones y conocimientos descubiertos (paginas 6 y 7)
# ---------------------------------------------------------------------------
def _valor(p, ind, ent, anio):
    s = p[(p["indicador"] == ind) & (p["entidad"] == ent) & (p["anio"] == anio) & (p["periodicidad"] == "Anual")]
    return float(s["valor"].iloc[0]) if len(s) else None


def conocimientos(p, vt):
    ks = []
    anio_ref = vt["anio_ref"]
    anio_ini = min(vt["anios"]) if vt["anios"] else None

    # --- K1 Drill-down territorial: concentracion dentro de Sudamerica -------
    sa = p[(p["indicador"] == IND_BASE) & (p["anio"] == anio_ref) & (p["nivel_geografico"] == "Nacional")
           & (p["region"] == REGION_FOCO)].sort_values("valor", ascending=False)
    tot = float(sa["valor"].sum()) if len(sa) else 0
    if tot > 0:
        sa = sa.assign(pct=sa["valor"] / tot * 100)
        rank_col = int(list(sa["entidad"]).index(PAIS_FOCO)) + 1 if PAIS_FOCO in list(sa["entidad"]) else None
        top3 = float(sa["pct"].head(3).sum())
        col = sa[sa["entidad"] == PAIS_FOCO]
        evid = [{"etiqueta": r.entidad, "valor": fmt_int(r.valor) + " Mt CO2", "pct": round(r.pct, 2),
                 "pct_txt": fmt_pct(r.pct)} for r in sa.head(5).itertuples()]
        if len(col) and PAIS_FOCO not in [e["etiqueta"] for e in evid]:
            r = col.iloc[0]
            evid.append({"etiqueta": PAIS_FOCO, "valor": fmt_int(r.valor) + " Mt CO2", "pct": round(r.pct, 2),
                         "pct_txt": fmt_pct(r.pct)})
        ofi = _valor(p, IND_BASE, REGION_FOCO, anio_ref)
        dif = (tot / ofi - 1) * 100 if ofi else None
        ks.append({
            "numero": 1,
            "titulo": "Dentro de Sudamerica, {} emite {} del CO2 y Colombia es el pais numero {}".format(
                sa.iloc[0]["entidad"], fmt_pct(sa.iloc[0]["pct"]), rank_col),
            "operacion": "Drill-down territorial (Region → Pais) + slice por anio e indicador",
            "vista": 2,
            "pregunta": "¿Como se reparte el CO2 de Sudamerica entre sus paises y donde queda Colombia?",
            "evidencia": evid,
            "hallazgo": "En {a}, {p1} aporta {s1} del CO2 de la region; los tres primeros suman {t3}. Colombia es el "
                        "pais numero {rk} de {n}, con {sc}. La suma de los paises ({tp} Mt) coincide con el agregado "
                        "oficial de la region con una diferencia de {df}.".format(
                            a=anio_ref, p1=sa.iloc[0]["entidad"], s1=fmt_pct(sa.iloc[0]["pct"]), t3=fmt_pct(top3),
                            rk=rank_col, n=len(sa), sc=fmt_pct(float(col.iloc[0]["pct"])) if len(col) else "sin dato",
                            tp=fmt_int(tot), df=fmt_signo(dif, 2) if dif is not None else "sin dato"),
            "interpretacion": "En la Etapa 4 Sudamerica aparecia como un bloque de bajo aporte (cerca del 3% mundial). "
                              "Al bajar un nivel, el cubo muestra que esa region tampoco es homogenea: la "
                              "responsabilidad regional esta concentrada en pocos paises.",
            "utilidad": "Para comparar a Colombia conviene usar a sus pares regionales de tamano parecido, no el "
                        "total regional dominado por un solo pais.",
        })

    # --- K2 Slice & dice (mapa de calor): cambio 2020 -> anio_ref ------------
    filas = []
    for ent in ORDEN_REGIONES + ["World", PAIS_FOCO]:
        v0 = _valor(p, IND_BASE, ent, anio_ini)
        v1 = _valor(p, IND_BASE, ent, anio_ref)
        if v0 and v1:
            filas.append((nombre_geo(ent), (v1 / v0 - 1) * 100, v0, v1))
    filas.sort(key=lambda x: -x[1])
    ren = {}
    for ent in [PAIS_FOCO, REGION_FOCO, "World"]:
        v0 = _valor(p, "Participacion de renovables en energia", ent, anio_ini)
        v1 = _valor(p, "Participacion de renovables en energia", ent, anio_ref)
        if v0 is not None and v1 is not None:
            ren[nombre_geo(ent)] = (v0, v1)
    if filas:
        mx = max(abs(f[1]) for f in filas) or 1
        evid = [{"etiqueta": f[0], "valor": fmt_signo(f[1]), "pct": round(abs(f[1]) / mx * 100, 2),
                 "pct_txt": "{} → {} Mt".format(fmt_int(f[2]), fmt_int(f[3])), "negativo": f[1] < 0}
                for f in filas]
        neg = [f[0] for f in filas if f[1] < 0]
        txt_ren = ""
        if "Colombia" in ren and "Mundo" in ren:
            txt_ren = (" En el mismo corte, la participacion de renovables en la energia de Colombia paso de {c0} a "
                       "{c1}, mientras la del mundo subio de {w0} a {w1}.").format(
                c0=fmt_pct(ren["Colombia"][0]), c1=fmt_pct(ren["Colombia"][1]),
                w0=fmt_pct(ren["Mundo"][0]), w1=fmt_pct(ren["Mundo"][1]))
        ks.append({
            "numero": 2,
            "titulo": "Entre {} y {} {} lidera el aumento de emisiones{}".format(
                anio_ini, anio_ref, filas[0][0], (" y " + " y ".join(neg) + " las reducen") if neg else ""),
            "operacion": "Dice (territorios × anios) + slice por indicador sobre el mapa de calor",
            "vista": 3,
            "pregunta": "¿Que territorios aumentaron o redujeron sus emisiones de CO2 en el periodo?",
            "evidencia": evid,
            "hallazgo": "{p} es el territorio que mas crece ({vp}); {neg}. Colombia queda practicamente estable "
                        "({vc}).{ren}".format(
                            p=filas[0][0], vp=fmt_signo(filas[0][1]),
                            neg=("bajan " + ", ".join(neg)) if neg else "ningun territorio reduce sus emisiones",
                            vc=fmt_signo(next((f[1] for f in filas if f[0] == PAIS_FOCO), 0)), ren=txt_ren),
            "interpretacion": "La foto de un solo anio (Etapa 4) muestra quien emite mas; el corte por anio muestra "
                              "hacia donde va cada territorio. Parte del crecimiento se explica por el rebote despues "
                              "de 2020, el anio de la pandemia, por lo que conviene leer tambien la variacion anual.",
            "utilidad": "Ayuda a no confundir tamano con tendencia: un territorio pequeno puede ser el que mas crece.",
        })

    # --- K3 Drill-down temporal ---------------------------------------------
    m = p[(p["periodicidad"] == "Mensual") & (p["indicador"] == "Anomalia de temperatura global")]
    ml = p[(p["periodicidad"] == "Mensual") & (p["indicador"] == "Concentracion de CO2 atmosferico")]
    if len(m):
        por_fte = m.groupby(["fuente", "anio"])["valor"].mean().unstack(0)
        completos = m.groupby("anio")["mes"].nunique()
        anios_c = [a for a in por_fte.index if completos.get(a, 0) >= 12]
        prom = por_fte.loc[anios_c].mean(axis=1)
        a_max = int(prom.idxmax())
        pico = m.loc[m["valor"].idxmax()]
        dif_ftes = (por_fte.loc[anios_c].max(axis=1) - por_fte.loc[anios_c].min(axis=1)).mean()
        evid = [{"etiqueta": str(int(a)), "valor": fmt_dec(v, 2) + " °C", "pct": round(v / prom.max() * 100, 2),
                 "pct_txt": "promedio de fuentes"} for a, v in prom.items()]
        txt_ml = ""
        if len(ml):
            mla = ml.groupby("anio")["valor"].mean()
            cmp_ = [a for a in mla.index if ml[ml["anio"] == a]["mes"].nunique() >= 12]
            if len(cmp_) >= 2:
                sube = (mla.loc[cmp_[-1]] - mla.loc[cmp_[0]]) / (cmp_[-1] - cmp_[0])
                txt_ml = (" Al hacer roll-up de Mauna Loa al nivel Anio, el CO2 atmosferico sube sin interrupcion de "
                          "{a} a {b} ppm entre {x} y {y} (≈ {s} ppm por anio), sin un solo anio de "
                          "descenso.").format(a=fmt_dec(mla.loc[cmp_[0]], 1), b=fmt_dec(mla.loc[cmp_[-1]], 1),
                                                         x=cmp_[0], y=cmp_[-1], s=fmt_dec(sube, 2))
        ks.append({
            "numero": 3,
            "titulo": "El calentamiento se ve en el anio, pero el pico solo aparece al bajar al mes",
            "operacion": "Drill-down y roll-up temporal (Anio ↔ Trimestre ↔ Mes) + slice por fuente",
            "vista": 1,
            "pregunta": "¿En que periodos la anomalia de temperatura fue mas alta y que tanto coinciden las fuentes?",
            "evidencia": evid,
            "hallazgo": "Con anios completos, {am} es el anio mas calido del periodo ({vm} °C de anomalia promedio). "
                        "Al bajar al nivel Mes aparece el maximo puntual: {mes} de {an}, con {vp} °C ({fp}). Las dos "
                        "fuentes difieren en promedio {dd} °C por su linea base, pero suben y bajan en los mismos "
                        "meses.{ml}".format(
                            am=a_max, vm=fmt_dec(prom.loc[a_max], 2), mes=MESES[int(pico["mes"]) - 1],
                            an=int(pico["anio"]), vp=fmt_dec(float(pico["valor"]), 2),
                            fp=nombre_fuente_corto(pico["fuente"]), dd=fmt_dec(dif_ftes, 2), ml=txt_ml),
            "interpretacion": "El nivel Anio sirve para ver la tendencia; el nivel Mes muestra episodios (como el "
                              "evento de El Nino 2023-2024) que el promedio anual suaviza. Comparar fuentes con un "
                              "slice evita leer como cambio real lo que es una diferencia de metodologia.",
            "utilidad": "Para hablar de eventos externos (ENSO, olas de calor) el proyecto debe analizarse a nivel "
                        "mensual; para tendencias, a nivel anual.",
        })

    # --- K4 Pivot: atipicos por nivel geografico y categoria -----------------
    piv = p.groupby(["nivel_geografico", "categoria"])["atipico"].agg(["mean", "size"]).reset_index()
    niv = p.groupby("nivel_geografico")["atipico"].mean() * 100
    if len(niv):
        evid = [{"etiqueta": "Nivel · " + k, "valor": fmt_int(int((p["nivel_geografico"] == k).sum())) + " registros",
                 "pct": round(v, 2), "pct_txt": fmt_pct(v) + " atipicos"} for k, v in niv.sort_values(ascending=False).items()]
        cat_reg = piv[piv["nivel_geografico"] == "Regional"].sort_values("mean", ascending=False)
        prim = p[p["fuente_tipo"] == "Primaria"]["atipico"].mean() * 100
        ks.append({
            "numero": 4,
            "titulo": "La marca de atipico depende del nivel geografico, no solo del dato",
            "operacion": "Pivot (Nivel geografico × Categoria, medida % de atipicos) + roll-up a Nivel",
            "vista": 4,
            "pregunta": "¿Los atipicos marcados en la limpieza se reparten igual en todo el cubo?",
            "evidencia": evid,
            "hallazgo": "El {r} de los registros regionales esta marcado como atipico, frente a {n} de los nacionales. "
                        "La categoria regional con mas atipicos es {c} ({cv}). En las fuentes primarias el porcentaje es "
                        "{pp}.".format(
                            r=fmt_pct(niv.get("Regional", 0)), n=fmt_pct(niv.get("Nacional", 0)),
                            c=cat_reg.iloc[0]["categoria"] if len(cat_reg) else "-",
                            cv=fmt_pct(cat_reg.iloc[0]["mean"] * 100) if len(cat_reg) else "-", pp=fmt_pct(prim)),
            "interpretacion": "El IQR de la Etapa 2 se calculo por indicador mezclando paises, continentes y el mundo. "
                              "Un continente siempre es \"grande\" frente a un pais, por eso cae fuera del rango aunque "
                              "su valor sea correcto. El cubo hace visible este efecto al cruzar la marca con el nivel.",
            "utilidad": "En analisis posteriores la deteccion de atipicos debe hacerse dentro de cada nivel geografico "
                        "(y, para los paises, quiza por grupo de tamano).",
        })
    return ks


def ejemplos_operaciones(p, vt):
    anio_ref = vt["anio_ref"]
    ej = {}
    reg = p[(p["indicador"] == IND_BASE) & (p["anio"] == anio_ref) & (p["nivel_geografico"] == "Nacional")]
    por_reg = reg.groupby("region")["valor"].sum()
    mundo = float(por_reg.sum()) if len(por_reg) else 0
    if mundo:
        ej["rollup"] = ("Los {n} paises suman {m} Mt de CO2 en {a}; al subir a Region, Asia concentra {asia}.").format(
            n=len(reg), m=fmt_int(mundo), a=anio_ref, asia=fmt_pct(por_reg.get("Asia", 0) / mundo * 100))
        sa = reg[reg["region"] == REGION_FOCO]
        ej["drilldown"] = ("Al abrir Sudamerica aparecen sus {n} paises; Colombia aporta {c} del CO2 regional.").format(
            n=len(sa), c=fmt_pct(float(sa[sa["entidad"] == PAIS_FOCO]["valor"].sum()) / float(sa["valor"].sum()) * 100)
            if len(sa) else "-")
    sl = p[(p["anio"] == anio_ref)]
    ej["slice"] = ("Fijar Anio = {a} deja {n} de {t} hechos del cubo.").format(
        a=anio_ref, n=fmt_int(len(sl)), t=fmt_int(len(p)))
    dc = p[(p["anio"].between(2022, 2024)) & (p["region"] == REGION_FOCO) & (p["categoria"] == "Energia")]
    ej["dice"] = ("Anio 2022–2024 × Region = Sudamerica × Categoria = Energia deja un subcubo de {n} hechos.").format(
        n=fmt_int(len(dc)))
    ej["pivot"] = ("La misma consulta puede leerse como Region en filas y Anio en columnas, o al reves, sin "
                   "recalcular nada: solo cambia la orientacion.")
    return ej


# ---------------------------------------------------------------------------
# 5. Punto de entrada
# ---------------------------------------------------------------------------
_CACHE = {}


def construir(df, n_consolidado=None):
    """Devuelve el dict completo para las paginas de la Etapa 5, o None."""
    if df is None or df.empty:
        return None
    clave = (id(df), len(df))
    if clave in _CACHE:
        return _CACHE[clave]
    hechos, dt, dg, di, dfu = construir_estrella(df)
    p = _plano(hechos, dt, dg, di, dfu)
    modelo = describir_modelo(hechos, dt, dg, di, dfu)
    vt = vista_territorial(p)
    info = {
        "modelo": modelo,
        "anio_min": int(dt["anio"].min()),
        "anio_max": int(dt["anio"].max()),
        "vistas": {
            "temporal": vista_temporal(p),
            "territorial": vt,
            "mapa": vista_mapa(p),
            "pivot": vista_pivot(p),
        },
        "conocimientos": conocimientos(p, vt),
        "ejemplos": ejemplos_operaciones(p, vt),
        "continuidad": continuidad(p, n_consolidado),
        "sin_region": int(((dg["nivel_geografico"] == "Nacional") & (dg["region"] == "Sin region")).sum()),
    }
    _CACHE.clear()
    _CACHE[clave] = info
    return info


if __name__ == "__main__":
    ruta = os.path.join(BASE_DIR, "data", "raw", "clima_limpio.csv")
    datos = pd.read_csv(ruta)
    info = construir(datos)
    print("Hechos:", info["modelo"]["n_hechos"])
    for d in info["modelo"]["dimensiones"]:
        print(" -", d["tabla"], d["filas"], "filas")
    for k in info["conocimientos"]:
        print("\n[{}] {}\n{}".format(k["numero"], k["titulo"], k["hallazgo"]))
