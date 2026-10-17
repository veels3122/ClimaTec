# -*- coding: utf-8 -*-
"""
ClimaTec - Etapa 4 / Dimension Territorial.

Calcula, a partir del conjunto de datos limpio (clima_limpio.csv), todo lo que
publica la pagina "Dimension Territorial":

  - reparto de cada indicador entre las seis regiones (continentes) del dataset;
  - concentracion entre paises: top 10, cuantos paises suman el 50 % y el 80 %,
    territorios con mayor y menor valor y posicion de Colombia;
  - comparacion per capita de Colombia y Sudamerica frente al promedio mundial;
  - los tres conocimientos evidentes, la limitacion y la decision, con cifras
    calculadas en vivo.

Ninguna cifra se escribe a mano: si cambia el CSV, cambia la pagina. Las
graficas se dibujan en el navegador (SVG) con el JSON que devuelve construir().
"""

import pandas as pd

PAIS_FOCO = "Colombia"
REGION_FOCO = "South America"
MUNDO = "World"

# Indicadores absolutos (se pueden sumar y repartir entre territorios).
INDICADORES = [
    ("Emisiones de CO2 (total)", "Emisiones de CO2"),
    ("Gases de efecto invernadero (total)", "Gases de efecto invernadero"),
    ("Consumo de energia primaria", "Consumo de energia primaria"),
    ("Emisiones de metano", "Emisiones de metano"),
    ("Generacion de electricidad", "Generacion de electricidad"),
]
IND_BASE = "Emisiones de CO2 (total)"

# Indicadores relativos para comparar Colombia, Sudamerica y el mundo.
PER_CAPITA = [
    ("Emisiones de CO2 per capita", "CO2 per capita", 2),
    ("GEI per capita (sin uso del suelo)", "GEI per capita", 2),
    ("Consumo de energia per capita", "Energia per capita", 0),
    ("Participacion de renovables en energia", "Renovables en la energia", 1),
]

REGIONES_ES = {
    "Africa": "Africa",
    "Asia": "Asia",
    "Europe": "Europa",
    "North America": "Norteamerica",
    "Oceania": "Oceania",
    "South America": "Sudamerica",
}


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


def fmt_val(x, unidad):
    """Valor con su unidad: 37.398 Mt CO2, 1,75 t CO2/persona."""
    if x is None:
        return "sin dato"
    d = 0 if abs(x) >= 100 else (1 if abs(x) >= 10 else 2)
    return "{} {}".format(fmt_dec(x, d), unidad)


def nombre(entidad):
    if entidad == PAIS_FOCO:
        return "Colombia"
    return REGIONES_ES.get(entidad, entidad)


# ---------------------------------------------------------------------------
# Calculos por indicador y anio
# ---------------------------------------------------------------------------
def _valor(sub, entidad):
    s = sub.loc[sub["entidad"] == entidad, "valor"]
    return float(s.iloc[0]) if len(s) else None


def _territorio(df, indicador, anio):
    sub = df[(df["indicador"] == indicador) & (df["anio"] == anio)]
    if sub.empty:
        return None
    unidad = str(sub["unidad"].iloc[0])

    reg = (sub[sub["nivel_geografico"] == "Regional"][["entidad", "valor"]]
           .dropna().sort_values("valor", ascending=False))
    suma_reg = float(reg["valor"].sum())
    regiones = [{"entidad": nombre(r.entidad), "valor": float(r.valor),
                 "pct": round(100 * r.valor / suma_reg, 2) if suma_reg else 0}
                for r in reg.itertuples()]

    nac = (sub[sub["nivel_geografico"] == "Nacional"][["entidad", "valor"]]
           .dropna().sort_values("valor", ascending=False).reset_index(drop=True))
    if nac.empty or not regiones:
        return None
    total = float(nac["valor"].sum())
    nac["pct"] = 100 * nac["valor"] / total
    acum = nac["pct"].cumsum()
    n50 = int((acum < 50).sum() + 1)
    n80 = int((acum < 80).sum() + 1)

    top = [{"entidad": nombre(r.entidad), "valor": float(r.valor), "pct": round(r.pct, 2)}
           for r in nac.head(10).itertuples()]
    top10_pct = round(float(nac.head(10)["pct"].sum()), 2)

    positivos = nac[nac["valor"] > 0]
    menores = [{"entidad": nombre(r.entidad), "valor": float(r.valor), "pct": round(r.pct, 4)}
               for r in positivos.tail(5).iloc[::-1].itertuples()]
    ceros = int((nac["valor"] <= 0).sum())

    col = None
    fila = nac.index[nac["entidad"] == PAIS_FOCO]
    if len(fila):
        i = int(fila[0])
        v = float(nac.loc[i, "valor"])
        sa = _valor(sub, REGION_FOCO)
        col = {"rank": i + 1, "valor": v, "pct": round(float(nac.loc[i, "pct"]), 3),
               "pct_sa": round(100 * v / sa, 2) if sa else None}

    mundo = _valor(sub, MUNDO)
    return {
        "anio": int(anio),
        "unidad": unidad,
        "regiones": regiones,
        "suma_regiones": suma_reg,
        "mundo": mundo,
        "paises": int(len(nac)),
        "total_paises": total,
        "top": top,
        "top10_pct": top10_pct,
        "resto": {"paises": int(len(nac) - len(top)), "valor": total - float(nac.head(10)["valor"].sum()),
                  "pct": round(100 - top10_pct, 2)},
        "n50": n50,
        "n80": n80,
        "menores": menores,
        "ceros": ceros,
        "colombia": col,
    }


