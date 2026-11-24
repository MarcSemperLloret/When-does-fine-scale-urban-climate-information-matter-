"""Station configuration, canopy transmittance and temperature-only disagreement (R6 2.2, R2 #5, R5 #9, R1 #3).

A. Valencia: IDW field rebuilt leaving out each of the six AVAMET stations (original pipeline code).
   Madrid: stored alternative networks (all 25 stations, AQ13 plus two, two six-station panels).
   The 144 cases of each city are reclassified with the alternative field as local reference and its
   own hourly mean as the uniform rule, over the hours common to both fields.
B. Canopy transmittance tau: q_tau = q_full + tau (q_buildings - q_full) for network-only routes.
   Interpolating between the two optimal routes bounds the exposure from below (the optimum over
   routes is concave in tau), so the test is optimistic about shade.
C. Net disagreement with and without the route-shade gate (central settings, network-only).
"""
from pathlib import Path
import sys, numpy as np, pandas as pd, geopandas as gpd
from scipy.stats import spearmanr
import matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
M3 = HERE.parents[1]
REL = M3 / 'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city'
E = 1 + 1e-7
TH = [28, 30, 32]; PHI = [.1, .2, .3, .4, .5, .6, .7, 1.]
pol = pd.read_parquet(REL / 'datos/policy_scores_two_cities.parquet')


def top(x, k):
    return np.argsort(-x, kind='stable')[:k]


def loss(s, sel, k):
    return 100 * (1 - s[sel].sum() / np.sort(s)[-k:].sum())


def sec_of(city):
    return pd.read_csv(REL / f'datos/secciones_{city}.csv', dtype={'CUSEC': str}).sort_values('CUSEC').reset_index(drop=True)


def route_matrix(rr, sec, ix, months, hours, col='fraction'):
    keys = [f'{m:02}-15' for m in months]
    lk = {(d, h): rr[rr.date.eq(d) & rr.hour.eq(h)].set_index('CUSEC').loc[sec.CUSEC][col].to_numpy()[ix] for d, h in sorted(set(zip(keys, hours)))}
    return np.stack([lk[d, h] for d, h in zip(keys, hours)], axis=1).astype(float)


def classify(city, w, mode, L, U, R, P, frac, ixk, label, base_lists=None):
    """Simple-rule sufficiency over thresholds and phi for one setting; L, U, R already restricted to reachable rows."""
    ix, k = ixk; p = P[ix]; out = []; lists = {}
    for thr in TH:
        bl, bu = L < thr, U < thr
        for phi in PHI:
            sh = frac <= phi + 1e-12
            sl = p * (1 - (bl & sh).mean(1)); su = p * (1 - (bu & sh).mean(1)); sr = p * (1 - ((R < thr) & sh).mean(1))
            lL = top(sl, k); lists[(thr, phi)] = lL
            row = dict(city=city, window=w, mode=mode, threshold=thr, phi=phi, variant=label, k=k,
                       pop_loss=loss(sl, top(p, k), k), uni_loss=loss(sl, top(su, k), k),
                       pop_loss_R=loss(sr, top(p, k), k), uni_loss_R=loss(sr, top(su, k), k))
            if base_lists is not None:
                row['changed_vs_base'] = k - len(np.intersect1d(lL, base_lists[(thr, phi)]))
            out.append(row)
    return out, lists


