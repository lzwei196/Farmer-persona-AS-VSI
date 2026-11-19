"""
LSMS 4-Country Full-Scale Run — 280 farmers × 4 tiers × 3 models

Uses the exact same tier prompts as the 52-farmer pilot (run_lsms_4country.py),
scaled to 70 farmers per country with per-farmer incremental save.

Usage:
    python3 agriagent/src/run_lsms_full.py run <tier> <provider>
    python3 agriagent/src/run_lsms_full.py run 1 claude
    python3 agriagent/src/run_lsms_full.py run all claude
    python3 agriagent/src/run_lsms_full.py run 1,2,3,4 all
    python3 agriagent/src/run_lsms_full.py verify
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ── Path setup ───────────────────────────────────────────────

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

sys.path.insert(0, str(SRC_DIR.parent.parent))
import paths as P
import lsms_utils as U

RESULTS_DIR = PROJECT_ROOT / "results" / "full" / "lsms"
SAMPLE_CSV = P.LSMS_4C_FULL_CSV

# ── Constants ────────────────────────────────────────────────

LLM_TIMEOUT_SEC = 300
MAX_RETRIES = 3
RETRY_BACKOFF = [30, 60, 120]
PROGRESS_EVERY = 10

KIMI_CLI_CMD_ENV = {"DYLD_LIBRARY_PATH": "/opt/homebrew/opt/expat/lib"}


# ── JSON extraction ─────────────────────────────────────────

def extract_json(text: str) -> Optional[dict]:
    """Extract JSON object from LLM response text."""
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    brace_depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == '{':
            if brace_depth == 0:
                start = i
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
            if brace_depth == 0 and start is not None:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    start = None
    return None


# ── CLI Callers (with exponential backoff) ──────────────────

def _clean_env_for_claude() -> dict:
    """Strip Claude Code session env vars so subprocess uses the user's
    real OAuth subscription at ~/.claude/credentials/ instead of the outer
    harness's short-lived tokens (which expire ~1h and kill long runs)."""
    strip_keys = {
        "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN",
        "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN",
        "CLAUDE_CODE_ENTRYPOINT", "CLAUDECODE",
        "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST",
        "CLAUDE_CODE_EXECPATH", "CLAUDE_CODE_SDK_HAS_OAUTH_REFRESH",
        "CLAUDE_AGENT_SDK_VERSION",
    }
    return {k: v for k, v in os.environ.items() if k not in strip_keys}


def call_claude(prompt: str) -> dict:
    last_err = None
    clean_env = _clean_env_for_claude()
    for attempt in range(MAX_RETRIES + 1):
        try:
            t0 = time.time()
            result = subprocess.run(
                ["claude", "-p", "--allowedTools", ""],
                input=prompt, capture_output=True, text=True,
                timeout=LLM_TIMEOUT_SEC, env=clean_env,
            )
            elapsed = round(time.time() - t0, 1)
            raw = result.stdout.strip()
            if result.returncode != 0 and not raw:
                raise RuntimeError(f"claude CLI failed: {result.stderr[:300]}")
            if '"authentication_error"' in raw or '"error"' in raw[:50]:
                raise RuntimeError(f"Auth error: {raw[:200]}")
            return {"raw_response": raw, "decision": extract_json(raw),
                    "elapsed_seconds": elapsed, "model": "claude-cli",
                    "attempts": attempt + 1}
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF[attempt]
                print(f"      Retry {attempt+1}/{MAX_RETRIES} after {wait}s — {e}")
                time.sleep(wait)
    return {"raw_response": "", "decision": None, "error": str(last_err),
            "model": "claude-cli", "attempts": MAX_RETRIES + 1}


