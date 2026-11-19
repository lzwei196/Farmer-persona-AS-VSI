# African prompt-design experiment

This folder contains four prompt designs for the original 280 plot profiles from Ethiopia, Malawi, Nigeria and Tanzania. Their 840 T1 responses are shared with the seven-country benchmark and stored once in `../application/data/model_outputs/raw_model_responses.jsonl.gz`. The archived T2–T4 file contains another 2,520 primary responses. The separate 840-record numeric-T3 archive is outside the primary comparison.

## Offline recalculation

From this directory, run:

```bash
python src/audit_african_prompt_designs.py --shared-responses ../application/data/model_outputs/raw_model_responses.jsonl.gz
```

The calculator needs NumPy and uses matched, finite observed outcomes; its reference is `results/analysis/african_prompt_design_metrics_recomputed.json`. It makes no model calls. `src/paper1_metrics.py` reconstructs African nitrogen summaries and the archived reference procedure from the consolidated archives; it needs NumPy and pandas. `src/paper1_multioutcome.py` also reads the consolidated archives to reconstruct continuous and binary African summaries. Both scripts need NumPy and pandas, and preserve the archived reference procedures.

`run_lsms_full.py` and `run_lsms_4country.py` retain African prompt builders and historical collection logic; they call hosted models when explicitly run. Primary T3 uses the anchor-free cognitive prompt in `run_lsms_full.py`; the older pilot builder documents the numeric variant. `prompts/` preserves the corresponding text. No live model calls are needed for offline reproduction.

The source-table CSVs retain their historical source numbers and reporting precision. Current display numbers are recorded in the combined package map. `PERSONA_FILE_PROVENANCE.json` records retained and adapted files with original and current hashes.
