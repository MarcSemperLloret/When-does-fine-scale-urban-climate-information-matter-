"""Section-level versus district-level agreement of shortlists under input changes (simulated reviewer 3, point 1).

District agreement between two shortlists of size K is sum_d min(n_d, n'_d) / K, the share of slots that
stay in the same district (1 = same number of slots in every district). Section agreement is the share of
sections in common. A random baseline draws K reachable sections at random (200 draws per case).
Inputs compared with the published local shortlist: population errors (CV 10% and 25%), canopy transmittance
(0.1, 0.25 and building-only shade) and, when their saved lists exist, alternative pedestrian origins and the
UTCI-based score.
"""
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
REV = HERE.parent; M3 = REV.parent
REL=(lambda r:r if (r/'datos/policy_scores_two_cities.parquet').exists() else Path(__file__).resolve().parents[2]/'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city')(Path(__file__).resolve().parents[2])
MAD = M3 / 'Madrid_2026-09-07'
pol = pd.read_parquet(REL / 'datos/policy_scores_two_cities.parquet')
sec = {c: pd.read_csv(REL / f'datos/secciones_{c}.csv', dtype={'CUSEC': str}).set_index('CUSEC') for c in ['Valencia', 'Madrid']}
DCOL = {'Valencia': 'distrito', 'Madrid': 'CDIS'}
rng = np.random.default_rng(20261124)


def top(x, k): return np.argsort(-x, kind='stable')[:k]


def agree(a, b, dist):
    a, b = list(a), list(b); k = len(a)
    da = pd.Series([dist[x] for x in a]).value_counts(); db = pd.Series([dist[x] for x in b]).value_counts()
    return len(set(a) & set(b)) / k, float(np.minimum(da, db.reindex(da.index).fillna(0)).sum() / k)


rows = []
cases = pol[(pol['mode'] == 'network')].groupby(['city', 'window', 'threshold', 'phi'])
base = {}
for (city, w, thr, phi), g in cases:
    g = g[g.reachable].sort_values('CUSEC'); ids = g.CUSEC.astype(str).to_numpy(); k = int(g.quota.iloc[0])
    dist = sec[city][DCOL[city]].astype(str).to_dict()
    L = g.local.to_numpy(); bl = ids[top(L, k)]; base[city, w, thr, phi] = (bl, dist, ids)
    for r in range(200):
        s, d_ = agree(bl, rng.choice(ids, k, replace=False), dist)
        rows.append(dict(check='random list', city=city, window=w, threshold=thr, phi=phi, section=s, district=d_))
    p = sec[city].loc[ids, 'pob_65'].to_numpy()
    for cv in [0.1, 0.25]:
        s2 = np.log(1 + cv ** 2)
        for r in range(50):
            e = np.exp(rng.normal(-s2 / 2, np.sqrt(s2), len(ids)))
            s, d_ = agree(bl, ids[top(L * e, k)], dist)
            rows.append(dict(check=f'population error {int(cv * 100)}%', city=city, window=w, threshold=thr, phi=phi, section=s, district=d_))

# canopy transmittance from the stored network-only routes (same construction as huecos/estaciones_sombra_mapa.py)
def route_matrix(rr, secidx, ix, months, hours):
    keys = [f'{m:02}-15' for m in months]
    lk = {(d, h): rr[rr.date.eq(d) & rr.hour.eq(h)].set_index('CUSEC').loc[secidx].fraction.to_numpy()[ix] for d, h in sorted(set(zip(keys, hours)))}
    return np.stack([lk[d, h] for d, h in zip(keys, hours)], axis=1).astype(float)


