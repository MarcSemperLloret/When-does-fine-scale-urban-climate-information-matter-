"""Is the easternmost AVAMET station (c15m250e08) representative of its surroundings? (R5 siting concern)

VITUclim timestamps are taken as UTC (reloj_vituclim.py). For each of the six AVAMET input stations, the mean
difference between the station and the VITUclim sites for which it is the nearest AVAMET station is computed
over the access-window hours of summer 2025. A station whose offset departs from the others would carry a
siting signal rather than a neighbourhood one. Each station's anomaly relative to the six-station mean is also
compared with the anomaly of its neighbouring sites relative to the 29-site mean.
"""
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
M3 = HERE.parents[1]
V = M3 / 'validacion_vituclim_2025'
obs = pd.read_parquet(V / 'observations_hourly.parquet')
st = pd.read_parquet(V / 'stations_selected.parquet').set_index('station_id')
sites = sorted(pd.read_parquet(V / 'matched_pairs.parquet').station_id.unique())
obs = obs[obs.station_id.isin(sites)].copy()
obs['local'] = (pd.DatetimeIndex(obs.clock_hour).tz_localize('UTC').tz_convert('Europe/Madrid').tz_localize(None))
SIX = ['c15m250e30', 'c15m250e15', 'c15m250e24', 'c15m250e11', 'c15m250e26', 'c15m250e08']
av = pd.read_parquet(M3 / 'datos/valencia_verano_qc.parquet', columns=['station_id', 'observed_local', 't_qc'])
av = av[(av.observed_local.dt.year == 2025) & av.station_id.isin(SIX)]
av['local'] = av.observed_local.dt.floor('h')
ah = av.groupby(['station_id', 'local']).t_qc.mean().unstack(0)
vh = obs.pivot_table(index='local', columns='station_id', values='observed')
rows = []
for w, hrs in [('Morning', [10, 11, 12]), ('Afternoon', [16, 17, 18])]:
    idx = ah.index.intersection(vh.index); idx = idx[idx.hour.isin(hrs)]
    A = ah.loc[idx]; Vv = vh.loc[idx]
    a_anom = A.sub(A.mean(1), axis=0); v_anom = Vv.sub(Vv.mean(1), axis=0)
    for s in SIX:
        nb = [i for i in sites if st.loc[i, 'nearest_avamet'] == s]
        if not nb:
            continue
        diff = A[s].to_frame().values - Vv[nb].values
        rows.append(dict(window=w, station=s, n_sites=len(nb), median_distance_m=float(st.loc[nb, 'nearest_avamet_distance_m'].median()),
                         station_minus_sites=float(np.nanmean(diff)), station_anomaly=float(a_anom[s].mean()),
                         sites_anomaly=float(v_anom[nb].mean().mean()), station_lon=float(av[av.station_id == s].observed_local.size and 0) or np.nan))
d = pd.DataFrame(rows).drop(columns='station_lon')
d.to_csv(HERE / 'estacion_costera.csv', index=False)
print(d.round(3).to_string())
