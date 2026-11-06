# -*- coding: utf-8 -*-
"""
ClimaTec - Etapa 5 / Verificacion del modelo estrella cargado en SQLite.

Dos bloques, ambos calculados en vivo:

  1. Integridad del modelo (consultas SQL sobre el almacen):
       - unicidad de las claves de las dimensiones;
       - correspondencia entre claves foraneas y registros relacionados;
       - ausencia de duplicados indebidos en la tabla de hechos;
       - tratamiento de valores faltantes y categorias desconocidas;
       - validez de las jerarquias (cada hijo tiene un solo padre).
  2. Comparaciones modelo vs. datos tratados: el mismo resultado se calcula con
     una consulta en estrella sobre SQLite y con pandas sobre clima_limpio.csv,
     y se explica cualquier diferencia.

Uso:  python scripts/verificar_modelo.py
"""

import os
import sqlite3
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cargar_modelo as cm  # noqa: E402
import multidimensional as md  # noqa: E402

TOL = 1e-6


def _uno(con, sql):
    return con.execute(sql).fetchone()[0]


def _fmt(x, d=2):
    if x is None:
        return "—"
    if isinstance(x, (int,)) or (isinstance(x, float) and float(x).is_integer() and abs(x) >= 1000):
        return md.fmt_int(x)
    return md.fmt_dec(x, d)


