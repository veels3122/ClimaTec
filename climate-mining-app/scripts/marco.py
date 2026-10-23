# -*- coding: utf-8 -*-
"""ClimaTec - Etapa 4 / Marco del analisis: tratamiento previo, registros disponibles,
problemas de calidad vigentes, unidad de analisis y las cuatro preguntas. Todo se calcula en vivo."""
import pandas as pd
from poblacional import fmt_int


def _p(x, d=1):
    return "{:.{d}f}".format(x, d=d).replace(".", ",")


def construir(df, rep=None, eventos=None):
    if df is None or df.empty:
        return None
    n = len(df)
    nac = df[df["nivel_geografico"] == "Nacional"]
    agr = n - len(nac)
    por_nivel = [{"nivel": k, "registros": fmt_int(g.shape[0]), "pct": _p(100 * len(g) / n), "entidades": int(g["entidad"].nunique())}
                 for k, g in df.groupby("nivel_geografico")]
    por_fuente = [{"fuente": k, "tipo": g["fuente_tipo"].iloc[0], "registros": fmt_int(len(g)), "pct": _p(100 * len(g) / n, 2)}
                  for k, g in df.groupby("fuente")]
    por_fuente.sort(key=lambda x: -float(x["pct"].replace(",", ".")))
    anual = df[df["periodicidad"] == "Anual"].groupby("anio").size()
    mens = int((df["periodicidad"] == "Mensual").sum())
    terc = float(df[df["fuente_tipo"] == "Terciaria"].shape[0]) / n * 100
    col = df[df["entidad"] == "Colombia"]
    fa = anual.get(max(anual.index), 0) if len(anual) else 0
    n_atip = int(df["atipico"].sum()) if "atipico" in df else 0
    causa = rep["atip_causas"]["pct_explicado"] if rep and rep.get("atip_causas") else None
    manifest_omit = ["NASA POWER", "Banco Mundial (WDI)", "IDEAM"]
    problemas = [
        ("Observaciones atipicas", "{} registros marcados ({} %), no eliminados".format(fmt_int(n_atip), _p(100 * n_atip / n, 2)),
         "Casi todas son reales (paises grandes y agregados mundiales){}. Los promedios simples se distorsionan: se usan medianas, per capita o valor_z.".format(
             "; {} % tiene causa identificada".format(_p(causa)) if causa else "")),
        ("Escalas y unidades heterogeneas", "{} indicadores / {} unidades".format(df["indicador"].nunique(), df["unidad"].nunique()),
         "No se pueden sumar ni promediar indicadores distintos entre si; cada analisis usa un indicador a la vez o su version normalizada."),
        ("Cobertura temporal desigual", "{} registros anuales en {} frente a {} en {}".format(fmt_int(fa), max(anual.index), fmt_int(anual.get(min(anual.index), 0)), min(anual.index)) if len(anual) else "-",
         "Las series anuales llegan completas hasta {}; despues quedan casi vacias. Solo hay {} registros mensuales ({} %), por eso la dimension temporal se limita a 2020-2025.".format(
             int(anual[anual > 0.9 * anual.max()].index.max()), fmt_int(mens), _p(100 * mens / n, 2))),
        ("Colombia con poca cobertura propia", "{} registros ({} %), una sola familia de fuente".format(fmt_int(len(col)), _p(100 * len(col) / n, 2)),
         "Las fuentes nacionales y regionales ({}) quedaron omitidas por falta de red: no hay clima local (temperatura, lluvia) para Colombia, solo emisiones y energia de OWID.".format(", ".join(manifest_omit))),
        ("Dependencia de fuentes terciarias", "{} % de los registros".format(_p(terc)),
         "OWID recopila datos de otras instituciones: sirve para comparar paises, pero no reemplaza una medicion primaria."),
        ("Mezcla de niveles geograficos", "{} registros agregados (mundo y regiones) = {} %".format(fmt_int(agr), _p(100 * agr / n)),
         "Los agregados ya contienen a los paises: sumarlos con ellos duplicaria las cantidades. Cada analisis separa los niveles."),
        ("Nulos estructurales", "iso_code ({} vacios) y mes ({} vacios)".format(fmt_int(int(df["iso_code"].isna().sum())), fmt_int(int(df["mes"].isna().sum()))),
         "Los agregados no tienen codigo ISO y las series anuales no tienen mes. No son errores y no se imputan."),
    ]
    ejemplo = col[(col["indicador"] == "Emisiones de CO2 (total)")].sort_values("anio").tail(1)
    ej = None if ejemplo.empty else ejemplo.iloc[0]
    tipos = [
        ("Persona", "No", "El dataset no contiene individuos; la poblacion aparece solo como un indicador mas."),
        ("Evento", "No (tabla aparte)", "Los {} eventos externos (ENSO, COP, emergencias) estan en otro archivo y solo se superponen al analisis.".format(len(eventos) if eventos is not None else 7)),
        ("Medicion", "Si", "Cada registro es el valor de un indicador, para un territorio, en un anio (o mes) y de una fuente."),
        ("Muestra / participacion", "No", "No hay muestreo de unidades ni participantes."),
        ("Cantidad agregada", "En parte", "{} registros (mundo y regiones) son sumas de paises; los {} nacionales son mediciones por pais.".format(fmt_int(agr), fmt_int(len(nac)))),
    ]
    preguntas = [
        {"n": 1, "dim": "Poblacional", "ep": "e4_poblacional",
         "q": "¿Como esta compuesta la poblacion de ClimaTec (nivel geografico, fuente e indicador) y como se reparte la poblacion mundial entre regiones y paises de distinto tamano, para saber a quien representan las emisiones y el consumo de energia analizados?",
         "ident": "Categorias principales, % de participacion, grupos predominantes y minoritarios y distribucion de las variables clave."},
        {"n": 2, "dim": "Territorial", "ep": "e4_territorial",
         "q": "¿Como se reparten las emisiones de CO2 y el consumo de energia entre las seis regiones y los paises, que territorios concentran los mayores valores y donde queda Colombia frente a Sudamerica y al promedio mundial?",
         "ident": "Diferencias en cantidades y porcentajes, concentraciones y rasgos propios de cada territorio."},
        {"n": 3, "dim": "Temporal", "ep": "e4_temporal",
         "q": "¿Como evolucionaron el CO2 atmosferico y la anomalia de temperatura entre 2020 y 2025, en que meses y trimestres estan sus maximos y minimos y que cambios importantes aparecen al comparar periodos equivalentes?",
         "ident": "Aumentos, disminuciones, periodos maximos y minimos, comparando mismo mes o trimestre entre anios."},
        {"n": 4, "dim": "Relacional multidimensional", "ep": "e4_relacional",
         "q": "¿Que perfiles de paises resultan de combinar tamano de poblacion, emisiones per capita y participacion de renovables, cuales son frecuentes, como se relacionan esas variables con el tiempo y los eventos externos y que paises son casos inusuales?",
         "ident": "Combinaciones de tres o mas variables, diferencias entre perfiles, relaciones evidentes y casos inusuales."},
    ]
    return {"n": n, "n_antes": rep["filas_antes"] if rep else n, "cols": df.shape[1], "acciones": (rep or {}).get("acciones", []),
            "por_nivel": por_nivel, "por_fuente": por_fuente, "n_ind": int(df["indicador"].nunique()), "n_ent": int(df["entidad"].nunique()),
            "anios": (int(df["anio"].min()), int(df["anio"].max())), "problemas": problemas, "ejemplo": ej, "tipos": tipos, "preguntas": preguntas,
            "clave": "fuente + nivel_geografico + entidad + anio + mes + indicador"}
