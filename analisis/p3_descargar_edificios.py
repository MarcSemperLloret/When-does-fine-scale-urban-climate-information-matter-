#!/usr/bin/env python3
"""Edificios de Valencia con altura, desde Catastro INSPIRE.

Catastro publica los edificios como GML bajo el esquema INSPIRE Buildings, con
un fichero por municipio. Para Valencia capital es `A.ES.SDGC.BU.46900.zip`.

**El fichero que sirve es `buildingpart.gml`, no `building.gml`.** En este
municipio `building.gml` trae `numberOfFloorsAboveGround` vacio al cien por
cien, y su campo `value` **no es una altura sino la superficie construida en
metros cuadrados** (`officialAreaReference = grossFloorArea`, `value_uom = m2`).
Tomarlo por altura da una mediana de 80 m, que es absurda para Valencia, y ese
es exactamente el tipo de fallo que produce numeros validos y no avisa.

`buildingpart.gml` si trae las plantas, en el cien por cien de las partes, y
ademas por parte y no por edificio, lo que conserva la variacion de altura
dentro de una misma manzana --una torre sobre un zocalo son dos partes-- que es
justo lo que importa para proyectar sombras.

**Catastro no publica altura medida en ninguno de los dos ficheros.** La altura
se deriva de las plantas con un valor por planta que es un supuesto declarado,
no una calibracion, y que la Puerta 3 debera contrastar contra PNOA-LiDAR.

Salida: manuscrito3/datos/edificios_valencia.gpkg
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos"
UTM = "EPSG:25830"

URL = ("https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/46/"
       "46900-VALENCIA/A.ES.SDGC.BU.46900.zip")
H = {"User-Agent": "downbursts-cv-pilot/1.0 (investigacion academica)"}

# Altura por planta. Supuesto declarado, no calibrado: Catastro no publica
# altura medida. 3,0 m es el valor habitual para vivienda colectiva en Espana,
# y se anade un metro por el sobrealzado de cubierta y peto. La sensibilidad a
# este parametro debe entrar en el analisis de sombra, y contrastarse con
# PNOA-LiDAR antes de publicar.
METROS_POR_PLANTA = 3.0
SOBREALZADO_M = 1.0


def descargar() -> Path:
    z = DATOS / "catastro_edificios_46900.zip"
    if z.exists():
        print(f"  ya estaba: {z.name} ({z.stat().st_size/1e6:.1f} MB)")
        return z
    print("  descargando Catastro (puede tardar)...")
    r = requests.get(URL, headers=H, timeout=900)
    r.raise_for_status()
    z.write_bytes(r.content)
    print(f"  descargado: {z.name} ({len(r.content)/1e6:.1f} MB)")
    return z


def main() -> None:
    DATOS.mkdir(parents=True, exist_ok=True)
    z = descargar()
    with zipfile.ZipFile(z) as zf:
        nombres = zf.namelist()
    print(f"  contenido: {nombres[:6]}")

    parte = next(n for n in nombres if n.lower().endswith("buildingpart.gml"))
    print(f"  leyendo {parte}")
    g = gpd.read_file(f"zip://{z}!{parte}").to_crs(UTM)
    print(f"  partes de edificio: {len(g):,}")

    col = "numberOfFloorsAboveGround"
    if col not in g.columns:
        raise SystemExit(f"Falta {col}: el esquema del GML ha cambiado")
    g["plantas"] = pd.to_numeric(g[col], errors="coerce")

    # Guardia contra el fallo que ya ocurrio una vez: si el campo llega vacio,
    # abortar en vez de escribir un fichero de alturas nulas que parece valido.
    cobertura = float(g["plantas"].notna().mean())
    if cobertura < 0.5:
        raise SystemExit(f"Solo el {cobertura:.1%} de las partes trae plantas; "
                         "revisar el fichero antes de seguir")
    print(f"  plantas informadas en el {cobertura:.1%} de las partes")

    g = g[g["plantas"].between(1, 60)].copy()
    g["altura_m"] = g["plantas"] * METROS_POR_PLANTA + SOBREALZADO_M
    g = g[g.geometry.notna() & ~g.geometry.is_empty]
    g["area_m2"] = g.geometry.area

    salida = DATOS / "edificios_valencia.gpkg"
    g[["plantas", "altura_m", "area_m2", "geometry"]].to_file(
        salida, driver="GPKG", layer="edificios")

    print(f"\n  guardadas {len(g):,} partes en {salida.name}")
    print(f"  plantas: mediana {g['plantas'].median():.0f}, "
          f"P90 {g['plantas'].quantile(0.9):.0f}, max {g['plantas'].max():.0f}")
    print(f"  altura derivada: mediana {g['altura_m'].median():.1f} m, "
          f"P90 {g['altura_m'].quantile(0.9):.1f} m, max {g['altura_m'].max():.1f} m")
    print(f"  supuesto: {METROS_POR_PLANTA} m/planta + {SOBREALZADO_M} m "
          "(Catastro no publica altura medida)")
    print(f"  superficie edificada total: {g['area_m2'].sum()/1e6:.2f} km2")


if __name__ == "__main__":
    main()
