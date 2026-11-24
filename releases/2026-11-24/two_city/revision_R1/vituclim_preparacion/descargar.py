"""Anonymous, cached monthly downloads; excludes the reserved 2024 summer."""
from pathlib import Path
import calendar, concurrent.futures, datetime, hashlib, json, time
import urllib.request, urllib.parse

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'viabilidad_vituclim_2026-09-21'
RAW=ROOT/'raw'
RAW.mkdir(parents=True,exist_ok=True)
URL='https://vituclim.org/geoserver/ceam/wfs'

def download(job):
    sid,month=job
    dest=RAW/f'station_{sid}_2025_{month:02}.json'
    provenance=dest.with_suffix('.provenance.json')
    if dest.exists() and provenance.exists():
        record=json.loads(provenance.read_text())
        if hashlib.sha256(dest.read_bytes()).hexdigest()==record['sha256']:
            return record
    last=calendar.monthrange(2025,month)[1]
    params={'service':'WFS','version':'2.0.0','request':'GetFeature',
      'typeNames':'ceam:vp_reporte_estaciones_10min','outputFormat':'application/json','count':20000,
      'viewparams':f'station_id:{sid};fecha_inicio:2025-{month:02}-01T00:00:00;fecha_fin:2025-{month:02}-{last:02}T23:59:59'}
    url=URL+'?'+urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url,timeout=55) as r:
                body=r.read(); status=r.status
            data=json.loads(body)
            n=len(data['features'])
            assert n==data['numberReturned']
            assert not isinstance(data.get('numberMatched'),int) or n==data['numberMatched']
            # A station assigned to multiple subnetworks can be repeated by
            # the report view. Preserve all records for explicit deduplication.
            assert n<20000, (sid,month,n)
            dest.write_bytes(body)
            record={'station_id':sid,'year':2025,'month':month,'url':url,'http_status':status,
              'rows':n,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),
              'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
            provenance.write_text(json.dumps(record,indent=2),encoding='utf-8')
            return record
        except Exception:
            if attempt==2: raise
            time.sleep(2*(attempt+1))

if __name__=='__main__':
    plan=json.loads((ROOT/'plan.json').read_text(encoding='utf-8'))
    jobs=[(sid,m) for sid in plan['station_ids'] for m in (6,7,8)]
    manifest=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for record in pool.map(download,jobs):
            manifest.append(record)
            print(f"{len(manifest)}/{len(jobs)} station={record['station_id']} month={record['month']} rows={record['rows']}",flush=True)
    (ROOT/'download_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
