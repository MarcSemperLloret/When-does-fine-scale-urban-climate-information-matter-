# Portable decision-level reproducibility package

This package supports the Valencia–Madrid heat-access screening revision. It contains aggregate derived census-section scores, demographic/district attributes, solver outputs and an independent audit. It contains no raw restricted AVAMET observations and does not claim to regenerate the weather, street network or shade geometry from provider downloads.

## Run

Use Python 3.13 and install `requirements_decision.txt`. From the extracted package root:

```text
python analisis/verificar_decisiones_portatil.py --resolve
```

The audit checks all 288 policy cases, 8,640 capacity–tolerance cases, the cardinality/capture/TV of 256 feasible district selections, eight exhaustive-enumeration examples and 12 frozen selections evaluated under the 41-weight score reference. With `--resolve`, it independently re-solves 44 common-loss problems: all 32 infeasible cases and the 12 central cases. Omitting the flag skips these optimisation reruns but retains the other checks. Outputs are written inside `qa/`.

## Data dictionary

- `datos/policy_scores_two_cities.parquet`: one row per section and policy case. Keys are `city`, `CUSEC`, `mode`, `window`, `threshold`, `phi`; `reachable` defines the selection universe. `local`, `regional` and `uniform` are population-weighted failure scores, not temperatures, outcomes or clinical benefits.
- `datos/secciones_*.csv`: aggregate attributes. `pob_65` is estimated population aged 65+. `CDIS` (Madrid) or `distrito` (Valencia) identifies the district.
- `mode`: `network` omits origin/destination connections; `connectors_sun` or `connectors_shade` includes their straight-line lengths with all-sun/all-shade exposure. These are geometric scenarios, not certified all-path bounds.
- `datos/central_*_working_Full_scores.parquet`: central scores with both 21- and 41-weight route grids. Additional columns contain derived scores under alternative temperature references. No raw weather records are included.
- `datos/cache_sensibilidad/*.json`: 276 unique solver certificates for 288 designed cases. `indices` refer to ascending CUSEC among reachable sections in that case. Some cases have identical inputs. `minimum_common_loss_percent` is the required loss before a district objective; `balance_status` distinguishes optimal allocations from proven incompatibility.
- `tablas/policy_sensitivity_two_cities.csv`: all 288 outcomes at 15% capacity. Captures and loss columns are percentages; district TV is a fraction from 0 to 1.
- `tablas/policy_capacity_two_cities.csv`: exact additive diagnostics at five capacities and six allowances. `tolerance` is a fraction (0.01 means 1%). District optimisation is not repeated over this whole table.
- `tablas/compromiso_malla41.csv` and `central_*_selections.csv`: refined-grid outcomes and identifiers of the central frozen selections.
- Other tables retain central checks, validation, bootstrap and reference stresses. Their presence does not imply that this portable audit reconstructs every upstream experiment.

The local reference is a transparent model choice, not ground truth. Capture percentages compare each selection with that scenario's own score optimum. District proportionality concerns assessment slots, not observed health equity. The designed grid has no probability weights.

All provided files are listed in `SHA256SUMS.txt`. This decision-level companion was updated on 4 October 2026. Raw provider observations and full geographic reconstruction are outside this package; see DATA_AVAILABILITY.md and RIGHTS.md.


## Explanatory revision: components, practical baselines and annual limits

Run the additional independent audit from the extracted package root:

```text
python analisis/verificar_componentes_portatil.py
```

It checks 437,904 section–case component rows, all 288 partitions and 1,728 fixed-baseline evaluations. It verifies the 50/162/44/32 hierarchical states, 253 passing pooled lists, three feasible cases missed by all fixed controls, signed exchange-loss reconstruction and improvement over the best passing baseline. It imports no code from the generating analysis.

- `datos/score_components.parquet`: the five components are `solar_failure`, `shared_thermal_failure`, `local_only_failure`, `regional_only_failure`, `joint_pass`. They are population-weighted hourly category frequencies; their sum is `pob_65`. Solar failure is assigned before thermal attribution. They do not measure separate causal effects.
- `tablas/mechanism_summary.csv`: 288 cases. `*_population_share` divides a component sum over reachable sections by their estimated older population. `*_local_top_score_share` divides its sum within the local top list by the optimal local score. Only solar, shared-thermal and local-only parts partition that local score. Regional-only and joint-pass columns with this suffix are comparisons using the same denominator, not parts of the local score. `*_exchange_loss_percent` are signed percentage-point contributions to the local loss of the regional shortlist.
- `joint_pass_frequency_population_weighted` is the fraction passing solar and both thermal criteria, weighted by population; it equals `joint_pass_population_share` and is retained as an explicit field label.
- `tablas/practical_benchmarks.csv`: six rules for each case. `minimum_capture` is the smaller percentage capture under the two references. `dual_feasible` requires at least 99% within numerical tolerance. `district_TV` is a fraction, not a percent. Normalised pooling ranks by `local/local_optimum + regional/regional_optimum`; multiplying by one half changes no ranking.
- `tablas/mechanism_annual_central.csv`: 72 annual central summaries with the pooled regional correction fixed, annual rankings and annual reference denominators. This differs from leave-summer-out calibration.
- `analisis/figuras_explicativas.py` regenerates the three new figures and three LaTeX tables from these derived tables. Install `requirements_figures.txt` for this optional step.
- `qa/mechanism_audit.json`, `qa/independent_mechanism_checks.csv`, `qa/annual_audit.json` and `qa/independent_annual_checks.csv` record the separate checks.