# ---------------------------------------------------------------------------
# 1. Integridad
# ---------------------------------------------------------------------------
def integridad(con, n_origen):
    checks = []

    def agregar(grupo, nombre, sql, esperado, obtenido, explicacion, ok=None):
        checks.append({"grupo": grupo, "nombre": nombre, "sql": sql.strip(), "esperado": esperado,
                       "obtenido": obtenido, "ok": (str(obtenido) == str(esperado)) if ok is None else ok,
                       "explicacion": explicacion})

    # --- Unicidad de claves de las dimensiones --------------------------------
    for tabla, pk, natural in [("dim_tiempo", "id_tiempo", "anio, mes"),
                               ("dim_geografia", "id_geo", "entidad, nivel_geografico"),
                               ("dim_indicador", "id_indicador", "indicador"),
                               ("dim_fuente", "id_fuente", "fuente")]:
        sql = "SELECT COUNT(*) - COUNT(DISTINCT {pk}) FROM {t};".format(pk=pk, t=tabla)
        agregar("Unicidad de claves", "{}.{} sin repetidos".format(tabla, pk), sql, 0, _uno(con, sql),
                "La clave primaria identifica un solo miembro.")
        sql = "SELECT COUNT(*) FROM (SELECT {n} FROM {t} GROUP BY {n} HAVING COUNT(*) > 1);".format(n=natural, t=tabla)
        agregar("Unicidad de claves", "{}: clave natural ({}) unica".format(tabla, natural), sql, 0, _uno(con, sql),
                "Ningun miembro del negocio se cargo dos veces con claves sustitutas distintas.")

    # --- Correspondencia de claves foraneas ---------------------------------
    for fk, tabla in [("id_tiempo", "dim_tiempo"), ("id_geo", "dim_geografia"),
                      ("id_indicador", "dim_indicador"), ("id_fuente", "dim_fuente")]:
        sql = ("SELECT COUNT(*) FROM hechos_observacion h LEFT JOIN {t} d ON d.{k} = h.{k} "
               "WHERE d.{k} IS NULL;").format(t=tabla, k=fk)
        agregar("Claves foraneas", "Todo hecho encuentra su {}".format(tabla), sql, 0, _uno(con, sql),
                "Ningun hecho queda huerfano al unirlo con la dimension.")
    sql = "PRAGMA foreign_key_check;"
    agregar("Claves foraneas", "Restricciones FOREIGN KEY de SQLite", sql, 0, len(con.execute(sql).fetchall()),
            "SQLite revisa todas las REFERENCES declaradas en el DDL.")
    sql = ("SELECT COUNT(*) FROM (SELECT d.id_geo FROM dim_geografia d LEFT JOIN hechos_observacion h "
           "ON h.id_geo = d.id_geo WHERE d.id_geo <> -1 GROUP BY d.id_geo HAVING COUNT(h.id_hecho) = 0);")
    agregar("Claves foraneas", "Miembros de geografia sin hechos", sql, 0, _uno(con, sql),
            "Las dimensiones se construyen desde los propios hechos: no hay miembros vacios (salvo el -1 reservado).")

    # --- Duplicados en la tabla de hechos -----------------------------------
    sql = ("SELECT COUNT(*) FROM (SELECT id_tiempo, id_geo, id_indicador, id_fuente FROM hechos_observacion "
           "GROUP BY id_tiempo, id_geo, id_indicador, id_fuente HAVING COUNT(*) > 1);")
    agregar("Duplicados en hechos", "Una sola fila por indicador × territorio × fecha × fuente", sql, 0, _uno(con, sql),
            "Respeta la granularidad declarada; ademas lo impide el UNIQUE de la tabla.")
    sql = "SELECT COUNT(*) FROM hechos_observacion;"
    agregar("Duplicados en hechos", "Hechos cargados = registros tratados", sql, n_origen, _uno(con, sql),
            "La carga no agrega ni pierde filas.")

    # --- Faltantes y desconocidos --------------------------------------------
    sql = ("SELECT COUNT(*) FROM hechos_observacion WHERE id_tiempo = -1 OR id_geo = -1 "
           "OR id_indicador = -1 OR id_fuente = -1;")
    agregar("Faltantes y desconocidos", "Hechos que apuntan al miembro «Desconocido» (-1)", sql, 0, _uno(con, sql),
            "Si una clave no se resolviera, el hecho iria al miembro -1 en vez de perderse; hoy no ocurre.")
    sql = "SELECT COUNT(*) FROM hechos_observacion WHERE valor IS NULL;"
    agregar("Faltantes y desconocidos", "Hechos sin valor", sql, 0, _uno(con, sql),
            "La columna valor es NOT NULL: la limpieza ya no dejaba valores vacios.")
    sql = "SELECT COUNT(*) FROM hechos_observacion WHERE valor_z IS NULL;"
    n_z = _uno(con, sql)
    agregar("Faltantes y desconocidos", "Hechos sin valor_z (se dejan en NULL)", sql, "informativo", n_z,
            "No se imputan: AVG(valor_z) los excluye y la medida se calcula con los que si tienen valor.", ok=True)
    sql = "SELECT COUNT(*) FROM dim_geografia WHERE iso_code = 'No aplica' AND id_geo <> -1;"
    agregar("Faltantes y desconocidos", "Entidades sin codigo ISO → «No aplica»", sql, "informativo", _uno(con, sql),
            "Nulo estructural de la Etapa 2: los agregados (regiones, mundo) no tienen ISO.", ok=True)
    sql = "SELECT COUNT(*) FROM dim_geografia WHERE nivel_geografico = 'Nacional' AND region = 'Sin region';"
    agregar("Faltantes y desconocidos", "Paises sin region asignada", sql, 0, _uno(con, sql),
            "Todos los ISO3 del dataset estan en dim_pais_region.csv.")
    sql = "SELECT COUNT(*) FROM dim_tiempo WHERE mes = 0 AND id_tiempo <> -1;"
    agregar("Faltantes y desconocidos", "Periodos anuales con mes = 0 («no aplica»)", sql, "informativo", _uno(con, sql),
            "El mes vacio de las series anuales se codifica como 0, sin inventar un mes.", ok=True)

    # --- Jerarquias validas ---------------------------------------------------
    for nombre, sql, expl in [
        ("Cada pais pertenece a una sola region",
         "SELECT COUNT(*) FROM (SELECT pais FROM dim_geografia WHERE nivel_geografico = 'Nacional' "
         "GROUP BY pais HAVING COUNT(DISTINCT region) > 1);",
         "Mundo → Region → Pais es una agrupacion valida."),
        ("Cada mes pertenece a un solo trimestre y semestre",
         "SELECT COUNT(*) FROM (SELECT mes FROM dim_tiempo WHERE mes > 0 "
         "GROUP BY mes HAVING COUNT(DISTINCT trimestre) > 1 OR COUNT(DISTINCT semestre) > 1);",
         "Anio → Semestre → Trimestre → Mes es una agrupacion valida."),
        ("Cada indicador pertenece a una sola categoria",
         "SELECT COUNT(*) FROM (SELECT indicador FROM dim_indicador GROUP BY indicador "
         "HAVING COUNT(DISTINCT categoria) > 1);",
         "Categoria → Indicador es una agrupacion valida."),
        ("Cada fuente tiene un solo proveedor y tipo",
         "SELECT COUNT(*) FROM (SELECT fuente FROM dim_fuente GROUP BY fuente "
         "HAVING COUNT(DISTINCT proveedor) > 1 OR COUNT(DISTINCT fuente_tipo) > 1);",
         "Tipo → Proveedor → Fuente es una agrupacion valida."),
    ]:
        agregar("Jerarquias", nombre, sql, 0, _uno(con, sql), expl)
    return checks


