"""Independent quarter-hour reconstruction and uncompressed coverage MILPs.

No imports from the analysis scripts. Recomputes decisions from distance inputs,
checks archived totals, and tests alternative provenance/access assumptions.
The LP coverage variables denote fractions only algebraically: positive weights
and binary facility choices make optimal union coverage exact.
"""
from pathlib import Path
import json, copy, itertools, platform, importlib.metadata
import numpy as np
import pandas as pd
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import csr_matrix, eye, hstack, vstack, coo_matrix
R=Path(__file__).resolve().parent; O=R/'resultados'
cat=json.loads((R/'catalogue_audited.json').read_text(encoding='utf-8'))
d=np.load(R/'datos/distances.npz'); p=d['population65']; clock=np.arange(16,21,.25)+.125
checks=[]

def active(site,t,extended=False,stay=0,continuous=False):
    schedule=copy.deepcopy(site['ordinary_intervals'])
    if extended:
        schedule[-1][1]=max(21,schedule[-1][1])
        if continuous: schedule.append([16,21])
    return any(a<=t and t+stay<=b and t<b for a,b in schedule)

catalogues={'reconstructed39':[i for i in range(41) if i not in [13,14]],
 'reconstructed38_no_science':[i for i in range(41) if i not in [13,14,15]],
 'reconstructed35_no_older_centres':[i for i in range(41) if i not in [13,14,31,32,33,34]],
 'named23':[i for i,s in enumerate(cat) if s['announced_extension']], 'current41':list(range(41))}
# Independently check each archived hourly coverage row by explicit set union.
table=pd.read_csv(O/'coverage_sensitivity.csv'); largest=0.
for r in table.itertuples():
    ids=catalogues[r.catalogue]; reachable=d[r.origin+'_m']<=r.speed*r.minutes*60+1e-9
    outcomes=[]
    for policy in ['ordinary','event','continuous','geographic']:
        selected=set()
        for j in ids:
            ext=policy in ['event','continuous'] and cat[j]['announced_extension']
            if policy=='geographic' or active(cat[j],r.hour,ext,continuous=policy=='continuous'):
                selected.update(np.flatnonzero(reachable[:,j]).tolist())
        outcomes.append(float(sum(p[i] for i in sorted(selected))))
    expected=[r.ordinary_older,r.event_older,r.continuous_event_older,r.geographic_older]
    largest=max(largest,max(abs(a-b) for a,b in zip(outcomes,expected)))
assert largest<1e-6
checks.append(dict(check='All hourly unions, independent explicit sets',rows=len(table),maximum_absolute_error=largest))
assert d['centroid_m'].shape==(591,41) and np.isfinite(d['centroid_m']).all()
assert len(set(d['CUSEC']))==591 and (p>=0).all()
checks.append(dict(check='Distance alignment, uniqueness and finite values',passed=True))

def build(items,ids,radius,origin='centroid',stay=0,eligible=None):
    reach=d[origin+'_m']<=radius+1e-9
    cost={j:.25*sum(active(items[j],t,True) and not active(items[j],t) for t in np.arange(8,21,.25)+.125) for j in ids}
    candidates=[j for j in ids if cost[j]>0 and (eligible is None or j in eligible)]
    budget=sum(cost[j] for j in ids if items[j]['announced_extension'])
    A=[]; w=[]; baseline=0; event=0
    for t in clock:
        before=np.array([j for j in ids if active(items[j],t,stay=stay)],int)
        after=np.array([j for j in ids if active(items[j],t,items[j]['announced_extension'],stay)],int)
        b=reach[:,before].any(axis=1); e=reach[:,after].any(axis=1)
        baseline+=.25*p[b].sum();event+=.25*p[e].sum()
        # Keep original person-time demands, deliberately without pattern merging.
        tmp=np.column_stack([reach[:,j]&~b&active(items[j],t,True,stay) for j in candidates])
        take=tmp.any(axis=1);A.append(tmp[take]);w.append(.25*p[take])
    return dict(A=np.concatenate(A).astype(float),w=np.concatenate(w),ids=candidates,
                cost=np.array([cost[j] for j in candidates]),budget=budget,baseline=baseline,event=event)

