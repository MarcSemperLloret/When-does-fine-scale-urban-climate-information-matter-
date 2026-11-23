"""Minimum extra centre-hours to retain fixed-budget benchmark gains.
The denominator remains each scenario's optimum at 73.25 centre-hours.
This is a model-based resource threshold, not a staffing or monetary estimate.
"""
from pathlib import Path
import json
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix,vstack
R=Path(__file__).resolve().parent;O=R/'resultados'
records=json.loads((O/'optimisation_results.json').read_text())
cases=[(.6,10),(.6,15),(.6,20),(.9,15),(.9,20),(1.2,20)]
data=[np.load(O/f'optimisation_matrix_{s}_{m}.npz') for s,m in cases]
cost=data[0]['cost'];ids=data[0]['candidate_ids'];n=len(cost)
refs=[next(r['gain'] for r in records if r['speed']==s and r['minutes']==m and r['budget_fraction']==1) for s,m in cases]
starts=np.cumsum([n]+[len(d['weights']) for d in data]);nv=int(starts[-1])
out=[]
for target in [.95,.99]:
    blocks=[];lb=[];ub=[]
    for k,(d,ref) in enumerate(zip(data,refs)):
        A=d['coverage'];w=d['weights'];m=len(w);ar,ac=np.nonzero(A)
        blocks.append(coo_matrix((np.r_[-A[ar,ac],np.ones(m)],(np.r_[ar,np.arange(m)],np.r_[ac,starts[k]+np.arange(m)])),shape=(m,nv)))
        lb.append(np.full(m,-np.inf));ub.append(np.zeros(m))
        blocks.append(coo_matrix((w/ref,(np.zeros(m),starts[k]+np.arange(m))),shape=(1,nv)))
        lb.append([target]);ub.append([np.inf])
    res=milp(np.r_[cost,np.zeros(nv-n)],integrality=np.r_[np.ones(n),np.zeros(nv-n)],bounds=Bounds(0,1),constraints=LinearConstraint(vstack(blocks,format='csr'),np.concatenate(lb),np.concatenate(ub)),options={'mip_rel_gap':1e-9,'time_limit':60})
    assert res.success,res.message
    take=np.flatnonzero(res.x[:n]>.5)
    scores=[float(100*d['weights'][(d['coverage'][:,take]>0).any(axis=1)].sum()/ref) for d,ref in zip(data,refs)]
    assert min(scores)>=100*target-1e-6
    row=dict(target_percent=100*target,minimum_centre_hours=float(cost[take].sum()),lower_bound=float(res.mip_dual_bound),gap=float(res.mip_gap),reference_budget=73.25,selected_ids=ids[take].tolist(),captures=scores)
    out.append(row);print(row,flush=True)
(O/'budget_thresholds.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
