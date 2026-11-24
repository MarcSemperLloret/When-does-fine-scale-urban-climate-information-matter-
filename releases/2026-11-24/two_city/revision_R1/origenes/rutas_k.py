"""Targeted route check for origins near the shade threshold (R1 #1).

For a sample of reachable origins whose chosen network-only route has an exposed fraction within 0.05 of 0.40,
simple paths to any destination are enumerated in order of duration (Yen's k-shortest paths on the walking
graph restricted to a 15-minute radius) until they exceed the 15-minute budget or 500 paths are reached. These
paths are not restricted to the weighted-sum family used by the main analysis. The check reports whether any
enumerated path has a lower exposed fraction than the chosen route and whether it would change the shade
classification at 0.40.
"""
from pathlib import Path
import sys, itertools, numpy as np, pandas as pd, networkx as nx

HERE = Path(__file__).resolve().parent
M3 = HERE.parents[1]; MAD = M3 / 'Madrid_2026-09-07'
NSAMPLE = 25; KMAX = 500; SLOTS = [('07-15', 11), ('07-15', 17)]


def run(city):
    if city == 'Madrid':
        e = pd.read_parquet(MAD / 'datos/aristas_central.parquet'); shade = pd.read_parquet(MAD / 'datos/sombra_central_Full.parquet').reindex(e.arista)
    else:
        e = pd.read_parquet(M3 / 'datos/aristas_con_sombra.parquet')[['arista', 'u', 'v', 'length']].sort_values('arista').reset_index(drop=True)
        shade = pd.read_parquet(M3 / 'datos/sombra_aristas_veg.parquet').reindex(e.arista)
    sec = pd.read_csv(MAD / f'tablas/secciones_central_{city}.csv', dtype={'CUSEC': str})
    dest = set(pd.read_csv(MAD / f'tablas/centros_central_{city}_working.csv').destination_node.astype(int))
    rt = pd.read_parquet(MAD / f'datos/rutas_central_{city}_working_Full.parquet').query("weights==21 and mode=='network'")
    rng = np.random.default_rng(20261124); rows = []
    for date, hour in SLOTS:
        col = f'{date}_{hour:02d}'
        tmin = e.length.to_numpy() / .9 / 60; smin = tmin * (1 - shade[col].to_numpy())
        G = nx.Graph()
        for a, b, t, s in zip(e.u.to_numpy(), e.v.to_numpy(), tmin, smin):
            if not G.has_edge(a, b) or G[a][b]['t'] > t:
                G.add_edge(int(a), int(b), t=float(t), s=float(s))
        for d in dest:
            G.add_edge(int(d), -1, t=0.0, s=0.0)
        r = rt[rt.date.eq(date) & rt.hour.eq(hour) & rt.reachable].merge(sec[['CUSEC', 'origin_node']], on='CUSEC')
        near = r[(r.fraction - .4).abs() <= .05]
        sample = near.sample(min(NSAMPLE, len(near)), random_state=int(rng.integers(1e9)))
        for _, o in sample.iterrows():
            src = int(o.origin_node)
            dist = nx.single_source_dijkstra_path_length(G, src, cutoff=15 + 1e-9, weight='t')
            H = G.subgraph(list(dist) + [-1]).copy()
            best = np.inf; n = 0; first_t = None
            for path in itertools.islice(nx.shortest_simple_paths(H, src, -1, weight='t'), KMAX):
                t = sum(H[a][b]['t'] for a, b in zip(path, path[1:])); s = sum(H[a][b]['s'] for a, b in zip(path, path[1:]))
                if first_t is None: first_t = t
                if t > 15 + 1e-9: break
                n += 1; best = min(best, s / t if t > 0 else 0)
            rows.append(dict(city=city, slot=col, CUSEC=o.CUSEC, chosen_fraction=o.fraction, paths_within_budget=n, best_enumerated_fraction=best,
                             lower_found=bool(best < o.fraction - 1e-9), classification_changes=bool(best < o.fraction - 1e-9 and o.fraction > .4 and best <= .4),
                             shortest_time=first_t, reduction=float(o.fraction - best)))
        print(city, col, len(sample), flush=True)
    return rows


rows = run(sys.argv[1])
d = pd.DataFrame(rows); d.to_csv(HERE / f'rutas_k_{sys.argv[1]}.csv', index=False)
print(d.groupby('slot')[['paths_within_budget', 'lower_found', 'classification_changes', 'reduction']].agg(['mean', 'max']).round(3).to_string())
