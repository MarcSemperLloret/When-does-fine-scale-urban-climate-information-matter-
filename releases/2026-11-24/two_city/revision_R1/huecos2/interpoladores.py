"""Alternative interpolators for the Valencia station field (R6 2.2, R2 #1, R5 #3).

From the same hourly AVAMET station values (at least three stations per hour, as in the original field):
  IDW      : inverse squared distance, 50 m floor (the published field; reproduced as a check)
  GP_r     : simple kriging of hourly anomalies about the station mean, exponential covariance with
             range r (1, 3, 8 km) and a 10% nugget (Gaussian-process interpolation)
  Drift    : hourly least-squares west-east linear trend through the stations plus IDW of the residuals
  Nearest  : nearest available station (Thiessen polygons)
Each field is (a) validated at the 29 VITUclim sites in summer 2025 (UTC timestamps) by the spatial MAE
after removing each hour's common error, and (b) used as the local reference, with its own hourly mean as
the uniform rule, to reclassify the 144 Valencia cases.
"""
from pathlib import Path
import sys, numpy as np, pandas as pd, geopandas as gpd

HERE = Path(__file__).resolve().parent
M3 = HERE.parents[1]
REL=(lambda r:r if (r/'datos/policy_scores_two_cities.parquet').exists() else Path(__file__).resolve().parents[2]/'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city')(Path(__file__).resolve().parents[2])
V = M3 / 'validacion_vituclim_2025'
E = 1 + 1e-7
sys.path.insert(0, str(M3 / 'analisis'))
import p2_comparar_era5land as P2

STATIONS = list(P2.BARRIOS)
df = pd.read_parquet(M3 / 'datos/valencia_verano_qc.parquet')
df = df[df.station_id.isin(STATIONS)].copy(); df['hora'] = df.observed_local.dt.hour
hor = df.groupby(['station_id', 'date', 'hora'], observed=True).t_qc.mean().reset_index()
piv = hor.pivot_table(index=['date', 'hora'], columns='station_id', values='t_qc').reindex(columns=STATIONS)
meta = df.groupby('station_id')[['latitude', 'longitude']].first().reindex(STATIONS)
sxy = gpd.GeoSeries(gpd.points_from_xy(meta.longitude, meta.latitude), crs=4326).to_crs(P2.UTM)
SXY = np.c_[sxy.x, sxy.y]


def field(name, TXY, Y):
    """Y: hours x stations (NaN = missing). Returns targets x hours."""
    out = np.full((len(TXY), len(Y)), np.nan)
    D = np.hypot(*(TXY[:, None, :] - SXY[None, :, :]).transpose(2, 0, 1))
    avail = np.isfinite(Y)
    for pat in np.unique(avail, axis=0):
        rows = np.flatnonzero((avail == pat).all(1)); s = np.flatnonzero(pat)
        if len(s) < 3:
            continue
        y = Y[np.ix_(rows, s)]
        if name == 'IDW':
            W = 1 / np.maximum(D[:, s], 50) ** 2; W /= W.sum(1, keepdims=True); out[:, rows] = W @ y.T
        elif name == 'Nearest':
            out[:, rows] = y[:, D[:, s].argmin(1)].T
        elif name.startswith('GP'):
            r = float(name.split('_')[1]) * 1000
            Ds = np.hypot(*(SXY[s][:, None, :] - SXY[s][None, :, :]).transpose(2, 0, 1))
            K = 0.9 * np.exp(-Ds / r) + 0.1 * np.eye(len(s)); k = 0.9 * np.exp(-D[:, s] / r)
            m = y.mean(1, keepdims=True); out[:, rows] = (k @ np.linalg.solve(K, (y - m).T)) + m.T
        elif name == 'Drift':
            X = np.c_[np.ones(len(s)), (SXY[s, 0] - SXY[:, 0].mean()) / 1000]
            beta = np.linalg.lstsq(X, y.T, rcond=None)[0]
            res = y - (X @ beta).T
            W = 1 / np.maximum(D[:, s], 50) ** 2; W /= W.sum(1, keepdims=True)
            out[:, rows] = np.c_[np.ones(len(TXY)), (TXY[:, 0] - SXY[:, 0].mean()) / 1000] @ beta + W @ res.T
    return out


NAMES = ['IDW', 'GP_1', 'GP_3', 'GP_8', 'Drift', 'Nearest']
# (a) validation at VITUclim sites, UTC convention
mp = pd.read_parquet(V / 'matched_pairs.parquet'); mp = mp[mp.clock == 'as_UTC'].dropna(subset=['observed'])
st = pd.read_parquet(V / 'stations_selected.parquet').set_index('station_id')
sites = sorted(mp.station_id.unique())
gx = gpd.GeoSeries(gpd.points_from_xy(st.loc[sites, 'longitude'], st.loc[sites, 'latitude']), crs=4326).to_crs(P2.UTM)
TXYs = np.c_[gx.x, gx.y]
mp['local'] = pd.DatetimeIndex(mp.clock_hour).tz_localize('UTC').tz_convert('Europe/Madrid').tz_localize(None)
keys = pd.MultiIndex.from_arrays([mp.local.dt.normalize().dt.date.astype(str), mp.local.dt.hour])
pidx = pd.MultiIndex.from_arrays([pd.to_datetime(piv.index.get_level_values(0)).date.astype(str), piv.index.get_level_values(1)])
pos = pidx.get_indexer(keys)
rows = []
for nm in NAMES:
    F = field(nm, TXYs, piv.to_numpy())
    si = {s: i for i, s in enumerate(sites)}
    pred = np.array([F[si[s], p] if p >= 0 else np.nan for s, p in zip(mp.station_id, pos)])
    m = mp.assign(pred=pred).dropna(subset=['pred'])
    if nm == 'IDW':
        print('IDW reproduction at sites, max |diff|:', float((m.pred - m.IDW).abs().max()))
    for w, g in m.groupby('window'):
        e = g.pred - g.observed; r = e - e.groupby(g.timestamp).transform('mean')
        an_o = g.observed - g.observed.groupby(g.timestamp).transform('mean'); an_p = g.pred - g.pred.groupby(g.timestamp).transform('mean')
        sm = pd.DataFrame({'o': an_o, 'p': an_p, 's': g.station_id}).groupby('s').mean()
        rows.append(dict(field=nm, window=w, spatial_MAE=float(r.abs().mean()), total_MAE=float(e.abs().mean()),
                         site_rho=float(sm.corr(method='spearman').iloc[0, 1]), obs_on_pred_slope=float(np.polyfit(sm.p, sm.o, 1)[0])))
