#!/usr/bin/env python3
"""Altura observada de LiDAR frente a la altura derivada de plantas catastrales.

Los nDSM normalizados del CNIG (MDSnE2,5, 2.a cobertura, hojas MTN50 0696, 0722
y 0747) dan altura de edificacion **sobre el terreno** a 2,5 m, que es
exactamente lo que el supuesto de `3,0 m/planta + 1,0 m` estaba sustituyendo.

Por cada parte de edificio de Catastro se toma la estadistica zonal del nDSM
dentro de su huella. Se reportan mediana, P75 y P90: los percentiles altos
existen porque el borde de la huella catastral y el borde real no coinciden, y
una celda de borde mezcla tejado con calle, de modo que la mediana subestima en
edificios pequenos. El P75 es el compromiso que se usa como altura de trabajo.

No se ajusta ninguna relacion Catastro -> LiDAR: se **sustituye** la altura, que
es mas simple y mas defendible.

Salidas:
  datos/edificios_valencia_lidar.gpkg
  salidas/tablas/p3_lidar_validacion.csv
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import rasterio.features
from rasterio.windows import from_bounds

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos"
TABLAS = BASE / "salidas" / "tablas"
UTM = "EPSG:25830"

HOJAS = ["0696", "0722", "0747"]
PLANTILLA = "NDSM-EDIFICIOS-H30-{}-COB2.tif"

# Minimo de celdas de 2,5 m dentro de la huella para que la estadistica zonal
# signifique algo. Cuatro celdas son 25 m2.
MIN_CELDAS = 4


def zonal(parts: gpd.GeoDataFrame) -> pd.DataFrame:
    """Estadistica zonal del nDSM por parte de edificio, hoja a hoja."""
    trozos = []
    for hoja in HOJAS:
        ruta = DATOS / PLANTILLA.format(hoja)
        with rasterio.open(ruta) as src:
            b = src.bounds
            sel = parts.cx[b.left:b.right, b.bottom:b.top]
            if sel.empty:
                continue
            x0, y0, x1, y1 = sel.total_bounds
            win = from_bounds(max(x0, b.left), max(y0, b.bottom),
                              min(x1, b.right), min(y1, b.top), src.transform)
            arr = src.read(1, window=win)
            tr = src.window_transform(win)
            print(f"  hoja {hoja}: {len(sel):,} partes, ventana {arr.shape}")

            # Se rasteriza el indice posicional de cada parte (+1 para que 0
            # quede como fondo) y se agrupa por el.
            ids = np.arange(1, len(sel) + 1, dtype="int32")
            idr = rasterio.features.rasterize(
                zip(sel.geometry, ids), out_shape=arr.shape, transform=tr,
                fill=0, dtype="int32")
            val = arr != src.nodata
            val &= np.isfinite(arr) & (arr > -1) & (arr < 250)
            m = (idr > 0) & val
            if not m.any():
                continue
            d = pd.DataFrame({"i": idr[m], "h": arr[m].astype("float32")})
            g = d.groupby("i")["h"].agg(
                n_celdas="size", h_mediana="median",
                h_p75=lambda s: s.quantile(0.75),
                h_p90=lambda s: s.quantile(0.90))
            g.index = sel.index[g.index.to_numpy() - 1]
            g["hoja"] = hoja
            trozos.append(g)
    out = pd.concat(trozos)
    # Una parte puede caer en el solape de dos hojas: se queda la que aporta
    # mas celdas, que es la que la contiene entera.
    return out.sort_values("n_celdas").groupby(level=0).last()


def main() -> None:
    print("Catastro")
    parts = gpd.read_file(DATOS / "edificios_valencia.gpkg", layer="edificios")
    parts = parts.to_crs(UTM)
    print(f"  {len(parts):,} partes")

    print("estadistica zonal del nDSM")
    z = zonal(parts)
    parts = parts.join(z)
    con = parts["n_celdas"].fillna(0) >= MIN_CELDAS
    print(f"  con estadistica utilizable: {con.sum():,} ({100*con.mean():.1f} %)")

    # Altura de trabajo: P75 del nDSM donde lo hay, y el supuesto catastral
    # como respaldo donde la huella es demasiado pequena o no hay dato.
    parts["altura_lidar_m"] = parts["h_p75"]
    parts["altura_final_m"] = np.where(con & parts["h_p75"].notna(),
                                       parts["h_p75"], parts["altura_m"])
    parts["fuente_altura"] = np.where(con & parts["h_p75"].notna(),
                                      "lidar_p75", "catastro_plantas")

    # ------------------------------------------------------- validacion
    v = parts[con & parts["h_p75"].notna()].copy()
    for etq, col in (("mediana", "h_mediana"), ("p75", "h_p75"), ("p90", "h_p90")):
        e = v["altura_m"].to_numpy() - v[col].to_numpy()   # catastral - lidar
        print(f"  catastral vs nDSM {etq}: sesgo {e.mean():+.2f} m, "
              f"MAE {np.abs(e).mean():.2f} m, RMSE {np.sqrt((e**2).mean()):.2f} m")

    e = v["altura_m"].to_numpy() - v["h_p75"].to_numpy()
    v = v.assign(err=e, tramo=pd.cut(v["plantas"], [0, 3, 6, 10, 60],
                                     labels=["1-3", "4-6", "7-10", ">10"]))
    por_tramo = v.groupby("tramo", observed=True).apply(
        lambda d: pd.Series({
            "n": len(d),
            "plantas_media": d["plantas"].mean(),
            "h_catastral_media": d["altura_m"].mean(),
            "h_lidar_media": d["h_p75"].mean(),
            "sesgo_m": d["err"].mean(),
            "mae_m": d["err"].abs().mean(),
            "error_rel_pct": 100 * (d["err"].abs() / d["h_p75"]).median(),
            "m_por_planta_lidar": ((d["h_p75"] - 1.0) / d["plantas"]).median(),
        }), include_groups=False).round(2)
    por_tramo.to_csv(TABLAS / "p3_lidar_por_tramo.csv")

    mpp = ((v["h_p75"] - 1.0) / v["plantas"])
    resumen = {
        "n_partes": int(len(parts)),
        "n_con_lidar": int(con.sum()),
        "pct_con_lidar": round(100 * float(con.mean()), 1),
        "sesgo_catastral_menos_lidar_m": round(float(e.mean()), 2),
        "mae_m": round(float(np.abs(e).mean()), 2),
        "rmse_m": round(float(np.sqrt((e ** 2).mean())), 2),
        "error_relativo_mediano_pct": round(
            100 * float(np.median(np.abs(e) / v["h_p75"])), 1),
        "metros_por_planta_lidar_mediana": round(float(mpp.median()), 2),
        "metros_por_planta_lidar_p25": round(float(mpp.quantile(0.25)), 2),
        "metros_por_planta_lidar_p75": round(float(mpp.quantile(0.75)), 2),
        "supuesto_previo": 3.0,
        "altura_mediana_catastral_m": round(float(parts["altura_m"].median()), 1),
        "altura_mediana_lidar_m": round(float(v["h_p75"].median()), 1),
    }
    (TABLAS / "p3_lidar_validacion.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

    parts[["plantas", "altura_m", "altura_lidar_m", "altura_final_m",
           "fuente_altura", "n_celdas", "h_mediana", "h_p75", "h_p90",
           "area_m2", "geometry"]].to_file(
        DATOS / "edificios_valencia_lidar.gpkg", driver="GPKG", layer="edificios")

    print("\n--- resumen ---")
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    print("\n--- por tramo de plantas ---")
    print(por_tramo.to_string())


if __name__ == "__main__":
    main()
