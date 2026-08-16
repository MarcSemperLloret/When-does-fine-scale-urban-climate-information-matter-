#!/usr/bin/env python3
"""Los 91 niveles del campo AVAMET, son informacion o son el interpolador?

El contraste "ERA5-Land da 3 valores distintos, AVAMET da 91" es
descriptivamente correcto pero puede exagerar la diferencia de informacion
efectiva: los 91 salen de interpolar seis estaciones sobre 591 secciones, no de
591 sensores. Un revisor puede sostener que la riqueza espacial la fabrica la
ponderacion inversa y no los datos.

Tres controles, de mas a menos directo:

1. **Comparacion en las propias estaciones.** Sin interpolador de por medio:
   cuantas celdas distintas de ERA5-Land tocan las seis estaciones, y cuanto
   difieren de la observacion en cada una. Si ERA5-Land no distingue dos
   estaciones separadas por 1,2 C, el problema es del producto y no del metodo.

2. **Leave-one-station-out del campo.** Se reconstruye el campo de cada seccion
   **sin la estacion mas proxima**. Si la priorizacion sigue cambiando frente a
   ERA5-Land, la estructura no la sostiene el vecino inmediato.

3. **Sensibilidad del interpolador.** Potencia de la IDW y numero de vecinos.
   Si la conclusion depende de p=2 o de usar las seis, es fragil.

Salidas en salidas/tablas/p2b_*.csv
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from p2_comparar_era5land import (BARRIOS, DATOS, TABLAS, UTM, campo_era5,  # noqa: E402
                                  clasificar)

VENTANA = [16, 17, 18]   # la tarde, que es la ventana con mas senal
UMBRAL = 30.0


def series_estaciones(horas):
    df = pd.read_parquet(DATOS / "valencia_verano_qc.parquet")
    df = df[df["station_id"].isin(BARRIOS)].copy()
    df["hora"] = df["observed_local"].dt.hour
    hor = (df.groupby(["station_id", "date", "hora"], observed=True)["t_qc"]
             .mean().reset_index())
    est = df.groupby("station_id")[["latitude", "longitude"]].first()
    ge = gpd.GeoDataFrame(est, geometry=gpd.points_from_xy(est["longitude"], est["latitude"]),
                          crs="EPSG:4326").to_crs(UTM)
    # Aqui SI se exigen las seis simultaneamente, y no es un descuido: este
    # script alimenta una comparacion **entre estaciones** (rango observado,
    # excedencias por estacion) y el control del interpolador. Si cada estacion
    # aportase horas distintas, el rango entre ellas mezclaria muestras y dejaria
    # de medir heterogeneidad espacial. El campo sobre secciones de
    # p2_comparar_era5land si renormaliza, porque alli lo que importa es la
    # cobertura temporal y no el equilibrio entre estaciones.
    from p2_comparar_era5land import pivot_estaciones
    return pivot_estaciones(hor, horas, ge.index, min_estaciones=6), ge


def idw(cent, ge, piv, potencia=2.0, k=None, excluir_mas_proxima=False):
    d = np.sqrt((cent.x.values[:, None] - ge.geometry.x.values[None, :]) ** 2
                + (cent.y.values[:, None] - ge.geometry.y.values[None, :]) ** 2)
    d = np.maximum(d, 50.0)
    w = 1.0 / d ** potencia
    if excluir_mas_proxima:
        # Cada seccion se estima sin su estacion mas proxima: el equivalente
        # espacial de un leave-one-out, aplicado seccion a seccion.
        w[np.arange(len(d)), d.argmin(axis=1)] = 0.0
    if k is not None and k < w.shape[1]:
        umbral = np.partition(w, -k, axis=1)[:, -k][:, None]
        w = np.where(w >= umbral, w, 0.0)
    w = w / w.sum(axis=1, keepdims=True)
    from p2_comparar_era5land import idw_renormalizada
    return idw_renormalizada(w, piv)


def metricas(T, alcanzable, pob, ref=None):
    f = clasificar(T, UMBRAL, alcanzable)[alcanzable]
    out = {"sd_espacial": round(float(f.std()), 4),
           "rango_espacial": round(float(f.max() - f.min()), 4),
           "valores_distintos": int(len(np.unique(f.round(6))))}
    if ref is not None:
        n = max(int(0.20 * alcanzable.sum()), 1)
        p = pob[alcanzable]
        t1 = set(pd.Series(p * (1 - f)).nlargest(n).index)
        t2 = set(pd.Series(p * (1 - ref)).nlargest(n).index)
        out["jaccard_vs_referencia"] = round(len(t1 & t2) / len(t1 | t2), 3)
        out["spearman_vs_referencia"] = round(
            float(pd.Series(f).corr(pd.Series(ref), method="spearman")), 3)
    return out


def main() -> None:
    sec = pd.read_csv(TABLAS / "p4_secciones.csv", dtype={"CUSEC": str})
    g = gpd.read_file(f"zip://{DATOS / 'seccionado_2024.zip'}!SECC_CE_20240101.shp")
    g = g[g["CUSEC"].isin(sec["CUSEC"])].to_crs(UTM).merge(sec, on="CUSEC")
    cent = g.geometry.centroid
    alcanzable = g["alcanzable"].to_numpy()
    pob = g["pob_65"].to_numpy()

    piv, ge = series_estaciones(VENTANA)
    inv = pd.read_csv(TABLAS / "p0_inventario_estaciones.csv", index_col=0)

    # ------------------------------------------- 1. en las propias estaciones
    T_e5_est, idx_e5, _ = campo_era5(gpd.GeoSeries(ge.geometry, crs=UTM), VENTANA)
    comun = piv.index.intersection(idx_e5)
    obs = piv.loc[comun].to_numpy().T                  # 6 x horas
    e5 = T_e5_est[:, idx_e5.get_indexer(comun)]        # 6 x horas

    est_tab = []
    for i, sid in enumerate(ge.index):
        est_tab.append({
            "station_id": sid,
            "nombre": inv.loc[sid, "nombre"].replace("València - ", ""),
            "T_obs_media": round(float(obs[i].mean()), 2),
            "T_era5_media": round(float(e5[i].mean()), 2),
            "sesgo_era5": round(float(e5[i].mean() - obs[i].mean()), 2),
            "pct_horas_ge30_obs": round(100 * float((obs[i] >= UMBRAL).mean()), 1),
            "pct_horas_ge30_era5": round(100 * float((e5[i] >= UMBRAL).mean()), 1),
        })
    est_df = pd.DataFrame(est_tab)
    # Cuantas celdas distintas de ERA5-Land tocan las seis estaciones.
    celdas = len(np.unique(e5.round(6), axis=0))
    est_df.to_csv(TABLAS / "p2b_en_estaciones.csv", index=False, encoding="utf-8")

    # ------------------------------------------------------ 2 y 3. el campo
    ref_full = clasificar(idw(cent, ge, piv), UMBRAL, alcanzable)[alcanzable]
    variantes = {
        "idw_p2_todas": dict(potencia=2.0),
        "idw_p1_todas": dict(potencia=1.0),
        "idw_p3_todas": dict(potencia=3.0),
        "idw_p2_k3": dict(potencia=2.0, k=3),
        "idw_p2_sin_mas_proxima": dict(potencia=2.0, excluir_mas_proxima=True),
        "idw_p2_k3_sin_mas_proxima": dict(potencia=2.0, k=3, excluir_mas_proxima=True),
    }
    filas = []
    for nombre, kw in variantes.items():
        m = metricas(idw(cent, ge, piv, **kw), alcanzable, pob, ref_full)
        m["variante"] = nombre
        filas.append(m)

    # ERA5-Land con correccion de sesgo, para tener la misma escala.
    T_e5_sec, idx2, _ = campo_era5(gpd.GeoSeries(cent, crs=UTM), VENTANA)
    T_av_sec = idw(cent, ge, piv)
    c2 = piv.index.intersection(idx2)
    T_e5_sec = T_e5_sec[:, idx2.get_indexer(c2)]
    T_av_sec = T_av_sec[:, piv.index.get_indexer(c2)]
    T_e5_sec = T_e5_sec + (np.nanmean(T_av_sec) - np.nanmean(T_e5_sec))
    ref2 = clasificar(T_av_sec, UMBRAL, alcanzable)[alcanzable]
    m = metricas(T_e5_sec, alcanzable, pob, ref2)
    m["variante"] = "era5_sesgo_corregido"
    filas.append(m)

    var = pd.DataFrame(filas)[["variante", "sd_espacial", "rango_espacial",
                               "valores_distintos", "jaccard_vs_referencia",
                               "spearman_vs_referencia"]]
    var.to_csv(TABLAS / "p2b_sensibilidad_interpolador.csv", index=False, encoding="utf-8")

    (TABLAS / "p2b_resumen.json").write_text(json.dumps({
        "celdas_era5_distintas_en_6_estaciones": int(celdas),
        "rango_observado_entre_estaciones_c": round(
            float(obs.mean(axis=1).max() - obs.mean(axis=1).min()), 2),
        "rango_era5_entre_estaciones_c": round(
            float(e5.mean(axis=1).max() - e5.mean(axis=1).min()), 2),
        "rango_pct_ge30_observado": round(
            float(est_df["pct_horas_ge30_obs"].max() - est_df["pct_horas_ge30_obs"].min()), 1),
        "rango_pct_ge30_era5": round(
            float(est_df["pct_horas_ge30_era5"].max() - est_df["pct_horas_ge30_era5"].min()), 1),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print("--- 1. comparacion en las seis estaciones, sin interpolador ---")
    print(est_df.to_string(index=False))
    print(f"\n  celdas ERA5-Land distintas que tocan las 6 estaciones: {celdas}")
    print(f"  rango entre estaciones: observado {obs.mean(axis=1).max()-obs.mean(axis=1).min():.2f} C, "
          f"ERA5-Land {e5.mean(axis=1).max()-e5.mean(axis=1).min():.2f} C")
    print(f"  rango de % de horas >=30 C: observado "
          f"{est_df['pct_horas_ge30_obs'].max()-est_df['pct_horas_ge30_obs'].min():.1f} pp, "
          f"ERA5-Land {est_df['pct_horas_ge30_era5'].max()-est_df['pct_horas_ge30_era5'].min():.1f} pp")
    print("\n--- 2 y 3. sensibilidad del interpolador (referencia: IDW p=2 con las seis) ---")
    print(var.to_string(index=False))


if __name__ == "__main__":
    main()