def gain(case,selected):
    columns=[case['ids'].index(j) for j in selected if j in case['ids']]
    return float(case['w'][case['A'][:,columns].any(axis=1)].sum()) if columns else 0.

def optimum(case):
    A=case['A'];w=case['w'];cost=case['cost'];n=len(cost);m=len(w)
    res=milp(np.r_[np.zeros(n),-w/w.sum()],integrality=np.r_[np.ones(n),np.zeros(m)],
        bounds=Bounds(0,1),constraints=[LinearConstraint(hstack([-csr_matrix(A),eye(m)]),-np.inf,0),
        LinearConstraint(csr_matrix(np.r_[cost,np.zeros(m)][None,:]),-np.inf,case['budget'])],options={'mip_rel_gap':1e-8,'time_limit':60})
    assert res.success,res.message
    selected=[case['ids'][i] for i in np.flatnonzero(res.x[:n]>.5)]
    return dict(gain=gain(case,selected),selected_ids=selected,upper=float(-res.mip_dual_bound*w.sum()),gap=float(res.mip_gap))

def robust(cases,opts):
    n=len(cases[0]['ids']); starts=np.cumsum([n]+[len(c['w']) for c in cases]);z=int(starts[-1]);nv=z+1
    rows=[];lb=[];ub=[]
    rows.append(csr_matrix(np.r_[cases[0]['cost'],np.zeros(nv-n)][None,:]));lb.append([-np.inf]);ub.append([cases[0]['budget']])
    for k,(c,opt) in enumerate(zip(cases,opts)):
        assert c['ids']==cases[0]['ids']
        ar,ac=np.nonzero(c['A']);m=len(c['w'])
        rows.append(coo_matrix((np.r_[-np.ones(len(ar)),np.ones(m)],(np.r_[ar,np.arange(m)],np.r_[ac,starts[k]+np.arange(m)])),shape=(m,nv)))
        lb.append(np.full(m,-np.inf));ub.append(np.zeros(m))
        rows.append(coo_matrix((np.r_[100*c['w']/opt['gain'],-1],(np.zeros(m+1),np.r_[starts[k]+np.arange(m),z])),shape=(1,nv)))
        lb.append([0]);ub.append([np.inf])
    objective=np.zeros(nv);objective[z]=-1
    res=milp(objective,integrality=np.r_[np.ones(n),np.zeros(nv-n)],bounds=Bounds(0,np.r_[np.ones(nv-1),100]),constraints=LinearConstraint(vstack(rows,format='csr'),np.concatenate(lb),np.concatenate(ub)),options={'mip_rel_gap':1e-8,'time_limit':60})
    assert res.success,res.message
    selected=[cases[0]['ids'][i] for i in np.flatnonzero(res.x[:n]>.5)]
    scores=[100*gain(c,selected)/o['gain'] for c,o in zip(cases,opts)]
    assert abs(min(scores)+res.fun)<1e-5
    return dict(selected_ids=selected,worst_capture=min(scores),captures=scores,upper_capture=float(-res.mip_dual_bound),gap=float(res.mip_gap))

primary_ids=catalogues['reconstructed39']; radii=[360,540,720,810,1080,1440]
base=build(cat,primary_ids,810)
summary=json.loads((O/'coverage_summary.json').read_text())
assert abs(base['event']-summary['event_person_hours'])<1e-6
assert abs(base['baseline']-summary['ordinary_person_hours'])<1e-6
for rec in summary['minimum_stay']:
    c=build(cat,primary_ids,810,stay=rec['minimum_stay_hours'])
    val=c['event'] if rec['event'] else c['baseline']
    assert abs(val-rec['potential_person_hours'])<1e-6
checks.append(dict(check='Quarter-hour integration including 30-minute dwell',passed=True))

# Small exhaustive oracle, using real non-additive coverage patterns and costs.
small=copy.deepcopy(base);small['A']=small['A'][:,:8];small['ids']=small['ids'][:8];small['cost']=small['cost'][:8];small['budget']=16.
brute=0.
for bits in itertools.product([0,1],repeat=8):
    mask=np.array(bits,bool)
    if small['cost'][mask].sum()<=small['budget']:
        brute=max(brute,gain(small,[small['ids'][i] for i in np.flatnonzero(mask)]))
