# -*- coding: utf-8 -*-
"""
ClimaTec - Etapa 4 / Dimension Temporal.

Analiza la evolucion en el tiempo con las SERIES MENSUALES REALES del dataset
limpio (clima_limpio.csv, periodicidad = Mensual):

  - Concentracion de CO2 atmosferico (NOAA GML, Mauna Loa, ppm);
  - Anomalia de temperatura global (NASA GISS - GISTEMP, grados C vs. base);
  - Anomalia de temperatura global (NOAA NCEI - GlobalTemp/GCAG, grados C vs. base);

y los eventos externos documentados (eventos_externos_muestra.csv).

Ninguna cifra se escribe a mano: si cambia el CSV, cambia la pagina. Las graficas
se dibujan en el navegador (SVG) con el JSON que devuelve construir().
"""

import numpy as np
import pandas as pd

from poblacional import fmt_dec, fmt_pct

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MESES_LARGO = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
               "septiembre", "octubre", "noviembre", "diciembre"]

IND_CO2 = "Concentracion de CO2 atmosferico"
IND_TEMP = "Anomalia de temperatura global"

# clave, etiqueta, unidad, texto de unidad, prefijo de fuente, indicador
SERIES = [
    ("co2", "CO2 atmosferico (Mauna Loa)", "ppm", "ppm", "NOAA GML", IND_CO2),
    ("gis", "Anomalia de temperatura (GISTEMP)", "°C", "°C vs. base", "NASA GISS", IND_TEMP),
    ("gcag", "Anomalia de temperatura (GCAG)", "°C", "°C vs. base", "NOAA NCEI", IND_TEMP),
]


def _sg(x, d=2):
    if abs(x) < 0.5 * 10 ** (-d):
        x = 0.0
    return ("+" if x > 0 else "") + fmt_dec(x, d)


def _ev(etiqueta, valor, pct):
    return {"etiqueta": etiqueta, "valor": valor, "pct": pct, "pct_txt": fmt_pct(pct)}


# ---------------------------------------------------------------------------
# Series
# ---------------------------------------------------------------------------
def _extraer(df):
    m = df[df["periodicidad"] == "Mensual"].copy()
    m = m.dropna(subset=["anio", "mes", "valor"])
    m["anio"] = m["anio"].astype(int)
    m["mes"] = m["mes"].astype(int)
    salida = {}
    for clave, etq, unidad, unidad_txt, pref, ind in SERIES:
        s = m[(m["indicador"] == ind) & (m["fuente"].str.startswith(pref))]
        s = s.sort_values(["anio", "mes"]).drop_duplicates(["anio", "mes"])
        if len(s) < 12:
            continue
        salida[clave] = {
            "clave": clave, "nombre": etq, "unidad": unidad, "unidad_txt": unidad_txt,
            "fuente": str(s["fuente"].iloc[0]), "fuente_tipo": str(s["fuente_tipo"].iloc[0]),
            "puntos": [[int(r.anio), int(r.mes), round(float(r.valor), 3)] for r in s.itertuples()],
        }
    return salida


def _anuales(puntos):
    """Promedio anual, meses con dato y si el anio esta completo."""
    por = {}
    for y, mo, v in puntos:
        por.setdefault(y, []).append(v)
    return [{"anio": y, "media": float(np.mean(v)), "n": len(v), "completo": len(v) == 12}
            for y, v in sorted(por.items())]


def _pendiente(puntos):
    x = np.array([y + (mo - 0.5) / 12 for y, mo, _ in puntos])
    v = np.array([p[2] for p in puntos])
    b, a = np.polyfit(x, v, 1)
    r = float(np.corrcoef(x, v)[0, 1])
    return float(b), float(a), r * r


def _estacional(puntos):
    """Desviacion media de cada mes respecto al promedio de su anio (solo anios completos)."""
    an = {a["anio"]: a for a in _anuales(puntos)}
    acc = {m: [] for m in range(1, 13)}
    for y, mo, v in puntos:
        if an[y]["completo"]:
            acc[mo].append(v - an[y]["media"])
    return [float(np.mean(acc[m])) if acc[m] else None for m in range(1, 13)]


