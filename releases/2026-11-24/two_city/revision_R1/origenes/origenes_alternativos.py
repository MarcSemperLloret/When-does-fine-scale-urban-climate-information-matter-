"""Sensitivity to the pedestrian origin within each census section (R6 2.1).

Routes are recomputed for network-only connections from three random interior points per section (snapped to
the nearest walking-graph node) in addition to the original centroid node, with the original route family
(21 weights of time and sun time, minimum exposed fraction among routes within 15 minutes, duration
tie-break), graph, shade layers and destination nodes. The centroid run must reproduce the published scores.
Each origin draw is then classified over the 48 network-only cases per city (2 windows x 3 thresholds x 8 phi)
with the two-reference sufficiency criterion.
"""
from pathlib import Path
import sys, numpy as np, pandas as pd, geopandas as gpd, networkx as nx
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from numba import njit

HERE = Path(__file__).resolve().parent
M3 = HERE.parents[1]
MAD = M3 / 'Madrid_2026-09-07'
REL=(lambda r:r if (r/'datos/policy_scores_two_cities.parquet').exists() else Path(__file__).resolve().parents[2]/'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city')(Path(__file__).resolve().parents[2])
E = 1 + 1e-7
NDRAW = 3
WEIGHTS = np.linspace(0, 1, 21)


@njit(cache=True)
def trace(pred, dist, dst, unique, chosen, et, es, n, root):
    T = np.full(len(dst), np.inf); S = T.copy()
    for j in range(len(dst)):
        cur = dst[j]
        if not np.isfinite(dist[cur]):
            continue
        tt = ss = 0.; steps = 0
        while cur != root:
            prev = pred[cur]
            key = min(cur, prev) * n + max(cur, prev)
            ix = np.searchsorted(unique, key)
            edge = chosen[ix]; tt += et[edge]; ss += es[edge]; cur = prev; steps += 1
        T[j] = tt; S[j] = ss
    return T, S


def top(x, k): return np.argsort(-x, kind='stable')[:k]
def loss(s, sel, k): return 100 * (1 - s[sel].sum() / np.sort(s)[-k:].sum())


