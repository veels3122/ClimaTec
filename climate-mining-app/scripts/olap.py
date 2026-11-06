# -*- coding: utf-8 -*-
"""
ClimaTec - Etapa 5 / Motor de consultas OLAP sobre el modelo estrella (SQLite).

Traduce una peticion multidimensional (atributo de filas, atributo de columnas,
medida y filtros) a una consulta en estrella sobre data/dw/climatec_dw.sqlite.
Es lo que usan las cuatro vistas de Flask (endpoint /api/etapa5/olap) y los
ejemplos de la pagina de operaciones.

    Drill-down / roll-up -> cambiar el atributo de filas o columnas a otro nivel
                            de la misma jerarquia (p. ej. region -> pais, anio -> mes).
    Slice                -> un filtro con un solo valor en una dimension.
    Dice                 -> filtros con varios valores en dos o mas dimensiones.
    Pivot                -> intercambiar el atributo de filas y el de columnas.

Las medidas se recalculan en SQL en cada nivel (SUM, AVG, proporciones con
numerador y denominador, COUNT DISTINCT); los totales de filas, columnas y el
total general salen de consultas propias, nunca de sumar celdas ya calculadas.
Todos los nombres de atributos y medidas pasan por listas blancas y los valores
de los filtros se envian como parametros.
"""

import sqlite3

JOINS = ("FROM hechos_observacion h "
         "JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo "
         "JOIN dim_geografia g ON g.id_geo = h.id_geo "
         "JOIN dim_indicador i ON i.id_indicador = h.id_indicador "
         "JOIN dim_fuente f ON f.id_fuente = h.id_fuente")

# atributo -> (dimension, jerarquia, clave SQL, etiqueta SQL, requiere mes)
ATRIBUTOS = {
    "anio": ("Tiempo", "Anio", "t.anio", "CAST(t.anio AS TEXT)", False),
    "semestre": ("Tiempo", "Semestre", "t.anio * 10 + t.semestre", "'S' || t.semestre || ' ' || t.anio", True),
    "trimestre": ("Tiempo", "Trimestre", "t.anio * 10 + t.trimestre", "'T' || t.trimestre || ' ' || t.anio", True),
    "mes": ("Tiempo", "Mes", "t.anio * 100 + t.mes", "t.nombre_mes || ' ' || t.anio", True),
    "mes_del_anio": ("Tiempo", "Mes del anio", "t.mes", "t.nombre_mes", True),
    "nivel": ("Geografia", "Nivel geografico", "g.nivel_geografico", "g.nivel_geografico", False),
    "region": ("Geografia", "Region", "g.region_es", "g.region_es", False),
    "pais": ("Geografia", "Pais", "g.entidad", "g.entidad", False),
    "territorio": ("Geografia", "Territorio", "g.entidad",
                   "CASE WHEN g.entidad = 'World' THEN 'Mundo' WHEN g.nivel_geografico = 'Regional' "
                   "THEN g.region_es ELSE g.entidad END", False),
    "categoria": ("Indicador", "Categoria", "i.categoria", "i.categoria", False),
    "indicador": ("Indicador", "Indicador", "i.indicador", "i.indicador", False),
    "tipo_fuente": ("Fuente", "Tipo de fuente", "f.fuente_tipo", "f.fuente_tipo", False),
    "proveedor": ("Fuente", "Proveedor", "f.proveedor", "f.proveedor", False),
    "fuente": ("Fuente", "Fuente", "f.fuente", "f.fuente", False),
}

MEDIDAS = {
    "n": ("Numero de registros", "SUM(h.n_registros)", "hechos"),
    "at": ("Registros atipicos", "SUM(h.atipico)", "hechos"),
    "pat": ("% de atipicos", "100.0 * SUM(h.atipico) / SUM(h.n_registros)", "%"),
    "z": ("Valor z promedio", "AVG(h.valor_z)", "z"),
    "suma": ("Valor sumado", "SUM(h.valor)", None),
    "prom": ("Valor promedio", "AVG(h.valor)", None),
    "paises": ("Paises con dato", "COUNT(DISTINCT CASE WHEN g.nivel_geografico = 'Nacional' THEN g.id_geo END)", "paises"),
}

