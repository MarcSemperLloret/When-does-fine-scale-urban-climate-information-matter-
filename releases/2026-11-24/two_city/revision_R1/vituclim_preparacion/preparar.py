from pathlib import Path
import json,sys,hashlib
import numpy as np
import pandas as pd
import geopandas as gpd

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
SOURCE=BASE/'viabilidad_vituclim_2026-09-21'
sys.path.insert(0,str(BASE/'analisis'))
from p2_comparar_era5land import campo_avamet,campo_era5,BARRIOS,UTM,pivot_estaciones

def observations():
    rows=[];checks=[]
    plan=json.loads((ROOT/'plan.json').read_text(encoding='utf-8'))
    for sid in plan['station_ids']:
        rr=[]
        for month in (6,7,8):
            f=ROOT/f'raw/station_{sid}_2025_{month:02}.json'
            meta=json.loads(f.with_suffix('.provenance.json').read_text())
            assert hashlib.sha256(f.read_bytes()).hexdigest()==meta['sha256']
            rr.extend([x['properties'] for x in json.loads(f.read_bytes())['features']])
        d=pd.DataFrame(rr);d['timestamp']=pd.to_datetime(d.fecha_hora)
        assert (d.timestamp.dt.year==2025).all()
        d['temperature']=pd.to_numeric(d.temperatura,errors='coerce')
        d['humidity']=pd.to_numeric(d.humedad,errors='coerce')
        conflict=d.groupby('timestamp').temperature.nunique(dropna=False)>1
        bad_times=conflict[conflict].index
        n=len(d);dup=int(d.duplicated('timestamp').sum())
        d=d[~d.timestamp.isin(bad_times)].drop_duplicates('timestamp').sort_values('timestamp').copy()
        invalid=~d.temperature.between(5,50)
        ninvalid=int(invalid.sum())
        d.loc[invalid,'temperature']=np.nan
        dt=d.timestamp.diff().dt.total_seconds();dx=d.temperature.diff();nxt=d.temperature.shift(-1)-d.temperature
        spike=(dt.eq(600)&dt.shift(-1).eq(600)&dx.abs().gt(4)&nxt.abs().gt(4)&(dx*nxt<0))
        groups=(d.temperature.ne(d.temperature.shift())|dt.ne(600)).cumsum()
        flat=groups.map(groups.value_counts()).ge(73)
        d['suspicious']=spike|flat
        d['station_id']=sid
        d['temperature_strict_qc']=d.temperature.mask(d.suspicious)
        d['clock_hour']=d.timestamp.dt.floor('h')
        h=d.groupby('clock_hour').agg(observed=('temperature','mean'),n_valid=('temperature','count'),
           observed_strict_qc=('temperature_strict_qc','mean'),n_strict_qc=('temperature_strict_qc','count'))
        h['station_id']=sid;h=h.reset_index()
        rows.append(h)
        expected=json.loads((SOURCE/f'daily_{sid}_2025.json').read_bytes())
        daily={pd.Timestamp(x['properties']['fecha']).date():x['properties']['lecturas_capturadas'] for x in expected['features']}
        counts=d.groupby(d.timestamp.dt.date).size()
        mismatches={str(day):[int(num),int(daily.get(day,0))] for day,num in counts.items() if num!=daily.get(day)}
        checks.append(dict(station_id=sid,raw_rows=n,duplicate_rows=dup,conflicting_timestamps=len(bad_times),
          unique_rows=len(d),invalid_temperature=ninvalid,spike_flags=int(spike.sum()),flat_flags=int(flat.sum()),
          null_humidity=int(d.humidity.isna().sum()),temperature_min=float(d.temperature.min()),temperature_max=float(d.temperature.max()),
          hours_ge5=int((h.n_valid>=5).sum()),hours_eq6=int((h.n_valid==6).sum()),
          daily_counter_mismatches=mismatches,non_10min_grid=int((d.timestamp.dt.minute%10!=0).sum())))
    pd.concat(rows,ignore_index=True).to_parquet(ROOT/'observations_hourly.parquet',index=False)
    (ROOT/'qc_summary.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print('Observation QC:',sum(r['unique_rows'] for r in checks),'unique readings;',sum(r['duplicate_rows'] for r in checks),'duplicates;',sum(r['invalid_temperature'] for r in checks),'invalid T',flush=True)

def predictions():
    plan=json.loads((ROOT/'plan.json').read_text(encoding='utf-8'))
    features=json.loads((SOURCE/'stations.json').read_bytes())['features']
    stations=gpd.GeoDataFrame.from_features([f for f in features if f['properties']['station_id'] in plan['station_ids']],crs=4326).sort_values('station_id').reset_index(drop=True)
    sec=gpd.read_file(BASE/'SCS_ampliado_2026-09-07/soporte/secciones.gpkg').sort_values('CUSEC').reset_index(drop=True)
    cent=sec.geometry.centroid
    raw=pd.read_parquet(BASE/'datos/valencia_verano_qc.parquet')
    assert 2024 not in raw.year.unique()
    raw=raw[raw.station_id.isin(BARRIOS)].copy();raw['hora']=raw.observed_local.dt.hour
    hourly=raw.groupby(['station_id','date','hora'],observed=True).t_qc.mean().reset_index()
    coords=raw.groupby('station_id')[['latitude','longitude']].first()
    ap=gpd.GeoDataFrame(coords,geometry=gpd.points_from_xy(coords.longitude,coords.latitude),crs=4326).to_crs(UTM)
    points=stations.to_crs(UTM).geometry
    distances=np.hypot(points.x.to_numpy()[:,None]-ap.geometry.x.to_numpy(),points.y.to_numpy()[:,None]-ap.geometry.y.to_numpy())
    station_info=stations.drop(columns='geometry').copy()
    station_info['longitude']=stations.geometry.x;station_info['latitude']=stations.geometry.y
    station_info['nearest_avamet']=ap.index[distances.argmin(axis=1)]
    station_info['nearest_avamet_distance_m']=distances.min(axis=1)
    station_info.to_parquet(ROOT/'stations_selected.parquet',index=False)
    result=[];audit=[]
    for window,hours in [('Morning',[10,11,12]),('Afternoon',[16,17,18])]:
        local,ia=campo_avamet(cent,hours)
        era,ie,_=campo_era5(cent,hours)
        common=ia.intersection(ie)
        local=local[:,ia.get_indexer(common)];era=era[:,ie.get_indexer(common)]
        correction=float(local.mean()-era.mean());regional=era+correction
        frozen=np.load(BASE/f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{window}.npz')
        assert np.array_equal(local,frozen['local']), 'IDW field differs from manuscript'
        assert np.allclose(regional,frozen['regional'],atol=1e-6,rtol=0), 'ERA field differs from manuscript'
        times=pd.DatetimeIndex(common.get_level_values('date'))+pd.to_timedelta(common.get_level_values('hora'),unit='h')
        np.savez_compressed(ROOT/f'city_fields_{window}.npz',local=local,regional=regional,timestamps=times.to_numpy(),CUSEC=sec.CUSEC.to_numpy().astype(str))
        target,ita=campo_avamet(points,hours)
        re,itre,_=campo_era5(stations.geometry,hours)
        target=target[:,ita.get_indexer(common)];re=re[:,itre.get_indexer(common)]+correction
        pivot=pivot_estaciones(hourly,hours,ap.index).reindex(common)
        a=pivot.to_numpy();nearest=[]
        for dist in distances:
            order=np.argsort(dist);ordered=a[:,order];first=np.argmax(np.isfinite(ordered),axis=1)
            nearest.append(ordered[np.arange(len(a)),first])
        uniform=local.mean(axis=0)
        mask=times.year==2025
        for pos,sid in enumerate(stations.station_id):
            result.append(pd.DataFrame({'station_id':int(sid),'timestamp':times[mask],'window':window,
              'IDW':target[pos,mask],'Uniform':uniform[mask],'Nearest':np.array(nearest)[pos,mask],'ERA5_corrected':re[pos,mask]}))
        audit.append(dict(window=window,correction=correction,original_field_reproduced=True,all_years_hours=len(times),hours_2025=int(mask.sum()),
          original_avamet_stations=list(ap.index),sensor_observations_used_for_fit=False))
    pd.concat(result,ignore_index=True).to_parquet(ROOT/'predictions_hourly.parquet',index=False)
    (ROOT/'model_reconstruction.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps(audit,indent=2),flush=True)

if __name__=='__main__':
    observations()
    predictions()
