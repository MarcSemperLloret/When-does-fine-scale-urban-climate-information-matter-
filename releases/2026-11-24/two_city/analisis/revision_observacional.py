"""Observational checks added in the 4 October 2026 revision.

A  Error decomposition at the 29 VITUclim sites: common (hourly panel-mean)
   offset versus spatial residual, per predictor, window and clock.
B  Time-averaged spatial pattern: do IDW and corrected ERA5-Land reproduce
   the observed site anomalies?
C  Coast-inland gradient: west-east position against observed site anomalies.
D  Simple-rule sufficiency against one reference at a time (288 cases).

The plan is fixed in plan_revision_observacional_2026-10-04.json. Portable usage:
    python analisis/revision_observacional.py --sm2 . --only sufficiency
Full upstream rerun (requires provider-dependent inputs):
    python analisis/revision_observacional.py --sm2 . --vit PATH --only all
Writes JSON and CSV to --out (default: qa/revision_observacional).
"""
from __future__ import annotations

import json
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
UC = HERE.parent
VIT = None
SM2 = UC
OUTPUT = UC / "qa/revision_observacional"
MODELS = ["IDW", "Uniform", "Nearest", "ERA5_corrected"]
MIN_SITES = 20
SEED = 20260921
NBOOT = 1000
DAYS = pd.date_range("2025-06-01", "2025-08-31")

pairs = None
east_km = None


def centred(z: pd.DataFrame) -> pd.DataFrame:
    """Keep hours with at least MIN_SITES sites and subtract the hourly panel mean."""
    n = z.groupby("timestamp").station_id.transform("size")
    z = z[n >= MIN_SITES].copy()
    for col in ["observed"] + MODELS:
        z[col + "_anom"] = z[col] - z.groupby("timestamp")[col].transform("mean")
    for m in MODELS:
        e = z[m] - z.observed
        z[m + "_err"] = e
        z[m + "_common"] = e.groupby(z.timestamp).transform("mean")
        z[m + "_resid"] = e - z[m + "_common"]
    z["day"] = z.timestamp.dt.normalize()
    return z


def decomposition(z: pd.DataFrame) -> dict:
    out = {}
    hourly = z.groupby("timestamp")
    for m in MODELS:
        common = hourly[m + "_common"].first()
        out[m] = dict(bias=float(z[m + "_err"].mean()), mae=float(z[m + "_err"].abs().mean()),
                      mean_abs_common=float(common.abs().mean()),
                      spatial_mae=float(z[m + "_resid"].abs().mean()))
    return out


ANOM = [c + "_anom" for c in ["observed"] + MODELS]


def site_stats(z: pd.DataFrame | None = None, s: pd.DataFrame | None = None) -> dict:
    """Site-level (time-averaged) anomaly pattern statistics."""
    if s is None:
        s = z.groupby("station_id")[ANOM].mean()
    x = east_km.reindex(s.index).to_numpy()
    o = s["observed_anom"].to_numpy()
    r = dict(n_sites=int(len(s)), sd_obs=float(o.std(ddof=1)),
             rho_east_obs=float(spearmanr(x, o).statistic),
             slope_obs_per10km=float(10 * np.polyfit(x, o, 1)[0]))
    for m in ["IDW", "Nearest", "ERA5_corrected"]:
        p = s[m + "_anom"].to_numpy()
        r[f"sd_{m}"] = float(p.std(ddof=1))
        r[f"rho_obs_{m}"] = float(spearmanr(o, p).statistic)
        r[f"amplitude_{m}"] = float(np.polyfit(o, p, 1)[0])
        r[f"rho_east_{m}"] = float(spearmanr(x, p).statistic)
    return r


