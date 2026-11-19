# Paper 2 — seven-country label matrix

Seventy frozen Tanzanian farmer profiles were crossed with all seven country labels while
all non-location profile fields were held fixed. Tanzania and Nigeria reuse the completed
randomized experiment; the other five labels were added prospectively under the frozen npj
design.

## Label-specific provider-ensemble predictions

| assigned label | country-wave prevalence | predicted adoption | mean N kg/ha | mean N kg/plot | farmer r |
|---|---:|---:|---:|---:|---:|
| Ethiopia | 51.5% | 0.700 | 29.03 | 38.69 | 0.021 |
| Malawi | 53.5% | 0.567 | 25.36 | 29.72 | 0.120 |
| Mali | 29.1% | 0.548 | 19.98 | 28.70 | -0.042 |
| Niger | 12.5% | 0.357 | 11.82 | 16.40 | -0.106 |
| Nigeria | 36.1% | 0.676 | 28.56 | 45.93 | -0.038 |
| Tanzania | 11.2% | 0.333 | 11.68 | 15.80 | -0.070 |
| Uganda | 3.7% | 0.186 | 6.76 | 11.44 | -0.132 |

## Exact seven-label ordering tests

| provider | prevalence basis | outcome | slope per prevalence unit | Pearson r (exact p) | Spearman rho (exact p) |
|---|---|---|---:|---:|---:|
| claude | frozen_unweighted | mean_predicted_n | +50.874 | +0.873 (0.0187) | +0.857 (0.0238) |
| claude | frozen_unweighted | mean_predicted_adoption | +1.193 | +0.832 (0.0306) | +0.750 (0.0663) |
| claude | frozen_unweighted | mean_predicted_quantity_kg | +59.116 | +0.764 (0.0560) | +0.750 (0.0663) |
| claude | survey_weighted_sensitivity | mean_predicted_n | +47.077 | +0.874 (0.0192) | +0.857 (0.0238) |
| claude | survey_weighted_sensitivity | mean_predicted_adoption | +1.112 | +0.839 (0.0284) | +0.786 (0.0480) |
| claude | survey_weighted_sensitivity | mean_predicted_quantity_kg | +55.822 | +0.781 (0.0464) | +0.786 (0.0480) |
| codex | frozen_unweighted | mean_predicted_n | +41.444 | +0.874 (0.0163) | +0.821 (0.0341) |
| codex | frozen_unweighted | mean_predicted_adoption | +0.881 | +0.882 (0.0151) | +0.811 (0.0349) |
| codex | frozen_unweighted | mean_predicted_quantity_kg | +63.566 | +0.806 (0.0369) | +0.821 (0.0341) |
| codex | survey_weighted_sensitivity | mean_predicted_n | +39.201 | +0.895 (0.0125) | +0.893 (0.0123) |
| codex | survey_weighted_sensitivity | mean_predicted_adoption | +0.833 | +0.901 (0.0095) | +0.937 (0.0048) |
| codex | survey_weighted_sensitivity | mean_predicted_quantity_kg | +60.596 | +0.831 (0.0278) | +0.893 (0.0123) |
| kimi | frozen_unweighted | mean_predicted_n | +34.582 | +0.970 (0.0014) | +0.929 (0.0067) |
| kimi | frozen_unweighted | mean_predicted_adoption | +0.514 | +0.897 (0.0056) | +0.857 (0.0238) |
| kimi | frozen_unweighted | mean_predicted_quantity_kg | +32.151 | +0.837 (0.0280) | +0.857 (0.0238) |
| kimi | survey_weighted_sensitivity | mean_predicted_n | +32.271 | +0.979 (0.0002) | +1.000 (0.0004) |
| kimi | survey_weighted_sensitivity | mean_predicted_adoption | +0.487 | +0.920 (0.0026) | +0.964 (0.0028) |
| kimi | survey_weighted_sensitivity | mean_predicted_quantity_kg | +29.922 | +0.843 (0.0264) | +0.857 (0.0238) |
| ensemble | frozen_unweighted | mean_predicted_n | +42.300 | +0.934 (0.0077) | +0.893 (0.0123) |
| ensemble | frozen_unweighted | mean_predicted_adoption | +0.863 | +0.893 (0.0119) | +0.893 (0.0123) |
| ensemble | frozen_unweighted | mean_predicted_quantity_kg | +51.611 | +0.803 (0.0401) | +0.857 (0.0238) |
| ensemble | survey_weighted_sensitivity | mean_predicted_n | +39.516 | +0.944 (0.0067) | +0.929 (0.0067) |
| ensemble | survey_weighted_sensitivity | mean_predicted_adoption | +0.811 | +0.908 (0.0101) | +0.929 (0.0067) |
| ensemble | survey_weighted_sensitivity | mean_predicted_quantity_kg | +48.780 | +0.821 (0.0339) | +0.857 (0.0238) |