def _comparacion(df, anio):
    filas = []
    for ind, etq, dec in PER_CAPITA:
        sub = df[(df["indicador"] == ind) & (df["anio"] == anio)]
        if sub.empty:
            continue
        c, s, m = _valor(sub, PAIS_FOCO), _valor(sub, REGION_FOCO), _valor(sub, MUNDO)
        if None in (c, s, m) or not m:
            continue
        filas.append({
            "indicador": etq, "unidad": str(sub["unidad"].iloc[0]), "dec": dec,
            "colombia": c, "sudamerica": s, "mundo": m,
            "idx_col": round(100 * c / m, 1), "idx_sa": round(100 * s / m, 1),
        })
    return filas


# ---------------------------------------------------------------------------
# Textos (interpretaciones, conocimientos, limitacion y decision)
# ---------------------------------------------------------------------------
def _ev(etiqueta, valor, pct):
    return {"etiqueta": etiqueta, "valor": valor, "pct": pct, "pct_txt": fmt_pct(pct)}


def _pob_regiones(df, anio):
    sub = df[(df["indicador"] == "Poblacion") & (df["anio"] == anio) &
             (df["nivel_geografico"] == "Regional")][["entidad", "valor"]].dropna()
    t = float(sub["valor"].sum())
    return {nombre(r.entidad): 100 * r.valor / t for r in sub.itertuples()} if t else {}


