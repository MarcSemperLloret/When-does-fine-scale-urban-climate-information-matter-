#!/usr/bin/env python3
"""Contrasta las cifras del manuscrito contra las tablas finales.

Existe porque tras la reejecucion con la rejilla de pesos convergida quedo un
96,0--100,0 % antiguo en Resultados mientras el resumen ya decia 94,6--99,8 %.
Ese tipo de residuo no se ve leyendo: hay que buscarlo.

Cada comprobacion declara la cifra esperada, calculada desde la tabla de origen,
y se busca literalmente en el .tex. No valida el texto entero, solo las
magnitudes que sostienen los cuatro claims.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
TEX = BASE / "manuscrito.tex"
T = BASE / "salidas" / "tablas"


def rng(lo, hi, dec=1):
    return f"{lo:.{dec}f}" + "}{" + f"{hi:.{dec}f}"


def main() -> None:
    tex = TEX.read_text(encoding="utf-8")
    checks = []

    # --- eficiencia a k=15 -------------------------------------------------
    # La Figura 5 y el texto usan los bloques de siete dias, no el bootstrap
    # diario: el esquema de dias independientes es anticonservador.
    d = pd.read_csv(T / "p4f_bootstrap_bloques.csv")
    d = d[d["bloque_dias"] == 7]
    k15 = d[(d["k_pct"] == 15) & (d["representacion"] == "R2_era5_sombra_completa")]
    lo, hi = k15["eficiencia_pct"].min(), k15["eficiencia_pct"].max()
    checks.append(("eficiencia ERA5+sombra k=15 (bloques)", rng(lo, hi), None))

    sin = d[(d["k_pct"] == 15) & (~d["representacion"].isin(
        ["R2_era5_sombra_completa", "R5_local_sombra_completa"]))]
    checks.append(("eficiencia sin sombra completa k=15 (bloques)",
                   rng(sin["eficiencia_pct"].min(), sin["eficiencia_pct"].max()), None))

    # --- factorial con vegetacion -----------------------------------------
    f = pd.read_csv(T / "p3_factorial_veg.csv")
    f = f[~f["solar_saturada"]]
    checks.append(("reclasificados maximo (factorial veg)",
                   f"{int(f['pob65_recl_met_con_sombra'].max())}", None))

    # --- transmitancia -----------------------------------------------------
    b = pd.read_csv(T / "p3b_curva_transmitancia.csv")
    pl = b[(b["tau"] >= 0.05) & (b["tau"] <= 0.30)
           & (b["presupuesto_sol_min"] == 8) & (~b["solar_saturada"])]
    checks.append(("reclasificados en tau plausible",
                   rng(pl["pob65_reclasificada"].min(),
                       pl["pob65_reclasificada"].max(), 0), None))
    checks.append(("jaccard en tau plausible",
                   rng(pl["jaccard"].min(), pl["jaccard"].max(), 3), None))

    # --- estabilidad estacional -------------------------------------------
    e = pd.read_csv(T / "p3b_estabilidad_estacional.csv")
    e8 = e[e["presupuesto_sol_min"] == 8]
    checks.append(("jaccard estacional a 8 min",
                   rng(e8["jaccard_top20"].min(), e8["jaccard_top20"].max(), 3), None))

    # --- rutas con vegetacion ---------------------------------------------
    r = pd.read_csv(T / "p3_rutas_frontera_veg.csv")
    checks.append(("ahorro de exposicion",
                   rng(r["ahorro_sol_pct"].min(), r["ahorro_sol_pct"].max(), 0), None))
    checks.append(("coste de tiempo",
                   rng(r["coste_tiempo_pct"].min(), r["coste_tiempo_pct"].max(), 0), None))

    # --- dominancia --------------------------------------------------------
    dom = pd.read_csv(T / "p4d_dominancia_restriccion.csv")
    man = dom[dom["ventana"] == "manana_10_12"]["n_incumplen_solar"].iloc[0]
    tar = dom[dom["ventana"] == "tarde_16_18"]["n_incumplen_solar"].iloc[0]
    checks.append(("secciones que incumplen (manana)", f"{{{man}}}", None))
    checks.append(("secciones que incumplen (tarde)", f"{{{tar}}}", None))

    # --- alcance -----------------------------------------------------------
    sec = pd.read_csv(T / "p4_secciones.csv")
    checks.append(("secciones alcanzables", f"{{{int(sec['alcanzable'].sum())}}}", None))

    # --- exposicion de la ruta a las 17 h -----------------------------------
    r17 = r[r["hora"] == 17].iloc[0]
    checks.append(("exposicion ruta rapida 17 h", f"{{{r17['sol_rapida']:.2f}}}", None))
    checks.append(("exposicion ruta sombreada 17 h",
                   f"{{{r17['sol_sombreada']:.2f}}}", None))

    # --- sombra de la red ---------------------------------------------------
    sv = pd.read_csv(T / "p3_sombra_vegetacion.csv")
    s17 = sv[sv["configuracion"] == "07-15_17"].iloc[0]
    checks.append(("fraccion sombreada solo edificios 17 h",
                   f"{{{s17['solo_edificios_pct']:.1f}}}", None))
    checks.append(("fraccion sombreada con arbolado 17 h",
                   f"{{{s17['con_arbolado_pct']:.1f}}}", None))

    # --- dominancia bajo los nueve presupuestos ------------------------------
    pb = pd.read_csv(T / "p5b_dominancia_presupuesto.csv")
    checks.append(("celdas de la comprobacion de invariancia",
                   f"{{{len(pb) // 2}}}", None))
    checks.append(("alcance minimo bajo el barrido",
                   f"{{{int(pb['n_alcanzables'].min())}}}", None))
    checks.append(("alcance maximo bajo el barrido",
                   f"{{{int(pb['n_alcanzables'].max())}}}", None))

    print(f"{'magnitud':42s} {'esperado':26s} en el .tex")
    print("-" * 84)
    fallos = 0
    for nombre, esperado, _ in checks:
        ok = esperado in tex.replace(" ", "").replace("\n", "") or esperado in tex
        if not ok:
            # segunda pasada tolerante a saltos de linea dentro del comando
            plano = re.sub(r"\s+", "", tex)
            ok = re.sub(r"\s+", "", esperado) in plano
        print(f"{nombre:42s} {esperado:26s} {'OK' if ok else '*** NO APARECE ***'}")
        fallos += not ok
    print("-" * 84)
    print(f"{fallos} magnitud(es) sin correspondencia en el manuscrito")


if __name__ == "__main__":
    main()
