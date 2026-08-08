#!/usr/bin/env python3
"""Piloto de accesibilidad: la representacion termica cambia la decision?

Prueba deliberadamente destructiva de la hipotesis. La pregunta no es si los
datos gruesos pierden microclima --eso es cierto por construccion y ya esta
publicado-- sino si cambian **que secciones censales se consideran atendidas y
que barrios se priorizan**.

El canal por el que la temperatura entra importa, y conviene decirlo por
adelantado porque decide el resultado:

* Por **velocidad de marcha** no entra. Con 1,2 C de contraste y cualquier
  penalizacion plausible por grado, la diferencia de tiempo de recorrido es del
  orden del 1 %, y no mueve ninguna decision. Se calcula igualmente para
  poder afirmarlo con un numero.
* Por **cruce de umbral** si entra, y mucho. La distribucion de temperatura es
  empinada cerca de los 30 C, de modo que 1,2 C de media separan un 22 % de
  horas por encima del umbral de un 9 %. Ahi es donde una representacion
  uniforme y una observada dejan de coincidir.

De modo que la variable de decision no es "se llega en quince minutos" sino
"durante que fraccion del verano se llega en quince minutos sin superar el
umbral de calor", que es como se formula una politica de acceso.

Escenarios:
  A  distancia, velocidad estandar
  B  velocidad adaptada a persona mayor
  C  B + temperatura uniforme para toda la ciudad  (representacion gruesa)
  D  B + temperatura observada por seccion         (representacion fina)

Salidas en salidas/tablas/p4_*.csv
"""

from __future__ import annotations

import json
import re
import zipfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd

import centros

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos"
TABLAS = BASE / "salidas" / "tablas"

MUNICIPIO = "46250"
UTM = "EPSG:25830"

# Velocidades de marcha. La estandar es la que usa por defecto casi toda la
# literatura de isocronas; la adaptada es la que se mide en poblacion mayor de
# 65 anos en trayecto real, no en test de laboratorio.
V_ESTANDAR = 1.25   # m/s
V_MAYOR = 0.90      # m/s

PRESUPUESTO_MIN = 15.0  # minutos de caminata aceptables hasta un centro de salud

# Umbrales de calor. 30 C es el punto donde el estres termico empieza a limitar
# la marcha en poblacion mayor; 32 C se reporta como sensibilidad.
UMBRAL_C = 30.0
UMBRAL_ALT_C = 32.0

VENTANAS = {"manana_10_12": [10, 11, 12], "tarde_16_18": [16, 17, 18]}

BARRIOS_PANEL = ["c15m250e30", "c15m250e15", "c15m250e24",
                 "c15m250e11", "c15m250e26", "c15m250e08"]

PRIMARIA = re.compile(
    r"centre de salut|centro de salud|consultori|consultorio|centre sanitari|ambulatori",
    re.I)

ox.settings.overpass_url = "https://maps.mail.ru/osm/tools/overpass/api"
ox.settings.requests_timeout = 300
ox.settings.use_cache = True
ox.settings.cache_folder = str(DATOS / "cache_osm")


# --------------------------------------------------------------------- datos
def secciones() -> gpd.GeoDataFrame:
    z = DATOS / "seccionado_2024.zip"
    g = gpd.read_file(f"zip://{z}!SECC_CE_20240101.shp")
    g = g[g["CUSEC"].str.startswith(MUNICIPIO)].to_crs(UTM)

    pob = pd.read_csv(DATOS / "poblacion_secciones_valencia.csv", index_col=0)
    # El indice viene como "4625001001 València sección 01001"; interesa el codigo.
    pob.index = pob.index.str.split().str[0]
    g = g.merge(pob, left_on="CUSEC", right_index=True, how="left")

    g["poblacion"] = g["Población"]
    g["pct_65"] = g["Porcentaje de población de 65 y más años"]
    g["pob_65"] = g["poblacion"] * g["pct_65"] / 100
    g["pct_unipersonal"] = g["Porcentaje de hogares unipersonales"]
    faltan = g["poblacion"].isna().sum()
    print(f"  secciones: {len(g)}; sin poblacion: {faltan}")
    g = g[g["poblacion"].notna() & (g["poblacion"] > 0)].copy()
    print(f"  con poblacion: {len(g)}; total {g['poblacion'].sum():,.0f} hab, "
          f"{g['pob_65'].sum():,.0f} de 65+")
    return g