rowsA = []
# ---------- A. Valencia leave-one-station-out
sys.path.insert(0, str(M3 / 'analisis'))
import p2_comparar_era5land as P2
secV = sec_of('Valencia'); PV = secV.pob_65.to_numpy()
shp = gpd.read_file(f"zip://{M3 / 'datos/seccionado_2024.zip'}!SECC_CE_20240101.shp")
gV = shp[shp.CUSEC.isin(secV.CUSEC)].to_crs(P2.UTM).sort_values('CUSEC').reset_index(drop=True)
assert np.array_equal(gV.CUSEC.to_numpy(), secV.CUSEC.to_numpy())
cent = gV.geometry.centroid
STATIONS = list(P2.BARRIOS)
routesV = pd.read_parquet(M3 / 'Madrid_2026-09-07/datos/rutas_central_Valencia_working_Full.parquet').query('weights==21')
for w, hrs in [('Morning', [10, 11, 12]), ('Afternoon', [16, 17, 18])]:
    z = np.load(M3 / f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz')
    L0, R0, months, hours = z['local'].astype(float), z['regional'].astype(float), z['months'], z['hours']
    P2.BARRIOS = STATIONS
    ta, ia = P2.campo_avamet(cent, hrs)
    te, ie, _ = P2.campo_era5(gpd.GeoSeries(cent, crs=P2.UTM), hrs)
    index = ia.intersection(ie)
    full = ta[:, ia.get_indexer(index)]
    assert np.allclose(full, L0, atol=1e-6), 'original Valencia field not reproduced'
    print('Valencia', w, 'field reproduced', flush=True)
    for s in STATIONS:
        P2.BARRIOS = [x for x in STATIONS if x != s]
        tl, il = P2.campo_avamet(cent, hrs)
        pos = index.get_indexer(il.intersection(index)); pos.sort()
        sub = index[pos]; Ls = tl[:, il.get_indexer(sub)]
        for mode, rr in routesV.groupby('mode'):
            reach = rr[rr.date.eq('06-15') & rr.hour.eq(10)].set_index('CUSEC').loc[secV.CUSEC].reachable.to_numpy()
            ix = np.flatnonzero(reach); k = int(.15 * len(ix))
            frac = route_matrix(rr, secV, ix, months[pos], hours[pos])
            Lb, Rb = L0[ix][:, pos], R0[ix][:, pos]
            base, bl = classify('Valencia', w, mode, Lb, np.broadcast_to(L0[:, pos].mean(0), Lb.shape), Rb, PV, frac, (ix, k), 'baseline_same_hours')
            alt, _ = classify('Valencia', w, mode, Ls[ix], np.broadcast_to(Ls.mean(0), Lb.shape), Rb, PV, frac, (ix, k), f'without_{s}', bl)
            for r in base + alt:
                r.update(hours_kept=len(pos), hours_total=len(index), excluded=s)
            rowsA += base + alt
        P2.BARRIOS = STATIONS
        print('  without', s, len(pos), 'of', len(index), 'hours', flush=True)

# ---------- A. Madrid alternative networks
secM = sec_of('Madrid'); PM = secM.pob_65.to_numpy()
routesM = pd.read_parquet(M3 / 'Madrid_2026-09-07/datos/rutas_central_Madrid_working_Full.parquet').query('weights==21')
for w in ['Morning', 'Afternoon']:
    z = np.load(M3 / f'Madrid_2026-09-07/datos/campos_central_{w}.npz')
    L0, R0, months, hours = z['local'].astype(float), z['regional'].astype(float), z['months'], z['hours']
    for net in ['All_25', 'AQ_plus_two_3m', 'AQ6_1', 'AQ6_2']:
        A = z[net].astype(float); pos = np.flatnonzero(np.isfinite(A).all(0) & np.isfinite(L0).all(0))
        for mode, rr in routesM.groupby('mode'):
            reach = rr[rr.date.eq('06-15') & rr.hour.eq(10)].set_index('CUSEC').loc[secM.CUSEC].reachable.to_numpy()
            ix = np.flatnonzero(reach); k = int(.15 * len(ix))
            frac = route_matrix(rr, secM, ix, months[pos], hours[pos])
            Lb, Rb = L0[ix][:, pos], R0[ix][:, pos]
            base, bl = classify('Madrid', w, mode, Lb, np.broadcast_to(L0[:, pos].mean(0), Lb.shape), Rb, PM, frac, (ix, k), 'baseline_same_hours')
            alt, _ = classify('Madrid', w, mode, A[ix][:, pos], np.broadcast_to(A[:, pos].mean(0), Lb.shape), Rb, PM, frac, (ix, k), net, bl)
            for r in base + alt:
                r.update(hours_kept=len(pos), hours_total=L0.shape[1], excluded=net)
            rowsA += base + alt
        print('Madrid', w, net, len(pos), 'of', L0.shape[1], flush=True)
dA = pd.DataFrame(rowsA); dA.to_csv(HERE / 'red_estaciones.csv', index=False)

# ---------- B. Canopy transmittance (network-only)
rowsB = []
cfg = {'Valencia': (secV, PV, M3 / 'SCS_ampliado_2026-09-07/datos_ampliacion/routes.parquet', 'fields_{w}.npz'),
       'Madrid': (secM, PM, None, None)}
for city in ['Valencia', 'Madrid']:
    sec, P = cfg[city][0], cfg[city][1]
    if city == 'Valencia':
        rt = pd.read_parquet(cfg['Valencia'][2])
        if 'route_policy' in rt: rt = rt[rt.route_policy == rt.route_policy.mode().iloc[0]]
        rf, rb = rt[rt.layer == 'Full'], rt[rt.layer == 'Buildings']
    else:
        rf = routesM[routesM['mode'] == 'network']
        rb = pd.read_parquet(M3 / 'Madrid_2026-09-07/datos/rutas_central_Madrid_working_Buildings.parquet').query("weights==21 and mode=='network'")
    reach = rf[rf.date.eq('06-15') & rf.hour.eq(10)].set_index('CUSEC').loc[sec.CUSEC].reachable.to_numpy()
    ix = np.flatnonzero(reach); k = int(.15 * len(ix))
    for w in ['Morning', 'Afternoon']:
        f = M3 / (f'Madrid_2026-09-07/datos/campos_central_{w}.npz' if city == 'Madrid' else f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz')
        z = np.load(f); L0, R0t, months, hours = z['local'].astype(float), z['regional'].astype(float), z['months'], z['hours']
        qf = route_matrix(rf, sec, ix, months, hours); qb = route_matrix(rb, sec, ix, months, hours)
        qb = np.where(np.isfinite(qb), qb, qf)
        Lr = L0[ix]; Ur = np.broadcast_to(L0.mean(0), Lr.shape)
        base = None
        for tau in [0, .1, .25, .5, 1]:
            q = qf + tau * (qb - qf)
            out, lists = classify(city, w, 'network', Lr, Ur, R0t[ix], P, q, (ix, k), f'tau={tau}', base)
            if tau == 0: base = lists
            for r in out: r['tau'] = tau
            sh = q <= .4 + 1e-12; s30 = P[ix] * (1 - ((Lr < 30) & sh).mean(1))
            for r in out:
                if r['threshold'] == 30 and r['phi'] == .4:
                    r['rho_shade_only'] = spearmanr(s30, P[ix] * (1 - sh.mean(1)))[0]
                    r['rho_population'] = spearmanr(s30, P[ix])[0]
            rowsB += out
        print('transmittance', city, w, flush=True)
dB = pd.DataFrame(rowsB); dB.to_csv(HERE / 'transmitancia.csv', index=False)

# ---------- C. Disagreement with and without the shade gate
rowsC = []; maps = {}
for city, sec, routes in [('Valencia', secV, routesV), ('Madrid', secM, routesM)]:
    g = gpd.read_file(REL / f'fixed/mapas/{city}_a1.gpkg').to_crs(25830); g['CUSEC'] = g.CUSEC.astype(str)
    g = g.drop_duplicates('CUSEC').set_index('CUSEC').loc[sec.CUSEC].reset_index()
    rr = routes[routes['mode'] == 'network']
    reach = rr[rr.date.eq('06-15') & rr.hour.eq(10)].set_index('CUSEC').loc[sec.CUSEC].reachable.to_numpy(); ix = np.flatnonzero(reach)
    for w in ['Morning', 'Afternoon']:
        f = M3 / (f'Madrid_2026-09-07/datos/campos_central_{w}.npz' if city == 'Madrid' else f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz')
        z = np.load(f); L0, R0 = z['local'].astype(float)[ix], z['regional'].astype(float)[ix]
        s = route_matrix(rr, sec, ix, z['months'], z['hours']) <= .4 + 1e-12
        bL, bR = L0 >= 30, R0 >= 30
        gated = 100 * ((s & bL & ~bR).mean(1) - (s & ~bL & bR).mean(1))
        ungated = 100 * ((bL & ~bR).mean(1) - (~bL & bR).mean(1))
        x = g.geometry.centroid.x.to_numpy()[ix]
        rowsC.append(dict(city=city, window=w, rho_gated_ungated=spearmanr(gated, ungated)[0], rho_east_gated=spearmanr(gated, x)[0],
                          rho_east_ungated=spearmanr(ungated, x)[0], p05_ungated=float(np.percentile(ungated, 5)), p95_ungated=float(np.percentile(ungated, 95)),
                          mean_shade_pass=float(s.mean())))
        maps[(city, w)] = (g.iloc[ix].assign(v=ungated))
dC = pd.DataFrame(rowsC); dC.to_csv(HERE / 'mapa_sin_sombra.csv', index=False); print(dC.round(3).to_string())

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'pdf.fonttype': 42})
fig, axs = plt.subplots(2, 2, figsize=(7.4, 7.0))
vmax = 30
for ax, (key, gg) in zip(axs.flat, maps.items()):
    gg.plot(column='v', cmap='RdBu_r', vmin=-vmax, vmax=vmax, ax=ax, linewidth=0)
    ax.set_title(f'{key[0]}, {key[1].lower()}', fontsize=10); ax.set_axis_off()
sm = plt.cm.ScalarMappable(cmap='RdBu_r', norm=plt.Normalize(-vmax, vmax))
cb = fig.colorbar(sm, ax=axs, orientation='horizontal', fraction=.04, pad=.03)
cb.set_label('Local minus regional exceedance of 30 °C, all hours (percentage points)')
fig.savefig(HERE / 'Figure_S_temperature_only.pdf', bbox_inches='tight'); fig.savefig(HERE / 'Figure_S_temperature_only.png', dpi=160, bbox_inches='tight')
