# Model rerun guide

Reissuing model calls is optional. The archived responses are already available in
`data/model_outputs/raw_model_responses.jsonl.gz`; analysis reproduction does not require
provider accounts. New calls may incur cost and should be treated as a replication because
hosted models, routing, safety layers, and command-line clients can change.

## Prerequisites

Install and authenticate the Claude, Codex, and/or Kimi command-line clients outside this
repository. Never store credentials in `.env` files committed to Git. Run `--help` on each
experiment script and inspect generated prompts before issuing calls.

## Prepare and run the country-label experiments

The seven-country crossover reuses the Tanzania and Nigeria conditions from the three-arm
ablation, so run the ablation first when creating a new response set.

```bash
python src/paper2_country_label_ablation.py prepare
python src/paper2_country_label_ablation.py show-prompts --profile 140
python src/paper2_country_label_ablation.py run claude --workers 1
python src/paper2_country_label_ablation.py run codex --workers 1
python src/paper2_country_label_ablation.py run kimi --workers 1
python src/paper2_country_label_ablation.py verify

python src/paper2_country_prior_matrix.py prepare
python src/paper2_country_prior_matrix.py run claude --workers 1
python src/paper2_country_prior_matrix.py run codex --workers 1
python src/paper2_country_prior_matrix.py run kimi --workers 1
python src/paper2_country_prior_matrix.py verify
```

Increase worker counts only after checking provider limits and account policies.

## Prepare and run the three-country extension

```bash
python src/paper2_extension_confirmatory.py prepare
python src/paper2_extension_confirmatory.py run claude --workers 1
python src/paper2_extension_confirmatory.py run codex --workers 1
python src/paper2_extension_confirmatory.py run kimi --workers 1
python src/paper2_extension_confirmatory.py verify
```

New outputs are written under the ignored `results/` directory. They do not replace the
archived release tables automatically. Record the date, CLI versions, model-facing identifiers,
prompt hashes, failures, retries, and any provider-side changes before comparing replications.
The archived study retained one accepted response per profile-condition-interface cell. Recovery
attempts made before acceptance are not repeated valid samples. A future repeat-call robustness
study should prespecify the subset, number of accepted repeats and synchronized collection window.
