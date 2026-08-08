#!/usr/bin/env python3
"""Figuras minimas de las Puertas 0 y 1 del plan de viabilidad.

Cubre los puntos 1 a 6 de la seccion 7 del plan --los que dependen unicamente
de observaciones-- reutilizando el estilo tipografico de los manuscritos
anteriores para que las tres piezas se lean como una misma publicacion.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE.parents[0] / "downbursts-cv-pilot" / "scripts"))
import figure_style as fs  # noqa: E402

TABLAS = BASE / "salidas" / "tablas"
FIGURAS = BASE / "salidas" / "figuras"
PANEL = "panel_largo"

AMBITO_COLOR = {"municipio": "#b2182b", "metropolitano": "#D55E00",
                "periurbano": "#0072B2"}


def guardar(fig, nombre: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGURAS / f"{nombre}.png")
    fig.savefig(FIGURAS / f"{nombre}.pdf")
    plt.close(fig)
    print(f"  {nombre}")


COSTA = [(39.75, -0.210), (39.63, -0.280), (39.55, -0.310), (39.50, -0.318),
         (39.47, -0.322), (39.44, -0.325), (39.40, -0.330), (39.36, -0.315),
         (39.30, -0.290), (39.22, -0.250)]


def corto(nombre: str) -> str:
    return nombre.replace("València - ", "").split(" - ")[0].split("/")[0][:18]


def fig1_mapa(inv: pd.DataFrame) -> None:
    # Dos panales porque en un solo mapa las siete estaciones del municipio
    # caen dentro de tres kilometros y sus etiquetas se pisan unas a otras.
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, fs.WIDTH_IN * 0.62))

    for ax in (ax1, ax2):
        ax.plot([c[1] for c in COSTA], [c[0] for c in COSTA], color=fs.MUTED,
                linewidth=1.0, zorder=1)
        ax.set_aspect(1 / np.cos(np.radians(39.47)))
        fs.tidy(ax, grid="both")

    for amb, g in inv.groupby("ambito"):
        usa = g["decision"] == "usar"
        ax1.scatter(g.loc[usa, "lon"], g.loc[usa, "lat"], s=26,
                    color=AMBITO_COLOR[amb], edgecolor="white", linewidth=0.5,
                    label=f"{amb} ({usa.sum()})", zorder=3)
        ax1.scatter(g.loc[~usa, "lon"], g.loc[~usa, "lat"], s=20, marker="x",
                    color=AMBITO_COLOR[amb], alpha=0.4, linewidth=0.8, zorder=2)
    ax1.add_patch(plt.Rectangle((-0.44, 39.34), 0.13, 0.17, fill=False,
                                edgecolor=fs.INK, linewidth=0.8, zorder=4))
    ax1.set_xlabel("longitud")
    ax1.set_ylabel("latitud")
    ax1.legend(loc="lower left", fontsize=fs.SMALLEST_PT - 2, handletextpad=0.3)
    fs.panel_label(ax1, "a", "Area de estudio (30 km)")

    mun = inv[(inv["ambito"] == "municipio") & (inv["decision"] == "usar")]
    otras = inv[(inv["decision"] == "usar") & (inv["ambito"] != "municipio")]
    ax2.scatter(otras["lon"], otras["lat"], s=26, color=AMBITO_COLOR["metropolitano"],
                edgecolor="white", linewidth=0.5, zorder=3)
    ax2.scatter(mun["lon"], mun["lat"], s=34, color=AMBITO_COLOR["municipio"],
                edgecolor="white", linewidth=0.5, zorder=4)
    # Las etiquetas se reparten a izquierda y derecha segun donde haya sitio.
    lados = {"c15m250e24": (6, -4), "c15m250e30": (6, 6), "c15m250e15": (-6, 5),
             "c15m250e11": (-6, -10), "c15m250e08": (6, -10),
             "c15m250e26": (6, -12), "c15m250e16": (6, 0)}
    for sid, r in mun.iterrows():
        dx, dy = lados.get(sid, (5, 3))
        ax2.annotate(corto(r["nombre"]), (r["lon"], r["lat"]),
                     textcoords="offset points", xytext=(dx, dy),
                     ha="left" if dx > 0 else "right",
                     fontsize=fs.SMALLEST_PT - 2.5, color=AMBITO_COLOR["municipio"])
    ax2.set_xlim(-0.45, -0.29)
    ax2.set_ylim(39.33, 39.53)
    ax2.set_xlabel("longitud")
    fs.panel_label(ax2, "b", "Municipio de Valencia")
    guardar(fig, "fig1_mapa_estaciones")


def fig2_cobertura(inv: pd.DataFrame) -> None:
    cols = [c for c in inv.columns if c.startswith("cob_")]
    anios = [int(c.split("_")[1]) for c in cols]
    urb = inv[inv["ambito"].isin(["municipio", "metropolitano"])].copy()
    urb = urb.sort_values(["ambito", "km_centro"])
    m = urb[cols].to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(fs.WIDTH_IN, fs.WIDTH_IN * 0.72))
    im = ax.imshow(m, aspect="auto", cmap="YlGnBu", vmin=0, vmax=100)
    ax.set_xticks(range(len(anios)), anios)
    ax.set_yticks(range(len(urb)),
                  [corto(n) for n in urb["nombre"]],
                  fontsize=fs.SMALLEST_PT - 1.5)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            if m[i, j] >= 80:
                ax.text(j, i, "*", ha="center", va="center", color="white",
                        fontsize=fs.SMALLEST_PT)
    # 2024 no aparece: es el ano confirmatorio congelado del proyecto de
    # reventones y este estudio no lo mira.
    ax.set_xlabel("verano (2024 reservado como muestra confirmatoria)")
    ax.set_title("Cobertura estival de temperatura validada (%)\n"
                 "asterisco: verano utilizable (>=80 %)")
    fig.colorbar(im, ax=ax, label="cobertura (%)", fraction=0.035, pad=0.02)
    guardar(fig, "fig2_cobertura_temporal")


def fig3_ciclo_horario() -> None:
    d = pd.read_csv(TABLAS / f"p1_dispersion_horaria_{PANEL}.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(fs.WIDTH_IN, fs.WIDTH_IN * 0.55))
    h = d.index.to_numpy()
    ax.fill_between(h, d["disp_p25"], d["disp_p75"], color=fs.WARM, alpha=0.16,
                    linewidth=0, label="P25-P75 de las horas")
    ax.plot(h, d["disp_mediana"], color=fs.WARM, linewidth=1.8,
            label="P90-P10 entre estaciones")
    ax.plot(h, d["iqr_mediana"], color=fs.COLD, linewidth=1.5, linestyle="--",
            label="P75-P25 entre estaciones")
    ax.axhline(1.0, color=fs.MUTED, linewidth=0.8, linestyle=":")
    ax.text(9.3, 1.07, "liston del plan: 1 C", color=fs.MUTED,
            fontsize=fs.SMALLEST_PT - 1.5)
    ax.axvspan(0, 6, color=fs.FAINT, zorder=0)
    ax.text(3, 0.35, "noche", ha="center", color=fs.MUTED,
            fontsize=fs.SMALLEST_PT - 1)
    ax.set_xlabel("hora local")
    ax.set_ylabel("dispersion entre estaciones (C)")
    ax.set_xlim(0, 23)
    ax.set_ylim(0.2, 4.0)
    ax.set_xticks(range(0, 24, 3))
    ax.set_title("Ciclo horario de la heterogeneidad termica intraurbana\n"
                 "7 estaciones, veranos 2019-2023 y 2025",
                 fontsize=fs.SMALLEST_PT + 0.5)
    ax.legend(loc="upper right", fontsize=fs.SMALLEST_PT - 1)
    fs.tidy(ax)
    guardar(fig, "fig3_ciclo_horario_dispersion")


def fig4_anomalia_estacion_hora(inv: pd.DataFrame) -> None:
    a = pd.read_csv(TABLAS / f"p1_anomalia_estacion_hora_{PANEL}.csv", index_col=0)
    nombres = [corto(inv.loc[s, "nombre"]) for s in a.index]
    v = np.abs(a.to_numpy()).max()

    fig, ax = plt.subplots(figsize=(fs.WIDTH_IN, fs.WIDTH_IN * 0.55))
    im = ax.imshow(a.to_numpy(), aspect="auto", cmap="RdBu_r", vmin=-v, vmax=v)
    ax.set_xticks(range(0, 24, 3), range(0, 24, 3))
    ax.set_yticks(range(len(a)), nombres, fontsize=fs.SMALLEST_PT - 1)
    ax.set_xlabel("hora local")
    ax.set_title("Anomalia media frente a la mediana de la red (C)")
    fig.colorbar(im, ax=ax, label="anomalia (C)", fraction=0.035, pad=0.02)
    guardar(fig, "fig4_anomalia_estacion_hora")


def fig5_estabilidad(inv: pd.DataFrame) -> None:
    por_anio = pd.read_csv(TABLAS / f"p1_anomalia_nocturna_por_anio_{PANEL}.csv",
                           index_col=0)
    ranking = pd.read_csv(TABLAS / f"p1_estabilidad_ranking_{PANEL}.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, fs.WIDTH_IN * 0.62),
                                   gridspec_kw={"width_ratios": [2.1, 1]})
    # Las etiquetas se apilan cuando dos series acaban juntas, asi que se
    # separan verticalmente por orden de llegada.
    fin = por_anio.iloc[-1].sort_values(ascending=False)
    for k, sid in enumerate(fin.index):
        amb = inv.loc[sid, "ambito"]
        ax1.plot(por_anio.index, por_anio[sid], marker="o", markersize=3.0,
                 linewidth=1.1, color=AMBITO_COLOR[amb])
        ax1.annotate(corto(inv.loc[sid, "nombre"]), (2025.35, fin.iloc[k]),
                     textcoords="offset points", xytext=(0, -3),
                     fontsize=fs.SMALLEST_PT - 3, color=AMBITO_COLOR[amb])
    ax1.axhline(0, color=fs.MUTED, linewidth=0.8)
    ax1.set_xlabel("verano")
    ax1.set_ylabel("anomalia nocturna (C)")
    ax1.set_xlim(2018.6, 2028.6)
    ax1.set_xticks([2019, 2021, 2023, 2025])
    fs.tidy(ax1)
    fs.panel_label(ax1, "a", "Anomalia nocturna por verano")

    ax2.hist(ranking["spearman"], bins=np.arange(0.955, 1.015, 0.01),
             color=fs.NEUTRAL, edgecolor="white", linewidth=0.6)
    ax2.set_xlabel("Spearman", fontsize=fs.SMALLEST_PT)
    ax2.set_ylabel("pares de veranos")
    ax2.set_xticks([0.96, 0.98, 1.00])
    fs.tidy(ax2)
    fs.panel_label(ax2, "b", "Ranking")
    guardar(fig, "fig5_estabilidad_rankings")


def fig6_episodios(inv: pd.DataFrame) -> None:
    ep = pd.read_csv(TABLAS / f"p1_dispersion_episodios_{PANEL}.csv", index_col=0)
    noches = pd.read_csv(TABLAS / f"p1_noches_calidas_{PANEL}.csv", index_col=0)
    noches = noches.sort_values("pct_torridas_comunes")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, fs.WIDTH_IN * 0.62))
    ax1.plot(ep.index, ep["ordinario"], color=fs.COLD, linewidth=1.6,
             label="dias ordinarios")
    ax1.plot(ep.index, ep["calido"], color=fs.WARM, linewidth=1.6,
             label="episodios calidos")
    ax1.set_xlabel("hora local")
    ax1.set_ylabel("dispersion (C)")
    ax1.set_xticks(range(0, 24, 6))
    ax1.legend(loc="lower center", fontsize=fs.SMALLEST_PT - 2)
    fs.tidy(ax1)
    fs.panel_label(ax1, "a", "Por regimen")

    y = np.arange(len(noches))
    ax2.barh(y, noches["pct_torridas_comunes"], color=fs.WARM, height=0.62)
    ax2.set_yticks(y, [corto(n) for n in noches["nombre"]],
                   fontsize=fs.SMALLEST_PT - 2.5)
    ax2.set_xlabel("noches Tmin >= 25 C (%)", fontsize=fs.SMALLEST_PT - 0.5)
    fs.tidy(ax2, grid="x")
    fs.panel_label(ax2, "b", "256 noches comunes")
    guardar(fig, "fig6_episodios_y_noches_torridas")


def main() -> None:
    fs.apply()
    FIGURAS.mkdir(parents=True, exist_ok=True)
    inv = pd.read_csv(TABLAS / "p0_inventario_estaciones.csv", index_col=0)
    print("figuras:")
    fig1_mapa(inv)
    fig2_cobertura(inv)
    fig3_ciclo_horario()
    fig4_anomalia_estacion_hora(inv)
    fig5_estabilidad(inv)
    fig6_episodios(inv)
    fig7_escalas()




def fig7_escalas() -> None:
    """La figura que separa lo que la primera pasada habia mezclado."""
    d = pd.read_csv(TABLAS / "p1b_dispersion_por_escala.csv")
    a = pd.read_csv(TABLAS / "p1b_anomalias_intramunicipal_barrios.csv", index_col=0)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, fs.WIDTH_IN * 0.58))

    escalas = ["intramunicipal_barrios", "intramunicipal_total", "metropolitano"]
    etiq = ["barrios de\nValencia (6)", "municipio\ncompleto (7)", "area metro-\npolitana (16)"]
    x = np.arange(len(escalas))
    for k, (ven, col, lab) in enumerate([("noche_00_06", fs.COLD, "noche 00-06 h"),
                                         ("diurna_10_18", fs.WARM, "dia 10-18 h")]):
        v = [d[(d.escala == e) & (d.ventana == ven)]["disp_p90_p10"].iloc[0] for e in escalas]
        ax1.bar(x + (k - 0.5) * 0.36, v, width=0.34, color=col, label=lab)
    ax1.axhline(1.0, color=fs.MUTED, linewidth=0.8, linestyle=":")
    ax1.set_xticks(x, etiq, fontsize=fs.SMALLEST_PT - 2.5)
    ax1.set_ylabel("dispersion P90-P10 (C)")
    ax1.legend(fontsize=fs.SMALLEST_PT - 2, loc="upper left")
    fs.tidy(ax1)
    fs.panel_label(ax1, "a", "La escala manda")

    # Entre barrios el orden termico se invierte: quien es mas calido de noche
    # no lo es de dia. Un mapa unico de "barrios calientes" seria incorrecto.
    for sid, r in a.iterrows():
        ax2.plot([0, 1], [r["dT_noche_00_06"], r["dT_diurna_10_18"]],
                 marker="o", markersize=3.5, linewidth=1.2,
                 color=AMBITO_COLOR["municipio"])
        ax2.annotate(corto(r["nombre"]), (1, r["dT_diurna_10_18"]),
                     textcoords="offset points", xytext=(5, -2),
                     fontsize=fs.SMALLEST_PT - 3, color=AMBITO_COLOR["municipio"])
    ax2.axhline(0, color=fs.MUTED, linewidth=0.8)
    ax2.set_xticks([0, 1], ["noche", "dia"])
    ax2.set_xlim(-0.15, 2.4)
    ax2.set_ylabel("anomalia intramunicipal (C)")
    fs.tidy(ax2)
    fs.panel_label(ax2, "b", "El orden se invierte")
    guardar(fig, "fig7_escalas_y_ventanas")


if __name__ == "__main__":
    main()
