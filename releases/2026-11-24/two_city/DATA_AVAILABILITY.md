# Data and computational scope

The package provides aggregate derived section-level screening scores, their exact nonnegative components, population and district attributes, selection certificates and machine-readable outputs for 288 policy cases. Independent scripts verify the additive decision calculations and benchmark comparisons. The annual tables are derived outputs; they do not regenerate the underlying hourly observations from this package.

Raw AVAMET observations are not redistributed because access is subject to the provider's conditions. Full hourly weather, route and shade reconstruction remain in the research archive; census polygons locating the new alternatives are included. No individual health records are included. Population aged 65 or older is estimated from published aggregate counts and percentages.

Source providers: [AVAMET](https://www.avamet.org/), [Madrid municipal observations](https://datos.madrid.es/), [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/), [INE](https://www.ine.es/), [CNIG](https://centrodedescargas.cnig.es/), [Cadastre](https://www.catastro.hacienda.gob.es/webinspire/index.html), [Valencian health service register](https://www.san.gva.es/), [Madrid regional data](https://datos.comunidad.madrid/) and [OpenStreetMap](https://www.openstreetmap.org/copyright).

Reference periods: JJA 2019–2023 and 2025, demographic estimates for 2023 joined to 2024 census boundaries. The 2024 summer is excluded as a locked holdout for separate work. Contemporary networks and destinations are applied to historical weather; this does not reconstruct historical service availability. Madrid LiDAR dates from 2016–2017. Madrid's OSM extract is pinned to 6 September 2026; the Valencia upstream assembly took place in August 2026.

No manuscript, cover letter, author title page or editorial review is included. Preparation of this archive is not a public deposit. The exact repository version must be cited once deposited.


The fixed-grid extension adds 12 derived matrices, 108 optimisations, eight benchmark rules and census-polygon assessment alternatives in both cities. The external comparison adds conditional aggregate VITUclim results and derived observation-motivated decision matrices. These have different support and must not be combined as if they were one calibrated experiment.

Additional provider: [CEAM / VITUclim](https://www.vituclim.org/). The anonymous WFS is documented in `external/RETRIEVAL_AND_LIMITS.md`. Public technical accessibility is not treated as permission to redistribute observations. Raw VITUclim records are excluded because a dataset-specific redistribution licence was not documented. The fixed-grid principal analysis does not require VITUclim values or a choice of their clock.

Map attribution: census-section boundaries, INE 2024; derived demographic attributes, INE ADRH 2023. Walking-network calculations use © OpenStreetMap contributors, under the Open Database Licence (ODbL): https://www.openstreetmap.org/copyright . This companion distributes derived analytical results and census polygons, not the OSM graph or a replacement licensed database. Other source terms remain those of their providers.
