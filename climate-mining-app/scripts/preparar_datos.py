# -*- coding: utf-8 -*-
"""
ClimaTec - Preparacion del dataset consolidado (Etapa 1).

Objetivo
--------
Construir un unico dataset REAL, multi-fuente y reproducible sobre cambio
climatico y eventos externos, en formato de TABLA DE HECHOS (formato largo/tidy):

    una fila = una observacion (indicador medido) para una entidad, en una fecha,
    proveniente de una fuente identificada.

Este formato es el que permite integrar fuentes heterogeneas (anuales y mensuales,
de distintos proveedores y niveles) bajo un mismo esquema: cada observacion queda
trazada a su columna `fuente` / `fuente_tipo`. Asi el proyecto deja de depender de
una sola fuente (OWID) e incorpora fuentes PRIMARIAS y de nivel nacional/regional.

Ventana temporal del entregable: 2020-2026.

Fuentes
-------
El script intenta descargar cada fuente. Las que estan alojadas en GitHub se
descargan siempre; las que viven en portales institucionales (NASA POWER, Banco
Mundial, IDEAM) se descargan cuando se ejecuta con acceso abierto a internet y se
OMITEN de forma controlada si el host no es alcanzable (queda constancia en el
manifiesto `fuentes_manifest.csv`). El script nunca inventa datos: solo consolida
lo que efectivamente descarga.

Ejecucion:
    python scripts/preparar_datos.py
"""

import io
import os
import sys
import urllib.request
import urllib.error

import pandas as pd

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
YEAR_MIN, YEAR_MAX = 2020, 2026

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROC_DIR, exist_ok=True)

SALIDA = os.path.join(RAW_DIR, "clima_consolidado.csv")
MANIFIESTO = os.path.join(RAW_DIR, "fuentes_manifest.csv")
EVENTOS = os.path.join(RAW_DIR, "eventos_externos_muestra.csv")

# 6 regiones continentales que usa OWID como agregados.
REGIONES = ["Africa", "Asia", "Europe", "North America", "Oceania", "South America"]

# Esquema unico de la tabla de hechos.
COLUMNAS = [
    "fuente", "fuente_tipo", "nivel_geografico", "entidad", "iso_code",
    "anio", "mes", "periodicidad", "indicador", "valor", "unidad", "fecha",
]

MANIFIESTO_FILAS = []


def _log(msg):
    print("[preparar_datos] " + msg)


