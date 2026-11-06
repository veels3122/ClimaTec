# -*- coding: utf-8 -*-
"""
ClimaTec - Etapa 5 / Exporta al repositorio la documentacion del modelo.

Genera, a partir del codigo y del almacen cargado (asi nunca se desactualiza):

    docs/etapa5/modelo_estrella.md          diagrama (Mermaid) y diccionario de datos
    docs/etapa5/sql/01_crear_modelo_sqlite.sql   tablas, claves y relaciones (SQLite)
    docs/etapa5/sql/02_consultas_analisis.sql    consultas de las vistas, conocimientos y operaciones
    docs/etapa5/sql/03_validaciones.sql          consultas de verificacion y condiciones

Uso (despues de cargar el modelo):
    python scripts/cargar_modelo.py
    python scripts/exportar_documentacion.py
"""

import os
import sqlite3
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cargar_modelo as cm  # noqa: E402
import multidimensional as md  # noqa: E402
import olap  # noqa: E402
import verificar_modelo as vm  # noqa: E402

REPO = os.path.dirname(cm.BASE_DIR)
DOCS = os.path.join(REPO, "docs", "etapa5")

DESCRIPCIONES = {
    "hechos_observacion": {
        "_tabla": "Tabla de hechos. Un registro = un indicador, para un territorio, en un periodo (anio o mes), segun una fuente.",
        "id_hecho": "Clave primaria sustituta (consecutivo).",
        "id_tiempo": "FK a dim_tiempo.",
        "id_geo": "FK a dim_geografia.",
        "id_indicador": "FK a dim_indicador.",
        "id_fuente": "FK a dim_fuente.",
        "valor": "Medida principal: valor observado del indicador (unidad en dim_indicador.unidad). Semiaditiva.",
        "valor_z": "Valor normalizado por indicador (Etapa 2). NULL si no se pudo calcular. Se promedia.",
        "atipico": "1 si la limpieza marco el registro como atipico (1,5 × IQR), 0 si no. Se suma.",
        "n_registros": "Siempre 1. SUM(n_registros) cuenta hechos.",
    },
    "dim_tiempo": {
        "_tabla": "Dimension Tiempo. Jerarquia Anio → Semestre → Trimestre → Mes (solo series mensuales).",
        "id_tiempo": "Clave primaria AAAAMM; MM = 00 en series anuales; -1 = desconocido.",
        "anio": "Anio de la observacion.",
        "semestre": "1 o 2; 0 = no aplica (serie anual).",
        "trimestre": "1 a 4; 0 = no aplica.",
        "mes": "1 a 12; 0 = no aplica.",
        "nombre_mes": "Abreviatura del mes (Ene…Dic); vacio en series anuales.",
        "periodicidad": "Anual o Mensual.",
        "nivel_detalle": "Anio o Mes: nivel mas fino disponible para el periodo.",
    },
    "dim_geografia": {
        "_tabla": "Dimension Geografia. Jerarquia Mundo → Region → Pais.",
        "id_geo": "Clave primaria sustituta; -1 = desconocido.",
        "nivel_geografico": "Global, Regional o Nacional.",
        "region": "Continente (nombre de la fuente). Para paises se obtiene del ISO3 con data/raw/dim_pais_region.csv.",
        "region_es": "Nombre del continente en espanol.",
        "pais": "Nombre del pais; «No aplica» en agregados.",
        "entidad": "Entidad tal como viene de la fuente (pais, continente o mundo).",
        "iso_code": "Codigo ISO3; «No aplica» en agregados.",
        "es_foco": "1 para Colombia, pais foco del proyecto.",
    },
    "dim_indicador": {
        "_tabla": "Dimension Indicador. Jerarquia Categoria → Indicador.",
        "id_indicador": "Clave primaria sustituta; -1 = desconocido.",
        "categoria": "Tema: Emisiones de CO2, Otros gases, Energia, Clima y atmosfera, Demografia.",
        "indicador": "Nombre homologado en la Etapa 3.",
        "unidad": "Unidad de medida del indicador.",
        "tipo_medida": "Absoluto, Per capita, Porcentaje, Anomalia o Concentracion.",
        "agregacion": "Regla al subir de nivel: suma (aditivo entre territorios) o promedio.",
    },
    "dim_fuente": {
        "_tabla": "Dimension Fuente. Jerarquia Tipo de fuente → Proveedor → Fuente.",
        "id_fuente": "Clave primaria sustituta; -1 = desconocido.",
        "fuente_tipo": "Primaria o Terciaria.",
        "proveedor": "Institucion que publica (Our World in Data, NASA, NOAA).",
        "fuente": "Producto de datos concreto.",
    },
}