val = pd.DataFrame(rows); val.to_csv(HERE / 'interpoladores_validacion.csv', index=False); print(val.round(3).to_string())

# (b) decisions over six summers
secV = pd.read_csv(REL / 'datos/secciones_Valencia.csv', dtype={'CUSEC': str}).sort_values('CUSEC').reset_index(drop=True)
shp = gpd.read_file(f"zip://{M3 / 'datos/seccionado_2024.zip'}!SECC_CE_20240101.shp")
gV = shp[shp.CUSEC.isin(secV.CUSEC)].to_crs(P2.UTM).sort_values('CUSEC').reset_index(drop=True)
cent = gV.geometry.centroid; TXYc = np.c_[cent.x, cent.y]; PV = secV.pob_65.to_numpy()
routes = pd.read_parquet(M3 / 'Madrid_2026-09-07/datos/rutas_central_Valencia_working_Full.parquet').query('weights==21')


def top(x, k): return np.argsort(-x, kind='stable')[:k]
def loss(s, sel, k): return 100 * (1 - s[sel].sum() / np.sort(s)[-k:].sum())


out = []
for w, hrs in [('Morning', [10, 11, 12]), ('Afternoon', [16, 17, 18])]:
    z = np.load(M3 / f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz')
    L0, R0, months, hours = z['local'].astype(float), z['regional'].astype(float), z['months'], z['hours']
    P2.BARRIOS = STATIONS
    ta, ia = P2.campo_avamet(cent, hrs); te, ie, _ = P2.campo_era5(gpd.GeoSeries(cent, crs=P2.UTM), hrs)
    index = ia.intersection(ie)
    ip = pd.MultiIndex.from_arrays([pd.to_datetime(piv.index.get_level_values(0)), piv.index.get_level_values(1)]).get_indexer(
        pd.MultiIndex.from_arrays([pd.to_datetime(index.get_level_values(0)), index.get_level_values(1)]))
    assert (ip >= 0).all()
    Y = piv.to_numpy()[ip]
    fields = {nm: field(nm, TXYc, Y) for nm in NAMES}
    print(w, 'IDW reproduction, max |diff|:', float(np.nanmax(np.abs(fields['IDW'] - L0))), flush=True)
    for mode, rr in routes.groupby('mode'):
        reach = rr[rr.date.eq('06-15') & rr.hour.eq(10)].set_index('CUSEC').loc[secV.CUSEC].reachable.to_numpy()
        ix = np.flatnonzero(reach); k = int(.15 * len(ix)); p = PV[ix]
        keysm = [f'{m:02}-15' for m in months]
        lk = {(d, h): rr[rr.date.eq(d) & rr.hour.eq(h)].set_index('CUSEC').loc[secV.CUSEC].fraction.to_numpy()[ix] for d, h in sorted(set(zip(keysm, hours)))}
        q = np.stack([lk[d, h] for d, h in zip(keysm, hours)], axis=1)
        base = {}
        for nm in NAMES:
            F = fields[nm]; Fi = F[ix]; Ui = np.broadcast_to(F.mean(0), Fi.shape)
            for thr in [28, 30, 32]:
                for phi in [.1, .2, .3, .4, .5, .6, .7, 1.]:
                    sh = q <= phi + 1e-12
                    sl = p * (1 - ((Fi < thr) & sh).mean(1)); su = p * (1 - ((Ui < thr) & sh).mean(1)); sr = p * (1 - ((R0[ix] < thr) & sh).mean(1))
                    lL = top(sl, k)
                    if nm == 'IDW': base[thr, phi] = lL
                    out.append(dict(field=nm, window=w, mode=mode, threshold=thr, phi=phi, k=k, pop_loss=loss(sl, top(p, k), k), uni_loss=loss(sl, top(su, k), k), pop_loss_R=loss(sr, top(p, k), k), uni_loss_R=loss(sr, top(su, k), k),
                                    changed_vs_IDW=k - len(np.intersect1d(lL, base[thr, phi])), changed_local_regional=k - len(np.intersect1d(lL, top(sr, k)))))
d = pd.DataFrame(out); d.to_csv(HERE / 'interpoladores_decision.csv', index=False)
d['simple'] = (d.pop_loss <= E) | (d.uni_loss <= E)
print(d.groupby(['field', 'window']).simple.sum().unstack().assign(total=lambda x: x.sum(1)).to_string())
print(d.assign(f=d.changed_vs_IDW / d.k).groupby(['field', 'window']).f.median().unstack().round(3).to_string())
c = d[(d.threshold == 30) & (d.phi == .4) & (d['mode'] == 'network')]
print(c.pivot_table(index='field', columns='window', values='changed_local_regional').to_string())
