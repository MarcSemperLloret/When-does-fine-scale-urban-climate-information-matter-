# Supplementary Material 3: shelter-hours decision companion

This anonymous package accompanies the shelter analysis in the manuscript. It reproduces decisions from the frozen factual catalogue, derived walking-distance matrix and estimated older population. It does not reconstruct every upstream geographic source or verify historical opening, admission, staffing, use or thermal exposure.

## Reproduce

Use Python 3.13 with the versions in requirements.txt. From this directory run:

```text
python -X utf8 evaluate_coverage.py
python -X utf8 optimise_extensions.py
python -X utf8 robust_extensions.py
python -X utf8 budget_thresholds.py
python -X utf8 verify_and_stress.py
```

The first four scripts regenerate the core hourly coverage, single-scenario policies, common policies and minimum-resource thresholds. The fifth independently reconstructs coverage and costs, checks an exhaustive small problem, and solves documentary/geometric sensitivities. Solves may take several minutes. No random sampling or seeds are used. Alternate optimal facility lists can occur across solver versions; compare objectives, bounds and feasibility rather than demanding a unique list.

Catalogue identifiers are zero-based (0–40). The primary 39-site inventory excludes IDs 13 and 14. CUSEC section identifiers are strings. Population65 is total population multiplied by the INE 2023 older-age percentage, joined to 2024 census boundaries. Distances are metres; facility coordinates are longitude/latitude EPSG:4326 and section geometry EPSG:25830. All time intervals are local civil time and half-open [start,end). No summer-2024 weather is used. There is no temperature input in this package.

The main benefit integrates union coverage over 16:00–21:00. Each population unit is counted once at each time regardless of overlapping facilities. Centre-hours count added opening between 08:00 and 21:00; they are neither staff-hours nor euros. Extending a centre prolongs its final daily opening interval to 21:00 without shortening later closing or removing earlier breaks. The 73.25-hour budget is reconstructed from ordinary schedules and a named announcement, not reported municipal expenditure. The 95% and 99% resource thresholds retain reference optima at that ORIGINAL budget.

## Files and provenance

catalogue_audited.json contains factual transcriptions, coordinates, source links and declared interpretations; full source prose is omitted. datos/distances.npz contains centroid_m, interior_m, network_m, CUSEC, site_id, population65 and district arrays. Geographic layers aid inspection; they do not establish actual entrances. resultados/ contains machine-readable policies, optima, bounds, table values and independent audit outputs. The cross_scenario_transfer.json greedy_capture_percent field evaluates a newly greedy selection at each scenario; the FROZEN central greedy comparison used by the paper is greedy_ids_frozen_capture in stress_tests.json. This distinction is essential.

fuentes/ contains retrieval URLs, UTC times and checksums, without raw pages, calendar PDFs or KML. network_provenance.json records original input basenames, hashes and graph conventions. Full graph reconstruction requires the upstream GraphML, edge, census-geometry and demographic files and is outside the portable decision-layer claim. The archived network_verification.json records upstream checks performed in the research workspace; it is not rerun by the portable scripts. Results retain an archival portability check; the final release also has a separate extraction audit outside the anonymous payload.

## Interpretation and rights

The event announcement names 23 facilities for 15 July 2026; its body contains a June/July inconsistency documented in Supplementary Material 1. The current catalogue and ordinary hours were retrieved in September. The 39-site reconstruction is conditional, and the 41-site and alternative-schedule variants do not prove historical truth. Announced-centres-only eligibility removes the modelled incompatibility. No operational recommendation follows from the solver list alone.

Street data: © OpenStreetMap contributors, https://www.openstreetmap.org/copyright, Open Database Licence (ODbL). INE and municipal providers retain their source-specific terms. This review companion does not grant a blanket licence over third-party data. Provider text, restricted weather observations and individual records are excluded. The source catalogue factual fields and derived data are supplied for scholarly audit with attribution. Preserve applicable provider obligations in subsequent redistribution. Code authorship and any public code licence remain with the manuscript authors; no public repository or DOI is claimed.
