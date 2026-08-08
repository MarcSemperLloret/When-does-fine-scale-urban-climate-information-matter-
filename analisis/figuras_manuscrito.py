#!/usr/bin/env python3
"""Las cinco figuras principales del manuscrito, mas una suplementaria.

  F1  diseno y datos
  F2  compresion meteorologica, medida en las propias estaciones
  F3  sombra y rutas: la frontera tiempo-exposicion
  F4  estabilidad decisional y dominancia de restriccion
  F5  eficiencia de priorizacion --la figura central
  S1  capa de destinos: OSM frente a oficial

Cinco figuras y no doce: el estudio tiene mas resultados que sitio, y las
tablas del suplemento recogen el resto.
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely.geometry import Point

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE.parents[0] / "downbursts-cv-pilot" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import figure_style as fs  # noqa: E402

DATOS = BASE / "datos"
TABLAS = BASE / "salidas" / "tablas"
OSM_T = BASE / "salidas" / "tablas_osm_sensibilidad"
FIG = BASE / "salidas" / "figuras_manuscrito"
UTM = "EPSG:25830"

COLOR = {"R2_era5_sombra_completa": "#0072B2",
         "R5_local_sombra_completa": "#000000",
         "R4_local_sombra_edificios": "#D55E00",
         "R3_local_sin_sombra": "#009E73",
         "R1_era5_sin_sombra": "#CC79A7"}
ETIQ = {"R1_era5_sin_sombra": "ERA5, no shade",
        "R2_era5_sombra_completa": "ERA5 + full shade",
        "R3_local_sin_sombra": "local, no shade",
        "R4_local_sombra_edificios": "local + buildings only",
        "R5_local_sombra_completa": "reference (local + full)"}


# Abreviaturas de estacion, iguales en los dos paneles. Truncar el nombre
# producia etiquetas cortadas ("Col.legi Dioce", "Camins al G") en la figura.
ABREV = {"Col·legi Diocesà San Juan Bosco": "Col·legi D.",
         "Col·legi Diocesà": "Col·legi D.",
         "Camins al Grau": "Camins", "Penya-roja": "Penya-roja",
         "Micalet": "Micalet", "Altocúmulo": "Altocúmulo",
         "l'Olivereta": "Olivereta"}


def abrev(n):
    return ABREV.get(n, n[:12])


def guardar(fig, nombre):
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{nombre}.{ext}")
    plt.close(fig)
    print(f"  {nombre}")


def secciones():
    sec = pd.read_csv(TABLAS / "p4_secciones.csv", dtype={"CUSEC": str})
    g = gpd.read_file(f"zip://{DATOS / 'seccionado_2024.zip'}!SECC_CE_20240101.shp")
    return g[g["CUSEC"].isin(sec["CUSEC"])].to_crs(UTM).merge(sec, on="CUSEC")


# --------------------------------------------------------------------- F1
def f1_diseno(g):
    cs = gpd.read_file(DATOS / "centros_salud_gva.geojson").to_crs(UTM)
    cs = cs[cs.geometry.within(g.union_all().buffer(1500))]
    inv = pd.read_csv(TABLAS / "p0_inventario_estaciones.csv", index_col=0)
    # Las seis de tejido urbano: se excluye l'Albufera, que es municipal pero
    # marjal, para que la figura y el texto cuenten lo mismo.
    est = inv[(inv["ambito"] == "municipio") & (inv["decision"] == "usar")
              & (inv.index != "c15m250e16")]
    ge = gpd.GeoSeries([Point(r.lon, r.lat) for r in est.itertuples()],
                       crs="EPSG:4326").to_crs(UTM)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, fs.WIDTH_IN * 0.66),
                                 gridspec_kw={"width_ratios": [1, 1]})
    g.plot(ax=a1, column="pob_65", cmap="YlOrBr", linewidth=0.1,
           edgecolor="white", legend=True,
           legend_kwds={"label": "population aged 65+", "shrink": 0.5})
    cs.plot(ax=a1, color="#0072B2", markersize=13, edgecolor="white", linewidth=0.4,
            label=f"primary-care centres ({len(cs)})", zorder=3)
    ge.plot(ax=a1, color=fs.ACCENT, marker="^", markersize=26, edgecolor="white",
            linewidth=0.4, label=f"AVAMET stations ({len(est)})", zorder=4)
    a1.legend(loc="lower left", fontsize=fs.SMALLEST_PT - 1.5,
              handletextpad=0.4, borderpad=0.4)
    a1.set_axis_off()
    fs.panel_label(a1, "a", "Older population and destinations")

    # Celdas de ERA5-Land sobre el municipio, a escala.
    x0, y0, x1, y1 = g.total_bounds
    g.plot(ax=a2, color="#f0f0f0", edgecolor="white", linewidth=0.1)
    ll = gpd.GeoSeries([Point(lo, la) for la in np.arange(39.2, 39.7, 0.1)
                        for lo in np.arange(-0.6, -0.15, 0.1)],
                       crs="EPSG:4326").to_crs(UTM)
    for p in ll:
        a2.add_patch(plt.Rectangle((p.x - 4300, p.y - 5550), 8600, 11100,
                                   fill=False, edgecolor="#0072B2",
                                   linewidth=1.0, zorder=3))
    ge.plot(ax=a2, color=fs.ACCENT, marker="^", markersize=26, zorder=4)
    a2.set_xlim(x0 - 3000, x1 + 3000)
    a2.set_ylim(y0 - 2000, y1 + 2000)
    a2.set_axis_off()
    a2.text(0.02, 0.02, "ERA5-Land cell ~9 km\n6 stations -> 2 cells",
            transform=a2.transAxes, fontsize=fs.SMALLEST_PT - 2, color="#0072B2")
    fs.panel_label(a2, "b", "The regional grid, to scale")
    guardar(fig, "F1_diseno")


# --------------------------------------------------------------------- F2
def f2_compresion():  # noqa: C901
    e = pd.read_csv(TABLAS / "p2b_en_estaciones.csv")
    est = pd.read_csv(TABLAS / "p2c_error_por_estacion.csv")
    est = est[est["ventana"] == "tarde_16_18"]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, fs.WIDTH_IN * 0.70),
                                 gridspec_kw={"width_ratios": [1.15, 1]})
    y = np.arange(len(e))
    a1.barh(y - 0.19, e["pct_horas_ge30_obs"], height=0.36, color=fs.ACCENT,
            label="observed")
    a1.barh(y + 0.19, e["pct_horas_ge30_era5"], height=0.36, color="#0072B2",
            label="ERA5-Land")
    a1.set_yticks(y, [abrev(n) for n in e["nombre"]], fontsize=fs.SMALLEST_PT - 1.5)
    a1.set_xlabel("afternoon hours with T >= 30 C (%)", fontsize=fs.SMALLEST_PT - 0.5)
    a1.legend(fontsize=fs.SMALLEST_PT - 2, loc="upper center",
              bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False)
    # Las anotaciones van a la derecha de la barra mas larga (~54 %), no encima
    # de las barras, que es donde caian con el limite anterior.
    a1.set_xlim(0, 100)
    a1.annotate("range between\nstations:\n21.1 pp observed", xy=(78, 4.3),
                color=fs.ACCENT, fontsize=fs.SMALLEST_PT - 3,
                ha="center", va="center")
    a1.annotate("2.2 pp in\nERA5-Land", xy=(78, 1.3), color="#0072B2",
                fontsize=fs.SMALLEST_PT - 3, ha="center", va="center")
    fs.tidy(a1, grid="x")
    fs.panel_label(a1, "a", "Measured at the stations")

    a2.scatter(est["km_costa"], est["raw_error_era5_minus_obs"], s=42,
               color="#0072B2", edgecolor="white", linewidth=0.5, zorder=3)
    z = np.polyfit(est["km_costa"], est["raw_error_era5_minus_obs"], 1)
    xs = np.linspace(est["km_costa"].min(), est["km_costa"].max(), 10)
    a2.plot(xs, np.polyval(z, xs), color=fs.MUTED, linewidth=1.0, linestyle="--")
    for r in est.itertuples():
        # Etiquetas alternando lado para que no se peguen al borde derecho.
        dx = -8 if r.km_costa > 5.0 else 8
        a2.annotate(abrev(r.nombre), (r.km_costa, r.raw_error_era5_minus_obs),
                    textcoords="offset points", xytext=(dx, -4),
                    ha="right" if dx < 0 else "left",
                    fontsize=fs.SMALLEST_PT - 3.5)
    a2.set_xlim(1.0, 8.0)
    a2.set_xlabel("distance to the sea (km)")
    a2.set_ylabel("ERA5-Land - observed (C)", fontsize=fs.SMALLEST_PT - 0.5)
    fs.tidy(a2)
    fs.panel_label(a2, "b", "Error towards the coast")
    guardar(fig, "F2_compresion")


# --------------------------------------------------------------------- F3
def f3_sombra():
    ed = pd.read_csv(TABLAS / "p3_rutas_frontera.csv")
    vg = pd.read_csv(TABLAS / "p3_rutas_frontera_veg.csv")
    sv = pd.read_csv(TABLAS / "p3_sombra_vegetacion.csv")
    sv = sv[sv["configuracion"].str.startswith("07-15")].copy()
    sv["hora"] = sv["configuracion"].str[-2:].astype(int)
    sv = sv.sort_values("hora")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, fs.WIDTH_IN * 0.58))
    a1.plot(sv["hora"], sv["solo_edificios_pct"], marker="o", markersize=4,
            color="#D55E00", label="buildings only")
    a1.plot(sv["hora"], sv["con_arbolado_pct"], marker="o", markersize=4,
            color="#009E73", label="buildings + trees")
    a1.fill_between(sv["hora"], sv["solo_edificios_pct"], sv["con_arbolado_pct"],
                    color="#009E73", alpha=0.15, linewidth=0)
    a1.set_xlabel("local hour")
    a1.set_ylabel("pedestrian network in shade (%)", fontsize=fs.SMALLEST_PT - 0.5)
    a1.set_xticks(sv["hora"])
    a1.legend(fontsize=fs.SMALLEST_PT - 2, loc="upper center")
    fs.tidy(a1)
    fs.panel_label(a1, "a", "Trees triple the shaded fraction")

    # Color codifica la capa de sombra; el estilo de linea, el tipo de ruta.
    # Mezclar ambos en la leyenda daba cuatro entradas largas en una figura
    # pequena, asi que se separan en dos leyendas de dos entradas.
    for d, col in ((ed, "#D55E00"), (vg, "#009E73")):
        a2.plot(d["hora"], d["sol_rapida"], marker="o", markersize=4, color=col)
        a2.plot(d["hora"], d["sol_sombreada"], marker="s", markersize=4,
                linestyle="--", color=col)
    from matplotlib.lines import Line2D
    l1 = a2.legend(handles=[Line2D([], [], color="#D55E00", label="buildings only"),
                            Line2D([], [], color="#009E73", label="+ trees")],
                   fontsize=fs.SMALLEST_PT - 2.5, loc="upper right", frameon=False)
    a2.add_artist(l1)
    a2.legend(handles=[Line2D([], [], color="grey", marker="o", label="fastest"),
                       Line2D([], [], color="grey", marker="s", linestyle="--",
                              label="least exposed")],
              fontsize=fs.SMALLEST_PT - 2.5, loc="lower left", frameon=False)
    a2.set_xlabel("local hour")
    a2.set_ylabel("equiv. open-sky exposure (min)", fontsize=fs.SMALLEST_PT - 0.5)
    a2.set_xticks(ed["hora"])
    fs.tidy(a2)
    fs.panel_label(a2, "b", "Time-exposure frontier")
    guardar(fig, "F3_sombra_rutas")


# --------------------------------------------------------------------- F4
def f4_estabilidad():
    c = pd.read_csv(TABLAS / "p4c_curva_phi.csv")
    c = c[c["capa_sombra"] == "edificios_vegetacion"]
    dom = pd.read_csv(TABLAS / "p4d_dominancia_restriccion.csv")

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(fs.WIDTH_IN, fs.WIDTH_IN * 0.92),
                                 gridspec_kw={"height_ratios": [1.7, 1]})
    for v, col, lab in (("manana_10_12", "#0072B2", "morning 10-12 h"),
                        ("tarde_16_18", fs.ACCENT, "afternoon 16-18 h")):
        s_ = c[c["ventana"] == v].sort_values("phi_max")
        a1.plot(s_["phi_max"], s_["pob65_reclasificada"] / 1000, marker="o",
                markersize=4, color=col, label=lab)
        sat = s_[s_["saturada"]]
        a1.scatter(sat["phi_max"], sat["pob65_reclasificada"] / 1000, s=95,
                   facecolors="none", edgecolors=col, linewidth=1.3, zorder=4)
    a1.axvline(0.40, color=fs.MUTED, linestyle=":", linewidth=1.0)
    a1.text(0.415, 9.5, "phi = 0.40 anchored", fontsize=fs.SMALLEST_PT - 2.5,
            color=fs.MUTED)
    a1.set_xlabel("maximum exposed fraction of the route")
    a1.set_ylabel("65+ reclassified (thousands)", fontsize=fs.SMALLEST_PT - 0.5)
    a1.legend(fontsize=fs.SMALLEST_PT - 2, loc="lower right")
    fs.tidy(a1)
    fs.panel_label(a1, "a", "Hollow circle: saturated constraint")

    # Las claves son las del CSV, en castellano; solo la etiqueta se traduce.
    cmap = {"dominada_por_sol": "#D55E00", "mixta": "#F0E442",
            "sensible_a_termica": "#009E73"}
    etq = {"dominada_por_sol": "sun-dominated", "mixta": "mixed",
           "sensible_a_termica": "thermally sensitive"}
    for i, v in enumerate(["tarde_16_18", "manana_10_12"]):
        s_ = dom[dom["ventana"] == v].sort_values("k_pct")
        for j, r in enumerate(s_.itertuples()):
            a2.add_patch(plt.Rectangle((j - 0.45, i - 0.36), 0.9, 0.72,
                                       color=cmap[r.regimen]))
            a2.text(j, i, f"{r.cociente_falla_cupo:.2f}", ha="center",
                    va="center", fontsize=fs.SMALLEST_PT - 1.5)
    a2.set_xlim(-0.6, 4.6)
    a2.set_ylim(-0.65, 1.55)
    a2.set_xticks(range(5), [f"k={k}%" for k in sorted(dom["k_pct"].unique())],
                  fontsize=fs.SMALLEST_PT - 1)
    a2.set_yticks([0, 1], ["afternoon", "morning"], fontsize=fs.SMALLEST_PT - 1)
    for k, col in cmap.items():
        a2.bar(0, 0, color=col, label=etq[k])
    a2.legend(fontsize=fs.SMALLEST_PT - 2.5, loc="lower center",
              bbox_to_anchor=(0.5, -0.55), ncol=3, frameon=False)
    a2.spines[["top", "right", "left", "bottom"]].set_visible(False)
    a2.tick_params(length=0)
    fs.panel_label(a2, "b", "Regime: N fail / quota")
    guardar(fig, "F4_estabilidad")


# --------------------------------------------------------------------- F5
def f5_eficiencia():
    # Bandas del bootstrap por bloques de siete dias, no de dias sueltos. El
    # esquema de dias independientes es anticonservador --los bloques ensanchan
    # el intervalo un 58 % de media-- y no hay razon para publicar como
    # principal el intervalo que sabemos que es demasiado estrecho. El bootstrap
    # diario queda en el suplemento.
    d = pd.read_csv(TABLAS / "p4f_bootstrap_bloques.csv")
    d = d[d["bloque_dias"] == 7].rename(
        columns={"ic_lo": "eficiencia_ic_lo", "ic_hi": "eficiencia_ic_hi"})
    fig, axes = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, fs.WIDTH_IN * 0.58),
                             sharey=True)
    for ax, v, tit in zip(axes, ["manana_10_12", "tarde_16_18"],
                          ["Morning 10-12 h", "Afternoon 16-18 h"]):
        for r in ["R2_era5_sombra_completa", "R4_local_sombra_edificios",
                  "R3_local_sin_sombra", "R1_era5_sin_sombra"]:
            s = d[(d["ventana"] == v) & (d["representacion"] == r)].sort_values("k_pct")
            ax.plot(s["k_pct"], s["eficiencia_pct"], marker="o", markersize=3.5,
                    color=COLOR[r], linewidth=1.5, label=ETIQ[r])
            ax.fill_between(s["k_pct"], s["eficiencia_ic_lo"], s["eficiencia_ic_hi"],
                            color=COLOR[r], alpha=0.18, linewidth=0)
        ax.axhline(100, color="black", linewidth=0.9, linestyle="--")
        ax.set_xlabel("prioritisation capacity k (%)")
        ax.set_xticks([5, 10, 15, 20, 25])
        ax.set_ylim(20, 105)
        fs.tidy(ax)
        fs.panel_label(ax, "a" if v.startswith("man") else "b", tit)
    axes[0].set_ylabel("benefit retained (%)", fontsize=fs.SMALLEST_PT - 0.5)
    axes[0].text(5.5, 101.5, "highest-information reference",
                 fontsize=fs.SMALLEST_PT - 3.5, color="black")
    axes[1].legend(fontsize=fs.SMALLEST_PT - 3, loc="lower right")
    guardar(fig, "F5_eficiencia")


# --------------------------------------------------------------------- S1
def s1_destinos(g):
    r = pd.read_csv(TABLAS / "p4e_comparacion_centros.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, fs.WIDTH_IN * 0.44))
    x = np.arange(2)
    for i, (col, lab, esc) in enumerate([("n_centros", "number of centres", 1.0),
                                         ("pct_pob65_alcanzable",
                                          "% of 65+ population reachable", 1.0)]):
        ax = (a1, a2)[i]
        ax.bar(x, r[col], color=["#CC79A7", "#0072B2"], width=0.55)
        for j, v in enumerate(r[col]):
            ax.text(j, v, f"{v:.4g}", ha="center", va="bottom",
                    fontsize=fs.SMALLEST_PT - 1)
        ax.set_xticks(x, ["OSM", "official register"])
        ax.set_ylabel(lab, fontsize=fs.SMALLEST_PT - 0.5)
        fs.tidy(ax)
    fs.panel_label(a1, "a", "Fewer centres...")
    fs.panel_label(a2, "b", "...and more population reached")
    guardar(fig, "S1_destinos")


def main():
    fs.apply()
    FIG.mkdir(parents=True, exist_ok=True)
    g = secciones()
    print("figuras del manuscrito:")
    f1_diseno(g)
    f2_compresion()
    f3_sombra()
    f4_estabilidad()
    f5_eficiencia()
    s1_destinos(g)


if __name__ == "__main__":
    main()
