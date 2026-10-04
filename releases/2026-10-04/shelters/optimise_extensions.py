"""Exploratory facility coverage allocation; no claim of operational feasibility.

Costs proxy additional centre-hours, not staffing cost. Facilities have no known
capacity constraints. The original paper's additive section objective is NOT used.
"""
from pathlib import Path
import json,itertools
import numpy as np,pandas as pd
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import csr_matrix,eye,hstack,vstack
R=Path(__file__).resolve().parent;O=R/'resultados'
cat=json.loads((R/'catalogue_audited.json').read_text(encoding='utf-8'));d=np.load(R/'datos/distances.npz');p=d['population65']
costtable=pd.read_csv(O/'extension_costs.csv').set_index('id')
ids=[i for i in range(41) if i not in [13,14]]
cost=costtable.loc[ids,'extra_hours_8_21'].to_numpy();candidates=np.array(ids)[cost>0];cost=cost[cost>0]
announced=np.array([cat[i]['announced_extension'] for i in candidates]);B=float(cost[announced].sum());assert abs(B-73.25)<1e-8

def opened(i,h):return any(a<=h<b for a,b in cat[i]['ordinary_intervals'])
def matrix(speed,minutes,origin='centroid'):
    reach=d[origin+'_m']<=speed*60*minutes+1e-9
    blocks=[];weights=[];base_total=0
    for h in range(16,21):
        before=np.array([opened(i,h) for i in ids]);baseline=reach[:,np.array(ids)[before]].any(axis=1)
        base_total+=p[baseline].sum()
        extended=np.array([h>=cat[i]['ordinary_intervals'][-1][0] and h<max(21,cat[i]['ordinary_intervals'][-1][1]) for i in candidates])
        cover=reach[:,candidates]&extended[None,:]&~baseline[:,None]
        keep=cover.any(axis=1);blocks.append(cover[keep]);weights.append(p[keep])
    A=np.concatenate(blocks);w=np.concatenate(weights)
    # Merge identical demand coverage patterns; exact weighted reduction.
    unique,inv=np.unique(A,axis=0,return_inverse=True);weight=np.bincount(inv,weights=w)
    return unique.astype(float),weight,float(base_total)

def gain(A,w,take):return float(w[(A[:,take]>0).any(axis=1)].sum()) if len(take) else 0.

def solve(A,w,budget):
    n=len(cost);m=len(w)
    obj=np.r_[np.zeros(n),-w/w.sum()]
    coverage=hstack([-csr_matrix(A),eye(m)],format='csr')
    constraints=[LinearConstraint(coverage,-np.inf,0),LinearConstraint(csr_matrix(np.r_[cost,np.zeros(m)][None,:]),-np.inf,budget)]
    res=milp(obj,integrality=np.r_[np.ones(n),np.zeros(m)],bounds=Bounds(np.zeros(n+m),np.ones(n+m)),constraints=constraints,options={'time_limit':120,'mip_rel_gap':1e-8})
    assert res.success,res.message
    take=np.flatnonzero(res.x[:n]>.5);val=gain(A,w,take)
    assert cost[take].sum()<=budget+1e-7 and abs(val+res.fun*w.sum())<1e-5
    return take,dict(gain=val,upper_gain=float(-res.mip_dual_bound*w.sum()),mip_gap=float(res.mip_gap),cost=float(cost[take].sum()),selected_ids=candidates[take].tolist())

def greedy(A,w,budget,adaptive=True):
    take=[];remaining=set(range(len(cost)));spent=0;current=0
    independent=np.array([gain(A,w,[i]) for i in range(len(cost))])
    while remaining:
        feasible=[i for i in remaining if cost[i]+spent<=budget+1e-9]
        if not feasible:break
        benefits={i:(gain(A,w,take+[i])-current if adaptive else independent[i])/cost[i] for i in feasible}
        best=min(feasible,key=lambda i:(-benefits[i],int(candidates[i])))
        if benefits[best]<=1e-9:break
        take.append(best);remaining.remove(best);spent+=cost[best];current=gain(A,w,take)
    return np.array(take,dtype=int)

records=[];cache={}
for speed in [.6,.9,1.2]:
 for minutes in [10,15,20]:
    A,w,base=matrix(speed,minutes);key=f'{speed}_{minutes}';cache[key]=(A,w,base)
    np.savez_compressed(O/f'optimisation_matrix_{key}.npz',coverage=A,weights=w,candidate_ids=candidates,cost=cost,baseline_person_hours=base)
    for fraction in [.25,.5,1.]:
        take,cert=solve(A,w,B*fraction)
        g=greedy(A,w,B*fraction);s=greedy(A,w,B*fraction,False)
        records.append(dict(speed=speed,minutes=minutes,budget_fraction=fraction,budget=B*fraction,baseline_person_hours=base,announced_gain=gain(A,w,np.flatnonzero(announced)),greedy_gain=gain(A,w,g),greedy_ids=candidates[g].tolist(),static_ratio_gain=gain(A,w,s),static_ratio_ids=candidates[s].tolist(),**cert))
        print(key,fraction,round(cert['gain']),round(gain(A,w,g)),round(gain(A,w,np.flatnonzero(announced))),flush=True)
(O/'optimisation_results.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
# Cross-evaluate the central exact selection against nine movement assumptions.
central=next(x for x in records if x['speed']==.9 and x['minutes']==15 and x['budget_fraction']==1.)
take=[list(candidates).index(i) for i in central['selected_ids']]
cross=[]
for row in records:
 if row['budget_fraction']==1:
    A,w,base=cache[f"{row['speed']}_{row['minutes']}"]
    val=gain(A,w,take)
    cross.append(dict(speed=row['speed'],minutes=row['minutes'],central_selection_gain=val,scenario_optimum=row['gain'],capture_percent=100*val/row['gain'],announced_gain=row['announced_gain'],greedy_capture_percent=100*row['greedy_gain']/row['gain']))
(O/'cross_scenario_transfer.json').write_text(json.dumps(cross,indent=2),encoding='utf-8')
print('CENTRAL',json.dumps(central,indent=2));print('CROSS',json.dumps(cross,indent=2))
