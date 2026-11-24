"""(a) Quantify the three conditions under which temperature information changed selections (R2 #6, #7):
local-exclusive score share, share of section-hours within 1 C of the threshold, and spatial coherence of the
net disagreement (share of its variance explained by a planar city-scale trend; Moran's I with 8 nearest neighbours is also reported), next to the decision outcomes, for each city and window.
(b) Profile of the sections excluded by the 15-minute network-only budget (R5 #8, R4 #7)."""
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
M3 = HERE.parents[1]; MAD = M3 / 'Madrid_2026-09-07'
REL = M3 / 'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city'
E = 1 + 1e-7
mech = pd.read_csv(REL / 'tablas/mechanism_summary.csv')
cap = pd.read_csv(HERE.parent / 'capacidad/capacidad_288x5_estados.csv'); cap = cap[cap.capacity == .15]
cap['simple'] = (cap.pop_loss_both <= E) | (cap.uni_loss_both <= E)


def moran(v, xy, k=8):
    _, nb = cKDTree(xy).query(xy, k + 1); nb = nb[:, 1:]
    z = v - v.mean(); num = (z[:, None] * z[nb]).sum(); return float(len(v) / (len(v) * k) * num / (z ** 2).sum())


rows = []; excl = []
for city in ['Valencia', 'Madrid']:
    sec = pd.read_csv(REL / f'datos/secciones_{city}.csv', dtype={'CUSEC': str}).sort_values('CUSEC').reset_index(drop=True)
    g = gpd.read_file(REL / f'fixed/mapas/{city}_a1.gpkg').to_crs(25830); g['CUSEC'] = g.CUSEC.astype(str)
    g = g.drop_duplicates('CUSEC').set_index('CUSEC').loc[sec.CUSEC]; XY = np.c_[g.geometry.centroid.x, g.geometry.centroid.y]
    rr = pd.read_parquet(MAD / f'datos/rutas_central_{city}_working_Full.parquet').query("weights==21 and mode=='network'")
    r0 = rr[rr.date.eq('06-15') & rr.hour.eq(10)].set_index('CUSEC').loc[sec.CUSEC]
    reach = r0.reachable.to_numpy(); ix = np.flatnonzero(reach)
    P = sec.pob_65.to_numpy()
    excl.append(dict(city=city, sections=len(sec), excluded=int((~reach).sum()), excluded_older=float(P[~reach].sum()),
                     excluded_older_share=float(P[~reach].sum() / P.sum()), median_shortest_min_excluded=float(np.median(r0.shortest_time_min.to_numpy()[~reach])),
                     pct65_excluded=float(np.median(sec.pct_65.to_numpy()[~reach])) if 'pct_65' in sec else np.nan,
                     pct65_included=float(np.median(sec.pct_65.to_numpy()[reach])) if 'pct_65' in sec else np.nan))
    for w in ['Morning', 'Afternoon']:
        f = MAD / f'datos/campos_central_{w}.npz' if city == 'Madrid' else M3 / f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz'
        z = np.load(f); L, R = z['local'].astype(float)[ix], z['regional'].astype(float)[ix]
        keys = [f'{m:02}-15' for m in z['months']]
        lk = {(d, h): rr[rr.date.eq(d) & rr.hour.eq(h)].set_index('CUSEC').loc[sec.CUSEC].fraction.to_numpy()[ix] for d, h in sorted(set(zip(keys, z['hours'])))}
        s = np.stack([lk[d, h] for d, h in zip(keys, z['hours'])], 1) <= .4 + 1e-12
        bL, bR = L >= 30, R >= 30
        net = 100 * ((s & bL & ~bR).mean(1) - (s & ~bL & bR).mean(1))
        m = mech[(mech.city == city) & (mech.window == w) & (mech['mode'] == 'network') & (mech.threshold == 30) & (mech.phi == .4)].iloc[0]
        c = cap[(cap.city == city) & (cap.window == w)]
        cc = c[(c['mode'] == 'network') & (c.threshold == 30) & (c.phi == .4)].iloc[0]
        rows.append(dict(city=city, window=w, local_exclusive_share=100 * float(m.local_only_failure_local_top_score_share),
                         near_threshold_share=100 * float((np.abs(L - 30) <= 1).mean()), moran_I_disagreement=moran(net, XY[ix]), planar_trend_R2=float(1 - np.var(net - np.c_[np.ones(len(ix)), XY[ix]] @ np.linalg.lstsq(np.c_[np.ones(len(ix)), XY[ix]], net, rcond=None)[0]) / np.var(net)),
                         simple_cases=int(c.simple.sum()), incompatible_cases=int((c.minimum_common_loss > E).sum()), central_slots_changed=int(cc.changed_local_regional), k=int(cc.k)))
d = pd.DataFrame(rows); d.to_csv(HERE / 'tres_condiciones.csv', index=False); print(d.round(3).to_string())
x = pd.DataFrame(excl); x.to_csv(HERE / 'secciones_excluidas.csv', index=False); print(x.round(2).to_string())
