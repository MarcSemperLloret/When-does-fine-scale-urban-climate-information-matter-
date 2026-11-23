from pathlib import Path
import json
import numpy as np,pandas as pd
R=Path(__file__).resolve().parent;O=R/'resultados';O.mkdir(exist_ok=True)
cat=json.loads((R/'catalogue_audited.json').read_text(encoding='utf-8'));d=np.load(R/'datos/distances.npz');pop=d['population65'];hours=np.arange(16,21)
def intervals(site,event=False,continuous=False):
    ints=[list(x) for x in site['ordinary_intervals']]
    if event and site['announced_extension']:
        if continuous:ints.append([16,21])
        else:ints[-1][1]=max(ints[-1][1],21)
    return ints
def availability(items,time,event=False,continuous=False,stay=0):
    return np.array([any(a<=time and time<b and time+stay<=b for a,b in intervals(x,event,continuous)) for x in items])
def additional_cost(site,start=8,end=21):
    grid=np.arange(start,end,.25)
    # Hypothetical extension for every eligible site, regardless of announced selection.
    hypothetical=dict(site,announced_extension=True)
    return .25*sum(availability([hypothetical],t,True)[0] and not availability([site],t)[0] for t in grid)
catalogues={'reconstructed39':[i for i in range(41) if i not in [13,14]],
 'reconstructed38_no_science':[i for i in range(41) if i not in [13,14,15]],
 'reconstructed35_no_older_centres':[i for i in range(41) if i not in [13,14,31,32,33,34]],
 'named23':[i for i,x in enumerate(cat) if x['announced_extension']],
 'current41':list(range(41))}
records=[];detail=[]
for origin in ['centroid','interior','network']:
 for speed in [.6,.9,1.2]:
  for minutes in [10,15,20]:
   reach=d[origin+'_m']<=speed*60*minutes+1e-9
   for cname,ids in catalogues.items():
    sites=[cat[i] for i in ids];C=reach[:,ids]
    for h in hours:
     base=availability(sites,h);event=availability(sites,h,True);continuous=availability(sites,h,True,True)
     covered=lambda active:C[:,active].any(axis=1) if active.any() else np.zeros(len(pop),bool)
     a,b,c,geo=[covered(v) for v in [base,event,continuous,np.ones(len(ids),bool)]]
     assert np.all(~a|b) and np.all(~b|c) and np.all(~c|geo)
     records.append(dict(origin=origin,speed=speed,minutes=minutes,catalogue=cname,hour=int(h),ordinary_centres=int(base.sum()),event_centres=int(event.sum()),ordinary_older=float(pop[a].sum()),event_older=float(pop[b].sum()),additional_older=float(pop[b&~a].sum()),continuous_event_older=float(pop[c].sum()),geographic_older=float(pop[geo].sum()),ordinary_sections=int(a.sum()),event_sections=int(b.sum()),total_older=float(pop.sum())))
     if origin=='centroid' and speed==.9 and minutes==15 and cname=='reconstructed39':
      for i,cusec in enumerate(d['CUSEC']):detail.append(dict(CUSEC=cusec,hour=int(h),population65=float(pop[i]),district=str(d['district'][i]),ordinary=bool(a[i]),event=bool(b[i]),continuous=bool(c[i]),geographic=bool(geo[i])))
out=pd.DataFrame(records);out.to_csv(O/'coverage_sensitivity.csv',index=False)
pd.DataFrame(detail).to_parquet(O/'central_section_membership.parquet',index=False)
main=out[(out.origin.eq('centroid'))&(out.speed.eq(.9))&(out.minutes.eq(15))&(out.catalogue.eq('reconstructed39'))]
main.to_csv(O/'central_hourly_coverage.csv',index=False)
costs=[dict(id=s['id'],name=s['name'],announced=s['announced_extension'],extra_hours_8_21=additional_cost(s),extra_hours_16_21=additional_cost(s,16,21)) for s in cat]
pd.DataFrame(costs).to_csv(O/'extension_costs.csv',index=False)
# Integrate 30-minute minimum remaining opening duration as a separate scenario.
stay=[];ids=catalogues['reconstructed39'];sites=[cat[i] for i in ids];C=d['centroid_m'][:,ids]<=810+1e-9
for minimum_stay in [0,.5]:
 for event in [False,True]:
  total=0
  # Midpoints integrate piecewise-constant eligibility exactly here; using a
  # left endpoint would overcount the interval starting exactly at close-stay.
  for t in np.arange(16,21,.25)+.125:
   active=availability(sites,t,event,stay=minimum_stay);sel=C[:,active].any(axis=1) if active.any() else np.zeros(len(pop),bool)
   total+=.25*pop[sel].sum()
  stay.append(dict(minimum_stay_hours=minimum_stay,event=event,potential_person_hours=float(total)))
report=dict(interpretation='Conditional reconstruction using current published July-Wednesday ordinary hours and a dated announcement; not observed execution or health benefit.',primary_hourly=main.to_dict(orient='records'),ordinary_person_hours=float(main.ordinary_older.sum()),event_person_hours=float(main.event_older.sum()),incremental_person_hours=float(main.additional_older.sum()),announced_centres=23,announced_positive_cost_centres=sum(s['announced'] and s['extra_hours_8_21']>0 for s in costs),announced_extra_hours_8_21=sum(s['extra_hours_8_21'] for s in costs if s['announced']),announced_extra_hours_16_21=sum(s['extra_hours_16_21'] for s in costs if s['announced']),minimum_stay=stay)
(O/'coverage_summary.json').write_text(json.dumps(report,indent=2,default=lambda x:x.item()),encoding='utf-8')
print(main[['hour','ordinary_centres','event_centres','ordinary_older','event_older','additional_older','geographic_older']].to_string(index=False))
print(json.dumps({k:v for k,v in report.items() if k!='primary_hourly'},indent=2,default=lambda x:x.item()))
if __name__=='__main__':pass
