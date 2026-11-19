"""Complete a seven-country label matrix on the frozen Tanzanian profiles.

The completed Tanzania and Nigeria country-labelled responses are reused from the
v1 country-label experiment. This runner adds Ethiopia, Malawi, Mali, Niger, and
Uganda while holding every farmer/profile field byte-identical.

Commands
--------
    /usr/bin/python3 src/paper2_country_prior_matrix.py prepare
    /usr/bin/python3 src/paper2_country_prior_matrix.py run claude --workers 4
    /usr/bin/python3 src/paper2_country_prior_matrix.py run codex --workers 4
    /usr/bin/python3 src/paper2_country_prior_matrix.py run kimi --workers 4
    /usr/bin/python3 src/paper2_country_prior_matrix.py verify
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT.parent))

try:
    import lsms_utils as U  # noqa: E402
except ModuleNotFoundError:  # standalone reproducibility bundle
    import lsms_utils as U  # type: ignore[no-redef]  # noqa: E402
from paper2_country_label_ablation import (  # noqa: E402
    call_provider,
    cli_version,
    sha256_text,
)

SAMPLE = ROOT / "data" / "profiles" / "lsms_4country_full.csv"
TEMPLATE = ROOT / "prompts" / "main" / "paper2_country_label_ablation_template.txt"
PREVALENCE = ROOT / "data" / "processed" / "paper2_country_wave_prevalence.csv"
PRIOR_RESULTS = ROOT / "results" / "paper2_country_label_ablation"
RESULTS = ROOT / "results" / "paper2_country_prior_matrix"
MANIFEST = RESULTS / "design_manifest.csv"
METADATA = RESULTS / "_metadata.json"
SEED = 20260827
DESIGN_VERSION = "paper2-seven-country-prior-matrix-v1"
PROVIDERS = ("claude", "codex", "kimi")
LABELS = ("Ethiopia", "Malawi", "Mali", "Niger", "Nigeria", "Tanzania", "Uganda")
REUSE = {"Tanzania": "true_country", "Nigeria": "swapped_country"}
NEW_LABELS = tuple(label for label in LABELS if label not in REUSE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_profiles() -> pd.DataFrame:
    sample = pd.read_csv(SAMPLE)
    sample["farmer_idx"] = sample.index.astype(int)
    profiles = sample[sample["country"] == "Tanzania"].copy()
    if len(profiles) != 70:
        raise RuntimeError(f"Expected 70 Tanzania profiles, found {len(profiles)}")
    if profiles["nitrogen_kg_per_ha"].isna().any():
        raise RuntimeError("Missing observed N-rate in Tanzania matrix profiles")
    return profiles


def render_prompt(row: pd.Series, label: str) -> str:
    fields = U.row_to_identity_fields(row)
    fields["location_line"] = f"- Country: {label}"
    prompt = TEMPLATE.read_text(encoding="utf-8").format(**fields)
    region = str(row.get("region_clean", ""))
    if region and region.lower() != "nan" and region in prompt:
        raise RuntimeError(f"Admin-region leakage for farmer {row.name}: {region}")
    country_mentions = [
        candidate for candidate in LABELS
        if re.search(rf"(?<![A-Za-z]){re.escape(candidate)}(?![A-Za-z])", prompt)
    ]
    if country_mentions != [label]:
        raise RuntimeError(f"Country-label audit failed for {label}: {country_mentions}")
    return prompt


def existing_path(provider: str, label: str, farmer_idx: int) -> Path | None:
    arm = REUSE.get(label)
    if arm is None:
        return None
    return PRIOR_RESULTS / provider / arm / f"Tanzania_{farmer_idx}.json"


def new_path(provider: str, label: str, farmer_idx: int) -> Path:
    return RESULTS / provider / label / f"Tanzania_{farmer_idx}.json"


def valid_decision(decision: object) -> bool:
    if not isinstance(decision, dict):
        return False
    nitrogen = decision.get("nitrogen_kg_per_ha")
    adoption = decision.get("inorganic_fertilizer")
    return (isinstance(nitrogen, (int, float)) and np.isfinite(nitrogen)
            and isinstance(adoption, bool))


def completed(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return valid_decision(payload.get("decision"))


def build_manifest() -> pd.DataFrame:
    profiles = load_profiles().set_index("farmer_idx")
    rng = np.random.default_rng(SEED)
    profile_order = rng.permutation(profiles.index.to_numpy(int))
    records = []
    run_order = 0
    for block_order, farmer_idx in enumerate(profile_order):
        label_order = rng.permutation(LABELS)
        for within_block_order, label in enumerate(label_order):
            prompt = render_prompt(profiles.loc[farmer_idx], str(label))
            records.append({
                "run_order": run_order,
                "block_order": block_order,
                "within_block_order": within_block_order,
                "farmer_idx": int(farmer_idx),
                "actual_country": "Tanzania",
                "assigned_country": str(label),
                "response_source": "reuse_v1" if label in REUSE else "prospective_v1",
                "prompt_sha256": sha256_text(prompt),
            })
            run_order += 1
    manifest = pd.DataFrame(records)
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: pd.DataFrame) -> None:
    if len(manifest) != 490:
        raise RuntimeError(f"Expected 490 profile-label cells, found {len(manifest)}")
    if manifest.duplicated(["farmer_idx", "assigned_country"]).any():
        raise RuntimeError("Duplicate profile-label cell")
    label_counts = manifest["assigned_country"].value_counts().to_dict()
    if label_counts != {label: 70 for label in LABELS}:
        raise RuntimeError(f"Unexpected label counts: {label_counts}")
    per_profile = manifest.groupby("farmer_idx")["assigned_country"].nunique()
    if not (per_profile == len(LABELS)).all():
        raise RuntimeError("Every profile must receive all seven labels")


def prepare(write: bool = True) -> pd.DataFrame:
    manifest = build_manifest()
    profiles = load_profiles().set_index("farmer_idx")
    for item in manifest[manifest["response_source"] == "reuse_v1"].itertuples(index=False):
        for provider in PROVIDERS:
            path = existing_path(provider, item.assigned_country, item.farmer_idx)
            if not completed(path):
                # A clean public checkout has archived responses in JSONL form.
                # The files appear here after rerunning the three-arm ablation.
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            prior_hash = payload.get("prompt_sha256")
            if prior_hash and prior_hash != item.prompt_sha256:
                raise RuntimeError(f"Reusable prompt hash mismatch: {path}")
            current_hash = sha256_text(render_prompt(profiles.loc[item.farmer_idx],
                                                     item.assigned_country))
            if current_hash != item.prompt_sha256:
                raise RuntimeError("Prompt changed during reuse audit")
    if not write:
        return manifest
    RESULTS.mkdir(parents=True, exist_ok=True)
    if MANIFEST.exists():
        existing = pd.read_csv(MANIFEST)
        validate_manifest(existing)
        if not existing[list(manifest.columns)].equals(manifest):
            raise RuntimeError("Existing matrix manifest differs; refusing overwrite")
    else:
        manifest.to_csv(MANIFEST, index=False)
    metadata = {
        "design_version": DESIGN_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "experimental_unit": "frozen Tanzania farmer profile",
        "n_profiles": 70,
        "assigned_country_labels": list(LABELS),
        "providers": list(PROVIDERS),
        "complete_cells_per_provider": len(manifest),
        "reused_cells_per_provider": int((manifest["response_source"] == "reuse_v1").sum()),
        "new_cells_per_provider": int((manifest["response_source"] == "prospective_v1").sum()),
        "planned_new_calls": int((manifest["response_source"] == "prospective_v1").sum()
                                 * len(PROVIDERS)),
        "sample": str(SAMPLE),
        "sample_sha256": sha256_file(SAMPLE),
        "template": str(TEMPLATE),
        "template_sha256": sha256_file(TEMPLATE),
        "country_wave_prevalence": str(PREVALENCE),
        "country_wave_prevalence_sha256": sha256_file(PREVALENCE),
        "prior_results": str(PRIOR_RESULTS),
        "provider_cli_versions_at_prepare": {p: cli_version(p) for p in PROVIDERS},
    }
    if not METADATA.exists():
        METADATA.write_text(json.dumps(metadata, indent=2) + "\n")
    return manifest


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    temporary.replace(path)


def run_one(provider: str, item, row: pd.Series) -> tuple[str, bool, str]:
    label = item.assigned_country
    path = new_path(provider, label, item.farmer_idx)
    prompt = render_prompt(row, label)
    if sha256_text(prompt) != item.prompt_sha256:
        raise RuntimeError(f"Prompt drift for Tanzania_{item.farmer_idx}, {label}")
    result = call_provider(provider, prompt)
    schema_valid = valid_decision(result.get("decision"))
    result.update({
        "design_version": DESIGN_VERSION,
        "provider": provider,
        "farmer_id": f"Tanzania_{item.farmer_idx}",
        "farmer_idx": int(item.farmer_idx),
        "actual_country": "Tanzania",
        "assigned_country": label,
        "run_order": int(item.run_order),
        "block_order": int(item.block_order),
        "within_block_order": int(item.within_block_order),
        "prompt_sha256": item.prompt_sha256,
        "schema_valid": schema_valid,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    })
    if not schema_valid and "error" not in result:
        result["error"] = "parsed JSON did not include Boolean adoption and numeric N rate"
    atomic_write(path, result)
    return f"Tanzania_{item.farmer_idx}/{label}", schema_valid, result.get("error", "")


def run_provider(provider: str, workers: int, max_calls: int | None = None) -> None:
    manifest = prepare(write=True)
    profiles = load_profiles().set_index("farmer_idx")
    prospective = manifest[manifest["response_source"] == "prospective_v1"].sort_values("run_order")
    missing = []
    for item in prospective.itertuples(index=False):
        if not completed(new_path(provider, item.assigned_country, item.farmer_idx)):
            missing.append(item)
    if max_calls is not None:
        missing = missing[:max_calls]
    print(f"{provider}: {len(missing)} new label calls scheduled; workers={workers}", flush=True)
    if not missing:
        return
    done = valid = errors = 0
    started = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_one, provider, item, profiles.loc[item.farmer_idx]): item
            for item in missing
        }
        for future in as_completed(futures):
            item = futures[future]
            done += 1
            try:
                _, ok, error = future.result()
            except Exception as exc:
                ok, error = False, repr(exc)
            if ok:
                valid += 1
            else:
                errors += 1
                print(f"  ERROR Tanzania_{item.farmer_idx}/{item.assigned_country}: "
                      f"{error[:180]}", flush=True)
            if done % 10 == 0 or done == len(missing):
                elapsed = time.time() - started
                rate = elapsed / done
                print(f"  [{done}/{len(missing)}] valid={valid} errors={errors} "
                      f"elapsed={elapsed/60:.1f}m ETA={(len(missing)-done)*rate/60:.1f}m",
                      flush=True)


def response_path(provider: str, label: str, farmer_idx: int) -> Path:
    return existing_path(provider, label, farmer_idx) or new_path(provider, label, farmer_idx)


def verification() -> pd.DataFrame:
    manifest = prepare(write=False)
    rows = []
    for provider in PROVIDERS:
        for label in LABELS:
            subset = manifest[manifest["assigned_country"] == label]
            paths = [response_path(provider, label, int(idx)) for idx in subset["farmer_idx"]]
            rows.append({
                "provider": provider,
                "assigned_country": label,
                "source": "reuse_v1" if label in REUSE else "prospective_v1",
                "expected": len(paths),
                "files": sum(path.exists() for path in paths),
                "valid": sum(completed(path) for path in paths),
            })
    return pd.DataFrame(rows)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    run = sub.add_parser("run")
    run.add_argument("provider", choices=PROVIDERS + ("all",))
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--max-calls", type=int, default=None)
    sub.add_parser("verify")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "prepare":
        manifest = prepare(write=True)
        new_calls = int((manifest["response_source"] == "prospective_v1").sum())
        print(f"Wrote/verified {MANIFEST}: 490 cells/provider; {new_calls} new calls/provider")
    elif args.command == "run":
        providers = PROVIDERS if args.provider == "all" else (args.provider,)
        for provider in providers:
            run_provider(provider, workers=max(1, args.workers), max_calls=args.max_calls)
    elif args.command == "verify":
        print(verification().to_string(index=False))


if __name__ == "__main__":
    main()