def _descargar(url, timeout=90):
    """Descarga texto de una URL. Devuelve None si el host no es alcanzable."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        _log("  ! no se pudo descargar ({}): {}".format(url.split("//")[-1][:50], e))
        return None


def _leer_cache(nombre):
    """Permite reutilizar una copia previa en data/processed (util sin red)."""
    ruta = os.path.join(PROC_DIR, nombre)
    if os.path.exists(ruta):
        return pd.read_csv(ruta)
    return None


def _registrar(fuente, tipo, nivel, estado, filas):
    MANIFIESTO_FILAS.append({
        "fuente": fuente, "tipo": tipo, "nivel": nivel,
        "estado": estado, "registros_aportados": filas,
    })


# ---------------------------------------------------------------------------
# 1. OWID - CO2 and Greenhouse Gas Emissions (Global Carbon Project, terciaria)
#    Niveles: Global (World) / Regional (continentes) / Nacional (paises ISO3)
# ---------------------------------------------------------------------------
def fuente_owid_co2():
    nombre = "Our World in Data - CO2 & GHG (Global Carbon Project)"
    url = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"
    txt = _descargar(url)
    df = pd.read_csv(io.StringIO(txt)) if txt else _leer_cache("owid_co2.csv")
    if df is None:
        _registrar(nombre, "Terciaria", "Global/Regional/Nacional", "OMITIDA (sin red)", 0)
        return pd.DataFrame(columns=COLUMNAS)

    indicadores = {
        "co2": ("Emisiones de CO2 (total)", "Mt CO2"),
        "co2_per_capita": ("Emisiones de CO2 per capita", "t CO2/persona"),
        "co2_growth_prct": ("Variacion anual de CO2", "%"),
        "cumulative_co2": ("CO2 acumulado historico", "Mt CO2"),
        "coal_co2": ("CO2 por carbon", "Mt CO2"),
        "oil_co2": ("CO2 por petroleo", "Mt CO2"),
        "gas_co2": ("CO2 por gas", "Mt CO2"),
        "cement_co2": ("CO2 por cemento", "Mt CO2"),
        "methane": ("Emisiones de metano", "Mt eq. CO2"),
        "nitrous_oxide": ("Emisiones de oxido nitroso", "Mt eq. CO2"),
        "total_ghg": ("Gases de efecto invernadero (total)", "Mt eq. CO2"),
        "ghg_excluding_lucf_per_capita": ("GEI per capita (sin uso del suelo)", "t eq. CO2/persona"),
        "temperature_change_from_ghg": ("Contribucion de GEI a la temperatura", "grados C"),
        "temperature_change_from_co2": ("Contribucion del CO2 a la temperatura", "grados C"),
        "population": ("Poblacion", "personas"),
        "primary_energy_consumption": ("Consumo de energia primaria", "TWh"),
    }
    keep = [c for c in indicadores if c in df.columns]
    df = df[["country", "iso_code", "year"] + keep].copy()
    df = df[(df["year"] >= YEAR_MIN) & (df["year"] <= YEAR_MAX)]

    def nivel(row):
        if row["country"] == "World":
            return "Global"
        if row["country"] in REGIONES:
            return "Regional"
        if isinstance(row["iso_code"], str) and len(row["iso_code"]) == 3:
            return "Nacional"
        return None  # descarta agregados por ingreso u otros

    df["nivel_geografico"] = df.apply(nivel, axis=1)
    df = df[df["nivel_geografico"].notna()]

    largo = df.melt(
        id_vars=["country", "iso_code", "year", "nivel_geografico"],
        value_vars=keep, var_name="cod", value_name="valor",
    ).dropna(subset=["valor"])
    largo["indicador"] = largo["cod"].map(lambda c: indicadores[c][0])
    largo["unidad"] = largo["cod"].map(lambda c: indicadores[c][1])
    largo["fuente"] = nombre
    largo["fuente_tipo"] = "Terciaria"
    largo["entidad"] = largo["country"]
    largo["mes"] = pd.NA
    largo["periodicidad"] = "Anual"
    largo["anio"] = largo["year"].astype(int)
    largo["fecha"] = largo["anio"].map(lambda a: "{}-12-31".format(a))
    out = largo[COLUMNAS]
    _registrar(nombre, "Terciaria", "Global/Regional/Nacional", "INTEGRADA", len(out))
    _log("OWID CO2: {} observaciones".format(len(out)))
    return out


# ---------------------------------------------------------------------------
# 2. OWID - Energy (Energy Institute Statistical Review + Ember, terciaria)
#    Proveedor DISTINTO de OWID-CO2; nivel Nacional (+ World / regiones).
# ---------------------------------------------------------------------------
def fuente_owid_energy():
    nombre = "Our World in Data - Energy (Energy Institute / Ember)"
    url = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"
    txt = _descargar(url)
    df = pd.read_csv(io.StringIO(txt)) if txt else _leer_cache("energy.csv")
    if df is None:
        _registrar(nombre, "Terciaria", "Nacional/Global", "OMITIDA (sin red)", 0)
        return pd.DataFrame(columns=COLUMNAS)

    indicadores = {
        "energy_per_capita": ("Consumo de energia per capita", "kWh/persona"),
        "electricity_generation": ("Generacion de electricidad", "TWh"),
        "renewables_share_energy": ("Participacion de renovables en energia", "%"),
        "fossil_share_energy": ("Participacion de fosiles en energia", "%"),
        "low_carbon_share_energy": ("Participacion baja en carbono", "%"),
        "greenhouse_gas_emissions": ("Emisiones GEI del sector electrico", "Mt eq. CO2"),
    }
    keep = [c for c in indicadores if c in df.columns]
    df = df[["country", "iso_code", "year"] + keep].copy()
    df = df[(df["year"] >= YEAR_MIN) & (df["year"] <= YEAR_MAX)]

    def nivel(row):
        if row["country"] == "World":
            return "Global"
        if row["country"] in REGIONES:
            return "Regional"
        if isinstance(row["iso_code"], str) and len(row["iso_code"]) == 3:
            return "Nacional"
        return None

    df["nivel_geografico"] = df.apply(nivel, axis=1)
    df = df[df["nivel_geografico"].notna()]

    largo = df.melt(
        id_vars=["country", "iso_code", "year", "nivel_geografico"],
        value_vars=keep, var_name="cod", value_name="valor",
    ).dropna(subset=["valor"])
    largo["indicador"] = largo["cod"].map(lambda c: indicadores[c][0])
    largo["unidad"] = largo["cod"].map(lambda c: indicadores[c][1])
    largo["fuente"] = nombre
    largo["fuente_tipo"] = "Terciaria"
    largo["entidad"] = largo["country"]
    largo["mes"] = pd.NA
    largo["periodicidad"] = "Anual"
    largo["anio"] = largo["year"].astype(int)
    largo["fecha"] = largo["anio"].map(lambda a: "{}-12-31".format(a))
    out = largo[COLUMNAS]
    _registrar(nombre, "Terciaria", "Nacional/Global", "INTEGRADA", len(out))
    _log("OWID Energy: {} observaciones".format(len(out)))
    return out


# ---------------------------------------------------------------------------
# 3. NOAA GML - Observatorio de Mauna Loa (CO2 atmosferico) - PRIMARIA, mensual
# ---------------------------------------------------------------------------
def fuente_mauna_loa():
    nombre = "NOAA GML - Observatorio de Mauna Loa (CO2 in situ)"
    url = "https://raw.githubusercontent.com/datasets/co2-ppm/main/data/co2-mm-mlo.csv"
    txt = _descargar(url)
    # El archivo trae un encabezado desalineado (6 nombres, 7 columnas de datos),
    # por eso se lee posicionalmente: campo 0 = fecha (YYYY-MM), campo 2 = promedio
    # mensual (ppm), campo 3 = valor interpolado (relleno de faltantes).
    origen = io.StringIO(txt) if txt else os.path.join(PROC_DIR, "mlo.csv")
    if not txt and not os.path.exists(origen):
        _registrar(nombre, "Primaria", "Global", "OMITIDA (sin red)", 0)
        return pd.DataFrame(columns=COLUMNAS)
    df = pd.read_csv(origen, header=None, skiprows=1, index_col=False,
                     names=["fecha_ym", "decimal", "promedio", "interpolado",
                            "c4", "c5", "c6"])
    df["valor_ppm"] = df["promedio"].where(df["promedio"] > 0, df["interpolado"])
    df = df[df["valor_ppm"] > 0].dropna(subset=["fecha_ym"])
    df["fecha_ym"] = df["fecha_ym"].astype(str)
    df["anio"] = df["fecha_ym"].str.slice(0, 4).astype(int)
    df["mes"] = df["fecha_ym"].str.slice(5, 7).astype(int)
    df = df[(df["anio"] >= YEAR_MIN) & (df["anio"] <= YEAR_MAX)]
    out = pd.DataFrame({
        "fuente": nombre, "fuente_tipo": "Primaria",
        "nivel_geografico": "Global", "entidad": "Global (Mauna Loa)",
        "iso_code": pd.NA, "anio": df["anio"], "mes": df["mes"],
        "periodicidad": "Mensual",
        "indicador": "Concentracion de CO2 atmosferico",
        "valor": df["valor_ppm"], "unidad": "ppm",
        "fecha": df["fecha_ym"] + "-15",
    })[COLUMNAS]
    _registrar(nombre, "Primaria", "Global", "INTEGRADA", len(out))
    _log("Mauna Loa (CO2 mensual): {} observaciones".format(len(out)))
    return out


# ---------------------------------------------------------------------------
# 4. Anomalia de temperatura global mensual - NASA GISTEMP y NOAA GCAG
#    Dos proveedores distintos (observacionales), mensual.
# ---------------------------------------------------------------------------
def fuente_temperatura_global():
    url = "https://raw.githubusercontent.com/datasets/global-temp/main/data/monthly.csv"
    txt = _descargar(url)
    df = pd.read_csv(io.StringIO(txt)) if txt else _leer_cache("gtemp.csv")
    if df is None:
        _registrar("NASA GISTEMP / NOAA GCAG (temp global)", "Primaria", "Global", "OMITIDA (sin red)", 0)
        return pd.DataFrame(columns=COLUMNAS)

    mapa = {
        "GISTEMP": "NASA GISS - GISTEMP (anomalia de temperatura)",
        "GCAG": "NOAA NCEI - GlobalTemp/GCAG (anomalia de temperatura)",
    }
    df["anio"] = df["Year"].str.slice(0, 4).astype(int)
    df["mes"] = df["Year"].str.slice(5, 7).astype(int)
    df = df[(df["anio"] >= YEAR_MIN) & (df["anio"] <= YEAR_MAX)]
    out = pd.DataFrame({
        "fuente": df["Source"].map(mapa),
        "fuente_tipo": "Primaria",
        "nivel_geografico": "Global",
        "entidad": "Global (superficie terrestre y oceanica)",
        "iso_code": pd.NA, "anio": df["anio"], "mes": df["mes"],
        "periodicidad": "Mensual",
        "indicador": "Anomalia de temperatura global",
        "valor": df["Mean"], "unidad": "grados C (vs. base)",
        "fecha": df["Year"] + "-15",
    })[COLUMNAS]
    total = 0
    for src, sub in out.groupby("fuente"):
        _registrar(src, "Primaria", "Global", "INTEGRADA", len(sub))
        total += len(sub)
    _log("Temperatura global (GISTEMP+GCAG): {} observaciones".format(total))
    return out


# ---------------------------------------------------------------------------
# 5. NASA POWER - reanalisis MERRA-2 (temperatura y precipitacion) - PRIMARIA,
#    mensual, NIVEL NACIONAL (Colombia) y REGIONAL (paises de Sudamerica).
#    Se descarga al ejecutar con acceso abierto a internet (power.larc.nasa.gov).
# ---------------------------------------------------------------------------
PAISES_SUDAMERICA = {
    "COL": ("Colombia", 4.6, -74.1), "BRA": ("Brasil", -15.8, -47.9),
    "ARG": ("Argentina", -34.6, -58.4), "PER": ("Peru", -12.0, -77.0),
    "CHL": ("Chile", -33.4, -70.7), "ECU": ("Ecuador", -0.2, -78.5),
    "VEN": ("Venezuela", 10.5, -66.9), "BOL": ("Bolivia", -16.5, -68.1),
    "PRY": ("Paraguay", -25.3, -57.6), "URY": ("Uruguay", -34.9, -56.2),
}


def fuente_nasa_power():
    nombre = "NASA POWER - reanalisis MERRA-2 (T2M, precipitacion)"
    filas = []
    alcanzable = True
    for iso, (pais, lat, lon) in PAISES_SUDAMERICA.items():
        if not alcanzable:
            break
        url = (
            "https://power.larc.nasa.gov/api/temporal/monthly/point"
            "?parameters=T2M,PRECTOTCORR&community=RE"
            "&latitude={}&longitude={}&start={}&end={}&format=JSON"
        ).format(lat, lon, YEAR_MIN, YEAR_MAX)
        txt = _descargar(url, timeout=60)
        if txt is None:
            alcanzable = False
            break
        try:
            import json
            data = json.loads(txt)["properties"]["parameter"]
        except Exception:
            continue
        etiquetas = {"T2M": ("Temperatura media (2 m)", "grados C"),
                     "PRECTOTCORR": ("Precipitacion total", "mm/dia")}
        for param, serie in data.items():
            ind, uni = etiquetas.get(param, (param, ""))
            for k, v in serie.items():
                if k.endswith("13") or v in (-999, None):  # -999 = faltante; '..13' = anual
                    continue
                anio, mes = int(k[:4]), int(k[4:6])
                nivel = "Nacional" if iso == "COL" else "Regional"
                filas.append({
                    "fuente": nombre, "fuente_tipo": "Primaria",
                    "nivel_geografico": nivel, "entidad": pais, "iso_code": iso,
                    "anio": anio, "mes": mes, "periodicidad": "Mensual",
                    "indicador": ind, "valor": v, "unidad": uni,
                    "fecha": "{}-{:02d}-15".format(anio, mes),
                })
    if not filas:
        _registrar(nombre, "Primaria", "Nacional/Regional", "OMITIDA (sin red)", 0)
        _log("NASA POWER: host no alcanzable en este entorno; se omite (se integra al ejecutar con internet).")
        return pd.DataFrame(columns=COLUMNAS)
    out = pd.DataFrame(filas)[COLUMNAS]
    _registrar(nombre, "Primaria", "Nacional/Regional", "INTEGRADA", len(out))
    _log("NASA POWER: {} observaciones".format(len(out)))
    return out


# ---------------------------------------------------------------------------
# 6. Banco Mundial - indicadores climaticos por pais - SECUNDARIA, anual,
#    NIVEL NACIONAL/REGIONAL. Se descarga con acceso abierto (api.worldbank.org).
# ---------------------------------------------------------------------------
def fuente_banco_mundial():
    nombre = "Banco Mundial - World Development Indicators (clima)"
    indicadores = {
        "EN.ATM.CO2E.PC": ("Emisiones de CO2 per capita (BM)", "t/persona"),
        "EG.USE.PCAP.KG.OE": ("Uso de energia per capita", "kg eq. petroleo"),
        "EG.FEC.RNEW.ZS": ("Consumo de energia renovable", "%"),
    }
    paises = ";".join(PAISES_SUDAMERICA.keys())
    filas = []
    alcanzable = True
    for cod, (ind, uni) in indicadores.items():
        if not alcanzable:
            break
        url = ("https://api.worldbank.org/v2/country/{}/indicator/{}"
               "?format=json&per_page=2000&date={}:{}"
               ).format(paises, cod, YEAR_MIN, YEAR_MAX)
        txt = _descargar(url, timeout=60)
        if txt is None:
            alcanzable = False
            break
        try:
            import json
            payload = json.loads(txt)
            registros = payload[1] if len(payload) > 1 and payload[1] else []
        except Exception:
            registros = []
        for r in registros:
            if r.get("value") is None:
                continue
            iso = r.get("countryiso3code") or ""
            nivel = "Nacional" if iso == "COL" else "Regional"
            filas.append({
                "fuente": nombre, "fuente_tipo": "Secundaria",
                "nivel_geografico": nivel,
                "entidad": r["country"]["value"], "iso_code": iso,
                "anio": int(r["date"]), "mes": pd.NA, "periodicidad": "Anual",
                "indicador": ind, "valor": r["value"], "unidad": uni,
                "fecha": "{}-12-31".format(r["date"]),
            })
    if not filas:
        _registrar(nombre, "Secundaria", "Nacional/Regional", "OMITIDA (sin red)", 0)
        _log("Banco Mundial: host no alcanzable en este entorno; se omite (se integra al ejecutar con internet).")
        return pd.DataFrame(columns=COLUMNAS)
    out = pd.DataFrame(filas)[COLUMNAS]
    _registrar(nombre, "Secundaria", "Nacional/Regional", "INTEGRADA", len(out))
    _log("Banco Mundial: {} observaciones".format(len(out)))
    return out


# ---------------------------------------------------------------------------
# 7. IDEAM (Colombia) via datos abiertos - PRIMARIA (red de estaciones).
#    Endpoint Socrata (datos.gov.co). Requiere el identificador del recurso;
#    se descarga con acceso abierto a internet.
# ---------------------------------------------------------------------------
def fuente_ideam():
    nombre = "IDEAM - Datos abiertos de clima e hidrologia (Colombia)"
    import urllib.parse
    recurso = os.environ.get("IDEAM_DATASET_ID", "sbwg-7ju4")  # temperatura por estacion
    where = ("fechaobservacion between '{}-01-01T00:00:00' and "
             "'{}-12-31T23:59:59'").format(YEAR_MIN, YEAR_MAX)
    params = urllib.parse.urlencode({"$limit": 50000, "$where": where})
    url = "https://www.datos.gov.co/resource/{}.csv?{}".format(recurso, params)
    txt = _descargar(url, timeout=60)
    if txt is None:
        _registrar(nombre, "Primaria", "Nacional", "OMITIDA (sin red)", 0)
        _log("IDEAM: host no alcanzable en este entorno; se omite (se integra al ejecutar con internet).")
        return pd.DataFrame(columns=COLUMNAS)
    try:
        df = pd.read_csv(io.StringIO(txt))
    except Exception:
        _registrar(nombre, "Primaria", "Nacional", "OMITIDA (formato)", 0)
        return pd.DataFrame(columns=COLUMNAS)
    col_fecha = next((c for c in df.columns if "fecha" in c.lower()), None)
    col_valor = next((c for c in df.columns if "valor" in c.lower()), None)
    if not col_fecha or not col_valor:
        _registrar(nombre, "Primaria", "Nacional", "OMITIDA (esquema)", 0)
        return pd.DataFrame(columns=COLUMNAS)
    df = df[[col_fecha, col_valor]].dropna()
    df["fecha_dt"] = pd.to_datetime(df[col_fecha], errors="coerce")
    df = df.dropna(subset=["fecha_dt"])
    df["anio"] = df["fecha_dt"].dt.year
    df["mes"] = df["fecha_dt"].dt.month
    df = df[(df["anio"] >= YEAR_MIN) & (df["anio"] <= YEAR_MAX)]
    out = pd.DataFrame({
        "fuente": nombre, "fuente_tipo": "Primaria",
        "nivel_geografico": "Nacional", "entidad": "Colombia", "iso_code": "COL",
        "anio": df["anio"], "mes": df["mes"], "periodicidad": "Mensual",
        "indicador": "Temperatura observada (estaciones IDEAM)",
        "valor": pd.to_numeric(df[col_valor], errors="coerce"),
        "unidad": "grados C", "fecha": df["fecha_dt"].dt.strftime("%Y-%m-%d"),
    }).dropna(subset=["valor"])[COLUMNAS]
    _registrar(nombre, "Primaria", "Nacional", "INTEGRADA", len(out))
    _log("IDEAM: {} observaciones".format(len(out)))
    return out


# ---------------------------------------------------------------------------
# 8. Eventos externos documentados (secundaria: documentacion oficial UNFCCC,
#    boletines ENSO de NOAA, reportes UNGRD). Dataset pequeno y curado a mano.
# ---------------------------------------------------------------------------
EVENTOS_DOC = [
    ("2020-08", "Inicio de fase La Nina 2020-2023 (ENSO frio, triple)", "Fenomeno climatico", "Global/Sudamerica", "NOAA CPC"),
    ("2021-11", "COP26 - Pacto Climatico de Glasgow", "Acuerdo climatico", "Global", "UNFCCC"),
    ("2021-11", "Segunda temporada de lluvias intensas por La Nina en Colombia", "Emergencia", "Nacional (Colombia)", "UNGRD/IDEAM"),
    ("2022-11", "COP27 - Fondo de perdidas y danos", "Acuerdo climatico", "Global", "UNFCCC"),
    ("2023-06", "Transicion a El Nino 2023-2024 (ENSO calido)", "Fenomeno climatico", "Global/Sudamerica", "NOAA CPC"),
    ("2023-12", "COP28 - Balance mundial y transicion de combustibles fosiles", "Acuerdo climatico", "Global", "UNFCCC"),
    ("2024-01", "Sequia y desabastecimiento por El Nino en Colombia", "Emergencia", "Nacional (Colombia)", "UNGRD/IDEAM"),
]


def escribir_eventos():
    df = pd.DataFrame(EVENTOS_DOC, columns=["fecha", "evento", "tipo", "ambito", "fuente"])
    df.to_csv(EVENTOS, index=False, encoding="utf-8")
    _log("eventos_externos_muestra.csv: {} eventos".format(len(df)))


# ---------------------------------------------------------------------------
# Orquestacion
# ---------------------------------------------------------------------------
def main():
    _log("Ventana temporal: {}-{}".format(YEAR_MIN, YEAR_MAX))
    partes = [
        fuente_owid_co2(),
        fuente_owid_energy(),
        fuente_mauna_loa(),
        fuente_temperatura_global(),
        fuente_nasa_power(),      # nacional/regional primaria (con internet)
        fuente_banco_mundial(),   # nacional/regional secundaria (con internet)
        fuente_ideam(),           # nacional primaria (con internet)
    ]
    df = pd.concat([p for p in partes if len(p)], ignore_index=True)

    df["anio"] = df["anio"].astype(int)
    df = df.sort_values(["nivel_geografico", "fuente", "entidad", "anio", "mes", "indicador"])
    df = df[COLUMNAS].reset_index(drop=True)

    df.to_csv(SALIDA, index=False, encoding="utf-8")
    pd.DataFrame(MANIFIESTO_FILAS).to_csv(MANIFIESTO, index=False, encoding="utf-8")
    escribir_eventos()

    _log("-" * 60)
    _log("TOTAL observaciones consolidadas: {}".format(len(df)))
    _log("Fuentes integradas: {}".format(df["fuente"].nunique()))
    _log("Indicadores distintos: {}".format(df["indicador"].nunique()))
    _log("Por nivel: {}".format(df["nivel_geografico"].value_counts().to_dict()))
    _log("Escrito: {}".format(SALIDA))
    if len(df) < 10000:
        _log("AVISO: por debajo de 10.000 (faltan fuentes con red). "
             "Ejecuta con acceso a internet para integrar NASA POWER / Banco Mundial / IDEAM.")


if __name__ == "__main__":
    sys.exit(main())