def call_codex(prompt: str) -> dict:
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            t0 = time.time()
            result = subprocess.run(
                ["npx", "@openai/codex", "exec",
                 "--skip-git-repo-check", "--full-auto", prompt],
                capture_output=True, text=True, timeout=LLM_TIMEOUT_SEC,
            )
            elapsed = round(time.time() - t0, 1)
            raw = result.stdout.strip()
            if result.returncode != 0 and not raw:
                raise RuntimeError(f"codex CLI failed: {result.stderr[:300]}")
            return {"raw_response": raw, "decision": extract_json(raw),
                    "elapsed_seconds": elapsed, "model": "codex-cli/gpt-5.4",
                    "attempts": attempt + 1}
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF[attempt]
                print(f"      Retry {attempt+1}/{MAX_RETRIES} after {wait}s — {e}")
                time.sleep(wait)
    return {"raw_response": "", "decision": None, "error": str(last_err),
            "model": "codex-cli/gpt-5.4", "attempts": MAX_RETRIES + 1}


def call_kimi(prompt: str) -> dict:
    env = {**os.environ, **KIMI_CLI_CMD_ENV}
    last_err = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            t0 = time.time()
            result = subprocess.run(
                ["kimi", "--print", "--final-message-only",
                 "--input-format", "text"],
                input=prompt, capture_output=True, text=True,
                timeout=LLM_TIMEOUT_SEC, env=env,
            )
            elapsed = round(time.time() - t0, 1)
            raw = result.stdout.strip()
            if result.returncode != 0 and not raw:
                raise RuntimeError(f"kimi CLI failed: {result.stderr[:300]}")
            return {"raw_response": raw, "decision": extract_json(raw),
                    "elapsed_seconds": elapsed, "model": "kimi-cli/kimi-for-coding",
                    "attempts": attempt + 1}
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF[attempt]
                print(f"      Retry {attempt+1}/{MAX_RETRIES} after {wait}s — {e}")
                time.sleep(wait)
    return {"raw_response": "", "decision": None, "error": str(last_err),
            "model": "kimi-cli/kimi-for-coding", "attempts": MAX_RETRIES + 1}


CALLERS = {"claude": call_claude, "codex": call_codex, "kimi": call_kimi}


# ── Prompt Builders (imported from run_lsms_4country.py) ────
# We import the EXACT same prompt builders to ensure consistency
# with the pilot. They're defined here to avoid circular imports.

def build_tier1_prompt(row):
    return U.render_prompt(P.LSMS_4C_TIER1_TEMPLATE, row)


# Import the tier context blocks from run_lsms_4country
from run_lsms_4country import (
    TIER2_CONTEXT, TIER3_RULES,
    TIER4_FERT_CONTEXT, TIER4_SEED_CONTEXT, TIER4_IRRIG_CONTEXT,
)


def build_tier2_prompt(row):
    country = row["country"]
    context = TIER2_CONTEXT[country]
    region = row.get("region_clean", "")
    return context + f"You are in the {region} region.\n\n---\n\n" + build_tier1_prompt(row)


# Tier 3 redesigned: cognitive grounding (reasoning style by education,
# cash constraint, peer copying, context shapers).
# The numerical-practice-range version is preserved as TIER3_RULES (used by
# the T4 diagnostic-checks build), and its results are saved under
# tier3_calibration_backup for sensitivity analysis.
_LSMS_TIER3_COGNITIVE = (PROJECT_ROOT / "prompts" / "lsms_tier3_cognitive_grounding.txt").read_text()


def build_tier3_prompt(row):
    """Tier 3 = cognitive grounding on top of Tier 2 agro-ecological context."""
    return _LSMS_TIER3_COGNITIVE + "\n\n---\n\n" + build_tier2_prompt(row)


