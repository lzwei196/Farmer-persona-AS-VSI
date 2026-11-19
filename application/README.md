# LLM agents know the country, not the farmer: data and code


**11.09 as numbering:** current Fig. 2 is the national-statistics comparison (original Fig. 3); current Fig. 3 is the individual/transfer comparison (original Fig. 2). See `README_FIGURE_NUMBERING_20261109.md` and `figures/SUBMISSION_IMAGE_MAP.json`. All scientific data and figure pixels are unchanged.
Unified data and code package for **Large language model agents know the country, not the farmer: Simulating fertilizer use in data-scarce regions**. This 8 November 2026 package follows the revised manuscript (v5) and includes the October 17 corrections and October 19 audit update. Figure sources, analysis inputs, model responses and code are organized in one repository. Figure 6 uses the same structure as Figures 1–8 and Supplementary Figure S1.

The package covers Figures 1–8, Supplementary Figure S1, Tables 1–3 and Supplementary Tables S1–S12. It includes the fixed 490 study profiles, the country-label experiment and a compact, pseudonymized full-survey trait-analysis input. Original third-party survey files can be obtained from their official archive.

## Start here

Python 3.12 is used. Install dependencies in an environment of your choice:

```bash
python -m pip install -r requirements.txt
python scripts/validate_release.py
python run_all.py --bootstrap 200
```

The 200-draw run checks the analysis pipeline and point estimates. It does not reproduce publication confidence limits. Use the recorded 10,000 primary draws for paper-level intervals:

```bash
python run_all.py --bootstrap 10000
```

Trait-model intervals use the separately specified 500 survey-cluster and 2,000 profile draws. Seed and grouping rules are recorded with their outputs. Analyses write into `reproduced/`; the archived results and figure inputs are retained. Each run reports analyses completed and any source-limited or external-data steps.

To redraw all figures from the included source data:

```bash
python figures/run_all.py
```

Figure 1 is the supplied study-design image. Its current raster source is included; the older editable PowerPoint is identified as historical. Figure 2 can be redrawn from included survey/model quantities and the reported national-regression values; the precision and original-fit limitation are documented in its source notes. Other figure directories contain the matching plotting code and inputs. No exact pixel-for-pixel identity across fonts and operating systems is implied.

## Files

| Directory | Contents |
|---|---|
| `data/profiles/` and `data/processed/` | Frozen study profiles, survey design, target totals and compact full-survey analysis inputs |
| `data/model_outputs/` | Consolidated predictions and the core raw-response archive |
| `data/analysis/` | Archived full-precision results, intervals and sensitivity outputs |
| `data/manuscript_tables/` | Current Tables 1–3 and S1–S12; S8 has two panels |
| `figures/Fig1/` … `figures/Fig8/` | All main figures, source inputs, code/source assets and outputs |
| `figures/SuppFigS1/` | Supplementary figure, source data and plotting code |
| `src/` | Experiment, sampling, analysis and source-data preparation programs |
| `scripts/` | Reproduction entry points, data acquisition, validation and integrity tools |
| `prompts/` and `config/` | Prompt templates, randomization manifests, hashes and collection metadata |
| `docs/` | Reproduction instructions, data dictionary, source coverage and remaining provenance boundaries |

Consult `docs/REPRODUCIBILITY.md` for individual commands and `docs/REPOSITORY_MAP.md` for the complete source-to-result map. `FILE_MANIFEST.csv` and `SHA256SUMS.txt` list the package contents and checksums.

## Data provenance

The source survey is the **LSMS-ISA harmonised dataset v2.0**, available at [Zenodo](https://doi.org/10.5281/zenodo.15774761), licensed CC0 1.0 in the official archive and described by [Bentze and Wollburg (2025)](https://doi.org/10.1038/s41597-025-05639-9). The compact survey input retains the variables needed for the reported trait regressions and uses pseudonymous sampling-group labels. The original `.dta` files are obtained separately to avoid storing large duplicate copies in Git. Source acquisition information and checksums are included.

Core experiments contain 3,570 experiment-tagged records, representing 3,150 distinct accepted responses. The 420 reused Tanzania/Nigeria cells are documented. The 840 original four-country T1 responses were also analysed in a related manuscript (Li et al., 2026, COMPAG-D-26-10597); its other prompt designs are not included here. Generated rationales are computational outputs, not statements collected from actual farmers.

## Reproduction boundaries

The pipeline can recompute the supplied-data analyses and redraw the figures. The original national-statistics benchmark is retained with an explicit boundary: its complete annual full-precision input series, exact survey-year mapping for spanning-year waves and original conditional-bootstrap implementation were not located. The supplied rounded-input audit is labeled approximate and does not certify exact reproduction of those interval endpoints. Current Figure 1's editable engineering file was not located; its supplied final image is archived.

The original 280-profile sampling builder and some early model-call metadata were not retained. Frozen profiles and recorded responses define the analyzed cohorts. New hosted-model calls require the provider CLIs and credentials supplied by the user; backend changes can prevent exact response replication. Offline reproduction never makes model calls.

## Version and citation

Version **0.3.0**, packaged on **2026-11-07**. The associated manuscript has not completed peer review. `CITATION.cff` mirrors its current author list. The duplicated author name in the manuscript, the study-generated data licence and eventual public repository/archive identifiers remain author metadata to resolve before publication; no repository URL or DOI is invented here.

Original code retains its MIT licence. Survey-derived materials retain their source attribution and applicable CC0 1.0 terms. See `DATA_LICENSE.md` for the distinction from model-generated data. This is a local release candidate; preparing it does not publish it to GitHub.

## Obtain the original official source

```bash
python scripts/fetch_source_data.py --list
python scripts/fetch_source_data.py --files Plot_dataset.dta
python scripts/fetch_source_data.py --verify-only --output-dir /path/to/lsms --files Plot_dataset.dta
```

The fixed v2.0 DOI is10.5281/zenodo.15774761. Downloaded files are checked against official MD5 values and the exact study SHA256 records. The default download directory is ignored by Git. This step is optional for the included compact-data analysis workflow.