def _conocimientos(datos, comp, pob_reg, anio):
    co2 = datos[IND_BASE][str(anio)]
    met = datos["Emisiones de metano"].get(str(anio))
    r = co2["regiones"]
    asia, sa = r[0], next(x for x in r if x["entidad"] == "Sudamerica")
    tres = r[0]["pct"] + r[1]["pct"] + r[2]["pct"]

    k1 = {
        "numero": 1,
        "titulo": "Tres regiones concentran casi todas las emisiones de CO2",
        "pregunta": "Como se reparten las emisiones de CO2 entre las seis regiones del dataset en {}?".format(anio),
        "variables": "nivel_geografico = Regional, entidad (continente), indicador = Emisiones de CO2 (total) en Mt CO2, anio; y Poblacion para comparar.",
        "procedimiento": "Se sumaron las emisiones de las seis regiones en {}, se dividio la de cada una entre esa suma y se comparo con su participacion en la poblacion del mismo anio.".format(anio),
        "evidencia_titulo": "Participacion en las emisiones de CO2 de {}".format(anio),
        "evidencia": [_ev(x["entidad"], fmt_val(x["valor"], co2["unidad"]), x["pct"]) for x in r],
        "hallazgo": "{} emite {} del CO2, seguida de {} ({}) y {} ({}): las tres suman {}. Sudamerica aporta {} con {} de la poblacion, y {} aporta {} con {} de la poblacion.".format(
            asia["entidad"], fmt_pct(asia["pct"]), r[1]["entidad"], fmt_pct(r[1]["pct"]), r[2]["entidad"],
            fmt_pct(r[2]["pct"]), fmt_pct(tres), fmt_pct(sa["pct"]), fmt_pct(pob_reg.get("Sudamerica", 0)),
            r[1]["entidad"], fmt_pct(r[1]["pct"]), fmt_pct(pob_reg.get(r[1]["entidad"], 0))),
        "interpretacion": "Las emisiones no se reparten como la poblacion: Norteamerica y Europa emiten mucho mas de lo que pesan en habitantes, mientras Sudamerica y Africa emiten bastante menos. La responsabilidad climatica esta concentrada territorialmente.",
        "utilidad": "Indica en que regiones tendria mas efecto una politica de mitigacion y ubica a Sudamerica como una region de bajo aporte absoluto.",
        "limitacion": "Son agregados continentales calculados por Our World in Data; la suma de las regiones no incluye el transporte internacional (aviacion y barcos), por eso es algo menor que el valor World.",
    }

    k2 = {
        "numero": 2,
        "titulo": "Diez paises emiten mas de dos tercios del CO2 de {} paises".format(co2["paises"]),
        "pregunta": "Que tan concentradas estan las emisiones de CO2 entre los paises en {}?".format(anio),
        "variables": "nivel_geografico = Nacional, entidad (pais), indicador = Emisiones de CO2 (total), anio.",
        "procedimiento": "Se ordenaron los {} paises de mayor a menor emision, se calculo la participacion de cada uno sobre la suma de paises y el porcentaje acumulado hasta llegar al 50 % y al 80 %.".format(co2["paises"]),
        "evidencia_titulo": "Los cinco paises con mas emisiones y el resto",
        "evidencia": [_ev(x["entidad"], fmt_val(x["valor"], co2["unidad"]), x["pct"]) for x in co2["top"][:5]]
            + [_ev("Resto ({} paises)".format(co2["resto"]["paises"]), fmt_val(co2["resto"]["valor"], co2["unidad"]), co2["resto"]["pct"])],
        "hallazgo": "{}, por si sola, emite {}; los 10 primeros suman {}. Bastan {} paises para llegar a la mitad de las emisiones y {} para el 80 %, mientras los {} restantes se reparten el 20 % final.".format(
            co2["top"][0]["entidad"], fmt_pct(co2["top"][0]["pct"]), fmt_pct(co2["top10_pct"]), co2["n50"], co2["n80"],
            co2["paises"] - co2["n80"]),
        "interpretacion": "La concentracion entre paises es aun mayor que entre regiones: el resultado global depende de muy pocos territorios. La mayoria de los paises tiene un peso individual casi nulo en el total.",
        "utilidad": "Permite enfocar el seguimiento y la validacion de datos en los pocos paises que explican la mayor parte del total.",
        "limitacion": "El total absoluto favorece a los paises grandes; no dice quien emite mas por habitante ni la tendencia historica acumulada.",
    }

    filas = {f["indicador"]: f for f in comp}
    pc = filas.get("CO2 per capita")
    ren = filas.get("Renovables en la energia")
    colm = met["colombia"] if met else None
    colc = co2["colombia"]
    k3 = {
        "numero": 3,
        "titulo": "Colombia emite poco CO2 por habitante, pero pesa mas en metano",
        "pregunta": "Como se ubica Colombia frente a Sudamerica y al mundo en {}?".format(anio),
        "variables": "entidad = Colombia, South America y World; indicadores per capita de CO2, GEI y energia, participacion de renovables, Emisiones de CO2 (total) y Emisiones de metano.",
        "procedimiento": "Se compararon los valores per capita de Colombia y Sudamerica con el promedio mundial (mundo = 100) y se calculo la posicion de Colombia en el ranking de paises para CO2 y para metano.",
        "evidencia_titulo": "Colombia frente al promedio mundial (mundo = 100)",
        "evidencia": [_ev(f["indicador"], fmt_val(f["colombia"], f["unidad"]), f["idx_col"]) for f in comp],
        "hallazgo": "Colombia emite {} t de CO2 por habitante, {} del promedio mundial ({} t) y menos que Sudamerica ({} t). En CO2 total ocupa el puesto {} de {} paises ({} del mundo), pero en metano sube al puesto {} de {} ({}). Sus renovables son {} de la energia frente a {} en el mundo.".format(
            fmt_dec(pc["colombia"], 2), fmt_pct(pc["idx_col"], 0), fmt_dec(pc["mundo"], 2),
            fmt_dec(pc["sudamerica"], 2), colc["rank"], co2["paises"], fmt_pct(colc["pct"], 2),
            colm["rank"] if colm else "-", met["paises"] if met else "-", fmt_pct(colm["pct"], 2) if colm else "-",
            fmt_pct(ren["colombia"]) if ren else "-", fmt_pct(ren["mundo"]) if ren else "-"),
        "interpretacion": "El perfil de Colombia no es el de un gran emisor energetico: su matriz tiene mas renovables que el promedio mundial y su CO2 por habitante es bajo. Su peso climatico aparece en otros gases, como el metano, asociado sobre todo a la ganaderia, la agricultura y los residuos.",
        "utilidad": "Sugiere que una estrategia climatica para Colombia deberia mirar ademas del CO2 energetico, porque su aporte relativo es mayor en metano.",
        "limitacion": "El dataset no desagrega el metano por sector ni por departamento; la asociacion con la ganaderia es una interpretacion del contexto, no un dato calculado aqui.",
    }
    return [k1, k2, k3]


