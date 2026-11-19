"""Run Paper 2's country-label ablation on fixed Tanzanian profiles.

Experimental unit
-----------------
One of the 70 Tanzania profiles in ``lsms_4country_full.csv``.  Each profile is
queried once per location arm and provider.  Location is the only prompt field
that changes within a profile:

* true_country: ``Country: Tanzania``
* region_only: ``Broad region: East Africa`` (country name absent)
* swapped_country: ``Country: Nigeria``

Admin-region names are omitted in every arm so the region-only and swap arms do
not leak or contradict the true country.  Profile blocks and within-block arm
order are randomized with a frozen seed.  Calls are stateless, so there is no
carry-over between arms.

Commands
--------
    python src/paper2_country_label_ablation.py prepare
    python src/paper2_country_label_ablation.py show-prompts --profile 140
    python src/paper2_country_label_ablation.py run claude
    python src/paper2_country_label_ablation.py run codex
    python src/paper2_country_label_ablation.py run kimi
    python src/paper2_country_label_ablation.py verify

The runner is incremental and safe to resume.  A completed JSON decision is
never overwritten unless ``--force`` is explicitly supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

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

SAMPLE = ROOT / "data" / "profiles" / "lsms_4country_full.csv"
TEMPLATE = ROOT / "prompts" / "main" / "paper2_country_label_ablation_template.txt"
RESULTS = ROOT / "results" / "paper2_country_label_ablation"
MANIFEST = RESULTS / "design_manifest.csv"
METADATA = RESULTS / "_metadata.json"
SEED = 20260826
DESIGN_VERSION = "paper2-country-label-v1"
PROVIDERS = ("claude", "codex", "kimi")
LLM_TIMEOUT_SECONDS = 300
MAX_RETRIES = 1
ARMS = {
    "true_country": "- Country: Tanzania",
    "region_only": "- Broad region: East Africa",
    "swapped_country": "- Country: Nigeria",
}


def extract_json(text):
    """Extract the first valid JSON object, preferring a fenced JSON block."""
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    depth = 0
    start = None
    for i, char in enumerate(text):
        if char == "{":
            if depth == 0:
                start = i
            depth += 1
        elif char == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    start = None
    return None


def clean_claude_env():
    """Use the user's CLI authentication, not short-lived outer-harness credentials."""
    strip = {
        "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_BASE_URL",
        "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_ENTRYPOINT", "CLAUDECODE",
        "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST", "CLAUDE_CODE_EXECPATH",
        "CLAUDE_CODE_SDK_HAS_OAUTH_REFRESH", "CLAUDE_AGENT_SDK_VERSION",
    }
    return {key: value for key, value in os.environ.items() if key not in strip}


def call_provider(provider, prompt):
    """Call the currently installed CLI in an empty cwd to prevent project-context leakage."""
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            with tempfile.TemporaryDirectory(prefix=f"paper2_{provider}_") as empty_cwd:
                if provider == "claude":
                    # These are the flags already validated by the completed LSMS run.  The
                    # empty cwd supplies experiment isolation without disabling OAuth/keychain.
                    command = ["claude", "--print", "--allowedTools", ""]
                    run_kwargs = {"input": prompt, "env": clean_claude_env()}
                elif provider == "codex":
                    command = [
                        "codex", "exec", "--skip-git-repo-check", "--ephemeral",
                        "--ignore-rules", "--sandbox", "read-only", "-",
                    ]
                    run_kwargs = {"input": prompt}
                elif provider == "kimi":
                    command = ["kimi", "--prompt", prompt, "--output-format", "text"]
                    env = {**os.environ, "DYLD_LIBRARY_PATH": "/opt/homebrew/opt/expat/lib"}
                    run_kwargs = {"env": env}
                else:  # pragma: no cover - guarded by argparse
                    raise ValueError(provider)

                started = time.time()
                completed_run = subprocess.run(
                    command, capture_output=True, text=True, timeout=LLM_TIMEOUT_SECONDS,
                    cwd=empty_cwd, **run_kwargs)
                elapsed = round(time.time() - started, 1)
            raw = completed_run.stdout.strip()
            if completed_run.returncode != 0:
                raise RuntimeError(completed_run.stderr.strip()[:1000] or
                                   f"exit={completed_run.returncode}")
            decision = extract_json(raw)
            if decision is None:
                raise RuntimeError(f"no JSON decision parsed; response starts: {raw[:500]}")
            return {
                "raw_response": raw,
                "decision": decision,
                "elapsed_seconds": elapsed,
                "model": f"{provider}-cli-current",
                "attempts": attempt + 1,
            }
        except Exception as exc:  # subprocess errors are recorded after one retry
            last_error = exc
            if attempt < MAX_RETRIES:
                print(f"      {provider} retry after 10s — {exc}", flush=True)
                time.sleep(10)
    return {
        "raw_response": "",
        "decision": None,
        "error": str(last_error),
        "model": f"{provider}-cli-current",
        "attempts": MAX_RETRIES + 1,
    }


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cli_version(provider):
    commands = {
        "claude": ["claude", "--version"],
        "codex": ["codex", "--version"],
        "kimi": ["kimi", "--version"],
    }
    try:
        result = subprocess.run(commands[provider], capture_output=True, text=True, timeout=30)
        text = (result.stdout or result.stderr).strip()
        return text[:500] if text else f"exit={result.returncode}"
    except Exception as exc:  # pragma: no cover - environment diagnostic only
        return f"unavailable: {exc}"


