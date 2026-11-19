# Data

This directory includes the data used throughout the manuscript, not only the latest Figure 6 correction.

- `profiles/`: the 280 original and 210 extension profiles. Household and plot grouping IDs use one-way pseudonyms.
- `processed/`: all 490 frozen profiles, recovered survey design and calibration weights, population targets and all 55 post-stratum totals. A compact deidentified input contains the 64,917 complete-trait survey rows, allowing the corrected trait analyses to run offline without the full Stata file.
- `model_outputs/`: parsed principal predictions and a gzip JSON Lines archive with the accepted model responses. The rationales are model-generated and unverified.
- `analysis/`: numeric analysis estimates, bootstrap draws, trait coefficients and fold assignments, sensitivities, and bibliography. Numeric outputs are distinct from displayed table snapshots.
- `manuscript_tables/`: the current Tables 1–3 and Supplementary Tables S1–S12, including both S8 panels. `table_metadata.json` supplies captions, notes, column headings and hashes of the source documents. Display cells are rounded; do not treat them as full-precision inputs.
- `raw/`: verified official download metadata and acquisition instructions for the harmonized LSMS-ISA source files. The source is open under CC0 1.0; approximately 1 GB of uncompressed Stata files is obtained from the fixed official archive rather than duplicated in GitHub.

Units and missing-value definitions are documented in `DATA_DICTIONARY.md`, `processed/TRAIT_INPUT_README.md`, table metadata and figure source-data metadata. The primary excluded-rate pool and the all-rates capped sensitivity pool differ for the extension countries; their target files are named separately.

The principal archive contains 3,570 experiment-tagged analysis rows representing 3,150 distinct accepted responses. The 840 original four-country T1 responses were also analysed in a related manuscript (Li et al., 2026, COMPAG-D-26-10597); that study’s other prompt designs are not part of this package.

The original annual full-precision national-statistics inputs and exact historical year mapping were not retained. The current Table S8 is supplied as an archival display record; a rounded-input reconstruction must not be described as exact reproduction of those historical inputs.
