"""
Script reproducible de preparacion de datos - Proyecto ClimaTec.

Genera el ecosistema de datos de la Etapa 1 a partir de la fuente original
(Our World in Data - CO2 and Greenhouse Gas Emissions), SIN modificar el
archivo fuente. Deja trazabilidad completa de todas las transformaciones.

Fuente original:
    https://github.com/owid/co2-data  ->  owid-co2-data.csv
    (descarga directa: https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv)

Uso:
    1. Colocar owid-co2-data.csv en data/processed/  (no se versiona por tamano)
    2. Ejecutar:  python scripts/preparar_datos.py

Transformaciones aplicadas (documentadas para trazabilidad):
    - Seleccion de 14 columnas relevantes (de las 79 originales).
    - Filtro temporal: year >= 1950  (mejor completitud que el historico completo).
    - Mapeo de nivel_geografico:
        * Global   = "World"
        * Regional = 6 agregados continentales (Africa, Asia, Europe,
                     North America, Oceania, South America)
        * Nacional = 218 paises con codigo ISO3 (incluye Colombia)
    - Salida principal: data/raw/clima_consolidado.csv  (>10.000 registros)
    - Se conservan ademas 3 vistas de apoyo (World / South America / Colombia)
      y el dataset manual de eventos externos.
"""

import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTE_ORIGINAL = os.path.join(BASE_DIR, "data", "processed", "owid-co2-data.csv")
DESTINO = os.path.join(BASE_DIR, "data", "raw")

ANIO_MIN = 1950
CONTINENTES = ["Africa", "Asia", "Europe", "North America", "Oceania", "South America"]

COLUMNAS = [
    "country", "year", "iso_code", "population",
    "co2", "co2_per_capita", "co2_growth_prct",
    "cumulative_co2", "ghg_excluding_lucf_per_capita",
    "temperature_change_from_ghg", "temperature_change_from_co2",
    "methane", "nitrous_oxide", "primary_energy_consumption",
]


def preparar():
    if not os.path.exists(FUENTE_ORIGINAL):
        print(
            "No se encontro el archivo fuente en:\n  "
            f"{FUENTE_ORIGINAL}\n"
            "Descargalo desde https://github.com/owid/co2-data "
            "(owid-co2-data.csv) y colocalo en esa ruta."
        )
        return

    df = pd.read_csv(FUENTE_ORIGINAL)
    cols = [c for c in COLUMNAS if c in df.columns]
    os.makedirs(DESTINO, exist_ok=True)

    # --- Dataset consolidado (el que usa la app para la Etapa 1) ---
    g = df[(df.country == "World") & (df.year >= ANIO_MIN)].copy()
    g["nivel_geografico"] = "Global"
    r = df[(df.country.isin(CONTINENTES)) & (df.year >= ANIO_MIN)].copy()
    r["nivel_geografico"] = "Regional"
    n = df[(df.iso_code.notna()) & (df.iso_code.str.len() == 3) & (df.year >= ANIO_MIN)].copy()
    n["nivel_geografico"] = "Nacional"

    consolidado = pd.concat([g, r, n], ignore_index=True)[cols + ["nivel_geografico"]]
    consolidado = consolidado.sort_values(["nivel_geografico", "country", "year"])
    consolidado.to_csv(os.path.join(DESTINO, "clima_consolidado.csv"), index=False)

    # --- Vistas de apoyo (trazabilidad / narrativa por nivel) ---
    world = df[(df.country == "World") & (df.year >= 1995)][cols].sort_values("year")
    world.to_csv(os.path.join(DESTINO, "global_climate_owid_1995_2024.csv"), index=False)
    sudam = df[(df.country == "South America") & (df.year >= 1995)][cols].sort_values("year")
    sudam.to_csv(os.path.join(DESTINO, "regional_sudamerica_owid_1995_2024.csv"), index=False)
    col = df[(df.country == "Colombia") & (df.year >= 1960)][cols].sort_values("year")
    col.to_csv(os.path.join(DESTINO, "nacional_colombia_owid_1960_2024.csv"), index=False)

    print("Archivos generados en data/raw/:")
    print(f"  - clima_consolidado.csv ({len(consolidado)} filas)  <- dataset principal Etapa 1")
    print(f"      Global:   {(consolidado.nivel_geografico=='Global').sum()} filas")
    print(f"      Regional: {(consolidado.nivel_geografico=='Regional').sum()} filas")
    print(f"      Nacional: {(consolidado.nivel_geografico=='Nacional').sum()} filas")
    print(f"  - global_climate_owid_1995_2024.csv ({len(world)} filas)")
    print(f"  - regional_sudamerica_owid_1995_2024.csv ({len(sudam)} filas)")
    print(f"  - nacional_colombia_owid_1960_2024.csv ({len(col)} filas)")
    print("  - eventos_externos_muestra.csv (se mantiene manual)")


if __name__ == "__main__":
    preparar()
