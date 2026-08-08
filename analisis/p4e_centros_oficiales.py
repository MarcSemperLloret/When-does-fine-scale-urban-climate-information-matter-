#!/usr/bin/env python3
"""Centros de salud oficiales de la Generalitat frente a los de OpenStreetMap.

Los 64 centros usados hasta aqui salen de OSM filtrados por nombre. La
completitud de OSM en equipamiento sanitario no esta garantizada, y este estudio
ya ha encontrado suficientes fallos silenciosos como para no dar por buena una
capa sin contrastarla.

La capa oficial es `ca_centros_salud` de la Generalitat Valenciana, publicada en
dadesobertes.gva.es y localizada por el catalogo de datos.gob.es. El portal de
la Generalitat no respondia por su pagina principal, pero la URL directa del
recurso si.

Lo que se mide no es solo cuantos centros hay de mas o de menos, sino cuanto
cambia lo que depende de ellos: secciones alcanzables, distancia, poblacion
cubierta y --lo que importa-- el conjunto prioritario.

Salidas en salidas/tablas/p4e_*.csv
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p2_comparar_era5land import DATOS, TABLAS, UTM  # noqa: E402

URL = ("https://dadesobertes.gva.es/dataset/dc6c6d98-ea54-43bf-8445-1c654b4cc206/"
       "resource/aa9fc68a-2c93-468b-90e0-338ba0e7f806/download/"
       "ca_centros_salud_20260705.geojson")
H = {"User-Agent": "downbursts-cv-pilot/1.0 (investigacion academica)"}

MUNICIPIO = "46250"
V_MAYOR = 0.90
PRESUPUESTO_MIN = 15.0
PRIMARIA = (r"centre de salut|centro de salud|consultori|consultorio|"
            r"centre sanitari|ambulatori")


def descargar() -> gpd.GeoDataFrame:
    destino = DATOS / "centros_salud_gva.geojson"
    if not destino.exists():
        r = requests.get(URL, headers=H, timeout=300)
        r.raise_for_status()
        destino.write_bytes(r.content)
        print(f"  descargado {destino.name} ({len(r.content)/1e6:.1f} MB)")
    g = gpd.read_file(destino)
    print(f"  centros en la Comunitat: {len(g)}; columnas: {list(g.columns)[:12]}")
    return g


def distancias(G, e, origenes_lonlat, cent_lonlat):
    """Dijkstra multiorigen desde los centros hasta cada seccion."""
    Gu = ox.convert.to_undirected(G)
    nodos = ox.nearest_nodes(G, origenes_lonlat[0], origenes_lonlat[1])
    Gu.add_node("__o__")
    for n in set(nodos):
        Gu.add_edge("__o__", n, length=0.0)
    d = nx.single_source_dijkstra_path_length(Gu, "__o__", weight="length")
    ns = ox.nearest_nodes(G, cent_lonlat[0], cent_lonlat[1])
    return np.array([d.get(n, np.inf) for n in ns])


def main() -> None:
    print("capa oficial de la Generalitat")
    ofi = descargar()

    # Recorte al municipio y a atencion primaria.
    sec = pd.read_csv(TABLAS / "p4_secciones.csv", dtype={"CUSEC": str})
    g = gpd.read_file(f"zip://{DATOS / 'seccionado_2024.zip'}!SECC_CE_20240101.shp")
    g = g[g["CUSEC"].isin(sec["CUSEC"])].to_crs(UTM).merge(sec, on="CUSEC")
    muni = g.union_all()

    ofi = ofi.to_crs(UTM)
    col_nom = next((c for c in ofi.columns
                    if re.search(r"nom|denom|desc", c, re.I)), ofi.columns[0])
    col_tipo = next((c for c in ofi.columns if re.search(r"tipo|tipus|clas", c, re.I)), None)
    print(f"  campo de nombre: {col_nom}; campo de tipo: {col_tipo}")
    if col_tipo:
        print("  tipos:", ofi[col_tipo].value_counts().head(8).to_dict())

    dentro = ofi[ofi.geometry.within(muni.buffer(1500))].copy()
    print(f"  dentro del municipio (+1,5 km): {len(dentro)}")

    # OSM, tal como se venia usando.
    osm = pd.read_csv(DATOS / "servicios_sanitarios_osm.csv")
    osm["nombre"] = osm["nombre"].fillna("")
    osm = osm[osm["nombre"].str.contains(PRIMARIA, case=False, regex=True)]
    osm_g = gpd.GeoDataFrame(osm, geometry=gpd.points_from_xy(osm["lon"], osm["lat"]),
                             crs="EPSG:4326").to_crs(UTM)
    osm_dentro = osm_g[osm_g.geometry.within(muni.buffer(1500))]
    print(f"  OSM dentro del municipio (+1,5 km): {len(osm_dentro)}")

    # Emparejamiento por proximidad, para ver cuantos coinciden.
    if len(dentro) and len(osm_dentro):
        pares = gpd.sjoin_nearest(osm_dentro[["geometry"]], dentro[["geometry"]],
                                  how="left", max_distance=150, distance_col="d")
        emparejados = int(pares["d"].notna().sum())
        print(f"  OSM con un oficial a menos de 150 m: {emparejados} de {len(osm_dentro)}")
    else:
        emparejados = 0

    print("\naccesibilidad con cada capa")
    G = ox.load_graphml(DATOS / "red_peatonal_valencia.graphml")
    e = ox.graph_to_gdfs(G, nodes=False)
    cll = g.geometry.centroid.to_crs("EPSG:4326")
    alc_prev = g["alcanzable"].to_numpy()
    pob = g["pob_65"].to_numpy()

    filas = []
    for etq, capa in (("osm", osm_dentro), ("oficial", dentro)):
        ll = capa.to_crs("EPSG:4326")
        d = distancias(G, e, (ll.geometry.x.values, ll.geometry.y.values),
                       (cll.x.values, cll.y.values))
        t = d / V_MAYOR / 60
        alc = t <= PRESUPUESTO_MIN
        filas.append({
            "capa": etq, "n_centros": len(capa),
            "dist_mediana_m": round(float(np.median(d[np.isfinite(d)])), 0),
            "dist_p90_m": round(float(np.percentile(d[np.isfinite(d)], 90)), 0),
            "secciones_alcanzables": int(alc.sum()),
            "pct_pob65_alcanzable": round(100 * float(pob[alc].sum() / pob.sum()), 2),
        })
        g[f"t_{etq}"] = t
        g[f"alc_{etq}"] = alc

    comp = pd.DataFrame(filas)
    a, b = g["alc_osm"].to_numpy(), g["alc_oficial"].to_numpy()
    jac_alc = float((a & b).sum() / max((a | b).sum(), 1))
    cambian = int((a != b).sum())
    pob_cambia = float(pob[a != b].sum())

    # Conjunto prioritario por necesidad no cubierta, con cada capa.
    tops = {}
    for etq in ("osm", "oficial"):
        alc = g[f"alc_{etq}"].to_numpy()
        idx = np.where(alc)[0]
        n = max(int(0.20 * len(idx)), 1)
        score = pob[idx] * g[f"t_{etq}"].to_numpy()[idx]
        tops[etq] = set(idx[np.argsort(-score)[:n]])
    jac_top = len(tops["osm"] & tops["oficial"]) / len(tops["osm"] | tops["oficial"])

    resumen = {
        "n_osm": int(len(osm_dentro)), "n_oficial": int(len(dentro)),
        "osm_emparejados_150m": emparejados,
        "jaccard_secciones_alcanzables": round(jac_alc, 3),
        "secciones_que_cambian_alcance": cambian,
        "pob65_que_cambia_alcance": round(pob_cambia),
        "jaccard_conjunto_prioritario": round(jac_top, 3),
    }
    comp.to_csv(TABLAS / "p4e_comparacion_centros.csv", index=False, encoding="utf-8")
    (TABLAS / "p4e_resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n--- comparacion de capas ---")
    print(comp.to_string(index=False))
    print("\n--- efecto sobre las decisiones ---")
    print(json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
