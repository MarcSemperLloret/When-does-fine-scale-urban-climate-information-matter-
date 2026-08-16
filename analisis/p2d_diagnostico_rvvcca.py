"""Por que la red oficial RVVCCA no puede validar el campo termico intraurbano.

Se descargo el extracto horario de la Red Valenciana de Vigilancia y Control de
la Contaminacion Atmosferica que publica el Ayuntamiento (CC BY 4.0) con la
intencion de validar el campo observado contra estaciones oficiales que no
entran en la interpolacion. El extracto parecia inmejorable: doce estaciones,
temperatura horaria, cobertura del 96 al 100 % de las horas de junio a agosto
de 2019 a 2021, y ademas humedad, viento, presion y radiacion.

**La columna de temperatura no es por estacion.** Nueve de las doce etiquetas
comparten una unica serie identica hasta el ultimo decimal, incluidas las siete
que caen en tejido urbano. La desviacion tipica entre esas estaciones en un
mismo instante es exactamente cero en los 25 485 instantes con dato, y las
correlaciones por pares son 1.0000 exactas. Solo tres series son realmente
distintas: la replicada, Nazaret Meteo y las dos del puerto.

Un estudio de calor urbano construido sobre este fichero creeria disponer de
ocho estaciones intraurbanas y dispondria de una. El fichero esta completo, bien
formado, tiene licencia abierta y procede del organismo que opera la red; nada
en el delata el problema, que es justo el patron que documenta S2: el aviso no
es un valor implausible sino la ausencia de razon mecanica para el resultado.

Este script deja la evidencia por escrito. No valida nada, porque no se puede.

El fichero de entrada no se redistribuye aqui porque es un dato de origen de
48 MB; se descarga del portal municipal, que lo publica bajo CC BY 4.0:

    https://opendata.vlci.valencia.es/dataset/b5c2656c-6c1c-413d-a56e-549e52220502
        /resource/4be7248b-9597-4017-89af-82a9b6e2382f/download/
        rvvcca.-datos-horarios-valencia-2016-2021-curt-cas.csv

Guardarlo como `analisis/rvvcca_horario.csv`. Dos avisos sobre ese fichero, que
no estan documentados en el portal: publica en **UTC**, no en hora local, y la
hora del dia va en una columna `Hora` aparte, con `Fecha` siempre a medianoche,
de modo que `Fecha.dt.hour` devuelve cero para todas las filas.

Salida: salidas/tablas/p2d_diagnostico_rvvcca.csv
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
CSV = Path(__file__).resolve().parent / "rvvcca_horario.csv"
TABLAS = BASE / "salidas" / "tablas"
URBANAS = ["Avda. Francia", "Bulevard Sud", "Molí del Sol", "Pista Silla",
           "Politécnico", "Valencia Centro", "Viveros"]


def main() -> None:
    d = pd.read_csv(CSV, sep=";", encoding="utf-8-sig",
                    usecols=["Fecha", "Hora", "Estación", "Temperatura"],
                    parse_dates=["Fecha"])
    d = d.rename(columns={"Estación": "estacion", "Temperatura": "t"})
    p = d.pivot_table(index=["Fecha", "Hora"], columns="estacion", values="t")

    # Agrupacion de etiquetas cuya serie es identica hasta el ultimo decimal.
    grupos: list[list[str]] = []
    for c in p.columns:
        for g in grupos:
            q = p[[g[0], c]].dropna()
            if len(q) > 100 and (q[g[0]] - q[c]).abs().max() < 1e-9:
                g.append(c)
                break
        else:
            grupos.append([c])

    filas = [dict(grupo=i, n_etiquetas=len(g), etiquetas="; ".join(g))
             for i, g in enumerate(grupos, 1)]
    TABLAS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas).to_csv(TABLAS / "p2d_diagnostico_rvvcca.csv", index=False)

    urb = p[[c for c in URBANAS if c in p.columns]].dropna()
    sd = urb.std(axis=1)
    print(f"instantes con las {urb.shape[1]} urbanas a la vez: {len(urb)}")
    print(f"desviacion tipica ENTRE estaciones: max {sd.max():.10f}, "
          f"media {sd.mean():.10f}")
    print(f"correlacion minima por pares: {urb.corr().min().min():.6f}")
    print(f"\nseries realmente distintas: {len(grupos)} de {p.shape[1]} etiquetas")
    for i, g in enumerate(grupos, 1):
        print(f"  grupo {i} ({len(g)}): {', '.join(g)}")


if __name__ == "__main__":
    main()