def _eventos(eventos):
    if eventos is None or eventos.empty:
        return []
    out = []
    for r in eventos.sort_values("fecha").itertuples():
        f = str(r.fecha)
        try:
            y, mo = int(f[:4]), int(f[5:7])
        except ValueError:
            continue
        out.append({"anio": y, "mes": mo, "fecha": f[:7], "evento": str(r.evento),
                    "tipo": str(r.tipo), "ambito": str(r.ambito)})
    return out


# ---------------------------------------------------------------------------
# Conocimientos evidentes
# ---------------------------------------------------------------------------
def _conocimientos(S, eventos):
    co2 = S["co2"]["puntos"]
    an = _anuales(co2)
    comp = [a for a in an if a["completo"]]
    inc = [(comp[i]["anio"], comp[i]["media"] - comp[i - 1]["media"]) for i in range(1, len(comp))]
    pend, _, r2 = _pendiente(co2)
    mayor = max(inc, key=lambda t: t[1])
    menor = min(inc, key=lambda t: t[1])
    media_inc = float(np.mean([d for _, d in inc]))
    suben = sum(1 for _, d in inc if d > 0)

    parcial = [a for a in an if not a["completo"]]
    txt_parcial = ""
    if parcial:
        p = parcial[-1]
        meses_p = [mo for y, mo, _ in co2 if y == p["anio"]]
        prev = [v for y, mo, v in co2 if y == p["anio"] - 1 and mo in meses_p]
        act = [v for y, mo, v in co2 if y == p["anio"] and mo in meses_p]
        if prev and act:
            txt_parcial = " En {} (solo {} meses) el promedio de los mismos meses es {} ppm mayor que en {}.".format(
                p["anio"], len(meses_p), fmt_dec(float(np.mean(act)) - float(np.mean(prev)), 2), p["anio"] - 1)

    k1 = {
        "numero": 1,
        "titulo": "El CO2 atmosferico sube todos los anios, sin pausas",
        "pregunta": "Cual es la tasa de crecimiento del CO2 y se detiene en algun momento del periodo?",
        "variables": "anio, mes y valor de la concentracion de CO2 atmosferico (ppm), serie mensual de Mauna Loa.",
        "procedimiento": "Se promedio cada anio completo ({} a {}), se calculo el cambio frente al anio anterior y se ajusto una regresion lineal sobre los {} meses de la serie.".format(
            comp[0]["anio"], comp[-1]["anio"], len(co2)),
        "evidencia_titulo": "Aumento del promedio anual de CO2 frente al anio anterior (ppm)",
        "evidencia": [_ev(str(y), "{} ppm".format(_sg(d, 2)), min(d / mayor[1] * 100, 100)) for y, d in inc],
        "hallazgo": "El promedio anual pasa de {} ppm en {} a {} ppm en {}: {} de {} anios consecutivos son ascensos. La regresion mensual da {} ppm por anio (R² = {}); el mayor salto es {} ppm en {} y el menor {} ppm en {}.{}".format(
            fmt_dec(comp[0]["media"], 1), comp[0]["anio"], fmt_dec(comp[-1]["media"], 1), comp[-1]["anio"],
            suben, len(inc), fmt_dec(pend, 2), fmt_dec(r2, 2), _sg(mayor[1], 2), mayor[0], _sg(menor[1], 2), menor[0], txt_parcial),
        "interpretacion": "La concentracion de CO2 se acumula de forma continua: en ningun anio del periodo baja el promedio. El ritmo medio es de unos {} ppm por anio, con variaciones entre anios pero siempre positivo.".format(fmt_dec(media_inc, 1)),
        "utilidad": "Da una tasa de referencia para seguir cada anio si el CO2 acelera o se frena frente al ritmo observado.",
        "limitacion": "Es una sola estacion de medicion y un periodo corto; no permite repartir el aumento por pais ni por sector.",
    }

    # K2: estacionalidad del CO2
    est = _estacional(co2)
    i_max = int(np.argmax(est))
    i_min = int(np.argmin(est))
    amp = est[i_max] - est[i_min]
    escala = max(abs(e) for e in est)
    k2 = {
        "numero": 2,
        "titulo": "El CO2 sigue un ciclo anual cuyo vaiven es mayor que su crecimiento anual",
        "pregunta": "Que meses tienen el CO2 mas alto y mas bajo cada anio y que tan marcado es ese ciclo?",
        "variables": "mes y valor del CO2 atmosferico (ppm), anios completos {}-{}.".format(comp[0]["anio"], comp[-1]["anio"]),
        "procedimiento": "Para cada anio completo se resto el promedio del anio a cada mes (para quitar la tendencia) y se promedio esa desviacion por mes calendario.",
        "evidencia_titulo": "Desviacion media respecto al promedio anual, por mes (ppm)",
        "evidencia": [_ev(MESES[i], "{} ppm".format(_sg(est[i], 2)), abs(est[i]) / escala * 100) for i in range(12)],
        "hallazgo": "El maximo se da en {} ({} ppm sobre el promedio del anio) y el minimo en {} ({} ppm). La diferencia entre ambos es de {} ppm, unas {} veces el aumento anual medio ({} ppm).".format(
            MESES_LARGO[i_max], _sg(est[i_max], 2), MESES_LARGO[i_min], _sg(est[i_min], 2),
            fmt_dec(amp, 1), fmt_dec(amp / media_inc, 1), fmt_dec(media_inc, 1)),
        "interpretacion": "Dentro de cada anio el CO2 sube hasta {} y baja hasta {}, un ciclo regular que se repite todos los anios y es consistente con el ciclo de la vegetacion del hemisferio norte. Encima de ese ciclo se monta la tendencia ascendente.".format(
            MESES_LARGO[i_max], MESES_LARGO[i_min]),
        "utilidad": "Evita leer como 'aumento' o 'descenso' una diferencia entre meses que es solo estacional: para seguir la tendencia hay que comparar el mismo mes entre anios.",
        "limitacion": "El ciclo corresponde a la estacion de Mauna Loa (hemisferio norte); en otras latitudes el patron puede ser distinto.",
    }

    # K3: temperatura
    ga = [a for a in _anuales(S["gis"]["puntos"]) if a["completo"]]
    g = {a["anio"]: a["media"] for a in ga}
    top = max(g, key=g.get)
    dif = {y: g[y] - g[y - 1] for y in g if y - 1 in g}
    salto = max(dif, key=dif.get)
    j = pd.DataFrame(S["gis"]["puntos"], columns=["y", "m", "g"]).merge(
        pd.DataFrame(S["gcag"]["puntos"], columns=["y", "m", "c"]), on=["y", "m"])
    r_fuentes = float(j["g"].corr(j["c"]))
    dif_fuentes = float((j["g"] - j["c"]).mean())
    j2 = j.merge(pd.DataFrame(co2, columns=["y", "m", "co2"]), on=["y", "m"])
    r_co2 = float(j2["g"].corr(j2["co2"]))
    nina = next((e for e in eventos if "Nina" in e["evento"]), None)
    nino = next((e for e in eventos if "El Nino" in e["evento"] and e["tipo"] == "Fenomeno climatico"), None)
    ctx = ""
    bajos = [y for y in g if y > min(g) and g[y] < g[min(g)]]
    if nina and nino and bajos:
        ctx = " La caida de {} coincide con la fase La Nina documentada desde {} y el salto de {} con la transicion a El Nino ({}); es una coincidencia en el tiempo, no una prueba de causa.".format(
            " y ".join(str(y) for y in bajos), nina["fecha"], salto, nino["fecha"])
    k3 = {
        "numero": 3,
        "titulo": "La temperatura global sube a saltos, no al ritmo regular del CO2, y dos fuentes coinciden",
        "pregunta": "Como evoluciona la anomalia de temperatura global y coinciden las dos fuentes mensuales del dataset?",
        "variables": "anio, mes y valor de la anomalia de temperatura global de NASA GISTEMP y NOAA GCAG, y el CO2 mensual.",
        "procedimiento": "Se promedio la anomalia de GISTEMP por anio completo, se comparo cada anio con el anterior y se calculo la correlacion mensual entre las dos fuentes y con el CO2.",
        "evidencia_titulo": "Anomalia media anual GISTEMP (°C vs. base)",
        "evidencia": [_ev(str(y), "{} °C".format(fmt_dec(v, 2)), v / max(g.values()) * 100) for y, v in g.items()],
        "hallazgo": "La anomalia anual va de {} °C en {} a {} °C en {} (el maximo de la serie). El mayor salto es {} °C en {}. Las dos fuentes se mueven casi igual (correlacion mensual {}; GISTEMP queda {} °C por encima de GCAG en promedio), mientras la correlacion mensual con el CO2 es solo {}.".format(
            fmt_dec(g[min(g)], 2), min(g), fmt_dec(g[top], 2), top, _sg(dif[salto], 2), salto,
            fmt_dec(r_fuentes, 2), fmt_dec(dif_fuentes, 2), fmt_dec(r_co2, 2)),
        "interpretacion": "Mientras el CO2 sube de forma pareja, la temperatura global cambia en escalones: baja en los anios intermedios y sube con fuerza despues. Que dos fuentes distintas den la misma forma da confianza en el patron.{}".format(ctx),
        "utilidad": "Sugiere seguir la temperatura con ambas fuentes y no esperar que responda mes a mes al CO2; hay otros factores que mueven la serie.",
        "limitacion": "Son anomalias globales respecto a una base, no temperaturas absolutas ni locales, y {} anios no bastan para separar tendencia de variabilidad natural.".format(len(g)),
    }
    info = {"inc": inc, "media_inc": media_inc, "mayor": mayor, "g": g, "top": top, "pend": pend,
            "amp": amp, "i_max": i_max, "i_min": i_min}
    return [k1, k2, k3], info


