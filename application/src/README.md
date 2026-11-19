# Analysis and collection code

Current source modules read canonical inputs under data/ and write regenerated results under reproduced/. The default run_all.py runs all available public-data analyses and all current figures; it does not make hosted-model calls. See the main README and docs/REPOSITORY_MAP.md for per-result inputs and commands.

The core modules cover individual/national benchmarks, paired labels, transfer comparisons, weighting, profile influence and output consistency. Added modules reproduce full-survey and predicted traits with S11 sensitivity, all prompt versions with S9 checks, and all55post-strata with S12 checks. The national-statistics diagnostic is explicitly approximate because historical full-precision inputs were not retained.

The matched transfer model uses country and an administrative-location category (including documented district fallbacks); the rich specification omits those fields and adds other covariates. Both protect target-country outcomes during model selection and fitting.

Source preparation programs reconstruct pseudonymized survey views and study design from the fixed official Plot dataset. Their optional external input is described by data/raw/source_data_manifest.json. Original280profile sampling code was not retained, so frozen profiles remain the canonical panel. Experiment and original prompt-design collection sources are included for future replication with provider CLIs. Historical source programs are kept under historical/ and are not substituted for current target-blind analysis.
