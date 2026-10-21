# -*- coding: utf-8 -*-
"""
ClimaTec - Etapa 4 / Dimension Relacional Multidimensional.

Cruza las dimensiones ya analizadas (poblacional, territorial y temporal) y los
eventos externos documentados, a partir del dataset limpio (clima_limpio.csv) y
de eventos_externos_muestra.csv:

  - poblacion vs indicador por pais (correlacion, recta log-log, posicion de
    Colombia respecto a lo esperado por su tamano), para cada anio e indicador;
  - evolucion 2020-2024 de cada region en base 100 (territorio x tiempo);
  - variacion anual del CO2 mundial frente a los eventos externos (tiempo x evento);
  - los tres conocimientos evidentes, la limitacion y la decision, con cifras
    calculadas en vivo.

Ninguna cifra se escribe a mano: si cambia el CSV, cambia la pagina. Las
graficas se dibujan en el navegador (SVG) con el JSON que devuelve construir().
"""

import numpy as np
import pandas as pd

from poblacional import GRUPOS, REGIONES_ES, fmt_dec, fmt_int, fmt_pct, fmt_pob, _asignar_grupo

PAIS_FOCO = "Colombia"
MUNDO = "World"
IND_POB = "Poblacion"
IND_VAR_CO2 = "Variacion anual de CO2"
IND_CO2 = "Emisiones de CO2 (total)"

# (indicador del dataset, etiqueta, unidad corta, tipo)
INDICADORES = [
    ("Emisiones de CO2 (total)", "CO2 total", "Mt CO2", "total"),
    ("Gases de efecto invernadero (total)", "GEI total", "Mt eq. CO2", "total"),
    ("Consumo de energia primaria", "Energia primaria total", "TWh", "total"),
    ("Emisiones de CO2 per capita", "CO2 per capita", "t CO2/persona", "per capita"),
    ("GEI per capita (sin uso del suelo)", "GEI per capita", "t eq. CO2/persona", "per capita"),
    ("Consumo de energia per capita", "Energia per capita", "kWh/persona", "per capita"),
]


def _signo(x, d=1):
    if abs(x) < 0.5 * 10 ** (-d):
        x = 0.0
    return ("+" if x > 0 else "") + fmt_dec(x, d) + "%"


def _ev(etiqueta, valor, pct):
    return {"etiqueta": etiqueta, "valor": valor, "pct": pct, "pct_txt": fmt_pct(pct)}


def _r(x, d=2):
    return None if x is None or not np.isfinite(x) else round(float(x), d)


def _sig(x, cifras=4):
    """Redondea a cifras significativas para aligerar el JSON."""
    if x == 0 or not np.isfinite(x):
        return 0
    return float("{:.{n}g}".format(float(x), n=cifras))


# ---------------------------------------------------------------------------
# Poblacion vs indicador (por pais, anio e indicador)
# ---------------------------------------------------------------------------
def _dispersion(df, anios, nombres):
    nac = df[df["nivel_geografico"] == "Nacional"]
    salida = {}
    for ind, etq, unidad, tipo in INDICADORES:
        por_anio = {}
        for a in anios:
            n_a = nac[nac["anio"] == a]
            pob = n_a[n_a["indicador"] == IND_POB].drop_duplicates("entidad").set_index("entidad")["valor"]
            val = n_a[n_a["indicador"] == ind].drop_duplicates("entidad").set_index("entidad")["valor"]
            j = pd.concat([pob, val], axis=1, keys=["p", "v"]).dropna()
            j = j[(j["p"] > 0) & (j["v"] > 0)]
            if len(j) < 10:
                continue
            lp, lv = np.log10(j["p"]), np.log10(j["v"])
            pend, inter = np.polyfit(lp, lv, 1)
            pearson = float(np.corrcoef(lp, lv)[0, 1])
            spearman = float(j["p"].rank().corr(j["v"].rank()))
            pred = inter + pend * lp
            resid = lv - pred

            foco = None
            if PAIS_FOCO in j.index:
                rk = int(j["v"].rank(ascending=False)[PAIS_FOCO])
                foco = {
                    "pob": float(j.loc[PAIS_FOCO, "p"]),
                    "valor": float(j.loc[PAIS_FOCO, "v"]),
                    "razon": float(10 ** resid[PAIS_FOCO]),
                    "puesto": rk, "de": int(len(j)),
                }
            # paises con mayor valor respecto a lo esperado por su tamano (>= 1 M de habitantes)
            grandes = resid[j["p"] >= 1e6].sort_values(ascending=False)
            sobre = [{"entidad": e, "razon": float(10 ** grandes[e])} for e in grandes.index[:3]]

            puntos = [[nombres.index(e), _sig(j.loc[e, "p"], 4), _sig(j.loc[e, "v"], 4),
                       GRUPOS.index(next(g for g in GRUPOS if g[0] == _asignar_grupo(j.loc[e, "p"])))]
                      for e in j.index]
            por_anio[str(a)] = {
                "n": int(len(j)), "spearman": _r(spearman, 3), "pearson_log": _r(pearson, 3),
                "pendiente": _r(pend, 3), "intercepto": _r(inter, 4),
                "foco": foco, "sobre": sobre, "puntos": puntos,
            }
        salida[ind] = por_anio
    return salida