def _interpretaciones(info):
    mayor = info["mayor"]
    v1 = ("La linea muestra el CO2 mes a mes: sube con un ritmo de {} ppm por anio y dibuja una ondulacion regular dentro de cada anio. "
          "Los rombos son los eventos externos documentados; en la serie no se ve una ruptura asociada a ellos."
          ).format(fmt_dec(info["pend"], 2))
    v2 = ("En el CO2 el maximo cae en {} y el minimo en {}: el vaiven anual es de unas {} ppm, unas {} veces el aumento anual. "
          "Se mide como desviacion frente al promedio del propio anio para separar la estacionalidad de la tendencia."
          ).format(MESES_LARGO[info["i_max"]], MESES_LARGO[info["i_min"]], fmt_dec(info["amp"], 1),
                   fmt_dec(info["amp"] / info["media_inc"], 1))
    v3 = ("Las barras comparan el promedio de cada anio: el CO2 crece siempre (mayor aumento {} ppm en {}). Los anios incompletos se marcan como parciales "
          "y no se comparan con anios completos.").format(_sg(mayor[1], 2), mayor[0])
    return {"v1": v1, "v2": v2, "v3": v3}


def _limitacion(anios):
    return {
        "titulo": "Series globales y de una sola estacion, sin variables locales como humedad o temperatura absoluta",
        "texto": ("Las series mensuales del dataset son tres: el CO2 de la estacion de Mauna Loa y dos anomalias de temperatura global. "
                  "Describen el planeta o un punto de medicion, no una ciudad ni una region, y la temperatura se expresa como anomalia "
                  "frente a una base, no como grados absolutos. El dataset no incluye humedad ni temperatura local, por lo que no es posible "
                  "analizar ventanas estacionales de calor o su relacion con la humedad. Con solo {} anios ({}-{}) tampoco se puede separar una "
                  "tendencia de largo plazo de la variabilidad natural ni atribuir un cambio a un evento concreto."
                  ).format(len(anios), min(anios), max(anios)),
    }


