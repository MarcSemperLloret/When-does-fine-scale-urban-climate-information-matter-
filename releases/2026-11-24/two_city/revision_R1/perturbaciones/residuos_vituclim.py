"""Persistent site residuals (observed anomaly minus IDW anomaly) at the 29 VITUclim sites and their spatial structure."""
from pathlib import Path
import json, numpy as np, pandas as pd
from scipy.optimize import curve_fit
V=Path(__file__).resolve().parents[2]/'validacion_vituclim_2025'
m=pd.read_parquet(V/'matched_pairs.parquet').dropna(subset=['IDW','observed'])
st=pd.read_parquet(V/'stations_selected.parquet')
import pyproj
tr=pyproj.Transformer.from_crs(4326,25830,always_xy=True)
st['x'],st['y']=tr.transform(st.longitude.to_numpy(),st.latitude.to_numpy())
xy=st.set_index('station_id')[['x','y']]
expo=lambda h,n,s,r:n+s*(1-np.exp(-h/r))
rows=[];res={}
for (clock,w),g in m.groupby(['clock','window']):
    g=g.copy()
    for c in ['IDW','observed']:g[c+'_a']=g[c]-g.groupby('timestamp')[c].transform('mean')
    g['r']=g.observed_a-g.IDW_a
    site=g.groupby('station_id').r.mean();hourly_sd=float((g.r-g.station_id.map(site)).std())
    P=xy.loc[site.index].to_numpy();D=np.hypot(*(P[:,None,:]-P[None,:,:]).transpose(2,0,1))
    iu=np.triu_indices(len(site),1);h=D[iu];gam=0.5*(site.values[:,None]-site.values[None,:])[iu]**2
    bins=np.array([0,500,1000,1500,2000,3000,4000,6000,9000]);b=np.digitize(h,bins)
    hb=np.array([h[b==i].mean() for i in range(1,len(bins)) if (b==i).sum()>=5]);gb=np.array([gam[b==i].mean() for i in range(1,len(bins)) if (b==i).sum()>=5])
    nb=np.array([(b==i).sum() for i in range(1,len(bins)) if (b==i).sum()>=5])
    try:
        (n,s,r),_=curve_fit(expo,hb,gb,p0=[gb[0]/2,site.var(),1500],bounds=([0,0,100],[np.inf,np.inf,20000]),sigma=1/np.sqrt(nb))
    except Exception as e:n=s=r=np.nan
    rows.append(dict(clock=clock,window=w,n_sites=len(site),site_resid_sd=float(site.std()),hourly_resid_sd=hourly_sd,nugget=n,sill_partial=s,range_m=r,nugget_share=n/(n+s) if n+s>0 else np.nan))
    res[f'{clock}_{w}']=dict(bins_m=hb.round(0).tolist(),gamma=gb.round(4).tolist(),pairs=nb.tolist())
d=pd.DataFrame(rows);print(d.round(3).to_string());d.to_csv('residuos_vituclim.csv',index=False)
json.dump(res,open('variogramas_empiricos.json','w'),indent=1);print(json.dumps(res,indent=0)[:1500])