def build_tier4_prompt(row):
    country = row["country"]
    plot_ha = row["plot_area_GPS"]
    n_upper = 120 * plot_ha
    asset = row.get("hh_asset_index", 0)
    if pd.isna(asset):
        asset = 0.0

    cereal_low = max(5, 50 * plot_ha)
    cereal_high = max(20, 150 * plot_ha)
    root_low = max(10, 100 * plot_ha)
    root_high = max(30, 250 * plot_ha)

    fert_ctx = TIER4_FERT_CONTEXT[country]
    seed_ctx = TIER4_SEED_CONTEXT[country]
    irrig_ctx = TIER4_IRRIG_CONTEXT[country]

    checks = f"""## Diagnostic Checks and Calibration Anchors

### Plausibility Bounds

Before finalizing, check each decision:

{fert_ctx}

**Nitrogen (if using fertilizer):**
- This plot is {plot_ha:.2f} ha. Scale N to plot size.
- Typical: 0.25ha→5-20kg N, 0.5ha→10-40kg N, 1.0ha→30-80kg N.
- If N > {n_upper:.0f} kg for this plot, that exceeds 95th percentile. Reconsider.

**Improved seed:** {seed_ctx}

**Irrigation:** {irrig_ctx}

**Labor for this {plot_ha:.2f} ha plot:**
- Cereals: {cereal_low:.0f}-{cereal_high:.0f} family labor days
- Root crops/perennials: {root_low:.0f}-{root_high:.0f} family labor days
- Hired labor >50 days on <0.5ha: unusual.

### Cross-Consistency Checks
- fertilizer=no AND improved_seed=yes: unlikely (~5%)
- fertilizer=yes AND nitrogen_kg=0: inconsistent
- irrigated=yes: needs strong justification
- hired_labor > family_labor for a small farm: unusual

### Resource Constraint
Asset index: {asset:.2f} (national mean=0.00).
{"Bottom quartile: severely cash-constrained. Inputs only if subsidized." if asset < -0.5 else "Middle range: some purchasing power, watches costs." if asset < 0.5 else "Top quartile: can afford optimal inputs."}

"""
    return checks + build_tier3_prompt(row)


PROMPT_BUILDERS = {
    1: build_tier1_prompt,
    2: build_tier2_prompt,
    3: build_tier3_prompt,
    4: build_tier4_prompt,
}


# ── Run ──────────────────────────────────────────────────────

def run_lsms(tiers=None, providers=None):
    """
    Run the full LSMS 4-country experiment.

    Results saved per-farmer to:
        results/full/lsms/{provider}/tier{N}/{farmer_idx}.json
    """
    tiers = tiers or [1, 2, 3, 4]
    providers = providers or ["claude", "codex", "kimi"]

    print(f"Loading sample from {SAMPLE_CSV}...")
    sample = pd.read_csv(SAMPLE_CSV)
    print(f"  {len(sample)} farmers, {sorted(sample['country'].unique())}")

    # Save ground truth once
    gt_path = RESULTS_DIR / "_ground_truth.json"
    gt_path.parent.mkdir(parents=True, exist_ok=True)
    gt = sample.to_dict(orient="records")
    with open(gt_path, "w") as f:
        json.dump(gt, f, indent=2, default=str)

    # Save metadata
    meta = {
        "experiment": "lsms_4country_full",
        "n_farmers": len(sample),
        "countries": sorted(sample["country"].unique().tolist()),
        "per_country": dict(sample["country"].value_counts()),
        "tiers": tiers,
        "providers": providers,
        "timestamp": datetime.now().isoformat(),
        "sample_source": str(SAMPLE_CSV),
    }
    with open(RESULTS_DIR / "_metadata.json", "w") as f:
        json.dump(meta, f, indent=2, default=str)

    # Run: provider → tier → farmers
    for provider in providers:
        caller = CALLERS[provider]
        for tier in tiers:
            builder = PROMPT_BUILDERS[tier]
            tier_dir = RESULTS_DIR / provider / f"tier{tier}"
            tier_dir.mkdir(parents=True, exist_ok=True)
            errors_log = RESULTS_DIR / provider / "errors.log"

            n_total = len(sample)
            n_done = 0
            n_skipped = 0
            n_errors = 0
            elapsed_list = []
            t_start = time.time()

            print(f"\n{'='*70}")
            print(f"[{provider.upper()} T{tier}] Starting — {n_total} farmers")
            print(f"{'='*70}")

            for idx, row in sample.iterrows():
                farmer_id = f"{row['country']}_{idx}"
                out_path = tier_dir / f"{farmer_id}.json"

                # Skip if already done
                if out_path.exists():
                    try:
                        existing = json.load(open(out_path))
                        if existing.get("decision") is not None:
                            n_skipped += 1
                            n_done += 1
                            continue
                    except (json.JSONDecodeError, KeyError):
                        pass

                # Build prompt
                prompt = builder(row)

                # Call LLM
                result = caller(prompt)

                # Add metadata
                result["farmer_id"] = farmer_id
                result["farmer_idx"] = int(idx)
                result["country"] = row["country"]
                result["tier"] = tier
                result["provider"] = provider

                # Save immediately
                with open(out_path, "w") as f:
                    json.dump(result, f, indent=2, default=str)

                n_done += 1
                if result.get("decision"):
                    elapsed_list.append(result.get("elapsed_seconds", 0))
                else:
                    n_errors += 1
                    err_msg = (f"[{provider} T{tier}] {farmer_id}: "
                               f"{result.get('error', 'no JSON parsed')}\n")
                    with open(errors_log, "a") as ef:
                        ef.write(err_msg)

                # Progress report
                if (n_done - n_skipped) % PROGRESS_EVERY == 0 or idx == n_total - 1:
                    avg_s = sum(elapsed_list) / len(elapsed_list) if elapsed_list else 0
                    remaining = n_total - n_done
                    eta_h = (remaining * avg_s) / 3600 if avg_s > 0 else 0
                    pct = 100 * n_done / n_total
                    print(f"[{provider.upper()} T{tier}] {n_done}/{n_total} ({pct:.1f}%) — "
                          f"avg {avg_s:.0f}s/call — ETA {eta_h:.1f}h — "
                          f"errors={n_errors}, skipped={n_skipped}")

            elapsed_total = time.time() - t_start
            print(f"[{provider.upper()} T{tier}] DONE in {elapsed_total/60:.1f}min — "
                  f"{n_done} done, {n_errors} errors, {n_skipped} skipped")