def bootstrap(z: pd.DataFrame, rng: np.random.Generator) -> dict:
    """Seven-day circular blocks shared by all sites, as in Supplementary Material 1, S9."""
    sums = z.groupby(["day", "station_id"])[ANOM].sum()
    counts = z.groupby(["day", "station_id"]).size()
    stations = sorted(z.station_id.unique())
    full = pd.MultiIndex.from_product([DAYS, stations], names=["day", "station_id"])
    S = sums.reindex(full, fill_value=0).to_numpy().reshape(92, len(stations), len(ANOM))
    C = counts.reindex(full, fill_value=0).to_numpy().reshape(92, len(stations))
    reps = []
    for _ in range(NBOOT):
        start = rng.integers(0, 92, size=14)
        ix = ((start[:, None] + np.arange(7)[None, :]) % 92).ravel()[:92]
        mean = S[ix].sum(0) / C[ix].sum(0)[:, None]
        reps.append(site_stats(s=pd.DataFrame(mean, index=stations, columns=ANOM)))
    keys = [k for k in reps[0] if k != "n_sites"]
    return {k + "_ci95": np.quantile([r[k] for r in reps], [.025, .975]).tolist() for k in keys}


def main_sites() -> dict:
    res = {}
    for clock in ["as_local_CEST", "as_fixed_CET", "as_UTC"]:
        for window in ["Morning", "Afternoon"]:
            z = centred(pairs[(pairs.clock == clock) & (pairs.window == window)])
            rng = np.random.default_rng(SEED)
            res[f"{window}_{clock}"] = dict(n_pairs=int(len(z)), n_hours=int(z.timestamp.nunique()),
                                             decomposition=decomposition(z), site=site_stats(z),
                                             site_bootstrap=bootstrap(z, rng))
    return res


# ---------------- D: one-reference sufficiency ----------------
def top(scores: pd.Series, k: int) -> np.ndarray:
    order = sorted(zip(-scores.to_numpy(), scores.index), key=lambda t: (t[0], t[1]))
    return np.array([c for _, c in order[:k]])


def capture(u: pd.Series, sel: np.ndarray, k: int) -> float:
    best = np.sort(u.to_numpy())[::-1][:k].sum()
    return 100 * u.loc[sel].sum() / best


def main_sufficiency() -> dict:
    pol = pd.read_parquet(SM2 / "datos/policy_scores_two_cities.parquet")
    comp = pd.read_parquet(SM2 / "datos/score_components.parquet")
    keys = ["city", "mode", "window", "threshold", "phi"]
    comp["population"] = comp[["solar_failure", "shared_thermal_failure", "local_only_failure",
                               "regional_only_failure", "joint_pass"]].sum(axis=1)
    df = pol.merge(comp[keys + ["CUSEC", "population"]], on=keys + ["CUSEC"], validate="one_to_one")
    df = df[df.reachable]
    df["CUSEC"] = df.CUSEC.astype(str)
    rows = []
    for key, g in df.groupby(keys):
        g = g.set_index("CUSEC")
        k = int(g.quota.iloc[0])
        row = dict(zip(keys, key))
        for rule in ["population", "uniform"]:
            sel = top(g[rule], k)
            row[f"{rule}_L"] = capture(g.local, sel, k)
            row[f"{rule}_R"] = capture(g.regional, sel, k)
        rows.append(row)
    t = pd.DataFrame(rows)

    def classify(refs):
        pop = np.all([t[f"population_{r}"] >= 99 for r in refs], axis=0)
        uni = np.all([t[f"uniform_{r}"] >= 99 for r in refs], axis=0)
        return int(pop.sum()), int((~pop & uni).sum()), int((~pop & ~uni).sum()), (~pop & ~uni)

    out = {}
    for name, refs in [("both", ["L", "R"]), ("local_only", ["L"]), ("regional_only", ["R"])]:
        p, u, n, mask = classify(refs)
        out[name] = dict(population=p, uniform_additional=u, simple_sufficient=p + u, neither=n)
        if name == "local_only":
            nb = t[mask]
            out[name]["neither_by_city_window"] = nb.groupby(["city", "window"]).size().to_dict()
            out[name]["neither_by_city_window"] = {f"{a}_{b}": int(v) for (a, b), v in
                                                   out[name]["neither_by_city_window"].items()}
    t.to_csv(OUTPUT / "suficiencia_una_referencia.csv", index=False)
    return out


