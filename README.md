# When does fine-scale urban climate information matter?

Analysis code and derived results for a study of thermal exposure and pedestrian
accessibility to primary-care centres for adults aged 65 and over in València
(Spain).

The study asks a decision question rather than a mapping question: **which
information layer actually changes a prioritisation decision?** It compares five
representations of the environment — regional reanalysis with and without urban
shade, local observations with and without shade — and measures not whether they
agree spatially but whether they select the same places to act on.

Two results organise the repository:

- **Spatial agreement is not decision efficiency.** Substituting the corrected
  regional field for the local observed field reclassifies up to 10,128
  residents aged 65+, and yet, paired with a complete building-plus-vegetation
  shade layer, it retains 94.3–99.8 % of the attainable prioritisation benefit.
- **The value of information depends on the active constraint.** When the number
  of sections failing the binding solar constraint exceeds the prioritisation
  quota, the thermal layer is *decision-inactive*: it cannot change the outcome
  regardless of its quality.

---

## Data: what is here and what is not

**No raw observations are redistributed in this repository.**

Air temperature comes from the AVAMET volunteer network (Associació Valenciana
de Meteorologia) under a research access agreement that covers **access, not
redistribution**. What is published here are **derived products only** —
per-station quality-control metrics, coverage statistics, hourly anomalies,
aggregated exceedance frequencies, and station identifiers and coordinates.
There is no minute-level or hourly observation anywhere in this tree, and the
query endpoint is not included.

**If you need the raw AVAMET series, request them from AVAMET directly.** Please
do not ask us to forward them.

Every other input is openly available and can be re-downloaded by the scripts in
`analisis/`. Nothing under `datos/` is shipped (≈660 MB, all obtainable from the
sources below).

| Layer | Source | Version / reference period |
|---|---|---|
| Air temperature | AVAMET volunteer network | summers 2019–2023, 2025 |
| Regional reanalysis | ERA5-Land via Copernicus CDS | hourly, same summers |
| Building footprints | Spanish Cadastre, INSPIRE | `A.ES.SDGC.BU.46900` |
| Building heights | CNIG MDSnE2.5 | 2nd coverage, sheets 0696/0722/0747 |
| Vegetation heights | CNIG MDSnV2.5 | 2nd coverage, same sheets |
| Census sections | INE | `SECC_CE_20240101` |
| Population 65+ | INE ADRH demographic indicators | reference year 2023 |
| Primary-care centres | Generalitat Valenciana | `ca_centros_salud` |
| Pedestrian network | OpenStreetMap via OSMnx | `walk` network |

**Summer 2024 is deliberately excluded and was never inspected.** It is a locked
confirmatory holdout for the wider project this work belongs to. Please keep it
closed if you extend this analysis.

ERA5-Land downloads need Copernicus CDS credentials in a `.env` file
(`CDS_API_URL`, `CDS_API_KEY`). None are included here.

---

## Layout

```
analisis/          the pipeline, in numbered stages
salidas/tablas/    every derived table the paper reports
salidas/figuras/   the five main figures and one supplementary
informes/          the methodological record, including the failure table
```

`informes/TABLA_FALLOS_SILENCIOSOS.md` is worth reading before the code. It
documents fifteen silent failure modes found during this work — cases where the
analysis produced a plausible wrong answer without any error being raised. In
thirteen of the fifteen, **the erroneous result was cleaner than the correct
one**: a Jaccard of exactly 1.000, a round 80 m median building height, a
well-formed empty set. The safeguards adopted in response are part of the
method, not incidental.

---

## Running it

Python 3.11.

```bash
pip install -r requirements.txt
export CENTROS=oficial          # official register; use 'osm' for the sensitivity run
```

Stages, in order. Stage 0 requires the AVAMET archive and cannot be run without
it; every later stage runs from the derived tables shipped here.

```bash
# 0. thermal data and station quality control  (needs AVAMET access)
py -3.11 analisis/extraer_subconjunto_valencia.py
py -3.11 analisis/p0_inventario.py
py -3.11 analisis/p1_senal_termica.py
py -3.11 analisis/p1b_escalas.py

# 1. regional reanalysis and bias correction   (needs CDS credentials)
py -3.11 analisis/p2_descargar_era5land.py
py -3.11 analisis/p2_comparar_era5land.py
py -3.11 analisis/p2b_control_interpolador.py
py -3.11 analisis/p2c_validacion_sesgo.py

# 2. urban form and shade
py -3.11 analisis/p3_descargar_edificios.py
py -3.11 analisis/p3_validar_lidar.py
py -3.11 analisis/p3_altura_final.py
py -3.11 analisis/p3_sombra_edificios.py
py -3.11 analisis/p3_sombra_vegetacion.py
py -3.11 analisis/p3_rutas_sombra.py
py -3.11 analisis/p3_factorial.py
py -3.11 analisis/p3b_transmitancia.py

# 3. accessibility, prioritisation and regret
py -3.11 analisis/p4_descargar_datos.py
py -3.11 analisis/p4_piloto_accesibilidad.py
py -3.11 analisis/p4c_regret.py
py -3.11 analisis/p4d_regret_bootstrap.py
py -3.11 analisis/p4f_bootstrap_bloques.py

# 4. robustness
py -3.11 analisis/p5_robustez_rutas.py
py -3.11 analisis/p5b_dominancia_presupuesto.py

# 5. figures, and a check that the reported numbers match the tables
py -3.11 analisis/figuras_manuscrito.py
py -3.11 analisis/verificar_cifras.py
```

`verificar_cifras.py` recomputes each published quantity from its source table.
It exists because after one large re-run four figures survived in the text at
their pre-run values, two of them landing on suspiciously round numbers. A stale
number is plausible by construction, because it *was* correct — reading the text
does not catch it.

---

## Notes on two choices that affect reproduction

**The Pareto frontier is approximated.** Routes come from a weighted-sum scan
over 21 weights, which recovers only *supported* efficient solutions; the exact
problem is a resource-constrained shortest path, NP-hard in general. The
approximation is conservative: reported exposure is an upper bound and the
shade-related saving a lower bound. A 5-weight grid is *not* converged — it
misses better routes in 9–28 % of sections — so do not reduce `LAMBDAS` in
`p3_rutas_sombra.py` without re-checking convergence.

**Confidence intervals use moving blocks, not independent days.** Heatwaves
autocorrelate consecutive days, which makes independent-day resampling
anticonservative by a factor of about 1.58 in interval width. The published
bands come from 1000 resamples of seven-day blocks drawn within each summer.

---

## What is not here

The manuscript itself. It is under review; this repository is the analysis
artefact only.

## Licence

MIT for the code. Derived tables are released under CC BY 4.0. Neither covers
the underlying AVAMET observations, which are not distributed here.