MERMAID = """```mermaid
erDiagram
    dim_tiempo ||--o{ hechos_observacion : "id_tiempo"
    dim_geografia ||--o{ hechos_observacion : "id_geo"
    dim_indicador ||--o{ hechos_observacion : "id_indicador"
    dim_fuente ||--o{ hechos_observacion : "id_fuente"
    hechos_observacion {
        int id_hecho PK
        int id_tiempo FK
        int id_geo FK
        int id_indicador FK
        int id_fuente FK
        real valor "medida"
        real valor_z "medida"
        int atipico "medida 0/1"
        int n_registros "medida = 1"
    }
    dim_tiempo {
        int id_tiempo PK "AAAAMM"
        int anio
        int semestre
        int trimestre
        int mes
        text nombre_mes
        text periodicidad
        text nivel_detalle
    }
    dim_geografia {
        int id_geo PK
        text nivel_geografico
        text region
        text region_es
        text pais
        text entidad
        text iso_code
        int es_foco
    }
    dim_indicador {
        int id_indicador PK
        text categoria
        text indicador
        text unidad
        text tipo_medida
        text agregacion
    }
    dim_fuente {
        int id_fuente PK
        text fuente_tipo
        text proveedor
        text fuente
    }
```"""


def _modelo_md(con, info):
    l = ["# Modelo multidimensional de ClimaTec (Etapa 5)", "",
         "Documento generado por `climate-mining-app/scripts/exportar_documentacion.py` a partir del almacen "
         "`data/dw/climatec_dw.sqlite`.", "",
         "## Diagrama del modelo estrella", "", MERMAID, "",
         "- **Tabla de hechos:** `hechos_observacion`.",
         "- **Granularidad:** un indicador, para un territorio, en un periodo (anio o mes), segun una fuente. "
         "Restriccion `UNIQUE (id_tiempo, id_geo, id_indicador, id_fuente)`.",
         "- **Relaciones:** 1:N desde cada dimension (FOREIGN KEY). Las dimensiones no se relacionan entre si.",
         "- **Miembro desconocido:** clave `-1` en cada dimension.", "",
         "## Filas por tabla", "", "| Tabla | Filas |", "|---|---|"]
    for t in ["hechos_observacion", "dim_tiempo", "dim_geografia", "dim_indicador", "dim_fuente"]:
        l.append("| `{}` | {} |".format(t, con.execute("SELECT COUNT(*) FROM {}".format(t)).fetchone()[0]))
    l += ["", "## Diccionario de datos", ""]
    for t in ["hechos_observacion", "dim_tiempo", "dim_geografia", "dim_indicador", "dim_fuente"]:
        d = DESCRIPCIONES[t]
        l += ["### `{}`".format(t), "", d["_tabla"], "", "| Campo | Tipo | Clave | Nulo | Descripcion |", "|---|---|---|---|---|"]
        fks = {r[3]: r[2] for r in con.execute("PRAGMA foreign_key_list({})".format(t)).fetchall()}
        for cid, nombre, tipo, notnull, _, pk in con.execute("PRAGMA table_info({})".format(t)).fetchall():
            clave = "PK" if pk else ("FK → {}".format(fks[nombre]) if nombre in fks else "")
            l.append("| `{}` | {} | {} | {} | {} |".format(nombre, tipo, clave, "No" if notnull or pk else "Si",
                                                          d.get(nombre, "")))
        l.append("")
    l += ["## Medidas", "", "| Medida | Unidad | Formula | Agregacion | Tipo | Cuando se suma |", "|---|---|---|---|---|---|"]
    for m in info["modelo"]["medidas"]:
        l.append("| {} | {} | `{}` | {} | {} | {} |".format(m["nombre"], m["unidad"], m["formula"], m["agregacion"],
                                                          m["aditividad"], m["cuando"]))
    l += ["", "## Jerarquias", "", "| Dimension | Niveles | Validez |", "|---|---|---|"]
    for d in info["modelo"]["dimensiones"]:
        l.append("| {} | {} | {} |".format(d["nombre"].replace("Dimension ", ""), " → ".join(d["jerarquia"]), d["validez"]))
    l += ["", "## Correspondencia con `clima_limpio.csv`", "", "| Variable original | Campo del modelo | Transformacion |", "|---|---|---|"]
    for o, c, t in cm.CORRESPONDENCIA:
        l.append("| `{}` | `{}` | {} |".format(o, c, t))
    l.append("")
    return "\n".join(l)


