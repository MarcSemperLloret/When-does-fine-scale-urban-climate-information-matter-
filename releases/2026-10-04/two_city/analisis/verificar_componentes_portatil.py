"""Independent decision-layer audit; does not import the generating analysis.

The hourly partition is checked upstream. Here derived nonnegative components,
canonical scores, rankings and territorial comparisons are checked independently.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parents[1]
KEY=['city','mode','window','threshold','phi']
PART=['solar_failure','shared_thermal_failure','local_only_failure','regional_only_failure','joint_pass']
def equal(a,b):
    assert np.allclose(a,b,rtol=1e-10,atol=1e-8),(a,b)
def order(v,k):return np.array(sorted(range(len(v)),key=lambda i:(-v[i],i))[:k])
def main():
    scores=pd.read_parquet(R/'datos/policy_scores_two_cities.parquet')
    parts=pd.read_parquet(R/'datos/score_components.parquet')
    sm=pd.read_csv(R/'tablas/mechanism_summary.csv').set_index(KEY)
    bm=pd.read_csv(R/'tablas/practical_benchmarks.csv').set_index(KEY+['baseline'])
    policy=pd.read_csv(R/'tablas/policy_sensitivity_two_cities.csv').set_index(KEY)
    groups={k:f.sort_values('CUSEC') for k,f in parts.groupby(KEY)}
    counts={};audit=[];gains=[];exceptions=[];pool_ok=0;sectionrows=0
    for key,frame in scores.groupby(KEY):
        frame=frame.sort_values('CUSEC');c=groups[key]
        sec=pd.read_csv(R/f'datos/secciones_{key[0]}.csv',dtype={'CUSEC':str}).sort_values('CUSEC')
        assert list(frame.CUSEC)==list(c.CUSEC)==list(sec.CUSEC)
        assert np.array_equal(frame.reachable.to_numpy(bool),c.reachable.to_numpy(bool))
        P=sec.pob_65.to_numpy();allc=c[PART].to_numpy()
        assert np.isfinite(allc).all() and (allc>=-1e-10).all()
        equal(allc.sum(axis=1),P)
        equal(allc[:,:3].sum(axis=1),frame.local)
        equal(allc[:,[0,1,3]].sum(axis=1),frame.regional)
        reach=c.reachable.to_numpy(bool);p=P[reach]
        g=sec['CDIS' if key[0]=='Madrid' else 'distrito'].to_numpy()[reach]
        u=frame.local.to_numpy()[reach];v=frame.regional.to_numpy()[reach]
        cc=allc[reach];k=int(len(u)*.15);a=order(u,k);b=order(v,k)
        opt=[u[a].sum(),v[b].sum()]
        strategies={'Population':p,'Uniform':frame.uniform.to_numpy()[reach],
                    'Shared':cc[:,0]+cc[:,1],'Pooled':u/opt[0]+v/opt[1],
                    'Local':u,'Regional':v}
        feasible={};captures={};tvall={}
        for name,vec in strategies.items():
            take=order(vec,k);cap=[100*u[take].sum()/opt[0],100*v[take].sum()/opt[1]]
            labels=sorted(set(g));target=np.array([p[g==z].sum()/p.sum() for z in labels])
            observed=np.array([np.count_nonzero(g[take]==z)/k for z in labels])
            tv=.5*np.abs(observed-target).sum()
            stored=bm.loc[key+(name,)]
            equal(cap,[stored.local_capture,stored.regional_capture]);equal(tv,stored.district_TV)
            feasible[name]=min(cap)>=99-1e-7;captures[name]=min(cap);tvall[name]=tv
            assert bool(stored.dual_feasible)==feasible[name]
        compatible=policy.loc[key].balance_status=='optimal'
        state=('Population sufficient' if feasible['Population'] else 'Uniform sufficient' if feasible['Uniform']
               else 'Other common selection' if compatible else 'Incompatible')
        stored=sm.loc[key];assert state==stored.stage;counts[state]=counts.get(state,0)+1
        pool_ok+=feasible['Pooled'];assert compatible or not any(feasible.values())
        passing=[tvall[n] for n in strategies if feasible[n]]
        if passing:
            gain=min(passing)-policy.loc[key].district_TV
            equal(gain,stored.dual_TV_gain_over_baseline);assert gain>1e-8;gains.append(gain)
        elif compatible:exceptions.append([v.item() if isinstance(v,np.generic) else v for v in key])
        for j,name in enumerate(PART):
            equal(cc[a,j].sum()/opt[0],stored[name+'_local_top_score_share'])
            equal(cc[:,j].sum()/p.sum(),stored[name+'_population_share'])
        signed=100*(cc[a,:3].sum(axis=0)-cc[b,:3].sum(axis=0))/opt[0]
        equal(signed,[stored[n+'_exchange_loss_percent'] for n in PART[:3]])
        equal(signed.sum(),policy.loc[key].loss_percent)
        sectionrows+=len(c);audit.append(dict(zip(KEY,key),partition=True,benchmarks=True,exchange=True,stage=state))
    assert counts=={'Population sufficient':50,'Uniform sufficient':162,'Other common selection':44,'Incompatible':32}
    assert pool_ok==253 and len(exceptions)==3 and len(gains)==253
    (R/'qa').mkdir(exist_ok=True)
    pd.DataFrame(audit).to_csv(R/'qa/independent_mechanism_checks.csv',index=False)
    report=dict(status='PASS',cases=len(audit),section_case_rows=sectionrows,baseline_checks=len(audit)*6,
                stages=counts,pooled_feasible=int(pool_ok),feasible_without_passing_fixed_baseline=exceptions,
                TV_gain_min=min(gains),TV_gain_max=max(gains),
                scope='Derived partition identities and decision layer; not independent physical validation or hourly regeneration.')
    (R/'qa/mechanism_audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
