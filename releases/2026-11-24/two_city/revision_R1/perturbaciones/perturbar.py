"""Spatially varying, residual-informed perturbations of the station field (R5#6, R6 3.3, R4#4).

Persistent error e(s) ~ GP(0, sigma^2 * exp(-d/range)) on census-section centroids (range 0 = independent),
optionally plus iid hourly noise. sigma from VITUclim persistent site residuals (0.40-0.59 C).
For each realisation and each of the 288 cases: P/U sufficiency (local loss <=1%), list turnover
vs station list, station-list loss. Regional field unchanged. Madrid uses Valencia statistics (transfer).
"""
from pathlib import Path
import sys, numpy as np, pandas as pd, geopandas as gpd
M3=Path(__file__).resolve().parents[2]
REL=(lambda r:r if (r/'datos/policy_scores_two_cities.parquet').exists() else Path(__file__).resolve().parents[2]/'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city')(Path(__file__).resolve().parents[2])
CONFIGS=[(0.4,0,0),(0.6,0,0),(0.4,1000,0),(0.6,1000,0),(0.4,2500,0),(0.6,2500,0),(0.4,5000,0),(0.6,5000,0),(0.6,0,0.5)]
NREAL=int(sys.argv[1]) if len(sys.argv)>1 else 100
PHI=[.1,.2,.3,.4,.5,.6,.7,1.];TH=[28,30,32]
def top(x,k):return np.argsort(-x,kind='stable')[:k]
pol=pd.read_parquet(REL/'datos/policy_scores_two_cities.parquet')
rows=[]
for city in ['Valencia','Madrid']:
    sec=pd.read_csv(REL/f'datos/secciones_{city}.csv',dtype={'CUSEC':str}).sort_values('CUSEC').reset_index(drop=True)
    g=gpd.read_file(REL/f'fixed/mapas/{city}_a1.gpkg').to_crs(25830);g['CUSEC']=g.CUSEC.astype(str)
    g=g.drop_duplicates('CUSEC').set_index('CUSEC').loc[sec.CUSEC];c=g.geometry.centroid
    XY=np.c_[c.x,c.y];D=np.hypot(*(XY[:,None,:]-XY[None,:,:]).transpose(2,0,1))
    P=sec.pob_65.to_numpy();n=len(sec)
    routes=pd.read_parquet(M3/f'Madrid_2026-09-07/datos/rutas_central_{city}_working_Full.parquet').query('weights==21')
    fields={}
    for w in ['Morning','Afternoon']:
        f=M3/(f'Madrid_2026-09-07/datos/campos_central_{w}.npz' if city=='Madrid' else f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz')
        z=np.load(f);fields[w]=(z['local'].astype(float),z['months'],z['hours'])
    # case set-up: per window/mode -> ix,k,shade masks per phi, reference lists
    cases=[]
    for w,(L,months,hours) in fields.items():
        for mode,rr in routes.groupby('mode'):
            reach=rr[rr.date.eq('06-15')&rr.hour.eq(10)].set_index('CUSEC').loc[sec.CUSEC].reachable.to_numpy()
            ix=np.flatnonzero(reach);k=int(.15*len(ix))
            lookup={(int(d[:2]),h):rr[rr.date.eq(d)&rr.hour.eq(h)].set_index('CUSEC').loc[sec.CUSEC].fraction.to_numpy()[ix] for d,h in sorted(set(zip([f'{m:02}-15' for m in months],hours)))}
            frac=np.stack([lookup[m,h] for m,h in zip(months,hours)],axis=1)
            for thr in TH:
                for phi in PHI:
                    o=pol.query('city==@city and window==@w and mode==@mode and threshold==@thr and phi==@phi').sort_values('CUSEC')
                    sL=o.local.to_numpy()[ix];sU=o.uniform.to_numpy()[ix]
                    cases.append(dict(w=w,mode=mode,thr=thr,phi=phi,ix=ix,k=k,shade=frac<=phi+1e-12,lP=top(P[ix],k),lU=top(sU,k),lL=top(sL,k)))
    rng=np.random.default_rng(20261123)
    for sigma,rng_m,hsd in CONFIGS:
        Lc=np.linalg.cholesky(np.exp(-D/rng_m)+1e-8*np.eye(n)) if rng_m>0 else None
        for r in range(NREAL):
            e=sigma*(Lc@rng.standard_normal(n) if Lc is not None else rng.standard_normal(n))
            pert={}
            for w,(L,_,_) in fields.items():
                F=L+e[:,None]
                if hsd>0:F=F+hsd*rng.standard_normal(L.shape)
                pert[w]=F
            for cs in cases:
                ix,k=cs['ix'],cs['k'];p=P[ix]
                s=p*(1-((pert[cs['w']][ix]<cs['thr'])&cs['shade']).mean(axis=1))
                opt=np.sort(s)[-k:].sum();lA=top(s,k)
                ls=lambda sel:100*(1-s[sel].sum()/opt)
                rows.append(dict(city=city,window=cs['w'],mode=cs['mode'],threshold=cs['thr'],phi=cs['phi'],sigma=sigma,range_m=rng_m,hourly_sd=hsd,real=r,k=k,
                    pop_loss=ls(cs['lP']),uni_loss=ls(cs['lU']),station_list_loss=ls(cs['lL']),changed_vs_station=k-len(np.intersect1d(lA,cs['lL']))))
        print(city,sigma,rng_m,hsd,flush=True)
pd.DataFrame(rows).to_parquet(f'perturbaciones_{NREAL}.parquet',index=False)
