#!/usr/bin/env python3
"""Descarga los datos no meteorologicos del piloto de accesibilidad.

Tres fuentes, todas publicas y citables:

  INE ADRH tabla 31258  poblacion y estructura de edad por seccion censal
  INE seccionado 2024   geometria de las secciones censales
  OpenStreetMap         red peatonal y centros de salud

El portal municipal de datos abiertos de Valencia no responde desde esta
maquina, asi que los servicios esenciales salen de OSM. Para el piloto sirve;
para el articulo final habria que contrastarlos con el listado oficial de la
Conselleria de Sanitat, porque la completitud de OSM en equipamiento sanitario
no esta garantizada y es exactamente el tipo de sesgo que un revisor pregunta.

Salidas en manuscrito3/datos/
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos"
H = {"User-Agent": "downbursts-cv-pilot/1.0 (investigacion academica)"}

ADRH_VALENCIA = 31258
CARTO = "https://www.ine.es/prodyser/cartografia/seccionado_2024.zip"
# overpass-api.de rechaza las peticiones desde esta maquina con un 406, y
# overpass.osm.ch sirve solo el extracto suizo, de modo que responde 200 con
# cero elementos para cualquier consulta espanola: un fallo silencioso que
# parece "no hay centros de salud en Valencia".
OVERPASS = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"

# Codigo INE del municipio de Valencia.
MUNICIPIO = "46250"

# Caja del termino municipal, generosa por el sur para incluir el Saler y la
# Albufera, que son Valencia aunque esten a trece kilometros.
BBOX = (39.28, -0.44, 39.55, -0.29)  # sur, oeste, norte, este


def descargar(url: str, destino: Path, **kw) -> Path:
    if destino.exists():
        print(f"  ya estaba: {destino.name} ({destino.stat().st_size/1e6:.1f} MB)")
        return destino
    r = requests.get(url, headers=H, timeout=600, **kw)
    r.raise_for_status()
    destino.write_bytes(r.content)
    print(f"  descargado: {destino.name} ({len(r.content)/1e6:.1f} MB)")
    return destino


def adrh() -> None:
    print("INE ADRH (poblacion por seccion censal)")
    crudo = DATOS / "ine_adrh_valencia.csv"
    descargar(f"https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/{ADRH_VALENCIA}.csv", crudo)

    df = pd.read_csv(crudo, sep=";", encoding="utf-8-sig", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    print("  indicadores disponibles:")
    for ind in sorted(df["Indicadores demográficos"].dropna().unique()):
        print(f"    - {ind}")

    # Solo secciones (no totales de municipio ni de distrito) del municipio.
    sec = df[df["Municipios"].str.startswith(MUNICIPIO, na=False)
             & df["Secciones"].notna() & (df["Secciones"].str.strip() != "")].copy()
    ultimo = sorted(sec["Periodo"].unique())[-1]
    sec = sec[sec["Periodo"] == ultimo]
    print(f"  periodo mas reciente: {ultimo}; filas de seccion: {len(sec)}")

    sec["valor"] = (sec["Total"].str.replace(".", "", regex=False)
                                .str.replace(",", ".", regex=False)
                                .astype(float))
    ancho = sec.pivot_table(index="Secciones", columns="Indicadores demográficos",
                            values="valor", aggfunc="first")
    ancho.index = ancho.index.str.strip()
    ancho.to_csv(DATOS / "poblacion_secciones_valencia.csv", encoding="utf-8")
    print(f"  secciones del municipio: {len(ancho)}")
    print(ancho.head(3).to_string())


def cartografia() -> None:
    print("INE cartografia de secciones censales")
    z = DATOS / "seccionado_2024.zip"
    descargar(CARTO, z)
    with zipfile.ZipFile(z) as zf:
        nombres = zf.namelist()
    print(f"  contenido ({len(nombres)} entradas):")
    for n in nombres[:12]:
        print("   ", n)


# Comprobacion de cordura del endpoint. Un espejo de Overpass que sirva otro
# extracto geografico responde 200 con cero elementos, que es un conjunto vacio
# perfectamente valido: el pipeline sigue y produce "Valencia no tiene centros
# de salud". Por eso la consulta de control se ejecuta **antes** que ninguna
# otra y aborta si falla, en vez de dejar que el vacio se propague.
CONTROL = ("[out:json][timeout:60];"
           "node(39.46,-0.40,39.49,-0.36)[amenity=pharmacy];out ids 5;")
MIN_CONTROL = 3


def overpass(consulta: str, etiqueta: str) -> dict:
    r = requests.post(OVERPASS, data={"data": consulta}, headers=H, timeout=300)
    r.raise_for_status()
    d = r.json()
    print(f"  {etiqueta}: {len(d.get('elements', []))} elementos")
    return d


def comprobar_endpoint() -> None:
    """El centro de Valencia tiene farmacias. Si el endpoint dice que no, miente."""
    n = len(overpass(CONTROL, "control de endpoint").get("elements", []))
    if n < MIN_CONTROL:
        raise SystemExit(
            f"El endpoint {OVERPASS} devuelve {n} farmacias en el centro de Valencia, "
            f"menos de {MIN_CONTROL}. Sirve otro extracto geografico o esta caido. "
            "Abortado para no producir un conjunto vacio que parece un resultado.")


def servicios() -> None:
    print("OpenStreetMap: servicios esenciales")
    comprobar_endpoint()
    s, o, n, e = BBOX
    caja = f"{s},{o},{n},{e}"
    q = f"""[out:json][timeout:180];
(
  nwr({caja})["amenity"="clinic"];
  nwr({caja})["amenity"="doctors"];
  nwr({caja})["amenity"="hospital"];
  nwr({caja})["healthcare"="centre"];
  nwr({caja})["healthcare"="hospital"];
);
out center tags;"""
    d = overpass(q, "sanitarios")
    filas = []
    for el in d["elements"]:
        t = el.get("tags", {})
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None:
            continue
        filas.append({"osm_id": f"{el['type']}/{el['id']}", "lat": lat, "lon": lon,
                      "nombre": t.get("name", ""), "amenity": t.get("amenity", ""),
                      "healthcare": t.get("healthcare", ""),
                      "operator": t.get("operator", ""),
                      "operator_type": t.get("operator:type", "")})
    df = pd.DataFrame(filas)
    if df.empty:
        raise SystemExit("Overpass no devolvio elementos: revisar el endpoint")
    df.to_csv(DATOS / "servicios_sanitarios_osm.csv", index=False, encoding="utf-8")
    print(f"  guardados {len(df)}; con nombre: {(df['nombre'] != '').sum()}")
    print("  por amenity:", df["amenity"].value_counts().to_dict())
    print("  por operator:type:", df["operator_type"].value_counts().head(5).to_dict())


def main() -> None:
    DATOS.mkdir(parents=True, exist_ok=True)
    adrh()
    print()
    cartografia()
    print()
    servicios()


if __name__ == "__main__":
    main()
