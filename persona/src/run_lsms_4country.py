"""
LSMS 4-Country Experiment — Claude Code, Codex, Kimi CLI

Runs the 4-country pilot sample (52 farmers, 4 countries) through Tier 1–4
prompts using three different LLM CLI tools.

Usage:
    python3 agriagent/src/run_lsms_4country.py run 1 all
    python3 agriagent/src/run_lsms_4country.py run 1,2,3,4 claude
    python3 agriagent/src/run_lsms_4country.py run all all
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ── Path setup ───────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import paths as P
import lsms_utils as U


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


# ── CLI Callers ──────────────────────────────────────────────

def call_claude(prompt: str, retry=1) -> dict:
    """Call Claude Code via CLI."""
    for attempt in range(retry + 1):
        try:
            t0 = time.time()
            result = subprocess.run(
                ["claude", "-p", "--allowedTools", ""],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=P.LLM_TIMEOUT_SEC,
            )
            elapsed = round(time.time() - t0, 1)
            raw = result.stdout.strip()
            if result.returncode != 0 and not raw:
                raise RuntimeError(f"claude CLI failed: {result.stderr[:300]}")
            decision = extract_json(raw)
            if decision is None and attempt < retry:
                print(f"      JSON parse failed, retrying...")
                continue
            return {
                "raw_response": raw,
                "decision": decision,
                "elapsed_seconds": elapsed,
                "model": "claude-cli",
            }
        except subprocess.TimeoutExpired:
            if attempt < retry:
                print(f"      Timeout, retrying...")
                continue
            raise


def call_codex(prompt: str, retry=1) -> dict:
    """Call Codex via CLI."""
    for attempt in range(retry + 1):
        try:
            t0 = time.time()
            result = subprocess.run(
                ["npx", "@openai/codex", "exec",
                 "--skip-git-repo-check", "--full-auto",
                 prompt],
                capture_output=True, text=True,
                timeout=P.LLM_TIMEOUT_SEC,
            )
            elapsed = round(time.time() - t0, 1)
            raw = result.stdout.strip()
            if result.returncode != 0 and not raw:
                raise RuntimeError(f"codex CLI failed: {result.stderr[:300]}")
            decision = extract_json(raw)
            if decision is None and attempt < retry:
                print(f"      JSON parse failed, retrying...")
                continue
            return {
                "raw_response": raw,
                "decision": decision,
                "elapsed_seconds": elapsed,
                "model": "codex-cli/gpt-5.4",
            }
        except subprocess.TimeoutExpired:
            if attempt < retry:
                print(f"      Timeout, retrying...")
                continue
            raise


def call_kimi(prompt: str, retry=1) -> dict:
    """Call Kimi CLI (kimi-for-coding model)."""
    env = {**os.environ, **P.KIMI_CLI_CMD_ENV}
    for attempt in range(retry + 1):
        try:
            t0 = time.time()
            result = subprocess.run(
                ["kimi", "--print", "--final-message-only",
                 "--input-format", "text"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=P.LLM_TIMEOUT_SEC,
                env=env,
            )
            elapsed = round(time.time() - t0, 1)
            raw = result.stdout.strip()
            if result.returncode != 0 and not raw:
                raise RuntimeError(f"kimi CLI failed: {result.stderr[:300]}")
            decision = extract_json(raw)
            if decision is None and attempt < retry:
                print(f"      JSON parse failed, retrying...")
                continue
            return {
                "raw_response": raw,
                "decision": decision,
                "elapsed_seconds": elapsed,
                "model": "kimi-cli/kimi-for-coding",
            }
        except subprocess.TimeoutExpired:
            if attempt < retry:
                print(f"      Timeout, retrying...")
                continue
            raise


CALLERS = {"claude": call_claude, "codex": call_codex, "kimi": call_kimi}


# ── Prompt Builders ──────────────────────────────────────────

def build_tier1_prompt(row):
    """Tier 1: render from the 4-country template."""
    return U.render_prompt(P.LSMS_4C_TIER1_TEMPLATE, row)


# ── Tier 2: Country/Regional Agronomic Context ──────────────

TIER2_CONTEXT = {
    "Nigeria": """## Regional Agronomic Context: Nigeria

