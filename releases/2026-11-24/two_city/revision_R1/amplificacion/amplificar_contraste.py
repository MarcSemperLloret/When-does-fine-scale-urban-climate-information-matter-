"""Gradient-amplification experiment (reviewers R1#2, R2#1, R3, R4#4, R5#3/#6, R6).

Local field at amplification a:  L_a(s,t) = Lbar(t) + a * (L(s,t) - Lbar(t)),
Lbar(t) = hourly citywide mean of the station field (the uniform comparator).
a=0 reproduces the uniform reference and a=1 the station field. Regional (ERA5-Land) is unchanged.
For each of the 288 grid cases and each a: P and U lists (simple rules) evaluated
under L_a and regional, top-k overlap with the station (a=1) and uniform lists.
"""
from pathlib import Path
import numpy as np, pandas as pd
M3=Path(__file__).resolve().parents[2]
REL=(lambda r:r if (r/'datos/policy_scores_two_cities.parquet').exists() else Path(__file__).resolve().parents[2]/'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city')(Path(__file__).resolve().parents[2])
A_GRID=[0,0.5,1,1.3,1.5,2,2.5,3,3.5,4]
def top(x,k):return np.lexsort((np.arange(len(x)),-x))[:k]
def loss(score,sel,k):return 100*(1-score[sel].sum()/np.sort(score)[-k:].sum())
pol=pd.read_parquet(REL/'datos/policy_scores_two_cities.parquet')
ref=pd.read_csv(REL/'tablas/policy_sensitivity_two_cities.csv')
rows=[]
for city in ['Valencia','Madrid']:
    sec=pd.read_csv(REL/f'datos/secciones_{city}.csv',dtype={'CUSEC':str}).sort_values('CUSEC').reset_index(drop=True)
    P=sec.pob_65.to_numpy()
    routes=pd.read_parquet(M3/f'Madrid_2026-09-07/datos/rutas_central_{city}_working_Full.parquet').query('weights==21')
    for w in ['Morning','Afternoon']:
        f=M3/(f'Madrid_2026-09-07/datos/campos_central_{w}.npz' if city=='Madrid' else f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz')
        z=np.load(f);L=z['local'].astype(float);R=z['regional'].astype(float);months=z['months'];hours=z['hours']
        if 'CUSEC' in z:assert np.array_equal(sec.CUSEC.to_numpy(),z['CUSEC'].astype(str))
        Lbar=L.mean(axis=0,keepdims=True)
        for mode,rr in routes.groupby('mode'):
            reach=rr[rr.date.eq('06-15')&rr.hour.eq(10)].set_index('CUSEC').loc[sec.CUSEC].reachable.to_numpy()
            ix=np.flatnonzero(reach);k=int(.15*len(ix));p=P[ix]
            lookup={(int(d[:2]),h):rr[rr.date.eq(d)&rr.hour.eq(h)].set_index('CUSEC').loc[sec.CUSEC].fraction.to_numpy()[ix] for d,h in sorted(set(zip([f'{m:02}-15' for m in months],hours)))}
            frac=np.stack([lookup[m,h] for m,h in zip(months,hours)],axis=1)
            for thr in [28,30,32]:
                for phi in sorted(pol.phi.unique()):
                    shade=frac<=phi+1e-12
                    fn=lambda F:p*(1-((F<thr)&shade).mean(axis=1))
                    orig=pol.query('city==@city and window==@w and mode==@mode and threshold==@thr and phi==@phi').sort_values('CUSEC')
                    assert len(orig)==len(sec) and orig.quota.iloc[0]==k
                    sR=orig.regional.to_numpy()[ix];sU=orig.uniform.to_numpy()[ix];sL=orig.local.to_numpy()[ix]
                    assert np.allclose(fn(L[ix]),sL,atol=1e-9) and np.allclose(fn(R[ix]),sR,atol=1e-9)
                    u0=fn(np.broadcast_to(Lbar,L.shape)[ix]);uok=bool(np.allclose(u0,sU,atol=1e-9))
                    lP=top(p,k);lU=top(sU,k);lL=top(sL,k);lR=top(sR,k)
                    for a in A_GRID:
                        sA=sL if a==1 else (sU if a==0 and uok else fn((Lbar+a*(L-Lbar))[ix]))
                        lA=top(sA,k)
                        rows.append(dict(city=city,window=w,mode=mode,threshold=thr,phi=phi,a=a,k=k,uniform_is_a0=uok,
                            pop_loss=loss(sA,lP,k),uni_loss=loss(sA,lU,k),pop_loss_both=max(loss(sA,lP,k),loss(sR,lP,k)),uni_loss_both=max(loss(sA,lU,k),loss(sR,lU,k)),
                            station_list_loss_under_a=loss(sA,lL,k),regional_list_loss_under_a=loss(sA,lR,k),
                            changed_vs_station=k-len(np.intersect1d(lA,lL)),changed_vs_uniform=k-len(np.intersect1d(lA,lU)),
                            changed_vs_regional=k-len(np.intersect1d(lA,lR))))
            print(city,w,mode,flush=True)
d=pd.DataFrame(rows)
# Reproduction check at a=1 against the published table
c=d[d.a==1].merge(ref,on=['city','mode','window','threshold','phi'])
assert len(c)==288
assert (c.pop_loss-c.population_loss_percent).abs().max()<1e-6 and (c.uni_loss-c.uniform_loss_percent).abs().max()<1e-6
print('max |pop loss diff|',float((c.pop_loss-c.population_loss_percent).abs().max()),'max |uni loss diff|',float((c.uni_loss-c.uniform_loss_percent).abs().max()))
print('uniform reproduced by a=0 in',int(d[d.a==0].uniform_is_a0.sum()),'of 288')
d.to_csv('amplificacion_288.csv',index=False)
