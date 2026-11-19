# Figure file map

| Current figure | Content | Code | Complete local inputs | Provenance |
|---|---|---|---|---|
| Fig1 | Author-supplied study-design raster | Fig1/export_fig1.py | Fig1/source/Fig1_supplied.png | current supplied raster; previous PPT is historical |
| Fig2 | National targets, predictions and statistics benchmark | Fig2/Fig2.py | Fig2/data/Fig2_plotting_values.csv; Fig2_input_provenance.csv; Table_S8a_reported.csv; capped sensitivity targets; legacy inputs | new portable redraw with explicit mixed precision; original augmented rendering code absent |
| Fig3 | Individual agreement and transfer benchmarks | Fig3/Fig3.py | Fig3/data/Fig3_country_benchmark.csv | revised layout; archived full-precision figure inputs |
| Fig4 | Paired country-label effects | Fig4/Fig4.py | Fig4/data/Fig4a_label_means.csv; Fig4b_variance_components.csv; Fig4c_high_low_contrasts.csv; Fig4d_ranking_change.csv | original figure inputs |
| Fig5 | Provider-by-label levels and individual agreement | Fig5/Fig5.py | Fig5/data/Fig5_provider_label_matrix.csv | original figure inputs |
| Fig6 | Trait associations and explained variation | Fig6/Fig6.py | Fig6/data/Fig6_trait_coefficients_snapshot.csv; Fig6_explained_variation_snapshot.csv | October 17 corrected trait outputs; integrated full-precision inference files |
| Fig7 | Profile ranking and country-label distributions | Fig7/Fig7.py | Fig7/data/Fig7_profile_label_predictions.csv | renumbered from old repository Fig6 |
| Fig8 | Rate and population-expanded label contrasts | Fig8/Fig8.py | Fig8/data/Fig8_profile_population_effects.csv; Fig8_diagnostic_summary.csv | renumbered from old repository Fig7 |
| SuppFigS1 | Omission, weighting and concentration sensitivity | SuppFigS1/SuppFigS1.py | SuppFigS1/data/paper2_influence_leave_one_out.csv; paper2_influence_sensitivity.csv; paper2_label_contributions.csv | revised labels/layout; original numerical inputs retained |

Each figure also includes `reference/accepted_manuscript.png` and its exact caption.
The archived `outputs/` contain available high-resolution exports; fresh renders go to
`rendered/` by default. See README and per-figure provenance notes for the two source gaps
(the current editable Fig1 source and the original augmented Fig2 script).
