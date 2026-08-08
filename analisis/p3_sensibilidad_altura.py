#!/usr/bin/env python3
"""Sensibilidad del factorial al supuesto de altura de los edificios.

La altura sale de `3,0 m/planta + 1,0 m`. El contraste con OpenStreetMap deja
ese supuesto en pie --la mediana de metros por planta entre los edificios que
llevan altura y plantas en OSM es exactamente 3,00-- pero el recuento de
plantas solo coincide con OSM dentro de +-1 planta, y el sesgo aparente cambia
de signo segun como se empareje, de modo que no es identificable.

Una planta son tres metros: sobre una mediana de trece, eso es un +-23 %. Aqui
se rehace la cadena completa --sombra, rutas, factorial-- con la altura
multiplicada por 0,8 y por 1,2, y se compara lo unico que importa: si cambian
las conclusiones de priorizacion.

Salida: salidas/tablas/p3_sensibilidad_altura.csv
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parent))
import centros  # noqa: E402
from p2_comparar_era5land import campo_avamet, campo_era5  # noqa: E402
from p3_rutas_sombra import (LAMBDAS, PRESUPUESTO_MIN, PRIMARIA,  # noqa: E402
                             V_MAYOR, acumular, matriz)
from p3_sombra_edificios import (HORAS, PASO_MUESTREO_M, muestrear_red,  # noqa: E402
                                 posiciones_solares, rasterizar_alturas, sombra)

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos"
TABLAS = BASE / "salidas" / "tablas"
UTM = "EPSG:25830"

FACTORES = [0.8, 1.0, 1.2]
FECHA = "07-15"
# Solo las configuraciones no saturadas del factorial: presupuesto de 8 minutos
# de sol y umbral de 30 C. Repetir toda la rejilla triplicaria el coste sin
# anadir nada, porque las saturadas no informan.
UMBRAL_T, PRESUPUESTO_SOL = 30.0, 8.0
VENTANAS = {"manana_10_12": [10, 11, 12], "tarde_16_18": [16, 17, 18]}


def main() -> None:
    print("preparacion")
    sol = posiciones_solares()
    sol = sol[sol["fecha"] == FECHA]
    aristas, puntos, idx_arista = muestrear_red()
    ed = gpd.read_file(DATOS / "edificios_valencia.gpkg", layer="edificios")
    x0, y0 = puntos.min(axis=0) - 500
    x1, y1 = puntos.max(axis=0) + 500
    ed = ed[ed.intersects(box(x0, y0, x1, y1))]

    sec = pd.read_csv(TABLAS / "p4_secciones.csv", dtype={"CUSEC": str})
    g = gpd.read_file(f"zip://{DATOS / 'seccionado_2024.zip'}!SECC_CE_20240101.shp")
    g = g[g["CUSEC"].isin(sec["CUSEC"])].to_crs(UTM).merge(sec, on="CUSEC")
    cent = g.geometry.centroid
    alcanzable = g["alcanzable"].to_numpy()
    pob = g["pob_65"].to_numpy()

    G = ox.load_graphml(DATOS / "red_peatonal_valencia.graphml")
    cs = centros.cargar(g.union_all())
    nodos_cen = ox.nearest_nodes(G, cs["lon"].values, cs["lat"].values)
    cll = gpd.GeoSeries(cent, crs=UTM).to_crs("EPSG:4326")
    nodos_sec = ox.nearest_nodes(G, cll.x.values, cll.y.values)

    e = ox.graph_to_gdfs(G, nodes=False).to_crs(UTM).reset_index()
    t_arista = (e["length"] / V_MAYOR / 60).to_numpy()
    _, nodos, idx = matriz(G, e, t_arista)
    mapa = {}
    for a, (uu, vv) in enumerate(zip(e["u"].map(idx), e["v"].map(idx))):
        mapa[(min(uu, vv), max(uu, vv))] = a
    src = np.unique([idx[n] for n in nodos_cen])
    dst = np.array([idx[n] for n in nodos_sec])

    # Campos termicos, comunes a los tres factores.
    campos = {}
    for v, horas in VENTANAS.items():
        T_av, ia = campo_avamet(cent, horas)
        T_e5, ie, _ = campo_era5(gpd.GeoSeries(cent, crs=UTM), horas)
        com = ia.intersection(ie)
        T_av, T_e5 = T_av[:, ia.get_indexer(com)], T_e5[:, ie.get_indexer(com)]
        campos[v] = (T_av, T_e5 + (np.nanmean(T_av) - np.nanmean(T_e5)))

    filas = []
    for factor in FACTORES:
        print(f"\n=== altura x {factor} ===")
        ed_f = ed.copy()
        ed_f["altura_m"] = ed["altura_m"] * factor
        H, transform = rasterizar_alturas(ed_f, (x0, y0, x1, y1))
        inv_t = ~transform
        cols, fils = inv_t * (puntos[:, 0], puntos[:, 1])
        cols = np.clip(cols.astype(int), 0, H.shape[1] - 1)
        fils = np.clip(fils.astype(int), 0, H.shape[0] - 1)

        sol_por_hora = {}
        for r in sol.itertuples():
            m = sombra(H, r.elevacion, r.azimut)
            df = pd.DataFrame({"arista": idx_arista, "s": m[fils, cols]})
            frac = df.groupby("arista")["s"].mean().reindex(
                np.arange(len(e))).fillna(0.0).to_numpy()
            s_arista = t_arista * (1.0 - frac)

            candidatos = []
            for lam in LAMBDAS:
                M, _, _ = matriz(G, e, (1 - lam) * t_arista + lam * s_arista)
                _, pred, _ = dijkstra(M, directed=False, indices=src,
                                      min_only=True, return_predecessors=True)
                tt, ss, _ = acumular(pred, set(src.tolist()), dst,
                                     t_arista, s_arista, mapa)
                candidatos.append((tt, ss))
            mejor = np.full(len(dst), np.inf)
            for tt, ss in candidatos:
                ok = tt <= PRESUPUESTO_MIN
                mejor = np.where(ok & (ss < mejor), ss, mejor)
            sol_por_hora[r.hora] = mejor
            print(f"  hora {r.hora}: sombra media {100*frac.mean():4.1f} %, "
                  f"sol mediano {np.nanmedian(mejor[alcanzable]):5.2f} min")

        for v, horas in VENTANAS.items():
            T_av, T_e5 = campos[v]
            sol_v = np.nanmean([sol_por_hora[h] for h in horas], axis=0)
            solar = (sol_v <= PRESUPUESTO_SOL).astype(float)
            fr = {}
            for etq, T in (("C", T_e5), ("D", T_av)):
                fr[etq] = np.where(alcanzable, (T < UMBRAL_T).mean(axis=1) * solar, 0.0)
            n = max(int(0.20 * alcanzable.sum()), 1)
            tops = {k: set(pd.Series((pob * (1 - f))[alcanzable]).nlargest(n).index)
                    for k, f in fr.items()}
            jac = len(tops["C"] & tops["D"]) / len(tops["C"] | tops["D"])
            recl = float(pd.Series(pob[alcanzable]).reindex(
                list(tops["D"] - tops["C"])).sum())
            filas.append({
                "factor_altura": factor, "ventana": v,
                "pct_cumplen_solar": round(100 * float(solar[alcanzable].mean()), 1),
                "sol_mediano_min": round(float(np.nanmedian(sol_v[alcanzable])), 2),
                "cobertura_C_pct": round(100 * float((fr["C"] * pob).sum() / pob.sum()), 2),
                "cobertura_D_pct": round(100 * float((fr["D"] * pob).sum() / pob.sum()), 2),
                "jaccard_met_con_sombra": round(jac, 3),
                "pob65_recl_met_con_sombra": round(recl),
            })

    res = pd.DataFrame(filas)
    res.to_csv(TABLAS / "p3_sensibilidad_altura.csv", index=False, encoding="utf-8")
    print("\n--- sensibilidad al supuesto de altura (umbral 30 C, presupuesto 8 min) ---")
    print(res.to_string(index=False))


if __name__ == "__main__":
    main()
