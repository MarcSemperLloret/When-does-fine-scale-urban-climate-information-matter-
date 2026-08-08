#!/usr/bin/env python3
"""Puerta 2: descarga de ERA5-Land para el area de Valencia.

El piloto de accesibilidad comparo el campo observado contra un campo
espacialmente uniforme. Ese uniforme es un limite inferior de informacion
--una representacion incapaz por construccion de producir diferencias
espaciales-- y un revisor lo llamaria straw man con razon. ERA5-Land es el
baseline real: 0,1 grados, unos 9 km, que sobre Valencia son pocas celdas pero
no necesariamente una sola, y puede conservar algun gradiente costero.

Se descarga solo lo que el estudio usa: temperatura a 2 m, horaria, junio a
agosto, de los veranos de desarrollo. **2024 no se descarga**: es la muestra
confirmatoria congelada del proyecto y bajarla ahora invitaria a mirarla.

Credenciales desde downbursts-cv-pilot/.env, que git ignora.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cdsapi

BASE = Path(__file__).resolve().parents[1]
DATOS = BASE / "datos" / "era5land"
ENV = BASE.parents[0] / "downbursts-cv-pilot" / ".env"

# Caja de descarga en el orden que pide el CDS: norte, oeste, sur, este.
# Generosa respecto al termino municipal para que la interpolacion a las
# secciones no dependa de celdas de borde.
AREA = [39.65, -0.65, 39.20, -0.15]

ANIOS = ["2019", "2020", "2021", "2022", "2023", "2025"]
MESES = ["06", "07", "08"]
LOCKED = "2024"


def credenciales() -> tuple[str, str]:
    kv = {}
    for linea in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in linea and not linea.strip().startswith("#"):
            k, v = linea.split("=", 1)
            kv[k.strip()] = v.strip().strip('"').strip("'")
    url, key = kv.get("CDS_API_URL", ""), kv.get("CDS_API_KEY", "")
    if not url or not key:
        sys.exit("Faltan CDS_API_URL o CDS_API_KEY en el .env")
    return url, key


def peticion(anios, meses, dias, destino: Path) -> None:
    url, key = credenciales()
    if LOCKED in anios:
        sys.exit(f"{LOCKED} es el ano confirmatorio congelado: no se descarga")
    c = cdsapi.Client(url=url, key=key, quiet=False, wait_until_complete=True)
    c.retrieve(
        "reanalysis-era5-land",
        {
            "variable": ["2m_temperature"],
            "year": anios,
            "month": meses,
            "day": dias,
            "time": [f"{h:02d}:00" for h in range(24)],
            "area": AREA,
            "data_format": "netcdf",
            "download_format": "unarchived",
        },
        str(destino),
    )
    print(f"  escrito {destino} ({destino.stat().st_size/1e6:.1f} MB)")


def main() -> None:
    DATOS.mkdir(parents=True, exist_ok=True)
    modo = sys.argv[1] if len(sys.argv) > 1 else "prueba"

    if modo == "prueba":
        # Un solo dia: valida credenciales, licencia aceptada y geometria de la
        # caja antes de encolar seis veranos.
        destino = DATOS / "prueba_2023_07_01.nc"
        peticion(["2023"], ["07"], ["01"], destino)
    elif modo == "completo":
        # Los seis veranos en una sola peticion los rechaza el CDS con
        # "cost limits exceeded": 6 x 3 x 31 x 24 son 13.392 campos. Se parte
        # por ano y mes, 744 campos cada una, y se concatena despues.
        dias = [f"{d:02d}" for d in range(1, 32)]
        pendientes = []
        for anio in ANIOS:
            for mes in MESES:
                destino = DATOS / f"era5land_{anio}_{mes}.nc"
                if destino.exists():
                    print(f"  ya estaba: {destino.name}")
                    continue
                pendientes.append((anio, mes, destino))
        print(f"  peticiones pendientes: {len(pendientes)}")
        for anio, mes, destino in pendientes:
            print(f"  -> {anio}-{mes}")
            peticion([anio], [mes], dias, destino)
    else:
        sys.exit("uso: p2_descargar_era5land.py [prueba|completo]")


if __name__ == "__main__":
    main()