Nigeria spans multiple agro-ecological zones from north to south:

**Sudan Savanna (northern Nigeria):**
- Unimodal rainfall: 500-1000mm, June-September
- Main crops: millet, sorghum, cowpea, groundnut, maize
- Growing season: ~120-150 days
- Soils generally sandy, low organic matter, low inherent fertility
- Most agriculture is rainfed; dry-season irrigation limited to fadama areas

**Guinea Savanna (central/middle belt Nigeria):**
- Rainfall: 1000-1500mm, April-October
- Main crops: maize, sorghum, yam, cassava, cowpea, rice
- Growing season: ~180-200 days
- Better soils than Sudan Savanna but still nutrient-depleted
- Most productive agricultural zone in Nigeria

**Humid Forest (southern Nigeria):**
- Bimodal rainfall: 1500-3000mm, March-July and September-November
- Main crops: cassava, yam, cocoyam, plantain, rice, maize, oil palm, cocoa
- Year-round cropping possible; intercropping very common
- Root crops dominate over cereals

**Input Access:**
- Inorganic fertilizer is subsidized but distribution is uneven
- Main products: NPK 20-10-10, NPK 15-15-15, urea
- Improved seeds available through agro-dealers but adoption is ~10-15% nationally
- Pesticide use is low (~15%) except for cowpea and vegetables
- Most smallholders have no access to formal agricultural credit

""",

    "Ethiopia": """## Regional Agronomic Context: Ethiopia

Ethiopia's agriculture is shaped by elevation and rainfall:

**Highland (>1800m, e.g. much of Amhara, parts of Oromia, SNNP):**
- Bimodal rainfall (belg + meher) in some areas, unimodal meher in others
- Main crops: teff, wheat, barley, beans/pulses, enset (false banana)
- Growing season (meher): June-October harvest Nov-Jan
- Cool temperatures; frost risk at highest elevations
- Relatively fertile vertisols and nitisols but waterlogging common

**Mid-altitude (1500-1800m, e.g. parts of Oromia, SNNP, Benshagul Gumuz):**
- Rainfall: 800-1500mm, unimodal
- Main crops: maize, sorghum, teff, coffee, enset, root crops
- Most productive zone for maize
- Better market access in central highlands than periphery

**Lowland (<1500m, e.g. Somali, Afar, parts of Oromia, Harari):**
- Rainfall: 400-800mm, erratic
- Main crops: sorghum, maize, chat (khat), groundnut
- Agro-pastoralist systems; crop agriculture more marginal
- Drought risk high

**Input Access:**
- Fertilizer distributed through cooperative system; mainly DAP and urea
- Government subsidizes but supply is often late or insufficient
- Improved seed adoption ~20-25% for maize, ~10% for wheat
- Pesticide use very low (~5-10%) except for chat and vegetables
- Most farmers rely on ox-plough cultivation

""",

    "Tanzania": """## Regional Agronomic Context: Tanzania

Tanzania's agriculture varies by zone:

**Northern Highlands (e.g. Arusha, Kilimanjaro):**
- Bimodal rainfall: short rains (vuli) Oct-Dec, long rains (masika) Mar-May
- Main crops: maize, beans, coffee, banana, wheat
- Relatively fertile volcanic soils
- Better market access and extension services

**Western/Lake Zone (e.g. Mwanza, Kigoma, Tabora):**
- Unimodal rainfall: 800-1200mm, Nov-April
- Main crops: maize, rice, cassava, cotton, sweet potato
- Long dry season; cassava important as drought buffer
- Tobacco in Tabora region

**Southern Highlands (e.g. Mbeya, Iringa):**
- Unimodal rainfall: 1000-1600mm
- Main crops: maize, rice, tea, Irish potato
- Major maize surplus zone — "breadbasket"
- Relatively good soils and reliable rainfall

**Coastal/Eastern (e.g. Lindi, Mtwara, Zanzibar/Pemba):**
- Bimodal rainfall: 800-1200mm
- Main crops: cassava, cashew nut, coconut, rice, clove (Zanzibar)
- Sandy soils, low inherent fertility
- Cashew and clove important cash crops