oracle=optimum(small);assert abs(oracle['gain']-brute)<1e-6
checks.append(dict(check='Real-data exhaustive 256-subset oracle',brute_force=brute,milp=oracle['gain']))

# Independently recompute every archived selected policy's objective from demands.
archived=json.loads((O/'optimisation_results.json').read_text())
for row in archived:
    c=build(cat,primary_ids,row['speed']*row['minutes']*60)
    for field,value in [('selected_ids','gain'),('greedy_ids','greedy_gain'),('static_ratio_ids','static_ratio_gain')]:
        assert abs(gain(c,row[field])-row[value])<1e-5
        spend=sum(c['cost'][c['ids'].index(j)] for j in row[field]);assert spend<=row['budget']+1e-8
checks.append(dict(check='All archived objective values and budgets from raw demands',policies=3*len(archived)))

variants=[('primary',cat,primary_ids,'centroid',0,None)]
alternative=copy.deepcopy(cat)
for j,ints in {19:[[9.5,14],[16.5,21]],20:[[11,14],[17,21.5]],22:[[9.5,14],[16,20]]}.items():
    alternative[j]['ordinary_intervals']=ints
variants += [('alternative_culture_fiches',alternative,primary_ids,'centroid',0,None),
 ('interior_origins',cat,primary_ids,'interior',0,None),
 ('minimum_stay_30min',cat,primary_ids,'centroid',.5,None),
 ('without_older_centres',cat,catalogues['reconstructed35_no_older_centres'],'centroid',0,None),
 ('current41',cat,catalogues['current41'],'centroid',0,None),
 ('announced_candidates_only',cat,primary_ids,'centroid',0,{i for i,s in enumerate(cat) if s['announced_extension']})]
out=[]
for label,items,ids,origin,stay,eligible in variants:
    cases=[build(items,ids,r,origin,stay,eligible) for r in radii]
    opts=[optimum(c) for c in cases];rob=robust(cases,opts)
    fixed=[100*gain(c,opts[3]['selected_ids'])/o['gain'] for c,o in zip(cases,opts)]
    record=dict(variant=label,budget=cases[0]['budget'],origin=origin,minimum_stay=stay,
        ordinary_person_hours=cases[3]['baseline'],announced_person_hours=cases[3]['event'],
        announced_gain=cases[3]['event']-cases[3]['baseline'],radii=radii,scenario_optima=opts,
        frozen_central_captures=fixed,frozen_central_worst=min(fixed),robust=rob)
    out.append(record);print(label,'budget',record['budget'],'gain',round(record['announced_gain']),
        'fixed',round(min(fixed),4),'robust',round(rob['worst_capture'],4),flush=True)
primary=out[0];original=json.loads((O/'robust_results.json').read_text())[-1]
assert abs(primary['robust']['worst_capture']-original['worst_capture'])<1e-5
checks.append(dict(check='Uncompressed quarter-hour primary MILP optimality',worst_capture=primary['robust']['worst_capture'],gap=primary['robust']['gap']))
for label in ['greedy_ids','static_ratio_ids']:
    ref=next(x for x in archived if x['speed']==.9 and x['minutes']==15 and x['budget_fraction']==1)
    cases=[build(cat,primary_ids,r) for r in radii]
    primary[label+'_frozen_capture']=[100*gain(c,ref[label])/o['gain'] for c,o in zip(cases,primary['scenario_optima'])]
(O/'stress_tests.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
environment={'python':platform.python_version(),'platform':platform.platform(),
    'packages':{name:importlib.metadata.version(name) for name in ['numpy','pandas','scipy','pyarrow','geopandas','shapely','pyogrio','matplotlib','requests','beautifulsoup4']}}
(O/'verification.json').write_text(json.dumps(dict(passed=True,checks=checks,environment=environment),indent=2),encoding='utf-8')
print('Independent verification PASS',len(checks),flush=True)
