# Farmer-persona-AS-VSI

**Constructing large language model farmer personas: information layers, country context and fertilizer decisions**

Qi Wei, Yirong Zhang, Junzeng Xu, Ruiqi Wu, Huijun Qi, Man Liu, Wenbo Xue, Yuchen Liu, Zhiming Qi and Ziwei Li.


Repository: https://github.com/lzwei196/Farmer-persona-AS-VSI

The study combines a four-country assessment of farmer-persona prompts with the seven-country fertilizer benchmark and paired country-label experiment. The archived four-country T1 responses are shared between the two components and counted once. Current manuscript figure and table numbers are mapped in `DISPLAY_NUMBERING.json` and `figures/FIGURE_MAP.md`; the historical application release retains its original local numbering.

## Contents

- `persona/`: 280-profile African survey panel, T1–T4 prompt documentation, archived T2–T4 decisions, full-precision metrics and an offline calculator.
- `application/`: 490 seven-country profiles, model responses, compact survey inputs, survey weights, primary country-label analyses, benchmarks and all original application figure code.
- `figures/`: current main-figure and African supplementary plotting scripts, five shared plotting CSVs, source manifests and exports.
- `merged_tables/`: current displayed Word tables as CSV, with provenance.
- Official survey sources: download the four harmonized files using `application/scripts/fetch_source_data.py`; see `application/data/raw/README.md`. The large local survey ZIP is not duplicated in Git.

## Response accounting

The primary African analyses contain 5,670 distinct accepted response records: 3,360 from T1–T4 tests on 280 profiles, 630 from the three-country T1 extension, 1,470 from the seven-country-label matrix and 210 from the regional-label experiment. The original 840 T1 calls are shared with the seven-country benchmark and counted once. The 420 initial country-label responses are included in the 1,470-record matrix. These are model responses, not 5,670 independent farmers.

The application archive contains 3,570 experiment-tagged rows representing 3,150 distinct responses because 420 label calls appear under both experimental tags. The separate numeric-T3 archive contains 840 historical responses outside the primary T1–T4 comparison.

## Offline checks

From this directory, use:

```bash
python application/scripts/validate_release.py
python persona/src/audit_african_prompt_designs.py --shared-responses application/data/model_outputs/raw_model_responses.jsonl.gz
python figures/persona_supplement/prepare_source_data.py .
python figures/persona_supplement/draw_supplementary_persona.py
python figures/main_integration/draw_main_figures.py
```

Install the dependencies in `application/requirements.txt` and the NumPy/Matplotlib plotting dependencies; Times New Roman is required for identical figure typography. These commands do not call a hosted model. The five plotting CSVs preserve all source precision and use common valid pairs within each outcome. Nitrogen comparisons use 275 plots. The archived distribution-only reference retains 400 samples of 280 draws fitted to the 275 observations, as described in the figure caption.

## Reproduction boundaries

The application release preserves national-statistics regression results and a rounded-input diagnostic. The annual full-precision external fertilizer series, exact spanning-year mapping and original conditional-bootstrap implementation remain unavailable; see `application/docs/REPRODUCTION_LIMITS.md`. This limitation has not been removed by repackaging. The survey source is the fixed Zenodo v2.0 record, DOI10.5281/zenodo.15774761.

The table CSV manifest records the source Word documents from the prepared AS-VSI package; these historical source documents are not distributed here. The latest submission manuscript supplied on 19 November 2026 determines the repository title and authors. This import does not certify that every table or figure matches later manuscript edits. See `IMPORT_PROVENANCE.md`.

## Citation and licensing

Use the root `CITATION.cff` for the combined manuscript. Citation metadata inside `application/` belongs to the historical component release. Original code retains its MIT licence; survey and study-generated data terms are described in `application/DATA_LICENSE.md`.
