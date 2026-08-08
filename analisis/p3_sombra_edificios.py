#!/usr/bin/env python3
"""Sombra horaria proyectada por los edificios sobre la red peatonal.

Primera fase: **solo geometria de edificios**. Ni arbolado ni indice termico.
La afirmacion que sostiene es "accesibilidad condicionada por exposicion
solar", no "ruta termicamente segura".

Metodo. Con 8.800 km de red y 214.000 partes de edificio, trazar un rayo por
punto de muestreo y edificio candidato no es viable. Se usa el metodo raster
habitual (desplazamiento iterativo del modelo digital de superficie): se
rasteriza la altura de los edificios y, para cada posicion solar, se recorre el
raster en direccion al sol comparando la altura encontrada con la que haria
falta para tapar el sol a esa distancia,

    tapa si   H(x + n*paso*u) > n*paso*tan(elevacion)

que es exacto salvo por la discretizacion, y se resuelve con desplazamientos de
array en vez de con geometria.

Posiciones solares: tres fechas representativas por ventana --15 de junio, 15
de julio y 15 de agosto-- por cada hora analizada. La elevacion solar a una
misma hora varia unos diez grados a lo largo del verano, asi que tres fechas la
muestrean de forma razonable; cada hora real se asigna despues a la fecha mas
proxima. Es una aproximacion declarada, y su sensibilidad debe medirse.

Salidas:
  datos/sombra_aristas.parquet   fraccion sombreada por arista y configuracion
  salidas/tablas/p3_sombra_*.csv
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
import pvlib
import rasterio.features
from shapely.geometry import box

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos"
TABLAS = BASE / "salidas" / "tablas"
UTM = "EPSG:25830"

# Resolucion del raster. Tres metros es un compromiso: las calles del centro
# historico tienen ocho o diez metros de ancho, asi que resolverlas exige estar
# bastante por debajo, y bajar a un metro multiplica por nueve el coste.
RES_M = 3.0

# Muestreo de la red: un punto cada quince metros, mas los extremos. La mediana
# de longitud de arista es de veintidos metros, de modo que casi toda arista
# aporta al menos dos puntos.
PASO_MUESTREO_M = 15.0

HORAS = [10, 11, 12, 16, 17, 18]
FECHAS = ["06-15", "07-15", "08-15"]
ANIO_REF = 2023

LAT, LON = 39.47, -0.376
TZ = "Europe/Madrid"

# Por debajo de esta elevacion el sol esta tan rasante que la sombra es
# practicamente universal y el metodo pierde sentido; se marca como tal.
ELEV_MINIMA = 5.0


def posiciones_solares() -> pd.DataFrame:
    filas = []
    for f in FECHAS:
        for h in HORAS:
            t = pd.Timestamp(f"{ANIO_REF}-{f} {h:02d}:30", tz=TZ)
            sp = pvlib.solarposition.get_solarposition(
                pd.DatetimeIndex([t]), LAT, LON)
            filas.append({"fecha": f, "hora": h,
                          "elevacion": float(sp["apparent_elevation"].iloc[0]),
                          "azimut": float(sp["azimuth"].iloc[0])})
    return pd.DataFrame(filas)


def rasterizar_alturas(edificios: gpd.GeoDataFrame, bounds):
    x0, y0, x1, y1 = bounds
    ancho = int(np.ceil((x1 - x0) / RES_M))
    alto = int(np.ceil((y1 - y0) / RES_M))
    transform = rasterio.transform.from_origin(x0, y1, RES_M, RES_M)
    print(f"  raster {alto} x {ancho} = {alto*ancho/1e6:.1f} M celdas a {RES_M} m")
    H = rasterio.features.rasterize(
        ((geom, h) for geom, h in zip(edificios.geometry, edificios["altura_m"])),
        out_shape=(alto, ancho), transform=transform, fill=0.0,
        merge_alg=rasterio.enums.MergeAlg.replace, dtype="float32")
    print(f"  celdas con edificio: {(H > 0).sum()/1e6:.2f} M "
          f"({100*(H > 0).mean():.1f} %)")
    return H, transform


def sombra(H: np.ndarray, elevacion: float, azimut: float) -> np.ndarray:
    """Mascara de sombra por desplazamiento iterativo hacia el sol."""
    if elevacion <= ELEV_MINIMA:
        return np.ones(H.shape, dtype=bool)
    tan_e = np.tan(np.radians(elevacion))
    # Vector unitario hacia el sol en coordenadas de mapa (x este, y norte).
    ux, uy = np.sin(np.radians(azimut)), np.cos(np.radians(azimut))
    # En indices de raster: columna crece al este, fila crece al SUR.
    dcol, dfil = ux, -uy

    alcance = float(H.max()) / tan_e          # sombra maxima posible
    n_pasos = int(np.ceil(alcance / RES_M))
    sombreado = np.zeros(H.shape, dtype=bool)

    for n in range(1, n_pasos + 1):
        df = int(round(n * dfil))
        dc = int(round(n * dcol))
        altura_necesaria = n * RES_M * tan_e
        if altura_necesaria > H.max():
            break
        # H desplazado: lo que hay a n pasos en direccion al sol.
        f0, f1 = max(0, df), H.shape[0] + min(0, df)
        c0, c1 = max(0, dc), H.shape[1] + min(0, dc)
        if f1 <= f0 or c1 <= c0:
            break
        origen = H[f0:f1, c0:c1]
        destino_f0, destino_c0 = f0 - df, c0 - dc
        bloque = origen > altura_necesaria
        sombreado[destino_f0:destino_f0 + (f1 - f0),
                  destino_c0:destino_c0 + (c1 - c0)] |= bloque
    return sombreado


def muestrear_red():
    G = ox.load_graphml(DATOS / "red_peatonal_valencia.graphml")
    e = ox.graph_to_gdfs(G, nodes=False).to_crs(UTM).reset_index()
    e["arista"] = np.arange(len(e))
    puntos, idx = [], []
    for i, geom in zip(e["arista"].to_numpy(), e.geometry.to_numpy()):
        L = geom.length
        n = max(2, int(L // PASO_MUESTREO_M) + 1)
        for d in np.linspace(0, L, n):
            p = geom.interpolate(d)
            puntos.append((p.x, p.y))
            idx.append(i)
    return e, np.asarray(puntos), np.asarray(idx)


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    print("posiciones solares")
    sol = posiciones_solares()
    print(sol.round(1).to_string(index=False))

    print("\nred peatonal")
    aristas, puntos, idx_arista = muestrear_red()
    print(f"  {len(aristas):,} aristas, {len(puntos):,} puntos de muestreo")

    print("\nedificios")
    # Se prefiere la capa con altura observada de LiDAR cuando existe. La de
    # plantas catastrales queda como respaldo, y el nombre de la columna dice
    # cual se esta usando, para que no se pueda confundir en una re-ejecucion.
    lidar = DATOS / "edificios_valencia_lidar.gpkg"
    if lidar.exists():
        ed = gpd.read_file(lidar, layer="edificios")
        ed["altura_m"] = ed["altura_final_m"]
        n_lidar = int((ed["fuente_altura"] == "lidar_p75").sum())
        print(f"  altura de LiDAR en {n_lidar:,} partes, calibrada por plantas "
              f"en {len(ed) - n_lidar:,}")
    else:
        ed = gpd.read_file(DATOS / "edificios_valencia.gpkg", layer="edificios")
        print("  AVISO: sin capa de LiDAR, se usa el supuesto de 3 m/planta")
    x0, y0 = puntos.min(axis=0) - 500
    x1, y1 = puntos.max(axis=0) + 500
    ed = ed[ed.intersects(box(x0, y0, x1, y1))]
    print(f"  {len(ed):,} partes dentro del area de la red")
    H, transform = rasterizar_alturas(ed, (x0, y0, x1, y1))

    inv_t = ~transform
    cols, filas = inv_t * (puntos[:, 0], puntos[:, 1])
    cols = np.clip(cols.astype(int), 0, H.shape[1] - 1)
    filas = np.clip(filas.astype(int), 0, H.shape[0] - 1)

    print("\nsombra por configuracion")
    resultados = {}
    for r in sol.itertuples():
        m = sombra(H, r.elevacion, r.azimut)
        sombreado = m[filas, cols]
        clave = f"{r.fecha}_{r.hora:02d}"
        resultados[clave] = sombreado
        print(f"  {clave}  elev {r.elevacion:5.1f}  azim {r.azimut:6.1f}  "
              f"puntos en sombra {100*sombreado.mean():5.1f} %")

    # Fraccion sombreada por arista.
    df = pd.DataFrame(resultados)
    df["arista"] = idx_arista
    frac = df.groupby("arista").mean()
    frac.to_parquet(DATOS / "sombra_aristas.parquet")

    aristas_out = aristas[["arista", "u", "v", "length"]].merge(
        frac, left_on="arista", right_index=True, how="left")
    aristas_out.to_parquet(DATOS / "aristas_con_sombra.parquet", index=False)

    resumen = {"resolucion_m": RES_M, "paso_muestreo_m": PASO_MUESTREO_M,
               "n_aristas": int(len(aristas)), "n_puntos": int(len(puntos)),
               "n_partes_edificio": int(len(ed)),
               "supuesto_altura": "3,0 m por planta + 1,0 m de sobrealzado",
               "fraccion_sombreada_media": {
                   k: round(float(v.mean()), 4) for k, v in resultados.items()}}
    (TABLAS / "p3_sombra_resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    sol.round(2).to_csv(TABLAS / "p3_posiciones_solares.csv", index=False)

    print("\nfraccion sombreada de la red, ponderada por longitud:")
    L = aristas.set_index("arista")["length"]
    for k in resultados:
        f = frac[k].reindex(L.index).fillna(0)
        print(f"  {k}: {100*float((f*L).sum()/L.sum()):5.1f} %")


if __name__ == "__main__":
    main()
