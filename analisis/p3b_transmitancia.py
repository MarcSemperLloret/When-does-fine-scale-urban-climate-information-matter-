#!/usr/bin/env python3
"""Puerta 3b: transmitancia de copa, y en que rango la conclusion sobrevive.

La copa opaca era la cota superior del beneficio de sombra, y el propio
experimento mostro que la conclusion cualitativa **cambia entre los dos
extremos** de vegetacion. Mientras eso siga asi, la jerarquia
`arbolado > edificios > termica local` esta sesgada a favor del arbol, porque
se le evalua en su maximo efecto y a los otros con representaciones realistas.

Se sustituye el binario por una **transmitancia** con significado fisico: la
fraccion de radiacion directa que atraviesa la copa. La exposicion de un tramo
pasa a ser

    E = t * (f_abierto + tau * f_copa)

con `tau = 0` para el edificio, que es opaco de verdad, y `tau = 1` para el
cielo abierto. No es un peso arbitrario como el `k` que se evito en las rutas:
tau es una magnitud medible, y lo que se reporta es la **curva completa**, no un
valor elegido.

Los tres estados salen de las dos capas ya calculadas, sin rehacer sombras:

    f_edificio = frac_solo_edificios
    f_copa     = frac_con_arbolado - frac_solo_edificios
    f_abierto  = 1 - frac_con_arbolado

Se anade ademas la estabilidad estacional: si el orden de prioridad de los
barrios se mantiene entre el 15 de junio, julio y agosto, usar fechas
representativas esta justificado; si no, hace falta sombra dia a dia.

Salidas en salidas/tablas/p3b_*.csv
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
from p2_comparar_era5land import campo_avamet, campo_era5  # noqa: E402
from p3_rutas_sombra import (LAMBDAS, PRESUPUESTO_MIN, PRIMARIA,  # noqa: E402
                             V_MAYOR, acumular, matriz)

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos"
TABLAS = BASE / "salidas" / "tablas"
UTM = "EPSG:25830"

# Barrido de transmitancia. Los extremos son los dos limites ya conocidos; el
# rango fisicamente plausible para copa en hoja se suele situar entre 0,05 y
# 0,30, y es donde tiene que decidirse si la conclusion aguanta.
TAUS = [0.0, 0.05, 0.10, 0.20, 0.30, 0.50, 1.0]
TAU_REF = 0.10          # valor central para la comprobacion estacional
FECHAS = ["06-15", "07-15", "08-15"]
FECHA_BASE = "07-15"
HORAS = [10, 11, 12, 16, 17, 18]
VENTANAS = {"manana_10_12": [10, 11, 12], "tarde_16_18": [16, 17, 18]}
UMBRALES_T = (28.0, 30.0, 32.0)
PRESUPUESTOS_SOL = (3.0, 5.0, 8.0)


def preparar():
    G = ox.load_graphml(DATOS / "red_peatonal_valencia.graphml")
    e = ox.graph_to_gdfs(G, nodes=False).to_crs(UTM).reset_index()
    e["arista"] = np.arange(len(e))
    ed = pd.read_parquet(DATOS / "sombra_aristas.parquet")
    vg = pd.read_parquet(DATOS / "sombra_aristas_veg.parquet")

    sec = pd.read_csv(TABLAS / "p4_secciones.csv", dtype={"CUSEC": str})
    g = gpd.read_file(f"zip://{DATOS / 'seccionado_2024.zip'}!SECC_CE_20240101.shp")
    g = g[g["CUSEC"].isin(sec["CUSEC"])].to_crs(UTM).merge(sec, on="CUSEC")

    cs = centros.cargar(g.union_all())

    t_arista = (e["length"] / V_MAYOR / 60).to_numpy()
    _, nodos, idx = matriz(G, e, t_arista)
    mapa = {}
    for a, (uu, vv) in enumerate(zip(e["u"].map(idx), e["v"].map(idx))):
        mapa[(min(uu, vv), max(uu, vv))] = a
    src = np.unique([idx[n] for n in ox.nearest_nodes(G, cs["lon"].values,
                                                      cs["lat"].values)])
    cll = g.geometry.centroid.to_crs("EPSG:4326")
    dst = np.array([idx[n] for n in ox.nearest_nodes(G, cll.x.values, cll.y.values)])
    return G, e, ed, vg, g, t_arista, mapa, src, dst


def exposicion_por_arista(ed, vg, e, clave, tau, t_arista):
    """E = t * (f_abierto + tau * f_copa); el edificio es opaco."""
    f_ed = ed[clave].reindex(e["arista"]).fillna(0.0).to_numpy()
    f_vg = vg[clave].reindex(e["arista"]).fillna(0.0).to_numpy()
    f_copa = np.clip(f_vg - f_ed, 0.0, 1.0)
    f_abierto = np.clip(1.0 - f_vg, 0.0, 1.0)
    return t_arista * (f_abierto + tau * f_copa)


def rutas_para(G, e, t_arista, mapa, src, dst, s_arista):
    """Frontera de Pareto: minima exposicion entre las rutas dentro del plazo."""
    mejor = np.full(len(dst), np.inf)
    rapida = None
    for lam in LAMBDAS:
        M, _, _ = matriz(G, e, (1 - lam) * t_arista + lam * s_arista)
        _, pred, _ = dijkstra(M, directed=False, indices=src,
                              min_only=True, return_predecessors=True)
        tt, ss, _ = acumular(pred, set(src.tolist()), dst, t_arista, s_arista, mapa)
        if lam == 0.0:
            rapida = (tt, ss)
        ok = tt <= PRESUPUESTO_MIN
        mejor = np.where(ok & (ss < mejor), ss, mejor)
    return rapida, mejor


def metricas(T_av, T_e5, sol, alcanzable, pob, u, ps):
    solar = (sol <= ps).astype(float)
    fr = {}
    for etq, T in (("C", T_e5), ("D", T_av)):
        fr[etq] = np.where(alcanzable, (T < u).mean(axis=1) * solar, 0.0)
    n = max(int(0.20 * alcanzable.sum()), 1)
    tops = {k: set(pd.Series((pob * (1 - f))[alcanzable]).nlargest(n).index)
            for k, f in fr.items()}
    jac = len(tops["C"] & tops["D"]) / len(tops["C"] | tops["D"])
    recl = float(pd.Series(pob[alcanzable]).reindex(list(tops["D"] - tops["C"])).sum())
    return {
        "pct_cumplen_solar": round(100 * float(solar[alcanzable].mean()), 1),
        "cobertura_C_pct": round(100 * float((fr["C"] * pob).sum() / pob.sum()), 2),
        "cobertura_D_pct": round(100 * float((fr["D"] * pob).sum() / pob.sum()), 2),
        "jaccard": round(jac, 3),
        "pob65_reclasificada": round(recl),
        "top20": tops["D"],
    }


def main() -> None:
    G, e, ed, vg, g, t_arista, mapa, src, dst = preparar()
    alcanzable = g["alcanzable"].to_numpy()
    pob = g["pob_65"].to_numpy()
    print(f"{len(e):,} aristas, {len(g)} secciones, {alcanzable.sum()} alcanzables")

    campos = {}
    for v, horas in VENTANAS.items():
        T_av, ia = campo_avamet(g.geometry.centroid, horas)
        T_e5, ie, _ = campo_era5(gpd.GeoSeries(g.geometry.centroid, crs=UTM), horas)
        com = ia.intersection(ie)
        T_av, T_e5 = T_av[:, ia.get_indexer(com)], T_e5[:, ie.get_indexer(com)]
        campos[v] = (T_av, T_e5 + (np.nanmean(T_av) - np.nanmean(T_e5)))

    # ------------------------------------------------- barrido de transmitancia
    filas, tops_por_tau = [], {}
    for tau in TAUS:
        print(f"\n=== tau = {tau} ===")
        sol_hora = {}
        for h in HORAS:
            s = exposicion_por_arista(ed, vg, e, f"{FECHA_BASE}_{h:02d}", tau, t_arista)
            (t_rap, s_rap), mejor = rutas_para(G, e, t_arista, mapa, src, dst, s)
            sol_hora[h] = mejor
        for v, horas in VENTANAS.items():
            T_av, T_e5 = campos[v]
            sol = np.nanmean([sol_hora[h] for h in horas], axis=0)
            print(f"  {v}: exposicion mediana {np.nanmedian(sol[alcanzable]):.2f} min")
            for u in UMBRALES_T:
                for ps in PRESUPUESTOS_SOL:
                    m = metricas(T_av, T_e5, sol, alcanzable, pob, u, ps)
                    tops_por_tau[(tau, v, u, ps)] = m.pop("top20")
                    filas.append({"tau": tau, "ventana": v, "umbral_c": u,
                                  "presupuesto_sol_min": ps,
                                  "exposicion_mediana_min": round(
                                      float(np.nanmedian(sol[alcanzable])), 2),
                                  **m})

    cur = pd.DataFrame(filas)
    cur["solar_saturada"] = cur["pct_cumplen_solar"] < 60
    cur.to_csv(TABLAS / "p3b_curva_transmitancia.csv", index=False, encoding="utf-8")

    # ------------------------------------------------ estabilidad estacional
    est = []
    for fecha in FECHAS:
        sol_hora = {}
        for h in HORAS:
            s = exposicion_por_arista(ed, vg, e, f"{fecha}_{h:02d}", TAU_REF, t_arista)
            _, mejor = rutas_para(G, e, t_arista, mapa, src, dst, s)
            sol_hora[h] = mejor
        for v, horas in VENTANAS.items():
            T_av, T_e5 = campos[v]
            sol = np.nanmean([sol_hora[h] for h in horas], axis=0)
            for u in (30.0,):
                for ps in (5.0, 8.0):
                    m = metricas(T_av, T_e5, sol, alcanzable, pob, u, ps)
                    est.append({"fecha": fecha, "ventana": v, "umbral_c": u,
                                "presupuesto_sol_min": ps,
                                "exposicion_mediana_min": round(
                                    float(np.nanmedian(sol[alcanzable])), 2),
                                "_top": m.pop("top20"), **m})
    ests = pd.DataFrame(est)
    # Jaccard del conjunto prioritario entre fechas, misma configuracion.
    pares = []
    for (v, u, ps), sub in ests.groupby(["ventana", "umbral_c", "presupuesto_sol_min"]):
        for i in range(len(sub)):
            for j in range(i + 1, len(sub)):
                a, b = sub.iloc[i], sub.iloc[j]
                pares.append({"ventana": v, "umbral_c": u, "presupuesto_sol_min": ps,
                              "fecha_a": a["fecha"], "fecha_b": b["fecha"],
                              "jaccard_top20": round(
                                  len(a["_top"] & b["_top"]) / len(a["_top"] | b["_top"]), 3)})
    pd.DataFrame(pares).to_csv(TABLAS / "p3b_estabilidad_estacional.csv",
                               index=False, encoding="utf-8")
    ests.drop(columns="_top").to_csv(TABLAS / "p3b_estacional_detalle.csv",
                                     index=False, encoding="utf-8")

    (TABLAS / "p3b_resumen.json").write_text(json.dumps({
        "taus": TAUS, "tau_referencia_estacional": TAU_REF,
        "definicion": "E = t * (f_abierto + tau * f_copa); edificio opaco (tau=0)",
        "nota": ("tau es la fraccion de radiacion directa que atraviesa la copa; "
                 "se reporta la curva completa, no un valor elegido"),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n--- curva de transmitancia (umbral 30 C) ---")
    print(cur[(cur["umbral_c"] == 30.0)][
        ["tau", "ventana", "presupuesto_sol_min", "exposicion_mediana_min",
         "pct_cumplen_solar", "jaccard", "pob65_reclasificada",
         "solar_saturada"]].to_string(index=False))
    print("\n--- estabilidad estacional (tau = %.2f) ---" % TAU_REF)
    print(pd.DataFrame(pares).to_string(index=False))


if __name__ == "__main__":
    main()
