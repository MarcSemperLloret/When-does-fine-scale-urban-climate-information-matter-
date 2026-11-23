"""Infer the VITUclim timestamp convention from the data (R1 #4, R2 #4, R5 #4, R6 2.3).

For every site, the diurnal temperature course in the provider's clock hours is aligned with two references
whose clocks are known: the nearest AVAMET station (minute data in local time, averaged over shifted
one-hour windows in 10-minute steps) and ERA5-Land 2-m temperature (UTC, interpolated). The lag that maximises
the correlation of hour-to-hour temperature changes identifies the offset of the provider's clock from local
summer time: 0 h = local summer time, +1 h = fixed CET, +2 h = UTC.
"""
from pathlib import Path
import glob, numpy as np, pandas as pd, xarray as xr

HERE = Path(__file__).resolve().parent
M3 = HERE.parents[1]
V = M3 / 'validacion_vituclim_2025'
obs = pd.read_parquet(V / 'observations_hourly.parquet')
st = pd.read_parquet(V / 'stations_selected.parquet').set_index('station_id')
sites = sorted(pd.read_parquet(V / 'matched_pairs.parquet').station_id.unique())
av = pd.read_parquet(M3 / 'datos/valencia_verano_qc.parquet', columns=['station_id', 'observed_local', 't_qc'])
av = av[(av.observed_local.dt.year == 2025)]

# ERA5-Land (UTC) at the nearest land cell to each site, 2025
ds = xr.concat([xr.open_dataset(f) for f in sorted(glob.glob(str(M3 / 'datos/era5land/era5land_2025_*.nc')))], dim='valid_time')
t2m = ds.t2m - 273.15
utc = pd.DatetimeIndex(ds.valid_time.values).tz_localize('UTC')

LAGS_MIN = np.arange(-180, 181, 10)
rows = []
for sid in sites:
    o = obs[obs.station_id == sid].set_index('clock_hour').observed.sort_index()
    o = o[(o.index >= '2025-06-02') & (o.index < '2025-08-31')]
    do = o.diff()[o.index.to_series().diff() == pd.Timedelta(hours=1)]
    # AVAMET: minute series of nearest station
    code = st.loc[sid, 'nearest_avamet']
    a = av[av.station_id == code].set_index('observed_local').t_qc.sort_index()
    a = a[~a.index.duplicated()].resample('10min').mean().interpolate(limit=3)
    best_a = None; corr_a = []
    for L in LAGS_MIN:
        # mean of AVAMET over [t+L, t+L+60min) for each provider clock hour t
        hm = a.rolling('60min').mean().shift(-5, freq='10min')  # value at t = mean over [t, t+60)
        al = hm.reindex(o.index + pd.Timedelta(minutes=int(L)))
        al.index = o.index
        da = al.diff()
        j = pd.concat([do, da], axis=1, join='inner').dropna()
        corr_a.append(j.corr().iloc[0, 1] if len(j) > 100 else np.nan)
    La = int(LAGS_MIN[int(np.nanargmax(corr_a))])
    # ERA5-Land: hour mean ~ value at mid-hour; local summer time = UTC + 2 h
    lat, lon = st.loc[sid, 'latitude'], st.loc[sid, 'longitude']
    cell = t2m.sel(latitude=lat, longitude=lon, method='nearest').values
    if np.isnan(cell).all():
        sub = t2m.isel(valid_time=0).to_dataframe().dropna().reset_index()
        k = ((sub.latitude - lat) ** 2 + (sub.longitude - lon) ** 2).idxmin()
        cell = t2m.sel(latitude=sub.latitude[k], longitude=sub.longitude[k]).values
    e = pd.Series(cell, index=utc.tz_convert('Europe/Madrid').tz_localize(None)).sort_index()
    e = e[~e.index.duplicated()].resample('10min').interpolate()
    corr_e = []
    for L in LAGS_MIN:
        el = e.reindex(o.index + pd.Timedelta(minutes=int(L) + 30)); el.index = o.index
        j = pd.concat([do, el.diff()], axis=1, join='inner').dropna()
        corr_e.append(j.corr().iloc[0, 1] if len(j) > 100 else np.nan)
    Le = int(LAGS_MIN[int(np.nanargmax(corr_e))])
    rows.append(dict(station_id=int(sid), nearest_avamet=code, lag_avamet_min=La, corr_avamet=float(np.nanmax(corr_a)),
                     corr_avamet_lag0=float(corr_a[list(LAGS_MIN).index(0)]), corr_avamet_lag60=float(corr_a[list(LAGS_MIN).index(60)]),
                     corr_avamet_lag120=float(corr_a[list(LAGS_MIN).index(120)]),
                     lag_era5_min=Le, corr_era5=float(np.nanmax(corr_e))))
    print(sid, code, La, Le, flush=True)
d = pd.DataFrame(rows); d.to_csv(HERE / 'reloj_vituclim.csv', index=False)
print(d.describe().round(3).to_string())
print('AVAMET lag counts', d.lag_avamet_min.value_counts().sort_index().to_dict())
print('ERA5 lag counts', d.lag_era5_min.value_counts().sort_index().to_dict())