def load_profiles():
    sample = pd.read_csv(SAMPLE)
    sample["farmer_idx"] = sample.index.astype(int)
    profiles = sample[sample["country"] == "Tanzania"].copy()
    if len(profiles) != 70:
        raise RuntimeError(f"Expected 70 Tanzania profiles, found {len(profiles)}")
    if profiles["nitrogen_kg_per_ha"].isna().any():
        raise RuntimeError("Tanzania ablation profiles unexpectedly contain missing N-rate truth")
    return profiles


def build_manifest():
    """Randomized complete-block schedule: profile block order and arm order both seeded."""
    profiles = load_profiles()
    rng = np.random.default_rng(SEED)
    profile_order = rng.permutation(profiles["farmer_idx"].to_numpy(int))
    records = []
    run_order = 0
    for block_order, farmer_idx in enumerate(profile_order):
        for within_block_order, arm in enumerate(rng.permutation(list(ARMS))):
            records.append({
                "run_order": run_order,
                "block_order": block_order,
                "within_block_order": within_block_order,
                "farmer_idx": int(farmer_idx),
                "actual_country": "Tanzania",
                "arm": arm,
                "location_line": ARMS[arm],
            })
            run_order += 1
    manifest = pd.DataFrame(records)
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest):
    if len(manifest) != 210:
        raise RuntimeError(f"Manifest should have 210 rows, found {len(manifest)}")
    if manifest.duplicated(["farmer_idx", "arm"]).any():
        raise RuntimeError("Duplicate profile-arm assignment in manifest")
    counts = manifest.groupby("farmer_idx")["arm"].nunique()
    if not (counts == len(ARMS)).all():
        raise RuntimeError("Every profile must receive every arm exactly once")
    if set(manifest["arm"]) != set(ARMS):
        raise RuntimeError("Manifest arm set does not match frozen design")


def render_prompt(row, arm):
    fields = U.row_to_identity_fields(row)
    fields["location_line"] = ARMS[arm]
    prompt = TEMPLATE.read_text(encoding="utf-8").format(**fields)
    # Location audit: only the true arm may contain the true country; no arm contains admin_1.
    if arm != "true_country" and "Tanzania" in prompt:
        raise RuntimeError(f"True-country leakage in {arm} prompt")
    region = str(row.get("region_clean", ""))
    if region and region.lower() != "nan" and region in prompt:
        raise RuntimeError(f"Admin-region leakage in {arm} prompt: {region}")
    if arm == "swapped_country" and "Nigeria" not in prompt:
        raise RuntimeError("Swap label missing from swapped-country prompt")
    return prompt


def prepare(write=True):
    manifest = build_manifest()
    profiles = load_profiles().set_index("farmer_idx")
    prompt_hashes = []
    for item in manifest.itertuples(index=False):
        prompt_hashes.append(sha256_text(render_prompt(profiles.loc[item.farmer_idx], item.arm)))
    manifest["prompt_sha256"] = prompt_hashes
    if write:
        RESULTS.mkdir(parents=True, exist_ok=True)
        if MANIFEST.exists():
            existing = pd.read_csv(MANIFEST)
            validate_manifest(existing)
            cols = list(manifest.columns)
            if not existing[cols].equals(manifest[cols]):
                raise RuntimeError("Existing manifest differs from frozen design; refusing overwrite")
        else:
            manifest.to_csv(MANIFEST, index=False)
        metadata = {
            "design_version": DESIGN_VERSION,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "seed": SEED,
            "experimental_unit": "Tanzania farmer profile",
            "n_profiles": 70,
            "arms": ARMS,
            "n_calls_per_provider": len(manifest),
            "providers": list(PROVIDERS),
            "planned_total_calls": len(manifest) * len(PROVIDERS),
            "sample": str(SAMPLE),
            "template": str(TEMPLATE),
            "template_sha256": sha256_text(TEMPLATE.read_text(encoding="utf-8")),
            "provider_cli_versions_at_prepare": {p: cli_version(p) for p in PROVIDERS},
        }
        if not METADATA.exists():
            METADATA.write_text(json.dumps(metadata, indent=2) + "\n")
    return manifest


