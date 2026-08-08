#!/usr/bin/env python3
"""Altura de trabajo definitiva: LiDAR donde lo hay, calibrado donde no.

El contraste con el nDSM deja dos cosas claras.

**Para edificios de siete plantas o mas, el supuesto de 3,0 m/planta era casi
exacto**: sesgo entre -0,2 y +0,5 m y metros por planta implicitos de 2,93 a
2,99, estables en todos los tamanos de huella.

**Para edificios de una a tres plantas era malo**: sesgo de -4,2 m y metros por
planta implicitos de 4,1. Y no es contaminacion de borde --se comprobo cruzando
tramo de plantas con numero de celdas y el sesgo no disminuye al crecer la
huella, se mantiene entre -2,5 y -5,6 m-- sino que las naves, los locales
comerciales y la edificacion industrial de Valencia tienen plantas altas de
verdad. La capa de sombra anterior, por tanto, **subestimaba sistematicamente
la sombra de la edificacion baja**.

De ahi la regla: altura del LiDAR donde la huella da estadistica utilizable, y
metros por planta calibrados **por tramo** donde no.

Salida: datos/edificios_valencia_lidar.gpkg (columna altura_final_m)
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos"
TABLAS = BASE / "salidas" / "tablas"

TRAMOS = [0, 3, 6, 10, 60]
ETIQUETAS = ["1-3", "4-6", "7-10", ">10"]
MIN_CELDAS = 4
SOBREALZADO_M = 1.0


def main() -> None:
    g = gpd.read_file(DATOS / "edificios_valencia_lidar.gpkg", layer="edificios")
    g["tramo"] = pd.cut(g["plantas"], TRAMOS, labels=ETIQUETAS)
    con = (g["n_celdas"].fillna(0) >= MIN_CELDAS) & g["h_p75"].notna()

    # Calibracion de metros por planta por tramo, con las partes que si tienen
    # LiDAR utilizable.
    cal = ((g.loc[con, "h_p75"] - SOBREALZADO_M) / g.loc[con, "plantas"]) \
        .groupby(g.loc[con, "tramo"], observed=True).median()
    print("metros por planta calibrados con LiDAR:")
    print(cal.round(2).to_string())

    mpp = g["tramo"].map(cal).astype(float).fillna(3.0)
    altura_calibrada = g["plantas"] * mpp + SOBREALZADO_M

    g["altura_final_m"] = np.where(con, g["h_p75"], altura_calibrada)
    g["fuente_altura"] = np.where(con, "lidar_p75", "plantas_calibradas")

    print(f"\naltura final: LiDAR en {int(con.sum()):,} partes "
          f"({100*con.mean():.1f} %), calibrada en {int((~con).sum()):,}")
    for col, etq in (("altura_m", "supuesto anterior 3 m/planta"),
                     ("altura_final_m", "altura final")):
        print(f"  {etq:32s} mediana {g[col].median():5.1f} m  "
              f"P90 {g[col].quantile(0.9):5.1f} m  media {g[col].mean():5.1f} m")

    # Cuanto cambia la sombra potencial: la longitud de sombra es proporcional
    # a la altura, asi que el cociente de alturas medias es el factor de cambio.
    factor = float(g["altura_final_m"].mean() / g["altura_m"].mean())
    print(f"\n  la altura media sube un factor {factor:.2f}: la sombra proyectada "
          "crece aproximadamente en la misma proporcion")

    resumen = {
        "metros_por_planta_calibrados": {k: round(float(v), 2) for k, v in cal.items()},
        "n_lidar": int(con.sum()), "n_calibradas": int((~con).sum()),
        "altura_mediana_antes_m": round(float(g["altura_m"].median()), 1),
        "altura_mediana_despues_m": round(float(g["altura_final_m"].median()), 1),
        "factor_altura_media": round(factor, 3),
    }
    (TABLAS / "p3_altura_final.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

    g[["plantas", "altura_m", "altura_lidar_m", "altura_final_m", "fuente_altura",
       "n_celdas", "h_p75", "area_m2", "geometry"]].to_file(
        DATOS / "edificios_valencia_lidar.gpkg", driver="GPKG", layer="edificios")
    print(f"\nescrito {DATOS / 'edificios_valencia_lidar.gpkg'}")


if __name__ == "__main__":
    main()
