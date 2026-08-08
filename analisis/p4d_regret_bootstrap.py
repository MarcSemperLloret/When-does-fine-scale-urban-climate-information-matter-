#!/usr/bin/env python3
"""Regret con intervalos, eficiencia, y dominancia de restriccion.

Tres correcciones sobre el analisis anterior.

**1. R5 no es la verdad.** Es la representacion de mayor informacion disponible,
y arrastra sus propios errores: seis estaciones, interpolacion, transmitancia
supuesta, exposicion solar geometrica, incertidumbre del nDSM. El regret se
define por tanto respecto a la **referencia de informacion completa**, no
respecto a la realidad, y se nombra asi en todas las salidas.

**2. "R3 es peor que R1" hay que demostrarlo o retirarlo.** Se remuestrean dias
completos con reposicion y se da intervalo del 95 % para cada regret y para la
diferencia emparejada R3 - R1. Si el intervalo cruza cero, la afirmacion se
sustituye por "no se encontro evidencia de que mejorar solo la meteorologia
aporte utilidad cuando se omite la sombra".

**3. Dominancia de restriccion.** Cuando el numero de secciones que incumplen la
condicion solar iguala o supera el cupo `k*N`, toda la capacidad de priorizacion
se consume antes de que la condicion termica entre en juego, y el termino
termico queda **no identificable para la decision**. No es un defecto del
analisis: es una propiedad de la regla de politica, y merece nombre y figura.

Se anade ademas la **eficiencia** `B(S_r)/B(S_ref)`, que dice lo mismo que el
regret pero se comunica mejor: "retiene el 96,5 % del beneficio alcanzable".

Nota de lenguaje: `k` es **capacidad de priorizacion** --cuantas secciones puede
un ayuntamiento seleccionar para evaluacion detallada o intervencion-- y no un
presupuesto de obra. El calculo no supone que priorizar una seccion elimine su
carga termica.

Salidas en salidas/tablas/p4d_*.csv
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

VENTANAS = {"manana_10_12": [10, 11, 12], "tarde_16_18": [16, 17, 18]}
N_BOOT = 400
RNG = np.random.default_rng(20260807)

NOMBRES = {
    "R1_era5_sin_sombra": "ERA5 corregido, sin sombra",
    "R2_era5_sombra_completa": "ERA5 corregido + sombra completa",
    "R3_local_sin_sombra": "meteorologia local, sin sombra",
    "R4_local_sombra_edificios": "local + sombra de edificios",
    "R5_local_sombra_completa": "referencia de informacion completa",
}
REF = "R5_local_sombra_completa"


def seleccion(frac, pob, idx_alc, n):
    orden = np.argsort(-(pob[idx_alc] * (1 - frac[idx_alc])))
    return idx_alc[orden[:n]]


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

    filas, dominancia, dif_pares = [], [], []
    for v, horas in VENTANAS.items():
        T_av, ia = campo_avamet(g.geometry.centroid, horas)
        T_e5, ie, _ = campo_era5(gpd.GeoSeries(g.geometry.centroid, crs=UTM), horas)
        com = ia.intersection(ie)
        T_av, T_e5 = T_av[:, ia.get_indexer(com)], T_e5[:, ie.get_indexer(com)]
        T_e5 = T_e5 + (np.nanmean(T_av) - np.nanmean(T_e5))
        dias = pd.DatetimeIndex(com.get_level_values("date"))
        udias = dias.unique()

        s_ed = (fraccion_expuesta(r_ed, horas, cusec) <= PHI_REF).astype(float)
        s_vg = (fraccion_expuesta(r_vg, horas, cusec) <= PHI_REF).astype(float)
        uno = np.ones(len(g))
        reps = {"R1_era5_sin_sombra": (T_e5, uno),
                "R2_era5_sombra_completa": (T_e5, s_vg),
                "R3_local_sin_sombra": (T_av, uno),
                "R4_local_sombra_edificios": (T_av, s_ed),
                REF: (T_av, s_vg)}

        # ------------------------------------------- dominancia de restriccion
        n_falla = int((s_vg[idx_alc] == 0).sum())
        for k in PRESUPUESTOS_K:
            cupo = max(int(k * len(idx_alc)), 1)
            regimen = ("dominada_por_sol" if n_falla >= cupo else
                       "mixta" if n_falla >= 0.5 * cupo else "sensible_a_termica")
            dominancia.append({"ventana": v, "k_pct": int(100 * k), "cupo": cupo,
                               "n_incumplen_solar": n_falla,
                               "cociente_falla_cupo": round(n_falla / cupo, 2),
                               "regimen": regimen})

        # ------------------------------------------------------- bootstrap
        muestras = {k: {r: [] for r in reps} for k in PRESUPUESTOS_K}
        eficiencias = {k: {r: [] for r in reps} for k in PRESUPUESTOS_K}
        for _ in range(N_BOOT):
            s = RNG.choice(udias, size=len(udias), replace=True)
            cols = np.concatenate([np.where(dias == d)[0] for d in s])
            fr = {r: np.where(alc, (T[:, cols] < UMBRAL_T).mean(axis=1) * sol, 0.0)
                  for r, (T, sol) in reps.items()}
            carga = np.where(alc, pob * (1 - fr[REF]), 0.0)
            for k in PRESUPUESTOS_K:
                cupo = max(int(k * len(idx_alc)), 1)
                b_ref = float(carga[seleccion(fr[REF], pob, idx_alc, cupo)].sum())
                for r in reps:
                    b = float(carga[seleccion(fr[r], pob, idx_alc, cupo)].sum())
                    muestras[k][r].append(100 * (b_ref - b) / b_ref if b_ref > 0 else np.nan)
                    eficiencias[k][r].append(100 * b / b_ref if b_ref > 0 else np.nan)

        for k in PRESUPUESTOS_K:
            for r in reps:
                m = np.asarray(muestras[k][r])
                ef = np.asarray(eficiencias[k][r])
                lo, hi = np.nanpercentile(m, [2.5, 97.5])
                filas.append({
                    "ventana": v, "k_pct": int(100 * k), "representacion": r,
                    "descripcion": NOMBRES[r],
                    "regret_pct": round(float(np.nanmedian(m)), 2),
                    "regret_ic_lo": round(float(lo), 2),
                    "regret_ic_hi": round(float(hi), 2),
                    "eficiencia_pct": round(float(np.nanmedian(ef)), 2),
                    "eficiencia_ic_lo": round(float(np.nanpercentile(ef, 2.5)), 2),
                    "eficiencia_ic_hi": round(float(np.nanpercentile(ef, 97.5)), 2),
                })
            # Diferencia emparejada R3 - R1: la afirmacion que hay que probar.
            d = np.asarray(muestras[k]["R3_local_sin_sombra"]) - \
                np.asarray(muestras[k]["R1_era5_sin_sombra"])
            lo, hi = np.nanpercentile(d, [2.5, 97.5])
            dif_pares.append({
                "ventana": v, "k_pct": int(100 * k),
                "dif_R3_menos_R1_pp": round(float(np.nanmedian(d)), 2),
                "ic_lo": round(float(lo), 2), "ic_hi": round(float(hi), 2),
                "distinguible_de_cero": bool(lo > 0 or hi < 0),
            })

    res = pd.DataFrame(filas)
    res.to_csv(TABLAS / "p4d_regret_ic.csv", index=False, encoding="utf-8")
    dom = pd.DataFrame(dominancia).drop_duplicates()
    dom.to_csv(TABLAS / "p4d_dominancia_restriccion.csv", index=False, encoding="utf-8")
    dif = pd.DataFrame(dif_pares)
    dif.to_csv(TABLAS / "p4d_diferencia_R3_R1.csv", index=False, encoding="utf-8")

    (TABLAS / "p4d_resumen.json").write_text(json.dumps({
        "referencia": "R5 = representacion de mayor informacion disponible, NO la realidad",
        "k": "capacidad de priorizacion (secciones seleccionables para evaluacion "
             "detallada o intervencion), no presupuesto de obra",
        "n_boot": N_BOOT, "phi_ref": PHI_REF, "umbral_c": UMBRAL_T,
        "dominancia": ("si n_incumplen_solar >= cupo, el termino termico es no "
                       "identificable para la decision"),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print("--- regret y eficiencia, con IC 95 % por bootstrap de dias ---")
    print(res[["ventana", "k_pct", "representacion", "regret_pct", "regret_ic_lo",
               "regret_ic_hi", "eficiencia_pct"]].to_string(index=False))
    print("\n--- dominancia de restriccion ---")
    print(dom.to_string(index=False))
    print("\n--- diferencia emparejada R3 - R1 (positivo = R3 peor) ---")
    print(dif.to_string(index=False))


if __name__ == "__main__":
    main()
