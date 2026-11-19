# Current manuscript figures and complete plotting inputs

This directory contains **Figures 1–8 and Supplementary Figure S1** in the
October 17 manuscript order. Figure 6 is integrated with the complete figure
collection. The earlier repository had seven main figures: its old Figure 6
is now Figure 7, and its old Figure 7 is now Figure 8.

Each figure directory contains its plotting code (or supplied raster), all
figure-level input CSVs, archived outputs and the exact image embedded in the
current Word document. `reference/accepted_manuscript.png` is the immutable
manuscript reference; `reference/caption.txt` contains its caption. Word has
reduced the image resolution of several main figures, so the embedded PNG and
the original high-resolution plotting export are not byte-identical.

## Render the complete set

From the repository root:

```bash
python -m pip install -r figures/requirements.txt
python figures/run_all.py
```

Fresh renders are written to `figures/rendered/`, leaving `reference/` and the
archived `outputs/` files intact. To use a different output directory:

```bash
python figures/run_all.py --output-dir /path/to/new/figure-renders
```

No model calls or external data downloads are performed by this figure-only
command. The figure-level tables are plotting inputs, not replacements for the
experiment records and analysis code in the repository's `data/`, `src/` and
`scripts/` directories. Full analysis reconstruction is described in the main
repository README.

## Source and precision notes

- **Figure 1** is the supplied current study-design raster. Its current editable
  source was not found. An earlier PowerPoint is kept under `Fig1/historical/`
  with an explicit warning that it differs. The export script preserves the
  supplied pixels and can place them in a raster PDF.
- **Figure 2** has a new, documented portable redraw. The original script for
  the national-statistics and capping layers was not retained. Archived
  full-precision survey/LLM point values and quantity intervals are combined
  with rate/adoption intervals and national-statistics predictions at the
  precision reported in current Table S8. Capped survey targets are saved at
  full precision from a separate aggregate calculation. Every plotted value
  has a source/precision record in `Fig2/data/Fig2_input_provenance.csv`.
  This redraw does not refit the national-statistics regressions, recover
  missing annual external inputs, or recreate their original bootstrap.
  Its layout is not a pixel-identical copy of the accepted image.
- **Figure 6** uses the October 17 corrected trait intervals and held-out
  explained variation; its full coefficient and summary tables and inference
  code are integrated with the repository analysis files. Its figure CSVs
  remain plotting snapshots, with their source described in `Fig6/data/README.txt`.
- Figures 2, 4, 5, 7, 8 and S1 retain the available complete plotting inputs and
  source code, with Figure 3 and S1 using the revised labels/layouts.

The plotting scripts use local relative paths. Matplotlib may substitute a
serif font if Times New Roman is unavailable, so rendering on another computer
can change typography or export metadata without changing the plotted values.
No proprietary fonts or installed dependency binaries are bundled.

See `FIGURE_FILE_MAP.md` and `SOURCE_MANIFEST.json` for the complete mapping.
