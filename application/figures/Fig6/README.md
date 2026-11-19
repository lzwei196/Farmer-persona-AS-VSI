# Figure 6: trait associations and explained variation

`Fig6.py` reads the two local figure snapshots under `data/`. These use the
October 17 corrected confidence intervals and held-out explained variation;
all 48 coefficient records are retained. The current accepted figure is
preserved at `reference/accepted_manuscript.png`.

The full-precision analysis outputs are integrated under
`../../data/analysis/traits/`, including `trait_coefficients_full_precision.csv`
and `trait_summary.csv`. The analysis entry point is
`../../src/paper2_trait_models.py`. Its grouping, missing-area fallback and
cross-validation rules are documented with the analysis files; plotting these
snapshots does not itself rerun the survey regressions.

This figure is part of the same Figure 1–8 and S1 source collection. The old
repository's Figure 6 (profile-ranking heatmaps) is now Figure 7.