def _interpretaciones(datos, comp, anio):
    co2 = datos[IND_BASE][str(anio)]
    co2_0 = datos[IND_BASE][str(min(int(k) for k in datos[IND_BASE]))]
    r = co2["regiones"]
    a0 = next(x for x in co2_0["regiones"] if x["entidad"] == r[0]["entidad"])
    v1 = ("En {} {} concentra {} de las emisiones de CO2 de las seis regiones y Sudamerica apenas {}. "
          "Entre {} y {} la participacion de {} paso de {} a {}: el peso del continente asiatico sigue creciendo. "
          "Con el filtro de indicador se ve que el reparto cambia segun el gas: en metano Africa y Sudamerica pesan mucho mas que en CO2.").format(
        anio, r[0]["entidad"], fmt_pct(r[0]["pct"]),
        fmt_pct(next(x for x in r if x["entidad"] == "Sudamerica")["pct"]),
        co2_0["anio"], anio, r[0]["entidad"], fmt_pct(a0["pct"]), fmt_pct(r[0]["pct"]))
    v2 = ("Las barras caen muy rapido: {} sola emite {} y los nueve paises siguientes suman {}; despues del decimo pais, "
          "ninguno supera el {} del total. Colombia aparece en el puesto {} con {}. Los territorios con menos emisiones son "
          "islas y territorios pequenos (por ejemplo {}), con valores cercanos a cero.").format(
        co2["top"][0]["entidad"], fmt_pct(co2["top"][0]["pct"]), fmt_pct(co2["top10_pct"] - co2["top"][0]["pct"]),
        fmt_pct(co2["top"][-1]["pct"]), co2["colombia"]["rank"], fmt_pct(co2["colombia"]["pct"], 2),
        ", ".join(x["entidad"] for x in co2["menores"][:3]))
    bajo = [f["indicador"] for f in comp if f["idx_col"] < 100]
    alto = [f["indicador"] for f in comp if f["idx_col"] >= 100]
    v3 = ("Colombia queda por debajo del promedio mundial en {} y por encima en {}. Sudamerica sigue el mismo patron pero "
          "con valores mas altos que Colombia en todos los indicadores: dentro de su propia region, Colombia es un territorio "
          "de bajas emisiones por habitante.").format(
        ", ".join(bajo) if bajo else "ningun indicador", ", ".join(alto) if alto else "ningun indicador")
    return {"v1": v1, "v2": v2, "v3": v3}


def _limitacion(anios):
    return {
        "titulo": "Los territorios del dataset son paises y continentes, no departamentos ni municipios",
        "texto": (
            "El nivel territorial mas fino del dataset es el pais: no hay datos por departamento, municipio o zona, por lo que "
            "no se pueden ver diferencias dentro de Colombia. Las seis regiones son agregados calculados por Our World in Data, "
            "su suma no incluye el transporte internacional y no siempre coincide con el valor World. Ademas, los indicadores "
            "territoriales solo existen entre {} y {} y algunos paises no reportan todos los gases. Las conclusiones describen "
            "como se reparten las emisiones entre territorios, no sus causas."
        ).format(min(anios), max(anios)),
    }