# ── Verify ───────────────────────────────────────────────────

def verify_results():
    print(f"\n{'Provider':<10} {'Tier':>4} {'Done':>6} {'Valid':>6} {'Errors':>7}")
    print("-" * 40)
    for provider in ["claude", "codex", "kimi"]:
        for tier in [1, 2, 3, 4]:
            tier_dir = RESULTS_DIR / provider / f"tier{tier}"
            if not tier_dir.exists():
                print(f"{provider:<10} T{tier:>3}      -      -       -")
                continue
            files = list(tier_dir.glob("*.json"))
            valid = 0
            errors = 0
            for fp in files:
                try:
                    d = json.load(open(fp))
                    if d.get("decision"):
                        valid += 1
                    else:
                        errors += 1
                except Exception:
                    errors += 1
            print(f"{provider:<10} T{tier:>3} {len(files):>6} {valid:>6} {errors:>7}")


# ── Entry Point ──────────────────────────────────────────────

def print_usage():
    print("Usage: python3 agriagent/src/run_lsms_full.py run <tiers> <provider>")
    print()
    print("  tiers:    1 | 2 | 3 | 4 | 1,2,3,4 | all")
    print("  provider: claude | codex | kimi | all")
    print()
    print("Examples:")
    print("  python3 agriagent/src/run_lsms_full.py run 1 claude")
    print("  python3 agriagent/src/run_lsms_full.py run all claude")
    print("  python3 agriagent/src/run_lsms_full.py verify")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "verify":
        verify_results()
        sys.exit(0)

    if cmd != "run" or len(sys.argv) < 4:
        print_usage()
        sys.exit(1)

    tier_arg = sys.argv[2]
    if tier_arg == "all":
        tiers = [1, 2, 3, 4]
    else:
        tiers = [int(t) for t in tier_arg.split(",")]

    prov_arg = sys.argv[3]
    if prov_arg == "all":
        providers = ["claude", "codex", "kimi"]
    else:
        providers = [prov_arg]

    run_lsms(tiers=tiers, providers=providers)
