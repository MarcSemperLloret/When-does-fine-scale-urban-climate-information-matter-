"""Reviewer-motivated robustness of the 29-site results (added 4 October 2026, after the
peer-review simulation; exploratory, not in the dated plan).

1. How many distinct corrected ERA5-Land values (cells) the 29 sites sample.
2. Leave-one-site-out ranges of the easting gradient and pattern correlations.
3. Seven-day block-bootstrap interval of the relative spatial-MAE gain of IDW over
   the uniform field (same blocks and seed as Supplementary Material 1, S9).
Usage: python robustez_sitios.py <validacion_vituclim_2025>
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

VIT = Path(sys.argv[1])
UC = Path(__file__).resolve().parent.parent
pairs = pd.read_parquet(VIT / "matched_pairs.parquet")
st = pd.read_parquet(VIT / "stations_selected.parquet")
xy = gpd.GeoSeries(gpd.points_from_xy(st.longitude, st.latitude), crs=4326).to_crs("EPSG:25830")
east = pd.Series(xy.x.to_numpy() / 1000, index=st.station_id.astype(int))
DAYS = pd.date_range("2025-06-01", "2025-08-31")
out = {}
for (clock, window), z in pairs.groupby(["clock", "window"]):
    n = z.groupby("timestamp")["station_id"].transform("size")
    z = z[n >= 20].copy()
    for c in ["observed", "IDW", "Uniform", "ERA5_corrected"]:
        z[c + "_a"] = z[c] - z.groupby("timestamp")[c].transform("mean")
    for m in ["IDW", "Uniform"]:
        e = z[m] - z["observed"]
        z[m + "_r"] = (e - e.groupby(z["timestamp"]).transform("mean")).abs()
    s = z.groupby("station_id")[["observed_a", "IDW_a", "ERA5_corrected_a"]].mean()
    x = east.reindex(s.index)
    # Compare identical hours across all sites: different observation gaps must
    # not make sites in the same reanalysis cell appear to occupy different cells.
    era5_panel = z.pivot_table(index="timestamp", columns="station_id", values="ERA5_corrected")
    era5_complete = era5_panel.dropna(axis=0, how="any")
    if era5_complete.empty:
        raise ValueError(f"No complete site-hours available for {window}, {clock}")
    era5_cells = era5_complete.T.round(4)
    n_cells = int(era5_cells.drop_duplicates().shape[0])
    loo = {"rho_east_obs": [], "slope_obs_per10km": [], "rho_obs_IDW": [], "rho_obs_ERA5": []}
    for sid in s.index:
        t = s.drop(sid)
        xt = x.drop(sid)
        loo["rho_east_obs"].append(spearmanr(xt, t.observed_a).statistic)
        loo["slope_obs_per10km"].append(10 * np.polyfit(xt, t.observed_a, 1)[0])
        loo["rho_obs_IDW"].append(spearmanr(t.observed_a, t.IDW_a).statistic)
        loo["rho_obs_ERA5"].append(spearmanr(t.observed_a, t.ERA5_corrected_a).statistic)
    # block bootstrap of relative spatial-MAE gain
    z["day"] = z["timestamp"].dt.normalize()
    daily = z.groupby("day")[["IDW_r", "Uniform_r"]].agg(["sum", "count"])
    S = np.stack([daily[("IDW_r", "sum")].reindex(DAYS, fill_value=0).to_numpy(),
                  daily[("Uniform_r", "sum")].reindex(DAYS, fill_value=0).to_numpy()])
    C = daily[("IDW_r", "count")].reindex(DAYS, fill_value=0).to_numpy()
    rng = np.random.default_rng(20260921)
    gains = []
    for _ in range(1000):
        start = rng.integers(0, 92, size=14)
        ix = ((start[:, None] + np.arange(7)[None, :]) % 92).ravel()[:92]
        gains.append(100 * (1 - S[0, ix].sum() / S[1, ix].sum()))
    point = 100 * (1 - z["IDW_r"].mean() / z["Uniform_r"].mean())
    out[f"{window}_{clock}"] = dict(
        distinct_era5_cells=n_cells,
        complete_site_hours_for_cell_count=int(len(era5_complete)),
        distinct_era5_site_anomalies=int(s.ERA5_corrected_a.round(3).nunique()),
        loo_range={k: [float(min(v)), float(max(v))] for k, v in loo.items()},
        spatial_mae_gain_pct=float(point),
        spatial_mae_gain_ci95=np.quantile(gains, [.025, .975]).tolist())
path = UC / "control_interno/robustez_sitios_2026-10-04.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(out, indent=1), encoding="utf-8")
for k, v in out.items():
    print(k, v["distinct_era5_cells"], {a: [round(b, 2) for b in r] for a, r in v["loo_range"].items()},
          round(v["spatial_mae_gain_pct"], 1), [round(g, 1) for g in v["spatial_mae_gain_ci95"]])
