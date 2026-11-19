# Data dictionary

## Common fields

| Field | Meaning |
|---|---|
| `panel` | Original four-country panel or three-country extension |
| `profile_key` | Public stable key; not an LSMS identifier |
| `country` | Country associated with the frozen survey profile |
| `assigned_country` | Country label displayed to the model in the crossover |
| `provider` | Model command-line provider (`claude`, `codex`, `kimi`, or ensemble) |
| `observed_n` | Survey-derived nitrogen rate, kg N ha-1 |
| `predicted_n` | LLM-recommended nitrogen rate, kg N ha-1 |
| `observed_adoption` | Observed inorganic-fertilizer use indicator |
| `predicted_adoption` | Model-predicted inorganic-fertilizer use indicator |
| `plot_area_ha` | Plot area in hectares |
| `population_analysis_weight` | Post-stratified analysis weight |
| `prompt_sha256` | SHA-256 digest of the exact rendered prompt |

## Pseudonymized grouping fields

`hh_id_merge`, `plot_id_merge`, `strataid`, and `ea_id_merge` are one-way project pseudonyms.
They preserve equality/grouping within this release but are not original LSMS identifiers.

## Raw-response archive

`raw_model_responses.jsonl.gz` contains one JSON object per logical experimental cell. The
`raw_response` field is the provider's unedited text, and `decision` is the parsed structured
decision. Null provenance fields reflect metadata that were not retained in historical runs.

## Additional complete-repository inputs (17 October 2026)

- `processed/trait_survey_analysis_input.csv.gz`: complete eight-trait survey model input. See `TRAIT_INPUT_README.md`; `pw` is the household survey weight; `adoption` is binary; `rate_excl` and `rate_cap` are kg N ha-1. Plot and farm sizes are hectares. Anonymous row and cluster codes do not encode the original survey identifiers.
- `processed/paper2_population_poststrata.csv`: country by binary adoption, female-manager and formal-education cells. `population_cell_n` is the number of eligible plot records; `population_cell_weight_total` sums household survey weights applied to those records. All 55 cells are represented among the 490 profiles.
- `processed/paper2_country_wave_capped_rate_targets.csv`: full-precision capped means on the primary country-specific eligible pools. Original four-country pools retain high-rate records for weighting; extension pools exclude them before weighting.
- `processed/paper2_country_wave_capped_sensitivity_targets.csv`: full-precision capped means on the all-rates sensitivity pools in all seven countries, with rates above 300 retained and clipped at 300 kg N ha-1. This supplies the capped survey target marks in Figure 2 and the Table S8 sensitivity targets. `survey_weighted_mean_capped_n_kg_per_plot` is capped rate times plot area, averaged using `pw`; it is not the weighted mean rate times mean area.
- `analysis/traits/`: corrected full-precision coefficients, bootstrap coefficient draws, cross-validation folds, and sensitivity comparisons. Survey fold `row_id` matches the new anonymous `row_id` in the compact trait input; original raw dataset row indices are not included.
- `manuscript_tables/table_metadata.json`: display table captions, notes and column headings, including units and CI definitions; source Word-document SHA-256 hashes provide traceability without publishing those document files in the data repository.

`processed/trait_survey_analysis_input.csv.gz` also contains `adoption_indicator_missing`: 1 for an originally missing inorganic-fertilizer indicator, 0 otherwise. There are 398 flagged rows; removal gives the 64,519-record S11 complete-case sample. The actual underlying harmonized source files match v2.0, DOI 10.5281/zenodo.15774761 (CC0), as documented by official MD5 and local SHA-256 checksums in `raw/source_data_manifest.json`.