**Input Access:**
- Fertilizer subsidy program (National Agricultural Input Voucher Scheme) phased in/out
- Main products: urea, DAP, CAN
- Improved maize seed adoption ~25-30%
- Pesticide use low (~10%) except for cash crops
- Most smallholders use hand-hoe cultivation

""",

    "Malawi": """## Regional Agronomic Context: Malawi

Malawi's agriculture is dominated by maize-based systems:

**Central Region (e.g. Lilongwe, Dowa, Ntchisi, Nkhotakota):**
- Unimodal rainfall: 800-1200mm, Nov-April
- Main crops: maize, groundnut, soybean, tobacco, beans
- Most productive agricultural zone
- Better access to markets and extension

**Southern Region (e.g. Zomba, Machinga, Mangochi, Mulanje, Nsanje):**
- Rainfall: 800-1600mm (higher in Mulanje highlands)
- Main crops: maize, rice, cassava, pigeon pea, cotton
- More diverse cropping; some tea in highlands
- Flood risk in Lower Shire (Nsanje, Chikwawa)

**Northern Region (e.g. Mzimba, Chitipa):**
- Rainfall: 1000-1500mm
- Main crops: maize, cassava, beans, tobacco
- Longer growing season but lower population density
- More land per household than south

**Input Access:**
- Farm Input Subsidy Programme (FISP) is major driver of fertilizer use
- ~40-50% of smallholders receive subsidized fertilizer coupons
- Main products: NPK 23-21-0+4S, urea (46-0-0)
- Without subsidy, fertilizer use drops sharply
- Improved maize seed (hybrid): ~30-40% adoption, driven by FISP
- Pesticide use very low (<10%) for food crops

""",
}


def build_tier2_prompt(row):
    """Tier 2: Tier 1 + country/regional agronomic context."""
    country = row["country"]
    context = TIER2_CONTEXT[country]
    region = row.get("region_clean", "")
    return context + f"You are in the {region} region.\n\n---\n\n" + build_tier1_prompt(row)


# ── Tier 3: Decision Rules and Typical Practice Ranges ──────

TIER3_RULES = {
    "Nigeria": """## Decision Rules and Typical Practice Ranges: Nigeria

### Fertilizer Use
- ~35% of Nigerian plots receive inorganic fertilizer
- Higher in savanna zones (~45-55% for cereals), lower in humid forest (~15-25%)
- Farmers closer to markets (<15 km) more likely to use fertilizer
- Farmers with formal education more likely to use fertilizer
- Female-managed plots have ~5-10pp lower fertilizer use

### Nitrogen Application Rates (users only)
| Crop | Typical N (kg/ha) | Range |
|------|-------------------|-------|
| Maize | 40-80 | 20-120 |
| Sorghum | 30-60 | 15-80 |
| Millet | 20-40 | 10-60 |
| Rice | 50-80 | 30-120 |
| Cassava | 0-20 | 0-40 |
| Yam | 10-30 | 0-50 |
| Cowpea/beans | 0-15 | 0-30 |

NOTE: These are per-hectare. Scale to actual plot size. Small plots often
get higher effective kg/ha because farmers apply in whole bags.

### Seed Choice
- Improved maize: ~35-40% adoption (higher in Guinea Savanna)
- Root crops: mostly local varieties
- Fertilizer and improved seed are complementary

### Labor
- Family labor: 50-150 person-days/ha (cereals), 100-250/ha (root crops)
- ~30% of plots use hired labor
- Larger farms almost always hire some labor

### Pesticide
- ~15% nationally; higher for cowpea (~40%), very low for cassava/yam (<5%)

""",

    "Ethiopia": """## Decision Rules and Typical Practice Ranges: Ethiopia

### Fertilizer Use
- ~35-40% of Ethiopian plots receive inorganic fertilizer
- Highest for cereals in highland/mid-altitude zones (teff, wheat, maize): ~50-60%
- Very low for perennial crops (enset, coffee, chat): ~5-15%
- Pulses/legumes rarely fertilized (<10%) — N-fixing
- Farmers with formal education and ox-plough are more likely to use fertilizer
- Female-headed households ~10-15pp lower fertilizer use

