# Main figures for the AS-focused merged draft

This directory contains the revised study route (Fig. 1) and the compact four-panel African prompt comparison (Fig. 2). They are specific to the version that preserves the AS application as the main narrative and places the fuller persona diagnostics in the Supplementary Material.

To reproduce both figures, run:

```bash
python draw_main_figures.py
```

The script uses its sibling `data` directory and needs NumPy, Matplotlib and installed Times New Roman fonts. It is independent of the working directory and makes no model calls or network requests. The delivered version was tested with NumPy 2.5.5 and Matplotlib 3.11.2. The included `audit_panel_alignment.py` makes the render-time alignment check self-contained. Exports are editable PDF/SVG and 600-dpi PNG at a width of 180 mm.

Fig. 1 is a coded vector flow diagram based on the archived experimental accounting. Its rounded panels, blue/cream palette, functional line icons and bottom analytical-check strip follow the supplied original style. The separate `draw_study_design.py` module draws Fig. 1; it can also be run alone. The image is 180 × 153 mm. The experimental content and response accounting are unchanged. Its count of 5,670 distinct African primary responses equals 3,360 prompt-test responses + 630 three-country extension responses + 1,470 seven-label responses + 210 East Africa responses. The 840 four-country T1 responses are shared with the seven-country benchmark and are not counted a second time. The 420 initial Tanzania- and Nigeria-label responses are included in the 1,470-record matrix.

Fig. 2 reads `african_configurations.csv` and `african_nitrogen_reference.csv`. All model metrics use the same 275 profiles with finite observed nitrogen rates. The median-prediction MAE reference uses that matched sample. The archived distribution-only KS reference was generated from 400 samples of 280 values fitted to the 275 observed rates. This difference is explicitly stated in the caption. None of the panels treats T1 as a statistically selected optimum.

The five CSV snapshots contain the retained African data. Only `african_configurations.csv` and `african_nitrogen_reference.csv` are needed for the two main figures; the other three support the African supplementary figures. Source mapping and checksums are recorded in `SOURCE_MANIFEST.json`.

Both figures passed strict rendered panel alignment, PDF collision and effective-text-size checks and were visually reviewed panel by panel. The PDF fonts are Times New Roman regular/bold; all effective glyph sizes are at least 6.3 pt. Internal QA reports are generated in `qa`. The static checker assumes sans-serif fonts, so its font-family finding is intentionally overridden for the author's explicit Times New Roman preference. Width was independently verified at 180 mm from the exported PDFs. TIFF was not requested; PNG/PDF/SVG exports are provided.