for city in ['Valencia', 'Madrid']:
    S = pd.read_csv(REL / f'datos/secciones_{city}.csv', dtype={'CUSEC': str}).sort_values('CUSEC').reset_index(drop=True)
    if city == 'Valencia':
        rt = pd.read_parquet(M3 / 'SCS_ampliado_2026-09-07/datos_ampliacion/routes.parquet')
        if 'route_policy' in rt: rt = rt[rt.route_policy == rt.route_policy.mode().iloc[0]]
        rf, rb = rt[rt.layer == 'Full'], rt[rt.layer == 'Buildings']
    else:
        rf = pd.read_parquet(MAD / 'datos/rutas_central_Madrid_working_Full.parquet').query("weights==21 and mode=='network'")
        rb = pd.read_parquet(MAD / 'datos/rutas_central_Madrid_working_Buildings.parquet').query("weights==21 and mode=='network'")
    reach = rf[rf.date.eq('06-15') & rf.hour.eq(10)].set_index('CUSEC').loc[S.CUSEC].reachable.to_numpy(); ix = np.flatnonzero(reach); k = int(.15 * len(ix))
    P = S.pob_65.to_numpy()[ix]; ids = S.CUSEC.to_numpy()[ix]
    for w in ['Morning', 'Afternoon']:
        f = MAD / f'datos/campos_central_{w}.npz' if city == 'Madrid' else M3 / f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz'
        z = np.load(f); Li = z['local'].astype(float)[ix]
        qf = route_matrix(rf, S.CUSEC, ix, z['months'], z['hours']); qb = route_matrix(rb, S.CUSEC, ix, z['months'], z['hours']); qb = np.where(np.isfinite(qb), qb, qf)
        for tau in [0.1, 0.25, 1.0]:
            q = qf + tau * (qb - qf)
            for thr in [28, 30, 32]:
                for phi in [.1, .2, .3, .4, .5, .6, .7, 1.]:
                    bl, dist, _ = base[city, w, thr, phi]
                    sl = P * (1 - ((Li < thr) & (q <= phi + 1e-12)).mean(1))
                    s, d_ = agree(bl, ids[top(sl, k)], dist)
                    rows.append(dict(check='building-only shade' if tau == 1 else f'canopy transmittance {tau}', city=city, window=w, threshold=thr, phi=phi, section=s, district=d_))

# alternative origins and UTCI, if their saved shortlists exist
for city in ['Valencia', 'Madrid']:
    f = REV / f'origenes/origenes_{city}.csv'
    if f.exists():
        o = pd.read_csv(f)
        if 'shortlist' in o:
            for r in o[o.draw > 0].itertuples():
                bl, dist, _ = base[city, r.window, r.threshold, r.phi]
                s, d_ = agree(bl, r.shortlist.split(';'), dist)
                rows.append(dict(check='alternative origin', city=city, window=r.window, threshold=r.threshold, phi=r.phi, section=s, district=d_))
u = REV / 'utci/utci_estados.csv'
if u.exists():
    ud = pd.read_csv(u, dtype={'shortlist': str, 'binary_shortlist': str})
    if 'shortlist' in ud:
        for r in ud[(ud.wind_factor == 1.0) & (ud['mode'] == 'network')].itertuples():
            dist = sec[r.city][DCOL[r.city]].astype(str).to_dict()
            s, d_ = agree(r.binary_shortlist.split(';'), r.shortlist.split(';'), dist)
            rows.append(dict(check=f'UTCI {r.utci_threshold} C', city=r.city, window=r.window, threshold=30, phi=.4, section=s, district=d_))

d = pd.DataFrame(rows)
rnd = d[d.check == 'random list'].groupby(['city', 'window', 'threshold', 'phi'])[['section', 'district']].mean().rename(columns={'section': 'sec_rand', 'district': 'dis_rand'})
d = d.merge(rnd, left_on=['city', 'window', 'threshold', 'phi'], right_index=True, how='left')
d['section_beyond_chance'] = (d.section - d.sec_rand) / (1 - d.sec_rand)
d['district_beyond_chance'] = (d.district - d.dis_rand) / (1 - d.dis_rand)
d.to_csv(HERE / 'distritos.csv', index=False)
t = d.groupby('check')[['section', 'district', 'section_beyond_chance', 'district_beyond_chance']].median().round(3)
t['n'] = d.groupby('check').size()
print(t.sort_values('district').to_string())
print(d.groupby(['check', 'city'])[['section', 'district']].median().round(2).unstack('city').to_string())
