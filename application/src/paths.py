from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LSMS_DIR = DATA_DIR / "profiles"
RAW_LSMS_DIR = Path(os.environ.get("LSMS_DATA_DIR", DATA_DIR / "raw" / "lsms_isa"))
PROMPTS_DIR = ROOT / "prompts"
RESULTS_DIR = ROOT / "results"

ORIGINAL_SAMPLE_FILE = LSMS_DIR / "lsms_4country_full.csv"
EXTENSION_SAMPLE_FILE = LSMS_DIR / "lsms_extension_3country.csv"
COUNTRY_FILTERS = ["Ethiopia", "Malawi", "Nigeria", "Tanzania"]
EXTENSION_COUNTRIES = ["Mali", "Niger", "Uganda"]

LSMS_PLOT_DTA = RAW_LSMS_DIR / "Plot_dataset.dta"
LSMS_4C_FULL_CSV = ORIGINAL_SAMPLE_FILE
PLOT_AREA_MIN_HA = 0.05
PLOT_AREA_MAX_HA = 20
N_HA_CAP = 300
YIELD_HA_CAP = 8000

def ensure_data_exists():
    if not LSMS_PLOT_DTA.exists():
        raise FileNotFoundError(f"Supply the cited harmonized Plot_dataset.dta via LSMS_DATA_DIR: {LSMS_PLOT_DTA}")

LSMS_4C_TIER1_TEMPLATE = PROMPTS_DIR / "main" / "lsms_4country_tier1_template.txt"