def completed(path):
    if not path.exists():
        return False
    try:
        return (json.loads(path.read_text(encoding="utf-8")).get("decision") or {}) != {}
    except (json.JSONDecodeError, OSError):
        return False


def run_provider(provider, force=False, max_calls=None):
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")
    manifest = prepare(write=True)
    profiles = load_profiles().set_index("farmer_idx")
    out_root = RESULTS / provider
    out_root.mkdir(parents=True, exist_ok=True)
    errors_path = out_root / "errors.log"

    attempted = valid = skipped = errors = 0
    started = time.time()
    for item in manifest.sort_values("run_order").itertuples(index=False):
        out_dir = out_root / item.arm
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"Tanzania_{item.farmer_idx}.json"
        if completed(out_path) and not force:
            skipped += 1
            continue
        if max_calls is not None and attempted >= max_calls:
            break

        row = profiles.loc[item.farmer_idx]
        prompt = render_prompt(row, item.arm)
        prompt_hash = sha256_text(prompt)
        if prompt_hash != item.prompt_sha256:
            raise RuntimeError(f"Prompt hash drift for profile {item.farmer_idx}, arm {item.arm}")

        result = call_provider(provider, prompt)
        result.update({
            "design_version": DESIGN_VERSION,
            "farmer_id": f"Tanzania_{item.farmer_idx}",
            "farmer_idx": int(item.farmer_idx),
            "actual_country": "Tanzania",
            "arm": item.arm,
            "location_line": item.location_line,
            "run_order": int(item.run_order),
            "block_order": int(item.block_order),
            "within_block_order": int(item.within_block_order),
            "provider": provider,
            "prompt_sha256": prompt_hash,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        })
        out_path.write_text(json.dumps(result, indent=2, default=str) + "\n")
        attempted += 1
        if result.get("decision"):
            valid += 1
        else:
            errors += 1
            with open(errors_path, "a") as f:
                f.write(f"{result['timestamp_utc']} {item.arm} Tanzania_{item.farmer_idx}: "
                        f"{result.get('error', 'no JSON decision')}\n")
        if attempted % 10 == 0:
            elapsed = time.time() - started
            rate = elapsed / attempted
            remaining = len(manifest) - skipped - attempted
            print(f"[{provider}] attempted={attempted}, valid={valid}, errors={errors}, "
                  f"preexisting={skipped}, {rate:.1f}s/call, ETA={remaining * rate / 3600:.2f}h",
                  flush=True)
    print(f"[{provider}] finished this invocation: attempted={attempted}, valid={valid}, "
          f"errors={errors}, preexisting={skipped}")


def verification():
    manifest = prepare(write=False)
    rows = []
    for provider in PROVIDERS:
        for arm in ARMS:
            paths = list((RESULTS / provider / arm).glob("*.json")) \
                if (RESULTS / provider / arm).exists() else []
            valid = sum(completed(path) for path in paths)
            rows.append({"provider": provider, "arm": arm, "files": len(paths),
                         "valid": valid, "expected": int((manifest.arm == arm).sum())})
    return pd.DataFrame(rows)


def show_prompts(profile):
    profiles = load_profiles().set_index("farmer_idx")
    if profile not in profiles.index:
        raise ValueError(f"Profile {profile} is not a Tanzania profile")
    row = profiles.loc[profile]
    for arm in ARMS:
        print(f"\n{'=' * 30} {arm} {'=' * 30}\n")
        print(render_prompt(row, arm))


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    show = sub.add_parser("show-prompts")
    show.add_argument("--profile", type=int, default=140)
    run = sub.add_parser("run")
    run.add_argument("provider", choices=PROVIDERS + ("all",))
    run.add_argument("--force", action="store_true")
    run.add_argument("--max-calls", type=int, default=None,
                     help="Diagnostic cap for this invocation; omitted means finish provider")
    sub.add_parser("verify")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.command == "prepare":
        manifest = prepare(write=True)
        print(f"Wrote/verified {MANIFEST}: {len(manifest)} scheduled calls per provider")
    elif args.command == "show-prompts":
        show_prompts(args.profile)
    elif args.command == "verify":
        print(verification().to_string(index=False))
    elif args.command == "run":
        providers = PROVIDERS if args.provider == "all" else (args.provider,)
        for provider in providers:
            run_provider(provider, force=args.force, max_calls=args.max_calls)


if __name__ == "__main__":
    main()
