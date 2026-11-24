"""UTCI-based heat-access score (R2 #2, R4 #5, R5 #2, R6 3.1).

Air temperature varies by section (station, regional or uniform field, as in the main analysis); humidity,
wind and radiation are citywide hourly values from ERA5 (nearest land grid point to the city centre), because
no intra-urban fields of those variables exist. Mean radiant temperature (MRT) for a standing pedestrian:

  S = a_k [f_p I_n + 0.5 D + 0.5 alpha G] + eps_p [0.5 L_down + 0.5 L_up],  MRT = (S / (eps_p sigma))^0.25
  sun:   I_n = direct normal irradiance (fdir / sin(elevation)), f_p = projected-area factor
  shade: I_n = 0
with a_k = 0.7, eps_p = 0.97, alpha = 0.2 and L_up from a ground at air temperature (shade) or air
temperature + 10 K (sun). UTCI uses the Bröde et al. (2012) polynomial in pythermalcomfort. The primary
calculation uses the ERA5 10-m wind speed. A separate sensitivity halves that input. Both inputs are clipped
to the wind-speed range used by the implementation.

The exploratory route score averages q UTCI_sun + (1 - q) UTCI_shade, with q the chosen route's exposed
fraction. The weighted average represents the mix of sun and shade along the route. A section-hour fails when route UTCI reaches the threshold (26 C, moderate heat stress; and
32 C, strong heat stress). The score is P_i times the failure frequency, the same structure as Eq. 1 with UTCI
replacing the conjunction. Cases are classified P/U/C/X at 15% capacity as in the main analysis.
"""
from pathlib import Path
import sys, json, zipfile, tempfile, numpy as np, pandas as pd, xarray as xr, geopandas as gpd
from pythermalcomfort.models import utci

HERE = Path(__file__).resolve().parent
M3 = HERE.parents[1]
REL=(lambda r:r if (r/'datos/policy_scores_two_cities.parquet').exists() else Path(__file__).resolve().parents[2]/'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city')(Path(__file__).resolve().parents[2])
sys.path.insert(0, str(HERE.parent / 'capacidad')); from capacidad import common_loss, top
E = 1 + 1e-7
SIG = 5.670374e-8
CENTRE = {'Valencia': (39.47, -0.376), 'Madrid': (40.42, -3.70)}


import os
SOURCE = os.environ.get('UTCI_SOURCE', 'openmeteo')


def openmeteo_city(city):
    """Open-Meteo ERA5 archive: radiation is the mean over the preceding hour (as CDS accumulations stamped at
    the end of the hour); downward longwave is not provided and is estimated with Brutsaert's clear-sky
    emissivity and a quadratic cloud correction, eps = a (e/T)^(1/7) (1 + b c^2) capped at 1, with a and b calibrated
    against ERA5 strd for Valencia 2021 (out-of-sample August bias -0.1 W m-2, MAE 12.6 W m-2)."""
    d = pd.concat([pd.read_csv(f) for f in sorted((HERE / 'openmeteo').glob(f'openmeteo_{city}_*.csv'))])
    t = pd.DatetimeIndex(pd.to_datetime(d.time)).tz_localize('UTC')
    T = d.temperature_2m.to_numpy() + 273.15; Td = d.dew_point_2m.to_numpy()
    e = 6.112 * np.exp(17.62 * Td / (243.12 + Td))
    cal = json.loads((HERE / 'onda_larga_calibracion.json').read_text())  # fitted to ERA5 strd, Valencia 2021 (calibrar_onda_larga.py)
    eps = np.minimum(cal['a'] * (e / T) ** (1 / 7) * (1 + cal['b'] * (d.cloud_cover.to_numpy() / 100) ** 2), 1.0)
    out = pd.DataFrame(dict(d2m=Td + 273.15, t2m=T, u10=d.wind_speed_10m.to_numpy(), v10=0.0,
                            ssrd=d.shortwave_radiation.to_numpy() * 3600, fdir=d.direct_radiation.to_numpy() * 3600,
                            strd=eps * SIG * T ** 4 * 3600), index=t)
    return out.sort_index()


def era5_city(city):
    if SOURCE == 'openmeteo':
        return openmeteo_city(city)
    frames = []
    for f in sorted((HERE / 'era5').glob(f'era5_utci_{city}_*.nc')):
        tmp = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(f) as z:
            z.extractall(tmp)
        ds = xr.merge([xr.open_dataset(p) for p in tmp.glob('*.nc')], compat='override')
        lat, lon = CENTRE[city]
        pt = ds.sel(latitude=lat, longitude=lon, method='nearest')
        frames.append(pt[['d2m', 't2m', 'u10', 'v10', 'ssrd', 'fdir', 'strd']].to_dataframe())
    d = pd.concat(frames).drop(columns=['latitude', 'longitude', 'number', 'expver'], errors='ignore')
    d.index = pd.DatetimeIndex(d.index).tz_localize('UTC')
    return d.sort_index()