## Label-versus-profile variance

Marginal variances compare variation across seven label means with variation across
seventy profile means in the same complete crossed matrix.

| provider | outcome | label variance [95% CI] | profile variance [95% CI] | ratio [95% CI] |
|---|---|---:|---:|---:|
| claude | predicted_n | 134.966 [97.650, 182.207] | 164.869 [128.656, 204.967] | 0.819 [0.554, 1.258] |
| claude | predicted_adoption | 0.082 [0.061, 0.107] | 0.091 [0.073, 0.106] | 0.899 [0.596, 1.427] |
| claude | predicted_quantity_kg | 237.554 [90.489, 514.150] | 856.762 [355.441, 1404.747] | 0.277 [0.185, 0.430] |
| codex | predicted_n | 89.265 [60.880, 126.657] | 224.349 [174.507, 271.561] | 0.398 [0.251, 0.649] |
| codex | predicted_adoption | 0.040 [0.025, 0.059] | 0.135 [0.109, 0.157] | 0.295 [0.166, 0.531] |
| codex | predicted_quantity_kg | 247.142 [71.098, 648.348] | 1925.931 [629.112, 3567.553] | 0.128 [0.074, 0.246] |
| kimi | predicted_n | 50.466 [31.404, 78.828] | 342.490 [276.458, 400.122] | 0.147 [0.085, 0.265] |
| kimi | predicted_adoption | 0.013 [0.007, 0.025] | 0.144 [0.116, 0.166] | 0.090 [0.042, 0.197] |
| kimi | predicted_quantity_kg | 58.584 [13.593, 239.776] | 4772.310 [1733.874, 7920.598] | 0.012 [0.003, 0.051] |
| ensemble | predicted_n | 81.406 [58.938, 109.736] | 220.474 [177.380, 260.568] | 0.369 [0.246, 0.567] |
| ensemble | predicted_adoption | 0.037 [0.027, 0.049] | 0.110 [0.089, 0.128] | 0.336 [0.217, 0.544] |
| ensemble | predicted_quantity_kg | 164.061 [58.015, 370.563] | 2158.135 [844.778, 3654.550] | 0.076 [0.046, 0.142] |

## Crossed provider-profile-label decomposition

These descriptive components partition variation across the three evaluated
providers, 70 profiles, and seven labels. The three-way term includes cell residual
variation because there is one response per cell.

| outcome | label share [95% CI] | profile share [95% CI] | label/profile ratio [95% CI] | provider-label share |
|---|---:|---:|---:|---:|
| predicted_n | 0.147 [0.110, 0.196] | 0.457 [0.384, 0.522] | 0.321 [0.214, 0.500] | 0.018 |
| predicted_adoption | 0.127 [0.094, 0.170] | 0.435 [0.355, 0.506] | 0.292 [0.189, 0.472] | 0.027 |
| predicted_quantity_kg | 0.035 [0.024, 0.056] | 0.528 [0.419, 0.677] | 0.066 [0.039, 0.123] | 0.004 |

## Higher-use minus lower-use labels

Higher-use labels: Ethiopia, Malawi, Nigeria. Lower-use labels: Niger, Tanzania, Uganda. Mali is prespecified as the middle label and excluded.