# ---------------------------------------------------------------------------
# Regiones en base 100 (territorio x tiempo)
# ---------------------------------------------------------------------------
def _regiones_base100(df, anios):
    reg = df[df["nivel_geografico"] == "Regional"]
    salida = {}
    for ind, _, _, _ in INDICADORES + [(IND_POB, "Poblacion", "personas", "total")]:
        series = []
        for entidad, g in reg[reg["indicador"] == ind].groupby("entidad"):
            g = g.drop_duplicates("anio").set_index("anio")["valor"].reindex(anios)
            if g.isna().any() or g.iloc[0] == 0:
                continue
            base = float(g.iloc[0])
            series.append({
                "entidad": REGIONES_ES.get(entidad, entidad),
                "base100": [round(float(v) / base * 100, 2) for v in g.values],
                "valores": [_sig(v, 5) for v in g.values],
                "cambio_pct": round((float(g.iloc[-1]) / base - 1) * 100, 2),
            })
        salida[ind] = series
    return salida


# ---------------------------------------------------------------------------
# Tiempo x eventos
# ---------------------------------------------------------------------------
def _eventos(eventos):
    if eventos is None or eventos.empty:
        return []
    ev = eventos.copy()
    ev["anio"] = ev["fecha"].astype(str).str[:4].astype(int)
    return [{"anio": int(r.anio), "fecha": str(r.fecha), "evento": str(r.evento),
             "tipo": str(r.tipo), "ambito": str(r.ambito)} for r in ev.sort_values("fecha").itertuples()]


def _mundo(df, anios):
    w = df[df["entidad"] == MUNDO]
    var = w[w["indicador"] == IND_VAR_CO2].drop_duplicates("anio").set_index("anio")["valor"]
    tot = w[w["indicador"] == IND_CO2].drop_duplicates("anio").set_index("anio")["valor"]
    return [{"anio": int(a),
             "variacion": None if a not in var.index else round(float(var[a]), 2),
             "co2": None if a not in tot.index else round(float(tot[a]), 1)} for a in anios]


