"""Regional-reference losses of the fixed shortlists (population, uniform and station-field lists) for all 288
cases. The regional field is unchanged in the amplification and perturbation experiments, so these losses
complete the two-reference sufficiency criterion of Methods 3.2 without rerunning them."""
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
REL=(lambda r:r if (r/'datos/policy_scores_two_cities.parquet').exists() else Path(__file__).resolve().parents[2]/'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city')(Path(__file__).resolve().parents[2])
pol = pd.read_parquet(REL / 'datos/policy_scores_two_cities.parquet')
secs = {c: pd.read_csv(REL / f'datos/secciones_{c}.csv', dtype={'CUSEC': str}).set_index('CUSEC') for c in ['Valencia', 'Madrid']}
rows = []
for (city, mode, w, thr, phi), g in pol.groupby(['city', 'mode', 'window', 'threshold', 'phi']):
    g = g[g.reachable].sort_values('CUSEC'); k = int(g.quota.iloc[0])
    p = secs[city].loc[g.CUSEC.astype(str), 'pob_65'].to_numpy()
    L, R, U = g.local.to_numpy(), g.regional.to_numpy(), g.uniform.to_numpy()
    top = lambda x: np.argsort(-x, kind='stable')[:k]
    lossR = lambda sel: 100 * (1 - R[sel].sum() / np.sort(R)[-k:].sum())
    rows.append(dict(city=city, mode=mode, window=w, threshold=thr, phi=phi,
                     pop_loss_R=lossR(top(p)), uni_loss_R=lossR(top(U)), station_list_loss_R=lossR(top(L))))
pd.DataFrame(rows).to_csv(HERE / 'regional_fijo.csv', index=False)
print(len(rows))
