# Paper 2 — clean three-provider country extension

The prospective extension uses the exact T1 template without an added system prompt and
runs every provider in an empty working directory. Original four-country T1 results are
shown as discovery evidence; they were collected earlier and may represent older provider
backends. All samples are adopter-balanced, so population calibration is not estimated from
these rows.

## Provider-ensemble farmer-level results

Adoption AUC and Brier scores use all 70 profiles per country. The sample-size column counts valid observed nitrogen rates; rate and quantity metrics use that smaller sample where rates are missing. Ensemble adoption values for Ethiopia and Nigeria include the five previously omitted profiles, as corrected on 17 October 2026.

| country | panel | valid observed-N n | area-filtered inorganic-use prevalence | overall r [95% CI] | adoption AUC [95% CI] | Brier [95% CI] | positive-N rho [95% CI] |
|---|---|---:|---:|---:|---:|---:|---:|
| Ethiopia | original_discovery | 67 | 51.5% | 0.335 [0.113, 0.563] | 0.648 [0.524, 0.765] | 0.313 [0.224, 0.408] | 0.254 [-0.141, 0.597] |
| Malawi | original_discovery | 70 | 53.5% | 0.312 [0.093, 0.513] | 0.670 [0.551, 0.787] | 0.314 [0.214, 0.414] | 0.280 [-0.083, 0.581] |
| Nigeria | original_discovery | 68 | 36.1% | 0.341 [0.083, 0.563] | 0.691 [0.569, 0.804] | 0.289 [0.208, 0.376] | 0.100 [-0.268, 0.453] |
| Tanzania | original_discovery | 70 | 11.2% | 0.032 [-0.194, 0.285] | 0.528 [0.407, 0.648] | 0.432 [0.332, 0.532] | 0.005 [-0.336, 0.352] |
| Mali | prospective_extension_v2 | 70 | 29.1% | 0.306 [0.067, 0.526] | 0.780 [0.669, 0.876] | 0.222 [0.143, 0.311] | -0.015 [-0.429, 0.425] |
| Niger | prospective_extension_v2 | 70 | 12.5% | 0.212 [0.103, 0.440] | 0.595 [0.476, 0.710] | 0.343 [0.284, 0.402] | 0.599 [0.350, 0.777] |
| Uganda | prospective_extension_v2 | 70 | 3.7% | 0.119 [-0.066, 0.349] | 0.673 [0.588, 0.757] | 0.379 [0.322, 0.432] | -0.133 [-0.458, 0.211] |

## Provider-specific overall r

| country | Claude | Codex | Kimi | ensemble |
|---|---:|---:|---:|---:|
| Ethiopia | 0.268 [0.064, 0.551] | 0.292 [0.089, 0.499] | 0.359 [0.092, 0.561] | 0.335 [0.113, 0.563] |
| Malawi | 0.266 [0.061, 0.466] | 0.245 [0.019, 0.451] | 0.347 [0.118, 0.547] | 0.312 [0.093, 0.513] |
| Nigeria | 0.412 [0.169, 0.617] | 0.240 [0.014, 0.442] | 0.281 [0.000, 0.520] | 0.341 [0.083, 0.563] |
| Tanzania | 0.032 [-0.192, 0.279] | 0.010 [-0.205, 0.250] | 0.048 [-0.168, 0.296] | 0.032 [-0.194, 0.285] |
| Mali | 0.323 [0.072, 0.535] | 0.277 [0.050, 0.495] | 0.273 [0.039, 0.502] | 0.306 [0.067, 0.526] |
| Niger | 0.095 [-0.009, 0.312] | 0.046 [-0.009, 0.290] | 0.258 [0.064, 0.422] | 0.212 [0.103, 0.440] |
| Uganda | NA | 0.023 [-0.082, 0.175] | 0.150 [-0.082, 0.409] | 0.119 [-0.066, 0.349] |

## Household-cluster sensitivity for the provider ensemble

The primary intervals resample profiles within adoption strata. These sensitivity
intervals keep repeated plots from the same sampled household together.

| country | r | household-cluster 95% CI |
|---|---:|---:|
| Ethiopia | +0.335 | [0.106, 0.556] |
| Malawi | +0.312 | [0.091, 0.514] |
| Nigeria | +0.341 | [0.089, 0.563] |
| Tanzania | +0.032 | [-0.195, 0.282] |
| Mali | +0.306 | [0.065, 0.531] |
| Niger | +0.212 | [0.087, 0.435] |
| Uganda | +0.119 | [-0.068, 0.348] |

## Descriptive prevalence–fidelity ordering

The country label is the independent unit (n=7); repeated profiles do not increase
the country-level sample size.

- Frozen unweighted prevalence: Pearson r = +0.819, exact p = 0.0286; Spearman rho = +0.821, exact p = 0.0341.
- Survey-weighted sensitivity: Pearson r = +0.815, exact p = 0.0300; Spearman rho = +0.786, exact p = 0.0480.

## Completeness

```
provider  panel                   
claude    original_discovery          280
          prospective_extension_v2    210
codex     original_discovery          280
          prospective_extension_v2    210
ensemble  original_discovery          280
          prospective_extension_v2    210
kimi      original_discovery          280
          prospective_extension_v2    210
```

## Boundaries

- The frozen country-wave prevalence is an unweighted, area-filtered survey estimate,
  not a national estimate; survey-weighted ordering is reported as a sensitivity.
- Adoption AUROC and Brier use the survey inorganic-fertilizer indicator used for
  sampling; positive-intensity metrics use reported nitrogen greater than zero.
- Discovery and extension calls may use different provider backend versions.
- The samples are balanced on observed adoption; mean and zero-mass errors in this
  report describe the experimental samples, not country populations.
- Uganda may be intrinsically difficult for both LLMs and conventional transfer
  models; an agent failure there is not mechanism evidence by itself.
