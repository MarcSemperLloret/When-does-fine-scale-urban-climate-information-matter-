# Analyses added in revision (R1)

This folder adds the scripts and derived outputs of the analyses introduced in response to the reviewers. They are described in Methods 3.2–3.3, Sections 4.2 and 4.5, Fig. 5 and Supplementary Material 1, Section S12. Everything outside this folder is the original decision-level companion, unchanged.

## Contents

| Folder | Analysis | Main outputs |
|---|---|---|
| `amplificacion/` | Rescaling of the station field's hourly spatial anomalies by a factor *a* (Eq. 5), and the observational calibration of *a* at the 29 VITUclim sites | `amplificacion_288.csv` (288 cases × 9 values of *a*), `calibracion_amplificacion.csv`, `resumen_amplificacion.csv` |
| `perturbaciones/` | Persistent site residuals and their empirical variograms; Gaussian-process section errors (σ = 0.4 and 0.6 °C, correlation length 0–5 km, 100 realisations) | `residuos_vituclim.csv`, `variogramas_empiricos.json`, `perturbaciones_100.parquet` (one row per case, setting and realisation), `resumen_*.csv` |
| `capacidad/` | Full P/U/C/X classification at capacities of 5–25% with the common-loss MILP, shortlist overlap, and states under amplification | `capacidad_288x5_estados.csv`, `estados_capacidad.csv`, `estados_amplificacion.csv` |
| `formulaciones/` | Continuous score forms, rank decomposition, routes near the shade threshold and slower walking speeds | `continuas.csv`, `descomposicion.csv`, `umbral_sombra.csv`, `velocidad.csv` |
| `huecos/` | Central-case capture and turnover table, exceedance skill at the VITUclim sites, threshold frequencies, population-allocation errors, station-network sensitivity (Valencia leave-one-station-out, Madrid alternative networks), canopy transmittance and the all-hours disagreement map | `tabla_central.csv`, `excedencia_vituclim.csv`, `excedencia_mixtas.csv`, `umbrales_frecuencia.csv`, `poblacion_ruido.parquet`, `red_estaciones.csv`, `transmitancia.csv`, `mapa_sin_sombra.csv`, `Figure_S_temperature_only.pdf` |
| `huecos2/` | Exact walking-speed and time-budget sensitivity from the stored route candidates, inference of the VITUclim timestamp convention, the near-coast station against its neighbouring sites, alternative interpolators of the Valencia stations and unequal section costs | `velocidad_exacta.csv`, `reloj_vituclim.csv`, `estacion_costera.csv`, `interpoladores_validacion.csv`, `interpoladores_decision.csv`, `costes_desiguales.csv` |
| `origenes/` | Alternative pedestrian origins inside each section (re-routing from three random interior points), a targeted k-shortest-path check of routes near the shade threshold, the three conditions table and the profile of excluded sections | `origenes_*.csv`, `rutas_k_*.csv`, `tres_condiciones.csv`, `secciones_excluidas.csv` |
| `utci/` | UTCI-based screening score with citywide ERA5 humidity, wind and radiation, retrieved from the Open-Meteo historical archive (ERA5 model; re-download with `descargar_openmeteo.py`, data under CC BY 4.0). Downward longwave is parametrised and calibrated against ERA5 from the Copernicus Climate Data Store for Valencia 2021 (`calibrar_onda_larga.py`, `onda_larga_calibracion.json`) | `utci_estados.csv`, `utci_diagnostico.csv` |
| `celdas_era5/` | Sites and mean anomalies per corrected ERA5-Land cell | `celdas_era5.csv` |
| `figura5_sensibilidad.py`, `figuras/` | Fig. 5 from the outputs above | `figuras/Figure_5.pdf` |

Column names follow the original companion. Losses and captures are percentages. `state` takes the values P (population sufficient), U (uniform sufficient), C (another common selection exists) and X (no common selection). `changed_*` columns count census sections that differ between two shortlists of the same size *k*.

## What runs from this package

The following run from the extracted package root, with the packages in `requirements_decision.txt`:

```text
python revision_R1/capacidad/capacidad.py
python revision_R1/figura5_sensibilidad.py
cd revision_R1/capacidad && python resumir_capacidad.py && cd ../..
cd revision_R1/amplificacion && python resumir.py && cd ../..
cd revision_R1/perturbaciones && python resumir_perturbaciones.py perturbaciones_100.parquet && cd ../..
cd revision_R1/formulaciones && python resumir_formulaciones.py && cd ../..
```

The first two commands run from the package root. The summary scripts read the outputs in their own folders, so the block changes into each folder and back. `capacidad.py` reads `datos/policy_scores_two_cities.parquet` from this companion and reproduces the published 15% losses and states exactly before extending them to the other capacities.

The other generators (`amplificar_contraste.py`, `velocidad_exacta.py`, `reloj_vituclim.py`, `estacion_costera.py`, `interpoladores.py`, `costes_desiguales.py`, `estaciones_sombra_mapa.py`, `rapidos.py`, `estados_amplificacion.py`, `perturbar.py`, `formulaciones.py`, `residuos_vituclim.py`, `calibrar_amplificacion.py`, `celdas.py`) need the hourly station and ERA5-Land fields, the stored route tables and, for the observational parts, the matched VITUclim pairs. These upstream inputs derive from restricted AVAMET observations and from VITUclim records without documented redistribution terms, so they are not included (see `DATA_AVAILABILITY.md`). The scripts are supplied so that the computations can be inspected, and so that readers with authorised access can rerun them once the matched inputs have been prepared as described in the observational README. Each generator checks its reconstruction against the published scores before computing anything new: the 288 local, regional and uniform scores to 10⁻⁹, and the published 15% losses to 10⁻¹³.

## Reproducibility notes

- All optimisations (1,440 in the capacity sweep and 2,016 under amplification) terminated with certified optimality (`milp_status` = `optimal`); the unequal-cost knapsacks were solved to a relative gap of at most 10⁻⁶.
- VITUclim timestamps are UTC, as inferred in `huecos2/reloj_vituclim.py`; analyses that use the matched pairs report the UTC rows as primary.
- Perturbations use the seed 20261123 and common random numbers across cases.
- Madrid perturbations transfer the Valencia residual statistics, because Madrid has no independent panel.
- `formulaciones/velocidad.csv` is an earlier approximation of slower walking speeds; it is superseded by the exact recomputation in `huecos2/velocidad_exacta.csv`.

## Preparing the matched VITUclim inputs (readers with authorised access)

`vituclim_preparacion/` contains the three scripts that built the matched inputs used by `analisis/revision_observacional.py` and by the revision analyses. No observations are included.

1. `descargar.py` downloads the 10-minute records of each selected site for June–August 2025 from the provider's anonymous WFS (`https://vituclim.org/geoserver/ceam/wfs`, layer `ceam:vp_reporte_estaciones_10min`), month by month, and stores a SHA-256 provenance record next to each file. The 2024 summer is not requested. Site selection (at least 90% of expected readings in June–August 2025, inside the Valencia study sections) follows `external/RETRIEVAL_AND_LIMITS.md`.
2. `preparar.py` applies the quality control, aggregates readings to clock hours and builds `matched_pairs.parquet` and `stations_selected.parquet` with the schema given in `observational/README.md`, pairing each site-hour with the IDW, uniform, nearest-station and corrected ERA5-Land predictions under each of the three clock conventions.
3. `analizar.py` computes the site metrics. `huecos2/reloj_vituclim.py` then infers the timestamp convention (UTC) from the same records.

Paths at the top of each script point to the research archive and must be adapted. Whether the provider's terms allow a given reuse must be checked with the provider before downloading.
