# Compact survey input for trait models

`trait_survey_analysis_input.csv.gz` contains the 64,917 survey records with all eight model traits and positive finite household weights. It is derived from the seven country-wave samples in the harmonized LSMS-ISA Plot dataset. Source: Bentze (2025), LSMS-ISA harmonised dataset v2.0, DOI 10.5281/zenodo.15774761, CC0 1.0.

The variables retain the values used in the corrected trait analysis. `adoption` uses the study definition (missing indicator responses coded zero, with positive N also required in Ethiopia). `rate_excl` excludes rates above 300 kg N/ha; `rate_cap` caps them at 300. The country-specific exclusions for population weighting are separate and do not alter this trait sample.

`row_id` is a new consecutive anonymous row label. `ea_id_merge` and `hh_id_merge` are anonymous grouping codes, retaining missing-EA flags and original group ordering for deterministic cross-validation. Original survey IDs, raw dataset row indices, detailed crop categories, and geographic fields have been removed. `main_crop` preserves only MAIZE versus OTHER, as used in the model. These codes allow the same known-EA and household-fallback resampling. They cannot recover unknown enumeration areas.

`paper2_population_poststrata.csv` contains the 55 full-survey post-stratum sizes and household-weight totals needed to rebuild profile post-stratification weights. `paper2_country_wave_capped_rate_targets.csv` adds full-precision capped N-rate targets. Existing excluded-rate and quantity targets remain in `paper2_country_wave_population_targets.csv`.

`paper2_country_wave_capped_sensitivity_targets.csv` instead retains high-rate observations in all seven eligible country-wave pools and clips them at 300 kg N/ha, matching the capped sensitivity targets in Figure 2 and Table S8. It is distinct from the primary-pool capped target file for the extension countries.

`adoption_indicator_missing` flags the 398 records whose original inorganic-fertilizer indicator was missing before the study adoption coding rule. Excluding those rows yields the 64,519-record complete-case sensitivity sample (Supplementary Table S10). The flag does not change the primary adoption values.
