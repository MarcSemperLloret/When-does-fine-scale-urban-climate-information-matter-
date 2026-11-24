"""Calibrate the downward-longwave parametrisation used with Open-Meteo against ERA5 strd from the CDS file
available for Valencia 2021 (06-18 UTC, June-August). eps = a (e/T)^(1/7) (1 + b c^2); a and b are fitted by
least squares on June-July and tested on August."""
from pathlib import Path
import zipfile, tempfile, json, numpy as np, pandas as pd, xarray as xr
from scipy.optimize import least_squares

HERE = Path(__file__).resolve().parent
SIG = 5.670374e-8
tmp = Path(tempfile.mkdtemp())
with zipfile.ZipFile(HERE / 'era5/era5_utci_Valencia_2021.nc') as z:
    z.extractall(tmp)
ds = xr.merge([xr.open_dataset(p) for p in tmp.glob('*.nc')], compat='override')
pt = ds.sel(latitude=39.5, longitude=-0.5, method='nearest')
cds = pd.DataFrame({'strd': pt.strd.values / 3600}, index=pd.DatetimeIndex(pt.valid_time.values))
om = pd.read_csv(HERE / 'openmeteo/openmeteo_Valencia_2021.csv'); om.index = pd.DatetimeIndex(pd.to_datetime(om.time))
j = om.join(cds, how='inner').dropna()
T = j.temperature_2m.to_numpy() + 273.15; Td = j.dew_point_2m.to_numpy(); c = j.cloud_cover.to_numpy() / 100
e = 6.112 * np.exp(17.62 * Td / (243.12 + Td)); y = j.strd.to_numpy()
model = lambda p, m: np.minimum(p[0] * (e[m] / T[m]) ** (1 / 7) * (1 + p[1] * c[m] ** 2), 1.0) * SIG * T[m] ** 4
train = j.index.month <= 7; test = ~train
fit = least_squares(lambda p: model(p, train) - y[train], x0=[1.24, 0.22])
a, b = fit.x
res = dict(a=float(a), b=float(b), n_train=int(train.sum()), n_test=int(test.sum()),
           bias_test=float(np.mean(model(fit.x, test) - y[test])), mae_test=float(np.mean(np.abs(model(fit.x, test) - y[test]))),
           r_test=float(np.corrcoef(model(fit.x, test), y[test])[0, 1]),
           bias_uncalibrated_test=float(np.mean(model([1.24, 0.22], test) - y[test])), grid=[float(pt.latitude), float(pt.longitude)])
(HERE / 'onda_larga_calibracion.json').write_text(json.dumps(res, indent=2), encoding='utf-8')
print(json.dumps(res, indent=1))
