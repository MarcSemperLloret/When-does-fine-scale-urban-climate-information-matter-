"""Independent, portable decision audit. No upstream weather/GIS imports.

python analisis/verificar_decisiones_portatil.py
python analisis/verificar_decisiones_portatil.py --resolve
--resolve independently resolves all 32 infeasible and 12 central minima.
"""
from pathlib import Path
import argparse,itertools,json,concurrent.futures
import numpy as np,pandas as pd
from scipy.optimize import milp,Bounds,LinearConstraint
R=Path(__file__).resolve().parents[1]
def order(u):return np.lexsort((np.arange(len(u)),-u))
def diagnostics(u,b,k,eps=.01):
    a=order(u);selected=a[:k];outside=a[k:];opt=u[selected].sum();v=order(b)[:k]
    costs=np.cumsum(np.sort(u[selected])[:min(k,len(outside))]-np.sort(u[outside])[::-1][:min(k,len(outside))])
    exchanged=len(set(selected)-set(v));loss=100*(opt-u[v].sum())/opt
    return dict(optimum=opt,exchanged=exchanged,loss_percent=loss,minimum_loss_same_swaps_percent=0. if not exchanged else 100*costs[exchanged-1]/opt,mandatory=int(((u[selected]-u[outside].max())>eps*opt+1e-8).sum()),possible=int(k+((u[selected].min()-u[outside])<=eps*opt+1e-8).sum()),max_swaps=int((costs<=eps*opt+1e-8).sum()))