### Nitrogen Application Rates (users only)
| Crop | Typical N (kg/ha) | Range |
|------|-------------------|-------|
| Teff | 30-60 | 15-80 |
| Wheat | 40-70 | 20-100 |
| Barley | 30-50 | 15-70 |
| Maize | 40-80 | 20-120 |
| Sorghum | 20-50 | 10-70 |
| Beans/pulses | 0-10 | 0-20 |
| Enset/perennials | 0-10 | 0-20 |

NOTE: Ethiopian smallholders typically apply DAP at planting + urea topdress.
Standard "package" is 100kg DAP + 100kg urea per hectare (~64 kg N/ha).
Many farmers apply less than the recommended package due to cash constraints.

### Seed Choice
- Improved maize: ~20-25% adoption
- Improved wheat: ~10-15%
- Teff: mostly local varieties (~5% improved)
- Farmers who use fertilizer are more likely to also use improved seed

### Labor
- Family labor: 60-150 person-days/ha (cereals), 80-200/ha (perennials)
- Ox-plough land preparation is standard; families without oxen rent or share
- Hired labor: ~20-25% of plots; mainly for weeding and harvest
- Female-managed plots use less hired labor

### Pesticide
- ~5-10% nationally
- Slightly higher for wheat (~15% — rust control)
- Very low for teff, enset, pulses

""",

    "Tanzania": """## Decision Rules and Typical Practice Ranges: Tanzania

### Fertilizer Use
- ~10-15% of Tanzanian plots receive inorganic fertilizer
- Highest in Southern Highlands for maize (~30-40%) and Northern Highlands
- Very low in western/lake zone and coastal areas (~5%)
- Fertilizer use strongly associated with market access and cash crops
- Educated farmers ~10-15pp more likely to use fertilizer

### Nitrogen Application Rates (users only)
| Crop | Typical N (kg/ha) | Range |
|------|-------------------|-------|
| Maize | 30-60 | 15-100 |
| Rice | 40-70 | 20-100 |
| Sorghum | 20-40 | 10-60 |
| Beans | 0-15 | 0-30 |
| Cassava | 0-10 | 0-20 |
| Cashew/tree crops | 0-15 | 0-30 |

NOTE: Most Tanzanian smallholders who use fertilizer apply less than
recommended rates due to cost. A common practice is 1 bag (50 kg)
of DAP or CAN regardless of plot size.

### Seed Choice
- Improved maize: ~25-30% adoption (higher in surplus zones)
- Improved rice: ~15-20%
- Cassava, sorghum: mostly local varieties
- Open-pollinated improved varieties more common than hybrids

### Labor
- Family labor: 60-180 person-days/ha (hand-hoe systems)
- Most cultivation by hand hoe (jembe); ox-plough rare
- Hired labor: ~25-30% of plots, especially for land clearing and weeding
- Larger farms rely more on hired labor

### Pesticide
- ~10% nationally
- Higher for cashew (~30%), cotton, vegetables
- Very low for maize, cassava, beans (<5%)

""",

    "Malawi": """## Decision Rules and Typical Practice Ranges: Malawi

### Fertilizer Use
- ~40-50% of Malawian plots receive inorganic fertilizer
- Strongly driven by FISP subsidy: recipients ~70-80% use, non-recipients ~15-20%
- Maize plots much more likely to receive fertilizer than other crops
- Tobacco growers also high fertilizer users
- Female-headed households ~5-10pp lower (less access to FISP coupons)

### Nitrogen Application Rates (users only)
| Crop | Typical N (kg/ha) | Range |
|------|-------------------|-------|
| Maize | 40-80 | 20-120 |
| Tobacco | 60-100 | 40-150 |
| Rice | 30-60 | 15-80 |
| Beans/pulses | 0-10 | 0-20 |
| Sorghum | 15-35 | 5-50 |
| Groundnut | 0-10 | 0-20 |

NOTE: Standard FISP package is 1 bag NPK + 1 bag urea (50 kg each)
for 0.4 ha, giving ~69 kg N/ha. Many farmers spread this over more
land than intended, reducing effective rates.

### Seed Choice
- Hybrid maize: ~30-40% adoption (driven by FISP seed coupons)
- OPV maize: ~20% — cheaper, can be recycled
- Local maize: ~30-40% still use local varieties
- Legume seed: mostly local/recycled

