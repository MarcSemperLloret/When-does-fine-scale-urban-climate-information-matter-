"""P/U/C/X states under gradient amplification a (15% capacity); C needs the common-loss MILP."""
from pathlib import Path
import sys, numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0,str(Path(__file__).parent));from capacidad import common_loss, top
M3=Path(__file__).resolve().parents[2];REL=(lambda r:r if (r/'datos/policy_scores_two_cities.parquet').exists() else Path(__file__).resolve().parents[2]/'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city')(Path(__file__).resolve().parents[2])
A_GRID=[0.5,1,1.3,1.5,2,2.5,3,4]
def work(t):
    meta,a,sA,sR,sU,p,k=t;ml,st,_=common_loss(sA,sR,k)
    lo=lambda sel:100*(1-sA[sel].sum()/np.sort(sA)[-k:].sum())
    loR=lambda sel:100*(1-sR[sel].sum()/np.sort(sR)[-k:].sum())
    return dict(**meta,a=a,k=k,pop_loss=lo(top(p,k)),uni_loss=lo(top(sU,k)),pop_loss_R=loR(top(p,k)),uni_loss_R=loR(top(sU,k)),minimum_common_loss=ml,milp_status=st)
def tasks():
    pol=pd.read_parquet(REL/'datos/policy_scores_two_cities.parquet')
    for city in ['Valencia','Madrid']:
        sec=pd.read_csv(REL/f'datos/secciones_{city}.csv',dtype={'CUSEC':str}).sort_values('CUSEC').reset_index(drop=True);P=sec.pob_65.to_numpy()
        routes=pd.read_parquet(M3/f'Madrid_2026-09-07/datos/rutas_central_{city}_working_Full.parquet').query('weights==21')
        for w in ['Morning','Afternoon']:
            f=M3/(f'Madrid_2026-09-07/datos/campos_central_{w}.npz' if city=='Madrid' else f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz')
            z=np.load(f);L=z['local'].astype(float);months=z['months'];hours=z['hours'];Lbar=L.mean(axis=0,keepdims=True)
            for mode,rr in routes.groupby('mode'):
                reach=rr[rr.date.eq('06-15')&rr.hour.eq(10)].set_index('CUSEC').loc[sec.CUSEC].reachable.to_numpy()
                ix=np.flatnonzero(reach);k=int(.15*len(ix));p=P[ix]
                lookup={(int(d[:2]),h):rr[rr.date.eq(d)&rr.hour.eq(h)].set_index('CUSEC').loc[sec.CUSEC].fraction.to_numpy()[ix] for d,h in sorted(set(zip([f'{m:02}-15' for m in months],hours)))}
                frac=np.stack([lookup[m,h] for m,h in zip(months,hours)],axis=1)
                for a in A_GRID:
                    F=(Lbar+a*(L-Lbar))[ix]
                    for thr in [28,30,32]:
                        below=F<thr
                        for phi in [.1,.2,.3,.4,.5,.6,.7,1.]:
                            o=pol.query('city==@city and window==@w and mode==@mode and threshold==@thr and phi==@phi').sort_values('CUSEC')
                            sA=p*(1-(below&(frac<=phi+1e-12)).mean(axis=1))
                            if a==1:sA=o.local.to_numpy()[ix]
                            yield (dict(city=city,window=w,mode=mode,threshold=thr,phi=phi),a,sA,o.regional.to_numpy()[ix],o.uniform.to_numpy()[ix],p,k)
                print(city,w,mode,flush=True)
if __name__=='__main__':
    rows=[]
    with ProcessPoolExecutor(6) as ex:
        for r in ex.map(work,tasks(),chunksize=4):rows.append(r)
    d=pd.DataFrame(rows);d.to_csv('estados_amplificacion.csv',index=False)
    e=1+1e-7;d['state']=np.select([(d.pop_loss<=e)&(d.pop_loss_R<=e),(d.uni_loss<=e)&(d.uni_loss_R<=e),d.minimum_common_loss<=e],['P','U','C'],'X')
    print(d.milp_status.value_counts().to_dict())
    print(d.pivot_table(index='a',columns='state',values='k',aggfunc='count',fill_value=0).to_string())
    print(d.assign(X=d.state.eq('X')).pivot_table(index=['city','window'],columns='a',values='X',aggfunc='sum').to_string())
