"""Confirmatory T1 run for Paper 2's Mali/Niger/Uganda extension.

This v2 protocol fixes two comparability problems in the exploratory Claude run:

1. it uses the exact original T1 prompt without an extra system prompt; and
2. every CLI call runs in an empty temporary directory, preventing project-context leakage.

The design is frozen by ``results/analysis/paper2_npj_confirmatory_design.md``.

Commands
--------
    /usr/bin/python3 src/paper2_extension_confirmatory.py prepare
    /usr/bin/python3 src/paper2_extension_confirmatory.py run claude --workers 4
    /usr/bin/python3 src/paper2_extension_confirmatory.py run codex --workers 4
    /usr/bin/python3 src/paper2_extension_confirmatory.py run kimi --workers 4
    /usr/bin/python3 src/paper2_extension_confirmatory.py verify
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
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

SAMPLE = ROOT / "data" / "profiles" / "lsms_extension_3country.csv"
TEMPLATE = ROOT / "prompts" / "main" / "lsms_4country_tier1_template.txt"
RESULTS = ROOT / "results" / "full" / "lsms_extension_confirmatory_v2"
MANIFEST = RESULTS / "design_manifest.csv"
METADATA = RESULTS / "_metadata.json"
SEED = 20260827
DESIGN_VERSION = "paper2-extension-confirmatory-v2"
PROVIDERS = ("claude", "codex", "kimi")
REQUIRED_COUNTRIES = ("Mali", "Niger", "Uganda")
REQUIRED_KEYS = {
    "inorganic_fertilizer", "nitrogen_kg_per_ha", "organic_fertilizer",
    "improved_seed", "used_pesticides", "irrigated", "family_labor_days",
    "hired_labor_days",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_profiles() -> pd.DataFrame:
    profiles = pd.read_csv(SAMPLE).copy()
    profiles["profile_index"] = profiles.index.astype(int)
    if len(profiles) != 210:
        raise RuntimeError(f"Expected 210 extension profiles, found {len(profiles)}")
    counts = profiles["country"].value_counts().to_dict()
    if counts != {country: 70 for country in REQUIRED_COUNTRIES}:
        raise RuntimeError(f"Unexpected country counts: {counts}")
    if profiles["nitrogen_kg_per_ha"].isna().any():
        raise RuntimeError("Missing observed N-rate in frozen extension sample")
    return profiles


def profile_id(row: pd.Series) -> str:
    raw = f"{row['country']}_{row['plot_id_merge']}"
    return raw.replace("/", "_").replace(" ", "_")


def output_key(profile_name: str, profile_index: int) -> str:
    """Unique file key even when a survey plot identifier repeats across rows."""
    return f"{profile_name}__row{profile_index}"


def render_prompt(row: pd.Series) -> str:
    return U.render_prompt(TEMPLATE, row)


def build_manifest() -> pd.DataFrame:
    profiles = load_profiles()
    rng = np.random.default_rng(SEED)
    order = rng.permutation(profiles["profile_index"].to_numpy(int))
    indexed = profiles.set_index("profile_index")
    records = []
    for run_order, idx in enumerate(order):
        row = indexed.loc[int(idx)]
        prompt = render_prompt(row)
        records.append({
            "run_order": run_order,
            "profile_index": int(idx),
            "profile_id": profile_id(row),
            "country": row["country"],
            "plot_id_merge": row["plot_id_merge"],
            "prompt_sha256": sha256_text(prompt),
        })
    manifest = pd.DataFrame(records)
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: pd.DataFrame) -> None:
    if len(manifest) != 210:
        raise RuntimeError(f"Manifest should contain 210 rows, found {len(manifest)}")
    if manifest["profile_index"].duplicated().any():
        raise RuntimeError("Duplicate profile in extension manifest")
    keys = [output_key(row.profile_id, int(row.profile_index))
            for row in manifest.itertuples(index=False)]
    if len(keys) != len(set(keys)):
        raise RuntimeError("Output keys are not unique")
    counts = manifest["country"].value_counts().to_dict()
    if counts != {country: 70 for country in REQUIRED_COUNTRIES}:
        raise RuntimeError(f"Manifest country counts changed: {counts}")


def prepare(write: bool = True) -> pd.DataFrame:
    manifest = build_manifest()
    if not write:
        return manifest
    RESULTS.mkdir(parents=True, exist_ok=True)
    if MANIFEST.exists():
        existing = pd.read_csv(MANIFEST)
        validate_manifest(existing)
        if not existing[list(manifest.columns)].equals(manifest):
            raise RuntimeError("Existing extension manifest differs; refusing overwrite")
    else:
        manifest.to_csv(MANIFEST, index=False)
    metadata = {
        "design_version": DESIGN_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "n_profiles": len(manifest),
        "countries": list(REQUIRED_COUNTRIES),
        "providers": list(PROVIDERS),
        "calls_per_provider": len(manifest),
        "planned_total_calls": len(manifest) * len(PROVIDERS),
        "sample": str(SAMPLE),
        "sample_sha256": sha256_file(SAMPLE),
        "template": str(TEMPLATE),
        "template_sha256": sha256_file(TEMPLATE),
        "additional_system_prompt": False,
        "empty_working_directory": True,
        "response_filename_key": "country_plot_id__row{profile_index}",
        "repeated_plot_id_note": "Two Uganda plot identifiers occur twice; row index distinguishes all 210 experimental units.",
        "provider_cli_versions_at_prepare": {p: cli_version(p) for p in PROVIDERS},
    }
    if not METADATA.exists():
        METADATA.write_text(json.dumps(metadata, indent=2) + "\n")
    return manifest


def valid_decision(decision: object) -> bool:
    if not isinstance(decision, dict) or not REQUIRED_KEYS.issubset(decision):
        return False
    nitrogen = decision.get("nitrogen_kg_per_ha")
    return isinstance(nitrogen, (int, float)) and np.isfinite(nitrogen)


def completed(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return bool(payload.get("schema_valid")) and valid_decision(payload.get("decision"))


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    temporary.replace(path)


def run_one(provider: str, item, row: pd.Series) -> tuple[str, bool, str]:
    out_path = RESULTS / provider / f"{output_key(item.profile_id, item.profile_index)}.json"
    prompt = render_prompt(row)
    if sha256_text(prompt) != item.prompt_sha256:
        raise RuntimeError(f"Prompt drift for {item.profile_id}")
    result = call_provider(provider, prompt)
    schema_valid = valid_decision(result.get("decision"))
    result.update({
        "design_version": DESIGN_VERSION,
        "provider": provider,
        "profile_index": int(item.profile_index),
        "profile_id": item.profile_id,
        "country": item.country,
        "plot_id": item.plot_id_merge,
        "tier": 1,
        "run_order": int(item.run_order),
        "prompt_sha256": item.prompt_sha256,
        "observed_n_per_ha": float(row["nitrogen_kg_per_ha"]),
        "observed_fertilizer": int(float(row["nitrogen_kg_per_ha"]) > 0),
        "schema_valid": schema_valid,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    })
    if not schema_valid and "error" not in result:
        result["error"] = "parsed JSON did not match the frozen T1 response schema"
    atomic_write(out_path, result)
    return item.profile_id, schema_valid, result.get("error", "")


def run_provider(provider: str, workers: int, max_calls: int | None = None) -> None:
    if provider not in PROVIDERS:
        raise ValueError(provider)
    manifest = prepare(write=True).sort_values("run_order")
    profiles = load_profiles().set_index("profile_index")
    missing = []
    for item in manifest.itertuples(index=False):
        path = RESULTS / provider / f"{output_key(item.profile_id, item.profile_index)}.json"
        if not completed(path):
            missing.append(item)
    if max_calls is not None:
        missing = missing[:max_calls]
    print(f"{provider}: {len(missing)} calls scheduled; workers={workers}", flush=True)
    if not missing:
        return
    valid = errors = done = 0
    started = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_one, provider, item, profiles.loc[item.profile_index]): item
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
                print(f"  ERROR {item.profile_id}: {error[:180]}", flush=True)
            if done % 10 == 0 or done == len(missing):
                elapsed = time.time() - started
                rate = elapsed / done
                print(f"  [{done}/{len(missing)}] valid={valid} errors={errors} "
                      f"elapsed={elapsed/60:.1f}m ETA={(len(missing)-done)*rate/60:.1f}m",
                      flush=True)


def verification() -> pd.DataFrame:
    manifest = prepare(write=False)
    rows = []
    for provider in PROVIDERS:
        for country in REQUIRED_COUNTRIES:
            subset = manifest[manifest["country"] == country]
            paths = [
                RESULTS / provider / f"{output_key(item.profile_id, item.profile_index)}.json"
                for item in subset.itertuples(index=False)
            ]
            rows.append({
                "provider": provider,
                "country": country,
                "expected": len(paths),
                "files": sum(path.exists() for path in paths),
                "valid": sum(completed(path) for path in paths),
            })
    return pd.DataFrame(rows)


def migrate_legacy_filenames() -> None:
    """Preserve completed pilot/full calls made before row indexes entered filenames."""
    moved = skipped = 0
    for provider in PROVIDERS:
        directory = RESULTS / provider
        if not directory.exists():
            continue
        for path in list(directory.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                idx = int(payload["profile_index"])
                name = str(payload["profile_id"])
            except Exception:
                skipped += 1
                continue
            target = directory / f"{output_key(name, idx)}.json"
            if path == target:
                continue
            if target.exists():
                raise RuntimeError(f"Migration target already exists: {target}")
            path.replace(target)
            moved += 1
    print(f"Migrated {moved} completed response files; skipped {skipped}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    sub.add_parser("migrate-legacy-filenames")
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
        print(f"Wrote/verified {MANIFEST}: {len(manifest)} calls per provider")
    elif args.command == "migrate-legacy-filenames":
        migrate_legacy_filenames()
    elif args.command == "run":
        providers = PROVIDERS if args.provider == "all" else (args.provider,)
        for provider in providers:
            run_provider(provider, workers=max(1, args.workers), max_calls=args.max_calls)
    elif args.command == "verify":
        print(verification().to_string(index=False))


if __name__ == "__main__":
    main()
