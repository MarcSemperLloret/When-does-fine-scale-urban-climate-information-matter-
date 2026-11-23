"""Quick checks closing remaining reviewer points.

1. Central-case table: capture and turnover side by side (R3 Results, R1 minor 2).
2. Exceedance skill at the 29 VITUclim sites (R5 #4).
3. Share of section-hours above 28/30/32 C (R2 minor 1).
4. Population-allocation noise (R6 2.1).
5. Temperature-only disagreement, without the shade gate (R1 #3): metrics per section.
"""
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
M3 = HERE.parents[1]
REL = M3 / 'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city'
V = M3 / 'validacion_vituclim_2025'
E = 1 + 1e-7
pol = pd.read_parquet(REL / 'datos/policy_scores_two_cities.parquet')


def top(x, k):
    return np.argsort(-x, kind='stable')[:k]


def cap(s, sel, k):
    return 100 * s[sel].sum() / np.sort(s)[-k:].sum()


# 1. Central table
st = pd.read_csv(HERE.parent / 'capacidad/capacidad_288x5_estados.csv')
st = st[(st.capacity == .15) & (st.threshold == 30) & (st.phi == .4)].set_index(['city', 'window', 'mode'])
rows = []
for (city, w, mode), g in pol[(pol.threshold == 30) & (pol.phi == .4)].groupby(['city', 'window', 'mode']):
    g = g[g.reachable].sort_values('CUSEC')
    sec = pd.read_csv(REL / f'datos/secciones_{city}.csv', dtype={'CUSEC': str}).set_index('CUSEC')
    p = sec.loc[g.CUSEC.astype(str), 'pob_65'].to_numpy()
    L, R, U = g.local.to_numpy(), g.regional.to_numpy(), g.uniform.to_numpy()
    k = int(g.quota.iloc[0])
    lL, lR, lU, lP = top(L, k), top(R, k), top(U, k), top(p, k)
    rows.append(dict(city=city, window=w, mode=mode, k=k, state=st.loc[(city, w, mode), 'state'],
                     pop_cap_L=cap(L, lP, k), pop_cap_R=cap(R, lP, k), uni_cap_L=cap(L, lU, k), uni_cap_R=cap(R, lU, k),
                     regional_list_cap_L=cap(L, lR, k), local_list_cap_R=cap(R, lL, k),
                     changed_L_R=k - len(np.intersect1d(lL, lR)), changed_L_U=k - len(np.intersect1d(lL, lU)),
                     changed_L_P=k - len(np.intersect1d(lL, lP)), min_common_loss=st.loc[(city, w, mode), 'minimum_common_loss']))
ct = pd.DataFrame(rows)
ct.to_csv(HERE / 'tabla_central.csv', index=False)
print(ct.round(2).to_string())

# 2. Exceedance skill at VITUclim sites
m = pd.read_parquet(V / 'matched_pairs.parquet').dropna(subset=['observed', 'IDW', 'Uniform', 'Nearest', 'ERA5_corrected'])
rows = []
for thr in [28, 30, 32]:
    for (clock, w), g in m.groupby(['clock', 'window']):
        o = g.observed >= thr
        for mdl in ['IDW', 'Uniform', 'Nearest', 'ERA5_corrected']:
            pr = g[mdl] >= thr
            a = (pr & o).sum(); b = (pr & ~o).sum(); c = (~pr & o).sum(); d = (~pr & ~o).sum(); n = a + b + c + d
            exp = ((a + b) * (a + c) + (c + d) * (b + d)) / n
            hss = ((a + d) - exp) / (n - exp) if n != exp else np.nan
            # spatial skill: which sites exceed in each hour, relative to the uniform comparator
            rows.append(dict(threshold=thr, clock=clock, window=w, model=mdl, n=int(n), obs_rate=float(o.mean()), pred_rate=float(pr.mean()),
                             hit_rate=a / (a + c) if a + c else np.nan, false_alarm_ratio=b / (a + b) if a + b else np.nan,
                             accuracy=(a + d) / n, HSS=hss))
