"""Sufficiency conditioned on how much the local score can depend on local temperature (simulated reviewer 1, point 1).
The local-exclusive share is the fraction of the local top-list score that comes from hours in which local
temperature exceeds the threshold where the regional field does not (D^L, Methods 3.2)."""
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
M3 = HERE.parents[1]
REL=(lambda r:r if (r/'datos/policy_scores_two_cities.parquet').exists() else Path(__file__).resolve().parents[2]/'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city')(Path(__file__).resolve().parents[2])
E = 1 + 1e-7
m = pd.read_csv(REL / 'tablas/mechanism_summary.csv')
c = pd.read_csv(HERE.parent / 'capacidad/capacidad_288x5_estados.csv'); c = c[c.capacity == .15]
c['state'] = np.select([c.pop_loss_both <= E, c.uni_loss_both <= E, c.minimum_common_loss <= E], ['P', 'U', 'C'], 'X')
d = c.merge(m[['city', 'window', 'mode', 'threshold', 'phi', 'local_only_failure_local_top_score_share']], on=['city', 'window', 'mode', 'threshold', 'phi'])
d['share'] = 100 * d.local_only_failure_local_top_score_share
d['band'] = pd.cut(d.share, [-1, 2, 5, 100], labels=['<2%', '2-5%', '>=5%'])
t = d.pivot_table(index='band', columns='state', values='k', aggfunc='count', fill_value=0, observed=False)[list('PUCX')]
t['cases'] = t.sum(1); t['simple'] = t.P + t.U
print(t.to_string())
print(d.groupby(['band', 'city', 'window'], observed=False).size().unstack(['city', 'window']).to_string())
t.to_csv(HERE / 'suficiencia_por_peso_local.csv')
