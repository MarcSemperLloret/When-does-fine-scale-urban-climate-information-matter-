from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from scipy.optimize import linprog
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'observation_stress'
r=pd.read_json(OUT/'robust_summary.json')
s=pd.read_json(OUT/'symmetric_summary.json')
nested=pd.read_json(OUT/'clock_subset_summary.json')
ben=pd.read_parquet(OUT/'robust_benchmarks.parquet')
sel=pd.read_parquet(OUT/'inspection_shortlists.parquet')
checks=[]
def check(name,truth):
    if not bool(truth):raise AssertionError(name)
    checks.append(name)
lp=[]
for _,z in r.iterrows():
    w,mode=z.window,z['mode'];key=w+'_'+mode
    data=np.load(OUT/f'scenarios_{key}.npz');A=data['normalised'];scores=data['scores'];ids=data['CUSEC'];k=int(data['quota']);N=A.shape[1]
    ss=sel.query('window==@w and mode==@mode').set_index('CUSEC').loc[ids]
    check(key+' normalisation',np.allclose(A,100*scores/np.sort(scores,axis=1)[:,-k:].sum(axis=1)[:,None]))
    for label,bs in ben.query('window==@w and mode==@mode').set_index('rule').iterrows():
        take=np.flatnonzero(ss[label].to_numpy());capture=A[:,take].sum(axis=1).min()
        check(key+' '+label+' quota',len(take)==k)
        check(key+' '+label+' capture',abs(capture-bs.minimum_capture)<1e-8)
    check(key+' optimal bound',abs(z.minimum_capture-z.upper_bound_capture)<1e-7 and z.optimal)
    check(key+' excludes99',z.upper_bound_capture<99)
    js=s.query('window==@w and mode==@mode').iloc[0]
    sub=nested.query('window==@w and mode==@mode')
    check(key+' scenario nesting',js.minimum_loss>=z.minimum_loss-1e-7 and (sub.minimum_loss<=js.minimum_loss+1e-7).all())
    jj=np.load(OUT/f'symmetric_{key}.npz')
    check(key+' symmetric selected quota',len(jj['selected'])==k)
    check(key+' symmetric selected captures',abs(jj['normalised'][:,jj['selected']].sum(axis=1).min()-js.minimum_capture)<1e-8)
    # Independent continuous relaxation: allowing fractional slots can only increase capture.
    sol=linprog(np.r_[np.zeros(N),-1],A_ub=np.column_stack([-A,np.ones(len(A))]),b_ub=np.zeros(len(A)),A_eq=np.r_[np.ones(N),0][None,:],b_eq=[k],bounds=[(0,1)]*N+[(0,100)],method='highs')
    check(key+' LP success',sol.success)
    check(key+' LP upper bound',-sol.fun>=z.minimum_capture-1e-7)
    check(key+' LP also excludes99',-sol.fun<99)
    lp.append(dict(window=w,mode=mode,relaxed_upper_capture=float(-sol.fun),minimum_loss_lower_bound=float(100+sol.fun)))

check('all 18 clock solutions optimal',nested.optimal.all() and (nested.mip_gap==0).all())
check('all 9 morning clock cases incompatible',(nested.query("window=='Morning'").minimum_loss>1).all())
check('afternoon compatibility count',int((nested.query("window=='Afternoon'").minimum_loss<=1).sum())==4)


(ROOT/'qa/independent_observation_stress_checks.json').write_text(json.dumps(dict(status='PASS',passed=len(checks),checks=checks,lp_certificates=lp),indent=2),encoding='utf-8')
print('Complementary observation-stress checks passed:',len(checks))
