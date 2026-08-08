#!/usr/bin/env python3
"""Robustez del enrutado: convergencia de la frontera y sensibilidad al presupuesto.

Dos comprobaciones que el texto necesitaba y no tenia.

**1. La frontera de Pareto es aproximada.** Se genera por barrido de sumas
ponderadas, y en un problema discreto la escalarizacion lineal recupera solo las
soluciones *soportadas*: puede perder puntos eficientes no soportados. El
problema exacto --minima exposicion sujeta a tiempo <= presupuesto-- es un
camino minimo con restriccion de recurso, NP-duro en general.

Dos consecuencias, y conviene decir las dos. La aproximacion es **conservadora**:
devuelve siempre una ruta factible, de modo que la exposicion reportada es una
cota superior de la optima y el ahorro por sombra que publicamos es una cota
inferior del alcanzable. Y su calidad se puede medir: aqui se compara la rejilla
de cinco pesos usada en el articulo contra una de veintiuno.

**2. El presupuesto de marcha.** Quince minutos determina que secciones son
alcanzables y, con ello, el universo sobre el que se define la dominancia de
restriccion. Se barre 10/15/20 minutos y 0,80/0,90/1,00 m/s.

Salidas en salidas/tablas/p5_*.csv
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, str(Path(__file__).resolve().parent))
import centros  # noqa: E402
from p3_rutas_sombra import DATOS, TABLAS, UTM, acumular, matriz  # noqa: E402

REJILLA_GRUESA = [0.0, 0.25, 0.5, 0.75, 1.0]
REJILLA_FINA = list(np.round(np.linspace(0.0, 1.0, 21), 3))
HORAS = [10, 12, 17]
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
    cs = centros.cargar(g.union_all())
    return G, e, g, cs


def rutas(G, e, t_arista, mapa, src, dst, s_arista, presupuesto, rejilla):
    mejor = np.full(len(dst), np.inf)
    rapida_t = None
    for lam in rejilla:
        M, _, _ = matriz(G, e, (1 - lam) * t_arista + lam * s_arista)
        _, pred, _ = dijkstra(M, directed=False, indices=src,
                              min_only=True, return_predecessors=True)
        tt, ss, _ = acumular(pred, set(src.tolist()), dst, t_arista, s_arista, mapa)
        if lam == 0.0:
            rapida_t = tt
        ok = tt <= presupuesto
        mejor = np.where(ok & (ss < mejor), ss, mejor)
    return rapida_t, mejor


def main() -> None:
    G, e, g, cs = preparar()
    pob = g["pob_65"].to_numpy()

    filas_conv, filas_sens = [], []
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
            for h in HORAS:
                s_arista = t_arista * (1.0 - e[f"{FECHA}_{h:02d}"].to_numpy())
                t_rap, sol_g = rutas(G, e, t_arista, mapa, src, dst, s_arista,
                                     pres, REJILLA_GRUESA)
                alc = t_rap <= pres
                filas_sens.append({
                    "velocidad_ms": vel, "presupuesto_min": pres, "hora": h,
                    "n_alcanzables": int(alc.sum()),
                    "pct_pob65_alcanzable": round(100 * float(pob[alc].sum() / pob.sum()), 2),
                    "sol_mediano_min": round(float(np.nanmedian(sol_g[alc])), 2),
                })

                # Convergencia solo en la configuracion del articulo, que es la
                # unica sobre la que se publican cifras.
                if vel == 0.90 and pres == 15.0:
                    _, sol_f = rutas(G, e, t_arista, mapa, src, dst, s_arista,
                                     pres, REJILLA_FINA)
                    d = sol_g[alc] - sol_f[alc]
                    filas_conv.append({
                        "hora": h, "n": int(alc.sum()),
                        "sol_rejilla_5": round(float(np.nanmedian(sol_g[alc])), 3),
                        "sol_rejilla_21": round(float(np.nanmedian(sol_f[alc])), 3),
                        "dif_media_min": round(float(np.nanmean(d)), 4),
                        "dif_max_min": round(float(np.nanmax(d)), 3),
                        "pct_secciones_que_mejoran": round(100 * float((d > 1e-6).mean()), 2),
                        "reduccion_relativa_pct": round(
                            100 * float(np.nanmean(d) / np.nanmedian(sol_g[alc])), 3),
                    })

    conv = pd.DataFrame(filas_conv)
    sens = pd.DataFrame(filas_sens)
    conv.to_csv(TABLAS / "p5_convergencia_pareto.csv", index=False, encoding="utf-8")
    sens.to_csv(TABLAS / "p5_sensibilidad_presupuesto.csv", index=False, encoding="utf-8")

    (TABLAS / "p5_resumen.json").write_text(json.dumps({
        "rejilla_articulo": REJILLA_GRUESA, "rejilla_control": REJILLA_FINA,
        "nota": ("la escalarizacion lineal recupera solo soluciones soportadas; "
                 "la exposicion reportada es cota superior de la optima y el "
                 "ahorro por sombra, cota inferior"),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print("--- convergencia de la frontera (0,9 m/s, 15 min) ---")
    print(conv.to_string(index=False))
    print("\n--- sensibilidad al presupuesto y la velocidad ---")
    print(sens.to_string(index=False))


if __name__ == "__main__":
    main()