def solve_minimum(task):
    key,u,b,k,expected=task;n=len(u);a=100*u/u[order(u)[:k]].sum();bb=100*b/b[order(b)[:k]].sum()
    A=np.stack([np.r_[np.ones(n),0],np.r_[a,-1],np.r_[bb,-1]])
    r=milp(np.r_[np.zeros(n),-1],integrality=np.r_[np.ones(n),0],bounds=Bounds(np.zeros(n+1),np.r_[np.ones(n),100]),constraints=LinearConstraint(A,[k,0,0],[k,np.inf,np.inf]),options={'time_limit':120,'mip_rel_gap':1e-8})
    assert r.success,(key,r.message)
    take=np.flatnonzero(r.x[:-1]>.5);capture=min(a[take].sum(),bb[take].sum());loss=100-capture
    assert len(take)==k and abs(loss-expected)<1e-6,(key,loss,expected)
    return dict(key=key,minimum_loss=loss,lower_bound_loss=100+float(r.mip_dual_bound),gap=float(r.mip_gap),passed=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--resolve',action='store_true');args=ap.parse_args()
    # Independent exhaustive oracle for additive near-optimal diagnostics.
    for u in [np.array([8.,7,5,4,2,1]),np.array([8.,8,5,5,2,2])]:
        k=3;a=set(order(u)[:k]);opt=u[list(a)].sum()
        for eps in [0,.01,.1,.3]:
            fam=[set(s) for s in itertools.combinations(range(6),k) if u[list(s)].sum()>=opt*(1-eps)-1e-8]
            q=diagnostics(u,u[::-1],k,eps)
            assert q['mandatory']==len(set.intersection(*fam)) and q['possible']==len(set.union(*fam)) and q['max_swaps']==max(len(a-s) for s in fam)
    d=pd.read_csv(R/'tablas/policy_sensitivity_two_cities.csv');s=pd.read_parquet(R/'datos/policy_scores_two_cities.parquet')
    assert len(d)==288 and (d.minimum_status=='optimal').all()
    assert d.balance_status.eq('optimal').sum()==256 and d.balance_status.eq('infeasible_by_minimum_loss').sum()==32
    attributes={c:pd.read_csv(R/f'datos/secciones_{c}.csv',dtype={'CUSEC':str}).set_index('CUSEC') for c in d.city.unique()}
    groups={key:f.sort_values('CUSEC') for key,f in s.groupby(['city','mode','window','threshold','phi'])};rows=[];tasks=[]
    for q in d.itertuples():
        key=(q.city,q.mode,q.window,q.threshold,q.phi);full=groups[key];f=full[full.reachable];u=f.local.to_numpy();b=f.regional.to_numpy();k=q.quota
        assert len(f)==q.reachable and k==int(.15*len(f)) and np.isfinite(full[['local','regional','uniform']]).all().all()
        a=attributes[q.city].loc[f.CUSEC];p=a.pob_65.to_numpy();g=a['CDIS' if q.city=='Madrid' else 'distrito'].to_numpy()
        for field,val in diagnostics(u,b,k).items():assert np.isclose(val,getattr(q,field),rtol=1e-9,atol=1e-7),(key,field,val,getattr(q,field))
        cert=json.loads((R/f'datos/cache_sensibilidad/{q.solver_key}.json').read_text())
        if q.balance_status=='optimal':
            ix=np.array(cert['indices']);assert len(ix)==k and len(set(ix))==k and min(ix)>=0 and max(ix)<len(f)
            cl=100*u[ix].sum()/u[order(u)[:k]].sum();cr=100*b[ix].sum()/b[order(b)[:k]].sum()
            tv=.5*sum(abs((g[ix]==v).sum()/k-p[g==v].sum()/p.sum()) for v in np.unique(g))
            assert cl>=99-1e-6 and cr>=99-1e-6
            assert np.allclose([cl,cr,tv],[q.local_capture,q.regional_capture,q.district_TV],atol=1e-8,rtol=0)
            assert cert['mip_gap']<=1e-8 and np.isclose(2*k*tv,cert['objective_bound'],atol=1e-6)
        else:assert q.minimum_common_loss_percent>1+1e-7
        central=q.threshold==30 and q.phi==.4
        if args.resolve and (central or q.balance_status!='optimal'):tasks.append((str(key),u,b,k,q.minimum_common_loss_percent))
        rows.append(dict(city=q.city,mode=q.mode,window=q.window,threshold=q.threshold,phi=q.phi,passed=True))
    pd.DataFrame(rows).to_csv(R/'qa/independent_decision_checks.csv',index=False)
    cap=pd.read_csv(R/'tablas/policy_capacity_two_cities.csv');assert len(cap)==8640
    for q in cap.itertuples():
        f=groups[q.city,q.mode,q.window,q.threshold,q.phi];f=f[f.reachable];calc=diagnostics(f.local.to_numpy(),f.regional.to_numpy(),q.quota,q.tolerance)
        for field,val in calc.items():assert np.isclose(val,getattr(q,field),rtol=1e-9,atol=1e-7),('capacity',q.Index,field)
    if tasks:
        with concurrent.futures.ProcessPoolExecutor(max_workers=3) as pool:proofs=list(pool.map(solve_minimum,tasks))
        pd.DataFrame(proofs).to_csv(R/'qa/independent_minimum_loss_certificates.csv',index=False)
    refined=pd.read_csv(R/'tablas/compromiso_malla41.csv');frozen_checks=[]
    for city in ['Valencia','Madrid']:
        fields=pd.read_parquet(R/f'datos/central_{city}_working_Full_scores.parquet')
        choices=pd.read_csv(R/f'tablas/central_{city}_working_Full_selections.csv',dtype={'CUSEC':str})
        for case in refined[refined.city.eq(city)].itertuples():
            f=fields[(fields['mode']==case.mode)&fields.window.eq(case.window)&fields.weights.eq(41)&fields.reachable].sort_values('CUSEC')
            pick=choices[(choices['mode']==case.mode)&choices.window.eq(case.window)&choices.method.eq('Dual1_regional')].CUSEC
            take=f.CUSEC.isin(pick);assert take.sum()==case.quota
            for col in ['local','regional']:
                u=f[col].to_numpy();v=100*f.loc[take,col].sum()/u[order(u)[:case.quota]].sum()
                assert np.isclose(v,getattr(case,'frozen21_'+col+'_capture'),atol=1e-7,rtol=0)
            frozen_checks.append(dict(city=city,mode=case.mode,window=case.window,passed=True))
    pd.DataFrame(frozen_checks).to_csv(R/'qa/independent_frozen41_checks.csv',index=False)
    result=dict(policy_cases_verified=len(rows),capacity_cases_verified=len(cap),dual_allocations_verified=256,infeasible_cases=32,exhaustive_oracles=8,independently_resolved_minima=len(tasks),frozen41_cases_verified=len(frozen_checks),status='PASS; decision layer only')
    (R/'qa/decision_audit.json').write_text(json.dumps(result,indent=2));print(result,flush=True)
if __name__=='__main__':main()
