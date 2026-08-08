#!/usr/bin/env python3
"""Sombra de edificios mas arbolado, desde los nDSM del CNIG.

Se anade la vegetacion al campo de obstruccion como

    H(x, y) = max(H_edificio, H_vegetacion)

con la altura de vegetacion tomada directamente del MDSnV2,5 de 2.a cobertura
(hojas 0696, 0722 y 0747), que ya viene normalizada a altura sobre el terreno.
Que las dos capas compartan la misma definicion de altura es la razon por la
que se espero a tener el LiDAR en vez de estimar arboles de un inventario.

**La copa se trata como opaca.** No es cierto --una copa transmite entre el 5 y
el 30 % de la radiacion segun especie y epoca-- pero sin una referencia
defendible para Valencia, inventarse una transmitancia repetiria el error del
peso arbitrario. Asi que se calculan los dos extremos y se reporta el intervalo:

    solo edificios          cota inferior del beneficio de sombra
    edificios + copa opaca  cota superior

La contribucion marginal del arbolado es la diferencia entre ambos, y el
resultado real esta dentro.

Se descarta la vegetacion por debajo de dos metros: cesped y arbusto bajo no
dan sombra utilizable a un peaton, y a las elevaciones solares de estas
ventanas su sombra cae sobre si misma.

Salidas:
  datos/sombra_aristas_veg.parquet
  salidas/tablas/p3_sombra_vegetacion.csv
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import Resampling, reproject

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3_sombra_edificios import (HORAS, muestrear_red, posiciones_solares,  # noqa: E402
                                 rasterizar_alturas, sombra)

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos"
TABLAS = BASE / "salidas" / "tablas"
UTM = "EPSG:25830"

HOJAS = ["0696", "0722", "0747"]
VEG = "NDSM-VEGETACION-H30-{}-COB2.tif"

# Altura minima de vegetacion que se considera capaz de dar sombra a un peaton.
VEG_MIN_M = 2.0
# Techo de cordura: por encima de esto es casi seguro edificio mal clasificado.
VEG_MAX_M = 40.0


def mosaico_vegetacion(shape, transform) -> np.ndarray:
    """Vegetacion de las tres hojas remuestreada a la rejilla de sombra."""
    out = np.zeros(shape, dtype="float32")
    for hoja in HOJAS:
        ruta = DATOS / VEG.format(hoja)
        if not ruta.exists():
            print(f"  AVISO: falta {ruta.name}; esa hoja queda sin vegetacion")
            continue
        with rasterio.open(ruta) as src:
            buf = np.zeros(shape, dtype="float32")
            reproject(source=rasterio.band(src, 1), destination=buf,
                      src_transform=src.transform, src_crs=src.crs,
                      dst_transform=transform, dst_crs=UTM,
                      src_nodata=src.nodata, dst_nodata=0.0,
                      resampling=Resampling.max)
            buf[~np.isfinite(buf)] = 0.0
            buf[(buf < VEG_MIN_M) | (buf > VEG_MAX_M)] = 0.0
            out = np.maximum(out, buf)
            print(f"  hoja {hoja}: {100*(buf > 0).mean():.1f} % de celdas con arbolado")
    return out


def main() -> None:
    print("posiciones solares y red")
    sol = posiciones_solares()
    aristas, puntos, idx_arista = muestrear_red()

    print("\nedificios")
    ed = gpd.read_file(DATOS / "edificios_valencia_lidar.gpkg", layer="edificios")
    ed["altura_m"] = ed["altura_final_m"]
    x0, y0 = puntos.min(axis=0) - 500
    x1, y1 = puntos.max(axis=0) + 500
    from shapely.geometry import box
    ed = ed[ed.intersects(box(x0, y0, x1, y1))]
    H_ed, transform = rasterizar_alturas(ed, (x0, y0, x1, y1))

    print("\nvegetacion")
    H_veg = mosaico_vegetacion(H_ed.shape, transform)
    H = np.maximum(H_ed, H_veg)
    solo_veg = (H_veg > 0) & (H_ed <= 0)
    print(f"  celdas con obstruccion: {100*(H > 0).mean():.1f} % "
          f"(solo edificio {100*((H_ed > 0) & ~solo_veg).mean():.1f} %, "
          f"solo arbolado {100*solo_veg.mean():.1f} %)")
    print(f"  altura de arbolado donde lo hay: mediana {np.median(H_veg[H_veg > 0]):.1f} m, "
          f"P90 {np.percentile(H_veg[H_veg > 0], 90):.1f} m")

    inv_t = ~transform
    cols, fils = inv_t * (puntos[:, 0], puntos[:, 1])
    cols = np.clip(cols.astype(int), 0, H.shape[1] - 1)
    fils = np.clip(fils.astype(int), 0, H.shape[0] - 1)

    print("\nsombra con arbolado")
    resultados = {}
    for r in sol.itertuples():
        m = sombra(H, r.elevacion, r.azimut)
        clave = f"{r.fecha}_{r.hora:02d}"
        resultados[clave] = m[fils, cols]
        print(f"  {clave}  puntos en sombra {100*resultados[clave].mean():5.1f} %")

    df = pd.DataFrame(resultados)
    df["arista"] = idx_arista
    frac = df.groupby("arista").mean()
    frac.to_parquet(DATOS / "sombra_aristas_veg.parquet")

    # Comparacion con la version de solo edificios.
    solo_ed = pd.read_parquet(DATOS / "sombra_aristas.parquet")
    L = aristas.set_index("arista")["length"]
    filas = []
    for k in resultados:
        a = solo_ed[k].reindex(L.index).fillna(0)
        b = frac[k].reindex(L.index).fillna(0)
        filas.append({"configuracion": k,
                      "solo_edificios_pct": round(100 * float((a * L).sum() / L.sum()), 2),
                      "con_arbolado_pct": round(100 * float((b * L).sum() / L.sum()), 2)})
    comp = pd.DataFrame(filas)
    comp["aporte_arbolado_pp"] = (comp["con_arbolado_pct"]
                                  - comp["solo_edificios_pct"]).round(2)
    comp["aporte_relativo_pct"] = (100 * comp["aporte_arbolado_pp"]
                                   / comp["solo_edificios_pct"]).round(1)
    comp.to_csv(TABLAS / "p3_sombra_vegetacion.csv", index=False, encoding="utf-8")

    (TABLAS / "p3_sombra_vegetacion.json").write_text(json.dumps({
        "veg_min_m": VEG_MIN_M, "veg_max_m": VEG_MAX_M,
        "tratamiento_copa": "opaca (cota superior del beneficio de sombra)",
        "hojas": HOJAS,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n--- sombra de la red, ponderada por longitud ---")
    print(comp.to_string(index=False))


if __name__ == "__main__":
    main()
