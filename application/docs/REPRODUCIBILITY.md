# Reproduction guide

## Canonical inputs

The fixed 490 profiles, consolidated accepted model responses, compact 64917-row survey view, 55 post-stratum totals and aggregate targets are the canonical inputs. Current display tables are snapshots; they do not replace analytical inputs. Consult `data/README.md` and each figure's source notes for units and transformations.

## Unified offline run

```bash
python -m pip install -r requirements.txt
python scripts/validate_release.py
python run_all.py --bootstrap 200
```

The 200-draw run checks data flow and point estimates. Use 10000 primary bootstrap draws for paper-level confidence limits. Trait intervals use their separately recorded 500 survey and 2000 profile draws with seed 20260827. The runner reports which calculations completed and which historical-source limits remain. It writes analysis results to `reproduced/`, preserving the archived reference results.

```bash
python run_all.py --bootstrap 10000
python figures/run_all.py
```

## Original survey acquisition and preparation

The exact source is the open CC0 LSMS-ISA harmonised dataset v2.0, https://doi.org/10.5281/zenodo.15774761. All four local study files match the official file sizes and MD5 checksums. The full source is large; the supplied compact input supports the reported trait models without downloading it.

```bash
python scripts/fetch_source_data.py --list
python scripts/fetch_source_data.py --files Plot_dataset.dta
python scripts/fetch_source_data.py --verify-only --output-dir /path/to/lsms --files Plot_dataset.dta
```

To reconstruct source-derived inputs as well as run the analyses, provide the official plot file:

```bash
python run_all.py --bootstrap 200 --plot-data /path/to/Plot_dataset.dta --rebuild-survey-design
```

`src/prepare_survey_analysis_inputs.py` prepares pseudonymized survey views. `src/paper2_recover_survey_design.py` matches the frozen measured fields back to source records and rebuilds weights and targets. Each program provides `--help`. Generated source reconstructions stay in ignored output directories. Seven verified season metadata labels were corrected in this release; their previous labels are retained in `data/provenance/season_metadata_corrections.csv`. They do not affect any analysis input value or result.

## Figure sources

Figure numbering follows the current manuscript: Figure 6 shows trait associations, Figure 7 shows observed and predicted profiles, and Figure 8 shows expanded contributions. Figure 1 exports the supplied current raster; the older PowerPoint is explicitly historical. Figure 2 has a documented redraw with source precision notes and the accepted image retained separately. Other figures contain their current inputs and plotting code. `figures/run_all.py` draws the complete set without making model calls.

## New model calls and historical programs

Collection programs and prompt templates are included for future replication. New hosted-model calls require provider CLIs and external credentials. Immutable backend identifiers and some original per-call metadata were not retained, so new calls need not match archived responses. The default offline workflow never makes these calls. Older alternative analyses are retained under `src/historical/` and are not used to generate the current manuscript results.

## Integrity and numerical comparison

`FILE_MANIFEST.csv` and `SHA256SUMS.txt` list every distributed file and digest. Regenerate them after intentional edits. Validation checks current figure/table coverage, profile and response counts, prompt hash links, pseudonyms, source syntax and checksums.

Three matched-model correlation columns showed a maximum numerical difference of 0.0000073 from the archive on the tested environment. Their comparison allows at most 0.0001 absolute difference and separately requires the reported three-decimal values to remain identical. Other point estimates retain strict comparisons. This does not replace archived results with new values.

`REPRODUCTION_LIMITS.md` records the historical inputs that remain unavailable, including exact national-statistics interval inputs. A successful package test does not remove those limits.