def _decision(datos, comp, anio):
    co2 = datos[IND_BASE][str(anio)]
    met = datos["Emisiones de metano"][str(anio)]
    return {
        "titulo": "Comparar a Colombia con indicadores per capita y vigilar el metano, no solo el CO2 total",
        "texto": (
            "Colombia representa {} del CO2 de los paises del dataset, pero {} del metano. Con esta evidencia se puede decidir "
            "(1) que en el proyecto Colombia se compare con Sudamerica y con el mundo usando indicadores per capita y de "
            "participacion, porque en valores absolutos queda opacada por los {} paises que concentran la mitad del CO2, y "
            "(2) que el seguimiento de Colombia incluya el metano como indicador prioritario, ya que es donde su aporte "
            "relativo es mayor."
        ).format(fmt_pct(co2["colombia"]["pct"], 2), fmt_pct(met["colombia"]["pct"], 2), co2["n50"]),
        "sustento": "Sustento: visualizaciones 2 y 3, y el conocimiento evidente 3.",
    }


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def construir(df):
    """Devuelve el dict completo para la pagina, o None si no hay datos."""
    if df is None or df.empty:
        return None
    base = df[(df["indicador"] == IND_BASE) & (df["nivel_geografico"] == "Nacional")]
    anios = sorted(int(a) for a in base["anio"].dropna().unique())
    if not anios:
        return None
    anio_ref = max(anios)

    datos = {}
    for ind, _ in INDICADORES:
        por_anio = {}
        for a in anios:
            t = _territorio(df, ind, a)
            if t:
                por_anio[str(a)] = t
        if por_anio:
            datos[ind] = por_anio
    if IND_BASE not in datos or str(anio_ref) not in datos[IND_BASE]:
        return None

    comparacion = {str(a): _comparacion(df, a) for a in anios}
    comp_ref = comparacion[str(anio_ref)]
    pob_reg = _pob_regiones(df, anio_ref)
    co2 = datos[IND_BASE][str(anio_ref)]

    nac = df[df["nivel_geografico"] == "Nacional"]
    territorial = df[df["indicador"].isin([i for i, _ in INDICADORES]) & df["anio"].isin(anios)]
    variables = [
        {"variable": "nivel_geografico", "tipo": "Categorica", "uso": "Escala del territorio: Global (mundo), Regional (6 continentes) o Nacional (paises)."},
        {"variable": "entidad", "tipo": "Categorica", "uso": "Territorio concreto: {} paises, 6 regiones y el agregado World.".format(int(nac["entidad"].nunique()))},
        {"variable": "iso_code", "tipo": "Categorica", "uso": "Codigo ISO de 3 letras de cada pais; vacio por diseno en regiones y en el mundo."},
        {"variable": "indicador", "tipo": "Categorica", "uso": "Filtro 2: variable que se reparte entre territorios (CO2, GEI, energia, metano, electricidad) y los indicadores per capita."},
        {"variable": "anio", "tipo": "Temporal", "uso": "Filtro 1: anio de analisis ({}-{}).".format(min(anios), max(anios))},
        {"variable": "valor / unidad", "tipo": "Numerica", "uso": "Magnitud del indicador en cada territorio (Mt CO2, TWh, t por persona, %)."},
        {"variable": "participacion (derivada)", "tipo": "Numerica derivada", "uso": "Valor del territorio dividido entre la suma de su nivel; permite comparar territorios."},
        {"variable": "indice mundo = 100 (derivada)", "tipo": "Numerica derivada", "uso": "Valor de Colombia o Sudamerica dividido entre el valor mundial, por 100."},
    ]

    graficos = {
        "anios": anios,
        "anio_ref": anio_ref,
        "indicadores": [{"clave": i, "nombre": n, "unidad": datos[i][str(anio_ref)]["unidad"]}
                        for i, n in INDICADORES if i in datos and str(anio_ref) in datos[i]],
        "datos": datos,
        "comparacion": comparacion,
    }
    return {
        "anio_min": min(anios),
        "anio_max": max(anios),
        "anio_ref": anio_ref,
        "n_paises": int(nac["entidad"].nunique()),
        "n_registros": int(len(territorial)),
        "co2": co2,
        "variables": variables,
        "interpretaciones": _interpretaciones(datos, comp_ref, anio_ref),
        "conocimientos": _conocimientos(datos, comp_ref, pob_reg, anio_ref),
        "limitacion": _limitacion(anios),
        "decision": _decision(datos, comp_ref, anio_ref),
        "graficos": graficos,
    }
