#!/usr/bin/env python3
"""Puerta 1 recortada por escala espacial y por ventana horaria.

Corrige un error de encuadre de la primera pasada: el contraste mas
espectacular del Bloque A --Penya-roja frente a Almassera-- separa dos
municipios y describe un gradiente nucleo denso / huerta abierta, no
heterogeneidad entre barrios de Valencia. Presentarlo como lo segundo seria
falso, y ademas apoya la hipotesis equivocada, porque la accesibilidad peatonal
ocurre de dia y la senal nocturna es la que domina ese contraste.

Se separan por tanto tres escalas, cada una respondiendo a su propia pregunta:

  intramunicipal  solo estaciones dentro del municipio de Valencia
                  -> heterogeneidad entre barrios; es la escala del articulo
                     de accesibilidad
  metropolitano   municipio mas corona inmediata (<12 km)
                  -> gradiente ciudad / huerta / litoral
  periurbano      12-30 km, como referencia externa

y dentro de cada una se separan las ventanas horarias que corresponden a cada
decision. La accesibilidad a centros de salud se juega entre las 10 y las 18,
no de madrugada.

Salidas en salidas/tablas/p1b_*.csv
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
QC = BASE / "datos" / "valencia_verano_qc.parquet"
INV = BASE / "salidas" / "tablas" / "p0_inventario_estaciones.csv"
TABLAS = BASE / "salidas" / "tablas"

RNG = np.random.default_rng(20260806)
N_BOOT = 1000

# Ventanas horarias, en hora local. Las dos diurnas son las que el propio
# diseno de accesibilidad va a usar: media manana y media tarde, ambas dentro
# del horario de apertura de un centro de salud.
VENTANAS = {
    "noche_00_06": list(range(0, 7)),
    "manana_10_12": [10, 11, 12],
    "tarde_16_18": [16, 17, 18],
    "diurna_10_18": list(range(10, 19)),
}

# l'Albufera esta dentro del termino municipal pero es marjal a trece
# kilometros del centro, no tejido urbano. Entra en la escala municipal
# administrativa y sale de la escala de barrios, y la diferencia entre ambas
# cifras es justamente lo que hay que reportar por separado.
ALBUFERA = "c15m250e16"


def bootstrap_dia(g: pd.DataFrame, col: str) -> tuple[float, float]:
    dias = g["date"].unique()
    por_dia = {d: s.to_numpy() for d, s in g.groupby("date")[col]}
    out = np.empty(N_BOOT)
    for b in range(N_BOOT):
        m = RNG.choice(dias, size=len(dias), replace=True)
        out[b] = np.concatenate([por_dia[d] for d in m]).mean()
    return tuple(np.percentile(out, [2.5, 97.5]))


def horario(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["hora"] = df["observed_local"].dt.hour
    hor = (
        df.groupby(["station_id", "date", "hora"], observed=True)
        .agg(t=("t_qc", "mean"))
        .reset_index()
    )
    hor["date"] = pd.to_datetime(hor["date"])
    hor["year"] = hor["date"].dt.year
    hor["ts"] = hor["date"] + pd.to_timedelta(hor["hora"], unit="h")
    return hor


def analizar(hor: pd.DataFrame, panel: list[str], min_est: int):
    p = hor[hor["station_id"].isin(panel)].copy()
    ref = p.groupby("ts")["t"].agg(
        t_ref="median", n_est="count",
        p90=lambda s: s.quantile(0.90), p10=lambda s: s.quantile(0.10),
        p75=lambda s: s.quantile(0.75), p25=lambda s: s.quantile(0.25),
        rango=lambda s: s.max() - s.min(),
    )
    ref["dispersion"] = ref["p90"] - ref["p10"]
    ref["iqr"] = ref["p75"] - ref["p25"]
    ref = ref[ref["n_est"] >= min_est]
    p = p.join(ref, on="ts", how="inner")
    p["dT"] = p["t"] - p["t_ref"]
    ref = ref.copy()
    ref["hora"] = ref.index.hour
    return p, ref


def main() -> None:
    inv = pd.read_csv(INV, index_col=0)
    usables = inv[inv["decision"] == "usar"]
    nombres = inv["nombre"]

    df = pd.read_parquet(QC)
    df = df[df["station_id"].isin(usables.index)]
    hor = horario(df)

    municipio = sorted(usables[usables["ambito"] == "municipio"].index)
    barrios = [s for s in municipio if s != ALBUFERA]
    metro = sorted(usables[usables["ambito"].isin(["municipio", "metropolitano"])].index)
    # La corona metropolitana solo esta poblada desde 2023, asi que su panel se
    # restringe a esos veranos para no confundir crecimiento de red con senal.
    escalas = {
        "intramunicipal_barrios": (barrios, 5, None),
        "intramunicipal_total": (municipio, 5, None),
        "metropolitano": (metro, 12, [2023, 2025]),
    }

    resumen = {}
    filas_disp = []
    for nombre_escala, (panel, min_est, anios) in escalas.items():
        sub = hor if anios is None else hor[hor["year"].isin(anios)]
        p, ref = analizar(sub, panel, min_est)

        info = {"estaciones": panel, "n_estaciones": len(panel),
                "horas_validas": int(len(ref)),
                "anios": anios or sorted(sub["year"].unique().tolist())}

        for v, horas in VENTANAS.items():
            r = ref[ref["hora"].isin(horas)]
            info[f"disp_{v}_mediana"] = round(float(r["dispersion"].median()), 3)
            info[f"iqr_{v}_mediana"] = round(float(r["iqr"].median()), 3)
            info[f"rango_{v}_mediana"] = round(float(r["rango"].median()), 3)
            info[f"rango_{v}_p90"] = round(float(r["rango"].quantile(0.90)), 3)
            filas_disp.append({"escala": nombre_escala, "ventana": v,
                               "n_estaciones": len(panel), "n_horas": len(r),
                               "disp_p90_p10": round(float(r["dispersion"].median()), 3),
                               "iqr": round(float(r["iqr"].median()), 3),
                               "rango_max_min": round(float(r["rango"].median()), 3),
                               "rango_p90": round(float(r["rango"].quantile(0.90)), 3)})

        # Anomalia por estacion en cada ventana, con IC bootstrap por dia.
        est = {}
        for v, horas in VENTANAS.items():
            pv = p[p["hora"].isin(horas)]
            m = pv.groupby("station_id")["dT"].mean()
            est[f"dT_{v}"] = m.round(3)
            if v in ("noche_00_06", "diurna_10_18"):
                ic = {sid: bootstrap_dia(g, "dT") for sid, g in pv.groupby("station_id")}
                est[f"dT_{v}_lo"] = pd.Series({k: round(x[0], 3) for k, x in ic.items()})
                est[f"dT_{v}_hi"] = pd.Series({k: round(x[1], 3) for k, x in ic.items()})
        tabla = pd.DataFrame(est)
        tabla["nombre"] = tabla.index.map(nombres)
        tabla["km_centro"] = tabla.index.map(inv["km_centro"]).round(2)
        tabla["km_costa"] = tabla.index.map(inv["km_costa"]).round(2)
        # Si el orden termico se invierte entre dia y noche, un mapa unico de
        # "barrios calientes" es incorrecto. Se mide explicitamente.
        tabla["rank_noche"] = tabla["dT_noche_00_06"].rank(ascending=False)
        tabla["rank_diurno"] = tabla["dT_diurna_10_18"].rank(ascending=False)
        tabla = tabla.sort_values("dT_diurna_10_18", ascending=False)
        tabla.to_csv(TABLAS / f"p1b_anomalias_{nombre_escala}.csv")

        rho = tabla["dT_noche_00_06"].corr(tabla["dT_diurna_10_18"], method="spearman")
        info["spearman_ranking_noche_vs_dia"] = round(float(rho), 3)
        info["rango_dT_noche"] = round(float(tabla["dT_noche_00_06"].max()
                                             - tabla["dT_noche_00_06"].min()), 3)
        info["rango_dT_diurno"] = round(float(tabla["dT_diurna_10_18"].max()
                                              - tabla["dT_diurna_10_18"].min()), 3)
        info["dT_diurno_significativas"] = int(
            ((tabla["dT_diurna_10_18_lo"] > 0) | (tabla["dT_diurna_10_18_hi"] < 0)).sum())

        # Noches calidas dentro de la escala, sobre noches comunes.
        tmin = (p[p["hora"].isin(VENTANAS["noche_00_06"])]
                .groupby(["station_id", "date"])["t"].min().reset_index())
        comp = tmin.groupby("date")["station_id"].nunique()
        com = set(comp[comp == len(panel)].index)
        tc = tmin[tmin["date"].isin(com)]
        noches = tc.groupby("station_id")["t"].agg(
            n="size", tropicales=lambda s: int((s >= 20).sum()),
            torridas=lambda s: int((s >= 25).sum()))
        noches["pct_tropicales"] = (100 * noches["tropicales"] / noches["n"]).round(1)
        noches["pct_torridas"] = (100 * noches["torridas"] / noches["n"]).round(1)
        noches["nombre"] = noches.index.map(nombres)
        noches.sort_values("pct_torridas", ascending=False).to_csv(
            TABLAS / f"p1b_noches_{nombre_escala}.csv")
        info["n_noches_comunes"] = len(com)
        info["pct_torridas_max"] = float(noches["pct_torridas"].max())
        info["pct_torridas_min"] = float(noches["pct_torridas"].min())
        info["pct_tropicales_max"] = float(noches["pct_tropicales"].max())
        info["pct_tropicales_min"] = float(noches["pct_tropicales"].min())

        resumen[nombre_escala] = info

    pd.DataFrame(filas_disp).to_csv(TABLAS / "p1b_dispersion_por_escala.csv", index=False)
    (TABLAS / "p1b_resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

    print(pd.DataFrame(filas_disp).to_string(index=False))
    for k, v in resumen.items():
        print(f"\n===== {k} ({v['n_estaciones']} estaciones) =====")
        print(json.dumps({a: b for a, b in v.items()
                          if a.startswith(("spearman", "rango_dT", "dT_", "pct_", "n_noches"))},
                         indent=2, ensure_ascii=False))
        print(pd.read_csv(TABLAS / f"p1b_anomalias_{k}.csv", index_col=0)[
            ["nombre", "dT_diurna_10_18", "dT_diurna_10_18_lo", "dT_diurna_10_18_hi",
             "dT_manana_10_12", "dT_tarde_16_18", "dT_noche_00_06",
             "rank_diurno", "rank_noche"]].to_string())


if __name__ == "__main__":
    main()
