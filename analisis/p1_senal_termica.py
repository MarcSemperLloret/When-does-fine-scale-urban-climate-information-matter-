#!/usr/bin/env python3
"""Puerta 1 del plan de viabilidad: existe una senal termica intraurbana estable?

Toda la puerta se apoya en una sola idea: referirse a la mediana de la propia
red en cada instante. Eso elimina la evolucion meteorologica regional --que es
comun a todas las estaciones-- y deja al descubierto la estructura espacial
relativa, que es lo unico que un producto de rejilla no puede reproducir.

Se trabaja sobre dos paneles porque la red crece con el tiempo y mezclarlos
confundiria un cambio de senal con un cambio de muestra:

  panel_largo  estaciones con >=5 veranos utiles -> 2019-2023 y 2025
  panel_denso  las 16 estaciones urbanas utiles  -> 2023 y 2025

Salidas en salidas/tablas/p1_*.csv y salidas/figuras/p1_*.png
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

# Minimo de estaciones que deben reportar en una hora para que la mediana de
# referencia y la dispersion sean interpretables. Con menos, P90-P10 mide sobre
# todo que estaciones estaban encendidas.
MIN_ESTACIONES = 5

# Noches: la ventana 00-06 hora local aisla el enfriamiento nocturno del efecto
# directo de la radiacion solar, que es lo que confunde una senal de isla de
# calor con una diferencia de exposicion del abrigo.
HORAS_NOCHE = list(range(0, 7))
HORAS_TARDE = list(range(12, 19))

RNG = np.random.default_rng(20260806)
N_BOOT = 1000


def cargar():
    df = pd.read_parquet(QC)
    inv = pd.read_csv(INV, index_col=0)
    usables = inv[inv["decision"] == "usar"]
    urbanas = usables[usables["ambito"].isin(["municipio", "metropolitano"])]

    df = df[df["station_id"].isin(usables.index)].copy()
    df["hora"] = df["observed_local"].dt.hour

    # A media horaria: las estaciones emiten cada 5, 10 o 20 minutos y comparar
    # dispersiones entre cadencias distintas introduce una diferencia de
    # suavizado que no es climatica.
    hor = (
        df.groupby(["station_id", "date", "hora"], observed=True)
        .agg(t=("t_qc", "mean"),
             hr=("relative_humidity_pct", "mean"),
             viento=("wind_mean_kmh", "mean"),
             dir_viento=("wind_direction_deg", "mean"),
             n=("t_qc", "size"))
        .reset_index()
    )
    hor["date"] = pd.to_datetime(hor["date"])
    hor["year"] = hor["date"].dt.year
    hor["ts"] = hor["date"] + pd.to_timedelta(hor["hora"], unit="h")
    return hor, inv, usables, urbanas


def anomalias(hor: pd.DataFrame, panel: list[str]) -> pd.DataFrame:
    """Anomalia de cada estacion frente a la mediana del panel en cada hora."""
    p = hor[hor["station_id"].isin(panel)].copy()
    ref = p.groupby("ts")["t"].agg(["median", "count",
                                    lambda s: s.quantile(0.90),
                                    lambda s: s.quantile(0.10),
                                    lambda s: s.quantile(0.75),
                                    lambda s: s.quantile(0.25)])
    ref.columns = ["t_ref", "n_est", "p90", "p10", "p75", "p25"]
    ref["dispersion"] = ref["p90"] - ref["p10"]
    # Con siete estaciones, P90 y P10 caen practicamente sobre el maximo y el
    # minimo, de modo que la dispersion la mueve una sola estacion. El rango
    # intercuartilico se reporta en paralelo porque no tiene ese problema, y es
    # el que sostiene la conclusion cuando el panel es pequeno.
    ref["iqr"] = ref["p75"] - ref["p25"]
    ref = ref[ref["n_est"] >= MIN_ESTACIONES]

    p = p.join(ref, on="ts", how="inner")
    p["dT"] = p["t"] - p["t_ref"]
    return p, ref


def bootstrap_por_dia(p: pd.DataFrame, col: str, n_boot: int = N_BOOT):
    """IC bootstrap remuestreando dias completos.

    Las horas dentro de un dia no son independientes --una noche calida lo es
    entera-- asi que remuestrear horas sueltas estrecharia los intervalos de
    forma artificial. El bloque es el dia.
    """
    dias = p["date"].unique()
    por_dia = {d: g for d, g in p.groupby("date")[col]}
    out = np.empty(n_boot)
    for b in range(n_boot):
        muestra = RNG.choice(dias, size=len(dias), replace=True)
        out[b] = np.concatenate([por_dia[d].to_numpy() for d in muestra]).mean()
    return np.percentile(out, [2.5, 97.5])


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    hor, inv, usables, urbanas = cargar()
    nombres = inv["nombre"]

    paneles = {
        "panel_largo": sorted(urbanas[urbanas["veranos_utiles"] >= 5].index),
        "panel_denso": sorted(urbanas.index),
    }
    anios = {"panel_largo": [2019, 2020, 2021, 2022, 2023, 2025],
             "panel_denso": [2023, 2025]}

    resumen = {}
    for nombre_panel, panel in paneles.items():
        sub = hor[hor["year"].isin(anios[nombre_panel])]
        p, ref = anomalias(sub, panel)
        resumen[nombre_panel] = {"estaciones": panel, "anios": anios[nombre_panel],
                                 "horas_validas": int(len(ref))}

        # ------------------------------------------------ dispersion intraurbana
        ref = ref.copy()
        ref["hora"] = ref.index.hour
        ref["date"] = ref.index.normalize()
        ref["year"] = ref.index.year
        disp_hora = ref.groupby("hora").agg(
            disp_mediana=("dispersion", "median"),
            disp_p25=("dispersion", lambda s: s.quantile(0.25)),
            disp_p75=("dispersion", lambda s: s.quantile(0.75)),
            disp_p90=("dispersion", lambda s: s.quantile(0.90)),
            iqr_mediana=("iqr", "median"),
            n=("dispersion", "size"),
        ).round(3)
        disp_hora.to_csv(TABLAS / f"p1_dispersion_horaria_{nombre_panel}.csv")

        noche = ref[ref["hora"].isin(HORAS_NOCHE)]["dispersion"]
        dia = ref[~ref["hora"].isin(HORAS_NOCHE)]["dispersion"]
        noche_iqr = ref[ref["hora"].isin(HORAS_NOCHE)]["iqr"]

        # ----------------------------------------------------- episodios calidos
        tmax_dia = ref.groupby("date")["t_ref"].max()
        umbral_calido = tmax_dia.quantile(0.90)
        dias_calidos = set(tmax_dia[tmax_dia >= umbral_calido].index)
        ref["calido"] = ref["date"].isin(dias_calidos)
        disp_calido = ref[ref["calido"]].groupby("hora")["dispersion"].median()
        disp_normal = ref[~ref["calido"]].groupby("hora")["dispersion"].median()
        pd.DataFrame({"calido": disp_calido, "ordinario": disp_normal}).round(3).to_csv(
            TABLAS / f"p1_dispersion_episodios_{nombre_panel}.csv")

        # ------------------------------------------- anomalia media por estacion
        p = p.copy()
        p["calido"] = p["date"].isin(dias_calidos)
        est = p.groupby("station_id").agg(
            dT_medio=("dT", "mean"),
            dT_noche=("dT", lambda s: s[p.loc[s.index, "hora"].isin(HORAS_NOCHE)].mean()),
            dT_tarde=("dT", lambda s: s[p.loc[s.index, "hora"].isin(HORAS_TARDE)].mean()),
            n_horas=("dT", "size"),
        )
        # IC bootstrap de la anomalia nocturna, que es la magnitud sobre la que
        # el plan fija el liston de 0,5-1 C.
        ic = {}
        pn = p[p["hora"].isin(HORAS_NOCHE)]
        for sid, g in pn.groupby("station_id"):
            lo, hi = bootstrap_por_dia(g, "dT")
            ic[sid] = (lo, hi)
        est["dT_noche_ic_lo"] = [ic[s][0] for s in est.index]
        est["dT_noche_ic_hi"] = [ic[s][1] for s in est.index]
        est["significativa"] = (est["dT_noche_ic_lo"] > 0) | (est["dT_noche_ic_hi"] < 0)
        est["nombre"] = est.index.map(nombres)
        est["km_costa"] = est.index.map(inv["km_costa"])
        est["km_centro"] = est.index.map(inv["km_centro"])
        est["alt_m"] = est.index.map(inv["alt_m"])
        est = est.sort_values("dT_noche", ascending=False).round(3)
        est.to_csv(TABLAS / f"p1_anomalias_estacion_{nombre_panel}.csv")

        # Anomalia media por estacion y hora: es la forma de la senal, y separa
        # el patron nocturno del patron de tarde, que no coinciden.
        (p.groupby(["station_id", "hora"])["dT"].mean().unstack("hora").round(3)
           .reindex(est.index)
           .to_csv(TABLAS / f"p1_anomalia_estacion_hora_{nombre_panel}.csv"))

        # ---------------------------------------------- estabilidad del ranking
        por_anio = (
            pn.groupby(["year", "station_id"])["dT"].mean().unstack("station_id")
        )
        rank = por_anio.rank(axis=1, ascending=False)
        pares = []
        anios_disp = list(por_anio.index)
        for i, a in enumerate(anios_disp):
            for b in anios_disp[i + 1:]:
                comun = por_anio.loc[[a, b]].dropna(axis=1)
                if comun.shape[1] >= 4:
                    rho = comun.loc[a].corr(comun.loc[b], method="spearman")
                    pares.append({"anio_a": a, "anio_b": b, "n_est": comun.shape[1],
                                  "spearman": round(rho, 3)})
        est_rank = pd.DataFrame(pares)
        est_rank.to_csv(TABLAS / f"p1_estabilidad_ranking_{nombre_panel}.csv", index=False)
        por_anio.round(3).to_csv(TABLAS / f"p1_anomalia_nocturna_por_anio_{nombre_panel}.csv")

        # ------------------------------------------------------- noches calidas
        tmin = (
            p[p["hora"].isin(HORAS_NOCHE)]
            .groupby(["station_id", "date"])["t"].min()
            .reset_index()
        )
        def contar_noches(t: pd.DataFrame) -> pd.DataFrame:
            n = t.groupby("station_id")["t"].agg(
                n_noches="size",
                tropicales=lambda s: int((s >= 20).sum()),
                torridas=lambda s: int((s >= 25).sum()),
                tmin_media="mean",
            )
            n["pct_tropicales"] = (100 * n["tropicales"] / n["n_noches"]).round(1)
            n["pct_torridas"] = (100 * n["torridas"] / n["n_noches"]).round(1)
            return n

        noches = contar_noches(tmin)
        # Las estaciones no cubren las mismas noches, y una diferencia de
        # porcentaje podria venir de que a una le faltase justo el verano mas
        # calido. Se repite sobre las noches en que reportan todas.
        completas = tmin.groupby("date")["station_id"].nunique()
        comunes = set(completas[completas == len(panel)].index)
        noches_com = contar_noches(tmin[tmin["date"].isin(comunes)])
        noches = noches.join(noches_com[["n_noches", "pct_tropicales", "pct_torridas"]],
                             rsuffix="_comunes")
        noches["nombre"] = noches.index.map(nombres)
        noches.round(2).to_csv(TABLAS / f"p1_noches_calidas_{nombre_panel}.csv")

        # ---------------------------------------------------------- LOSO
        # Si la senal la sostiene una sola estacion, quitarla debe hacerla caer.
        loso = []
        for fuera in panel:
            resto = [s for s in panel if s != fuera]
            p2, ref2 = anomalias(sub, resto)
            noc2 = ref2[ref2.index.hour.isin(HORAS_NOCHE)]
            e2 = (p2[p2["hora"].isin(HORAS_NOCHE)].groupby("station_id")["dT"].mean())
            loso.append({
                "excluida": fuera,
                "nombre": nombres.get(fuera, fuera),
                "disp_noche_mediana": round(noc2["dispersion"].median(), 3),
                "iqr_noche_mediana": round(noc2["iqr"].median(), 3),
                "rango_dT_noche": round(e2.max() - e2.min(), 3),
                "estacion_mas_calida": e2.idxmax(),
                "estacion_mas_fria": e2.idxmin(),
            })
        loso_df = pd.DataFrame(loso)
        loso_df.to_csv(TABLAS / f"p1_loso_{nombre_panel}.csv", index=False)

        # ------------------------------------------------- referencia periurbana
        # Control: si la estructura solo aparece frente a la mediana urbana pero
        # no frente a un entorno rural, seria un artefacto de la definicion.
        rurales = sorted(usables[(usables["ambito"] == "periurbano")
                                 & (usables["veranos_utiles"] >= 5)].index)
        rr = sub[sub["station_id"].isin(rurales)].groupby("ts")["t"].median().rename("t_rural")
        pu = p.join(rr, on="ts", how="inner")
        pu["dT_rural"] = pu["t"] - pu["t_rural"]
        uhi = pu[pu["hora"].isin(HORAS_NOCHE)].groupby("station_id")["dT_rural"].mean().round(3)
        uhi_df = uhi.to_frame("uhi_nocturna_c")
        uhi_df["nombre"] = uhi_df.index.map(nombres)
        uhi_df.sort_values("uhi_nocturna_c", ascending=False).to_csv(
            TABLAS / f"p1_uhi_vs_periurbano_{nombre_panel}.csv")

        # -------------------------------------------------------- regimen viento
        # Regimen diario a partir de la direccion media de la tarde en el panel.
        dirs = (
            sub[sub["hora"].isin(HORAS_TARDE)]
            .groupby("date")["dir_viento"]
            .agg(lambda s: np.degrees(np.arctan2(np.sin(np.radians(s)).mean(),
                                                 np.cos(np.radians(s)).mean())) % 360)
        )
        regimen = pd.cut(dirs, bins=[0, 45, 135, 225, 315, 360],
                         labels=["N", "brisa_E", "S", "poniente_W", "N2"])
        regimen = regimen.astype(str).replace({"N2": "N"})
        ref["regimen"] = ref["date"].map(regimen)
        disp_reg = (
            ref[ref["hora"].isin(HORAS_NOCHE)]
            .groupby("regimen")["dispersion"].agg(mediana="median", n="size").round(3)
        )
        disp_reg.to_csv(TABLAS / f"p1_dispersion_regimen_{nombre_panel}.csv")

        # -------------------------------------------------- coherencia fisica
        # El plan pide que la senal sea interpretable, no solo significativa.
        # Estas correlaciones son un anticipo de la Puerta 3 con las tres unicas
        # covariables disponibles sin descargar cartografia.
        coh = {}
        for cov in ("km_centro", "km_costa", "alt_m"):
            v = est[cov].astype(float)
            coh[f"spearman_dTnoche_{cov}"] = round(float(est["dT_noche"].corr(v, method="spearman")), 3)
            coh[f"spearman_dTtarde_{cov}"] = round(float(est["dT_tarde"].corr(v, method="spearman")), 3)
        pd.Series(coh).to_csv(TABLAS / f"p1_coherencia_fisica_{nombre_panel}.csv", header=False)

        resumen[nombre_panel].update({
            "dispersion_noche_mediana_c": round(float(noche.median()), 3),
            "dispersion_noche_p90_c": round(float(noche.quantile(0.90)), 3),
            "iqr_noche_mediana_c": round(float(noche_iqr.median()), 3),
            "dispersion_dia_mediana_c": round(float(dia.median()), 3),
            "dispersion_noche_calidos_c": round(float(
                ref[ref["calido"] & ref["hora"].isin(HORAS_NOCHE)]["dispersion"].median()), 3),
            "dispersion_noche_ordinarios_c": round(float(
                ref[~ref["calido"] & ref["hora"].isin(HORAS_NOCHE)]["dispersion"].median()), 3),
            "umbral_dia_calido_c": round(float(umbral_calido), 2),
            "n_dias_calidos": len(dias_calidos),
            "rango_dT_noche_c": round(float(est["dT_noche"].max() - est["dT_noche"].min()), 3),
            "estaciones_con_anomalia_significativa": int(est["significativa"].sum()),
            "spearman_ranking_mediana": round(float(est_rank["spearman"].median()), 3)
                if len(est_rank) else None,
            "spearman_ranking_min": round(float(est_rank["spearman"].min()), 3)
                if len(est_rank) else None,
            "loso_disp_noche_min": round(float(loso_df["disp_noche_mediana"].min()), 3),
            "loso_disp_noche_max": round(float(loso_df["disp_noche_mediana"].max()), 3),
            "loso_iqr_noche_min": round(float(loso_df["iqr_noche_mediana"].min()), 3),
            "loso_iqr_noche_max": round(float(loso_df["iqr_noche_mediana"].max()), 3),
            "loso_rango_dT_min": round(float(loso_df["rango_dT_noche"].min()), 3),
            "loso_estacion_mas_calida": sorted(loso_df["estacion_mas_calida"].unique()),
            "loso_estacion_mas_fria": sorted(loso_df["estacion_mas_fria"].unique()),
            "coherencia_fisica": coh,
            "uhi_nocturna_max_c": round(float(uhi.max()), 3),
            "uhi_nocturna_min_c": round(float(uhi.min()), 3),
            "pct_noches_tropicales_max": float(noches["pct_tropicales"].max()),
            "pct_noches_tropicales_min": float(noches["pct_tropicales"].min()),
            "n_noches_comunes": int(len(comunes)),
            "pct_tropicales_comunes_max": float(noches["pct_tropicales_comunes"].max()),
            "pct_tropicales_comunes_min": float(noches["pct_tropicales_comunes"].min()),
            "pct_torridas_comunes_max": float(noches["pct_torridas_comunes"].max()),
            "pct_torridas_comunes_min": float(noches["pct_torridas_comunes"].min()),
            "dispersion_por_regimen": disp_reg["mediana"].to_dict(),
        })

        print(f"\n===== {nombre_panel} ({len(panel)} estaciones, {anios[nombre_panel]}) =====")
        print(json.dumps({k: v for k, v in resumen[nombre_panel].items()
                          if k not in ("estaciones", "anios")}, indent=2, ensure_ascii=False))
        print("\nanomalia nocturna por estacion:")
        print(est[["nombre", "dT_noche", "dT_noche_ic_lo", "dT_noche_ic_hi",
                   "dT_tarde", "km_costa", "significativa"]].to_string())

    (TABLAS / "p1_resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