# Jerarquias para drill-down / roll-up (de general a detallado).
JERARQUIAS = {
    "Tiempo": ["anio", "semestre", "trimestre", "mes"],
    "Geografia": ["nivel", "region", "pais"],
    "Indicador": ["categoria", "indicador"],
    "Fuente": ["tipo_fuente", "proveedor", "fuente"],
}


class ErrorConsulta(ValueError):
    pass


def _filtros(filtros):
    """filtros: {atributo: [valores]} -> (sql WHERE, params, descripcion)."""
    partes, params, desc = [], [], []
    for attr, valores in (filtros or {}).items():
        if attr not in ATRIBUTOS:
            raise ErrorConsulta("Atributo de filtro no valido: {}".format(attr))
        valores = [v for v in valores if v not in (None, "")]
        if not valores:
            continue
        clave = ATRIBUTOS[attr][2]
        if len(valores) == 1:
            partes.append("{} = ?".format(clave))
        else:
            partes.append("{} IN ({})".format(clave, ", ".join("?" * len(valores))))
        params.extend(valores)
        desc.append({"atributo": attr, "nombre": ATRIBUTOS[attr][1], "valores": valores,
                     "operacion": "slice" if len(valores) == 1 else "dice"})
    return partes, params, desc


def _medida_sql(medida, con, filtros):
    if medida == "valor":
        inds = (filtros or {}).get("indicador") or []
        if len(inds) != 1:
            raise ErrorConsulta("La medida Valor necesita exactamente un indicador (slice por indicador): "
                                "no se suman unidades distintas.")
        fila = con.execute("SELECT agregacion, unidad FROM dim_indicador WHERE indicador = ?", (inds[0],)).fetchone()
        if not fila:
            raise ErrorConsulta("Indicador desconocido.")
        agr, unidad = fila
        sql = "SUM(h.valor)" if agr == "suma" else "AVG(h.valor)"
        return sql, "Valor ({})".format("suma" if agr == "suma" else "promedio"), unidad, agr
    if medida not in MEDIDAS:
        raise ErrorConsulta("Medida no valida: {}".format(medida))
    nombre, sql, unidad = MEDIDAS[medida]
    if unidad is None:
        inds = (filtros or {}).get("indicador") or []
        unidad = None
        if len(inds) == 1:
            r = con.execute("SELECT unidad FROM dim_indicador WHERE indicador = ?", (inds[0],)).fetchone()
            unidad = r[0] if r else None
    return sql, nombre, unidad, None


