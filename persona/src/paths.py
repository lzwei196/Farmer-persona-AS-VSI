"""Canonical paths for the AgriAgent project.

Always import from here instead of hardcoding paths. The LSMS-ISA data
directory has a leading space in its name ("agriagent/ LSMS-ISA data/"),
which is easy to mistype.

All paths are absolute and resolved from this file's location, so they
work regardless of the current working directory.
"""
from pathlib import Path

# Resolve from this file: src/paths.py -> src/ -> agriagent/ -> repo root
SRC_DIR = Path(__file__).resolve().parent
AGRIAGENT_DIR = SRC_DIR.parent
REPO_ROOT = AGRIAGENT_DIR.parent

# Data directories
LSMS_DATA_DIR = AGRIAGENT_DIR / " LSMS-ISA data"  # leading space is intentional
LSMS_PLOT_DTA = LSMS_DATA_DIR / "Plot_dataset.dta"
LSMS_HH_DTA = LSMS_DATA_DIR / "Household_dataset.dta"
LSMS_PLOTCROP_DTA = LSMS_DATA_DIR / "Plotcrop_dataset.dta"
LSMS_IND_DTA = LSMS_DATA_DIR / "Individual_dataset.dta"

# Project data (derived samples, summaries)
DATA_DIR = AGRIAGENT_DIR / "data"
LSMS_OUT_DIR = DATA_DIR / "lsms"
LSMS_4C_PILOT_CSV = LSMS_OUT_DIR / "lsms_4country_pilot.csv"
LSMS_4C_PILOT_STATS = LSMS_OUT_DIR / "lsms_4country_pilot_stats.md"
LSMS_4C_FULL_CSV = LSMS_OUT_DIR / "lsms_4country_full.csv"
LSMS_4C_FULL_STATS = LSMS_OUT_DIR / "lsms_4country_full_stats.md"
LSMS_NIGERIA_PILOT_CSV = LSMS_OUT_DIR / "lsms_pilot_sample.csv"
LSMS_DQ_FINDINGS = LSMS_OUT_DIR / "data_quality_findings.md"

# Prompts
PROMPTS_DIR = AGRIAGENT_DIR / "prompts"
LSMS_4C_TIER1_TEMPLATE = PROMPTS_DIR / "lsms_4country_tier1_template.txt"
LSMS_NG_TIER1_TEMPLATE = PROMPTS_DIR / "lsms_tier1_template.txt"
LSMS_NG_TIER2_TEMPLATE = PROMPTS_DIR / "lsms_tier2_template.txt"
LSMS_NG_TIER3_TEMPLATE = PROMPTS_DIR / "lsms_tier3_template.txt"
LSMS_NG_TIER4_TEMPLATE = PROMPTS_DIR / "lsms_tier4_template.txt"
FARMER_AGENT_SKILL = AGRIAGENT_DIR / "FARMER_AGENT_SKILL.md"

# Results
RESULTS_DIR = AGRIAGENT_DIR / "results"
RESULTS_LSMS_DIR = RESULTS_DIR / "lsms"
RESULTS_LSMS_COMBINED = RESULTS_LSMS_DIR / "combined"

# Canonical settings
SEED = 42
CLAUDE_CLI_CMD = ["claude", "-p", "--allowedTools", ""]
CODEX_CLI_CMD = ["npx", "@openai/codex", "exec", "--skip-git-repo-check",
                 "--full-auto", "--ephemeral"]
KIMI_CLI_CMD_ENV = {"DYLD_LIBRARY_PATH": "/opt/homebrew/opt/expat/lib"}
LLM_TIMEOUT_SEC = 300
LLM_RETRIES = 1

# Country configuration (active 4-country pilot)
COUNTRY_WAVES = {
    "Nigeria": 4,
    "Ethiopia": 3,
    "Tanzania": 3,
    "Malawi": 4,
}

# Filter constants (from data_quality_findings.md)
PLOT_AREA_MIN_HA = 0.05
PLOT_AREA_MAX_HA = 20.0
N_HA_CAP = 300.0  # kg N / ha — cap above this to NaN
YIELD_HA_CAP = 8000.0  # kg / ha — cap above this to NaN


def ensure_data_exists():
    """Fast check that the LSMS data directory is in place."""
    if not LSMS_DATA_DIR.is_dir():
        raise FileNotFoundError(
            f"LSMS data directory not found at {LSMS_DATA_DIR}. "
            f"Drop the harmonized .dta files into a folder named ' LSMS-ISA data' "
            f"(with a leading space) inside {AGRIAGENT_DIR}."
        )
    if not LSMS_PLOT_DTA.is_file():
        raise FileNotFoundError(f"Missing {LSMS_PLOT_DTA}")
    return True


if __name__ == "__main__":
    # Quick self-check when run directly
    print(f"REPO_ROOT         = {REPO_ROOT}")
    print(f"AGRIAGENT_DIR     = {AGRIAGENT_DIR}")
    print(f"LSMS_DATA_DIR     = {LSMS_DATA_DIR}  (exists: {LSMS_DATA_DIR.is_dir()})")
    print(f"LSMS_PLOT_DTA     = {LSMS_PLOT_DTA}  (exists: {LSMS_PLOT_DTA.is_file()})")
    print(f"LSMS_4C_PILOT_CSV = {LSMS_4C_PILOT_CSV}  (exists: {LSMS_4C_PILOT_CSV.is_file()})")
    print(f"LSMS_4C_TIER1     = {LSMS_4C_TIER1_TEMPLATE}  (exists: {LSMS_4C_TIER1_TEMPLATE.is_file()})")
    ensure_data_exists()
    print("\nAll required paths OK.")