def _consultas_sql(info):
    l = ["-- ClimaTec - Etapa 5: consultas de analisis sobre el modelo estrella (SQLite).",
         "-- Generado por scripts/exportar_documentacion.py. Cada consulta es la que ejecuta la app.", ""]
    l.append("-- =====================================================================")
    l.append("-- 1. Evidencia de los conocimientos multidimensionales (una o dos por conocimiento)")
    l.append("-- =====================================================================")
    for k in info["conocimientos"]:
        for c in k.get("evidencia_consultas", []):
            if "sql" in c:
                l += ["", "-- Conocimiento {} (vista {}): {}".format(k["numero"], k["vista"], k["titulo"]),
                      "-- {}".format(c["titulo"]), c["sql"].rstrip(";") + ";"]
    l += ["", "-- =====================================================================",
          "-- 2. Ejemplos de operaciones OLAP (drill-down, roll-up, slice, dice, pivot)",
          "-- ====================================================================="]
    for e in olap.ejemplos(cm.RUTA_DB):
        for titulo, t in e["tablas"]:
            l += ["", "-- {} · {} · {}".format(e["operacion"], e["titulo"], titulo), t["sql"].rstrip(";") + ";"]
    l += ["", "-- =====================================================================",
          "-- 3. Plantilla de las consultas de las vistas (/api/etapa5/olap)",
          "-- =====================================================================",
          "-- SELECT <clave filas>, <clave columnas>, <medida>",
          "-- FROM hechos_observacion h",
          "-- JOIN dim_tiempo t ON t.id_tiempo = h.id_tiempo",
          "-- JOIN dim_geografia g ON g.id_geo = h.id_geo",
          "-- JOIN dim_indicador i ON i.id_indicador = h.id_indicador",
          "-- JOIN dim_fuente f ON f.id_fuente = h.id_fuente",
          "-- WHERE <slice / dice> GROUP BY <filas>, <columnas>;",
          "-- Medidas: " + "; ".join("{} = {}".format(v[0], v[1]) for v in olap.MEDIDAS.values()), ""]
    return "\n".join(l)


def _validaciones_sql(df):
    con = sqlite3.connect(cm.RUTA_DB)
    try:
        checks = vm.integridad(con, len(df))
        comps = vm.comparaciones(con, df)
    finally:
        con.close()
    l = ["-- ClimaTec - Etapa 5: consultas de verificacion del modelo (SQLite).",
         "-- Generado por scripts/exportar_documentacion.py. Resultado esperado indicado en cada una.", ""]
    for c in checks:
        l += ["-- [{}] {} (esperado: {})".format(c["grupo"], c["nombre"], c["esperado"]), c["sql"], ""]
    l += ["-- =====================================================================",
          "-- Comparaciones con los datos tratados (el mismo resultado se calcula con pandas sobre clima_limpio.csv)",
          "-- ====================================================================="]
    for c in comps:
        l += ["", "-- {} · pandas: {}".format(c["titulo"], c["pandas"]), c["sql"]]
    l.append("")
    return "\n".join(l)


def exportar():
    df = pd.read_csv(cm.RUTA_ORIGEN)
    cm.asegurar_modelo()
    info = md.construir(df, len(df), cm.RUTA_DB)
    os.makedirs(os.path.join(DOCS, "sql"), exist_ok=True)
    con = sqlite3.connect(cm.RUTA_DB)
    try:
        md_txt = _modelo_md(con, info)
    finally:
        con.close()
    archivos = {
        os.path.join(DOCS, "modelo_estrella.md"): md_txt,
        os.path.join(DOCS, "sql", "01_crear_modelo_sqlite.sql"):
            "-- ClimaTec - Etapa 5: creacion de tablas, claves y relaciones del modelo estrella (SQLite).\n"
            "-- Es el DDL que ejecuta scripts/cargar_modelo.py. Version SQL Server: ssis/sql/04_modelo_estrella.sql\n"
            + cm.DDL,
        os.path.join(DOCS, "sql", "02_consultas_analisis.sql"): _consultas_sql(info),
        os.path.join(DOCS, "sql", "03_validaciones.sql"): _validaciones_sql(df),
    }
    for ruta, txt in archivos.items():
        with open(ruta, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
        print("escrito", os.path.relpath(ruta, REPO))


if __name__ == "__main__":
    exportar()
