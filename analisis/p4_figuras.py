#!/usr/bin/env python3
"""Figuras del piloto de accesibilidad."""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE.parents[0] / "downbursts-cv-pilot" / "scripts"))
import figure_style as fs  # noqa: E402

TABLAS = BASE / "salidas" / "tablas"
FIGURAS = BASE / "salidas" / "figuras"
DATOS = BASE / "datos"
UTM = "EPSG:25830"
PRESUPUESTO, VEL = 15.0, 0.90


def main() -> None:
    fs.apply()
    FIGURAS.mkdir(parents=True, exist_ok=True)
    sec = pd.read_csv(TABLAS / "p4_secciones.csv", dtype={"CUSEC": str})
    sens = pd.read_csv(TABLAS / "p4_sensibilidad.csv")

    g = gpd.read_file(f"zip://{DATOS / 'seccionado_2024.zip'}!SECC_CE_20240101.shp")
    g = g[g["CUSEC"].isin(sec["CUSEC"])].to_crs(UTM).merge(sec, on="CUSEC")

    a = g[g["alcanzable"]].copy()
    n = int(0.20 * len(a))
    top_d = set((a["pob_65"] * a["t_min_B"]).nlargest(n).index)
    top_c = set((a["pob_65"] * (1 - a["frac_D_observada_tarde_16_18"])).nlargest(n).index)

    def clase(i):
        if i in top_d and i in top_c:
            return "ambas"
        if i in top_d:
            return "solo distancia"
        if i in top_c:
            return "solo calor"
        return "ninguna"
    a["clase"] = [clase(i) for i in a.index]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, fs.WIDTH_IN * 0.60),
                                   gridspec_kw={"width_ratios": [1.15, 1]})

    colores = {"ninguna": "#f0f0f0", "ambas": "#4d4d4d",
               "solo distancia": fs.COLD, "solo calor": fs.WARM}
    g[~g["alcanzable"]].plot(ax=ax1, color="white", edgecolor="#d9d9d9", linewidth=0.15)
    for k, col in colores.items():
        sub = a[a["clase"] == k]
        if len(sub):
            sub.plot(ax=ax1, color=col, edgecolor="white", linewidth=0.12,
                     label=f"{k} ({len(sub)})")
    # El termino municipal baja trece kilometros por la Albufera y deja el
    # nucleo urbano reducido a una mancha; se encuadra sobre las secciones
    # alcanzables, que es donde ocurre la comparacion.
    x0, y0, x1, y1 = a.total_bounds
    mx, my = 0.06 * (x1 - x0), 0.06 * (y1 - y0)
    ax1.set_xlim(x0 - mx, x1 + mx)
    ax1.set_ylim(y0 - my, y1 + my)
    ax1.set_axis_off()
    ax1.legend(loc="upper left", fontsize=fs.SMALLEST_PT - 3, title="prioritaria segun",
               title_fontsize=fs.SMALLEST_PT - 3)
    fs.panel_label(ax1, "a", "Secciones prioritarias, tarde")

    # Sensibilidad: la cobertura agregada no se mueve; la priorizacion si.
    ax2.scatter(sens["cobertura_dif_puntos"], sens["pct_pob65_reclasificada"],
                s=34, color=fs.WARM, edgecolor="white", linewidth=0.5, zorder=3)
    ax2.axvline(5, color=fs.MUTED, linewidth=0.9, linestyle="--")
    ax2.axhline(5, color=fs.MUTED, linewidth=0.9, linestyle="--")
    ax2.text(1.35, 5.4, "liston del 5 %", fontsize=fs.SMALLEST_PT - 3, color=fs.MUTED)
    ax2.set_xlim(0, 6.2)
    ax2.set_ylim(0, 15)
    ax2.set_xlabel("cambio en cobertura agregada\n(puntos porcentuales)",
                   fontsize=fs.SMALLEST_PT - 1)
    ax2.set_ylabel("poblacion 65+ reclasificada (%)", fontsize=fs.SMALLEST_PT - 1)
    fs.tidy(ax2, grid="both")
    fs.panel_label(ax2, "b", "27 combinaciones de supuestos")

    fig.tight_layout()
    fig.savefig(FIGURAS / "fig8_piloto_accesibilidad.png")
    fig.savefig(FIGURAS / "fig8_piloto_accesibilidad.pdf")
    print("  fig8_piloto_accesibilidad")


if __name__ == "__main__":
    main()
