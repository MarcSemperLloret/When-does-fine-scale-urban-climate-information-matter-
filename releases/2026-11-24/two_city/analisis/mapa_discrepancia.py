"""Where do the local and regional temperature references disagree, and which
sections switch shortlist depending on the reference?

Central case: network-only routes, theta = 30 C, phi = 0.40, 15% capacity.
Inputs are the frozen decision-level files of Supplementary Material 2; no
score is recomputed. Writes figure Fig_discrepancy and a JSON of descriptives.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

HERE = Path(__file__).resolve().parent
UC = HERE.parent
SM2 = Path(sys.argv[1])  # extracted Supplementary_Material_2
sys.path.insert(0, str(Path.home() / ".claude/skills/scientific-figures/scripts"))
import figstyle as fs  # noqa: E402

UTM = "EPSG:25830"
STATIONS = {
    "Valencia": [(39.475, -0.376), (39.483, -0.385), (39.477, -0.390),
                 (39.471, -0.401), (39.467, -0.346), (39.458, -0.350)],
    "Madrid": [(40.4238823, -3.7122567), (40.4215533, -3.6823158), (40.4400457, -3.6392422),
               (40.3947825, -3.7318356), (40.4193577, -3.7473445), (40.4192091, -3.7031662),
               (40.4079517, -3.6453104), (40.4455439, -3.7071303), (40.4782322, -3.7115364),
               (40.3730118, -3.6121394), (40.3850336, -3.7187679), (40.5180701, -3.7746101),
               (40.465144, -3.609031)],
}
CASE = dict(mode="network", threshold=30, phi=0.4)

comp = pd.read_parquet(SM2 / "datos/score_components.parquet")
pol = pd.read_parquet(SM2 / "datos/policy_scores_two_cities.parquet")


def central(df, city, window):
    m = ((df.city == city) & (df.window == window) & (df["mode"] == CASE["mode"])
         & (df.threshold == CASE["threshold"]) & np.isclose(df.phi, CASE["phi"]))
    return df[m].set_index("CUSEC")


def top_k(s: pd.Series, k: int) -> set:
    # descending score, ascending identifier on ties (as in the manuscript)
    order = sorted(s.items(), key=lambda kv: (-kv[1], kv[0]))
    return {c for c, _ in order[:k]}


results, layers = {}, {}
for city in ("Valencia", "Madrid"):
    geo = gpd.read_file(SM2 / f"fixed/mapas/{city}_a1.gpkg")[["CUSEC", "geometry"]].to_crs(UTM)
    geo["CUSEC"] = geo["CUSEC"].astype(str)
    st = gpd.GeoSeries(gpd.points_from_xy([p[1] for p in STATIONS[city]],
                                          [p[0] for p in STATIONS[city]]), crs=4326).to_crs(UTM)
    cent = geo.set_index("CUSEC").geometry.representative_point()
    dist = pd.Series(np.min(np.stack([cent.distance(s) for s in st]), axis=0), index=cent.index)
    for window in ("Morning", "Afternoon"):
        c = central(comp, city, window)
        c = c[c.reachable]
        pop = c[["solar_failure", "shared_thermal_failure", "local_only_failure",
                 "regional_only_failure", "joint_pass"]].sum(axis=1)
        # percentage points of matched hours: local exceeds 30 C where regional does not, minus the reverse
        net = 100 * (c.local_only_failure - c.regional_only_failure) / pop
        p = central(pol, city, window)
        p = p[p.reachable]
        k = int(p.quota.iloc[0])
        L, R = top_k(p.local, k), top_k(p.regional, k)
        swing = (L ^ R)
        d = dist.reindex(net.index) / 1000
        is_swing = net.index.isin(list(swing))
        key = f"{city}_{window}"
        # west-east position; in Valencia the coast runs roughly north-south east of the city,
        # so easting is a proxy for proximity to the sea
        east = cent.reindex(net.index).x / 1000
        east = east - east.max()
        rho_e = spearmanr(east, net)
        lo = net.index.isin(list(L - R))
        ro = net.index.isin(list(R - L))
        rho = spearmanr(d, net.abs())
        mw = mannwhitneyu(d[is_swing], d[~is_swing]) if is_swing.any() else None
        results[key] = dict(
            reachable=int(len(net)), K=k, swing_sections=int(len(swing)),
            changed_slots=int(len(L - R)),
            net_pp_median=float(net.median()), net_pp_p05=float(net.quantile(.05)),
            net_pp_p95=float(net.quantile(.95)),
            abs_net_pp_median=float(net.abs().median()),
            spearman_abs_net_vs_station_km=float(rho.statistic), spearman_p=float(rho.pvalue),
            station_km_median_swing=float(d[is_swing].median()) if is_swing.any() else None,
            station_km_median_other=float(d[~is_swing].median()),
            mannwhitney_p=float(mw.pvalue) if mw else None,
            spearman_net_vs_easting=float(rho_e.statistic), spearman_easting_p=float(rho_e.pvalue),
            km_west_of_east_edge_median_local_only=float(-east[lo].median()) if lo.any() else None,
            km_west_of_east_edge_median_regional_only=float(-east[ro].median()) if ro.any() else None,
            km_west_of_east_edge_median_all=float(-east.median()),
        )
        g = geo.merge(net.rename("net").reset_index(), on="CUSEC", how="left")
        g["swing"] = g.CUSEC.map(lambda x: "L" if x in L - R else ("R" if x in R - L else ""))
        layers[key] = (g, st)

(UC / "control_interno").mkdir(exist_ok=True)
json.dump(results, open(UC / "control_interno/mapa_discrepancia_descriptivos.json", "w"), indent=1)
print(json.dumps(results, indent=1))

# ---------------- figure ----------------
from matplotlib.colors import TwoSlopeNorm  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

lim = max(abs(results[k][q]) for k in results for q in ("net_pp_p05", "net_pp_p95"))
lim = float(np.ceil(lim))
norm = TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim)
cmap = "RdBu_r"
fig, axes = fs.figure(6.69, 6.3, nrows=2, ncols=2)
axes = np.asarray(axes).ravel()
order = ["Valencia_Morning", "Valencia_Afternoon", "Madrid_Morning", "Madrid_Afternoon"]
for ax, key in zip(axes, order):
    g, st = layers[key]
    city, window = key.split("_")
    g[g.net.isna()].plot(ax=ax, color="#ececec", linewidth=0)
    g[g.net.notna()].plot(ax=ax, column="net", cmap=cmap, norm=norm, linewidth=0.1, edgecolor="white")
    for code, col in (("L", "black"), ("R", fs.C.green if hasattr(fs.C, "green") else "#009E73")):
        sel = g[g.swing == code]
        if len(sel):
            sel.boundary.plot(ax=ax, color=col, linewidth=1.1)
    st.plot(ax=ax, marker="^", color="black", markersize=22, zorder=5)
    r = g[g.net.notna()].total_bounds
    pad = 600
    ax.set_xlim(r[0] - pad, r[2] + pad)
    ax.set_ylim(r[1] - pad, r[3] + pad)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(f"{city}, {window.lower()}", loc="center")
    # scale bar
    L = 2000 if city == "Valencia" else 5000
    x0, y0 = r[0], r[1] - pad * 0.4
    ax.plot([x0, x0 + L], [y0, y0], color="black", lw=1.5, solid_capstyle="butt")
    ax.text(x0 + L / 2, y0 + pad * 0.35, f"{L // 1000} km", ha="center", va="bottom")
fs.label_panels(axes)
sm = __import__("matplotlib").cm.ScalarMappable(norm=norm, cmap=cmap)
cb = fig.colorbar(sm, ax=axes.tolist(), orientation="horizontal", fraction=0.035, pad=0.02, aspect=40)
cb.set_label("Local minus regional exceedance of 30 °C (percentage points of hours)")
handles = [Line2D([], [], marker="^", color="black", linestyle="none", markersize=5, label="Input station"),
           Patch(facecolor="none", edgecolor="black", linewidth=1.1, label="Shortlisted with local field only"),
           Patch(facecolor="none", edgecolor="#009E73", linewidth=1.1, label="Shortlisted with regional field only"),
           Patch(facecolor="#ececec", label="Outside 15 min reach")]
fig.legend(handles=handles, loc="outside upper center", ncols=4, frameon=False)
fs.save(fig, str(UC / "source/figuras/Fig_discrepancy"))
