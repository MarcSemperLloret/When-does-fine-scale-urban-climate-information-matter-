#!/usr/bin/env python3
"""Regla de exposicion anclada en la literatura, y regret presupuestario.

**Cambio de parametrizacion.** El presupuesto en minutos absolutos era el ultimo
parametro elegido por conveniencia, y ademas no es comparable entre trayectos:
ocho minutos al sol no significan lo mismo en un recorrido de nueve minutos que
en uno de quince. La literatura no da un presupuesto normativo en minutos, pero
si formula la restriccion como **fraccion del recorrido bajo radiacion directa**:

* Tomasi et al. (2024), Building and Environment, definen el umbral por
  balance energetico y lo expresan como porcentaje maximo de exposicion, con un
  presupuesto para persona mayor de 0,5 met frente a 2,1 met en adulto joven,
  es decir, del orden de un tercio.
* Los trabajos de diseno de sombreado de itinerarios peatonales usan como
  objetivo de desempeno **el 60 % del recorrido en sombra**, o sea el 40 %
  expuesto como maximo.

Se adopta por tanto la fraccion expuesta como restriccion, con phi = 0,40 de
referencia anclada, y **se reporta la curva completa** porque ningun valor es
normativo en sentido estricto y porque la pregunta interesante es para que
rango de politicas las decisiones dependen de la representacion.

**Regret presupuestario.** Un ayuntamiento puede intervenir en el k por ciento
de las secciones. Cada representacion elige unas; la carga vulnerable que se
deja sin atender por elegir con informacion incompleta es el regret:

    R(k) = B(S_completa(k)) - B(S_representacion(k))

con B evaluado siempre con la representacion completa, que es la que hace de
verdad de campo.

Salidas en salidas/tablas/p4c_*.csv
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

VENTANAS = {"manana_10_12": [10, 11, 12], "tarde_16_18": [16, 17, 18]}
UMBRAL_T = 30.0
TAU = 0.10

# Fraccion maxima del recorrido bajo sol. 0,40 es el complemento del objetivo
# de diseno del 60 % sombreado; el resto de la curva se reporta igualmente.
PHIS = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 1.00]
PHI_REF = 0.40

PRESUPUESTOS_K = [0.05, 0.10, 0.15, 0.20, 0.25]


def fraccion_expuesta(rutas: pd.DataFrame, horas, cusec, tau_mix=None):
    """Fraccion del recorrido bajo sol en la ruta sombreada."""
    r = rutas[rutas["hora"].isin(horas)]
    sol = r.groupby("CUSEC")["sol_sombreada_min"].mean().reindex(cusec)
    t = r.groupby("CUSEC")["t_sombreada_min"].mean().reindex(cusec)
    return (sol / t.replace(0, np.nan)).to_numpy()


def main() -> None:
    sec = pd.read_csv(TABLAS / "p4_secciones.csv", dtype={"CUSEC": str})
    g = gpd.read_file(f"zip://{DATOS / 'seccionado_2024.zip'}!SECC_CE_20240101.shp")
    g = g[g["CUSEC"].isin(sec["CUSEC"])].to_crs(UTM).merge(sec, on="CUSEC")
    g["distrito"] = g["CUSEC"].str[5:7]
    alc = g["alcanzable"].to_numpy()
    pob = g["pob_65"].to_numpy()
    cusec = g["CUSEC"]

    r_ed = pd.read_parquet(DATOS / "rutas_sombra.parquet")
    r_vg = pd.read_parquet(DATOS / "rutas_sombra_veg.parquet")

    campos = {}
    for v, horas in VENTANAS.items():
        T_av, ia = campo_avamet(g.geometry.centroid, horas)
        T_e5, ie, _ = campo_era5(gpd.GeoSeries(g.geometry.centroid, crs=UTM), horas)
        com = ia.intersection(ie)
        T_av, T_e5 = T_av[:, ia.get_indexer(com)], T_e5[:, ie.get_indexer(com)]
        campos[v] = (T_av, T_e5 + (np.nanmean(T_av) - np.nanmean(T_e5)))

    # ------------------------------------------------------- curva en phi
    filas = []
    for v, horas in VENTANAS.items():
        T_av, T_e5 = campos[v]
        phi_ed = fraccion_expuesta(r_ed, horas, cusec)
        phi_vg = fraccion_expuesta(r_vg, horas, cusec)
        for phi in PHIS:
            for etq, ph in (("solo_edificios", phi_ed), ("edificios_vegetacion", phi_vg)):
                solar = (ph <= phi).astype(float)
                fr = {k: np.where(alc, (T < UMBRAL_T).mean(axis=1) * solar, 0.0)
                      for k, T in (("C", T_e5), ("D", T_av))}
                n = max(int(0.20 * alc.sum()), 1)
                tops = {k: set(pd.Series((pob * (1 - f))[alc]).nlargest(n).index)
                        for k, f in fr.items()}
                jac = len(tops["C"] & tops["D"]) / len(tops["C"] | tops["D"])
                recl = float(pd.Series(pob[alc]).reindex(
                    list(tops["D"] - tops["C"])).sum())
                filas.append({
                    "ventana": v, "phi_max": phi, "capa_sombra": etq,
                    "pct_cumplen": round(100 * float(solar[alc].mean()), 1),
                    "phi_mediana": round(float(np.nanmedian(ph[alc])), 3),
                    "jaccard": round(jac, 3), "pob65_reclasificada": round(recl),
                    "saturada": bool(solar[alc].mean() < 0.6),
                })
    curva = pd.DataFrame(filas)
    curva.to_csv(TABLAS / "p4c_curva_phi.csv", index=False, encoding="utf-8")

    # --------------------------------------------------- regret presupuestario
    # Cinco representaciones, de menos a mas informacion. La ultima es la que
    # hace de campo de verdad para evaluar el beneficio de cualquier seleccion.
    reg, sel_ref = [], {}
    for v, horas in VENTANAS.items():
        T_av, T_e5 = campos[v]
        phi_ed = fraccion_expuesta(r_ed, horas, cusec)
        phi_vg = fraccion_expuesta(r_vg, horas, cusec)
        sin_sombra = np.ones(len(g))

        reps = {
            "R1_era5_sin_sombra": (T_e5, sin_sombra),
            "R2_era5_sombra_completa": (T_e5, (phi_vg <= PHI_REF).astype(float)),
            "R3_local_sin_sombra": (T_av, sin_sombra),
            "R4_local_sombra_edificios": (T_av, (phi_ed <= PHI_REF).astype(float)),
            "R5_local_sombra_completa": (T_av, (phi_vg <= PHI_REF).astype(float)),
        }
        fracs = {k: np.where(alc, (T < UMBRAL_T).mean(axis=1) * s, 0.0)
                 for k, (T, s) in reps.items()}

        # Carga vulnerable real de cada seccion, segun la representacion completa.
        carga = pob * (1 - fracs["R5_local_sombra_completa"])
        carga = np.where(alc, carga, 0.0)

        for k in PRESUPUESTOS_K:
            n = max(int(k * alc.sum()), 1)
            idx_alc = np.where(alc)[0]
            sel = {}
            for etq, f in fracs.items():
                orden = np.argsort(-(pob[idx_alc] * (1 - f[idx_alc])))
                sel[etq] = idx_alc[orden[:n]]
            b_max = float(carga[sel["R5_local_sombra_completa"]].sum())
            for etq, s in sel.items():
                b = float(carga[s].sum())
                comun = len(set(s) & set(sel["R5_local_sombra_completa"]))
                reg.append({
                    "ventana": v, "k_pct": int(100 * k), "n_secciones": n,
                    "representacion": etq,
                    "carga_capturada": round(b),
                    "carga_maxima": round(b_max),
                    "regret_absoluto": round(b_max - b),
                    "regret_relativo_pct": round(100 * (b_max - b) / b_max, 2)
                    if b_max > 0 else np.nan,
                    "solapamiento_con_completa": f"{comun}/{n}",
                    "jaccard_seleccion": round(
                        comun / len(set(s) | set(sel["R5_local_sombra_completa"])), 3),
                    "pob65_seleccionada": round(float(pob[s].sum())),
                })
        sel_ref[v] = sel
    regret = pd.DataFrame(reg)
    regret.to_csv(TABLAS / "p4c_regret.csv", index=False, encoding="utf-8")

    (TABLAS / "p4c_resumen.json").write_text(json.dumps({
        "phi_referencia": PHI_REF,
        "anclaje": ("60 % del recorrido en sombra como objetivo de diseno de "
                    "itinerarios peatonales (Tomasi et al. 2024, Building and "
                    "Environment); el presupuesto energetico de la persona mayor "
                    "se situa en ~1/3 del de adulto joven (Tomasi et al. 2024)"),
        "tau": TAU, "umbral_c": UMBRAL_T,
        "presupuestos_k": PRESUPUESTOS_K,
        "beneficio": ("carga vulnerable = poblacion 65+ x fraccion de horas NO "
                      "atendida, evaluada siempre con la representacion completa"),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print("--- curva en fraccion expuesta (umbral 30 C) ---")
    print(curva[curva["capa_sombra"] == "edificios_vegetacion"][
        ["ventana", "phi_max", "pct_cumplen", "jaccard",
         "pob65_reclasificada", "saturada"]].to_string(index=False))
    print(f"\n  fraccion expuesta mediana observada: "
          f"{curva['phi_mediana'].min():.3f}-{curva['phi_mediana'].max():.3f}")
    print("\n--- regret presupuestario (phi = %.2f, umbral %.0f C) ---" % (PHI_REF, UMBRAL_T))
    print(regret[["ventana", "k_pct", "representacion", "carga_capturada",
                  "regret_absoluto", "regret_relativo_pct",
                  "solapamiento_con_completa"]].to_string(index=False))


if __name__ == "__main__":
    main()
