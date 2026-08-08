#!/usr/bin/env python3
"""Diseno factorial: representacion termica x sombra.

                        sin sombra    con sombra
    ERA5-Land corregido      A             C
    campo AVAMET             B             D

La pregunta que decide el articulo no es B - A, que ya sabemos que es grande,
sino **D - C**: la mejora que aporta la meteorologia local sigue existiendo
cuando la ruta ya conoce la sombra? Y la interaccion (D - C) - (B - A) dice si
la sombra refuerza la necesidad de datos locales, la reduce o la sustituye.

Las dos condiciones se aplican por separado y se combinan con un Y logico, sin
pesos entre grados centigrados y minutos de sol:

    termica  T_seccion(h) < umbral
    solar    minutos al sol de la ruta <= presupuesto

Ambos umbrales se barren; ninguno se elige a posteriori. ERA5-Land bruto queda
como diagnostico, no como escenario de politica, porque su sesgo calido domina
el agregado y enmascara lo que se quiere medir.

Salidas en salidas/tablas/p3_factorial_*.csv
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p2_comparar_era5land import (DATOS, TABLAS, UTM, campo_avamet,  # noqa: E402
                                  campo_era5)

VENTANAS = {"manana_10_12": [10, 11, 12], "tarde_16_18": [16, 17, 18]}
RUTAS_PARQUET = os.environ.get("RUTAS_PARQUET", "rutas_sombra.parquet")
SUFIJO = os.environ.get("SUFIJO_SALIDA", "")
UMBRALES_T = (28.0, 30.0, 32.0)
PRESUPUESTOS_SOL = (3.0, 5.0, 8.0)     # minutos al sol tolerados en el trayecto


def servida(T, umbral, sol_min, presupuesto, alcanzable, usar_sombra):
    """Fraccion de horas de la ventana en que la seccion esta atendida."""
    termica = (T < umbral).mean(axis=1)
    if not usar_sombra:
        return np.where(alcanzable, termica, 0.0)
    solar = (sol_min <= presupuesto).astype(float)
    return np.where(alcanzable, termica * solar, 0.0)


def priorizacion(frac, pob, alcanzable, cuantil=0.20):
    a = alcanzable
    n = max(int(cuantil * a.sum()), 1)
    score = pd.Series((pob * (1 - frac))[a])
    return set(score.nlargest(n).index)


def main() -> None:
    sec = pd.read_csv(TABLAS / "p4_secciones.csv", dtype={"CUSEC": str})
    g = gpd.read_file(f"zip://{DATOS / 'seccionado_2024.zip'}!SECC_CE_20240101.shp")
    g = g[g["CUSEC"].isin(sec["CUSEC"])].to_crs(UTM).merge(sec, on="CUSEC")
    g["distrito"] = g["CUSEC"].str[5:7]
    cent = g.geometry.centroid
    alcanzable = g["alcanzable"].to_numpy()
    pob = g["pob_65"].to_numpy()

    rutas = pd.read_parquet(DATOS / RUTAS_PARQUET)

    filas, prio_filas = [], []
    for v, horas in VENTANAS.items():
        print(f"\n== {v} ==")
        T_av, idx_av = campo_avamet(cent, horas)
        T_e5, idx_e5, _ = campo_era5(gpd.GeoSeries(cent, crs=UTM), horas)
        comun = idx_av.intersection(idx_e5)
        T_av = T_av[:, idx_av.get_indexer(comun)]
        T_e5 = T_e5[:, idx_e5.get_indexer(comun)]
        T_e5 = T_e5 + (np.nanmean(T_av) - np.nanmean(T_e5))   # corregido
        print(f"  {len(comun)} horas comunes")

        # Minutos al sol de la ventana: mediana de las horas que la componen,
        # en la ruta rapida (sin conciencia de sombra) y en la sombreada.
        r = rutas[rutas["hora"].isin(horas)]
        sol_rapida = (r.groupby("CUSEC")["sol_rapida_min"].mean()
                       .reindex(g["CUSEC"]).to_numpy())
        sol_sombreada = (r.groupby("CUSEC")["sol_sombreada_min"].mean()
                          .reindex(g["CUSEC"]).to_numpy())
        print(f"  minutos al sol: ruta rapida {np.nanmedian(sol_rapida[alcanzable]):.2f}, "
              f"ruta sombreada {np.nanmedian(sol_sombreada[alcanzable]):.2f}")

        for u in UMBRALES_T:
            for ps in PRESUPUESTOS_SOL:
                esc = {
                    "A_era5_sin_sombra": servida(T_e5, u, sol_rapida, ps, alcanzable, False),
                    "B_avamet_sin_sombra": servida(T_av, u, sol_rapida, ps, alcanzable, False),
                    "C_era5_con_sombra": servida(T_e5, u, sol_sombreada, ps, alcanzable, True),
                    "D_avamet_con_sombra": servida(T_av, u, sol_sombreada, ps, alcanzable, True),
                }
                cob = {k: float((f * pob).sum() / pob.sum()) for k, f in esc.items()}
                tops = {k: priorizacion(f, pob, alcanzable) for k, f in esc.items()}

                def jac(a, b):
                    return len(tops[a] & tops[b]) / len(tops[a] | tops[b])

                def repob(a, b):
                    d = tops[b] - tops[a]
                    return float(pd.Series(pob[alcanzable]).reindex(list(d)).sum())

                # Diagnostico de saturacion. Si casi ninguna seccion cumple la
                # condicion solar, todas quedan a cero pase lo que pase con la
                # temperatura, el 20 % peor lo llenan las que fallan al sol y el
                # Jaccard sale 1 sin que eso signifique nada. Es el mismo modo
                # de fallo que la saturacion por alcance, y hay que verlo en la
                # tabla y no descubrirlo despues.
                pasa_solar = float((sol_sombreada[alcanzable] <= ps).mean())

                filas.append({
                    "ventana": v, "umbral_c": u, "presupuesto_sol_min": ps,
                    "pct_cumplen_solar": round(100 * pasa_solar, 1),
                    "solar_saturada": bool(pasa_solar < 0.6),
                    **{f"cobertura_{k[0]}": round(100 * c, 2) for k, c in cob.items()},
                    # Efecto de la meteorologia local, sin y con sombra.
                    "efecto_met_sin_sombra_pp": round(100 * (cob["B_avamet_sin_sombra"]
                                                             - cob["A_era5_sin_sombra"]), 2),
                    "efecto_met_con_sombra_pp": round(100 * (cob["D_avamet_con_sombra"]
                                                             - cob["C_era5_con_sombra"]), 2),
                    # Efecto de anadir sombra, bajo cada representacion.
                    "efecto_sombra_era5_pp": round(100 * (cob["C_era5_con_sombra"]
                                                          - cob["A_era5_sin_sombra"]), 2),
                    "efecto_sombra_avamet_pp": round(100 * (cob["D_avamet_con_sombra"]
                                                            - cob["B_avamet_sin_sombra"]), 2),
                    "interaccion_pp": round(100 * ((cob["D_avamet_con_sombra"] - cob["C_era5_con_sombra"])
                                                   - (cob["B_avamet_sin_sombra"] - cob["A_era5_sin_sombra"])), 2),
                    # Priorizacion.
                    "jaccard_met_sin_sombra": round(jac("A_era5_sin_sombra", "B_avamet_sin_sombra"), 3),
                    "jaccard_met_con_sombra": round(jac("C_era5_con_sombra", "D_avamet_con_sombra"), 3),
                    "jaccard_sombra_en_avamet": round(jac("B_avamet_sin_sombra", "D_avamet_con_sombra"), 3),
                    "pob65_recl_met_sin_sombra": round(repob("A_era5_sin_sombra", "B_avamet_sin_sombra")),
                    "pob65_recl_met_con_sombra": round(repob("C_era5_con_sombra", "D_avamet_con_sombra")),
                    "pob65_recl_sombra": round(repob("B_avamet_sin_sombra", "D_avamet_con_sombra")),
                })

    res = pd.DataFrame(filas)
    res.to_csv(TABLAS / f"p3_factorial{SUFIJO}.csv", index=False, encoding="utf-8")

    print("\n--- efectos sobre la cobertura (puntos porcentuales) ---")
    print(res[["ventana", "umbral_c", "presupuesto_sol_min",
               "efecto_met_sin_sombra_pp", "efecto_met_con_sombra_pp",
               "efecto_sombra_era5_pp", "efecto_sombra_avamet_pp",
               "interaccion_pp"]].to_string(index=False))
    print("\n--- estabilidad de la priorizacion ---")
    print(res[["ventana", "umbral_c", "presupuesto_sol_min", "pct_cumplen_solar",
               "solar_saturada", "jaccard_met_sin_sombra", "jaccard_met_con_sombra",
               "pob65_recl_met_sin_sombra", "pob65_recl_met_con_sombra",
               "pob65_recl_sombra"]].to_string(index=False))
    lim = res[~res["solar_saturada"]]
    print("\n--- solo configuraciones NO saturadas (la comparacion informativa) ---")
    print(lim[["ventana", "umbral_c", "presupuesto_sol_min", "pct_cumplen_solar",
               "jaccard_met_sin_sombra", "jaccard_met_con_sombra",
               "pob65_recl_met_sin_sombra", "pob65_recl_met_con_sombra"]].to_string(index=False))

    (TABLAS / f"p3_factorial_resumen{SUFIJO}.json").write_text(json.dumps({
        "escenarios": {"A": "ERA5-Land corregido, sin sombra",
                       "B": "campo AVAMET, sin sombra",
                       "C": "ERA5-Land corregido, con sombra",
                       "D": "campo AVAMET, con sombra"},
        "umbrales_c": list(UMBRALES_T),
        "presupuestos_sol_min": list(PRESUPUESTOS_SOL),
        "nota": ("la geometria solar de ruteo es la del 15 de julio; la variacion "
                 "de elevacion a la misma hora entre junio y agosto es de unos 8 grados"),
    }, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
