"""Robustness checks for the heat-access score (R1#1, R2#2/#5, R4#3, R5#1/#2, R6 2.1/3.1).

1. Continuous formulations replacing the binary conjunction (central capacity, all 12 city/window/mode settings):
   soft  : f = 1-(1-g(T))(1-h(q)),  g ramp on T, h ramp on exposed fraction q  (continuous Eq. 1)
   load  : f = q * g(T)              (sun-exposed heat load)
2. Rank correlation of the central local score with population, shade-only and temperature-only scores.
3. Section-hours near the shade threshold and 21- vs 41-weight route classification.
4. Slower walking speeds (0.75 and 0.6 m/s, i.e. 12.5- and 10-min budgets at 0.9 m/s) on all 288 cases;
   hours whose chosen route exceeds the shorter budget take q=1 (conservative) or keep q (optimistic).
"""
from pathlib import Path
import sys, numpy as np, pandas as pd
from scipy.stats import spearmanr
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'capacidad'));from capacidad import common_loss, top
M3=Path(__file__).resolve().parents[2];REL=(lambda r:r if (r/'datos/policy_scores_two_cities.parquet').exists() else Path(__file__).resolve().parents[2]/'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city')(Path(__file__).resolve().parents[2])
pol=pd.read_parquet(REL/'datos/policy_scores_two_cities.parquet')
ramp=lambda x,a,b:np.clip((x-a)/(b-a),0,1)
FORMS={'soft_T28-32_q0.2-0.6':lambda T,q:1-(1-ramp(T,28,32))*(1-ramp(q,.2,.6)),
       'soft_T26-34_q0.1-0.7':lambda T,q:1-(1-ramp(T,26,34))*(1-ramp(q,.1,.7)),
       'load_T28-32':lambda T,q:q*ramp(T,28,32),
       'load_T26-34':lambda T,q:q*ramp(T,26,34)}
F1=[];F2=[];F3=[];F4=[]
def lossf(s,sel,k):return 100*(1-s[sel].sum()/np.sort(s)[-k:].sum())
for city in ['Valencia','Madrid']:
    sec=pd.read_csv(REL/f'datos/secciones_{city}.csv',dtype={'CUSEC':str}).sort_values('CUSEC').reset_index(drop=True);P=sec.pob_65.to_numpy()
    allr=pd.read_parquet(M3/f'Madrid_2026-09-07/datos/rutas_central_{city}_working_Full.parquet')
    for w in ['Morning','Afternoon']:
        f=M3/(f'Madrid_2026-09-07/datos/campos_central_{w}.npz' if city=='Madrid' else f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz')
        z=np.load(f);L=z['local'].astype(float);R=z['regional'].astype(float);months=z['months'];hours=z['hours'];U=np.broadcast_to(L.mean(axis=0),L.shape)
        keys=[f'{m:02}-15' for m in months]
        for mode in ['network','connectors_sun','connectors_shade']:
            rr={wt:allr[(allr['mode']==mode)&(allr.weights==wt)] for wt in [21,41]}
            reach=rr[21][rr[21].date.eq('06-15')&rr[21].hour.eq(10)].set_index('CUSEC').loc[sec.CUSEC]
            ix=np.flatnonzero(reach.reachable.to_numpy());p=P[ix];k=int(.15*len(ix))
            def mat(wt,col):
                lk={(d,h):rr[wt][rr[wt].date.eq(d)&rr[wt].hour.eq(h)].set_index('CUSEC').loc[sec.CUSEC][col].to_numpy()[ix] for d,h in sorted(set(zip(keys,hours)))}
                return np.stack([lk[d,h] for d,h in zip(keys,hours)],axis=1).astype(float)
            q=mat(21,'fraction');q41=mat(41,'fraction');tm=mat(21,'time_min');st=reach.shortest_time_min.to_numpy()[ix]
            Li,Ri,Ui=L[ix],R[ix],U[ix]
            # 1. continuous formulations
            for name,fn in FORMS.items():
                sL=p*fn(Li,q).mean(1);sR=p*fn(Ri,q).mean(1);sU=p*fn(Ui,q).mean(1)
                lL,lR,lU,lP=top(sL,k),top(sR,k),top(sU,k),top(p,k)
                ml,stt,_=common_loss(sL,sR,k)
                F1.append(dict(city=city,window=w,mode=mode,form=name,k=k,pop_loss=lossf(sL,lP,k),uni_loss=lossf(sL,lU,k),
                    pop_loss_both=max(lossf(sL,lP,k),lossf(sR,lP,k)),uni_loss_both=max(lossf(sL,lU,k),lossf(sR,lU,k)),
                    minimum_common_loss=ml,milp=stt,changed_local_regional=k-len(np.intersect1d(lL,lR)),changed_local_uniform=k-len(np.intersect1d(lL,lU))))
            # 2. decomposition (central 30 C, phi 0.4)
            s=q<=.4+1e-12;sL=p*(1-((Li<30)&s).mean(1))
            F2.append(dict(city=city,window=w,mode=mode,rho_population=spearmanr(sL,p)[0],rho_shade_only=spearmanr(sL,p*(1-s.mean(1)))[0],
                rho_temperature_only=spearmanr(sL,p*(Li>=30).mean(1))[0],rho_temperature_only_given_shade=spearmanr(sL,p*((Li>=30)&s).mean(1))[0]))
            # 3. shade threshold proximity
            near=np.abs(q-.4)<=.05;flip=(q<=.4)!=(q41<=.4)
            F3.append(dict(city=city,window=w,mode=mode,share_near_0p05=float(near.mean()),share_flip_21_41=float(flip.mean()),share_flip_among_near=float(flip[near].mean()) if near.any() else np.nan))
            # 4. slower walking speeds, all thresholds/phi
            for v in [0.9,0.75,0.6]:
                B=15*v/0.9;keep=st<=B+1e-9;jx=np.flatnonzero(keep);kk=int(.15*len(jx))
                for variant in ['conservative','optimistic']:
                    qq=q[jx].copy()
                    if variant=='conservative':qq[tm[jx]>B+1e-9]=1.0
                    for thr in [28,30,32]:
                        bl=Li[jx]<thr;bu=Ui[jx]<thr;br=Ri[jx]<thr
                        for phi in [.1,.2,.3,.4,.5,.6,.7,1.]:
                            sh=qq<=phi+1e-12;pp=p[jx]
                            sl=pp*(1-(bl&sh).mean(1));su=pp*(1-(bu&sh).mean(1))
                            F4.append(dict(city=city,window=w,mode=mode,speed=v,variant=variant,threshold=thr,phi=phi,N=len(jx),k=kk,
                                pop_loss=lossf(sl,top(pp,kk),kk),uni_loss=lossf(sl,top(su,kk),kk)))
            print(city,w,mode,flush=True)
for name,F in [('continuas',F1),('descomposicion',F2),('umbral_sombra',F3),('velocidad',F4)]:pd.DataFrame(F).to_csv(f'{name}.csv',index=False)