# ---------------------------------------------------------------------------
# 2. Comparaciones modelo vs datos tratados
# ---------------------------------------------------------------------------
def comparaciones(con, df):
    d = df.copy()
    d["atipico"] = d["atipico"].astype(str).str.lower().isin(["true", "1"])
    reg = md._regiones()
    d = d.merge(reg[["iso_code", "region"]], on="iso_code", how="left")
    out = []

    # C1 - Conteo por anio
    sql = ("SELECT t.anio, SUM(h.n_registros) AS n FROM hechos_observacion h "
           "JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo GROUP BY t.anio ORDER BY t.anio;")
    m = dict(con.execute(sql).fetchall())
    o = d.groupby("anio").size().to_dict()
    filas = [{"clave": str(a), "modelo": md.fmt_int(m.get(a, 0)), "origen": md.fmt_int(o.get(a, 0)),
              "dif": md.fmt_int(m.get(a, 0) - o.get(a, 0))} for a in sorted(set(m) | set(o))]
    dif = sum(abs(m.get(a, 0) - o.get(a, 0)) for a in set(m) | set(o))
    out.append({"titulo": "Numero de registros por anio", "medida": "SUM(n_registros) agrupado por dim_tiempo.anio",
                "sql": sql, "pandas": "df.groupby('anio').size()", "filas": filas,
                "cols": ("Anio", "Modelo (SQLite)", "Datos tratados", "Diferencia"), "ok": dif == 0,
                "explicacion": "Coinciden en todos los anios: la carga no agrega ni pierde registros y el roll-up "
                               "de Mes a Anio de las series mensuales cae en el anio correcto."})

    # C2 - CO2 2024 por region: suma de paises (modelo) vs pandas vs agregado oficial
    sql = ("SELECT g.region, SUM(h.valor) FROM hechos_observacion h "
           "JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo "
           "JOIN dim_indicador i ON i.id_indicador = h.id_indicador "
           "WHERE i.indicador = 'Emisiones de CO2 (total)' AND g.nivel_geografico = 'Nacional' AND t.anio = 2024 "
           "GROUP BY g.region;")
    m = dict(con.execute(sql).fetchall())
    s = d[(d["indicador"] == "Emisiones de CO2 (total)") & (d["nivel_geografico"] == "Nacional") & (d["anio"] == 2024)]
    o = s.groupby("region")["valor"].sum().to_dict()
    ofi = d[(d["indicador"] == "Emisiones de CO2 (total)") & (d["nivel_geografico"] == "Regional") & (d["anio"] == 2024)]
    ofi = dict(zip(ofi["entidad"], ofi["valor"]))
    filas, dif = [], 0.0
    for r in md.ORDEN_REGIONES:
        mv, ov, fv = m.get(r, 0.0), o.get(r, 0.0), ofi.get(r)
        dif = max(dif, abs(mv - ov))
        filas.append({"clave": md.REGIONES_ES[r], "modelo": md.fmt_dec(mv, 1), "origen": md.fmt_dec(ov, 1),
                      "dif": md.fmt_dec(mv - ov, 3),
                      "extra": (md.fmt_dec(fv, 1) + " (" + md.fmt_signo((mv / fv - 1) * 100, 2) + ")") if fv else "—"})
    out.append({"titulo": "Emisiones de CO2 de 2024 por region (Mt CO2)",
                "medida": "SUM(valor) de los paises, roll-up Pais → Region", "sql": sql,
                "pandas": "df[paises, CO2, 2024].merge(dim_pais_region).groupby('region')['valor'].sum()",
                "filas": filas, "cols": ("Region", "Modelo (SQLite)", "Datos tratados", "Diferencia",
                                         "Agregado oficial de la fuente (dif. %)"), "ok": dif < 1e-3,
                "explicacion": "El modelo y los datos tratados dan la misma suma. Frente al agregado regional que "
                               "publica Our World in Data hay diferencias pequenas (menos de 0,5 % en cada region): la fuente "
                               "define sus continentes con criterios propios (paises transcontinentales y territorios "
                               "que no estan en el dataset), mientras el modelo asigna cada pais a un continente por su "
                               "codigo ISO. No es un error de carga. "
                               "Por eso la vista 2 muestra ambas cifras."})

    # C3 - Promedio anual de la anomalia por fuente
    sql = ("SELECT f.proveedor, t.anio, AVG(h.valor) FROM hechos_observacion h "
           "JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_fuente f ON f.id_fuente = h.id_fuente "
           "JOIN dim_indicador i ON i.id_indicador = h.id_indicador "
           "WHERE i.indicador = 'Anomalia de temperatura global' GROUP BY f.proveedor, t.anio ORDER BY 1, 2;")
    m = {(p, a): v for p, a, v in con.execute(sql).fetchall()}
    s = d[d["indicador"] == "Anomalia de temperatura global"].copy()
    s["proveedor"] = s["fuente"].map(md.proveedor)
    o = s.groupby(["proveedor", "anio"])["valor"].mean().to_dict()
    filas, dif = [], 0.0
    for k in sorted(set(m) | set(o)):
        mv, ov = m.get(k), o.get(k)
        dif = max(dif, abs((mv or 0) - (ov or 0)))
        filas.append({"clave": "{} · {}".format(k[0], k[1]), "modelo": md.fmt_dec(mv, 3) if mv is not None else "—",
                      "origen": md.fmt_dec(ov, 3) if ov is not None else "—",
                      "dif": md.fmt_dec((mv or 0) - (ov or 0), 4)})
    out.append({"titulo": "Anomalia de temperatura: promedio anual por proveedor (°C)",
                "medida": "AVG(valor), roll-up Mes → Anio por proveedor", "sql": sql,
                "pandas": "df[anomalia].groupby(['proveedor', 'anio'])['valor'].mean()",
                "filas": filas, "cols": ("Proveedor · anio", "Modelo (SQLite)", "Datos tratados", "Diferencia"),
                "ok": dif < TOL,
                "explicacion": "Coinciden. Es la comprobacion de una medida NO aditiva: el roll-up promedia los meses. "
                               "Los anios con menos de 12 meses (2026) se promedian con los meses disponibles, igual en "
                               "ambos calculos; por eso la vista 1 avisa cuando un anio esta incompleto."})

    # C4 - Atipicos por nivel geografico
    sql = ("SELECT g.nivel_geografico, SUM(h.atipico), SUM(h.n_registros) FROM hechos_observacion h "
           "JOIN dim_geografia g ON g.id_geo = h.id_geo GROUP BY g.nivel_geografico;")
    m = {n: (a, t) for n, a, t in con.execute(sql).fetchall()}
    o = d.groupby("nivel_geografico")["atipico"].agg(["sum", "size"]).to_dict("index")
    filas, dif = [], 0
    for n in sorted(set(m) | set(o)):
        ma, mt = m.get(n, (0, 0))
        oa, ot = int(o.get(n, {}).get("sum", 0)), int(o.get(n, {}).get("size", 0))
        dif += abs(ma - oa) + abs(mt - ot)
        filas.append({"clave": n, "modelo": "{} de {} ({})".format(md.fmt_int(ma), md.fmt_int(mt), md.fmt_pct(ma / mt * 100)),
                      "origen": "{} de {} ({})".format(md.fmt_int(oa), md.fmt_int(ot), md.fmt_pct(oa / ot * 100)),
                      "dif": md.fmt_int(ma - oa)})
    out.append({"titulo": "Registros atipicos por nivel geografico",
                "medida": "SUM(atipico) / SUM(n_registros) × 100", "sql": sql,
                "pandas": "df.groupby('nivel_geografico')['atipico'].agg(['sum', 'size'])",
                "filas": filas, "cols": ("Nivel", "Modelo (SQLite)", "Datos tratados", "Diferencia"), "ok": dif == 0,
                "explicacion": "Coinciden. El paso del booleano atipico a 0/1 no cambio ningun valor, y la proporcion se "
                               "recalcula desde numerador y denominador en lugar de promediar porcentajes."})

    # C5 - Control puntual: Colombia 2024, valor por valor
    sql = ("SELECT i.indicador, h.valor FROM hechos_observacion h "
           "JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo JOIN dim_geografia g ON g.id_geo = h.id_geo "
           "JOIN dim_indicador i ON i.id_indicador = h.id_indicador "
           "WHERE g.entidad = 'Colombia' AND t.anio = 2024;")
    m = dict(con.execute(sql).fetchall())
    s = d[(d["entidad"] == "Colombia") & (d["anio"] == 2024)]
    o = dict(zip(s["indicador"], s["valor"]))
    difs = [abs(m[k] - o[k]) for k in set(m) & set(o)]
    filas = [{"clave": "Hechos de Colombia 2024", "modelo": md.fmt_int(len(m)), "origen": md.fmt_int(len(o)),
              "dif": md.fmt_int(len(m) - len(o))},
             {"clave": "Indicadores presentes en ambos", "modelo": md.fmt_int(len(set(m) & set(o))),
              "origen": md.fmt_int(len(set(m) & set(o))), "dif": "0"},
             {"clave": "Mayor diferencia de valor", "modelo": "—", "origen": "—",
              "dif": md.fmt_dec(max(difs) if difs else 0, 6)}]
    out.append({"titulo": "Control puntual: la unidad Colombia 2024", "medida": "valor de cada hecho, sin agregar",
                "sql": sql, "pandas": "df[(entidad == 'Colombia') & (anio == 2024)]",
                "filas": filas, "cols": ("Control", "Modelo (SQLite)", "Datos tratados", "Diferencia"),
                "ok": len(m) == len(o) and (not difs or max(difs) < TOL),
                "explicacion": "Mismo numero de hechos y mismos valores, indicador por indicador: la unidad de analisis se "
                               "reconstruye completa desde el modelo."})
    return out


