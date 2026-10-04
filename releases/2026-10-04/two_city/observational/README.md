# Observational analysis and one-reference sufficiency (4 October 2026)

This addition supports the spatial-MAE columns of main Table 2, main Table 3,
the one-reference simple-rule classification, and the descriptive six-summer
field-gradient and threshold-proximity summaries in Supplementary Material 1, S9.

## Portable rerun

Install requirements_decision.txt. From the extracted companion root:

    python analisis/revision_observacional.py --sm2 . --only sufficiency

This reconstructs the population and uniform selections for all 288 cases,
including ascending-CUSEC tie breaking, and evaluates local-only, regional-only
and two-reference sufficiency. Results go to qa/revision_observacional/.
Compare its sufficiency object and CSV with the frozen files in this directory.
Expected counts: both/local-only = 50 population + 162 additional uniform;
regional-only = 82 population + 201 additional uniform.

## Full upstream rerun

Install requirements_figures.txt (geospatial dependencies) in addition to the
decision dependencies. Obtain the provider-dependent inputs described below,
then run from the companion root:

    python analisis/revision_observacional.py --sm2 . --vit PATH_TO_VALIDATION --only all

The validation directory must contain:

- matched_pairs.parquet: timestamp (datetime), station_id (integer), clock
  (as_local_CEST, as_fixed_CET, as_UTC), window (Morning, Afternoon), observed,
  IDW, Uniform, Nearest and ERA5_corrected temperatures in degrees C.
- stations_selected.parquet: station_id, longitude, latitude (WGS84).
- city_fields_Morning.npz and city_fields_Afternoon.npz: CUSEC and the local and
  regional six-summer hourly fields, with one row per census origin.

The site comparison covers June-August 2025. Hourly errors are separated into
the site-panel mean and residual; the spatial MAE is the mean absolute residual.
Site anomalies subtract each hour's panel mean before time averaging. Bootstrap
intervals use 1,000 shared seven-day circular blocks with seed 20260921. The
regression amplitude is the OLS slope of predicted on observed site anomalies,
not a ratio of west-east gradients. A common component may vary between hours;
constant-offset decision stresses are separate sensitivity experiments.

The provider-dependent inputs are not redistributed. The frozen JSON contains
aggregate analysis outputs and intervals, enabling inspection of the reported
values; it does not replace independent recomputation from the matched inputs.
See external/RETRIEVAL_AND_LIMITS.md for retrieval and processing provenance.
The date-stamped plan is preserved verbatim as an analysis record: it was fixed
before these metrics were computed, after decision results were known, and is
not an external preregistration. The six-summer descriptive summary was added
afterwards and is explicitly exploratory.

The script is supplied without submission prose, manuscript source, raw sensor
records or internal editorial reviews. It writes new outputs separately from
the frozen results. SHA256SUMS.txt at the companion root includes this addition.