# ---------------------------------------------------------------------------
# Conocimientos evidentes
# ---------------------------------------------------------------------------
def _conocimientos(disp, regs, mundo, eventos, anio):
    a = str(anio)
    co2 = disp[IND_CO2][a]
    co2pc = disp["Emisiones de CO2 per capita"][a]
    en = disp["Consumo de energia primaria"][a]

    k1 = {
        "numero": 1,
        "titulo": "Mas habitantes implica mas emisiones totales, pero no mas emisiones por persona",
        "pregunta": "Existe relacion entre el tamano poblacional de un pais y sus emisiones y consumo de energia?",
        "variables": "Poblacion, Emisiones de CO2 (total), Consumo de energia primaria y Emisiones de CO2 per capita, por pais en {}.".format(anio),
        "procedimiento": "Se cruzaron los paises que tienen poblacion y el indicador en {}, se calculo la correlacion de rangos de Spearman y la correlacion de Pearson sobre logaritmos (escala log-log) para no dejar que los paises enormes dominen el resultado.".format(anio),
        "evidencia_titulo": "Correlacion de Spearman con la poblacion ({} paises, {})".format(co2["n"], anio),
        "evidencia": [
            _ev("CO2 total", fmt_dec(co2["spearman"], 2), abs(co2["spearman"]) * 100),
            _ev("Energia primaria total", fmt_dec(en["spearman"], 2), abs(en["spearman"]) * 100),
            _ev("CO2 per capita", fmt_dec(co2pc["spearman"], 2), abs(co2pc["spearman"]) * 100),
        ],
        "hallazgo": "La correlacion entre poblacion y CO2 total es {} (Pearson log-log {}) y con la energia primaria {}. Con el CO2 per capita es {}: practicamente no hay relacion util. En la recta log-log, 10 veces mas habitantes se asocian con unas {} veces mas CO2.".format(
            fmt_dec(co2["spearman"], 2), fmt_dec(co2["pearson_log"], 2), fmt_dec(en["spearman"], 2),
            fmt_dec(co2pc["spearman"], 2), fmt_dec(10 ** co2["pendiente"], 1)),
        "interpretacion": "El tamano poblacional explica buena parte del volumen total de emisiones, pero no la intensidad por persona: un pais pequeno puede emitir mucho por habitante y uno grande, poco. Por eso los totales y los per capita cuentan historias distintas.",
        "utilidad": "Da una referencia de cuanto deberia emitir un pais segun su tamano y permite ubicar a los que estan por encima o por debajo de lo esperado.",
        "limitacion": "Es una asociacion entre paises en un anio; no demuestra que la poblacion cause las emisiones ni que el patron se repita dentro de cada pais.",
    }

    # K2: emisiones vs poblacion por region (territorio x tiempo)
    pob_r = {s["entidad"]: s for s in regs[IND_POB]}
    co2_r = {s["entidad"]: s for s in regs[IND_CO2]}
    filas = []
    for ent, s in co2_r.items():
        if ent in pob_r:
            filas.append({"entidad": ent, "co2": s["cambio_pct"], "pob": pob_r[ent]["cambio_pct"],
                          "dif": round(s["cambio_pct"] - pob_r[ent]["cambio_pct"], 2)})
    filas.sort(key=lambda r: r["dif"], reverse=True)
    n_mas = sum(1 for r in filas if r["dif"] > 0)
    sube, baja = filas[0], filas[-1]
    ini, fin = 2020, anio
    k2 = {
        "numero": 2,
        "titulo": "Las emisiones crecen a ritmos muy distintos segun la region y solo en algunas superan a la poblacion",
        "pregunta": "Entre {} y {}, las emisiones de cada region crecieron mas o menos que su poblacion?".format(ini, fin),
        "variables": "entidad (regiones), anio, Emisiones de CO2 (total) y Poblacion.",
        "procedimiento": "Para cada region se llevo el CO2 total y la poblacion a base 100 en {} y se compararon los cambios acumulados hasta {} (diferencia en puntos porcentuales).".format(ini, fin),
        "evidencia_titulo": "Cambio de CO2 menos cambio de poblacion, {}-{} (puntos porcentuales)".format(ini, fin),
        "evidencia": [_ev(r["entidad"], _signo(r["dif"], 1).replace("%", " pp"), min(abs(r["dif"]), 100)) for r in filas],
        "hallazgo": "En {} de las {} regiones el CO2 crecio mas que su poblacion. {} muestra la mayor diferencia ({}: CO2 {} frente a poblacion {}) y {} la menor ({}).".format(
            n_mas, len(filas), sube["entidad"], _signo(sube["dif"], 1).replace("%", " pp"),
            _signo(sube["co2"], 1), _signo(sube["pob"], 1), baja["entidad"], _signo(baja["dif"], 1).replace("%", " pp")),
        "interpretacion": "La emision por persona no se mueve igual en todas las regiones: donde el CO2 supera el ritmo poblacional, cada habitante esta emitiendo mas que en {}; donde lo iguala o no lo alcanza, la intensidad baja.".format(ini),
        "utilidad": "Permite elegir en que regiones conviene revisar politicas de intensidad de emisiones y en cuales el aumento es sobre todo demografico.",
        "limitacion": "Se compara con {} como base, un anio con un choque en las emisiones mundiales; parte de la diferencia refleja la recuperacion posterior y no una tendencia estructural.".format(ini),
    }

    # K3: tiempo x eventos
    vs = [m for m in mundo if m["variacion"] is not None]
    ev_por_anio = {}
    for e in eventos:
        ev_por_anio.setdefault(e["anio"], []).append(e)
    caida = min(vs, key=lambda m: m["variacion"])
    sig = [m for m in vs if m["anio"] > caida["anio"]]
    desacel = all(sig[i]["variacion"] >= sig[i + 1]["variacion"] for i in range(1, len(sig) - 1)) if len(sig) > 2 else False
    ult = vs[-1]
    n_ev = len(eventos)
    pico = max(sig, key=lambda m: m["variacion"]) if sig else None
    k3 = {
        "numero": 3,
        "titulo": "El CO2 mundial se recupera tras {} y desde entonces crece cada vez menos, sin cambios visibles en los anios con eventos".format(caida["anio"]),
        "pregunta": "Cambia la variacion anual del CO2 mundial en los anios en que hay eventos externos documentados?",
        "variables": "Variacion anual de CO2 (entidad World), anio y eventos externos (fecha, evento, tipo).",
        "procedimiento": "Se ordeno la variacion anual del CO2 mundial por anio y se ubicaron al lado los {} eventos del archivo de eventos externos segun el anio de su fecha.".format(n_ev),
        "evidencia_titulo": "Variacion anual del CO2 mundial y eventos por anio",
        "evidencia": [_ev("{} · {} evento(s)".format(m["anio"], len(ev_por_anio.get(m["anio"], []))),
                          _signo(m["variacion"], 2), min(abs(m["variacion"]) * 10, 100)) for m in vs],
        "hallazgo": "La mayor variacion es {} en {}, seguida de {} en {}; despues baja a {} en {}. {} tiene {} evento(s) en los datos, y en los anios con COP o El Nino ({}) la variacion sigue bajando gradualmente, sin un salto distinto del patron general.".format(
            _signo(caida["variacion"], 2), caida["anio"], _signo(pico["variacion"], 2) if pico else "n/d",
            pico["anio"] if pico else "n/d", _signo(ult["variacion"], 2), ult["anio"], caida["anio"],
            len(ev_por_anio.get(caida["anio"], [])), ", ".join(str(a) for a in sorted(ev_por_anio) if a > caida["anio"])),
        "interpretacion": "Los eventos documentados ayudan a contar el contexto, pero en estos datos no explican por si solos los cambios del CO2 mundial: el mayor movimiento ocurre en un anio con un solo evento climatico y el resto de los anios cambian poco entre si.",
        "utilidad": "Evita atribuir variaciones a un evento concreto sin mas evidencia y orienta a buscar datos mensuales y por pais para probar cualquier relacion.",
        "limitacion": "Son {} eventos curados y {} anios de variacion: es una coincidencia en el tiempo, no una prueba causal, y el archivo no incluye otros choques que tambien afectan al CO2.".format(n_ev, len(vs)),
    }
    return [k1, k2, k3], {"filas_regiones": filas, "desacelera": desacel}


