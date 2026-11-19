# Historical analyses

These original sources are retained because corresponding early outputs remain in the archive. They are not used to calculate the current manuscript results or to select the current conventional comparators.

- `paper2_uncertainty_decomposition.py` used the median metric across the original 3 interfaces × 4 tiers and a target-selected transfer comparator. Its archived outputs are `data/analysis/paper2_uncertainty_decomposition.*` and `data/model_outputs/uncertainty_predictions.csv`.
- `paper2_rival_test.py` and `paper2_rival_test_v2.py` are earlier transfer comparisons. The current target-blind conventional comparisons are implemented by `src/paper2_matched_baseline_analysis.py` and `src/paper2_rich_baseline_analysis.py` instead.
- `paper2_rival_test_confirmatory.py` is the original rich-input confirmatory analysis; its portable current counterpart is `src/paper2_rich_baseline_analysis.py`.
- `paper2_extension_transfer.py` and `paper2_extension_score.py` are early extension checks that preceded the full three-interface confirmatory panel.
- `paper2_label_effect_diagnostics.py` is the original post-stratified label diagnostic source. Current inference is in `src/paper2_country_prior_matrix_analysis.py` and `src/paper2_review_sensitivity_analysis.py`.

The packaging edits listed in `SOURCE_PROVENANCE.json` change path handling, not statistical expressions. These historical programs expect the original per-call `results/full/` tree and `data/lsms/` working layout; they are retained for inspection rather than invoked by `run_all.py`. The public archive provides consolidated responses, frozen profiles, and model predictions under `data/`; current scripts read those files directly. No historical output is presented as a newly verified result.
