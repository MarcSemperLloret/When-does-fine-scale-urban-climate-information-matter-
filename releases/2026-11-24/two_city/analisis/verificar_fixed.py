"""Independent audit of fixed-grid matrices and decisions; no generator imports.

Run from any working directory. --resolve independently solves all 108 cases.
Derived scores are the input boundary; this does not reconstruct meteorology.
"""
from pathlib import Path
import argparse, itertools, json
import numpy as np
import pandas as pd
from scipy.optimize import milp, Bounds, LinearConstraint
R=Path(__file__).resolve().parents[1]

def top(v,k):
    return np.array(sorted(range(len(v)),key=lambda i:(-v[i],i))[:k])

def close(a,b):
    assert np.allclose(a,b,rtol=1e-10,atol=1e-6),(a,b)

def independent_solve(A,k):
    # Minimise loss directly, with loss as first variable (generator maximises capture).
    n=A.shape[1]
    c=np.r_[1.,np.zeros(n)]
    constraints=[LinearConstraint(np.r_[0.,np.ones(n)][None,:],k,k),
                 LinearConstraint(np.column_stack([np.ones(len(A)),A]),100,np.inf)]
    res=milp(c,integrality=np.r_[0,np.ones(n)],
             bounds=Bounds(np.zeros(n+1),np.r_[100.,np.ones(n)]),
             constraints=constraints,options={'mip_rel_gap':1e-8,'time_limit':120})
    assert res.success,res.message
    ix=np.flatnonzero(res.x[1:]>.5)
    assert len(ix)==k
    close(res.fun,100-A[:,ix].sum(axis=1).min())
    return float(res.fun)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--resolve',action='store_true');args=ap.parse_args()
    rows=json.loads((R/'fixed/summary.json').read_text())
    bench=pd.read_parquet(R/'fixed/benchmarks.parquet')
    inspect=pd.read_parquet(R/'fixed/inspection_a1.parquet')
    scores=pd.read_parquet(R/'datos/policy_scores_two_cities.parquet')
    parts=pd.read_parquet(R/'datos/score_components.parquet')
    margins=json.loads((R/'fixed/margins.json').read_text())
    report=[];baseline_checks=0;recomputed=0
    assert len(rows)==108 and len(bench)==864
    for file in sorted((R/'fixed').glob('*.npz')):
        city,window,mode=file.stem.split('_',2)
        z=np.load(file,allow_pickle=False);A=z['normalised'];raw=z['scores'];ids=z['CUSEC'];k=int(z['quota']);delta=z['delta']
        assert raw.shape==A.shape==(34,len(ids))
        assert len(set(ids))==len(ids) and list(ids)==sorted(ids)
        assert np.isfinite(raw).all() and (raw>=0).all()
        assert k==int(.15*len(ids))
        close(A,100*raw/np.sort(raw,axis=1)[:,-k:].sum(axis=1)[:,None])
        for a in A:close(a[top(a,k)].sum(),100)
        choose=(scores.city.eq(city)&scores.window.eq(window)&scores['mode'].eq(mode)&scores.threshold.eq(30)&scores.phi.eq(.4))
        orig=scores[choose].set_index('CUSEC').loc[ids]
        cp=parts[(parts.city.eq(city)&parts.window.eq(window)&parts['mode'].eq(mode)&parts.threshold.eq(30)&parts.phi.eq(.4))].set_index('CUSEC').loc[ids]
        zeros=np.flatnonzero(delta==0);assert len(zeros)==2
        close(raw[zeros[0]],orig.local);close(raw[zeros[1]],orig.regional)
        fixed={'Population':top(z['population'],k),'Uniform':top(orig.uniform.to_numpy(),k),
               'Shared':top((cp.solar_failure+cp.shared_thermal_failure).to_numpy(),k),
               'Local':top(raw[zeros[0]],k),'Regional':top(raw[zeros[1]],k),
               'Two-reference pooling':top(A[zeros].sum(axis=0),k)}
        group=sorted([x for x in rows if (x['city'],x['window'],x['mode'])==(city,window,mode)],key=lambda x:x['amplitude'])
        assert [x['amplitude'] for x in group]==list(np.arange(0,2.01,.25))
        previous=-1.;first=None
        for row in group:
            amp=row['amplitude'];active=np.abs(delta)<=amp+1e-10;M=A[active];ix=np.array(row['selected_indices'])
            assert len(ix)==len(set(ix))==k and min(ix)>=0 and max(ix)<len(ids)
            assert len(M)==row['n_scenarios']==int(2+16*amp)
            capture=M[:,ix].sum(axis=1).min();loss=100-capture
            close(capture,row['minimum_capture']);close(loss,row['minimum_loss'])
            close(row['upper_bound_capture'],100-row['lower_bound_loss'])
            assert row['optimal'] and row['status']==0 and row['mip_gap']<=1e-8
            assert capture<=row['upper_bound_capture']+1e-6<=row['lp_upper_capture']+2e-6
            close(capture,row['upper_bound_capture'])
            assert loss>=previous-1e-6;previous=loss
            if first is None and row['lower_bound_loss']>1+1e-7:first=amp
            candidates=dict(fixed,**{'All-scenario pooling':top(M.mean(axis=0),k),'Maximin':ix})
            sub=bench[(bench.city.eq(city)&bench.window.eq(window)&bench['mode'].eq(mode)&bench.amplitude.eq(amp))].set_index('rule')
            assert len(sub)==8
            for rule,selection in candidates.items():
                cap=float(M[:,selection].sum(axis=1).min());close(cap,sub.loc[rule,'minimum_capture'])
                assert bool(sub.loc[rule,'passes99'])==(cap>=99-1e-7)
                assert cap<=capture+1e-6;baseline_checks+=1
            if amp==1:
                chosen=inspect[(inspect.city.eq(city)&inspect.window.eq(window)&inspect['mode'].eq(mode))].set_index('CUSEC').loc[ids]
                for label in ['local','uniform','maximin']:
                    take=candidates[label.capitalize()]
                    assert np.array_equal(chosen[label].to_numpy(),np.isin(np.arange(len(ids)),take))
            if args.resolve:close(independent_solve(M,k),loss);recomputed+=1
        margin=next(x for x in margins if (x['city'],x['window'],x['mode'])==(city,window,mode))
        assert first==margin['first_incompatible_grid_amplitude']
        close(group[4]['minimum_loss'],margin['loss_a1']);close(group[-1]['minimum_loss'],margin['loss_a2'])
        report.append(dict(city=city,window=window,mode=mode,first_incompatible=first,passed=True))
    # Small exhaustive oracle independently checks the optimisation formulation.
    rng=np.random.default_rng(20260921)
    for repeat in range(4):
        M=rng.uniform(.1,10,(5,8));M=100*M/np.sort(M,axis=1)[:,-3:].sum(axis=1)[:,None]
        exhaustive=min(100-M[:,list(ix)].sum(axis=1).min() for ix in itertools.combinations(range(8),3))
        close(independent_solve(M,3),exhaustive)
    assert sum(x['first_incompatible'] is not None for x in report)==9
    assert all(x['city']=='Madrid' and x['window']=='Afternoon' for x in report if x['first_incompatible'] is None)
    output=dict(status='PASS',matrices=len(report),optimisations=108,independent_resolves=recomputed,
                baseline_checks=baseline_checks,exhaustive_oracles=4,configurations=report,
                scope='Decision layer only; upstream weather and observation validity are outside this audit.')
    (R/'qa').mkdir(exist_ok=True);(R/'qa/independent_fixed_checks.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in output.items() if k!='configurations'},indent=2))
if __name__=='__main__':main()