def _interpretaciones(disp, regs, mundo, anio):
    a = str(anio)
    co2 = disp[IND_CO2][a]
    foco = co2["foco"]
    v1 = ("Cada punto es un pais. La nube sube de izquierda a derecha: los paises con mas habitantes emiten mas CO2 en total "
          "(Spearman {}). La recta marca lo esperado segun el tamano; {} queda {} de ella ({} veces lo esperado).").format(
              fmt_dec(co2["spearman"], 2), PAIS_FOCO,
              "por debajo" if foco and foco["razon"] < 1 else "por encima",
              fmt_dec(foco["razon"], 2) if foco else "n/d")
    filas = sorted(regs[IND_CO2], key=lambda s: s["cambio_pct"])
    v2 = ("Con todas las regiones en base 100, {} crece mas ({}) y {} menos ({}) entre {} y {}. Las lineas se abren con el tiempo: "
          "el crecimiento relativo difiere mucho entre territorios aunque se mida en la misma escala.").format(
              filas[-1]["entidad"], _signo(filas[-1]["cambio_pct"], 1), filas[0]["entidad"],
              _signo(filas[0]["cambio_pct"], 1), 2020, anio)
    vs = [m for m in mundo if m["variacion"] is not None]
    caida = min(vs, key=lambda m: m["variacion"])
    v3 = ("Las barras muestran el cambio anual del CO2 mundial y los marcadores los eventos del anio. El mayor movimiento es {} en {}; "
          "desde entonces el cambio es positivo y cada vez menor. Los anios con eventos no se separan del patron general.").format(
              _signo(caida["variacion"], 2), caida["anio"])
    return {"v1": v1, "v2": v2, "v3": v3}


def _limitacion(disp, anios, n_eventos):
    return {
        "titulo": "Asociaciones entre pocos anios y pocos eventos, no relaciones causales",
        "texto": ("El cruce de dimensiones se apoya en {} anios ({}-{}) y en {} eventos curados manualmente, y compara paises entre si, no "
                  "territorios internos ni series mensuales por pais. Las correlaciones describen que variables se mueven juntas; "
                  "no prueban que una cause la otra, y la coincidencia de un evento con una variacion del CO2 mundial puede deberse a "
                  "otros factores que el dataset no contiene."
                  ).format(len(anios), min(anios), max(anios), n_eventos),
    }


