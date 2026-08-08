#!/usr/bin/env python3
"""Regimen de dominancia bajo los nueve presupuestos de marcha.

La sensibilidad de S5 mostraba que el presupuesto cambia el universo del
problema --de 201 a 561 secciones alcanzables, del 33,6 al 94,7 % de la
poblacion 65+-- pero solo reportaba alcance y exposicion. Falta lo que sostiene
el cuarto claim: **a que capacidad k cambia el regimen**.

Importa porque los dos terminos de la frontera de dominancia se mueven en el
mismo sentido. Ampliar el presupuesto alcanza mas secciones, lo que aumenta el
cupo `kN`; pero tambien deja llegar a secciones peor conectadas y mas
expuestas, lo que aumenta `N_fallo`. Cual gana no se puede razonar de cabeza:
hay que calcularlo.

Se usa la rejilla de veintiun pesos de produccion, no la gruesa, porque la
fraccion expuesta de la ruta es exactamente la magnitud que la rejilla gruesa
sobreestimaba.

Salida en salidas/tablas/p5b_dominancia_presupuesto.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, str(Path(__file__).resolve().parent))
import centros  # noqa: E402
from p3_rutas_sombra import DATOS, LAMBDAS, TABLAS, UTM, acumular, matriz  # noqa: E402
from p4c_regret import PHI_REF, PRESUPUESTOS_K  # noqa: E402

VENTANAS = {"manana_10_12": [10, 11, 12], "tarde_16_18": [16, 17, 18]}
FECHA = "07-15"
PRESUPUESTOS = [10.0, 15.0, 20.0]
VELOCIDADES = [0.80, 0.90, 1.00]


def preparar():
    G = ox.load_graphml(DATOS / "red_peatonal_valencia.graphml")
    e = ox.graph_to_gdfs(G, nodes=False).to_crs(UTM).reset_index()
    e["arista"] = np.arange(len(e))
    vg = pd.read_parquet(DATOS / "sombra_aristas_veg.parquet")
    e = e.merge(vg, left_on="arista", right_index=True, how="left")
    for c in vg.columns:
        e[c] = e[c].fillna(0.0)

    sec = pd.read_csv(TABLAS / "p4_secciones.csv", dtype={"CUSEC": str})
    g = gpd.read_file(f"zip://{DATOS / 'seccionado_2024.zip'}!SECC_CE_20240101.shp")
    g = g[g["CUSEC"].isin(sec["CUSEC"])].to_crs(UTM).merge(sec, on="CUSEC")
    return G, e, g, centros.cargar(g.union_all())


def frontera(G, e, t_arista, mapa, src, dst, s_arista, presupuesto):
    """Devuelve tiempo de la ruta rapida y (tiempo, exposicion) de la menos expuesta."""
    mejor_s = np.full(len(dst), np.inf)
    mejor_t = np.full(len(dst), np.nan)
    rapida_t = None
    for lam in LAMBDAS:
        M, _, _ = matriz(G, e, (1 - lam) * t_arista + lam * s_arista)
        _, pred, _ = dijkstra(M, directed=False, indices=src,
                              min_only=True, return_predecessors=True)
        tt, ss, _ = acumular(pred, set(src.tolist()), dst, t_arista, s_arista, mapa)
        if lam == 0.0:
            rapida_t = tt
        gana = (tt <= presupuesto) & (ss < mejor_s)
        mejor_t = np.where(gana, tt, mejor_t)
        mejor_s = np.where(gana, ss, mejor_s)
    return rapida_t, mejor_t, mejor_s


def main() -> None:
    G, e, g, cs = preparar()
    pob = g["pob_65"].to_numpy()

    filas = []
    for vel in VELOCIDADES:
        t_arista = (e["length"] / vel / 60).to_numpy()
        _, nodos, idx = matriz(G, e, t_arista)
        mapa = {}
        for a, (uu, vv) in enumerate(zip(e["u"].map(idx), e["v"].map(idx))):
            mapa[(min(uu, vv), max(uu, vv))] = a
        src = np.unique([idx[n] for n in ox.nearest_nodes(G, cs["lon"].values,
                                                          cs["lat"].values)])
        cll = g.geometry.centroid.to_crs("EPSG:4326")
        dst = np.array([idx[n] for n in ox.nearest_nodes(G, cll.x.values, cll.y.values)])

        for pres in PRESUPUESTOS:
            for v, horas in VENTANAS.items():
                # Fraccion expuesta media de la ventana, como en el analisis principal.
                fr_h = []
                alc = None
                for h in horas:
                    s_arista = t_arista * (1.0 - e[f"{FECHA}_{h:02d}"].to_numpy())
                    t_rap, t_mej, s_mej = frontera(G, e, t_arista, mapa, src, dst,
                                                   s_arista, pres)
                    alc = t_rap <= pres if alc is None else alc & (t_rap <= pres)
                    with np.errstate(invalid="ignore", divide="ignore"):
                        fr_h.append(np.where(t_mej > 0, s_mej / t_mej, np.nan))
                frac = np.nanmean(np.vstack(fr_h), axis=0)

                ia = np.where(alc)[0]
                n_falla = int((frac[ia] > PHI_REF).sum())
                for k in PRESUPUESTOS_K:
                    cupo = max(int(k * len(ia)), 1)
                    regimen = ("dominada_por_sol" if n_falla >= cupo else
                               "mixta" if n_falla >= 0.5 * cupo else
                               "sensible_a_termica")
                    filas.append({
                        "velocidad_ms": vel, "presupuesto_min": pres, "ventana": v,
                        "n_alcanzables": len(ia),
                        "pct_pob65_alcanzable": round(
                            100 * float(pob[ia].sum() / pob.sum()), 1),
                        "k_pct": int(100 * k), "cupo": cupo,
                        "n_incumplen_solar": n_falla,
                        "cociente_falla_cupo": round(n_falla / cupo, 2),
                        "regimen": regimen,
                    })

    d = pd.DataFrame(filas)
    d.to_csv(TABLAS / "p5b_dominancia_presupuesto.csv", index=False, encoding="utf-8")

    print("--- regimen de dominancia por presupuesto y velocidad ---")
    print(d.to_string(index=False))

    print("\n--- k de transicion (primer k en cada regimen) ---")
    for (vel, pres, v), sub in d.groupby(["velocidad_ms", "presupuesto_min", "ventana"]):
        t = {r: sub[sub["regimen"] == r]["k_pct"].min() for r in
             ("dominada_por_sol", "mixta", "sensible_a_termica")}
        print(f"{vel:.2f} m/s  {pres:4.0f} min  {v:14s} "
              f"n={sub['n_alcanzables'].iloc[0]:3d}  "
              f"sol<=k{t['dominada_por_sol']}  mixta>=k{t['mixta']}  "
              f"termica>=k{t['sensible_a_termica']}")


if __name__ == "__main__":
    main()
