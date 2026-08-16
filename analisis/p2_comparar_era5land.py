#!/usr/bin/env python3
"""Puerta 2: la reclasificacion sobrevive frente a un baseline real?

El piloto comparo el campo observado contra un campo espacialmente uniforme, y
eso tiene dos problemas. Es un straw man --una representacion incapaz por
construccion de producir diferencias espaciales-- y ademas hace que la
descomposicion bidireccional de la reclasificacion sea imposible: si todas las
secciones reciben el mismo valor, todas cruzan el corte en el mismo sentido.

ERA5-Land tiene 0,1 grados, unos 9 km. Sobre Valencia son pocas celdas, pero
mas de una, y puede conservar un gradiente costero. Es el baseline que decide
si el mecanismo central existe frente a una representacion gruesa **real**.

Cinco representaciones, en orden creciente de informacion:

  R1 uniforme          mediana de la red en cada hora; limite inferior
  R2 era5_bruto        ERA5-Land tal cual, interpolado a cada seccion
  R3 era5_sesgo        R2 mas una correccion global de sesgo, unica para la
                       ciudad y ajustada solo con los anos de desarrollo
  R4 era5_sesgo_hora   R2 mas una correccion por hora del dia, todavia comun a
                       toda la ciudad
  R5 avamet            campo observado por ponderacion inversa; referencia

No se aplica correccion por estacion a ERA5-Land: eso reintroduciria
exactamente la informacion intraurbana que se esta evaluando.

Salidas en salidas/tablas/p2_*.csv
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos"
TABLAS = BASE / "salidas" / "tablas"
UTM = "EPSG:25830"

VENTANAS = {"manana_10_12": [10, 11, 12], "tarde_16_18": [16, 17, 18]}
BARRIOS = ["c15m250e30", "c15m250e15", "c15m250e24",
           "c15m250e11", "c15m250e26", "c15m250e08"]
UMBRALES = (30.0, 32.0)
RNG = np.random.default_rng(20260806)
N_BOOT = 400


# ------------------------------------------------------------------ campos
MIN_ESTACIONES = 3


def pivot_estaciones(hor, horas, orden, min_estaciones=MIN_ESTACIONES):
    """Horas x estaciones, conservando las horas con al menos `min_estaciones`.

    Sustituye al `.dropna()` que exigia las seis simultaneamente. Vive aqui, y
    no copiada en cada script, porque justamente el problema fue que cuatro
    ficheros repetian el mismo filtro y ninguno declaraba lo que descartaba.
    """
    piv = (hor[hor["hora"].isin(horas)]
           .pivot_table(index=["date", "hora"], columns="station_id", values="t_qc")
           .reindex(columns=list(orden)))
    return piv[(~piv.isna()).sum(axis=1) >= min_estaciones]


def idw_renormalizada(w, piv):
    """Aplica pesos IDW repartiendo el de cada estacion ausente entre las presentes.

    Devuelve NaN donde ninguna estacion con peso no nulo tiene dato, que puede
    ocurrir cuando el llamante ademas restringe los pesos (k vecinos, excluir la
    mas proxima) y no debe confundirse con un cero.
    """
    A = piv.to_numpy()
    M = ~np.isnan(A)
    den = w @ M.astype(float).T
    num = w @ np.where(M, A, 0.0).T
    return np.divide(num, den, out=np.full_like(num, np.nan), where=den > 0)


def campo_avamet(cent, horas, min_estaciones=MIN_ESTACIONES):
    """IDW p=2 sobre las seis estaciones urbanas, renormalizada en cada instante.

    Esta funcion hacia `.dropna()`, es decir exigia que las **seis** estaciones
    reportasen simultaneamente. Como l'Olivereta (c15m250e11) no entra en el
    archivo hasta junio de 2021, aquello dejaba 2019 y 2020 sin una sola hora y
    retenia el 32 % de las disponibles, sin que nada en la salida lo delatase:
    el campo se construia, las cifras salian plausibles y dos de los seis
    veranos no estaban. Es el mismo tipo de fallo silencioso que documenta S2.

    Ahora se usan las estaciones presentes en cada instante y los pesos se
    renormalizan sobre ellas, que es lo que haria un servicio real. Se exige un
    minimo de `min_estaciones` porque con menos de tres el campo no puede
    expresar un gradiente en dos dimensiones y se aplanaria hacia la estacion
    superviviente. Con tres se conservan practicamente todas las horas de los
    seis veranos.

    La contrapartida es que la composicion de la red varia en el tiempo --- la
    mediana de estaciones disponibles es 3 en 2020 y 5 o 6 en los demas
    veranos ---. Se declara en las limitaciones y se acompana del subconjunto
    estricto de seis estaciones como analisis de sensibilidad.
    """
    df = pd.read_parquet(DATOS / "valencia_verano_qc.parquet")
    df = df[df["station_id"].isin(BARRIOS)].copy()
    df["hora"] = df["observed_local"].dt.hour
    hor = (df.groupby(["station_id", "date", "hora"], observed=True)["t_qc"]
             .mean().reset_index())
    est = df.groupby("station_id")[["latitude", "longitude"]].first()
    ge = gpd.GeoDataFrame(est, geometry=gpd.points_from_xy(est["longitude"], est["latitude"]),
                          crs="EPSG:4326").to_crs(UTM)
    d = np.sqrt((cent.x.values[:, None] - ge.geometry.x.values[None, :]) ** 2
                + (cent.y.values[:, None] - ge.geometry.y.values[None, :]) ** 2)
    w = 1.0 / np.maximum(d, 50.0) ** 2
    w /= w.sum(axis=1, keepdims=True)
    piv = pivot_estaciones(hor, horas, ge.index, min_estaciones)
    M = ~np.isnan(piv.to_numpy())
    anos = pd.to_datetime(piv.index.get_level_values("date")).year
    print(f"  AVAMET: {len(piv)} horas, estaciones por hora "
          f"mediana {int(np.median(M.sum(axis=1)))}, "
          f"minimo {int(M.sum(axis=1).min())}; por verano "
          + ", ".join(f"{y}:{(anos == y).sum()}" for y in sorted(set(anos))))
    return idw_renormalizada(w, piv), piv.index


def campo_era5(cent_ll, horas):
    """ERA5-Land en cada seccion, por celda de tierra mas proxima.

    ERA5-Land es un producto de tierra: las celdas de mar son NaN. Interpolar
    sin filtrarlas arrastraria el hueco a las secciones del litoral, que son
    justo las que mas importan aqui, asi que se toma la celda **valida** mas
    proxima.
    """
    ficheros = sorted(DATOS.glob("era5land/era5land_2*.nc"))
    if len(ficheros) < 18:
        raise SystemExit(f"Solo {len(ficheros)} de 18 ficheros de ERA5-Land: descarga incompleta")
    # Concatenacion a mano en vez de open_mfdataset, que exige dask para dos
    # megabytes de datos.
    ds = xr.concat([xr.open_dataset(f) for f in ficheros], dim="valid_time")
    ds = ds.sortby("valid_time")
    t = ds["t2m"] - 273.15

    # ERA5-Land publica en UTC; todo el estudio esta en hora local peninsular.
    local = pd.DatetimeIndex(ds["valid_time"].values).tz_localize("UTC").tz_convert(
        "Europe/Madrid").tz_localize(None)
    t = t.assign_coords(local=("valid_time", local))
    t = t.sel(valid_time=np.isin(local.hour, horas) & np.isin(local.month, (6, 7, 8)))
    local = pd.DatetimeIndex(t["local"].values)

    arr = t.transpose("valid_time", "latitude", "longitude").values
    lats, lons = ds["latitude"].values, ds["longitude"].values
    valida = ~np.isnan(arr).all(axis=0)
    ii, jj = np.where(valida)
    print(f"  celdas ERA5-Land: {valida.size}, con dato (tierra): {valida.sum()}")

    glat, glon = lats[ii], lons[jj]
    gp = gpd.GeoSeries(gpd.points_from_xy(glon, glat), crs="EPSG:4326").to_crs(UTM)
    cent_utm = cent_ll.to_crs(UTM)
    d = np.sqrt((cent_utm.x.values[:, None] - gp.x.values[None, :]) ** 2
                + (cent_utm.y.values[:, None] - gp.y.values[None, :]) ** 2)
    k = d.argmin(axis=1)
    print(f"  celdas distintas asignadas a secciones: {len(np.unique(k))}")

    T = arr[:, ii[k], jj[k]].T                      # secciones x horas
    idx = pd.MultiIndex.from_arrays(
        [local.normalize(), local.hour], names=["date", "hora"])
    return T, idx, len(np.unique(k))


# ------------------------------------------------------------------ metricas
def clasificar(T, umbral, alcanzable):
    return (T < umbral).mean(axis=1)


def comparar(frac_g, frac_f, alcanzable, pob):
    """Cobertura, flujos y priorizacion de una representacion frente a AVAMET."""
    corte = np.median(frac_f[alcanzable])
    serv_g = alcanzable & (frac_g >= corte)
    serv_f = alcanzable & (frac_f >= corte)
    sube, baja = ~serv_g & serv_f, serv_g & ~serv_f

    cob_g = float((frac_g[alcanzable] * pob[alcanzable]).sum() / pob.sum())
    cob_f = float((frac_f[alcanzable] * pob[alcanzable]).sum() / pob.sum())
    return {
        "cobertura_gruesa_pct": round(100 * cob_g, 2),
        "cobertura_avamet_pct": round(100 * cob_f, 2),
        "cobertura_dif_puntos": round(100 * (cob_f - cob_g), 2),
        "sec_falsas_inaccesibles": int(sube.sum()),
        "sec_falsas_accesibles": int(baja.sum()),
        "sec_reclasificadas": int(sube.sum() + baja.sum()),
        "sec_balance_neto": int(sube.sum() - baja.sum()),
        "pob_falsas_inaccesibles": round(float(pob[sube].sum())),
        "pob_falsas_accesibles": round(float(pob[baja].sum())),
        "pob_reclasificada": round(float(pob[sube].sum() + pob[baja].sum())),
        "pob_balance_neto": round(float(pob[sube].sum() - pob[baja].sum())),
        "pct_pob_reclasificada": round(100 * (pob[sube].sum() + pob[baja].sum()) / pob.sum(), 2),
        "pct_pob_balance_neto": round(100 * (pob[sube].sum() - pob[baja].sum()) / pob.sum(), 2),
        "bidireccional": bool(sube.sum() > 0 and baja.sum() > 0),
    }


def main() -> None:
    sec = pd.read_csv(TABLAS / "p4_secciones.csv", dtype={"CUSEC": str})
    g = gpd.read_file(f"zip://{DATOS / 'seccionado_2024.zip'}!SECC_CE_20240101.shp")
    g = g[g["CUSEC"].isin(sec["CUSEC"])].to_crs(UTM).merge(sec, on="CUSEC")
    cent = g.geometry.centroid
    cent_ll = gpd.GeoSeries(cent, crs=UTM)
    alcanzable = g["alcanzable"].to_numpy()
    pob = g["pob_65"].to_numpy()
    g["distrito"] = g["CUSEC"].str[5:7]

    filas, prio, disp, corte = [], [], [], []
    for v, horas in VENTANAS.items():
        print(f"\n== {v} ==")
        T_av, idx_av = campo_avamet(cent, horas)
        T_e5, idx_e5, n_celdas = campo_era5(cent_ll, horas)

        # Horas comunes a las dos fuentes, para que la comparacion no mezcle
        # muestras distintas.
        comun = idx_av.intersection(idx_e5)
        sel_av = idx_av.get_indexer(comun)
        sel_e5 = idx_e5.get_indexer(comun)
        T_av, T_e5 = T_av[:, sel_av], T_e5[:, sel_e5]
        print(f"  horas comunes AVAMET/ERA5-Land: {len(comun)}")

        # Correcciones de sesgo, unicas para la ciudad.
        sesgo = np.nanmean(T_av) - np.nanmean(T_e5)
        T_e5_b = T_e5 + sesgo
        horas_idx = comun.get_level_values("hora").to_numpy()
        T_e5_h = T_e5.copy()
        for h in np.unique(horas_idx):
            m = horas_idx == h
            T_e5_h[:, m] += np.nanmean(T_av[:, m]) - np.nanmean(T_e5[:, m])
        # Signo explicito: `sesgo` es lo que hay que SUMAR a ERA5-Land para
        # llevarlo al campo observado, de modo que un valor negativo significa
        # que ERA5-Land esta por ENCIMA de lo observado. Escribirlo al reves es
        # facil y cambia la direccion del error de politica.
        print(f"  ERA5-Land - AVAMET = {-sesgo:+.2f} C "
              f"({'calido' if sesgo < 0 else 'frio'}); correccion a aplicar: {sesgo:+.2f} C")

        reps = {"R1_uniforme": np.tile(np.median(T_av, axis=0), (len(g), 1)),
                "R2_era5_bruto": T_e5,
                "R3_era5_sesgo": T_e5_b,
                "R4_era5_sesgo_hora": T_e5_h}

        for u in UMBRALES:
            frac_av = clasificar(T_av, u, alcanzable)
            for nombre, T in reps.items():
                r = comparar(clasificar(T, u, alcanzable), frac_av, alcanzable, pob)
                r.update(ventana=v, umbral=u, representacion=nombre,
                         celdas_era5=n_celdas if nombre.startswith("R2") else None)
                filas.append(r)

                # Priorizacion: 20 % peor de cada representacion.
                a = alcanzable
                n = max(int(0.20 * a.sum()), 1)
                sg = pd.Series((pob * (1 - clasificar(T, u, a)))[a])
                sf = pd.Series((pob * (1 - frac_av))[a])
                tg, tf = set(sg.nlargest(n).index), set(sf.nlargest(n).index)
                dg = pd.Series((pob * (1 - clasificar(T, u, a)))[a]).groupby(
                    g.loc[a, "distrito"].to_numpy()).sum().rank(ascending=False)
                dfn = pd.Series((pob * (1 - frac_av))[a]).groupby(
                    g.loc[a, "distrito"].to_numpy()).sum().rank(ascending=False)
                prio.append({
                    "ventana": v, "umbral": u, "representacion": nombre,
                    "jaccard_top20": round(len(tg & tf) / len(tg | tf), 3),
                    "spearman_distritos": round(float(dg.corr(dfn, method="spearman")), 3),
                    "top5_distritos": f"{len(set(dg.nsmallest(5).index) & set(dfn.nsmallest(5).index))}/5",
                })

        # ------------------------------------------------ dispersion espacial
        # La cifra que decide si ERA5-Land es un baseline real o un uniforme
        # disfrazado: cuantos valores distintos llega a producir sobre las
        # secciones alcanzables.
        for u in UMBRALES:
            for nombre, T in reps.items():
                f = clasificar(T, u, alcanzable)[alcanzable]
                disp.append({"ventana": v, "umbral": u, "representacion": nombre,
                             "sd_espacial": round(float(f.std()), 4),
                             "rango_espacial": round(float(f.max() - f.min()), 4),
                             "valores_distintos": int(len(np.unique(f.round(6))))})
            fa = clasificar(T_av, u, alcanzable)[alcanzable]
            disp.append({"ventana": v, "umbral": u, "representacion": "R5_avamet",
                         "sd_espacial": round(float(fa.std()), 4),
                         "rango_espacial": round(float(fa.max() - fa.min()), 4),
                         "valores_distintos": int(len(np.unique(fa.round(6))))})

        # ------------------------------------------------- barrido del corte
        # El corte de elegibilidad en la mediana es arbitrario y **maximiza** la
        # reclasificacion: si la representacion gruesa es casi plana, cae entera
        # a un lado del corte y arrastra a la mitad del censo. Hay que reportar
        # la curva completa, no un punto elegido.
        for u in UMBRALES:
            fa = clasificar(T_av, u, alcanzable)
            fe = clasificar(T_e5_h, u, alcanzable)
            for q in np.arange(0.1, 0.91, 0.1):
                c = float(np.quantile(fa[alcanzable], q))
                sg, sf = alcanzable & (fe >= c), alcanzable & (fa >= c)
                sube, baja = ~sg & sf, sg & ~sf
                corte.append({
                    "ventana": v, "umbral": u, "cuantil_corte": round(float(q), 1),
                    "sec_sube": int(sube.sum()), "sec_baja": int(baja.sum()),
                    "bruto": int(sube.sum() + baja.sum()),
                    "neto": int(sube.sum() - baja.sum()),
                    "pct_pob_reclasificada": round(
                        100 * float(pob[sube | baja].sum()) / pob.sum(), 1)})

        # Bootstrap por dia sobre la representacion clave.
        dias = comun.get_level_values("date")
        udias = dias.unique()
        for u in UMBRALES:
            m = []
            for _ in range(N_BOOT):
                s = RNG.choice(udias, size=len(udias), replace=True)
                cols = np.concatenate([np.where(dias == d)[0] for d in s])
                r = comparar(clasificar(T_e5_h[:, cols], u, alcanzable),
                             clasificar(T_av[:, cols], u, alcanzable), alcanzable, pob)
                m.append(r["pct_pob_reclasificada"])
            lo, hi = np.percentile(m, [2.5, 97.5])
            filas.append({"ventana": v, "umbral": u, "representacion": "R4_bootstrap_ic",
                          "pct_pob_reclasificada": round(float(np.median(m)), 2),
                          "ic_lo": round(lo, 2), "ic_hi": round(hi, 2)})

    res = pd.DataFrame(filas)
    res.to_csv(TABLAS / "p2_comparacion_era5land.csv", index=False, encoding="utf-8")
    pd.DataFrame(prio).to_csv(TABLAS / "p2_priorizacion_era5land.csv",
                              index=False, encoding="utf-8")
    pd.DataFrame(disp).to_csv(TABLAS / "p2_dispersion_espacial.csv",
                              index=False, encoding="utf-8")
    pd.DataFrame(corte).to_csv(TABLAS / "p2_barrido_corte.csv",
                               index=False, encoding="utf-8")
    print("\n--- dispersion espacial de la fraccion servida ---")
    print(pd.DataFrame(disp).to_string(index=False))
    print("\n--- barrido del corte de elegibilidad (tarde, 30 C) ---")
    cc = pd.DataFrame(corte)
    print(cc[(cc.ventana == "tarde_16_18") & (cc.umbral == 30.0)].to_string(index=False))

    cols = ["ventana", "umbral", "representacion", "cobertura_dif_puntos",
            "sec_falsas_inaccesibles", "sec_falsas_accesibles", "sec_reclasificadas",
            "sec_balance_neto", "pct_pob_reclasificada", "pct_pob_balance_neto",
            "bidireccional"]
    print("\n--- comparacion frente al campo AVAMET ---")
    print(res[res["representacion"] != "R4_bootstrap_ic"][cols].to_string(index=False))
    print("\n--- bootstrap ---")
    print(res[res["representacion"] == "R4_bootstrap_ic"][
        ["ventana", "umbral", "pct_pob_reclasificada", "ic_lo", "ic_hi"]].to_string(index=False))
    print("\n--- priorizacion ---")
    print(pd.DataFrame(prio).to_string(index=False))


if __name__ == "__main__":
    main()
