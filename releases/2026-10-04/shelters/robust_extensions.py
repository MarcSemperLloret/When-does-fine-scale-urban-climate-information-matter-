"""A common budgeted extension programme across distinct distance thresholds."""
from pathlib import Path
import json
import numpy as np
from scipy.sparse import csr_matrix,coo_matrix,vstack
from scipy.optimize import milp,Bounds,LinearConstraint
R=Path(__file__).resolve().parent;O=R/'resultados'
results=json.loads((O/'optimisation_results.json').read_text())
# Nine speed/time pairs induce only six unique walking-distance thresholds.
cases=[(.6,10),(.6,15),(.6,20),(.9,15),(.9,20),(1.2,20)]
data=[np.load(O/f'optimisation_matrix_{s}_{m}.npz') for s,m in cases]
cost=data[0]['cost'];ids=data[0]['candidate_ids'];n=len(cost)
allout=[]
for fraction in [.25,.5,1.]:
    refs=[next(x for x in results if x['speed']==s and x['minutes']==m and x['budget_fraction']==fraction) for s,m in cases]
    starts=np.cumsum([n]+[len(d['weights']) for d in data]);last=int(starts[-1]);nv=last+1
    blocks=[];lb=[];ub=[]
    rr=[0]*n;cc=list(range(n));val=cost.tolist()
    blocks.append(coo_matrix((val,(rr,cc)),shape=(1,nv)));lb.append(np.array([-np.inf]));ub.append(np.array([73.25*fraction]))
    for i,d in enumerate(data):
        A=d['coverage'];w=d['weights'];m=len(w);ar,ac=np.nonzero(A)
        block=coo_matrix((np.r_[-A[ar,ac],np.ones(m)],(np.r_[ar,np.arange(m)],np.r_[ac,starts[i]+np.arange(m)])),shape=(m,nv))
        blocks.append(block);lb.append(np.full(m,-np.inf));ub.append(np.zeros(m))
        block=coo_matrix((np.r_[100*w/refs[i]['gain'],-1],(np.zeros(m+1),np.r_[starts[i]+np.arange(m),last])),shape=(1,nv))
        blocks.append(block);lb.append(np.array([0.]));ub.append(np.array([np.inf]))
    objective=np.zeros(nv);objective[-1]=-1
    result=milp(objective,integrality=np.r_[np.ones(n),np.zeros(nv-n)],bounds=Bounds(np.zeros(nv),np.r_[np.ones(nv-1),100]),constraints=LinearConstraint(vstack(blocks,format='csr'),np.concatenate(lb),np.concatenate(ub)),options={'mip_rel_gap':1e-8,'time_limit':120})
    assert result.success,result.message
    selected=np.flatnonzero(result.x[:n]>.5);assert cost[selected].sum()<=73.25*fraction+1e-8
    caps=[]
    for (s,m),d,ref in zip(cases,data,refs):
        gain=float(d['weights'][(d['coverage'][:,selected]>0).any(axis=1)].sum());caps.append(dict(speed=s,minutes=m,distance_m=s*m*60,gain=gain,capture=100*gain/ref['gain']))
    worst=min(x['capture'] for x in caps);assert abs(worst+result.fun)<1e-5
    allout.append(dict(budget_fraction=fraction,budget=73.25*fraction,cost=float(cost[selected].sum()),selected_ids=ids[selected].tolist(),worst_capture=worst,upper_capture=float(-result.mip_dual_bound),mip_gap=float(result.mip_gap),scenarios=caps))
(O/'robust_results.json').write_text(json.dumps(allout,indent=2),encoding='utf-8')
print(json.dumps(allout,indent=2))
