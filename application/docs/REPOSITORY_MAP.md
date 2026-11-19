# Repository and source map

The current release covers nine figures and sixteen numbered tables. Table S8 has two panels, giving seventeen table CSVs. Paths below are relative to the repository root.

## Analyses

| Result | Code | Scope |
|---|---|---|
| Core individual validation | `src/paper2_extension_confirmatory_analysis.py` | Ensemble adoption uses all 70 profiles per country; nitrogen-rate metrics use valid pairs. |
| Source-country transfer benchmarks | `src/paper2_rich_baseline_analysis.py`, `src/paper2_matched_baseline_analysis.py` | Target-country outcomes are excluded from selection and fitting. |
| Country-label contrasts and ordering | `src/paper2_country_prior_matrix_analysis.py` | Whole-profile pairing is retained; exact ordering tests enumerate 5040 assignments. |
| Three-arm label sensitivity | `src/paper2_country_label_ablation_analysis.py` | Tanzania, East Africa and Nigeria conditions use the same Tanzanian profiles. |
| National weighting and nitrogen quantities | `src/paper2_population_consequence.py` | Observed quantities inherit rate quality control; expansion refers to eligible records. |
| Poststratum reconstruction TableS11 | `src/paper2_weight_validation.py` | All 55 joint cells and all 490 calibrated profile weights are reconstructed. |
| Influence recalibration and semantic audits | `src/paper2_review_sensitivity_analysis.py` | Includes leave-one-out checks, recalibrated bootstrap and output consistency. |
| Survey and generated traits TableS9 | `src/paper2_trait_models.py` | 64917 survey trait records and 488 complete ensemble profiles; 500/2000 bootstrap draws. |
| Missing-adoption sensitivity TableS10 | `src/paper2_trait_models.py` | Excludes 398 missing responses, retaining 64519 records; point estimates only. |
| National-statistics TableS8 | `src/paper2_national_statistics_audit.py` | Exact annual series, spanning-year mapping and original bootstrap were not retained. |
| Original survey view preparation | `scripts/fetch_source_data.py`, `src/prepare_survey_analysis_inputs.py`, `src/paper2_recover_survey_design.py` | Official v2.0 DOI 15774761, CC0; all four source MD5 values match. |
| Historical alternative analyses | `src/historical/` | Historical sources are retained for provenance and excluded from the current pipeline. |

The complete input list and reproduction status are in `ANALYSIS_COVERAGE.csv`.

## Tables

| Table | Current CSV | Source inputs |
|---|---|---|
| 1 | `data/manuscript_tables/Table_1.csv` | `data/analysis/paper2_matched_baseline_results.csv`, `data/analysis/paper2_population_consequence.csv`, `data/processed/paper2_country_wave_prevalence.csv` |
| 2 | `data/manuscript_tables/Table_2.csv` | `data/analysis/paper2_country_prior_matrix_results.json`, `data/model_outputs/country_prior_matrix_predictions.csv`, `data/processed/profile_survey_design.csv` |
| 3 | `data/manuscript_tables/Table_3.csv` | `data/analysis/paper2_label_contributions.csv`, `data/model_outputs/country_prior_matrix_predictions.csv` |
| S1 | `data/manuscript_tables/Supplementary_Table_S1.csv` | `config/experiment_metadata.json`, `config/manifests/`, `data/processed/frozen_profiles.csv` |
| S2 | `data/manuscript_tables/Supplementary_Table_S2.csv` | `data/processed/frozen_profiles.csv` |
| S3 | `data/manuscript_tables/Supplementary_Table_S3.csv` | `data/model_outputs/raw_model_responses.jsonl.gz`, `data/analysis/paper2_semantic_audit.csv` |
| S4 | `data/manuscript_tables/Supplementary_Table_S4.csv` | `data/model_outputs/raw_model_responses.jsonl.gz`, `config/manifests/`, `config/experiment_metadata.json` |
| S5 | `data/manuscript_tables/Supplementary_Table_S5.csv` | `data/analysis/paper2_extension_confirmatory_metrics.csv`, `data/model_outputs/benchmark_predictions.csv`, `data/analysis/adoption_bootstrap/` |
| S6 | `data/manuscript_tables/Supplementary_Table_S6.csv` | `src/paper2_matched_baseline_analysis.py`, `data/analysis/paper2_matched_baseline_results.json` |
| S7 | `data/manuscript_tables/Supplementary_Table_S7.csv` | `data/analysis/paper2_matched_baseline_results.csv`, `data/analysis/paper2_matched_baseline_predictions.csv` |
| S8a | `data/manuscript_tables/Supplementary_Table_S8a.csv` | `data/manuscript_tables/Supplementary_Table_S8a.csv`, `data/processed/paper2_country_wave_population_targets.csv`, `data/processed/paper2_country_wave_capped_sensitivity_targets.csv` |
| S8b | `data/manuscript_tables/Supplementary_Table_S8b.csv` | `data/manuscript_tables/Supplementary_Table_S8b.csv` |
| S9 | `data/manuscript_tables/Supplementary_Table_S9.csv` | `data/processed/trait_survey_analysis_input.csv.gz`, `data/analysis/traits/`, `data/model_outputs/benchmark_predictions.csv`, `data/processed/frozen_profiles.csv` |
| S10 | `data/manuscript_tables/Supplementary_Table_S10.csv` | `data/processed/trait_survey_analysis_input.csv.gz` |
| S11 | `data/manuscript_tables/Supplementary_Table_S11.csv` | `data/processed/profile_survey_design.csv`, `data/processed/paper2_population_poststrata.csv` |
| S12 | `data/manuscript_tables/Supplementary_Table_S12.csv` | `data/model_outputs/country_label_ablation_predictions.csv`, `data/analysis/paper2_country_label_ablation_results.json` |

Table captions, units and source-document hashes are in `data/manuscript_tables/`. Display snapshots are labeled separately from analytical inputs.

## Figures

All main and supplementary figures are under `figures/`. `figures/FIGURE_FILE_MAP.md` lists the code and inputs for each figure. `figures/SOURCE_MANIFEST.json` records their checksums. Every figure retains its accepted-manuscript reference image and caption alongside the available plotting sources and exports.

## Original data and integrity

`python scripts/fetch_source_data.py --list` shows the fixed official source version, URLs, sizes and checksums. The compact survey input supports offline analysis; the original survey files are optional for reconstructing that input from source.

`FILE_MANIFEST.csv` and `SHA256SUMS.txt` cover every distributed file. Data and figure subtrees also have manifests. `scripts/validate_release.py` checks coverage, counts, source links, syntax and integrity.