# ---------------- E: six-summer field gradients (added after C, to interpret it) ----------------
def field_gradients() -> dict:
    """West-east gradient of each six-summer Valencia field and threshold proximity by window."""
    import geopandas as gpd
    g = gpd.read_file(SM2 / "fixed/mapas/Valencia_a1.gpkg")[["CUSEC", "geometry"]].to_crs("EPSG:25830")
    x = g.set_index(g.CUSEC.astype(str)).geometry.representative_point().x / 1000
    out = {}
    for window in ["Morning", "Afternoon"]:
        f = np.load(VIT / f"city_fields_{window}.npz", allow_pickle=True)
        xx = x.reindex(pd.Index(f["CUSEC"].astype(str))).to_numpy()
        ok = ~np.isnan(xx)
        for ref in ["local", "regional"]:
            a = f[ref][ok]
            m = a.mean(1)
            out[f"{window}_{ref}"] = dict(
                n_sections=int(ok.sum()),
                slope_per10km=float(10 * np.polyfit(xx[ok], m, 1)[0]),
                rho_east=float(spearmanr(xx[ok], m).statistic),
                share_within_1C_of_30=float(((a >= 29) & (a < 31)).mean()))
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sm2", type=Path, default=UC, help="Extracted Supplementary Material 2 root")
    parser.add_argument("--vit", type=Path, help="Upstream validation folder (required for --only all)")
    parser.add_argument("--only", choices=["sufficiency", "all"], default="sufficiency")
    parser.add_argument("--out", type=Path, default=OUTPUT, help="Output directory; supplied results are not overwritten")
    args = parser.parse_args()
    SM2, VIT, OUTPUT = args.sm2.resolve(), args.vit, args.out.resolve()
    if args.only == "all" and VIT is None:
        parser.error("--only all requires --vit with provider-dependent inputs")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.only == "sufficiency":
        result = dict(sufficiency=main_sufficiency())
        (OUTPUT / "revision_observacional_2026-10-04.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
        print(json.dumps(result, indent=1))
        raise SystemExit(0)
    import geopandas as gpd
    VIT = VIT.resolve()
    pairs = pd.read_parquet(VIT / "matched_pairs.parquet")
    st = pd.read_parquet(VIT / "stations_selected.parquet")
    xy = gpd.GeoSeries(gpd.points_from_xy(st.longitude, st.latitude), crs=4326).to_crs("EPSG:25830")
    east_km = pd.Series(xy.x.to_numpy() / 1000, index=st.station_id.astype(int))
    result = dict(sufficiency=main_sufficiency(), sites=main_sites(), field_gradients=field_gradients())
    print(json.dumps(result["field_gradients"], indent=1))
    path = OUTPUT / "revision_observacional_2026-10-04.json"
    path.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result["sufficiency"], indent=1))
    for k, v in result["sites"].items():
        s, b = v["site"], v["site_bootstrap"]
        print(k, {m: round(d["spatial_mae"], 3) for m, d in v["decomposition"].items()},
              "| common IDW", round(v["decomposition"]["IDW"]["mean_abs_common"], 2),
              "| rho_east_obs", round(s["rho_east_obs"], 2), np.round(b["rho_east_obs_ci95"], 2),
              "| rho_obs_IDW", round(s["rho_obs_IDW"], 2), "ERA5", round(s["rho_obs_ERA5_corrected"], 2),
              "| sd obs/IDW/ERA5", round(s["sd_obs"], 2), round(s["sd_IDW"], 2), round(s["sd_ERA5_corrected"], 2))