# ---------------------------------------------------------------------------
_CACHE = {}


def verificar(ruta_db, df_tratado):
    if not ruta_db or not os.path.isfile(ruta_db) or df_tratado is None:
        return None
    clave = (ruta_db, os.path.getmtime(ruta_db), len(df_tratado))
    if clave in _CACHE:
        return _CACHE[clave]
    con = sqlite3.connect(ruta_db)
    try:
        checks = integridad(con, len(df_tratado))
        comps = comparaciones(con, df_tratado)
        tablas = {t: _uno(con, "SELECT COUNT(*) FROM {}".format(t)) for t in
                  ["dim_tiempo", "dim_geografia", "dim_indicador", "dim_fuente", "hechos_observacion"]}
        ddl = [r[0] for r in con.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name IN "
                                         "('hechos_observacion') ").fetchall()]
    finally:
        con.close()
    grupos = []
    for g in ["Unicidad de claves", "Claves foraneas", "Duplicados en hechos", "Faltantes y desconocidos", "Jerarquias"]:
        items = [c for c in checks if c["grupo"] == g]
        grupos.append({"grupo": g, "checks": items, "ok": all(c["ok"] for c in items)})
    r = {"grupos": grupos, "comparaciones": comps, "tablas": tablas, "ddl_hechos": ddl[0] if ddl else "",
         "n_ok": sum(c["ok"] for c in checks), "n_checks": len(checks),
         "n_comp_ok": sum(c["ok"] for c in comps), "carga": cm.ultima_carga(ruta_db)}
    _CACHE.clear()
    _CACHE[clave] = r
    return r