### Labor
- Family labor: 80-200 person-days/ha (maize), 60-150/ha (legumes)
- Hand-hoe dominant; ridging is standard practice for maize
- Hired labor (ganyu): ~25-35% of plots
- Cash-poor households often sell labor (ganyu) on others' farms

### Pesticide
- ~5-10% nationally for food crops
- Higher for tobacco (~40%)
- Very low for maize, beans, sorghum (<5%)

""",
}


def build_tier3_prompt(row):
    """Tier 3: Tier 2 + decision rules and practice ranges."""
    country = row["country"]
    rules = TIER3_RULES[country]
    return rules + build_tier2_prompt(row)


# ── Tier 4: Diagnostic Checks and Calibration Anchors ───────

TIER4_FERT_CONTEXT = {
    "Nigeria": """**Fertilizer:**
- Humid Forest + root crops: ~15-25% use fertilizer. Most do NOT.
- Savanna + cereals: ~40-55% use fertilizer.
- Farm <0.5ha, no education, >20km from market: fertilizer use ~15-20%.""",

    "Ethiopia": """**Fertilizer:**
- Highland cereals (teff, wheat, barley): ~50-60% use fertilizer.
- Lowland or perennial crops (enset, coffee, chat): ~5-15%.
- No education + remote area: fertilizer use ~15-20%.
- Pulses/legumes: rarely fertilized (<10%).""",

    "Tanzania": """**Fertilizer:**
- Southern Highlands maize: ~30-40% use fertilizer.
- Coastal/western zone + non-cereal crops: ~5% use fertilizer.
- Farm <0.5ha, no education: fertilizer use ~5-10%.
- Cash crop farmers (cashew, tobacco) more likely to use inputs.""",

    "Malawi": """**Fertilizer:**