def solar_elevation(ts_utc, lat, lon):
    doy = ts_utc.dayofyear.to_numpy(); hr = ts_utc.hour.to_numpy() + ts_utc.minute.to_numpy() / 60
    g = 2 * np.pi / 365 * (doy - 1 + (hr - 12) / 24)
    eq = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g) - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    dec = 0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g) + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g)
    ha = np.radians((hr * 60 + eq + 4 * lon) / 4 - 180)
    la = np.radians(lat)
    return np.degrees(np.arcsin(np.sin(la) * np.sin(dec) + np.cos(la) * np.cos(dec) * np.cos(ha)))


def hourly_inputs(city, local_starts):
    """Citywide inputs for local clock hours [h, h+1): accumulations stamped at the UTC end of the hour,
    instantaneous variables averaged over the two bounding UTC instants."""
    d = era5_city(city)
    st = pd.DatetimeIndex(local_starts).tz_localize('Europe/Madrid', ambiguous='NaT', nonexistent='NaT').tz_convert('UTC')
    end = st + pd.Timedelta(hours=1)
    acc = d[['ssrd', 'fdir', 'strd']].reindex(end) / 3600.0
    ins = (d[['d2m', 't2m', 'u10', 'v10']].reindex(st).to_numpy() + d[['d2m', 't2m', 'u10', 'v10']].reindex(end).to_numpy()) / 2
    ins = pd.DataFrame(ins, columns=['d2m', 't2m', 'u10', 'v10'], index=st)
    lat, lon = CENTRE[city]
    elev = solar_elevation(st + pd.Timedelta(minutes=30), lat, lon)
    out = pd.DataFrame(dict(G=acc.ssrd.to_numpy(), Ih=acc.fdir.to_numpy(), Ld=acc.strd.to_numpy(), Td=ins.d2m.to_numpy() - 273.15,
                            wind=np.hypot(ins.u10, ins.v10).to_numpy(), elev=elev), index=pd.DatetimeIndex(local_starts))
    out['D'] = (out.G - out.Ih).clip(lower=0)
    s = np.sin(np.radians(np.clip(out.elev, 1, 90)))
    out['In'] = np.where(out.elev > 1, (out.Ih / s).clip(upper=1100), 0)
    b = out.elev.clip(lower=0)
    out['fp'] = 0.308 * np.cos(np.radians(b * (1 - b ** 2 / 48402)))
    return out


def vapour_rh(T, Td):
    es = lambda t: 6.112 * np.exp(17.62 * t / (243.12 + t))
    return np.clip(100 * es(Td) / es(T), 5, 100)


def mrt(T, inp, sun):
    Lup = SIG * (T + 273.15 + (10 if sun else 0)) ** 4
    K = 0.7 * ((inp.fp.to_numpy() * inp.In.to_numpy() if sun else 0) + 0.5 * inp.D.to_numpy() + 0.5 * 0.2 * inp.G.to_numpy())
    S = K + 0.97 * (0.5 * inp.Ld.to_numpy() + 0.5 * Lup)
    return (S / (0.97 * SIG)) ** 0.25 - 273.15


def utci_pair(T, inp, wind_factor):
    """T: sections x hours. Returns (UTCI_sun, UTCI_shade)."""
    rh = vapour_rh(T, inp.Td.to_numpy()[None, :])
    v = np.clip(inp.wind.to_numpy()[None, :] * wind_factor, 0.5, 17) * np.ones_like(T)
    out = []
    for sun in (True, False):
        tr = mrt(T, inp, sun)
        u = utci(tdb=T.ravel(), tr=np.broadcast_to(tr, T.shape).ravel(), v=v.ravel(), rh=rh.ravel(), limit_inputs=False, round_output=False)
        out.append(np.asarray(u.utci, float).reshape(T.shape))
    return out