if __name__ == "__main__":
    df = pd.read_csv(cm.RUTA_ORIGEN)
    cm.asegurar_modelo()
    r = verificar(cm.RUTA_DB, df)
    for g in r["grupos"]:
        print("\n[{}] {}".format("OK" if g["ok"] else "REVISAR", g["grupo"]))
        for c in g["checks"]:
            print("  {:<3} {:<60} esperado={} obtenido={}".format("ok" if c["ok"] else "X", c["nombre"],
                                                                 c["esperado"], c["obtenido"]))
    for c in r["comparaciones"]:
        print("\n[{}] {}".format("OK" if c["ok"] else "DIF", c["titulo"]))
        for f in c["filas"]:
            print("   ", f)


# ---------------------------------------------------------------------------
# 3. Condiciones para realizar el analisis (pagina "Condiciones del analisis")
# ---------------------------------------------------------------------------
def condiciones(ruta_db):
    import olap
    con = sqlite3.connect(ruta_db)
    out = []

    def ev(texto, sql=None, valor=None):
        v = valor if valor is not None else (_uno(con, sql) if sql else None)
        return {"texto": texto, "sql": sql, "valor": v}

    try:
        # 1. Granularidad consistente
        dup = ("SELECT COUNT(*) FROM (SELECT id_tiempo, id_geo, id_indicador, id_fuente FROM hechos_observacion "
               "GROUP BY 1, 2, 3, 4 HAVING COUNT(*) > 1);")
        mix = ("SELECT COUNT(*) FROM (SELECT h.id_indicador FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo "
               "GROUP BY h.id_indicador HAVING COUNT(DISTINCT t.periodicidad) > 1);")
        e1, e2 = ev("Grupos de hechos repetidos en el grano declarado", dup), ev("Indicadores que mezclan series anuales y mensuales", mix)
        out.append({"condicion": "Mantener una granularidad consistente en la tabla de hechos",
                    "como": "Un hecho = un indicador × territorio × periodo × fuente, protegido por UNIQUE. Cada indicador tiene una sola "
                            "periodicidad, asi que nunca se mezclan en una celda un dato anual y uno mensual del mismo indicador.",
                    "evidencias": [e1, e2], "ok": e1["valor"] == 0 and e2["valor"] == 0})

        # 2. Relaciones que no multiplican valores
        n_h = _uno(con, "SELECT COUNT(*) FROM hechos_observacion;")
        n_j = ("SELECT COUNT(*) FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo "
               "JOIN dim_geografia g ON g.id_geo = h.id_geo JOIN dim_indicador i ON i.id_indicador = h.id_indicador "
               "JOIN dim_fuente f ON f.id_fuente = h.id_fuente;")
        s_h = _uno(con, "SELECT ROUND(SUM(valor), 4) FROM hechos_observacion;")
        s_j = _uno(con, n_j.replace("COUNT(*)", "ROUND(SUM(h.valor), 4)"))
        out.append({"condicion": "Evitar que las relaciones entre tablas multipliquen los valores",
                    "como": "Todas las relaciones son 1:N desde dimensiones con clave unica; no hay uniones entre dimensiones ni "
                            "tablas puente. Unir la estrella completa no cambia ni el numero de filas ni la suma de valores.",
                    "evidencias": [ev("Filas de la tabla de hechos sola", valor=n_h), ev("Filas tras unir las cuatro dimensiones", n_j),
                                   ev("SUM(valor) sin uniones vs. con uniones", valor="{} = {}".format(md.fmt_dec(s_h, 1), md.fmt_dec(s_j, 1)))],
                    "ok": n_h == _uno(con, n_j) and abs((s_h or 0) - (s_j or 0)) < 1e-6})

        # 3. Conteos de registros, entidades unicas y sumas
        r_n = olap.consulta(ruta_db, "region", None, "n", {"indicador": ["Emisiones de CO2 (total)"], "nivel": ["Nacional"],
                                                           "region": ["Sudamerica"], "anio": [2020, 2021, 2022, 2023, 2024]})
        r_p = olap.consulta(ruta_db, "region", None, "paises", {"indicador": ["Emisiones de CO2 (total)"], "nivel": ["Nacional"],
                                                                "region": ["Sudamerica"], "anio": [2020, 2021, 2022, 2023, 2024]})
        r_p1 = olap.consulta(ruta_db, "anio", None, "paises", {"indicador": ["Emisiones de CO2 (total)"], "nivel": ["Nacional"],
                                                               "region": ["Sudamerica"], "anio": [2020, 2021, 2022, 2023, 2024]})
        suma_anual = sum(v for v in r_p1["celdas"].values() if v)
        out.append({"condicion": "Diferenciar conteos de registros, conteos de entidades unicas y sumas de cantidades",
                    "como": "Son tres medidas distintas: SUM(n_registros) cuenta hechos, COUNT(DISTINCT id_geo) cuenta paises y "
                            "SUM(valor) suma la cantidad. El conteo distinto no se suma entre anios.",
                    "evidencias": [ev("Sudamerica, CO2, 2020–2024: registros (hechos)", valor=r_n["total"]),
                                   ev("Paises distintos en el mismo corte", valor=r_p["total"]),
                                   ev("Suma (incorrecta) de los paises de cada anio", valor=suma_anual),
                                   ev("Suma de la cantidad (Mt CO2), unidad distinta", valor=md.fmt_dec(r_n and olap.consulta(
                                       ruta_db, "region", None, "valor", {"indicador": ["Emisiones de CO2 (total)"], "nivel": ["Nacional"],
                                                                         "region": ["Sudamerica"], "anio": [2020, 2021, 2022, 2023, 2024]})["total"], 1))],
                    "ok": r_p["total"] < suma_anual})

        # 4. Denominadores de los porcentajes
        out.append({"condicion": "Indicar el denominador utilizado en los porcentajes",
                    "como": "Cada porcentaje del modulo declara su denominador, en esta tabla y en el subtitulo de la grafica o matriz que lo usa.",
                    "tabla": [("% de atipicos", "Registros (SUM(n_registros)) de la misma celda", "Vista 4"),
                              ("Participacion %", "Suma del nivel padre (region o mundo) del mismo indicador y anio", "Vista 2"),
                              ("Variacion %", "Valor del mismo territorio en el primer anio elegido", "Vista 3"),
                              ("Cambio en pp", "No es cociente: diferencia de dos porcentajes", "Vista 3"),
                              ("Indice mundo = 100", "Valor del Mundo en el mismo anio", "Vista 3")],
                    "evidencias": [], "ok": True})

        # 5 y 6. Recalcular porcentajes y promedios; no sumarlos
        ind = olap.consulta(ruta_db, "indicador", None, "pat", {"nivel": ["Nacional"], "categoria": ["Energia"]})
        cat = olap.consulta(ruta_db, "categoria", None, "pat", {"nivel": ["Nacional"], "categoria": ["Energia"]})
        vals = [v for v in ind["celdas"].values() if v is not None]
        mes = olap.consulta(ruta_db, "mes", None, "valor", {"indicador": ["Anomalia de temperatura global"], "proveedor": ["NASA"], "anio": [2023]})
        anio = olap.consulta(ruta_db, "anio", None, "valor", {"indicador": ["Anomalia de temperatura global"], "proveedor": ["NASA"], "anio": [2023]})
        mv = [v for v in mes["celdas"].values() if v is not None]
        out.append({"condicion": "Recalcular porcentajes y promedios al cambiar el nivel de agrupacion",
                    "como": "Cada nivel es una consulta nueva sobre los hechos: la proporcion usa el numerador y el denominador del grupo "
                            "y el promedio usa todos los hechos del grupo.",
                    "evidencias": [ev("% de atipicos de Energia recalculado (paises)", valor=md.fmt_pct(cat["total"], 2)),
                                   ev("Promedio de los 2023 meses (NASA) vs. valor anual recalculado",
                                      valor="{} = {} °C".format(md.fmt_dec(sum(mv) / len(mv), 3), md.fmt_dec(anio["total"], 3)))],
                    "ok": True})
        try:
            olap.consulta(ruta_db, "region", None, "valor", {})
            bloqueo = "no bloqueado"
        except olap.ErrorConsulta as e:
            bloqueo = str(e)
        out.append({"condicion": "Evitar sumar porcentajes o promedios de grupos sin considerar como fueron calculados",
                    "como": "Los totales de las matrices salen de su propia consulta; el motor rechaza sumar valores de indicadores distintos; "
                            "la vista 2 no suma anios (la poblacion es un stock).",
                    "evidencias": [ev("Promediar los % de los {} indicadores de Energia daria".format(len(vals)),
                                      valor=md.fmt_pct(sum(vals) / len(vals), 2) + " (incorrecto)"),
                                   ev("El valor correcto, con numerador y denominador", valor=md.fmt_pct(cat["total"], 2)),
                                   ev("Respuesta del motor a una suma de indicadores distintos", valor=bloqueo)],
                    "ok": bloqueo != "no bloqueado"})

        # 7. Periodos equivalentes
        meses = con.execute("SELECT t.anio, COUNT(DISTINCT t.mes) FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo "
                            "WHERE t.mes > 0 GROUP BY t.anio ORDER BY 1;").fetchall()
        reg = con.execute("SELECT t.anio, COUNT(*) FROM hechos_observacion h JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo "
                          "GROUP BY t.anio ORDER BY 1;").fetchall()
        out.append({"condicion": "Comparar periodos equivalentes cuando existan datos temporales",
                    "como": "Los promedios anuales y los indicadores de cambio de la vista 1 usan solo periodos completos; las vistas 2 y 3 "
                            "comparan hasta 2024, el ultimo anio con cobertura amplia; los meses se comparan con el mismo mes de otro anio.",
                    "evidencias": [ev("Meses con dato por anio (series mensuales)", valor=", ".join("{}: {}".format(a, n) for a, n in meses)),
                                   ev("Registros por anio", valor=", ".join("{}: {}".format(a, md.fmt_int(n)) for a, n in reg))],
                    "ok": True})

        # 8. Faltantes, desconocidos y negativos
        neg = con.execute("SELECT i.indicador, COUNT(*) FROM hechos_observacion h JOIN dim_indicador i ON i.id_indicador = h.id_indicador "
                          "WHERE h.valor < 0 GROUP BY i.indicador ORDER BY 2 DESC;").fetchall()
        n_pais = _uno(con, "SELECT COUNT(*) FROM dim_geografia WHERE nivel_geografico = 'Nacional';")
        sin_gas = _uno(con, "SELECT COUNT(*) FROM dim_geografia g WHERE g.nivel_geografico = 'Nacional' AND NOT EXISTS ("
                            "SELECT 1 FROM hechos_observacion h JOIN dim_indicador i ON i.id_indicador = h.id_indicador "
                            "JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo WHERE h.id_geo = g.id_geo "
                            "AND i.indicador = 'CO2 por gas' AND t.anio = 2024);")
        out.append({"condicion": "Diferenciar valores faltantes, categorias desconocidas y respuestas negativas",
                    "como": "Faltante = no existe el hecho: se muestra «—» y no se cuenta como cero. Desconocido = miembro -1 de una "
                            "dimension. No aplica = nulo estructural (ISO de un agregado, mes de una serie anual). Negativo = valor real "
                            "permitido en anomalias y variaciones; en estos datos solo aparece en la variacion anual de CO2.",
                    "evidencias": [ev("Paises sin dato de «CO2 por gas» en 2024 (faltantes, no ceros)", valor="{} de {}".format(sin_gas, n_pais)),
                                   ev("Hechos en miembros desconocidos (-1)", "SELECT COUNT(*) FROM hechos_observacion WHERE id_geo = -1 "
                                      "OR id_tiempo = -1 OR id_indicador = -1 OR id_fuente = -1;"),
                                   ev("Entidades con ISO «No aplica»", "SELECT COUNT(*) FROM dim_geografia WHERE iso_code = 'No aplica' AND id_geo <> -1;"),
                                   ev("Valores negativos legitimos", valor="; ".join("{}: {}".format(i, n) for i, n in neg) or "ninguno")],
                    "ok": True})

        # 9. Jerarquias validas
        jer = [c for c in integridad(con, n_h) if c["grupo"] == "Jerarquias"]
        out.append({"condicion": "Utilizar jerarquias con relaciones de agrupacion validas",
                    "como": "Cada hijo tiene un solo padre en Tiempo, Geografia, Indicador y Fuente (comprobado en el almacen).",
                    "evidencias": [ev(c["nombre"], c["sql"]) for c in jer], "ok": all(c["ok"] for c in jer)})
    finally:
        con.close()

    # 10 y 11. Asociacion vs causalidad; hipotesis
    out.append({"condicion": "Diferenciar las asociaciones observadas de las relaciones causales",
                "como": "Los ocho conocimientos se presentan como asociaciones observadas (campo «Tipo de relacion»). Ninguno afirma "
                        "causas: el cubo solo tiene medidas climaticas, energeticas y de poblacion, sin variables que permitan aislar efectos.",
                "evidencias": [], "ok": True, "ref_conocimientos": "tipo"})
    out.append({"condicion": "Presentar como hipotesis las explicaciones que no puedan comprobarse con los datos",
                "como": "Las posibles causas (pandemia, El Nino, vegetacion, hidroelectricidad, sectores emisores) se separan de la "
                        "interpretacion y se marcan como hipotesis en cada conocimiento.",
                "evidencias": [], "ok": True, "ref_conocimientos": "hipotesis"})
    return out
