#!/usr/bin/env python3
"""Sensibilidad del bootstrap: bloques moviles frente a dias sueltos.

El bootstrap principal remuestrea **jornadas completas**, lo que preserva el
ciclo diurno pero trata cada dia como independiente. Una ola de calor no lo es:
dura varios dias y los correlaciona. Remuestrear dias sueltos rompe esa
dependencia y, en general, **estrecha** los intervalos --se genera diversidad
sintetica que el clima real no ofrece--.

Aqui se repite el calculo con bloques moviles de L dias consecutivos, L = 3 y 7,
que es el orden de duracion de un episodio calido. Los bloques se muestrean
**dentro de cada verano**: un bloque a caballo entre dos agostos separados por
un ano no es continuidad temporal, es un artefacto del indexado.

No sustituye al bootstrap principal. Sirve para comprobar que la conclusion de
la Figura 5 --la representacion regional corregida con sombra completa retiene
casi todo el beneficio alcanzable-- no depende de la estructura de remuestreo.

Salida en salidas/tablas/p4f_bootstrap_bloques.csv
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p2_comparar_era5land import DATOS, TABLAS, UTM, campo_avamet, campo_era5  # noqa: E402
from p4c_regret import PHI_REF, PRESUPUESTOS_K, UMBRAL_T, fraccion_expuesta  # noqa: E402
from p4d_regret_bootstrap import REF, VENTANAS, seleccion  # noqa: E402

N_BOOT = 1000
BLOQUES = [1, 3, 7]  # L = 1 reproduce el bootstrap principal, como control
RNG = np.random.default_rng(20260808)


def muestrear_bloques(udias, L, rng):
    """Dias remuestreados por bloques moviles de longitud L, dentro de cada verano."""
    if L == 1:
        return rng.choice(udias, size=len(udias), replace=True)
    anos = pd.DatetimeIndex(udias).year
    fuera = []
    for a in np.unique(anos):
        d = np.sort(udias[anos == a])
        n = len(d)
        if n <= L:
            fuera.append(d)
            continue
        # Bloques dentro del verano; se toman los necesarios y se recorta a n.
        inicios = rng.integers(0, n - L + 1, size=int(np.ceil(n / L)))
        fuera.append(np.concatenate([d[i:i + L] for i in inicios])[:n])
    return np.concatenate(fuera)


def main() -> None:
    sec = pd.read_csv(TABLAS / "p4_secciones.csv", dtype={"CUSEC": str})
    g = gpd.read_file(f"zip://{DATOS / 'seccionado_2024.zip'}!SECC_CE_20240101.shp")
    g = g[g["CUSEC"].isin(sec["CUSEC"])].to_crs(UTM).merge(sec, on="CUSEC")
    alc = g["alcanzable"].to_numpy()
    idx_alc = np.where(alc)[0]
    pob = g["pob_65"].to_numpy()
    cusec = g["CUSEC"]

    r_ed = pd.read_parquet(DATOS / "rutas_sombra.parquet")
    r_vg = pd.read_parquet(DATOS / "rutas_sombra_veg.parquet")

    filas = []
    for v, horas in VENTANAS.items():
        T_av, ia = campo_avamet(g.geometry.centroid, horas)
        T_e5, ie, _ = campo_era5(gpd.GeoSeries(g.geometry.centroid, crs=UTM), horas)
        com = ia.intersection(ie)
        T_av, T_e5 = T_av[:, ia.get_indexer(com)], T_e5[:, ie.get_indexer(com)]
        T_e5 = T_e5 + (np.nanmean(T_av) - np.nanmean(T_e5))
        dias = pd.DatetimeIndex(com.get_level_values("date"))
        udias = dias.unique().to_numpy()

        s_ed = (fraccion_expuesta(r_ed, horas, cusec) <= PHI_REF).astype(float)
        s_vg = (fraccion_expuesta(r_vg, horas, cusec) <= PHI_REF).astype(float)
        uno = np.ones(len(g))
        reps = {"R1_era5_sin_sombra": (T_e5, uno),
                "R2_era5_sombra_completa": (T_e5, s_vg),
                "R3_local_sin_sombra": (T_av, uno),
                "R4_local_sombra_edificios": (T_av, s_ed),
                REF: (T_av, s_vg)}
        por_dia = {d: np.where(dias == d)[0] for d in udias}

        for L in BLOQUES:
            ef = {k: {r: [] for r in reps} for k in PRESUPUESTOS_K}
            for _ in range(N_BOOT):
                s = muestrear_bloques(udias, L, RNG)
                cols = np.concatenate([por_dia[d] for d in s])
                fr = {r: np.where(alc, (T[:, cols] < UMBRAL_T).mean(axis=1) * sol, 0.0)
                      for r, (T, sol) in reps.items()}
                carga = np.where(alc, pob * (1 - fr[REF]), 0.0)
                for k in PRESUPUESTOS_K:
                    cupo = max(int(k * len(idx_alc)), 1)
                    b_ref = float(carga[seleccion(fr[REF], pob, idx_alc, cupo)].sum())
                    for r in reps:
                        b = float(carga[seleccion(fr[r], pob, idx_alc, cupo)].sum())
                        ef[k][r].append(100 * b / b_ref if b_ref > 0 else np.nan)

            for k in PRESUPUESTOS_K:
                for r in reps:
                    x = np.asarray(ef[k][r])
                    lo, hi = np.nanpercentile(x, [2.5, 97.5])
                    filas.append({
                        "ventana": v, "bloque_dias": L, "k_pct": int(100 * k),
                        "representacion": r,
                        "eficiencia_pct": round(float(np.nanmedian(x)), 2),
                        "ic_lo": round(float(lo), 2), "ic_hi": round(float(hi), 2),
                        "amplitud_ic": round(float(hi - lo), 2),
                    })

    d = pd.DataFrame(filas)
    d.to_csv(TABLAS / "p4f_bootstrap_bloques.csv", index=False, encoding="utf-8")

    # Lo que hay que mirar: cuanto se ensancha el intervalo y si la mediana se mueve.
    piv = d.pivot_table(index=["ventana", "k_pct", "representacion"],
                        columns="bloque_dias",
                        values=["eficiencia_pct", "amplitud_ic"])
    ratio = (piv[("amplitud_ic", 7)] / piv[("amplitud_ic", 1)]).replace([np.inf], np.nan)
    desv = (piv[("eficiencia_pct", 7)] - piv[("eficiencia_pct", 1)]).abs()

    resumen = {
        "n_boot": N_BOOT, "bloques_dias": BLOQUES,
        "ensanchamiento_ic_L7_sobre_L1": {
            "mediana": round(float(ratio.median()), 3),
            "maximo": round(float(ratio.max()), 3),
        },
        "desplazamiento_eficiencia_pp": {
            "mediana": round(float(desv.median()), 3),
            "maximo": round(float(desv.max()), 3),
        },
    }
    (TABLAS / "p4f_resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

    print("--- eficiencia por longitud de bloque ---")
    print(d[d["k_pct"] == 15].to_string(index=False))
    print("\n--- resumen ---")
    print(json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
