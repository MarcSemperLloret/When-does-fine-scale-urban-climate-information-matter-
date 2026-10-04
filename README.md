# Heat-adaptation decision analysis: Valencia and Madrid

Code and derived-data companion for **When does intra-urban temperature
information change heat-adaptation priorities? Evidence from Valencia and Madrid**.

The current analysis release is [releases/2026-10-04](releases/2026-10-04/).
It contains the two-city heat-access screen, fixed-grid and observation-motivated
decision stresses, the 29-site external-comparison analysis and aggregate outputs,
and the complementary Valencia climate-shelter opening-hour analysis.

## Run the current release

Use Python 3.13. From releases/2026-10-04/two_city/:

    python -m pip install -r requirements_decision.txt
    python analisis/verificar_decisiones_portatil.py --resolve
    python analisis/verificar_componentes_portatil.py
    python analisis/verificar_fixed.py --resolve
    python analisis/verificar_observation_stress.py
    python analisis/revision_observacional.py --sm2 . --only sufficiency

The last command recomputes one-reference sufficiency from distributed derived
inputs. Its full site-analysis mode requires the provider-dependent matched data
described in two_city/observational/README.md. Aggregate results and the dated
analysis plan are included, while raw AVAMET/VITUclim observations are excluded.

For shelters, follow releases/2026-10-04/shelters/README.md and its pinned
requirements.txt. The two companions document their own reproduction boundaries.

## Contents and scope

- two_city/: derived scores and components for 288 cases, matrices, optimisation
  certificates, independent checks, thermal sensitivity outputs, and the
  observational extension (spatial error, site patterns and one-reference counts).
- shelters/: frozen factual catalogue, derived inputs, decisions, optimisation
  certificates and executable audits for opening-hour resource choices.
- SHA256SUMS.txt: release-level hashes for every included file.

The code supports decision-level reproduction and inspection of aggregate thermal
outputs. Complete upstream thermal/geographic regeneration requires the documented
provider inputs. Results concern modelled priorities and potential access.

## Rights and citation

The repository MIT licence applies to the analysis code. Derived third-party
inputs remain subject to provider terms; see the companions' RIGHTS.md and
DATA_AVAILABILITY.md. OpenStreetMap attribution and geographic-source terms apply.
This release contains no manuscript PDF/source, cover letter, highlights,
restricted sensor records, full third-party web pages or internal editorial notes.

Use CITATION.cff for the current analysis release. No new DOI is asserted. The
earlier Valencia-only artefact is archived at
https://doi.org/10.5281/zenodo.21851740 and is not the current release. Legacy
files remain in the repository root for provenance; current instructions refer
to releases/2026-10-04/.
