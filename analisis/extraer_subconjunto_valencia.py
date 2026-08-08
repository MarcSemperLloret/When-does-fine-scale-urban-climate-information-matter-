#!/usr/bin/env python3
"""Extraer el subconjunto estival del area de Valencia desde el archivo AVAMET reparado.

Se lee unicamente el split `development`. El split `locked` (2024) pertenece al
diseno confirmatorio del proyecto de reventones y mirarlo aqui lo destruiria,
asi que el verano de 2024 no entra en este estudio de viabilidad.

Se usa `observed_local` porque toda la Puerta 1 se articula sobre el ciclo
horario, y el ciclo horario solo tiene sentido en hora local.

Salida: manuscrito3/datos/valencia_verano.parquet
"""

from __future__ import annotations

from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[2] / "downbursts-cv-pilot"
ARCHIVE = REPO / "data" / "processed" / "avamet" / "archive" / "development"
STATIONS = REPO / "data" / "processed" / "avamet" / "stations.csv"
OUT = Path(__file__).resolve().parents[1] / "datos" / "valencia_verano.parquet"

# Centro historico de Valencia (Micalet). Todas las distancias del estudio se
# miden desde aqui.
CENTRO_LAT, CENTRO_LON = 39.4754, -0.3764

# Radio de captacion. 30 km recoge el municipio, su area metropolitana y un
# anillo periurbano que sirve de referencia externa en los controles.
RADIO_KM = 30.0

MESES_VERANO = (6, 7, 8)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false")

    dist = f"""
        6371.0 * acos(least(1.0,
            sin(radians(latitude)) * sin(radians({CENTRO_LAT}))
          + cos(radians(latitude)) * cos(radians({CENTRO_LAT}))
          * cos(radians(longitude - ({CENTRO_LON})))))
    """

    con.execute(
        f"""
        CREATE OR REPLACE TABLE bruto AS
        SELECT
            station_id,
            observed_local,
            date,
            latitude,
            longitude,
            altitude_m,
            temperature_c,
            relative_humidity_pct,
            wind_mean_kmh,
            wind_max_reported_kmh,
            wind_direction_deg,
            pressure_hpa,
            precipitation_interval_mm,
            year,
            month
        FROM read_parquet('{ARCHIVE.as_posix()}/**/*.parquet', hive_partitioning = 1)
        WHERE month IN {MESES_VERANO}
          AND {dist} < {RADIO_KM}
        """
    )

    n = con.sql("SELECT count(*) FROM bruto").fetchone()[0]
    e = con.sql("SELECT count(DISTINCT station_id) FROM bruto").fetchone()[0]
    print(f"filas estivales en {RADIO_KM:.0f} km: {n:,}  estaciones: {e}")

    # Etiquetas de red y tipologia. `c15m250` es el codigo AVAMET del municipio
    # de Valencia; el resto del anillo se separa por distancia al centro.
    con.execute(
        f"""
        CREATE OR REPLACE TABLE meta AS
        SELECT
            station_id,
            any_value(latitude)   AS lat,
            any_value(longitude)  AS lon,
            any_value(altitude_m) AS alt_m,
            {dist.replace('latitude', 'any_value(latitude)').replace('longitude', 'any_value(longitude)')} AS km_centro
        FROM bruto
        GROUP BY station_id
        """
    )

    con.execute(
        f"""
        COPY (
            SELECT
                b.*,
                m.km_centro,
                CASE
                    WHEN b.station_id LIKE 'c15m250%' THEN 'municipio'
                    WHEN m.km_centro < 12 THEN 'metropolitano'
                    ELSE 'periurbano'
                END AS ambito
            FROM bruto b
            JOIN meta m USING (station_id)
            ORDER BY station_id, observed_local
        ) TO '{OUT.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
        """
    )

    print(f"escrito {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")
    print(con.sql("SELECT ambito, count(DISTINCT station_id) AS n_est, count(*) AS filas "
                  f"FROM read_parquet('{OUT.as_posix()}') GROUP BY ambito ORDER BY ambito").df())


if __name__ == "__main__":
    main()