def _decision(disp, regs, anio):
    a = str(anio)
    co2 = disp[IND_CO2][a]
    foco = co2["foco"]
    sobre = co2["sobre"]
    nombres = ", ".join("{} ({} veces)".format(s["entidad"], fmt_dec(s["razon"], 1)) for s in sobre)
    texto = ("Usar la relacion poblacion-emisiones como linea base: comparar cada pais con lo que se esperaria por su tamano y revisar primero "
             "los que se alejan mas hacia arriba. En {} (paises de mas de 1 millon de habitantes) los tres mas alejados son {}. ").format(anio, nombres)
    if foco:
        texto += ("{} queda en el puesto {} de {} en emisiones totales y emite {} veces lo esperado por su poblacion, "
                  "por lo que no seria prioridad por tamano de emisiones; su seguimiento puede centrarse en tendencia y eventos.").format(
                      PAIS_FOCO, foco["puesto"], foco["de"], fmt_dec(foco["razon"], 2))
    return {
        "titulo": "Priorizar la revision de paises segun su distancia a la relacion poblacion-emisiones",
        "texto": texto,
        "sustento": "Sustento: visualizacion 1 y conocimiento evidente 1.",
    }


def construir(df, eventos=None):
    if df is None or df.empty:
        return None
    anios_pob = sorted(int(a) for a in df[df["indicador"] == IND_POB]["anio"].dropna().unique())
    if len(anios_pob) < 2:
        return None
    anio_ref = max(anios_pob)
    nombres = sorted(df[(df["nivel_geografico"] == "Nacional") & (df["indicador"] == IND_POB)]["entidad"].unique())

    disp = _dispersion(df, anios_pob, nombres)
    if IND_CO2 not in disp or str(anio_ref) not in disp[IND_CO2]:
        return None
    regs = _regiones_base100(df, anios_pob)
    mundo = _mundo(df, anios_pob)
    lista_ev = _eventos(eventos)
    conoc, extra = _conocimientos(disp, regs, mundo, lista_ev, anio_ref)

    graficos = {
        "anios": anios_pob, "anio_ref": anio_ref, "pais_foco": PAIS_FOCO,
        "indicadores": [{"clave": i, "nombre": e, "unidad": u, "tipo": t} for i, e, u, t in INDICADORES],
        "grupos": [g[0] for g in GRUPOS], "nombres": nombres,
        "dispersion": disp, "regiones": regs, "mundo": mundo, "eventos": lista_ev,
    }
    variables = [
        {"variable": "entidad / nivel_geografico", "tipo": "Categorica", "uso": "Territorio: paises (Nacional), regiones (Regional) y el agregado mundial."},
        {"variable": "anio", "tipo": "Temporal", "uso": "Filtro 1: anio de la relacion entre poblacion e indicadores ({}-{}).".format(min(anios_pob), max(anios_pob))},
        {"variable": "Poblacion", "tipo": "Numerica", "uso": "Tamano de cada pais o region; eje horizontal de la visualizacion 1."},
        {"variable": "Indicadores totales", "tipo": "Numerica", "uso": "CO2 total, GEI total y energia primaria; miden el volumen de cada territorio."},
        {"variable": "Indicadores per capita", "tipo": "Numerica", "uso": "CO2, GEI y energia por habitante; miden la intensidad. Filtro 2 elige el indicador."},
        {"variable": "Variacion anual de CO2", "tipo": "Numerica", "uso": "Cambio porcentual anual del CO2 mundial; se cruza con los eventos."},
        {"variable": "eventos externos (fecha, evento, tipo, ambito)", "tipo": "Categorica / Temporal", "uso": "{} eventos documentados (ENSO, COP, emergencias) ubicados por anio.".format(len(lista_ev))},
    ]
    return {
        "anio_ref": anio_ref, "n_eventos": len(lista_ev), "variables": variables,
        "conocimientos": conoc, "interpretaciones": _interpretaciones(disp, regs, mundo, anio_ref),
        "limitacion": _limitacion(disp, anios_pob, len(lista_ev)),
        "decision": _decision(disp, regs, anio_ref),
        "graficos": graficos,
        "total_registros": int(len(df)),
    }