def main(city):
    if city == 'Madrid':
        G = nx.read_graphml(MAD / 'datos/red_peatonal_madrid.graphml')
        e = pd.read_parquet(MAD / 'datos/aristas_central.parquet')
        shade = pd.read_parquet(MAD / 'datos/sombra_central_Full.parquet').reindex(e.arista)
    else:
        G = nx.read_graphml(M3 / 'datos/red_peatonal_valencia.graphml')
        e = pd.read_parquet(M3 / 'datos/aristas_con_sombra.parquet')[['arista', 'u', 'v', 'length']].sort_values('arista').reset_index(drop=True)
        shade = pd.read_parquet(M3 / 'datos/sombra_aristas_veg.parquet').reindex(e.arista)
    nodes = [int(x) for x in G.nodes]; idx = {u: i for i, u in enumerate(nodes)}; root = len(nodes); n = root + 1
    xy = gpd.GeoSeries(gpd.points_from_xy([float(G.nodes[str(u)]['x']) for u in nodes], [float(G.nodes[str(u)]['y']) for u in nodes]), crs=4326).to_crs(25830)
    tree = cKDTree(np.c_[xy.x, xy.y])
    sec = pd.read_csv(REL / f'datos/secciones_{city}.csv', dtype={'CUSEC': str}).sort_values('CUSEC').reset_index(drop=True)
    stab = pd.read_csv(MAD / f'tablas/secciones_central_{city}.csv', dtype={'CUSEC': str}).set_index('CUSEC').loc[sec.CUSEC]
    geo = gpd.read_file(REL / f'fixed/mapas/{city}_a1.gpkg').to_crs(25830); geo['CUSEC'] = geo.CUSEC.astype(str)
    geo = geo.drop_duplicates('CUSEC').set_index('CUSEC').loc[sec.CUSEC]
    cs = pd.read_csv(MAD / f'tablas/centros_central_{city}_working.csv')
    src = np.array([idx[int(x)] for x in cs.destination_node])
    rng = np.random.default_rng(20261124)
    draws = [np.array([idx[int(x)] for x in stab.origin_node])]
    snaps = [np.zeros(len(sec))]
    for _ in range(NDRAW):
        pts = np.array([[p.x, p.y] for p in geo.geometry.sample_points(1, rng=rng)])
        dd, ii = tree.query(pts); draws.append(ii.astype(np.int64)); snaps.append(dd)
    u = np.r_[e.u.map(idx).to_numpy(), np.full(len(src), root)].astype(int)
    v = np.r_[e.v.map(idx).to_numpy(), src].astype(int)
    key = np.minimum(u, v) * n + np.maximum(u, v); unique, group = np.unique(key, return_inverse=True); ul, uh = unique // n, unique % n
    edgeids = np.arange(len(u)); road_time = e.length.to_numpy() / .9 / 60
    et = np.r_[road_time, np.zeros(len(src))]
    res = {}
    for date in ['06-15', '07-15', '08-15']:
        for hour in [10, 11, 12, 16, 17, 18]:
            es = np.r_[road_time * (1 - shade[f'{date}_{hour:02d}'].to_numpy()), np.zeros(len(src))]
            TT = [[] for _ in draws]; SS = [[] for _ in draws]
            for lam in WEIGHTS:
                w = (1 - lam) * et + lam * es + 1e-10 * et + 1e-12
                order = np.lexsort((edgeids, w, group)); first = np.r_[True, group[order][1:] != group[order][:-1]]; chosen = order[first]
                mat = coo_matrix((np.r_[w[chosen], w[chosen]], (np.r_[ul, uh], np.r_[uh, ul])), shape=(n, n)).tocsr()
                dist, pred = dijkstra(mat, directed=True, indices=root, return_predecessors=True)
                for j, dst in enumerate(draws):
                    t, s_ = trace(pred, dist, dst, unique, chosen, et, es, n, root); TT[j].append(t); SS[j].append(s_)
            for j in range(len(draws)):
                T = np.stack(TT[j], 1); S = np.stack(SS[j], 1); valid = T <= 15 + 1e-9
                frac = np.divide(S, T, out=np.zeros_like(S), where=(T > 0) & np.isfinite(T))
                best = np.lexsort((T, np.where(valid, frac, np.inf)), axis=1)[:, 0]
                res[j, date, hour] = (T[:, 0] <= 15 + 1e-9, frac[np.arange(len(sec)), best])
            print(city, date, hour, flush=True)
    pol = pd.read_parquet(REL / 'datos/policy_scores_two_cities.parquet')
    P = sec.pob_65.to_numpy(); rows = []
    for w in ['Morning', 'Afternoon']:
        f = MAD / f'datos/campos_central_{w}.npz' if city == 'Madrid' else M3 / f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz'
        z = np.load(f); L, R = z['local'].astype(float), z['regional'].astype(float); keys = [(f'{m:02}-15', int(h)) for m, h in zip(z['months'], z['hours'])]
        base = {}
        for j in range(len(draws)):
            reach = res[j, '06-15', 10][0]; ix = np.flatnonzero(reach); k = int(.15 * len(ix)); p = P[ix]
            q = np.stack([res[j, d, h][1][ix] for d, h in keys], 1)
            Li, Ri = L[ix], R[ix]; Ui = np.broadcast_to(L.mean(0), Li.shape)
            for thr in [28, 30, 32]:
                for phi in [.1, .2, .3, .4, .5, .6, .7, 1.]:
                    sh = q <= phi + 1e-12
                    sl = p * (1 - ((Li < thr) & sh).mean(1)); sr = p * (1 - ((Ri < thr) & sh).mean(1)); su = p * (1 - ((Ui < thr) & sh).mean(1))
                    if j == 0:
                        o = pol.query("city==@city and window==@w and mode=='network' and threshold==@thr and phi==@phi").sort_values('CUSEC')
                        assert np.array_equal(o.reachable.to_numpy(), reach), 'reachability not reproduced'
                        assert np.allclose(sl, o.local.to_numpy()[ix], atol=1e-9), 'scores not reproduced'
                        base[thr, phi] = set(sec.CUSEC.to_numpy()[ix][top(sl, k)])
                    lL = set(sec.CUSEC.to_numpy()[ix][top(sl, k)])
                    rows.append(dict(city=city, window=w, draw=j, threshold=thr, phi=phi, N=len(ix), k=k,
                                     pop_loss=loss(sl, top(p, k), k), uni_loss=loss(sl, top(su, k), k), pop_loss_R=loss(sr, top(p, k), k), uni_loss_R=loss(sr, top(su, k), k),
                                     jaccard_vs_centroid=len(lL & base[thr, phi]) / len(lL | base[thr, phi]),
                                     median_snap_m=float(np.median(snaps[j])), shortlist=';'.join(sorted(lL))))
    d = pd.DataFrame(rows); d.to_csv(HERE / f'origenes_{city}.csv', index=False)
    d['simple'] = ((d.pop_loss <= E) & (d.pop_loss_R <= E)) | ((d.uni_loss <= E) & (d.uni_loss_R <= E))
    print(d.groupby(['draw', 'window']).simple.sum().unstack().to_string())
    print(d.groupby('draw')[['N', 'median_snap_m']].first().to_string()); print(d.groupby('draw').jaccard_vs_centroid.median().round(3).to_string())


if __name__ == '__main__':
    main(sys.argv[1])
