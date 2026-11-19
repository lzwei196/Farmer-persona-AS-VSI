# Change log

## 0.3.1 2026-11-08

- Updated the title to that of manuscript v5: "Large language model agents know the country, not the farmer: Simulating fertilizer use in data-scarce regions".
- Removed the supplementary fertilizer-price comparison (former Supplementary Text S7 and Table S13), its 6,525 raw responses and code, in line with manuscript v5.
- Updated documentation, provenance, run_all.py and validate_release.py, and rebuilt all checksum manifests.

## 0.3.0 2026-11-07

- Aligned the package with the revised manuscript (v4): "Can large language model agents simulate cross-country differences in farmers’ fertilizer use? Implications for data-scarce regions".
- Removed the four-country prompt-design comparison (former Table S9), its response archive, analysis program and exploratory prompt templates; those data belong to a related manuscript (Li et al., 2026, COMPAG-D-26-10597).
- Renumbered Supplementary Tables S10–S13 as S9–S12 in files, code, provenance and documentation.
- Added data/supplementary_price_ladder/ (6,525 raw responses, inputs and code) and Supplementary Table S13, reproduced exactly by code/price_ladder_table_S13.py.
- Redacted machine paths ("<home>") in failed-call error messages and run logs of the price-ladder raw files; no decision field changed.
- Updated run_all.py and validate_release.py, refreshed the manuscript reference snapshot and rebuilt all checksum manifests.

## 0.2.1 2026-10-20

- Packaged the current analysis inputs, code and sources for Figures 1–8 and Supplementary Figure S1 as one release. Figure 6 is included under figures/Fig6 with the same data, outputs and reference structure as the other figures.
- Retained the October 19 AUC correction and all existing analysis results without numerical changes.
- Updated release metadata and rebuilt the package manifests.

## 2026-10-19 audit correction

- Corrected the Codex/Niger AUC confidence interval in Table S5 to 0.500–0.586. The point estimate is unchanged. The archived interval had omitted 433 valid constant-score bootstrap draws; the existing analysis code includes them.
- Verified the full 10,000-draw offline workflow and reconstructed survey inputs, weights and targets from the official source. The exact historical Table S8 reconstruction limit remains documented.

## 0.2.0 2026-10-17

- Unified the original package and October 17 statistical corrections.
- Expanded coverage to current Figures 1–8 and Supplementary Figure S1, Tables 1–3 and Supplementary Tables S1–S13.
- Restored the complete prompt-design data and supporting source programs.
- Added compact pseudonymized full-survey trait inputs and explicit cluster/household grouping; kept original regression point estimates and samples.
- Corrected ensemble adoption denominators for Ethiopia and Nigeria while retaining nitrogen-based metrics and national estimates.
- Updated source-to-result maps, data acquisition routes, reproduction commands, metadata and integrity validation.
- Documented supplied-raster Figure 1 and precision-limited national-statistics/Figure 3 reconstruction without claiming missing historical inputs were recovered.

## 0.1.0 2026-09-06

Original consolidated research archive, retained as the base for this unified release.