YEARS = [int(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else None
SUFFIX = (('_' + sys.argv[1].replace(',', '-')) if len(sys.argv) > 1 else '') + ('' if SOURCE == 'openmeteo' else '_' + SOURCE)


def main():
    pol = pd.read_parquet(REL / 'datos/policy_scores_two_cities.parquet')
    rows = []; diag = []
    for city in ['Valencia', 'Madrid']:
        if SOURCE == 'cds' and not list((HERE / 'era5').glob(f'era5_utci_{city}_*.nc')):
            print('no ERA5 files for', city); continue
        sec = pd.read_csv(REL / f'datos/secciones_{city}.csv', dtype={'CUSEC': str}).sort_values('CUSEC').reset_index(drop=True); P = sec.pob_65.to_numpy()
        routes = pd.read_parquet(M3 / f'Madrid_2026-09-07/datos/rutas_central_{city}_working_Full.parquet').query('weights==21')
        for w in ['Morning', 'Afternoon']:
            if city == 'Madrid':
                z = np.load(M3 / f'Madrid_2026-09-07/datos/campos_central_{w}.npz'); starts = pd.DatetimeIndex(z['datetime_local_start'])
            else:
                z = np.load(M3 / f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz')
                starts = pd.DatetimeIndex(pd.read_csv(HERE / f'valencia_index_{w}.csv', parse_dates=['start']).start)
            L, R = z['local'].astype(float), z['regional'].astype(float); months, hours = z['months'], z['hours']
            if YEARS:
                keep = np.isin(starts.year, YEARS); starts = starts[keep]; L, R = z['local'].astype(float)[:, keep], z['regional'].astype(float)[:, keep]; months, hours = z['months'][keep], z['hours'][keep]
            assert len(starts) == L.shape[1] and (starts.hour == hours).all() and (starts.month == months).all()
            inp = hourly_inputs(city, starts)
            ok = inp.notna().all(axis=1).to_numpy()
            diag.append(dict(city=city, window=w, hours=len(ok), hours_with_era5=int(ok.sum())))
            if ok.sum() < 0.9 * len(ok):
                print(city, w, 'ERA5 coverage too low', int(ok.sum()), 'of', len(ok), flush=True); continue
            inp = inp[ok]; L, R = L[:, ok], R[:, ok]; U = np.broadcast_to(L.mean(0), L.shape)
            mo, ho = months[ok], hours[ok]
            for wf in [0.5, 1.0]:
                pairs = {name: utci_pair(F, inp, wf) for name, F in [('local', L), ('regional', R), ('uniform', np.ascontiguousarray(U))]}
                for mode, rr in routes.groupby('mode'):
                    reach = rr[rr.date.eq('06-15') & rr.hour.eq(10)].set_index('CUSEC').loc[sec.CUSEC].reachable.to_numpy()
                    ix = np.flatnonzero(reach); k = int(.15 * len(ix)); p = P[ix]
                    keys = [f'{m:02}-15' for m in mo]
                    lk = {(d, h): rr[rr.date.eq(d) & rr.hour.eq(h)].set_index('CUSEC').loc[sec.CUSEC].fraction.to_numpy()[ix] for d, h in sorted(set(zip(keys, ho)))}
                    q = np.stack([lk[d, h] for d, h in zip(keys, ho)], axis=1)
                    route = {n: q * su[ix] + (1 - q) * sh[ix] for n, (su, sh) in pairs.items()}
                    if wf == 0.5 and mode == 'network':
                        diag[-1].update({f'median_utci_sun_{wf}': float(np.median(pairs['local'][0])), f'median_utci_shade_{wf}': float(np.median(pairs['local'][1])),
                                         'median_route_utci': float(np.median(route['local'])), 'share_route_ge32': float((route['local'] >= 32).mean()),
                                         'share_route_ge26': float((route['local'] >= 26).mean())})
                    for thr in [26, 32]:
                        sc = {n: p * (r >= thr).mean(1) for n, r in route.items()}
                        uL, uR, uU = sc['local'], sc['regional'], sc['uniform']
                        if np.sort(uL)[-k:].sum() <= 0 or np.sort(uR)[-k:].sum() <= 0:
                            continue
                        lo = lambda sel: 100 * (1 - uL[sel].sum() / np.sort(uL)[-k:].sum())
                        loR = lambda sel: 100 * (1 - uR[sel].sum() / np.sort(uR)[-k:].sum())
                        ml, stt, _ = common_loss(uL, uR, k)
                        lL = top(uL, k)
                        # comparison with the published binary score (30 C, phi 0.4)
                        o = pol.query('city==@city and window==@w and mode==@mode and threshold==30 and phi==0.4').sort_values('CUSEC')
                        lB = top(o.local.to_numpy()[ix], k)
                        rows.append(dict(city=city, window=w, mode=mode, wind_factor=wf, utci_threshold=thr, k=k, pop_loss=lo(top(p, k)), uni_loss=lo(top(uU, k)), pop_loss_R=loR(top(p, k)), uni_loss_R=loR(top(uU, k)),
                                         minimum_common_loss=ml, milp=stt, changed_local_regional=k - len(np.intersect1d(lL, top(uR, k))),
                                         changed_vs_binary=k - len(np.intersect1d(lL, lB)), rho_population=float(pd.Series(uL).corr(pd.Series(p), method='spearman')),
                                         shortlist=';'.join(sorted(sec.CUSEC.to_numpy()[ix][lL])), binary_shortlist=';'.join(sorted(sec.CUSEC.to_numpy()[ix][lB]))))
                print(city, w, wf, flush=True)
    d = pd.DataFrame(rows); d.to_csv(HERE / f'utci_estados{SUFFIX}.csv', index=False); pd.DataFrame(diag).to_csv(HERE / f'utci_diagnostico{SUFFIX}.csv', index=False)
    d['state'] = np.select([(d.pop_loss <= E) & (d.pop_loss_R <= E), (d.uni_loss <= E) & (d.uni_loss_R <= E), d.minimum_common_loss <= E], ['P', 'U', 'C'], 'X')
    print(pd.DataFrame(diag).round(2).to_string())
    print(d.pivot_table(index=['city', 'window', 'mode'], columns=['wind_factor', 'utci_threshold'], values='state', aggfunc='first').to_string())
    print(d.groupby(['wind_factor', 'utci_threshold']).state.value_counts().unstack(fill_value=0).to_string())


if __name__ == '__main__':
    main()