| provider | outcome | mean difference [95% CI] | paired p | Holm p |
|---|---|---:|---:|---:|
| claude | predicted_n | +21.910 [+18.200, +25.681] | 3.93e-16 | 0.0000 |
| codex | predicted_n | +17.719 [+14.248, +21.233] | 1.94e-14 | 0.0000 |
| kimi | predicted_n | +13.067 [+10.076, +16.000] | 1.11e-12 | 0.0000 |
| ensemble | predicted_n | +17.565 [+14.617, +20.457] | 1.59e-17 | NA |
| claude | predicted_adoption | +0.510 [+0.433, +0.586] | 6.08e-19 | 0.0000 |
| codex | predicted_adoption | +0.362 [+0.276, +0.448] | 6.74e-12 | 0.0000 |
| kimi | predicted_adoption | +0.195 [+0.129, +0.262] | 6.27e-07 | 0.0000 |
| ensemble | predicted_adoption | +0.356 [+0.298, +0.414] | 3.73e-18 | NA |
| claude | predicted_quantity_kg | +27.462 [+16.948, +39.535] | 1.2e-05 | 0.0000 |
| codex | predicted_quantity_kg | +28.752 [+15.391, +46.274] | 0.000623 | 0.0012 |
| kimi | predicted_quantity_kg | +14.484 [+1.510, +28.210] | 0.0377 | 0.0377 |
| ensemble | predicted_quantity_kg | +23.566 [+14.416, +34.234] | 1.9e-05 | NA |

## Farmer-ranking stability across labels

The high-minus-low statistic compares farmer correlations under higher-use versus
lower-use labels using the same stratified profile bootstrap. Pairwise Spearman rho
measures how similarly the seven arms rank the 70 identical profiles.

| provider | min–max farmer r | r range [95% CI] | high-minus-low r [95% CI] | mean pairwise ranking rho |
|---|---:|---:|---:|---:|
| claude | -0.096 to +0.194 | 0.290 [0.226, 0.569] | +0.234 [+0.089, +0.356] | 0.501 |
| codex | -0.109 to +0.078 | 0.187 [0.111, 0.467] | +0.081 [-0.101, +0.282] | 0.652 |
| kimi | -0.196 to +0.079 | 0.275 [0.173, 0.500] | +0.060 [-0.035, +0.166] | 0.647 |
| ensemble | -0.132 to +0.120 | 0.252 [0.119, 0.477] | +0.137 [+0.015, +0.266] | 0.781 |

## Population-calibrated agricultural consequence

Household survey weights were recovered from the harmonized plot file and calibrated
within the sampling cells used to construct the adopter-balanced profiles. The table
reports the provider-ensemble higher-use minus lower-use label contrast after that
calibration.

| outcome | weighted difference [95% profile-bootstrap CI] | expanded eligible-plot total difference |
|---|---:|---:|
| predicted_n | +19.403 [+14.828, +23.733] kg N/ha | not additive |
| predicted_adoption | +0.360 [+0.277, +0.431] probability | not additive |
| predicted_quantity_kg | +19.459 [+11.808, +28.580] kg N/plot | 226,464 [137,417, 332,610] tonnes N |

## Prespecified title decision

- Label variance exceeds profile variance by provider: {'claude': False, 'codex': False, 'kimi': False}.
- Provider-ensemble dominance: False.
- The word **dominate** is NOT SUPPORTED under the frozen rule.

## Interpretation boundaries

- The assigned labels are controlled prompt interventions, not samples from the
  assigned countries.
- The primary prevalence values are frozen unweighted country-wave plot estimates,
  not national estimates; an identically filtered household-weighted sensitivity is
  reported separately.
- Expanded quantity totals apply only to the eligible plot population represented by
  the harmonized survey and the recovered household weights; they are not all-sector
  fertilizer sales totals.
- Label sensitivity does not identify proprietary training-data composition.
- Farmer correlations use observed Tanzanian outcomes and assess ranking stability
  under counterfactual labels.