def consulta(ruta_db, filas, columnas=None, medida="n", filtros=None, limite=400):
    """Ejecuta la consulta OLAP y devuelve celdas, totales y el SQL usado."""
    if filas not in ATRIBUTOS:
        raise ErrorConsulta("Atributo de filas no valido: {}".format(filas))
    if columnas and columnas not in ATRIBUTOS:
        raise ErrorConsulta("Atributo de columnas no valido: {}".format(columnas))
    if columnas == filas:
        columnas = None
    con = sqlite3.connect(ruta_db)
    try:
        m_sql, m_nombre, m_unidad, m_agr = _medida_sql(medida, con, filtros)
        where, params, desc = _filtros(filtros)
        where = ["h.id_tiempo <> -1"] + where
        for a in (filas, columnas):
            if a and ATRIBUTOS[a][4]:
                where.append("t.mes > 0")
        w = " WHERE " + " AND ".join(dict.fromkeys(where))
        fk, fl = ATRIBUTOS[filas][2], ATRIBUTOS[filas][3]
        if columnas:
            ck, cl = ATRIBUTOS[columnas][2], ATRIBUTOS[columnas][3]
            sql = ("SELECT {fk} AS fk, {fl} AS fl, {ck} AS ck, {cl} AS cl, {m} AS v, SUM(h.n_registros) AS n "
                   "{j}{w} GROUP BY fk, ck ORDER BY fk, ck").format(fk=fk, fl=fl, ck=ck, cl=cl, m=m_sql, j=JOINS, w=w)
        else:
            sql = ("SELECT {fk} AS fk, {fl} AS fl, NULL AS ck, NULL AS cl, {m} AS v, SUM(h.n_registros) AS n "
                   "{j}{w} GROUP BY fk ORDER BY fk").format(fk=fk, fl=fl, m=m_sql, j=JOINS, w=w)
        filas_res = con.execute(sql, params).fetchall()
        etq_f, etq_c, celdas, conteos = {}, {}, {}, {}
        for a, b, c, d, v, n in filas_res:
            etq_f[a] = b
            if columnas:
                etq_c[c] = d
            celdas["{}|{}".format(a, c if columnas else "")] = v
            conteos["{}|{}".format(a, c if columnas else "")] = n
        # Totales recalculados con su propia consulta.
        sql_tf = "SELECT {fk}, {m} {j}{w} GROUP BY {fk}".format(fk=fk, m=m_sql, j=JOINS, w=w)
        tot_f = {k: v for k, v in con.execute(sql_tf, params).fetchall()}
        tot_c = {}
        if columnas:
            sql_tc = "SELECT {ck}, {m} {j}{w} GROUP BY {ck}".format(ck=ck, m=m_sql, j=JOINS, w=w)
            tot_c = {k: v for k, v in con.execute(sql_tc, params).fetchall()}
        tot = con.execute("SELECT {m}, SUM(h.n_registros) {j}{w}".format(m=m_sql, j=JOINS, w=w), params).fetchone()
    finally:
        con.close()
    claves_f = list(etq_f.keys())[:limite]
    claves_c = list(etq_c.keys())[:limite]
    return {
        "filas": [{"clave": k, "etiqueta": etq_f[k]} for k in claves_f],
        "columnas": [{"clave": k, "etiqueta": etq_c[k]} for k in claves_c],
        "celdas": celdas,
        "conteos": conteos,
        "total_filas": {str(k): v for k, v in tot_f.items()},
        "total_columnas": {str(k): v for k, v in tot_c.items()},
        "total": tot[0],
        "n_hechos": tot[1] or 0,
        "medida": {"clave": medida, "nombre": m_nombre, "unidad": m_unidad, "agregacion": m_agr},
        "atributo_filas": {"clave": filas, "dimension": ATRIBUTOS[filas][0], "nivel": ATRIBUTOS[filas][1]},
        "atributo_columnas": ({"clave": columnas, "dimension": ATRIBUTOS[columnas][0], "nivel": ATRIBUTOS[columnas][1]}
                              if columnas else None),
        "filtros": desc,
        "sql": sql.replace("?", "{}").format(*["'{}'".format(p) for p in params]) if params else sql,
    }


def valores(ruta_db, atributo, filtros=None):
    """Miembros disponibles de un atributo (para llenar los filtros)."""
    if atributo not in ATRIBUTOS:
        raise ErrorConsulta("Atributo no valido")
    k, l = ATRIBUTOS[atributo][2], ATRIBUTOS[atributo][3]
    where, params, _ = _filtros(filtros)
    where = ["h.id_tiempo <> -1"] + where + (["t.mes > 0"] if ATRIBUTOS[atributo][4] else [])
    con = sqlite3.connect(ruta_db)
    try:
        r = con.execute("SELECT DISTINCT {k}, {l} {j} WHERE {w} ORDER BY {k}".format(
            k=k, l=l, j=JOINS, w=" AND ".join(where)), params).fetchall()
    finally:
        con.close()
    return [{"clave": a, "etiqueta": b} for a, b in r]


# ---------------------------------------------------------------------------
# Ejemplos aplicados al proyecto (pagina "Operaciones multidimensionales").
# Cada ejemplo ejecuta consultas reales sobre el modelo.
# ---------------------------------------------------------------------------
def _f(x, d=1):
    if x is None:
        return "—"
    s = "{:,.{d}f}".format(x, d=d)
    return s.replace(",", "#").replace(".", ",").replace("#", ".")


