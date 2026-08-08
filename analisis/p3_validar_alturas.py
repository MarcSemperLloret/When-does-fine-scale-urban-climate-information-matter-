#!/usr/bin/env python3
"""Contraste independiente de la altura derivada de Catastro.

La altura de la capa de sombra es `3,0 m/planta + 1,0 m`, un supuesto sin
calibrar, y la longitud de la sombra es proporcional a ella. La validacion
correcta seria contra el modelo digital de superficies de PNOA-LiDAR.

**No esta disponible desde esta maquina.** El WCS del IGN
(`servicios.idee.es/wcs-inspire/mdt`) publica unicamente Modelos Digitales del
**Terreno** --suelo desnudo, sin edificios-- y el centro de descargas del CNIG
sirve el MDS mediante un formulario con sesion que no se puede automatizar
limpiamente. Queda pendiente y hay que decirlo asi en el articulo.

Lo que si se puede hacer es un contraste independiente con OpenStreetMap, que
es mas debil que el LiDAR pero no es circular respecto a Catastro:

  * 321 edificios con `height` en metros -> calibra metros por planta
  * 37.405 con `building:levels`        -> contrasta el recuento de plantas

Salidas en salidas/tablas/p3_validacion_alturas_*.csv
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos"
TABLAS = BASE / "salidas" / "tablas"
UTM = "EPSG:25830"

OVERPASS = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
H = {"User-Agent": "downbursts-cv-pilot/1.0 (investigacion academica)"}
CAJA = "39.28,-0.44,39.55,-0.29"

METROS_POR_PLANTA = 3.0
SOBREALZADO_M = 1.0


def descargar_osm() -> pd.DataFrame:
    destino = DATOS / "osm_alturas_edificios.csv"
    if destino.exists():
        print(f"  ya estaba: {destino.name}")
        return pd.read_csv(destino)
    q = f"""[out:json][timeout:300];
(
  nwr({CAJA})["building"]["height"];
  nwr({CAJA})["building"]["building:levels"];
);
out center tags;"""
    r = requests.post(OVERPASS, data={"data": q}, headers=H, timeout=600)
    r.raise_for_status()
    filas = []
    for el in r.json()["elements"]:
        t = el.get("tags", {})
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None:
            continue
        filas.append({"lat": lat, "lon": lon,
                      "height": t.get("height"), "levels": t.get("building:levels")})
    d = pd.DataFrame(filas)
    if len(d) < 1000:
        raise SystemExit(f"Solo {len(d)} edificios de OSM: revisar el endpoint")
    d.to_csv(destino, index=False, encoding="utf-8")
    print(f"  descargados {len(d):,} edificios de OSM con altura o plantas")
    return d


def numerico(s: pd.Series) -> pd.Series:
    """Los valores de OSM traen unidades y comas: '12 m', '3.5', '12,5'."""
    return pd.to_numeric(
        s.astype(str).str.replace(",", ".", regex=False)
                     .str.extract(r"(-?\d+\.?\d*)")[0], errors="coerce")


def main() -> None:
    print("OpenStreetMap")
    osm = descargar_osm()
    osm["h_osm"] = numerico(osm["height"])
    osm["plantas_osm"] = numerico(osm["levels"])
    g_osm = gpd.GeoDataFrame(
        osm, geometry=gpd.points_from_xy(osm["lon"], osm["lat"]),
        crs="EPSG:4326").to_crs(UTM)

    print("Catastro")
    cat = gpd.read_file(DATOS / "edificios_valencia.gpkg", layer="edificios")
    print(f"  {len(cat):,} partes")

    # Cada punto de OSM se asigna a la parte de Catastro que lo contiene; si no
    # cae dentro de ninguna, a la mas proxima dentro de 15 m.
    j = gpd.sjoin(g_osm, cat[["plantas", "altura_m", "geometry"]],
                  how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    sin = j["plantas"].isna()
    if sin.any():
        cerca = gpd.sjoin_nearest(g_osm[sin.to_numpy()],
                                  cat[["plantas", "altura_m", "geometry"]],
                                  how="left", max_distance=15)
        cerca = cerca[~cerca.index.duplicated(keep="first")]
        j.loc[cerca.index, ["plantas", "altura_m"]] = cerca[["plantas", "altura_m"]]
    print(f"  emparejados con Catastro: {j['plantas'].notna().sum():,} de {len(j):,}")

    resumen = {}

    # ------------------------------------------ 1. recuento de plantas
    a = j[j["plantas_osm"].between(1, 60) & j["plantas"].between(1, 60)]
    if len(a) > 50:
        d = a["plantas"].to_numpy() - a["plantas_osm"].to_numpy()
        resumen["plantas"] = {
            "n": int(len(a)),
            "bias_catastro_menos_osm": round(float(d.mean()), 3),
            "mae": round(float(np.abs(d).mean()), 3),
            "rmse": round(float(np.sqrt((d ** 2).mean())), 3),
            "pct_identicas": round(100 * float((d == 0).mean()), 1),
            "pct_dentro_de_1": round(100 * float((np.abs(d) <= 1).mean()), 1),
            "spearman": round(float(a["plantas"].corr(a["plantas_osm"], method="spearman")), 3),
        }
        a[["plantas", "plantas_osm"]].to_csv(
            TABLAS / "p3_validacion_alturas_plantas.csv", index=False)

    # -------------------------------- 2. metros por planta, con altura de OSM
    b = j[j["h_osm"].between(3, 200) & j["plantas"].between(1, 60)]
    if len(b) > 20:
        mpp = (b["h_osm"] / b["plantas"]).to_numpy()
        h_mod = b["plantas"].to_numpy() * METROS_POR_PLANTA + SOBREALZADO_M
        e = h_mod - b["h_osm"].to_numpy()
        resumen["metros_por_planta"] = {
            "n": int(len(b)),
            "mediana": round(float(np.median(mpp)), 2),
            "p25": round(float(np.percentile(mpp, 25)), 2),
            "p75": round(float(np.percentile(mpp, 75)), 2),
            "supuesto_actual": METROS_POR_PLANTA,
        }
        resumen["altura_modelada_vs_osm"] = {
            "bias_m": round(float(e.mean()), 2),
            "mae_m": round(float(np.abs(e).mean()), 2),
            "rmse_m": round(float(np.sqrt((e ** 2).mean())), 2),
            "error_relativo_mediano_pct": round(
                100 * float(np.median(np.abs(e) / b["h_osm"].to_numpy())), 1),
        }
        # Error segun altura, que es donde mas duele para la sombra.
        b = b.assign(err=e, tramo=pd.cut(b["plantas"], [0, 3, 6, 10, 60],
                                         labels=["1-3", "4-6", "7-10", ">10"]))
        por_tramo = b.groupby("tramo", observed=True)["err"].agg(
            n="size", bias="mean", mae=lambda s: s.abs().mean()).round(2)
        por_tramo.to_csv(TABLAS / "p3_validacion_alturas_por_tramo.csv")
        resumen["por_tramo_de_plantas"] = por_tramo.to_dict("index")

    (TABLAS / "p3_validacion_alturas.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("\n" + json.dumps(resumen, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