def centros_salud(recorte=None) -> gpd.GeoDataFrame:
    """Capa canonica de destinos (ver analisis/centros.py)."""
    d = centros.cargar(recorte)
    g = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(d["lon"], d["lat"]),
                         crs="EPSG:4326").to_crs(UTM)
    print(f"  centros de atencion primaria ({centros.FUENTE}): {len(g)}")
    return g


def red_peatonal(g_sec: gpd.GeoDataFrame) -> nx.MultiDiGraph:
    cache = DATOS / "red_peatonal_valencia.graphml"
    if cache.exists():
        print("  red peatonal desde cache")
        return ox.load_graphml(cache)
    poly = g_sec.to_crs("EPSG:4326").union_all().buffer(0.012)  # ~1,3 km de margen
    print("  descargando red peatonal de OSM (puede tardar)...")
    G = ox.graph_from_polygon(poly, network_type="walk", simplify=True)
    ox.save_graphml(G, cache)
    return G


# ---------------------------------------------------------------- accesibilidad
def distancia_a_centro(G, g_sec, g_cen) -> pd.Series:
    """Distancia de red desde cada seccion al centro de salud mas proximo.

    Se resuelve con un Dijkstra multiorigen desde los centros, que da la
    distancia de todos los nodos en una sola pasada, en vez de un camino
    minimo por seccion.
    """
    Gu = ox.convert.to_undirected(G)
    cen4326 = g_cen.to_crs("EPSG:4326")
    nodos_cen = ox.nearest_nodes(G, cen4326.geometry.x.values, cen4326.geometry.y.values)

    Gu.add_node("__origen__")
    for n in set(nodos_cen):
        Gu.add_edge("__origen__", n, length=0.0)
    dist = nx.single_source_dijkstra_path_length(Gu, "__origen__", weight="length")

    cent = g_sec.geometry.centroid.to_crs("EPSG:4326")
    nodos_sec = ox.nearest_nodes(G, cent.x.values, cent.y.values)
    return pd.Series([dist.get(n, np.inf) for n in nodos_sec], index=g_sec.index)


