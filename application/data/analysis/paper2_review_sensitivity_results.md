# Reviewer-requested sensitivity analyses

## Observed-variable consistency

The frozen sample contains 35 profiles with a positive fertilizer indicator in each
country. No indicator-negative profile has a positive nitrogen rate. Zero or missing
nitrogen rates among indicator-positive profiles are reported rather than recoded.

| country | profiles | fertilizer_indicator_yes | nitrogen_rate_gt_zero | zero_nitrogen_among_indicator_yes | missing_nitrogen_among_indicator_yes | positive_nitrogen_among_indicator_no | missing_nitrogen_among_indicator_no |
|---|---|---|---|---|---|---|---|
| Ethiopia | 70 | 35 | 32 | 0 | 3 | 0 | 0 |
| Malawi | 70 | 35 | 35 | 0 | 0 | 0 | 0 |
| Mali | 70 | 35 | 29 | 6 | 0 | 0 | 0 |
| Niger | 70 | 35 | 35 | 0 | 0 | 0 | 0 |
| Nigeria | 70 | 35 | 33 | 0 | 2 | 0 | 0 |
| Tanzania | 70 | 35 | 35 | 0 | 0 | 0 | 0 |
| Uganda | 70 | 35 | 34 | 1 | 0 | 0 | 0 |

## Calibration diagnostics

| country | profiles | poststrata | minimum_profiles_per_poststratum | maximum_profiles_per_poststratum | eligible_plot_weight_total | kish_effective_profile_n | coefficient_of_variation_of_weights | maximum_normalized_weight | minimum_poststratification_factor | maximum_poststratification_factor |
|---|---|---|---|---|---|---|---|---|---|---|
| Ethiopia | 70 | 8 | 8 | 10 | 6.025e+07 | 30.25 | 1.146 | 0.07288 | 11.07 | 329.6 |
| Malawi | 70 | 8 | 8 | 10 | 6.39e+06 | 20.31 | 1.564 | 0.1297 | 11.98 | 110.3 |
| Mali | 70 | 8 | 8 | 11 | 4.176e+06 | 24.43 | 1.366 | 0.08725 | 4.545 | 1516 |
| Niger | 70 | 7 | 8 | 12 | 4.72e+06 | 12.59 | 2.136 | 0.1779 | 2.181 | 335.5 |
| Nigeria | 70 | 8 | 8 | 11 | 3.814e+07 | 27.53 | 1.242 | 0.09049 | 13.63 | 251.6 |
| Tanzania | 70 | 8 | 8 | 11 | 1.164e+07 | 26.23 | 1.292 | 0.07141 | 3.159 | 279.9 |
| Uganda | 70 | 8 | 2 | 20 | 1.955e+07 | 9.696 | 2.494 | 0.2746 | 1 | 392.7 |

## Tanzania influence and recalibration sensitivity

| method | rate_difference_kg_per_ha | rate_difference_kg_per_ha_lo | rate_difference_kg_per_ha_hi | adoption_difference | adoption_difference_lo | adoption_difference_hi | quantity_difference_kg_per_plot | quantity_difference_kg_per_plot_lo | quantity_difference_kg_per_plot_hi | expanded_difference_tonnes | expanded_difference_tonnes_lo | expanded_difference_tonnes_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| primary_fixed | 19.4 | 14.75 | 23.67 | 0.3595 | 0.2777 | 0.4311 | 19.46 | 11.82 | 28.46 | 2.265e+05 | 1.376e+05 | 3.312e+05 |
| full_strata_fixed | 19.4 | 14.85 | 23.63 | 0.3595 | 0.2813 | 0.4289 | 19.46 | 12.05 | 27.85 | 2.265e+05 | 1.402e+05 | 3.241e+05 |
| full_strata_recalibrated | 19.4 | 14.75 | 23.48 | 0.3595 | 0.2808 | 0.4256 | 19.46 | 12.11 | 28.53 | 2.265e+05 | 1.409e+05 | 3.32e+05 |

The full expanded high-minus-low contrast is 226,464 tonnes N. 
All leave-one-profile-out recalibrated estimates are positive and range from 191,141 to 238,683 tonnes. 
The recalibrated-bootstrap 95% interval is 140,894 to 332,000 tonnes.

## Structured-output semantic audit

| scope | experiment | provider | responses | valid_structured_decision | nonfinite_or_missing_rate | negative_rate | rate_above_300 | adoption_false_with_positive_rate | adoption_true_with_zero_rate | multiple_attempts |
|---|---|---|---|---|---|---|---|---|---|---|
| experiment_provider | benchmark_extension | claude | 210 | 210 | 0 | 0 | 0 | 0 | 0 | 0 |
| experiment_provider | benchmark_extension | codex | 210 | 210 | 0 | 0 | 0 | 0 | 0 | 0 |
| experiment_provider | benchmark_extension | kimi | 210 | 210 | 0 | 0 | 0 | 0 | 0 | 0 |
| experiment_provider | benchmark_original | claude | 280 | 280 | 0 | 0 | 0 | 0 | 0 | 0 |
| experiment_provider | benchmark_original | codex | 280 | 280 | 0 | 0 | 0 | 0 | 0 | 2 |
| experiment_provider | benchmark_original | kimi | 280 | 280 | 0 | 0 | 0 | 0 | 0 | 0 |
| experiment_provider | country_label_ablation | claude | 210 | 210 | 0 | 0 | 0 | 0 | 0 | 1 |
| experiment_provider | country_label_ablation | codex | 210 | 210 | 0 | 0 | 0 | 0 | 0 | 1 |
| experiment_provider | country_label_ablation | kimi | 210 | 210 | 0 | 0 | 0 | 0 | 0 | 0 |
| experiment_provider | country_prior_matrix | claude | 490 | 490 | 0 | 0 | 0 | 0 | 0 | 1 |
| experiment_provider | country_prior_matrix | codex | 490 | 490 | 0 | 0 | 0 | 0 | 0 | 0 |
| experiment_provider | country_prior_matrix | kimi | 490 | 490 | 0 | 0 | 0 | 0 | 0 | 0 |
| provider_total | all | claude | 1190 | 1190 | 0 | 0 | 0 | 0 | 0 | 2 |
| provider_total | all | codex | 1190 | 1190 | 0 | 0 | 0 | 0 | 0 | 3 |
| provider_total | all | kimi | 1190 | 1190 | 0 | 0 | 0 | 0 | 0 | 0 |
| overall | all | all | 3570 | 3570 | 0 | 0 | 0 | 0 | 0 | 5 |

The audit covered 3,570 archived analysis records,
representing 3,150 distinct accepted responses.
4 distinct response conditions required 5 additional
call attempts; retries produced one accepted response per condition and were not repeated
experimental samples. Counts above
300 kg N ha-1 are reported as an output-range diagnostic; this threshold was used for
survey outcome quality control, not to alter archived model outputs.
