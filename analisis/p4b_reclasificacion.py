#!/usr/bin/env python3
"""Descomposicion bidireccional de la reclasificacion, y curva de umbral.

Corrige un error del primer informe. Alli se atribuyo el pequeno cambio de
cobertura agregada a que "sustituir un campo por su mediana conserva el
promedio". **Eso es falso**: la mediana no conserva la media. Lo que ocurre es
una cancelacion entre dos flujos de signo contrario:

    cambio neto  = P(0->1) - P(1->0)
    reclasificacion bruta = P(0->1) + P(1->0)

y el neto puede ser casi nulo con un bruto grande. Este script separa los dos
flujos, que es lo que convierte un resultado aparentemente pequeno en un
problema de compensacion espacial oculta.

Anade ademas la curva continua de umbral, para que 30 y 32 C dejen de parecer
elegidos despues de mirar los datos, y un indice de fragilidad que intenta
predecir la reclasificacion a partir de cuanta masa de probabilidad hay cerca
del umbral.

Salidas en salidas/tablas/p4b_*.csv
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos"
TABLAS = BASE / "salidas" / "tablas"

PRESUPUESTO = 15.0
V_MAYOR = 0.90
VENTANAS = {"manana_10_12": [10, 11, 12], "tarde_16_18": [16, 17, 18]}
BARRIOS = ["c15m250e30", "c15m250e15", "c15m250e24",
           "c15m250e11", "c15m250e26", "c15m250e08"]
UMBRALES = np.arange(28.0, 34.01, 0.5)

RNG = np.random.default_rng(20260806)
N_BOOT = 500


def campo_termico(cent_x, cent_y, ventana_horas):
    """Igual que en el piloto: ponderacion inversa desde las seis estaciones."""
    import geopandas as gpd

    df = pd.read_parquet(DATOS / "valencia_verano_qc.parquet")
    df = df[df["station_id"].isin(BARRIOS)].copy()
    df["hora"] = df["observed_local"].dt.hour
    hor = (df.groupby(["station_id", "date", "hora"], observed=True)["t_qc"]
             .mean().reset_index())
    est = df.groupby("station_id")[["latitude", "longitude"]].first()
    ge = gpd.GeoDataFrame(est, geometry=gpd.points_from_xy(est["longitude"], est["latitude"]),
                          crs="EPSG:4326").to_crs("EPSG:25830")

    d = np.sqrt((cent_x[:, None] - ge.geometry.x.values[None, :]) ** 2
                + (cent_y[:, None] - ge.geometry.y.values[None, :]) ** 2)
    w = 1.0 / np.maximum(d, 50.0) ** 2
    w /= w.sum(axis=1, keepdims=True)

    piv = (hor[hor["hora"].isin(ventana_horas)]
           .pivot_table(index=["date", "hora"], columns="station_id", values="t_qc")
           .dropna()[list(ge.index)])
    return w @ piv.to_numpy().T, piv.index


def flujos(T_gruesa, T_fina, umbral, alcanzable, pob):
    """Reclasificacion en las dos direcciones, ponderada por poblacion.

    Una seccion-hora esta "servida" si es alcanzable y esta por debajo del
    umbral. Se compara la clasificacion que da cada representacion sobre la
    fraccion de horas servidas, con corte en la mediana de las alcanzables.
    """
    fg = (T_gruesa < umbral).mean(axis=1)
    ff = (T_fina < umbral).mean(axis=1)
    corte = np.median(ff[alcanzable])

    serv_g = alcanzable & (fg >= corte)
    serv_f = alcanzable & (ff >= corte)

    sube = ~serv_g & serv_f      # la gruesa la daba mal, la fina bien
    baja = serv_g & ~serv_f      # la gruesa la daba bien, la fina mal
    return {
        "corte_frac": float(corte),
        "sec_no_a_si": int(sube.sum()),
        "sec_si_a_no": int(baja.sum()),
        "sec_reclasificadas": int(sube.sum() + baja.sum()),
        "sec_balance_neto": int(sube.sum() - baja.sum()),
        "pob_no_a_si": float(pob[sube].sum()),
        "pob_si_a_no": float(pob[baja].sum()),
        "pob_reclasificada": float(pob[sube].sum() + pob[baja].sum()),
        "pob_balance_neto": float(pob[sube].sum() - pob[baja].sum()),
    }


def main() -> None:
    sec = pd.read_csv(TABLAS / "p4_secciones.csv", dtype={"CUSEC": str})
    import geopandas as gpd
    g = gpd.read_file(f"zip://{DATOS / 'seccionado_2024.zip'}!SECC_CE_20240101.shp")
    g = g[g["CUSEC"].isin(sec["CUSEC"])].to_crs("EPSG:25830").merge(sec, on="CUSEC")
    cent = g.geometry.centroid
    alcanzable = g["alcanzable"].to_numpy()
    pob65 = g["pob_65"].to_numpy()
    total65 = pob65.sum()
    n_total, n_alcanz = len(g), int(alcanzable.sum())

    filas, curva = [], []
    for v, horas in VENTANAS.items():
        T, idx = campo_termico(cent.x.values, cent.y.values, horas)
        T_uni = np.tile(np.median(T, axis=0), (len(g), 1))

        for u in UMBRALES:
            f = flujos(T_uni, T, u, alcanzable, pob65)
            f.update(ventana=v, umbral=round(float(u), 1))
            # Fragilidad: cuanta masa de observaciones cae a menos de la
            # discrepancia local del umbral. Si esto predice la reclasificacion,
            # el mecanismo es generalizable y no un accidente de Valencia.
            delta = np.abs(T - T_uni)
            f["fragilidad"] = float((np.abs(T - u) <= delta).mean())
            f["pct_pob_reclasificada"] = round(100 * f["pob_reclasificada"] / total65, 2)
            f["pct_pob_balance_neto"] = round(100 * f["pob_balance_neto"] / total65, 2)
            f["pct_sec_de_alcanzables"] = round(100 * f["sec_reclasificadas"] / n_alcanz, 2)
            f["pct_sec_de_totales"] = round(100 * f["sec_reclasificadas"] / n_total, 2)
            curva.append(f)

        # Bootstrap por dia sobre los umbrales principales.
        dias = pd.Index(idx.get_level_values(0))
        for u in (30.0, 32.0):
            muestras = []
            udias = dias.unique()
            for _ in range(N_BOOT):
                sel = RNG.choice(udias, size=len(udias), replace=True)
                cols = np.concatenate([np.where(dias == d)[0] for d in sel])
                Tb, Tub = T[:, cols], T_uni[:, cols]
                muestras.append(flujos(Tb, Tub, u, alcanzable, pob65)["pob_reclasificada"])
            lo, hi = np.percentile(muestras, [2.5, 97.5])
            filas.append({"ventana": v, "umbral": u,
                          "pob_reclasificada_ic_lo": round(100 * lo / total65, 2),
                          "pob_reclasificada_ic_hi": round(100 * hi / total65, 2)})

    cur = pd.DataFrame(curva)
    cur.to_csv(TABLAS / "p4b_curva_umbral.csv", index=False, encoding="utf-8")
    pd.DataFrame(filas).to_csv(TABLAS / "p4b_bootstrap.csv", index=False, encoding="utf-8")

    # Correlacion entre fragilidad y reclasificacion observada.
    rho = cur.groupby("ventana").apply(
        lambda d: d["fragilidad"].corr(d["pct_pob_reclasificada"], method="spearman"),
        include_groups=False)

    (TABLAS / "p4b_resumen.json").write_text(json.dumps({
        "n_secciones_totales": n_total,
        "n_secciones_alcanzables": n_alcanz,
        "poblacion_65_total": round(float(total65)),
        "spearman_fragilidad_vs_reclasificacion": rho.round(3).to_dict(),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print("--- descomposicion bidireccional (umbral 30 y 32 C) ---")
    cols = ["ventana", "umbral", "sec_no_a_si", "sec_si_a_no", "sec_reclasificadas",
            "sec_balance_neto", "pob_no_a_si", "pob_si_a_no", "pob_reclasificada",
            "pob_balance_neto", "pct_pob_reclasificada", "pct_pob_balance_neto",
            "pct_sec_de_alcanzables", "pct_sec_de_totales"]
    print(cur[cur["umbral"].isin([30.0, 32.0])][cols].round(1).to_string(index=False))
    print("\n--- bootstrap por dia ---")
    print(pd.DataFrame(filas).to_string(index=False))
    print("\n--- fragilidad vs reclasificacion (Spearman) ---")
    print(rho.round(3).to_string())


if __name__ == "__main__":
    main()
