"""Afternoon-minus-morning difference of the observed west-east gradient at the 29 VITUclim sites,
with a paired seven-day circular block bootstrap (the same day blocks for both windows), per clock convention."""
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd

HERE = Path(__file__).resolve().parent
V = HERE.parents[1] / 'validacion_vituclim_2025'
m = pd.read_parquet(V / 'matched_pairs.parquet').dropna(subset=['observed'])
st = pd.read_parquet(V / 'stations_selected.parquet').set_index('station_id')
x = gpd.GeoSeries(gpd.points_from_xy(st.longitude, st.latitude), crs=4326).to_crs(25830).x
x.index = st.index
rng = np.random.default_rng(20261124); NB = 2000; BL = 7
rows = []
for clock, g in m.groupby('clock'):
    g = g.copy(); g['day'] = pd.to_datetime(g.timestamp).dt.normalize()
    g['anom'] = g.observed - g.groupby('timestamp')['observed'].transform('mean')
    days = np.sort(g.day.unique()); nd = len(days)
    # site x day mean anomaly per window
    A = {w: g[g.window == w].pivot_table(index='day', columns='station_id', values='anom', aggfunc='mean').reindex(days) for w in ['Morning', 'Afternoon']}
    sites = sorted(set(A['Morning'].columns) & set(A['Afternoon'].columns)); xs = x.loc[sites].to_numpy() / 1e4

    def grad(sel):
        out = {}
        for w in A:
            s = np.nanmean(A[w][sites].to_numpy()[sel], axis=0)
            out[w] = np.polyfit(xs, s, 1)[0]
        return out
    full = grad(np.arange(nd))
    diffs = []
    for _ in range(NB):
        starts = rng.integers(0, nd, int(np.ceil(nd / BL)))
        sel = np.concatenate([(s + np.arange(BL)) % nd for s in starts])[:nd]
        r = grad(sel); diffs.append(r['Afternoon'] - r['Morning'])
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    rows.append(dict(clock=clock, grad_morning=full['Morning'], grad_afternoon=full['Afternoon'], diff_pm_minus_am=full['Afternoon'] - full['Morning'], ci_low=lo, ci_high=hi))
d = pd.DataFrame(rows); d.to_csv(HERE / 'gradiente_pareado.csv', index=False); print(d.round(3).to_string())
