"""Download ERA5 single-level variables needed for UTCI (dewpoint, wind, radiation) over both cities.

Uses the existing authorised CDS configuration (never printed). Summers 2019-2023 and 2025; 2024 excluded.
ERA5 (not ERA5-Land) is used because it provides direct-beam solar radiation at the surface.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json, hashlib
import cdsapi, xarray as xr

HERE = Path(__file__).resolve().parent
M3 = HERE.parents[1]
OUT = HERE / 'era5'; OUT.mkdir(exist_ok=True)
ENV = M3.parent / 'downbursts-cv-pilot/.env'
YEARS = [2019, 2020, 2021, 2022, 2023, 2025]
AREAS = {'Valencia': [39.65, -0.55, 39.30, -0.15], 'Madrid': [40.75, -4.0, 40.20, -3.30]}
VARS = ['2m_dewpoint_temperature', '2m_temperature', '10m_u_component_of_wind', '10m_v_component_of_wind',
        'surface_solar_radiation_downwards', 'total_sky_direct_solar_radiation_at_surface',
        'surface_thermal_radiation_downwards']


def main():
    kv = {}
    for line in ENV.read_text(encoding='utf8').splitlines():
        if '=' in line and not line.strip().startswith('#'):
            k, v = line.split('=', 1); kv[k.strip()] = v.strip().strip('"').strip("'")
    assert kv.get('CDS_API_URL') and kv.get('CDS_API_KEY'), 'Missing CDS configuration'

    def one(job):
        city, y = job
        p = OUT / f'era5_utci_{city}_{y}.nc'
        if p.exists():
            return dict(city=city, year=y, status='cached', file=p.name)
        print('requesting', city, y, flush=True)
        c = cdsapi.Client(url=kv['CDS_API_URL'].replace('/api/v2', '/api'), key=kv['CDS_API_KEY'], quiet=True, debug=False)
        c.retrieve('reanalysis-era5-single-levels', {
            'product_type': ['reanalysis'], 'variable': VARS, 'year': [str(y)], 'month': ['06', '07', '08'],
            'day': [f'{d:02d}' for d in range(1, 32)], 'time': [f'{h:02d}:00' for h in range(6, 19)],
            'area': AREAS[city], 'data_format': 'netcdf', 'download_format': 'unarchived'}, str(p))
        with xr.open_dataset(p) as d:
            names = list(d.data_vars)
        print('done', p.name, names, flush=True)
        return dict(city=city, year=y, status='downloaded', file=p.name, variables=names, sha256=hashlib.sha256(p.read_bytes()).hexdigest())

    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(one, [(c, y) for c in AREAS for y in YEARS]))
    (HERE / 'era5_descargas.json').write_text(json.dumps(dict(areas=AREAS, variables=VARS, requests=rows), indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
