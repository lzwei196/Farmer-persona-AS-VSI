# Paper 2 — target-blind conventional rival

For each target country, the hurdle-versus-random-forest choice uses only transfer
performance among the other six countries. The target country's outcomes are untouched
until the selected model is refit and evaluated once.

| target | selected model | source-validation r: hurdle / RF | conventional r [95% CI] | agent ensemble r [95% CI] | r gap [95% CI] |
|---|---|---:|---:|---:|---:|
| Ethiopia | random_forest | +0.236 / +0.259 | +0.336 [+0.210, +0.543] | +0.335 [+0.110, +0.562] | +0.001 [-0.195, +0.283] |
| Malawi | random_forest | +0.160 / +0.245 | +0.255 [+0.062, +0.454] | +0.312 [+0.092, +0.507] | -0.057 [-0.241, +0.149] |
| Mali | hurdle | +0.275 / +0.222 | +0.305 [-0.019, +0.583] | +0.306 [+0.070, +0.528] | -0.002 [-0.326, +0.266] |
| Niger | hurdle | +0.210 / +0.200 | +0.271 [+0.181, +0.549] | +0.212 [+0.106, +0.438] | +0.059 [-0.110, +0.287] |
| Nigeria | random_forest | +0.225 / +0.243 | +0.316 [+0.116, +0.491] | +0.341 [+0.084, +0.559] | -0.025 [-0.239, +0.193] |
| Tanzania | random_forest | +0.232 / +0.291 | +0.043 [-0.154, +0.283] | +0.032 [-0.193, +0.284] | +0.011 [-0.250, +0.330] |
| Uganda | random_forest | +0.276 / +0.302 | +0.098 [-0.052, +0.290] | +0.119 [-0.066, +0.342] | -0.022 [-0.217, +0.182] |

## Post-result descriptive country diagnostics

These diagnostics were added after the seven target-country results were seen and
are therefore descriptive, not confirmatory.

- Agent and conventional skill across countries: Pearson r = +0.955; Spearman rho = +0.857.
- frozen unweighted prevalence: agent r = +0.819 (exact p = 0.0286); conventional r = +0.700 (exact p = 0.0879).
- survey-weighted prevalence: agent r = +0.815 (exact p = 0.0300); conventional r = +0.703 (exact p = 0.0849).

## Interpretation boundary

This test asks whether observable farmer covariates contain transferable signal.
It does not identify model training-data composition. A conventional failure is weak
evidence because source-country transfer can itself fail under distribution shift.