def campo_termico(g_sec: gpd.GeoDataFrame) -> dict[str, pd.DataFrame]:
    """Serie horaria de temperatura de cada seccion, por ponderacion inversa.

    Seis estaciones para 591 secciones es una interpolacion pobre, y esa es
    precisamente la limitacion que la Puerta 3 vendria a resolver. Para el
    piloto basta: lo que se pone a prueba es si **alguna** heterogeneidad
    observada cambia la decision, no si este campo concreto es el mejor.
    """
    df = pd.read_parquet(DATOS / "valencia_verano_qc.parquet")
    df = df[df["station_id"].isin(BARRIOS_PANEL)].copy()
    df["hora"] = df["observed_local"].dt.hour
    hor = (df.groupby(["station_id", "date", "hora"], observed=True)["t_qc"]
             .mean().reset_index())

    est = (df.groupby("station_id")[["latitude", "longitude"]].first())
    ge = gpd.GeoDataFrame(est, geometry=gpd.points_from_xy(est["longitude"], est["latitude"]),
                          crs="EPSG:4326").to_crs(UTM)

    cent = g_sec.geometry.centroid
    dx = cent.x.values[:, None] - ge.geometry.x.values[None, :]
    dy = cent.y.values[:, None] - ge.geometry.y.values[None, :]
    d = np.sqrt(dx ** 2 + dy ** 2)
    w = 1.0 / np.maximum(d, 50.0) ** 2
    w = w / w.sum(axis=1, keepdims=True)          # 591 x 6

    salida = {}
    for v, horas in VENTANAS.items():
        piv = (hor[hor["hora"].isin(horas)]
               .pivot_table(index=["date", "hora"], columns="station_id", values="t_qc"))
        piv = piv.dropna()[list(ge.index)]         # solo horas con las seis
        T = w @ piv.to_numpy().T                   # 591 x n_horas
        salida[v] = pd.DataFrame(T, index=g_sec.index, columns=piv.index)
        print(f"  {v}: {piv.shape[0]} horas comunes, campo {T.shape}")
    return salida


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    print("datos")
    g_sec = secciones()
    g_cen = centros_salud(g_sec.union_all())
    G = red_peatonal(g_sec)
    print(f"  red: {G.number_of_nodes():,} nodos, {G.number_of_edges():,} aristas")

    print("accesibilidad")
    g_sec["dist_m"] = distancia_a_centro(G, g_sec, g_cen)
    print(f"  distancia mediana al centro mas proximo: {g_sec['dist_m'].median():.0f} m")

    print("campo termico")
    campos = campo_termico(g_sec)

    # ---------------------------------------------------------- escenarios
    res = g_sec[["CUSEC", "poblacion", "pob_65", "pct_65", "pct_unipersonal",
                 "dist_m"]].copy()
    res["t_min_A"] = res["dist_m"] / V_ESTANDAR / 60
    res["t_min_B"] = res["dist_m"] / V_MAYOR / 60
    res["servida_A"] = res["t_min_A"] <= PRESUPUESTO_MIN
    res["servida_B"] = res["t_min_B"] <= PRESUPUESTO_MIN

    resumen = {
        "n_secciones": int(len(res)),
        "poblacion_total": float(res["poblacion"].sum()),
        "poblacion_65": float(res["pob_65"].sum()),
        "n_centros_salud": int(len(g_cen)),
        "dist_mediana_m": float(res["dist_m"].median()),
        "presupuesto_min": PRESUPUESTO_MIN,
        "umbral_c": UMBRAL_C,
    }
    for e in ("A", "B"):
        resumen[f"pct_65_servida_{e}"] = round(
            100 * res.loc[res[f"servida_{e}"], "pob_65"].sum() / res["pob_65"].sum(), 2)

    # La priorizacion por calor solo tiene sentido donde ya se llega andando.
    # En una seccion que esta a 25 minutos del centro de salud, el problema es
    # la distancia y ninguna informacion termica lo cambia; meterlas en la
    # clasificacion hace que el quintil peor sea puro alcance y que las dos
    # representaciones coincidan por construccion.
    res["alcanzable"] = res["t_min_B"] <= PRESUPUESTO_MIN
    alc = res["alcanzable"].to_numpy()
    print(f"  secciones alcanzables en {PRESUPUESTO_MIN:.0f} min a {V_MAYOR} m/s: "
          f"{alc.sum()} de {len(res)}")

    representaciones = {}
    for v, campo in campos.items():
        T_obs = campo.to_numpy()
        # C: una sola temperatura para toda la ciudad en cada hora, que es lo
        #    que devuelve una rejilla regional de varios kilometros.
        T_uni = np.tile(np.median(T_obs, axis=0), (len(res), 1))
        # C2: ademas del promediado espacial, promediado temporal a un valor
        #     por dia. Es la otra simplificacion habitual, y hay que separarla
        #     de la espacial porque no pierden lo mismo.
        dias = pd.Index(campo.columns.get_level_values(0))
        T_dia = pd.DataFrame(T_uni, columns=campo.columns).T.groupby(dias).transform("mean").T.to_numpy()

        representaciones[v] = {"C_uniforme": T_uni, "C2_uniforme_diaria": T_dia,
                               "D_observada": T_obs}
        for etq, T in representaciones[v].items():
            for u, suf in ((UMBRAL_C, ""), (UMBRAL_ALT_C, "_u32")):
                res[f"frac_{etq}_{v}{suf}"] = ((T < u).mean(axis=1))
        res[f"delta_{v}"] = res[f"frac_D_observada_{v}"] - res[f"frac_C_uniforme_{v}"]

    # --------------------------------------------- metricas de decision
    res["distrito"] = res["CUSEC"].str[5:7]
    pob65 = res["pob_65"].to_numpy()
    met = []
    for v in VENTANAS:
        for suf, u in (("", 30), ("_u32", 32)):
            d = f"frac_D_observada_{v}{suf}"
            for cetq in ("C_uniforme", "C2_uniforme_diaria"):
                c = f"frac_{cetq}_{v}{suf}"
                # Cobertura: poblacion 65+ que alcanza un centro de salud y lo
                # hace en condiciones por debajo del umbral, ponderada por la
                # fraccion del verano en que eso ocurre.
                m = alc
                cob_c = float((res[c][m] * pob65[m]).sum() / pob65.sum())
                cob_d = float((res[d][m] * pob65[m]).sum() / pob65.sum())

                met.append({
                    "ventana": v, "umbral_c": u, "representacion_gruesa": cetq,
                    "cobertura_gruesa_pct": round(100 * cob_c, 2),
                    "cobertura_observada_pct": round(100 * cob_d, 2),
                    "dif_puntos_pct": round(100 * (cob_d - cob_c), 2),
                    "dif_relativa_pct": round(100 * (cob_d - cob_c) / cob_c, 2),
                })
    metricas = pd.DataFrame(met)

    # ------------------------------------------------------ priorizacion
    # Una representacion espacialmente uniforme asigna a cada seccion la misma
    # temperatura, de modo que **no puede ordenar barrios en absoluto**: su
    # ranking de prioridad es el de la distancia, sin mas. No tiene sentido
    # medir su Jaccard contra el observado, porque no hay variabilidad que
    # comparar. La pregunta util es otra: al anadir el calor observado a la
    # regla de priorizacion que un planificador usa hoy --distancia y poblacion
    # mayor-- cambia quien sale arriba?
    # El termino de distancia satura: una seccion fuera del presupuesto de
    # marcha puntua mas que cualquier seccion alcanzable, por caliente que
    # este, de modo que un ranking conjunto lo copan siempre las inalcanzables
    # y las dos reglas coinciden por construccion. Lo que hay que medir es la
    # informacion **incremental**: entre las secciones que si se alcanzan, el
    # calor observado senala a otras que las que senala la distancia?
    alcanzables = res[res["alcanzable"]].copy()
    prio = []
    for v in VENTANAS:
        for suf, u in (("", 30), ("_u32", 32)):
            d = f"frac_D_observada_{v}{suf}"
            a = alcanzables
            n = max(int(0.20 * len(a)), 1)

            # Regla vigente: priorizar donde mas mayores caminan mas lejos.
            score_dist = a["pob_65"] * a["t_min_B"]
            # Regla termica: priorizar donde mas mayores pasan mas horas del
            # verano por encima del umbral en su trayecto.
            score_calor = a["pob_65"] * (1 - a[d])

            top_d = set(score_dist.nlargest(n).index)
            top_c = set(score_calor.nlargest(n).index)
            jac = len(top_d & top_c) / len(top_d | top_c)
            entran = top_c - top_d

            rk_d = a.assign(s=score_dist).groupby("distrito")["s"].sum().rank(ascending=False)
            rk_c = a.assign(s=score_calor).groupby("distrito")["s"].sum().rank(ascending=False)
            t5d, t5c = set(rk_d.nsmallest(5).index), set(rk_c.nsmallest(5).index)

            prio.append({
                "ventana": v, "umbral_c": u,
                "n_secciones_alcanzables": len(a), "n_top20": n,
                "jaccard_top20_secciones": round(jac, 3),
                "secciones_que_entran": len(entran),
                "secciones_que_salen": len(top_d - top_c),
                "pob65_reclasificada": round(float(a.loc[list(entran), "pob_65"].sum())),
                "pct_pob65_reclasificada": round(
                    100 * float(a.loc[list(entran), "pob_65"].sum()) / res["pob_65"].sum(), 2),
                "spearman_secciones": round(
                    float(score_dist.corr(score_calor, method="spearman")), 3),
                "spearman_distritos": round(float(rk_d.corr(rk_c, method="spearman")), 3),
                "solapamiento_top5_distritos": f"{len(t5d & t5c)}/5",
            })
    prioridades = pd.DataFrame(prio)
    prioridades.to_csv(TABLAS / "p4_priorizacion.csv", index=False, encoding="utf-8")

    # ------------------------------------------------------- sensibilidad
    # El resultado no puede depender de tres constantes elegidas a ojo, asi que
    # se repite el contraste variando velocidad, presupuesto de marcha y umbral
    # de calor. Lo que se reporta es si la conclusion --la priorizacion cambia,
    # la cobertura agregada no-- sobrevive a todas las combinaciones.
    campo = campos["tarde_16_18"].to_numpy()
    sens = []
    for vel in (0.80, 0.90, 1.00):
        for pres in (10.0, 15.0, 20.0):
            for umbral in (28.0, 30.0, 32.0):
                tmin = res["dist_m"] / vel / 60
                alcanza = (tmin <= pres).to_numpy()
                if alcanza.sum() < 30:
                    continue
                frac = (campo < umbral).mean(axis=1)
                uni = np.tile(np.median(campo, axis=0), (len(res), 1))
                frac_uni = (uni < umbral).mean(axis=1)

                p65 = res["pob_65"].to_numpy()
                cob_u = (frac_uni[alcanza] * p65[alcanza]).sum() / p65.sum()
                cob_o = (frac[alcanza] * p65[alcanza]).sum() / p65.sum()

                a = res[alcanza]
                n = max(int(0.20 * len(a)), 1)
                sd = (a["pob_65"] * tmin[alcanza]).nlargest(n).index
                sc = (a["pob_65"] * (1 - frac[alcanza])).nlargest(n).index
                jac = len(set(sd) & set(sc)) / len(set(sd) | set(sc))
                recl = float(a.loc[list(set(sc) - set(sd)), "pob_65"].sum())

                sens.append({
                    "velocidad_ms": vel, "presupuesto_min": pres, "umbral_c": umbral,
                    "n_alcanzables": int(alcanza.sum()),
                    "cobertura_dif_puntos": round(100 * (cob_o - cob_u), 2),
                    "jaccard_top20": round(jac, 3),
                    "pct_pob65_reclasificada": round(100 * recl / p65.sum(), 2),
                })
    sensib = pd.DataFrame(sens)
    sensib.to_csv(TABLAS / "p4_sensibilidad.csv", index=False, encoding="utf-8")
    print("\n--- sensibilidad (ventana de tarde) ---")
    print(f"  combinaciones: {len(sensib)}")
    print(f"  cobertura, dif. en puntos: min {sensib['cobertura_dif_puntos'].min():.2f}, "
          f"mediana {sensib['cobertura_dif_puntos'].median():.2f}, "
          f"max {sensib['cobertura_dif_puntos'].max():.2f}")
    print(f"  jaccard top-20 %: min {sensib['jaccard_top20'].min():.3f}, "
          f"mediana {sensib['jaccard_top20'].median():.3f}, "
          f"max {sensib['jaccard_top20'].max():.3f}")
    print(f"  poblacion 65+ reclasificada (%): min {sensib['pct_pob65_reclasificada'].min():.2f}, "
          f"mediana {sensib['pct_pob65_reclasificada'].median():.2f}, "
          f"max {sensib['pct_pob65_reclasificada'].max():.2f}")

    res.drop(columns="geometry", errors="ignore").to_csv(
        TABLAS / "p4_secciones.csv", index=False, encoding="utf-8")
    metricas.to_csv(TABLAS / "p4_metricas_decision.csv", index=False, encoding="utf-8")
    (TABLAS / "p4_resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n--- resumen ---")
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    print("\n--- metricas de decision ---")
    print(metricas.to_string(index=False))


if __name__ == "__main__":
    main()
