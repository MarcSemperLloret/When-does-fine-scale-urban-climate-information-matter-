from pathlib import Path
import json,warnings
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parent
MODELS=['IDW','Uniform','Nearest','ERA5_corrected']
CLOCKS={'as_local_CEST':0,'as_fixed_CET':1,'as_UTC':2}
SEED=20260921

def metrics(obs,pred):
    err=pred-obs;a=obs>=30;b=pred>=30
    tp=int((a&b).sum());fn=int((a&~b).sum());fp=int((~a&b).sum());tn=int((~a&~b).sum())
    return dict(n=len(err),bias=float(err.mean()),mae=float(np.abs(err).mean()),rmse=float(np.sqrt((err**2).mean())),
      observed_ge30_pct=float(100*a.mean()),predicted_ge30_pct=float(100*b.mean()),
      frequency_bias_pp=float(100*(b.mean()-a.mean())),misclassification_pct=float(100*(a!=b).mean()),
      false_negative_pct=float(100*fn/(fn+tp)) if fn+tp else None,
      false_positive_pct=float(100*fp/(fp+tn)) if fp+tn else None,tp=tp,fn=fn,fp=fp,tn=tn)

def bootstrap(q):
    """All sites share resampled 7-day blocks; conditional inference on this panel."""
    days=pd.date_range('2025-06-01','2025-08-31')
    q=q.copy();q['day']=q.timestamp.dt.normalize()
    a=[]
    for model in MODELS:
        e=q[model]-q.observed
        frame=pd.DataFrame({'day':q.day,'count':1,'bias':e,'abs':e.abs(),'sq':e**2,
            'mis':(q[model]>=30)!=(q.observed>=30)})
        a.append(frame.groupby('day')[['count','bias','abs','sq','mis']].sum().reindex(days,fill_value=0).to_numpy())
    arr=np.array(a);rng=np.random.default_rng(SEED)
    ix=(rng.integers(0,92,size=(1000,14,1))+np.arange(7)[None,None,:])%92
    ix=ix.reshape(1000,-1)[:,:92]
    totals=arr[:,ix,:].sum(axis=2)
    vals={'bias':totals[:,:,1]/totals[:,:,0],'mae':totals[:,:,2]/totals[:,:,0],
       'rmse':np.sqrt(totals[:,:,3]/totals[:,:,0]),'misclassification_pct':100*totals[:,:,4]/totals[:,:,0]}
    out={}
    for i,m in enumerate(MODELS):
        out[m]={k+'_ci95':np.quantile(v[i],[.025,.975]).tolist() for k,v in vals.items()}
    differences=[]
    for i,m in enumerate(MODELS[1:],start=1):
        differences.append({'comparator':m,'mae_IDW_minus_comparator':float((q.IDW-q.observed).abs().mean()-(q[m]-q.observed).abs().mean()),
          'ci95':np.quantile(vals['mae'][0]-vals['mae'][i],[.025,.975]).tolist()})
    return out,differences

def main():
    obs=pd.read_parquet(ROOT/'observations_hourly.parquet')
    pred=pd.read_parquet(ROOT/'predictions_hourly.parquet')
    assert not pred.duplicated(['station_id','timestamp']).any()
    summary=[];site=[];spatial=[];paired=[];matched=[];daily=[]
    for clock,shift in CLOCKS.items():
        for variant,minimum,column,count in [('primary',5,'observed','n_valid'),('six_readings',6,'observed','n_valid'),('exclude_suspect',5,'observed_strict_qc','n_strict_qc')]:
            h=obs.loc[obs[count]>=minimum,['station_id','clock_hour',column,count]].rename(columns={column:'observed',count:'n_readings'})
            h['timestamp']=h.clock_hour+pd.Timedelta(hours=shift)
            q=pred.merge(h,on=['station_id','timestamp'],how='inner',validate='one_to_one').dropna(subset=['observed']+MODELS)
            assert len(q)>0
            if variant=='primary':
                out=q.copy();out['clock']=clock;matched.append(out)
            for window,z in q.groupby('window'):
                cis,diff=bootstrap(z) if variant=='primary' else ({m:{} for m in MODELS},[])
                for model in MODELS:
                    summary.append(dict(clock=clock,variant=variant,window=window,model=model,
                       n_sites=z.station_id.nunique(),n_dates=z.timestamp.dt.date.nunique(),
                       **metrics(z.observed.to_numpy(),z[model].to_numpy()),**cis[model]))
                if variant!='primary':continue
                for d in diff:paired.append(dict(clock=clock,window=window,**d))
                for sid,zz in z.groupby('station_id'):
                    for model in MODELS:
                        site.append(dict(clock=clock,window=window,station_id=int(sid),model=model,**metrics(zz.observed.to_numpy(),zz[model].to_numpy())))
                for time,zz in z.groupby('timestamp'):
                    if len(zz)<10:continue
                    for model in ['IDW','Nearest','ERA5_corrected']:
                        rho=spearmanr(zz.observed,zz[model]).statistic if zz[model].nunique()>1 and zz.observed.nunique()>1 else np.nan
                        spatial.append(dict(clock=clock,window=window,timestamp=time,model=model,n_sites=len(zz),rho=float(rho),
                          observed_sd=float(zz.observed.std()),predicted_sd=float(zz[model].std())))
                for day,zz in z.groupby(z.timestamp.dt.date):
                    for model in MODELS:
                        daily.append(dict(clock=clock,window=window,day=str(day),model=model,**metrics(zz.observed.to_numpy(),zz[model].to_numpy())))
    pd.concat(matched,ignore_index=True).to_parquet(ROOT/'matched_pairs.parquet',index=False)
    for name,data in [('metrics',summary),('site_metrics',site),('paired_mae',paired),('daily_metrics',daily)]:
        (ROOT/f'{name}.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    sf=pd.DataFrame(spatial);sf.to_parquet(ROOT/'spatial_correlations.parquet',index=False)
    s=[]
    for key,z in sf.groupby(['clock','window','model']):
        s.append(dict(zip(['clock','window','model'],key),n_hours=len(z),defined_hours=int(z.rho.notna().sum()),
          median_spatial_rho=float(z.rho.median()),q25=float(z.rho.quantile(.25)),q75=float(z.rho.quantile(.75)),
          mean_observed_spatial_sd=float(z.observed_sd.mean()),mean_predicted_spatial_sd=float(z.predicted_sd.mean())))
    (ROOT/'spatial_metrics.json').write_text(json.dumps(s,indent=2),encoding='utf-8')
    f=pd.DataFrame(summary)
    print(f.query("variant=='primary'")[['clock','window','model','n','bias','mae','rmse','misclassification_pct','frequency_bias_pp']].to_string(index=False))
    print('Paired MAE',json.dumps(paired,indent=2))

if __name__=='__main__':main()