sk = pd.DataFrame(rows)
sk.to_csv(HERE / 'excedencia_vituclim.csv', index=False)
print(sk[sk.threshold == 30].pivot_table(index=['clock', 'window'], columns='model', values='HSS').round(3).to_string())
print(sk[sk.threshold == 30].pivot_table(index=['clock', 'window'], columns='model', values='accuracy').round(3).to_string())
# Within-hour discrimination: among hours where observations disagree between sites, does IDW place exceedances at the right sites?
rows = []
for (clock, w), g in m.groupby(['clock', 'window']):
    g = g.assign(o=g.observed >= 30)
    mixed = g.groupby('timestamp').o.transform(lambda x: 0 < x.mean() < 1)
    h = g[mixed]
    for mdl in ['IDW', 'Nearest', 'ERA5_corrected']:
        # rank correlation within hour between predicted and observed temperatures, at mixed hours only
        r = h.groupby('timestamp').apply(lambda x: spearmanr(x[mdl], x.observed)[0] if x[mdl].nunique() > 1 else np.nan)
        rows.append(dict(clock=clock, window=w, model=mdl, mixed_hours=int(h.timestamp.nunique()), median_within_hour_rho=float(r.median())))
pd.DataFrame(rows).to_csv(HERE / 'excedencia_mixtas.csv', index=False)
print(pd.DataFrame(rows).pivot_table(index=['clock', 'window'], columns='model', values='median_within_hour_rho').round(3).to_string())

# 3. Share of section-hours above thresholds (station field)
rows = []
for city in ['Valencia', 'Madrid']:
    for w in ['Morning', 'Afternoon']:
        f = M3 / (f'Madrid_2026-09-07/datos/campos_central_{w}.npz' if city == 'Madrid' else f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz')
        L = np.load(f)['local'].astype(float)
        rows.append(dict(city=city, window=w, **{f'ge{t}': float((L >= t).mean()) for t in [28, 30, 32]}))
th = pd.DataFrame(rows); th.to_csv(HERE / 'umbrales_frecuencia.csv', index=False); print(th.round(3).to_string())

# 4. Population allocation noise
rng = np.random.default_rng(20261124)
rows = []
groups = [(key, g[g.reachable].sort_values('CUSEC')) for key, g in pol.groupby(['city', 'mode', 'window', 'threshold', 'phi'])]
secs = {c: pd.read_csv(REL / f'datos/secciones_{c}.csv', dtype={'CUSEC': str}).set_index('CUSEC') for c in ['Valencia', 'Madrid']}
for cv in [0.1, 0.25]:
    s2 = np.log(1 + cv ** 2)
    for r in range(100):
        eps = {c: pd.Series(np.exp(rng.normal(-s2 / 2, np.sqrt(s2), len(secs[c]))), index=secs[c].index) for c in secs}
        for key, g in groups:
            city = key[0]; e = eps[city].loc[g.CUSEC.astype(str)].to_numpy()
            p = secs[city].loc[g.CUSEC.astype(str), 'pob_65'].to_numpy() * e
            L = g.local.to_numpy() * e; U = g.uniform.to_numpy() * e; k = int(g.quota.iloc[0])
            simple = (100 - cap(L, top(p, k), k) <= E) or (100 - cap(L, top(U, k), k) <= E)
            rows.append(dict(cv=cv, real=r, city=city, window=key[2], simple=simple,
                             changed_vs_original=k - len(np.intersect1d(top(L, k), top(g.local.to_numpy(), k))), k=k))
pn = pd.DataFrame(rows)
pn.to_parquet(HERE / 'poblacion_ruido.parquet', index=False)
t = pn.groupby(['cv', 'real']).simple.sum().groupby('cv').agg(['mean', lambda x: x.quantile(.05), lambda x: x.quantile(.95)])
print(t.round(1).to_string())
print(pn.groupby(['cv', 'city', 'window', 'real']).simple.sum().groupby(['cv', 'city', 'window']).mean().unstack(['city', 'window']).round(1).to_string())
print((pn.changed_vs_original / pn.k).groupby(pn.cv).median().round(3).to_string())
