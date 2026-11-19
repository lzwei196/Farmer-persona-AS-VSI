# Matched-input target-blind conventional baseline

The matched baseline uses only the fields visible in the least-context LLM profile:
country, first-level region, manager age, sex and formal education, GPS plot area,
farm size, main crop, plot ownership and intercropping. Target-country outcomes are
excluded from candidate selection and fitting.

| Country | Selected matched model | Matched-input r [95% CI] | Rich-input r [95% CI] | LLM ensemble r [95% CI] | Matched minus LLM [95% CI] |
|---|---|---:|---:|---:|---:|
| Ethiopia | hurdle | -0.072 [-0.259, +0.117] | +0.336 [+0.210, +0.543] | +0.335 [+0.110, +0.562] | -0.407 [-0.650, -0.208] |
| Malawi | hurdle | +0.254 [-0.004, +0.497] | +0.255 [+0.062, +0.454] | +0.312 [+0.092, +0.507] | -0.057 [-0.267, +0.140] |
| Mali | hurdle | +0.164 [-0.083, +0.425] | +0.305 [-0.019, +0.583] | +0.306 [+0.070, +0.528] | -0.142 [-0.380, +0.074] |
| Niger | hurdle | +0.414 [+0.261, +0.756] | +0.271 [+0.181, +0.549] | +0.212 [+0.106, +0.438] | +0.202 [-0.029, +0.503] |
| Nigeria | hurdle | +0.532 [+0.225, +0.738] | +0.316 [+0.116, +0.491] | +0.341 [+0.084, +0.559] | +0.191 [+0.042, +0.301] |
| Tanzania | hurdle | +0.236 [+0.050, +0.407] | +0.043 [-0.154, +0.283] | +0.032 [-0.193, +0.284] | +0.204 [-0.089, +0.492] |
| Uganda | hurdle | +0.112 [-0.087, +0.369] | +0.098 [-0.052, +0.290] | +0.119 [-0.066, +0.342] | -0.007 [-0.308, +0.282] |

The matched-input benchmark removes the information advantage of the richer transfer
model but does not make the learning procedures equivalent: the conventional baseline
is fitted on labeled source-country records, whereas the LLM is used without local
fine-tuning. Confidence intervals are paired, adoption-stratified profile bootstraps.