The annual checks were also independently rerun from hourly arrays using direct conjunction scores rather than sums of the components. That script, `analisis/verificar_anuales.py`, and the generator `analisis/explicar_decisiones.py` require the original adjacent Madrid and Valencia archive directories and are retained in the upstream research archive; they are not advertised as runnable from the portable data alone. The portable annual table is a derived output, not a new out-of-sample validation.


## Principal fixed-grid extension (21 September 2026)

This companion accompanies *When does intra-urban temperature information change heat-adaptation priorities? Evidence from Valencia and Madrid*. It is a code and derived-data companion; its selected sets are candidates for assessment.

The principal extension uses both cities and all six original summers (2019–2023, 2025). It adds uniform offsets on a fixed 0.25°C grid to both fields and searches for one shortlist meeting all active scenarios. It does not derive these offsets from VITUclim measurements. For this threshold score, uniform temperature shifts are mathematically equivalent to threshold changes. This is an exploratory analysis designed after the earlier study and external pilot, not an independent prospective validation.

Run the independent new audit:

```text
python analisis/verificar_fixed.py --resolve
```

All 108 optimisations, 864 benchmark comparisons, zero-shift identities, selected-set cardinalities, normalisation, scenario nesting, stored primal/dual bounds and four small exhaustive-enumeration oracles are checked. `--resolve` independently solves every fixed-grid problem in a loss-minimisation formulation; the generator uses capture maximisation. Exact optimal membership can be non-unique; reproduction targets objective values and feasibility rather than identical tie-dependent MILP lists. Omitting `--resolve` keeps the stored-certificate and arithmetic checks.

- `fixed/*.npz`: 12 city/window/connection matrices. `scores` has 34 rows (17 Local then 17 Regional offsets from −2 to +2°C) and one column per reachable census section. `normalised` is 100 times each score divided by its own top-K total. `CUSEC`, `population`, `district`, `delta`, `names`, `quota` define alignment. All arrays can be read with `allow_pickle=False`.
- `fixed/summary.json`: 108 optimum values, selected zero-based indices, MIP dual bounds/gaps and LP-relaxation bounds. Each amplitude keeps every row with absolute `delta` at most that amplitude.
- `fixed/benchmarks.parquet`: eight rules for each case/amplitude. Six original lists remain fixed at zero shift, all-scenario pooling ranks the active normalised mean, and maximin optimises the worst active capture.
- `fixed/margins.json`: first incompatible amplitude on the tested grid; `null` means no incompatibility through ±2°C, not a globally safe bound.
- `fixed/inspection_a1.parquet`: original-local, uniform and maximin membership at ±1°C. It is a proposed assessment agenda, not a validated intervention list.
- `fixed/mapas/*.gpkg`: all census polygons with membership status (`both`, `added`, `removed`, `neither`, `unreachable`) for both windows and three connection modes. INE 2024 boundaries; geometry is supplied to locate the derived selection results. The plotted extent covers reachable sections, while the files retain all sections.
- `fixed/input_sha256.json`: hashes of the archived upstream files used by the new score generator. Those archived hourly fields are not distributed here. The decision audit begins at the supplied score matrices; it cannot verify those matrices from restricted hourly observations.

Optional figure regeneration, requiring `requirements_figures.txt` and the installed geospatial dependencies recorded in `environment.json`:

```text
python analisis/figuras_explicativas.py
python analisis/figuras_fixed.py
```

These regenerate the two original explanatory main figures, the district supplement figure, both new fixed-grid figures and their derived tables. Other supplied legacy figures and thermal tables are archived outputs, not all regenerated by these scripts. The main manuscript figure order is F4_score_partition, F6_practical_states, F10_fixed_margin, F11_fixed_maps; file labels identify provenance rather than final figure numbers.

## Complementary external evidence and observation-motivated stress

`external/` holds conditional aggregate outputs from the 29-site VITUclim Valencia JJA-2025 comparison. Neither raw VITUclim data nor restricted AVAMET observations are included. See `external/RETRIEVAL_AND_LIMITS.md` for the public retrieval specification, panel definition, processing and unresolved metadata. These aggregate files allow inspection of the reported values, but do not independently regenerate MAE or bootstrap intervals from raw observations.

`observation_stress/` is the separate, complementary Valencia-2025 experiment in Supplementary Material 1, Section S10. Its magnitudes are observation-motivated under three possible clocks. It is not the principal fixed grid, does not use the six-summer support, and does not estimate a calibrated error distribution. `scenarios_*` matrices contain 14 scenarios; `symmetric_*` contain 26; subset outputs compare 18 clock/window/connection cases. The negative residual biases are illustrative scalar perturbations, not validated bias corrections.

```text
python analisis/verificar_observation_stress.py
```

This checks the supplied complementary matrices, benchmark membership, minimum-capture arithmetic, nesting and independent LP upper bounds. It does not resolve VITUclim timing, calibration, installation height, reuse conditions or actual route exposure. No new CEAM confirmation was available when this package was prepared.

## Reproduction boundary

The paper's numerical guarantees are finite-scenario, additive-score statements. The matrices permit decision-level reproduction, including independent optimisation. They do not guarantee physical exposure, health effects, future climate performance or municipal adoption. The fixed grid has no fitted probabilities. Shared code and aggregate outputs are supplied for review; provider-specific rights remain applicable. `RIGHTS.md` makes no blanket third-party licence claim. No new public DOI or public deposit is asserted.


## Observational extension (4 October 2026)

The analysis script, dated plan and aggregate outputs for the new spatial-error and site-pattern checks are included. See observational/README.md for the portable one-reference rerun and the provider-dependent full rerun. The one-reference check runs without raw temperature records. The site checks require inputs described in that README.
