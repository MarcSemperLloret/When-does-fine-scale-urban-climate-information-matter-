#!/usr/bin/env python3
"""Puerta 0 del plan de viabilidad: inventario de estaciones y control de calidad.

Responde a la unica pregunta que importa antes de gastar esfuerzo en analisis
meteorologico: cuantas estaciones del area de Valencia son realmente utilizables,
durante que veranos, y cuales hay que descartar y por que.

Salidas:
  salidas/tablas/p0_inventario_estaciones.csv
  salidas/tablas/p0_cobertura_por_verano.csv
  salidas/tablas/p0_control_calidad.csv
  salidas/tablas/p0_decision.md
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos" / "valencia_verano.parquet"
STATIONS = BASE.parents[0] / "downbursts-cv-pilot" / "data" / "processed" / "avamet" / "stations.csv"
TABLAS = BASE / "salidas" / "tablas"

# Linea de costa del golfo de Valencia, digitalizada a mano con la precision
# suficiente para una covariable de distancia (error del orden de 200 m). No
# sustituye a una linea de costa oficial, que entraria en la Puerta 3.
COSTA = [
    (39.75, -0.210), (39.63, -0.280), (39.55, -0.310), (39.50, -0.318),
    (39.47, -0.322), (39.44, -0.325), (39.40, -0.330), (39.36, -0.315),
    (39.30, -0.290), (39.22, -0.250),
]

# Cadencia nativa de la red. AVAMET publica decadales.
CADENCIA_MIN = 10
DIAS_VERANO = 92  # junio + julio + agosto
SLOTS_VERANO = DIAS_VERANO * 24 * 60 // CADENCIA_MIN

# Umbrales de control de calidad. Elegidos para el verano mediterraneo: por
# debajo de 5 C o por encima de 50 C no hay observacion valida en junio-agosto
# en esta area. Este filtro captura sobre todo el 0,0 centinela (ver abajo).
T_MIN_PLAUSIBLE, T_MAX_PLAUSIBLE = 5.0, 50.0

# Defecto D- del archivo: varias estaciones codifican el dato ausente como
# "0,0" en el campo de temperatura. En un verano valenciano un 0,0 C no es una
# medida, pero es un numero perfectamente valido y entra en cualquier media sin
# avisar. Afecta desde el 0,001 % (l'Albufera) hasta el 5,5 % (Alfinach) de los
# partes de una estacion. Se enmascara a nivel de observacion, no se descarta
# la estacion: dos ceros en medio millon de partes no invalidan una serie.
SENTINELA = 0.0

# Deteccion de picos: un valor que se aparta mas de 4 C de la mediana movil de
# sus vecinos inmediatos y vuelve al paso siguiente es un pico instrumental,
# no una rampa fisica.
PICO_C = 4.0

# Rachas planas. Con resolucion de 0,1 C y cadencia decadal, una hora de valor
# identico es habitual de madrugada (mediana de la red: 3,8 % del registro), de
# modo que 6 pasos no discrimina nada. Dos horas si: la mediana de la red baja
# al 0,3 %, y solo destaca quien tiene un sensor lento de verdad.
PLANO_PASOS = 12


def km_haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def km_a_costa(lat, lon):
    """Distancia minima al segmento de costa mas proximo."""
    mejor = np.inf
    for (la1, lo1), (la2, lo2) in zip(COSTA[:-1], COSTA[1:]):
        # Proyeccion en plano local: a esta latitud el error es despreciable
        # frente a la incertidumbre de la propia linea digitalizada.
        kx = 111.32 * np.cos(np.radians(lat))
        ky = 110.57
        px, py = (lon - lo1) * kx, (lat - la1) * ky
        sx, sy = (lo2 - lo1) * kx, (la2 - la1) * ky
        t = np.clip((px * sx + py * sy) / (sx * sx + sy * sy), 0.0, 1.0)
        d = np.hypot(px - t * sx, py - t * sy)
        mejor = min(mejor, d)
    return mejor


def main() -> None:
    TABLAS.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(DATOS)
    nombres = pd.read_csv(STATIONS, encoding="utf-8-sig").set_index("station_code")["station_name"]

    df = df.sort_values(["station_id", "observed_local"])

    # ------------------------------------------- enmascarado a nivel observacion
    # El orden importa: primero se quita el centinela, porque si no, la
    # transicion 24 C -> 0,0 C -> 24 C se contabiliza como dos saltos de 24 C y
    # contamina la estadistica de saltos de la estacion.
    t = df["temperature_c"]
    fuera = (t < T_MIN_PLAUSIBLE) | (t > T_MAX_PLAUSIBLE)
    df["marca_rango"] = fuera
    t = t.mask(fuera)

    vecinos = t.groupby(df["station_id"]).transform(
        lambda s: s.rolling(5, center=True, min_periods=3).median()
    )
    pico = (t - vecinos).abs() > PICO_C
    df["marca_pico"] = pico.fillna(False)
    df["t_qc"] = t.mask(df["marca_pico"])
    df["enmascarado"] = df["marca_rango"] | df["marca_pico"]

    # ---------------------------------------------------------------- inventario
    meta = (
        df.groupby("station_id")
        .agg(
            lat=("latitude", "first"),
            lon=("longitude", "first"),
            alt_m=("altitude_m", "first"),
            km_centro=("km_centro", "first"),
            ambito=("ambito", "first"),
            n_obs=("temperature_c", "size"),
            primer_dia=("date", "min"),
            ultimo_dia=("date", "max"),
        )
    )
    meta["nombre"] = meta.index.map(nombres)
    meta["km_costa"] = [km_a_costa(r.lat, r.lon) for r in meta.itertuples()]

    # Cadencia real observada por estacion (mediana del intervalo entre partes).
    dt = df.groupby("station_id")["observed_local"].diff().dt.total_seconds() / 60
    meta["cadencia_min"] = dt.groupby(df["station_id"]).median()
    meta["hueco_max_h"] = dt.groupby(df["station_id"]).max() / 60

    # ------------------------------------------------------- cobertura por verano
    # La cobertura se cuenta sobre temperatura ya validada: un parte con el 0,0
    # centinela existe como fila pero no es una observacion de temperatura.
    cob = (
        df[df["t_qc"].notna()]
        .groupby(["station_id", "year"])["observed_local"]
        .nunique()
        .rename("slots")
        .reset_index()
    )
    cob["cobertura_pct"] = 100 * cob["slots"] / SLOTS_VERANO
    # La cadencia declarada no es universal: si una estacion emite cada 30 min su
    # cobertura nominal saldria baja sin ser un hueco. Se corrige por cadencia.
    cad = meta["cadencia_min"].reindex(cob["station_id"]).to_numpy()
    cob["cobertura_pct"] = np.minimum(100.0, cob["cobertura_pct"] * np.maximum(1.0, cad / CADENCIA_MIN))

    piv = (
        cob.pivot(index="station_id", columns="year", values="cobertura_pct")
        .reindex(meta.index)
        .fillna(0.0)
        .round(1)
    )
    piv.columns = [f"cob_{c}" for c in piv.columns]
    meta = meta.join(piv)

    # ---------------------------------------------------------- control de calidad
    filas = []
    for sid, g in df.groupby("station_id"):
        t = g["t_qc"]
        rh = g["relative_humidity_pct"]
        dt_min = g["observed_local"].diff().dt.total_seconds() / 60
        paso_normal = dt_min <= CADENCIA_MIN * 1.5

        # Rachas de valor identico sobre la serie ya validada.
        cambio = (t != t.shift()) | ~paso_normal
        rachas = t.groupby(cambio.cumsum()).size()
        frac_plana = 100 * rachas[rachas >= PLANO_PASOS].sum() / max(len(t), 1)

        # Rango diurno medio: un abrigo mal ventilado o expuesto al sol se
        # delata por un rango diario sistematicamente mayor que el de la red.
        rango = g.groupby("date")["t_qc"].agg(lambda s: s.max() - s.min())

        filas.append(
            {
                "station_id": sid,
                "n_partes": len(g),
                "n_temp_validas": int(t.notna().sum()),
                "centinela_0c": int((g["temperature_c"] == SENTINELA).sum()),
                "centinela_pct": round(100 * (g["temperature_c"] == SENTINELA).mean(), 3),
                "picos": int(g["marca_pico"].sum()),
                "enmascarado_pct": round(100 * g["enmascarado"].mean(), 3),
                "t_min": round(t.min(), 1),
                "t_max": round(t.max(), 1),
                "rh_imposibles": int(((rh < 0) | (rh > 100)).sum()),
                "racha_plana_max_pasos": int(rachas.max()) if len(rachas) else 0,
                "frac_plana_pct": round(frac_plana, 2),
                "duplicados": int(g["observed_local"].duplicated().sum()),
                "rango_diurno_medio": round(rango.mean(), 2),
                "rango_diurno_p95": round(rango.quantile(0.95), 2),
            }
        )
    qc = pd.DataFrame(filas).set_index("station_id")

    # ------------------------------------------------------------------- decision
    # Una estacion se descarta por un defecto sistemico, no por observaciones
    # sueltas: esas ya estan enmascaradas y no llegan al analisis.
    tabla = meta.join(qc)
    cols_cob = [c for c in tabla.columns if c.startswith("cob_")]
    tabla["veranos_utiles"] = (tabla[cols_cob] >= 80).sum(axis=1)
    tabla["cobertura_mediana"] = tabla[cols_cob].median(axis=1).round(1)

    # El umbral de rango diurno se fija contra la propia red, no a ojo: se marca
    # quien se aparta mas de 3 desviaciones robustas de la mediana de su ambito.
    med_rango = tabla["rango_diurno_medio"].median()
    mad_rango = 1.4826 * (tabla["rango_diurno_medio"] - med_rango).abs().median()
    umbral_rango = med_rango + 3 * mad_rango

    motivos, decisiones = [], []
    for r in tabla.itertuples():
        m = []
        if r.veranos_utiles < 2:
            m.append(f"solo {r.veranos_utiles} verano(s) con cobertura >=80%")
        if r.enmascarado_pct > 5:
            m.append(f"{r.enmascarado_pct}% de partes enmascarados")
        if r.frac_plana_pct > 10:
            m.append(f"sensor inercial ({r.frac_plana_pct}% en rachas >=2 h)")
        if r.rango_diurno_medio > umbral_rango:
            m.append(f"rango diurno {r.rango_diurno_medio} C > {umbral_rango:.1f} C de la red")
        if r.duplicados > 0:
            m.append(f"{r.duplicados} marcas de tiempo duplicadas")
        decisiones.append("descartar" if m else "usar")
        motivos.append("; ".join(m) if m else "")
    tabla["decision"] = decisiones
    tabla["motivo"] = motivos
    tabla.attrs["umbral_rango"] = umbral_rango

    orden = [
        "nombre", "ambito", "lat", "lon", "alt_m", "km_centro", "km_costa",
        "cadencia_min", "primer_dia", "ultimo_dia", "n_partes", "n_temp_validas",
        "hueco_max_h", *cols_cob, "veranos_utiles", "cobertura_mediana",
        "t_min", "t_max", "centinela_0c", "centinela_pct", "picos",
        "enmascarado_pct", "rh_imposibles", "racha_plana_max_pasos",
        "frac_plana_pct", "duplicados", "rango_diurno_medio", "rango_diurno_p95",
        "decision", "motivo",
    ]
    tabla = tabla[orden].sort_values(["ambito", "km_centro"])
    tabla.round(3).to_csv(TABLAS / "p0_inventario_estaciones.csv", encoding="utf-8")
    cob.round(2).to_csv(TABLAS / "p0_cobertura_por_verano.csv", index=False, encoding="utf-8")
    qc.to_csv(TABLAS / "p0_control_calidad.csv", encoding="utf-8")

    # ------------------------------------------------- criterios de la Puerta 0
    usables = tabla[tabla["decision"] == "usar"]
    mun = usables[usables["ambito"] == "municipio"]
    urbanas = usables[usables["ambito"].isin(["municipio", "metropolitano"])]

    # Veranos comunes: aquellos en que al menos 6 estaciones urbanas superan el 80%
    comunes = []
    for c in cols_cob:
        n = (urbanas[c] >= 80).sum()
        comunes.append((int(c.split("_")[1]), int(n)))

    resumen = {
        "estaciones_evaluadas": int(len(tabla)),
        "estaciones_usables": int(len(usables)),
        "usables_municipio": int(len(mun)),
        "usables_area_urbana": int(len(urbanas)),
        "usables_periurbanas": int((usables["ambito"] == "periurbano").sum()),
        "urbanas_con_cobertura_por_verano": comunes,
        "umbral_rango_diurno_c": round(float(umbral_rango), 2),
        "centinela_0c_total": int(tabla["centinela_0c"].sum()),
        "estaciones_con_centinela": int((tabla["centinela_0c"] > 0).sum()),
        "descartadas": tabla[tabla["decision"] == "descartar"][["nombre", "motivo"]].to_dict("index"),
    }
    (TABLAS / "p0_resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    # Serie ya validada, para que la Puerta 1 no repita el enmascarado.
    (df.loc[df["t_qc"].notna(),
            ["station_id", "observed_local", "date", "year", "month", "t_qc",
             "relative_humidity_pct", "wind_mean_kmh", "wind_direction_deg",
             "km_centro", "ambito", "altitude_m", "latitude", "longitude"]]
       .to_parquet(BASE / "datos" / "valencia_verano_qc.parquet", index=False))

    print(tabla[["nombre", "ambito", "km_centro", "km_costa", "cobertura_mediana",
                 "veranos_utiles", "centinela_pct", "frac_plana_pct",
                 "rango_diurno_medio", "decision"]].to_string())
    print("\n--- criterios Puerta 0 ---")
    print(json.dumps({k: v for k, v in resumen.items() if k != "descartadas"},
                     indent=2, ensure_ascii=False))
    print("\ndescartadas:")
    for sid, d in resumen["descartadas"].items():
        print(f"  {sid}  {d['nombre']}: {d['motivo']}")


if __name__ == "__main__":
    main()
