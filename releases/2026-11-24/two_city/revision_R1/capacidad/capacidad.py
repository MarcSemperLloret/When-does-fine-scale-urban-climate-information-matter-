"""Capacity sensitivity (R2#3, R5#5, R6 3.2) with full P/U/C/X states and shortlist overlap.

For 288 cases x capacities {5,10,15,20,25}% of reachable sections: P and U losses (local reference,
published definition), minimum common loss by MILP (maximise the smaller normalised capture), and
overlap between local, regional, uniform and population lists. Uses only the stored section scores.
"""
from pathlib import Path
import sys, numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor
from scipy.optimize import milp, Bounds, LinearConstraint
REL=(lambda r:r if (r/'datos/policy_scores_two_cities.parquet').exists() else Path(__file__).resolve().parents[2]/'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city')(Path(__file__).resolve().parents[2])
CAPS=[.05,.10,.15,.20,.25]
def top(x,k):return np.argsort(-x,kind='stable')[:k]
def common_loss(u,b,k):
    n=len(u);na=100*u/u[top(u,k)].sum();nb=100*b/b[top(b,k)].sum()
    A=np.stack([np.r_[np.ones(n),0.],np.r_[na,-1.],np.r_[nb,-1.]])
    res=milp(np.r_[np.zeros(n),-1.],integrality=np.r_[np.ones(n),0.],bounds=Bounds(np.zeros(n+1),np.r_[np.ones(n),100.]),
             constraints=LinearConstraint(A,[k,0,0],[k,np.inf,np.inf]),options={'time_limit':120,'mip_rel_gap':1e-8})
    if res.x is None:return np.nan,'failed',np.nan
    take=np.flatnonzero(res.x[:-1]>.5)
    loss=float(100-min(na[take].sum(),nb[take].sum()))
    return loss,'optimal' if res.success and res.status==0 else 'time_limit',float(100+res.mip_dual_bound)
def work(task):
    meta,u,b,un,p=task;out=[]
    for cap in CAPS:
        k=int(cap*len(u))
        lL,lR,lU,lP=top(u,k),top(b,k),top(un,k),top(p,k)
        optL=u[lL].sum();optR=b[lR].sum()
        ml,st,lb=common_loss(u,b,k)
        ch=lambda x,y:k-len(np.intersect1d(x,y))
        out.append(dict(**meta,capacity=cap,k=k,pop_loss=100*(1-u[lP].sum()/optL),uni_loss=100*(1-u[lU].sum()/optL),
            pop_loss_both=max(100*(1-u[lP].sum()/optL),100*(1-b[lP].sum()/optR)),uni_loss_both=max(100*(1-u[lU].sum()/optL),100*(1-b[lU].sum()/optR)),
            regional_list_local_loss=100*(1-u[lR].sum()/optL),minimum_common_loss=ml,milp_status=st,common_loss_lower_bound=lb,
            changed_local_regional=ch(lL,lR),changed_local_uniform=ch(lL,lU),changed_local_population=ch(lL,lP)))
    return out
def main():
    pol=pd.read_parquet(REL/'datos/policy_scores_two_cities.parquet')
    tasks=[]
    for key,g in pol.groupby(['city','mode','window','threshold','phi']):
        g=g[g.reachable].sort_values('CUSEC')
        sec=pd.read_csv(REL/f'datos/secciones_{key[0]}.csv',dtype={'CUSEC':str}).set_index('CUSEC')
        p=sec.loc[g.CUSEC.astype(str),'pob_65'].to_numpy()
        tasks.append((dict(zip(['city','mode','window','threshold','phi'],key)),g.local.to_numpy(),g.regional.to_numpy(),g.uniform.to_numpy(),p))
    rows=[]
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv)>1 else 6) as ex:
        for i,r in enumerate(ex.map(work,tasks)):
            rows+=r
            if i%24==0:print(i,flush=True)
    d=pd.DataFrame(rows);d.to_csv('capacidad_288x5.csv',index=False)
    ref=pd.read_csv(REL/'tablas/policy_sensitivity_two_cities.csv')
    c=d[d.capacity==.15].merge(ref,on=['city','mode','window','threshold','phi'])
    print('max |dP|',(c.pop_loss-c.population_loss_percent).abs().max(),'max |dU|',(c.uni_loss-c.uniform_loss_percent).abs().max(),
          'max |dC|',(c.minimum_common_loss-c.minimum_common_loss_percent).abs().max())
if __name__=='__main__':main()
