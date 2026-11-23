"""Unequal assessment or intervention costs (R6 3.2).

No section-level cost data exist, so two proxies are used: cost proportional to section area (for
interventions that scale with territory, such as street shading) and cost proportional to estimated older
population (for per-resident programmes). The budget is 15% of the total cost of the reachable universe.
Each reference optimum is a 0-1 knapsack solved exactly with HiGHS; the simple rules fill the budget greedily
in order of score per unit cost (population per unit cost is constant under the per-resident proxy, so that
rule is undefined there). A simple rule is sufficient when it captures at least 99% of the local knapsack
optimum, as in the main analysis.
"""
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
from scipy.optimize import milp, Bounds, LinearConstraint
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
M3 = HERE.parents[1]
REL = M3 / 'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city'
E = 1 + 1e-7


def knap(u, c, B):
    n = len(u)
    r = milp(-u, integrality=np.ones(n), bounds=Bounds(0, 1), constraints=LinearConstraint(c[None, :], 0, B),
             options={'time_limit': 30, 'mip_rel_gap': 1e-6})
    assert r.x is not None
    return float(u @ (r.x > .5)), bool(r.status == 0), float(r.mip_gap)


def greedy(rank, c, B):
    order = np.argsort(-rank, kind='stable'); take = np.zeros(len(c), bool); used = 0.
    for i in order:
        if used + c[i] <= B + 1e-9:
            take[i] = True; used += c[i]
    return take


def work(task):
    meta, L, R, U, p, area = task; out = []
    for proxy, c in [('area', area / area.mean()), ('older_population', p / p.mean())]:
        B = .15 * c.sum()
        optL, okL, gL = knap(L, c, B); optR, okR, gR = knap(R, c, B)
        uni = greedy(U / c, c, B)
        row = dict(**meta, proxy=proxy, optimal=okL and okR, max_gap=max(gL, gR), uni_loss=100 * (1 - L[uni].sum() / optL),
                   uni_loss_regional=100 * (1 - R[uni].sum() / optR))
        if proxy == 'area':
            pop = greedy(p / c, c, B); row['pop_loss'] = 100 * (1 - L[pop].sum() / optL)
        else:
            row['pop_loss'] = np.nan
        out.append(row)
    return out


def main():
    pol = pd.read_parquet(REL / 'datos/policy_scores_two_cities.parquet')
    areas = {}
    for city in ['Valencia', 'Madrid']:
        g = gpd.read_file(REL / f'fixed/mapas/{city}_a1.gpkg').to_crs(25830); g['CUSEC'] = g.CUSEC.astype(str)
        areas[city] = g.drop_duplicates('CUSEC').set_index('CUSEC').geometry.area
    secs = {c: pd.read_csv(REL / f'datos/secciones_{c}.csv', dtype={'CUSEC': str}).set_index('CUSEC') for c in areas}
    tasks = []
    for key, g in pol.groupby(['city', 'mode', 'window', 'threshold', 'phi']):
        g = g[g.reachable].sort_values('CUSEC'); ids = g.CUSEC.astype(str)
        tasks.append((dict(zip(['city', 'mode', 'window', 'threshold', 'phi'], key)), g.local.to_numpy(), g.regional.to_numpy(),
                      g.uniform.to_numpy(), secs[key[0]].loc[ids, 'pob_65'].to_numpy(), areas[key[0]].loc[ids].to_numpy()))
    rows = []
    with ProcessPoolExecutor(6) as ex:
        for r in ex.map(work, tasks):
            rows += r
    d = pd.DataFrame(rows); d.to_csv(HERE / 'costes_desiguales.csv', index=False)
    print('all optimal', bool(d.optimal.all()))
    d['simple'] = (d.pop_loss <= E) | (d.uni_loss <= E)
    print(d.groupby('proxy').simple.sum().to_string())
    print(d.groupby(['proxy', 'city', 'window']).simple.sum().unstack(['city', 'window']).to_string())
    print(d.groupby(['proxy']).uni_loss.median().round(3).to_string())


if __name__ == '__main__':
    main()
