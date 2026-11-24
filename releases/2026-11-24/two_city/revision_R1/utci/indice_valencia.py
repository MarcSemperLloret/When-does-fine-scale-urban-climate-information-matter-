"""Local start time of every hour in the Valencia fields (the original fields_*.npz store month and hour only)."""
from pathlib import Path
import sys, numpy as np, pandas as pd, geopandas as gpd
HERE = Path(__file__).resolve().parent
M3 = HERE.parents[1]
REL=(lambda r:r if (r/'datos/policy_scores_two_cities.parquet').exists() else Path(__file__).resolve().parents[2]/'codigo_publico_UC_2026-10-04/releases/2026-10-04/two_city')(Path(__file__).resolve().parents[2])
sys.path.insert(0, str(M3 / 'analisis'))
import p2_comparar_era5land as P2
sec = pd.read_csv(REL / 'datos/secciones_Valencia.csv', dtype={'CUSEC': str}).sort_values('CUSEC').reset_index(drop=True)
shp = gpd.read_file(f"zip://{M3 / 'datos/seccionado_2024.zip'}!SECC_CE_20240101.shp")
g = shp[shp.CUSEC.isin(sec.CUSEC)].to_crs(P2.UTM).sort_values('CUSEC').reset_index(drop=True)
cent = g.geometry.centroid
for w, hrs in [('Morning', [10, 11, 12]), ('Afternoon', [16, 17, 18])]:
    z = np.load(M3 / f'SCS_ampliado_2026-09-07/datos_ampliacion/fields_{w}.npz')
    ta, ia = P2.campo_avamet(cent, hrs); te, ie, _ = P2.campo_era5(gpd.GeoSeries(cent, crs=P2.UTM), hrs)
    index = ia.intersection(ie)
    assert np.allclose(ta[:, ia.get_indexer(index)], z['local'].astype(float), atol=1e-6)
    start = pd.to_datetime(index.get_level_values(0)) + pd.to_timedelta(index.get_level_values(1), unit='h')
    assert (start.hour == z['hours']).all() and (start.month == z['months']).all()
    pd.DataFrame({'start': start}).to_csv(HERE / f'valencia_index_{w}.csv', index=False)
    print(w, len(start), start.min(), start.max())
