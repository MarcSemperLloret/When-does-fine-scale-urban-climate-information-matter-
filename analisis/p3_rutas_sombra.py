#!/usr/bin/env python3
"""Rutas al centro de salud con frontera tiempo-sombra, sin peso arbitrario.

No se combina tiempo y sol en un coste con un parametro `k` inventado: eso
repetiria el problema del corte en la mediana, un numero elegido a conveniencia
del que despues depende todo. En su lugar se recorre una rejilla de pesos y se
retiene la **frontera de Pareto**, y la decision se formula como un problema
restringido, que es transparente:

    de entre las rutas que llegan en <= 15 minutos, la de menos minutos al sol

El peso solo sirve para generar candidatos; no aparece en ningun resultado.

La eleccion de ruta se resuelve con la geometria solar del 15 de julio, y la
exposicion se evalua despues con la sombra de la fecha real. La posicion solar a
una misma hora varia unos ocho grados entre junio y agosto: suficiente para
mover la exposicion, poco para cambiar que calle conviene tomar.

Salidas:
  datos/rutas_sombra.parquet
  salidas/tablas/p3_rutas_*.csv
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

import centros

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos"
TABLAS = BASE / "salidas" / "tablas"
UTM = "EPSG:25830"

V_MAYOR = 0.90            # m/s
PRESUPUESTO_MIN = 15.0
HORAS = [10, 11, 12, 16, 17, 18]
FECHA_RUTEO = "07-15"     # geometria solar con la que se eligen las rutas
# Rejilla de pesos para generar candidatos de la frontera. Veintiun valores,
# no cinco: con cinco, una rejilla de 21 encontraba rutas menos expuestas en el
# 9-28 % de las secciones (hasta 12 % de reduccion de la mediana). Con 21, pasar
# a 41 solo mejora el 3-5 % de las secciones en 0,006 min, un 0,5-0,7 %
# relativo, de modo que la frontera esta practicamente convergida.
LAMBDAS = [round(i / 20, 3) for i in range(21)]

PRIMARIA = (r"centre de salut|centro de salud|consultori|consultorio|"
            r"centre sanitari|ambulatori")

# La variante con arbolado usa la misma maquinaria con otra capa de sombra.
SOMBRA_PARQUET = os.environ.get("SOMBRA_PARQUET", "sombra_aristas.parquet")
RUTAS_PARQUET = os.environ.get("RUTAS_PARQUET", "rutas_sombra.parquet")
SUFIJO = os.environ.get("SUFIJO_SALIDA", "")


def cargar_red():
    G = ox.load_graphml(DATOS / "red_peatonal_valencia.graphml")
    e = ox.graph_to_gdfs(G, nodes=False).to_crs(UTM).reset_index()
    e["arista"] = np.arange(len(e))
    sombra = pd.read_parquet(DATOS / SOMBRA_PARQUET)
    e = e.merge(sombra, left_on="arista", right_index=True, how="left")
    for c in sombra.columns:
        e[c] = e[c].fillna(0.0)
    return G, e, list(sombra.columns)


def matriz(G, e, peso):
    nodos = list(G.nodes())
    idx = {n: i for i, n in enumerate(nodos)}
    u = e["u"].map(idx).to_numpy()
    v = e["v"].map(idx).to_numpy()
    w = peso
    # Red peatonal: se recorre en los dos sentidos.
    m = coo_matrix((np.concatenate([w, w]),
                    (np.concatenate([u, v]), np.concatenate([v, u]))),
                   shape=(len(nodos), len(nodos))).tocsr()
    return m, nodos, idx


def acumular(pred, fuentes, destinos, t_arista, s_arista, mapa_arista):
    """Recorre el arbol de caminos minimos acumulando tiempo y minutos al sol."""
    tiempo = np.full(len(destinos), np.inf)
    sol = np.full(len(destinos), np.inf)
    smax = np.full(len(destinos), np.inf)
    for k, d in enumerate(destinos):
        n, tt, ss, corrida, peor = d, 0.0, 0.0, 0.0, 0.0
        while pred[n] >= 0:
            p = pred[n]
            a = mapa_arista.get((min(p, n), max(p, n)))
            if a is None:
                break
            tt += t_arista[a]
            ss += s_arista[a]
            # Tramo continuo al sol: se corta cuando la arista esta sombreada.
            if s_arista[a] > 0.5 * t_arista[a]:
                corrida += t_arista[a]
                peor = max(peor, corrida)
            else:
                corrida = 0.0
            n = p
        if np.isfinite(tt) and pred[d] >= 0 or d in fuentes:
            tiempo[k], sol[k], smax[k] = tt, ss, peor
    return tiempo, sol, smax


def main() -> None:
    print("red y sombra")
    G, e, configs = cargar_red()
    print(f"  {len(e):,} aristas, {len(configs)} configuraciones de sombra")

    sec = pd.read_csv(TABLAS / "p4_secciones.csv", dtype={"CUSEC": str})
    g = gpd.read_file(f"zip://{DATOS / 'seccionado_2024.zip'}!SECC_CE_20240101.shp")
    g = g[g["CUSEC"].isin(sec["CUSEC"])].to_crs(UTM).merge(sec, on="CUSEC")

    cs = centros.cargar(g.union_all())
    print(f"  {len(cs)} centros de atencion primaria ({centros.FUENTE})")

    nodos_cen = ox.nearest_nodes(G, cs["lon"].values, cs["lat"].values)
    cent = g.geometry.centroid.to_crs("EPSG:4326")
    nodos_sec = ox.nearest_nodes(G, cent.x.values, cent.y.values)

    t_arista = (e["length"] / V_MAYOR / 60).to_numpy()      # minutos
    mapa = {}
    _, nodos, idx = matriz(G, e, t_arista)
    for a, (uu, vv) in enumerate(zip(e["u"].map(idx), e["v"].map(idx))):
        mapa[(min(uu, vv), max(uu, vv))] = a
    src = np.unique([idx[n] for n in nodos_cen])
    dst = np.array([idx[n] for n in nodos_sec])

    filas = []
    for h in HORAS:
        clave_ruteo = f"{FECHA_RUTEO}_{h:02d}"
        sombra_ruteo = e[clave_ruteo].to_numpy()
        s_arista = t_arista * (1.0 - sombra_ruteo)         # minutos al sol

        candidatos = []
        for lam in LAMBDAS:
            peso = (1 - lam) * t_arista + lam * s_arista
            M, _, _ = matriz(G, e, peso)
            _, pred, _ = dijkstra(M, directed=False, indices=src,
                                  min_only=True, return_predecessors=True)
            tt, ss, sm = acumular(pred, set(src.tolist()), dst,
                                  t_arista, s_arista, mapa)
            candidatos.append({"lambda": lam, "tiempo": tt, "sol": ss, "smax": sm})

        # Problema restringido: minimo sol entre las rutas que caben en el
        # presupuesto. La ruta rapida (lambda = 0) es la referencia "sin sombra".
        rapida = candidatos[0]
        viable = np.full(len(dst), False)
        mejor_sol = np.full(len(dst), np.inf)
        mejor_t = np.full(len(dst), np.inf)
        mejor_smax = np.full(len(dst), np.inf)
        for c in candidatos:
            ok = c["tiempo"] <= PRESUPUESTO_MIN
            mejor = ok & (c["sol"] < mejor_sol)
            mejor_sol[mejor] = c["sol"][mejor]
            mejor_t[mejor] = c["tiempo"][mejor]
            mejor_smax[mejor] = c["smax"][mejor]
            viable |= ok

        filas.append(pd.DataFrame({
            "CUSEC": g["CUSEC"].to_numpy(), "hora": h,
            "t_rapida_min": rapida["tiempo"], "sol_rapida_min": rapida["sol"],
            "smax_rapida_min": rapida["smax"],
            "alcanzable": rapida["tiempo"] <= PRESUPUESTO_MIN,
            "t_sombreada_min": mejor_t, "sol_sombreada_min": mejor_sol,
            "smax_sombreada_min": mejor_smax,
        }))
        alc = rapida["tiempo"] <= PRESUPUESTO_MIN
        print(f"  hora {h}: alcanzables {alc.sum():3d}/{len(dst)} | "
              f"sol en ruta rapida {np.nanmedian(rapida['sol'][alc]):5.2f} min | "
              f"en ruta sombreada {np.nanmedian(mejor_sol[alc]):5.2f} min | "
              f"ahorro {100*(1-np.nanmedian(mejor_sol[alc])/max(np.nanmedian(rapida['sol'][alc]),1e-9)):4.1f} %")

    rutas = pd.concat(filas, ignore_index=True)
    rutas.to_parquet(DATOS / RUTAS_PARQUET, index=False)

    alc = rutas[rutas["alcanzable"]]
    res = alc.groupby("hora").agg(
        n=("CUSEC", "size"),
        t_rapida=("t_rapida_min", "median"),
        sol_rapida=("sol_rapida_min", "median"),
        t_sombreada=("t_sombreada_min", "median"),
        sol_sombreada=("sol_sombreada_min", "median"),
        smax_rapida=("smax_rapida_min", "median"),
        smax_sombreada=("smax_sombreada_min", "median"),
    ).round(2)
    res["ahorro_sol_pct"] = (100 * (1 - res["sol_sombreada"] / res["sol_rapida"])).round(1)
    res["coste_tiempo_pct"] = (100 * (res["t_sombreada"] / res["t_rapida"] - 1)).round(1)
    res.to_csv(TABLAS / f"p3_rutas_frontera{SUFIJO}.csv")

    print("\n--- frontera tiempo-sombra (mediana sobre secciones alcanzables) ---")
    print(res.to_string())

    (TABLAS / f"p3_rutas_resumen{SUFIJO}.json").write_text(json.dumps({
        "velocidad_ms": V_MAYOR, "presupuesto_min": PRESUPUESTO_MIN,
        "lambdas": LAMBDAS, "fecha_ruteo": FECHA_RUTEO,
        "n_centros": int(len(cs)), "n_secciones": int(len(g)),
    }, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
