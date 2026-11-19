# Reproduction scope and remaining provenance

This package separates recomputation from included canonical inputs, redrawing from archived values, external-data preparation and new model calls. A successful package validation is not a claim that every historical input was recovered.

| Component | What can be reproduced | Boundary |
|---|---|---|
| National and individual LLM benchmarks | Fixed profiles, provider/ensemble predictions, adopted indicator metrics and nitrogen outcomes | The original280-profile sampling builder and original per-call dates/hashes were not retained |
| Country-label experiment | All1470matrixrecords, paired contrasts, ordering, variance summaries, weighted nitrogen scenarios |420records are response reuse; collection stages are not contemporaneous |
| Transfer benchmarks | Matched/rich pipelines and source-country-only validation | Input sets are not nested; hosted LLM training conditions differ |
| Trait regressions | Included64917-row pseudonymized survey input,488complete predicted profiles, coefficient/CV/interval calculations | Unknown EA labels cannot be recovered; household fallback leaves possible dependence between households |
| Post-stratification | Included55country-by-adoption/sex/education cell totals and profile household weights | Original broader survey reconstruction uses external official data and its recorded eligibility rules |
| National-statistics benchmark | Archived S8values and explicitly labeled rounded-input diagnostic reconstruction | Complete annual full-precision input series, exact spanning-year mapping and original conditional-bootstrap implementation were not located |
| Figure1 | Export of supplied current final image | Current editable engineering file was not located; included olderPowerPoint is historical |
| Figure2 | Redraw from available full-precision survey/model quantities and reported national-benchmark values | Some inputs are retained at table display precision; original national-regression fitting is not reconstructed by the plot |
| Other figures | Included code and source data for current figure numbers | Rendering can differ with fonts and operating systems |

The original `.dta` deposit is open CC0 1.0 and fetched separately because it is large. This is an acquisition choice, not a new access restriction. Code credentials are not part of the archive. Offline reproduction does not issue paid model calls.

Point estimates and sample sizes are protected in validation. Paper-level primary intervals use10000draws; a200draw smoke run is not substituted for archived confidence limits. Software versions and resampling seeds are stored with analysis outputs.
