"""
Script reproducible de preparacion de datos.

Este script documenta exactamente como se generaron los archivos que
estan en data/raw/, a partir de la fuente original (Our World in Data -
CO2 and Greenhouse Gas Emissions), sin modificar el archivo fuente.

Uso:
    1. Descargar el dataset original (no incluido en el repo por su tamano):
       https://github.com/owid/co2-data -> owid-co2-data.csv
    2. Guardarlo, por ejemplo, en data/processed/owid-co2-data.csv
    3. Ejecutar: python scripts/preparar_datos.py

Fecha de referencia de la descarga original usada para esta version base:
2026-08-21 (ver README.md para el detalle de trazabilidad).
"""

import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTE_ORIGINAL = os.path.join(BASE_DIR, "data", "processed", "owid-co2-data.csv")
DESTINO = os.path.join(BASE_DIR, "data", "raw")

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
            "(owid-co2-data.csv) y colocalo en esa ruta antes de "
            "ejecutar este script."
        )
        return

    df = pd.read_csv(FUENTE_ORIGINAL)
    columnas = [c for c in COLUMNAS if c in df.columns]

    os.makedirs(DESTINO, exist_ok=True)

    world = df[(df.country == "World") & (df.year >= 1995)][columnas].sort_values("year")
    world.to_csv(os.path.join(DESTINO, "global_climate_owid_1995_2024.csv"), index=False)

    regional = df[(df.country == "South America") & (df.year >= 1995)][columnas].sort_values("year")
    regional.to_csv(os.path.join(DESTINO, "regional_sudamerica_owid_1995_2024.csv"), index=False)

    colombia = df[(df.country == "Colombia") & (df.year >= 1960)][columnas].sort_values("year")
    colombia.to_csv(os.path.join(DESTINO, "nacional_colombia_owid_1960_2024.csv"), index=False)

    print("Archivos generados en data/raw/:")
    print(f"  - global_climate_owid_1995_2024.csv ({len(world)} filas)")
    print(f"  - regional_sudamerica_owid_1995_2024.csv ({len(regional)} filas)")
    print(f"  - nacional_colombia_owid_1960_2024.csv ({len(colombia)} filas)")
    print(
        "\nNota: el dataset de eventos externos "
        "(eventos_externos_muestra.csv) se mantiene y edita manualmente, "
        "no se genera con este script."
    )


if __name__ == "__main__":
    preparar()