def _decision(info):
    g = info["g"]
    return {
        "titulo": "Seguir cada anio el aumento de CO2 y la anomalia de temperatura con ambas fuentes",
        "texto": ("Fijar como indicadores de seguimiento anual el aumento del promedio de CO2 de Mauna Loa (media del periodo {} ppm por anio, maximo {} ppm en {}) "
                  "y la anomalia anual de temperatura con GISTEMP y GCAG (maximo de la serie {} °C en {}). Se propone revisar el caso cuando un anio supere el mayor "
                  "aumento de CO2 observado o el maximo de anomalia, y comparar siempre el mismo mes entre anios para no confundir estacionalidad con tendencia."
                  ).format(fmt_dec(info["media_inc"], 1), fmt_dec(info["mayor"][1], 1), info["mayor"][0],
                           fmt_dec(g[info["top"]], 2), info["top"]),
        "sustento": "Sustento: visualizaciones 1 y 3 y los conocimientos evidentes 1 y 3.",
    }


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def construir(df, eventos=None):
    """Devuelve el dict completo para la pagina, o None si faltan las series mensuales."""
    if df is None or df.empty:
        return None
    S = _extraer(df)
    if not all(k in S for k in ("co2", "gis", "gcag")):
        return None
    anios = sorted({p[0] for s in S.values() for p in s["puntos"]})
    lista_ev = _eventos(eventos)
    conoc, info = _conocimientos(S, lista_ev)

    graficos = {
        "anios": anios,
        "series": [S[k] for k in ("co2", "gis", "gcag")],
        "eventos": lista_ev,
        "meses": MESES,
        "tendencias": {k: dict(zip(("pendiente", "intercepto", "r2"), _pendiente(S[k]["puntos"]))) for k in S},
    }
    n_reg = sum(len(s["puntos"]) for s in S.values())
    variables = [
        {"variable": "anio", "tipo": "Temporal", "uso": "Filtro 1: anio de analisis ({}-{}).".format(min(anios), max(anios))},
        {"variable": "mes", "tipo": "Temporal", "uso": "Ordena los registros dentro del anio; permite el perfil estacional."},
        {"variable": "Concentracion de CO2 atmosferico (ppm)", "tipo": "Numerica", "uso": "Serie mensual de NOAA GML (Mauna Loa): {} meses.".format(len(S["co2"]["puntos"]))},
        {"variable": "Anomalia de temperatura global, GISTEMP (°C)", "tipo": "Numerica", "uso": "Serie mensual de NASA GISS: {} meses; diferencia frente a una base.".format(len(S["gis"]["puntos"]))},
        {"variable": "Anomalia de temperatura global, GCAG (°C)", "tipo": "Numerica", "uso": "Serie mensual de NOAA NCEI: {} meses; segunda fuente para contrastar.".format(len(S["gcag"]["puntos"]))},
        {"variable": "fuente / fuente_tipo / periodicidad", "tipo": "Categorica", "uso": "Identifican cada serie (fuentes primarias, periodicidad mensual)."},
        {"variable": "eventos externos (fecha, evento, tipo)", "tipo": "Categorica / Temporal", "uso": "{} eventos documentados que se marcan sobre la serie de CO2.".format(len(lista_ev))},
    ]
    return {
        "anio_min": min(anios), "anio_max": max(anios), "n_registros_mensuales": n_reg,
        "n_eventos": len(lista_ev), "variables": variables,
        "conocimientos": conoc, "interpretaciones": _interpretaciones(info),
        "limitacion": _limitacion(anios), "decision": _decision(info),
        "graficos": graficos,
    }
