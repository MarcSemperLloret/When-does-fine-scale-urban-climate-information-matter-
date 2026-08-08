#!/usr/bin/env python3
"""Capa canonica de destinos: centros de atencion primaria.

Un unico sitio del que leen todos los scripts, para que no vuelva a haber dos
definiciones de destino conviviendo en el mismo analisis.

**Escenario primario: la capa oficial de la Generalitat** (`ca_centros_salud`).
OSM queda como analisis de sensibilidad de la capa de destinos, no como fuente.
El contraste entre ambas esta en `INFORME_CENTROS_OFICIALES.md`: solo 36 de los
56 centros de OSM tienen un oficial a menos de 150 m, y con **menos** centros
(48 frente a 56) la capa oficial alcanza **mas** poblacion (74,4 % frente a
68,6 %), porque el error de OSM era de distribucion espacial y no de recuento.

Se selecciona con la variable de entorno CENTROS=oficial|osm.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

DATOS = Path(__file__).resolve().parents[1] / "datos"
UTM = "EPSG:25830"
FUENTE = os.environ.get("CENTROS", "oficial")

# Radio de holgura alrededor del municipio: un residente del borde puede usar un
# centro del municipio vecino, y excluirlos crearia un efecto de borde.
MARGEN_M = 1500

PRIMARIA_OSM = (r"centre de salut|centro de salud|consultori|consultorio|"
                r"centre sanitari|ambulatori")


def cargar(recorte_geom=None) -> pd.DataFrame:
    """Devuelve los centros con columnas lon, lat, nombre, fuente."""
    if FUENTE == "oficial":
        g = gpd.read_file(DATOS / "centros_salud_gva.geojson").to_crs(UTM)
        col = next((c for c in g.columns if re.search(r"desc|nom", c, re.I)), g.columns[0])
        g = g.rename(columns={col: "nombre"})
    elif FUENTE == "osm":
        d = pd.read_csv(DATOS / "servicios_sanitarios_osm.csv")
        d["nombre"] = d["nombre"].fillna("")
        d = d[d["nombre"].str.contains(PRIMARIA_OSM, case=False, regex=True)]
        g = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(d["lon"], d["lat"]),
                             crs="EPSG:4326").to_crs(UTM)
    else:
        raise SystemExit(f"CENTROS={FUENTE} no valido; usar 'oficial' u 'osm'")

    if recorte_geom is not None:
        g = g[g.geometry.within(recorte_geom.buffer(MARGEN_M))]

    ll = g.to_crs("EPSG:4326")
    out = pd.DataFrame({"lon": ll.geometry.x.values, "lat": ll.geometry.y.values,
                        "nombre": g["nombre"].astype(str).values})
    out["fuente"] = FUENTE
    if len(out) < 20:
        raise SystemExit(f"Solo {len(out)} centros con CENTROS={FUENTE}: revisar la capa")
    return out
