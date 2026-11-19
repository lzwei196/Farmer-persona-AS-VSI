# Figure 2 source reconstruction

The current manuscript image is preserved byte for byte at
`reference/accepted_manuscript.png`. It includes the national-statistics and
capped-target layers absent from the original shared repository's script.
The original script that added those layers could not be located.

`Fig2.py` is a portable redraw for this unified code release. It reads
`data/Fig2_plotting_values.csv`; `data/Fig2_input_provenance.csv` records the
source and precision of every numeric cell:

- Survey and LLM point estimates, plus the nitrogen-quantity intervals, are
  retained at the precision available in the original figure CSV.
- LLM adoption and nitrogen-rate intervals, and national-statistics regression
  predictions, use the values reported in current Supplementary Table S8a.
  Adoption values/intervals are reported to 3 decimal places and rate values/
  intervals to 2 decimal places. The current table is copied intact as
  `data/Table_S8a_reported.csv`.
- Capped targets use full-precision aggregate survey results in
  `data/paper2_country_wave_capped_sensitivity_targets.csv`. For this
  sensitivity all seven countries retain otherwise eligible records above
  300 kg N ha−1 before capping their rates. This differs from the primary
  extension-panel target pool, which excludes those records.
- MAE annotations reproduce the reported Table S8b values to the precision
  displayed in the manuscript (LLM/regression adoption 0.16/0.05; nitrogen
  rate 3.70/4.69 kg N ha−1).

The redraw does not fit the national-statistics regression or reproduce its
bootstrap intervals. The full-precision frozen annual external series, its
survey-year mapping and the original new inference implementation were not
present in the supplied archive. The reported input values are not presented
as new estimates from current online data.

The previous, incomplete two-series plot is retained for provenance in
`historical/Fig3_previous_plot.py`, and its exact input CSV is retained as
`data/Fig2_population_calibration_legacy.csv`. It is not called by the current
figure runner. The new redraw preserves the available evidence and reports
its precision limits; it does not promise identical original pixels.