def _tabla(r, fmt, limite=None, orden_valor=False):
    """Convierte un resultado en filas para mostrar (con columnas si las hay)."""
    cols = r["columnas"]
    filas = r["filas"]
    if orden_valor and not cols:
        filas = sorted(filas, key=lambda f: -(r["celdas"].get("{}|".format(f["clave"])) or 0))
    if limite:
        filas = filas[:limite]
    cab = [r["atributo_filas"]["nivel"]] + ([c["etiqueta"] for c in cols] if cols else [r["medida"]["nombre"]])
    cuerpo = []
    for f in filas:
        if cols:
            cuerpo.append([f["etiqueta"]] + [fmt(r["celdas"].get("{}|{}".format(f["clave"], c["clave"]))) for c in cols])
        else:
            cuerpo.append([f["etiqueta"], fmt(r["celdas"].get("{}|".format(f["clave"])))])
    pie = None
    if cols:
        pie = ["Total"] + [fmt(r["total_columnas"].get(str(c["clave"]))) for c in cols]
    else:
        pie = ["Total", fmt(r["total"])]
    return {"cab": cab, "filas": cuerpo, "pie": pie, "sql": r["sql"], "n": r["n_hechos"]}


def ejemplos(ruta_db):
    co2 = "Emisiones de CO2 (total)"
    ej = []

    # 1. Drill-down Region -> Pais (pregunta 2)
    antes = consulta(ruta_db, "region", None, "valor", {"indicador": [co2], "anio": [2024], "nivel": ["Nacional"]})
    despues = consulta(ruta_db, "pais", None, "valor", {"indicador": [co2], "anio": [2024], "nivel": ["Nacional"],
                                                         "region": ["Sudamerica"]})
    sa = antes["celdas"].get("Sudamerica|")
    hijos = sorted(((v, k.split("|")[0]) for k, v in despues["celdas"].items()), reverse=True)
    pos = [n for v, n in hijos].index("Colombia") + 1 if any(n == "Colombia" for v, n in hijos) else None
    ej.append({
        "id": "drilldown", "operacion": "Drill-down", "pregunta": 2, "vista": 2,
        "titulo": "De la region Sudamerica a sus paises",
        "dimensiones": "Geografia (Region → Pais), Indicador (slice: Emisiones de CO2), Tiempo (slice: 2024)",
        "medidas": "Valor sumado (Mt CO2) y participacion %",
        "nivel": "Antes: nivel Region. Despues: nivel Pais, con el filtro Region = Sudamerica.",
        "procedimiento": "Se repite la consulta en estrella cambiando el atributo de agrupacion de g.region_es a g.entidad y "
                         "agregando el filtro de la region elegida. La suma se recalcula en SQL para cada pais.",
        "tablas": [("Antes · nivel Region", _tabla(antes, lambda v: _f(v, 1), orden_valor=True)),
                   ("Despues · paises de Sudamerica", _tabla(despues, lambda v: _f(v, 1), limite=8, orden_valor=True))],
        "interpretacion": "Sudamerica suma {} Mt; al bajar un nivel, {} aporta {} y Colombia queda en el puesto {} de {}. La suma de "
                          "los paises es igual al valor de la region ({} Mt), lo que confirma que el drill-down recalcula sin perder datos.".format(
                              _f(sa, 1), hijos[0][1], _f(hijos[0][0] / despues["total"] * 100, 1) + "%", pos, len(hijos),
                              _f(despues["total"], 1)),
    })

    # 2a. Roll-up Mes -> Anio (pregunta 1)
    antes = consulta(ruta_db, "mes", None, "valor", {"indicador": ["Anomalia de temperatura global"], "proveedor": ["NASA"],
                                                      "anio": [2023]})
    despues = consulta(ruta_db, "anio", None, "valor", {"indicador": ["Anomalia de temperatura global"], "proveedor": ["NASA"],
                                                         "anio": [2023]})
    meses = [v for v in antes["celdas"].values() if v is not None]
    ej.append({
        "id": "rollup", "operacion": "Roll-up", "pregunta": 1, "vista": 1,
        "titulo": "De los meses de 2023 al anio 2023 (anomalia de temperatura, NASA)",
        "dimensiones": "Tiempo (Mes → Anio), Fuente (slice: NASA), Indicador (slice: anomalia)",
        "medidas": "Valor promedio (°C); medida no aditiva",
        "nivel": "Antes: nivel Mes. Despues: nivel Anio.",
        "procedimiento": "Se agrupa por t.anio en lugar de t.anio*100+t.mes. Como la anomalia es no aditiva, la regla de la "
                         "dimension Indicador aplica AVG: el valor anual es el promedio de sus meses, no su suma.",
        "tablas": [("Antes · nivel Mes", _tabla(antes, lambda v: _f(v, 2))),
                   ("Despues · nivel Anio", _tabla(despues, lambda v: _f(v, 2)))],
        "interpretacion": "Los 12 meses van de {} a {} °C; al subir a Anio queda un solo valor, {} °C, igual al promedio de los meses "
                          "({} °C). Sumarlos daria {} °C, un numero sin sentido fisico.".format(
                              _f(min(meses), 2), _f(max(meses), 2), _f(despues["total"], 2),
                              _f(sum(meses) / len(meses), 2), _f(sum(meses), 2)),
    })

    # 2b. Roll-up Indicador -> Categoria con una proporcion (pregunta 4)
    ind = consulta(ruta_db, "indicador", None, "pat", {"nivel": ["Nacional"], "categoria": ["Energia"]})
    cat = consulta(ruta_db, "categoria", None, "pat", {"nivel": ["Nacional"], "categoria": ["Energia"]})
    vals = [v for v in ind["celdas"].values() if v is not None]
    ingenuo = sum(vals) / len(vals) if vals else None
    ej.append({
        "id": "rollup2", "operacion": "Roll-up", "pregunta": 4, "vista": 4,
        "titulo": "De los indicadores de Energia a la categoria Energia (% de atipicos, paises)",
        "dimensiones": "Indicador (Indicador → Categoria), Geografia (slice: Nacional)",
        "medidas": "% de atipicos = SUM(atipico) / SUM(n_registros) × 100",
        "nivel": "Antes: nivel Indicador. Despues: nivel Categoria.",
        "procedimiento": "Se agrupa por i.categoria. La proporcion se recalcula con el numerador y el denominador de toda la "
                         "categoria; no se promedian los porcentajes de cada indicador.",
        "tablas": [("Antes · nivel Indicador", _tabla(ind, lambda v: _f(v, 1) + "%")),
                   ("Despues · nivel Categoria", _tabla(cat, lambda v: _f(v, 1) + "%"))],
        "interpretacion": "El valor correcto de la categoria es {}. Promediar los porcentajes de sus {} indicadores daria {}, porque "
                          "ignoraria que cada indicador tiene un numero distinto de registros.".format(
                              _f(cat["total"], 2) + "%", len(vals), _f(ingenuo, 2) + "%"),
    })

    # 3. Slice: Indicador = renovables (pregunta 3)
    ter = ["Africa", "Asia", "Europe", "North America", "Oceania", "South America", "World", "Colombia"]
    r = consulta(ruta_db, "territorio", "anio", "valor", {"indicador": ["Participacion de renovables en energia"],
                                                        "pais": ter, "anio": [2020, 2024]})
    col = (r["celdas"].get("Colombia|2020"), r["celdas"].get("Colombia|2024"))
    mun = (r["celdas"].get("World|2020"), r["celdas"].get("World|2024"))
    ej.append({
        "id": "slice", "operacion": "Slice", "pregunta": 3, "vista": 3,
        "titulo": "Fijar el indicador «Participacion de renovables en energia»",
        "dimensiones": "Indicador (slice), Geografia (territorios), Tiempo (2020 y 2024)",
        "medidas": "Valor del indicador (%)",
        "nivel": "Filtro de un solo valor en Indicador; Territorio y Anio quedan libres.",
        "procedimiento": "Se agrega WHERE i.indicador = 'Participacion de renovables en energia'. El cubo pierde la dimension "
                         "Indicador y queda una rebanada Territorio × Anio.",
        "tablas": [("Rebanada Territorio × Anio", _tabla(r, lambda v: _f(v, 1) + "%"))],
        "interpretacion": "En la rebanada, Colombia pasa de {} a {} mientras el mundo sube de {} a {}: es el unico territorio que pierde "
                          "participacion renovable.".format(_f(col[0], 1) + "%", _f(col[1], 1) + "%", _f(mun[0], 1) + "%", _f(mun[1], 1) + "%"),
    })

    # 4. Dice: territorios x anios x indicador (pregunta 3)
    r = consulta(ruta_db, "territorio", "anio", "valor", {"indicador": ["Emisiones de CO2 per capita"],
                                                        "pais": ["South America", "Colombia", "World"], "anio": [2021, 2024]})
    ej.append({
        "id": "dice", "operacion": "Dice", "pregunta": 3, "vista": 3,
        "titulo": "Subcubo {Sudamerica, Colombia, Mundo} × {2021, 2024} × CO2 per capita",
        "dimensiones": "Geografia (3 territorios), Tiempo (2 anios), Indicador (1 indicador)",
        "medidas": "Valor del indicador (t CO2/persona)",
        "nivel": "Filtros con varios valores en Geografia y Tiempo a la vez (IN), y uno en Indicador.",
        "procedimiento": "Se agregan WHERE g.entidad IN (…) AND t.anio IN (2021, 2024) AND i.indicador = …. El resultado es un "
                         "cubo mas pequeno con las mismas dimensiones. Se usa 2021 como base para evitar el efecto de la pandemia.",
        "tablas": [("Subcubo", _tabla(r, lambda v: _f(v, 2)))],
        "interpretacion": "Desde 2021, Colombia baja de {} a {} t por persona, Sudamerica de {} a {} y el mundo sube de {} a {}: con 2021 "
                          "como base, la region y el pais reducen su intensidad mientras el mundo la aumenta.".format(
                              _f(r["celdas"].get("Colombia|2021"), 2), _f(r["celdas"].get("Colombia|2024"), 2),
                              _f(r["celdas"].get("South America|2021"), 2), _f(r["celdas"].get("South America|2024"), 2),
                              _f(r["celdas"].get("World|2021"), 2), _f(r["celdas"].get("World|2024"), 2)),
    })

    # 5. Pivot: Nivel x Tipo de fuente <-> Tipo de fuente x Nivel (pregunta 4)
    a = consulta(ruta_db, "nivel", "tipo_fuente", "n", {})
    b = consulta(ruta_db, "tipo_fuente", "nivel", "n", {})
    ej.append({
        "id": "pivot", "operacion": "Pivot", "pregunta": 4, "vista": 4,
        "titulo": "Rotar Nivel geografico × Tipo de fuente",
        "dimensiones": "Geografia (Nivel geografico), Fuente (Tipo de fuente)",
        "medidas": "Numero de registros",
        "nivel": "Mismas dimensiones y filtros; solo cambia cual va en filas y cual en columnas.",
        "procedimiento": "Se intercambian los atributos de GROUP BY de filas y columnas. Las celdas son las mismas; los totales de "
                         "fila pasan a ser totales de columna.",
        "tablas": [("Filas: nivel · Columnas: tipo de fuente", _tabla(a, lambda v: _f(v, 0) if v is not None else "—")),
                   ("Filas: tipo de fuente · Columnas: nivel", _tabla(b, lambda v: _f(v, 0) if v is not None else "—"))],
        "interpretacion": ("Leida por nivel, la tabla muestra que Nacional y Regional vienen solo de la fuente terciaria, mientras "
                           "el nivel Global tiene {} de registros primarios. Rotada, muestra que las {} mediciones primarias "
                           "estan todas en el nivel Global. Mismo dato, otra pregunta: «¿de que se compone cada nivel?» frente a "
                           "«¿donde aporta cada tipo de fuente?».").format(
            _f((a["celdas"].get("Global|Primaria") or 0) / (a["total_filas"].get("Global") or 1) * 100, 1) + "%",
            _f(b["total_filas"].get("Primaria") or 0, 0)),
    })
    return ej
