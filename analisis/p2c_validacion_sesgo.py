#!/usr/bin/env python3
"""Cierre de la correccion de sesgo de ERA5-Land: fuera de muestra y por regimen.

Tres cosas, en este orden.

**1. Nomenclatura de signo, blindada.** La inversion de signo del informe
anterior costo una afirmacion equivocada sobre la direccion del error de
politica. Aqui las tres magnitudes tienen nombres que no se pueden confundir, y
hay una prueba que falla si alguna vez dejan de cumplir su definicion:

    raw_error_era5_minus_obs      = T_era5 - T_obs      (positivo => ERA5 calido)
    additive_correction_obs_minus_era5 = T_obs - T_era5 = -raw_error
    corrected_era5                = T_era5 + additive_correction

**2. Validacion temporal.** La correccion se ajustaba sobre las mismas horas en
que despues se evaluaba, de modo que estaba sobreajustada. Se pasa a
leave-one-summer-out: cinco veranos ajustan, el sexto evalua. 2024 sigue
cerrado.

**3. Mecanismo costero.** Que el error crezca hacia el mar es compatible con una
brisa marina no resuelta, pero no lo demuestra. La prediccion contrastable es
que la pendiente transversal del error se intensifique con brisa y se reduzca
con poniente. Para cada hora se ajusta

    e_it = alpha_t + beta_t * d_i,costa + eps_it

sobre las seis estaciones, y se compara la distribucion de beta_t entre
regimenes con bootstrap por dia. Con seis estaciones no se sostiene una
inferencia sobre una sola correlacion espacial; la repeticion temporal
condicionada por regimen si.

Salidas en salidas/tablas/p2c_*.csv
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p2_comparar_era5land import BARRIOS, DATOS, TABLAS, UTM, campo_era5  # noqa: E402

VENTANAS = {"manana_10_12": [10, 11, 12], "tarde_16_18": [16, 17, 18]}
UMBRAL = 30.0
VERANOS = [2019, 2020, 2021, 2022, 2023, 2025]
RNG = np.random.default_rng(20260807)
N_BOOT = 500

# Regimen a partir de la direccion media del viento en la ventana, promediada
# vectorialmente sobre las seis estaciones. Los sectores son los del informe de
# viabilidad, para no introducir una definicion nueva a mitad de estudio.
SECTORES = [(45, 135, "brisa_E"), (225, 315, "poniente_W")]
VIENTO_DEBIL_KMH = 6.0


def series_observadas(horas):
    df = pd.read_parquet(DATOS / "valencia_verano_qc.parquet")
    df = df[df["station_id"].isin(BARRIOS)].copy()
    df["hora"] = df["observed_local"].dt.hour
    df = df[df["hora"].isin(horas)]
    hor = (df.groupby(["station_id", "date", "hora"], observed=True)
             .agg(t=("t_qc", "mean"), v=("wind_mean_kmh", "mean"),
                  dir=("wind_direction_deg", "mean"))
             .reset_index())
    obs = hor.pivot_table(index=["date", "hora"], columns="station_id", values="t").dropna()
    vel = hor.pivot_table(index=["date", "hora"], columns="station_id", values="v")
    dirn = hor.pivot_table(index=["date", "hora"], columns="station_id", values="dir")
    est = df.groupby("station_id")[["latitude", "longitude"]].first()
    ge = gpd.GeoDataFrame(est, geometry=gpd.points_from_xy(est["longitude"], est["latitude"]),
                          crs="EPSG:4326").to_crs(UTM)
    return obs[list(ge.index)], vel.reindex(obs.index), dirn.reindex(obs.index), ge


def regimen(dirn, vel):
    """Un regimen por hora, del promedio vectorial de direccion de la red."""
    rad = np.radians(dirn.to_numpy())
    ang = (np.degrees(np.arctan2(np.nanmean(np.sin(rad), axis=1),
                                 np.nanmean(np.cos(rad), axis=1))) % 360)
    v = np.nanmean(vel.to_numpy(), axis=1)
    r = np.full(len(ang), "otro", dtype=object)
    for lo, hi, nombre in SECTORES:
        r[(ang >= lo) & (ang < hi)] = nombre
    r[v < VIENTO_DEBIL_KMH] = "viento_debil"
    return pd.Series(r, index=dirn.index, name="regimen")


def prueba_de_signo(era5, obs) -> None:
    """Falla si las tres magnitudes dejan de cumplir su definicion."""
    raw = era5 - obs
    corr = -raw
    corregido = era5 + corr.mean()
    assert np.allclose(corr, obs - era5), "additive_correction no es obs - era5"
    assert abs(float((corregido - obs).mean()) - 0.0) < 1e-9, \
        "corrected_era5 no queda centrado sobre las observaciones"
    signo = "calido" if raw.mean() > 0 else "frio"
    print(f"  prueba de signo OK: raw_error_era5_minus_obs = {raw.mean():+.2f} C "
          f"=> ERA5-Land es {signo} respecto a la observacion")


def main() -> None:
    inv = pd.read_csv(TABLAS / "p0_inventario_estaciones.csv", index_col=0)
    filas_val, filas_beta, filas_est = [], [], []

    for v, horas in VENTANAS.items():
        print(f"\n== {v} ==")
        obs, vel, dirn, ge = series_observadas(horas)
        era5_arr, idx_e5, _ = campo_era5(gpd.GeoSeries(ge.geometry, crs=UTM), horas)
        comun = obs.index.intersection(idx_e5)
        obs = obs.loc[comun]
        era5 = pd.DataFrame(era5_arr[:, idx_e5.get_indexer(comun)].T,
                            index=comun, columns=obs.columns)
        reg = regimen(dirn.loc[comun], vel.loc[comun])

        raw_error_era5_minus_obs = era5 - obs
        prueba_de_signo(era5.to_numpy(), obs.to_numpy())

        # --------------------------------------- 2. leave-one-summer-out
        anios = pd.DatetimeIndex(comun.get_level_values("date")).year
        for fuera in VERANOS:
            entrena, evalua = anios != fuera, anios == fuera
            if evalua.sum() < 50 or entrena.sum() < 50:
                continue
            # Correccion global y por hora, ajustadas SOLO con los otros veranos.
            c_glob = float((obs[entrena] - era5[entrena]).to_numpy().mean())
            c_hora = {h: float((obs[entrena] - era5[entrena])
                               .loc[comun[entrena].get_level_values("hora") == h]
                               .to_numpy().mean())
                      for h in horas}
            h_ev = comun[evalua].get_level_values("hora").to_numpy()
            corr_h = np.array([c_hora[h] for h in h_ev])[:, None]

            for nombre, corregido in (("global", era5[evalua] + c_glob),
                                      ("por_hora", era5[evalua] + corr_h)):
                res = corregido.to_numpy() - obs[evalua].to_numpy()
                exc_obs = (obs[evalua].to_numpy() >= UMBRAL).mean(axis=0) * 100
                exc_cor = (corregido.to_numpy() >= UMBRAL).mean(axis=0) * 100
                filas_val.append({
                    "ventana": v, "verano_excluido": fuera, "correccion": nombre,
                    "n_horas_evaluacion": int(evalua.sum()),
                    "correccion_aplicada_c": round(c_glob if nombre == "global"
                                                   else float(np.mean(list(c_hora.values()))), 2),
                    "sesgo_residual_c": round(float(res.mean()), 3),
                    "rmse_c": round(float(np.sqrt((res ** 2).mean())), 3),
                    # Lo que de verdad importa: el error en la dispersion entre
                    # estaciones, que es lo que sostiene la priorizacion.
                    "rango_excedencia_obs_pp": round(float(exc_obs.max() - exc_obs.min()), 1),
                    "rango_excedencia_era5_pp": round(float(exc_cor.max() - exc_cor.min()), 1),
                    "error_medio_excedencia_pp": round(float(np.abs(exc_cor - exc_obs).mean()), 1),
                    "spearman_excedencia": round(float(
                        pd.Series(exc_obs).corr(pd.Series(exc_cor), method="spearman")), 3),
                })

        # --------------------------------------- 3. gradiente costero
        km = inv.loc[list(obs.columns), "km_costa"].to_numpy(dtype=float)
        km_c = km - km.mean()
        E = raw_error_era5_minus_obs.to_numpy()
        # beta_t por minimos cuadrados sobre las seis estaciones, hora a hora.
        beta = (E * km_c).sum(axis=1) / (km_c ** 2).sum()
        bt = pd.DataFrame({"beta": beta, "regimen": reg.to_numpy()}, index=comun)

        dias = pd.DatetimeIndex(comun.get_level_values("date"))
        udias = dias.unique()
        for r, sub in bt.groupby("regimen"):
            if len(sub) < 30:
                continue
            m = []
            for _ in range(N_BOOT):
                s = RNG.choice(udias, size=len(udias), replace=True)
                cols = np.concatenate([np.where(dias == d)[0] for d in s])
                vals = bt["beta"].to_numpy()[cols][bt["regimen"].to_numpy()[cols] == r]
                if len(vals):
                    m.append(vals.mean())
            lo, hi = np.percentile(m, [2.5, 97.5]) if m else (np.nan, np.nan)
            filas_beta.append({
                "ventana": v, "regimen": r, "n_horas": len(sub),
                "beta_medio_c_por_km": round(float(sub["beta"].mean()), 4),
                "ic_lo": round(float(lo), 4), "ic_hi": round(float(hi), 4),
                "significativo": bool(lo > 0 or hi < 0),
            })

        for i, sid in enumerate(obs.columns):
            filas_est.append({
                "ventana": v, "station_id": sid,
                "nombre": inv.loc[sid, "nombre"].replace("València - ", ""),
                "km_costa": round(float(km[i]), 2),
                "raw_error_era5_minus_obs": round(float(E[:, i].mean()), 2),
            })

    val = pd.DataFrame(filas_val)
    beta_df = pd.DataFrame(filas_beta)
    est_df = pd.DataFrame(filas_est)
    val.to_csv(TABLAS / "p2c_validacion_temporal.csv", index=False, encoding="utf-8")
    beta_df.to_csv(TABLAS / "p2c_gradiente_por_regimen.csv", index=False, encoding="utf-8")
    est_df.to_csv(TABLAS / "p2c_error_por_estacion.csv", index=False, encoding="utf-8")

    print("\n--- 2. correccion fuera de muestra (leave-one-summer-out) ---")
    print(val.groupby(["ventana", "correccion"]).agg(
        sesgo_residual_medio=("sesgo_residual_c", "mean"),
        sesgo_residual_max=("sesgo_residual_c", lambda s: s.abs().max()),
        rmse_medio=("rmse_c", "mean"),
        rango_exc_obs=("rango_excedencia_obs_pp", "mean"),
        rango_exc_era5=("rango_excedencia_era5_pp", "mean"),
        error_exc_pp=("error_medio_excedencia_pp", "mean"),
        spearman_exc=("spearman_excedencia", "mean")).round(3).to_string())
    print("\n  por verano excluido (correccion por hora):")
    print(val[val["correccion"] == "por_hora"][
        ["ventana", "verano_excluido", "sesgo_residual_c", "rmse_c",
         "rango_excedencia_obs_pp", "rango_excedencia_era5_pp",
         "spearman_excedencia"]].to_string(index=False))

    print("\n--- 3. pendiente costera del error por regimen (C por km al mar) ---")
    print(beta_df.to_string(index=False))
    print("\n  error medio por estacion:")
    print(est_df.to_string(index=False))

    (TABLAS / "p2c_resumen.json").write_text(json.dumps({
        "definicion_signo": {
            "raw_error_era5_minus_obs": "T_era5 - T_obs; positivo = ERA5-Land calido",
            "additive_correction_obs_minus_era5": "-raw_error; es lo que se SUMA a ERA5-Land",
            "corrected_era5": "T_era5 + additive_correction",
        },
        "veranos": VERANOS,
        "locked_excluido": 2024,
    }, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
