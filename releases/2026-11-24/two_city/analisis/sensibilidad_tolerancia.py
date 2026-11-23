"""Reclassify the 288 grid cases under alternative loss allowances.

The population list, the uniform-temperature list and the minimum common loss
do not depend on the allowance, so the hierarchical states can be recomputed
from tablas/policy_sensitivity_two_cities.csv without new optimisations.

Usage (from an extracted Supplementary Material 2):
    python analisis/sensibilidad_tolerancia.py
"""
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tablas/policy_sensitivity_two_cities.csv"
OUT = ROOT / "tablas/sensibilidad_tolerancia.csv"
ALLOWANCES = (0.25, 0.5, 1.0, 1.5, 2.0, 3.0)


def classify(cases, allowance):
    population = cases.population_loss_percent <= allowance
    uniform = ~population & (cases.uniform_loss_percent <= allowance)
    common = ~population & ~uniform & (cases.minimum_common_loss_percent <= allowance)
    state = pd.Series("X", index=cases.index)
    state[common] = "C"
    state[uniform] = "U"
    state[population] = "P"
    return state


def main():
    cases = pd.read_csv(SOURCE)
    assert len(cases) == 288
    rows = []
    for allowance in ALLOWANCES:
        state = classify(cases, allowance)
        for (city, window), group in state.groupby([cases.city, cases.window]):
            counts = group.value_counts()
            rows.append({"allowance_percent": allowance, "city": city, "window": window,
                         **{s: int(counts.get(s, 0)) for s in "PUCX"}})
    table = pd.DataFrame(rows)
    central = table[table.allowance_percent == 1.0][list("PUCX")].sum()
    assert tuple(central) == (50, 162, 44, 32), "central classification not reproduced"
    table.to_csv(OUT, index=False)
    totals = table.groupby("allowance_percent")[list("PUCX")].sum()
    totals["simple"] = totals.P + totals.U
    print(totals.to_string())


if __name__ == "__main__":
    main()
