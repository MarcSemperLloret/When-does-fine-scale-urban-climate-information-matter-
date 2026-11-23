"""Rango observacional del factor de amplificación a del contraste espacial IDW (Valencia, VITUclim 2025)."""
from pathlib import Path
import json, numpy as np, pandas as pd
V=Path(__file__).resolve().parents[2]/'validacion_vituclim_2025'
m=pd.read_parquet(V/'matched_pairs.parquet').dropna(subset=['IDW','observed'])
out=[]
for (clock,w),g in m.groupby(['clock','window']):
    # hourly spatial anomalies across sites with data at that hour
    g=g.copy()
    for c in ['IDW','observed']:g[c+'_a']=g[c]-g.groupby('timestamp')[c].transform('mean')
    x,o=g.IDW_a.to_numpy(),g.observed_a.to_numpy()
    s=g.groupby('station_id')[['IDW_a','observed_a']].mean()
    xs,os_=s.IDW_a.to_numpy(),s.observed_a.to_numpy()
    out.append(dict(clock=clock,window=w,n_sites=len(s),n_pairs=len(g),
        hourly_pred_on_obs=float(np.polyfit(o,x,1)[0]),hourly_obs_on_pred=float(np.polyfit(x,o,1)[0]),
        hourly_sd_ratio=float(o.std()/x.std()),
        site_pred_on_obs=float(np.polyfit(os_,xs,1)[0]),site_obs_on_pred=float(np.polyfit(xs,os_,1)[0]),
        site_sd_ratio=float(os_.std()/xs.std()),site_r=float(np.corrcoef(xs,os_)[0,1])))
d=pd.DataFrame(out);print(d.round(3).to_string());d.to_csv('calibracion_amplificacion.csv',index=False)
