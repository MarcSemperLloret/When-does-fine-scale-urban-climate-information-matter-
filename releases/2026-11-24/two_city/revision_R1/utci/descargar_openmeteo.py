"""ERA5 hourly variables for UTCI from the Open-Meteo historical archive (ERA5 model, no credentials, no queue).

Requested per city and summer (June-August 2019-2023 and 2025; 2024 excluded): 2-m temperature and dew point,
10-m wind speed, global, direct and diffuse shortwave radiation (means over the preceding hour) and cloud
cover, in UTC. Only the two city-centre coordinates are sent.
"""
from pathlib import Path
import json, time, urllib.request, urllib.parse
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / 'openmeteo'; OUT.mkdir(exist_ok=True)
CENTRE = {'Valencia': (39.47, -0.376), 'Madrid': (40.42, -3.70)}
VARS = 'temperature_2m,dew_point_2m,wind_speed_10m,shortwave_radiation,direct_radiation,diffuse_radiation,cloud_cover'
rows = []
for city, (lat, lon) in CENTRE.items():
    for y in [2019, 2020, 2021, 2022, 2023, 2025]:
        f = OUT / f'openmeteo_{city}_{y}.csv'
        if not f.exists():
            q = urllib.parse.urlencode(dict(latitude=lat, longitude=lon, start_date=f'{y}-06-01', end_date=f'{y}-08-31', hourly=VARS,
                                            wind_speed_unit='ms', timezone='GMT', models='era5'))
            with urllib.request.urlopen('https://archive-api.open-meteo.com/v1/archive?' + q, timeout=120) as r:
                d = json.load(r)
            df = pd.DataFrame(d['hourly']); df['grid_lat'] = d['latitude']; df['grid_lon'] = d['longitude']
            df.to_csv(f, index=False); time.sleep(1)
        df = pd.read_csv(f); rows.append(dict(city=city, year=y, hours=len(df), missing=int(df.isna().any(axis=1).sum()), grid=(df.grid_lat[0], df.grid_lon[0])))
print(pd.DataFrame(rows).to_string())