- Maize with FISP subsidy access: ~70-80% use fertilizer.
- Maize without subsidy: ~15-20%.
- Non-maize food crops (beans, sorghum, groundnut): ~5-15%.
- Female-headed, no education: fertilizer use ~20-30%.""",
}

TIER4_SEED_CONTEXT = {
    "Nigeria": "~10-15% nationally. Needs plausible reason (agro-dealer access, education).",
    "Ethiopia": "~10-20% nationally. Higher for maize (~25%). Teff mostly local varieties.",
    "Tanzania": "~15-25% nationally. Higher in Southern Highlands for maize (~30%).",
    "Malawi": "~30-40% for maize (FISP-driven). Much lower for other crops.",
}

TIER4_IRRIG_CONTEXT = {
    "Nigeria": "Only ~2% of plots. Default to no unless fadama area.",
    "Ethiopia": "Only ~2-3% of plots. Default to no unless specific irrigation scheme mentioned.",
    "Tanzania": "Only ~2-3% of plots. Slightly higher for rice in lowland areas.",
    "Malawi": "Very rare (<2%). Nearly all rainfed.",
}


def build_tier4_prompt(row):
    """Tier 4: Tier 3 + diagnostic checks and calibration anchors."""
    country = row["country"]
    plot_ha = row["plot_area_GPS"]
    n_upper = 120 * plot_ha
    asset = row.get("hh_asset_index", 0)
    if pd.isna(asset):
        asset = 0.0

    # Scale labor bounds by plot area
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


# ── Run Experiment ───────────────────────────────────────────

def run_4country(tiers=None, providers=None, n_runs=1):
    """Run experiment across specified tiers and providers."""
    tiers = tiers or [1, 2, 3, 4]
    providers = providers or list(CALLERS.keys())

    # Load 4-country pilot sample
    sample = pd.read_csv(P.LSMS_4C_PILOT_CSV)
    print(f"Loaded {len(sample)} farmers from 4-country pilot")
    print(f"  Countries: {sorted(sample['country'].unique())}")
    print(f"  Tiers: {tiers}")
    print(f"  Providers: {providers}")

    # Create run directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = P.RESULTS_LSMS_DIR / f"run_4c_{timestamp}"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Save ground truth
    gt = sample.to_dict(orient="records")
    with open(results_dir / "_ground_truth.json", "w") as f:
        json.dump(gt, f, indent=2, default=str)

    # Save metadata
    meta = {
        "providers": providers,
        "tiers": tiers,
        "n_runs": n_runs,
        "n_farmers": len(sample),
        "n_countries": len(sample["country"].unique()),
        "countries": sorted(sample["country"].unique().tolist()),
        "timestamp": timestamp,
        "data_source": "LSMS-ISA Harmonized Panel — 4-country pilot",
    }
    with open(results_dir / "_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    for tier in tiers:
        builder = PROMPT_BUILDERS[tier]

        for provider in providers:
            caller = CALLERS[provider]
            tier_results = []
            save_path = results_dir / f"tier{tier}_{provider}.json"

            print(f"\n{'=' * 60}")
            print(f"TIER {tier} — {provider} — {len(sample)} farmers")
            print(f"{'=' * 60}")

            for idx, row in sample.iterrows():
                farmer_num = idx + 1
                country = row["country"]
                gender = "F" if row.get("female_manager") == 1 else "M"
                crop = row.get("main_crop", "?")
                plot_ha = row.get("plot_area_GPS", 0)

                print(f"\n  [{farmer_num}/{len(sample)}] {country} | "
                      f"{gender}, {plot_ha:.2f}ha, {crop}")

                prompt = builder(row)

                for run_id in range(n_runs):
                    try:
                        result = caller(prompt, retry=P.LLM_RETRIES)
                        result["farmer_idx"] = int(idx)
                        result["country"] = country
                        result["tier"] = tier
                        result["run_id"] = run_id
                        result["provider"] = provider
                        tier_results.append(result)

                        dec = result.get("decision", {})
                        if dec:
                            fert = dec.get("inorganic_fertilizer", "?")
                            n_kg = dec.get("nitrogen_kg_per_ha", dec.get("nitrogen_kg", "?"))
                            print(f"    Run {run_id+1}: {result['elapsed_seconds']}s — "
                                  f"fert={fert}, N={n_kg}")
                        else:
                            print(f"    Run {run_id+1}: {result['elapsed_seconds']}s — "
                                  f"JSON PARSE FAILED")

                    except Exception as e:
                        print(f"    Run {run_id+1}: FAILED — {e}")
                        tier_results.append({
                            "farmer_idx": int(idx),
                            "country": country,
                            "tier": tier,
                            "run_id": run_id,
                            "provider": provider,
                            "error": str(e),
                        })

                    # Incremental save
                    with open(save_path, "w") as f:
                        json.dump(tier_results, f, indent=2, default=str)

            n_valid = sum(1 for r in tier_results if r.get("decision"))
            print(f"\n  Tier {tier} {provider} complete: "
                  f"{n_valid}/{len(tier_results)} valid")

    print(f"\nAll results saved to {results_dir}")
    return results_dir


# ── Entry Point ──────────────────────────────────────────────

if __name__ == "__main__":
    P.RESULTS_LSMS_DIR.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) < 2:
        print("Usage: python3 agriagent/src/run_lsms_4country.py run [tiers] [provider] [n_runs]")
        print()
        print("  run all all         Run all 4 tiers, all 3 providers")
        print("  run 1 all           Run tier 1 only, all providers")
        print("  run 2,3,4 claude    Run tiers 2-4, Claude only")
        print("  run 1,2 codex 3     Run tiers 1-2, Codex, 3 runs each")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "run":
        # Parse tier arg
        tier_arg = sys.argv[2] if len(sys.argv) > 2 else "all"
        if tier_arg == "all":
            tiers = [1, 2, 3, 4]
        else:
            tiers = [int(t) for t in tier_arg.split(",")]

        # Parse provider
        provider_arg = sys.argv[3] if len(sys.argv) > 3 else "all"
        if provider_arg == "all":
            providers = list(CALLERS.keys())
        elif provider_arg in CALLERS:
            providers = [provider_arg]
        else:
            print(f"Unknown provider: {provider_arg}")
            print(f"Available: {', '.join(CALLERS.keys())}, all")
            sys.exit(1)

        # Parse n_runs
        n_runs = 1
        if len(sys.argv) > 4 and sys.argv[4].isdigit():
            n_runs = int(sys.argv[4])

        print(f"Running tiers={tiers}, providers={providers}, n_runs={n_runs}")
        run_4country(tiers=tiers, providers=providers, n_runs=n_runs)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
