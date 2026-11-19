# African supplementary persona figures

This directory reproduces Figures S1–S5: nitrogen means, errors and upper tails; dispersion across nitrogen and labor outcomes; four-country correlations; percentile ratios; and nitrogen empirical distributions. All five input CSVs use African records and retain the previously checked values.

Run `python draw_supplementary_persona.py` to export PDF, SVG and 600-dpi PNG. NumPy, Matplotlib and Times New Roman are required. The included panel-alignment auditor is called before export. No model calls or downloads occur.

Run `python prepare_source_data.py ../..` to rebuild the five CSVs from the packaged African survey profiles, response archives and retained metrics. Paths are resolved relative to the script and the supplied combined-code root. The 275 matched nitrogen plots and the historical 280-draw distribution-only reference are identified in the captions.

The current application sensitivity figure is maintained separately under `application/figures/SuppFigS1`; consult the combined figure map for its current display number. `SOURCE_MANIFEST.json` links each input to its retained source. Tables are in the combined `merged_tables/` directory.
