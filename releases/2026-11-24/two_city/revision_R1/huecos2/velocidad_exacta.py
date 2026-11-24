"""Exact walking-speed and time-budget sensitivity from the cached route candidates (R2 #5, R6 2.1).

The cache stores, for every section and each of 41 route weights, the candidate's duration and sun
minutes at 0.9 m/s. Both scale by 0.9/v at speed v, so the candidate set and exposed fractions are
unchanged and only feasibility moves; the 21-weight subgrid and the published selection rule
(minimum exposed fraction among feasible candidates, duration tie-break) are applied unchanged.
The 0.9 m/s, 15-minute setting must reproduce the published scores exactly.
"""
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
M3 = HERE.parents[1]
REL = M3 / 'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city'
CACHE = M3 / 'Madrid_2026-09-07/datos/rutas_cache'
E = 1 + 1e-7
SETTINGS = [(0.9, 15), (1.1, 15), (1.25, 15), (0.75, 15), (0.6, 15), (0.9, 10), (0.9, 20)]
TH = [28, 30, 32]; PHI = [.1, .2, .3, .4, .5, .6, .7, 1.]
pol = pd.read_parquet(REL / 'datos/policy_scores_two_cities.parquet')


def top(x, k):
    return np.argsort(-x, kind='stable')[:k]


def loss(s, sel, k):
    return 100 * (1 - s[sel].sum() / np.sort(s)[-k:].sum())


rows = []
for city in ['Valencia', 'Madrid']:
    sec = pd.read_csv(REL / f'datos/secciones_{city}.csv', dtype={'CUSEC': str}).sort_values('CUSEC').reset_index(drop=True)
    P = sec.pob_65.to_numpy()
    for w in ['Morning', 'Afternoon']:
        f = M3 / (f'Madrid_2026-09-07/datos/campos_central_{w}.npz' if city == 'Madrid' else f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz')
        z = np.load(f); L = z['local'].astype(float); R = z['regional'].astype(float); months, hours = z['months'], z['hours']
        keys = [(f'{m:02}-15', int(h)) for m, h in zip(months, hours)]
        for mode in ['network', 'connectors_sun', 'connectors_shade']:
            cand = {}
            for d, h in sorted(set(keys)):
                c = np.load(CACHE / f'{city}_working_Full_{mode}_{d}_{h}_41.npz')
                assert np.array_equal(c['CUSEC'].astype(str), sec.CUSEC.to_numpy())
                cand[d, h] = (c['time'][:, ::2], c['sun'][:, ::2])
            base_lists = {}
            for v, B in SETTINGS:
                fac = 0.9 / v
                sel = {}
                for (d, h), (T, S) in cand.items():
                    tt = T * fac; valid = tt <= B + 1e-9
                    frac = np.divide(S, T, out=np.zeros_like(S), where=(T > 0) & np.isfinite(T))
                    best = np.lexsort((tt, np.where(valid, frac, np.inf)), axis=1)[:, 0]
                    sel[d, h] = (valid.any(1), frac[np.arange(len(sec)), best])
                T0 = np.load(CACHE / f'{city}_working_Full_{mode}_06-15_10_41.npz')['time'][:, 0] * fac  # time-only candidate: hour-independent
                reach = T0 <= B + 1e-9; ix = np.flatnonzero(reach); k = int(.15 * len(ix))
                q = np.stack([sel[key][1][ix] for key in keys], axis=1)
                Li, Ri = L[ix], R[ix]; Ui = np.broadcast_to(L.mean(0), Li.shape); p = P[ix]
                for thr in TH:
                    bl, bu, br = Li < thr, Ui < thr, Ri < thr
                    for phi in PHI:
                        sh = q <= phi + 1e-12
                        sl = p * (1 - (bl & sh).mean(1)); su = p * (1 - (bu & sh).mean(1)); sr = p * (1 - (br & sh).mean(1))
                        if (v, B) == (0.9, 15):
                            o = pol.query('city==@city and window==@w and mode==@mode and threshold==@thr and phi==@phi').sort_values('CUSEC')
                            assert np.array_equal(o.reachable.to_numpy(), reach)
                            assert np.allclose(sl, o.local.to_numpy()[ix], atol=1e-9) and np.allclose(sr, o.regional.to_numpy()[ix], atol=1e-9)
                        lL = top(sl, k)
                        row = dict(city=city, window=w, mode=mode, speed=v, budget=B, threshold=thr, phi=phi, N=len(ix), k=k,
                                   pop_loss=loss(sl, top(p, k), k), uni_loss=loss(sl, top(su, k), k), pop_loss_R=loss(sr, top(p, k), k), uni_loss_R=loss(sr, top(su, k), k),
                                   changed_local_regional=k - len(np.intersect1d(lL, top(sr, k))))
                        if (v, B) == (0.9, 15):
                            base_lists[thr, phi] = set(sec.CUSEC.to_numpy()[ix][lL])
                        else:
                            now = set(sec.CUSEC.to_numpy()[ix][lL]); row['jaccard_vs_base'] = len(now & base_lists[thr, phi]) / len(now | base_lists[thr, phi])
                        rows.append(row)
            print(city, w, mode, flush=True)
d = pd.DataFrame(rows); d.to_csv(HERE / 'velocidad_exacta.csv', index=False)
d['simple'] = (d.pop_loss <= E) | (d.uni_loss <= E)
print(d.groupby(['speed', 'budget']).simple.sum().to_string())
print(d.groupby(['speed', 'budget', 'city', 'window']).simple.sum().unstack(['city', 'window']).to_string())
print(d.groupby(['speed', 'budget', 'city', 'mode']).N.first().unstack(['city', 'mode']).to_string())
print(d.groupby(['speed', 'budget']).jaccard_vs_base.median().round(3).to_string())
