"""Sites per corrected ERA5-Land cell and their observed/predicted anomalies (R1 major 4)."""
from pathlib import Path
import numpy as np, pandas as pd
V=Path(__file__).resolve().parents[2]/'validacion_vituclim_2025'
m=pd.read_parquet(V/'matched_pairs.parquet').dropna(subset=['observed','ERA5_corrected','IDW'])
st=pd.read_parquet(V/'stations_selected.parquet').set_index('station_id')
rows=[]
for (clock,w),g in m.groupby(['clock','window']):
    g=g.copy()
    # cell id: sites sharing identical ERA5 series = same cell
    sig=g.pivot_table(index='timestamp',columns='station_id',values='ERA5_corrected').round(6).dropna()
    groups={};[groups.setdefault(tuple(sig[s].values[:200]),[]).append(s) for s in sig.columns]
    cell={s:i for i,(k,v) in enumerate(sorted(groups.items(),key=lambda kv:np.mean([st.loc[s,'longitude'] for s in kv[1]]))) for s in v}
    for c in ['observed','ERA5_corrected','IDW']:g[c+'_a']=g[c]-g.groupby('timestamp')[c].transform('mean')
    g['cell']=g.station_id.map(cell)
    t=g.groupby('cell').agg(n_sites=('station_id','nunique'),obs_anom=('observed_a','mean'),era5_anom=('ERA5_corrected_a','mean'),idw_anom=('IDW_a','mean'))
    t['mean_lon']=[np.mean([st.loc[s,'longitude'] for s in v]) for v in [[s for s in cell if cell[s]==i] for i in t.index]]
    for i,r in t.iterrows():rows.append(dict(clock=clock,window=w,cell=i,**r.to_dict()))
d=pd.DataFrame(rows);print(d.round(3).to_string());d.to_csv('celdas_era5/celdas_era5.csv',index=False)
