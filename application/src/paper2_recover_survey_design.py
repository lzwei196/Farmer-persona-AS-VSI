"""Recover LSMS household weights and design IDs for Paper 2's frozen profiles.

The harmonized Plot dataset already contains ``pw`` (labelled "Household weight"),
``strataid``, and enumeration-area IDs, but the frozen 70-profile CSVs omitted
them. This script matches each frozen row back to the harmonized plot record and
constructs post-stratification weights for the deliberately adopter-balanced
evaluation samples.

It never modifies frozen profile files or experiment manifests. This source-data
reconstruction requires the cited harmonized Plot_dataset.dta. Outputs include
source survey identifiers and belong only in ignored reproduced/, not a public
upload. The archived deidentified design table remains the canonical public input.

Usage
-----
    python src/paper2_recover_survey_design.py --plot-data /path/to/Plot_dataset.dta
"""
from __future__ import annotations

from pathlib import Path
import sys
import argparse

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = None
ORIGINAL = ROOT / "data/profiles/lsms_4country_full.csv"
EXTENSION = ROOT / "data/profiles/lsms_extension_3country.csv"
OUT_DIR = ROOT / "reproduced/survey_design"
OUT_DESIGN = OUT_DIR / "profile_survey_design.csv"
OUT_TARGETS = OUT_DIR / "paper2_country_wave_population_targets.csv"
OUT_PREVALENCE_SENSITIVITY = OUT_DIR / "paper2_country_wave_prevalence_weighted_sensitivity.csv"
COUNTRY_WAVES = {
    "Nigeria": 4, "Ethiopia": 3, "Tanzania": 3, "Malawi": 4,
    "Mali": 2, "Niger": 1, "Uganda": 8,
}
STRATA_COLUMNS = ("fert_user", "female_manager", "formal_education_manager")

sys.path.insert(0, str(ROOT / "src"))
import lsms_utils as original_builder  # noqa: E402
import build_lsms_extension_sample as extension_builder  # noqa: E402


def normalize_id(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    return text[:-2] if text.endswith(".0") else text


def exact_or_close(series: pd.Series, value, tolerance=1e-7) -> pd.Series:
    if pd.isna(value):
        return series.isna()
    if pd.api.types.is_numeric_dtype(series):
        return np.isclose(series.astype(float), float(value), rtol=0, atol=tolerance,
                          equal_nan=False)
    return series.astype(str) == str(value)


def select_raw_record(raw: pd.DataFrame, row: pd.Series) -> pd.Series:
    # Public profile files use pseudonyms. Match the frozen measured fields
    # against the supplied source rather than assuming original IDs were released.
    candidates = raw[(raw.country == row.country)
                     & (raw.wave.astype(float) == float(row.wave))].copy()
    fields = ["plot_area_GPS", "nitrogen_kg", "farm_size", "age_manager", "main_crop",
              "female_manager", "formal_education_manager", "plot_owned", "intercropped",
              "harvest_kg", "total_family_labor_days", "total_hired_labor_days",
              "dist_popcenter", "elevation"]
    for column in fields:
        if column not in row or column not in candidates:
            continue
        values = candidates[column]
        if isinstance(values.dtype, pd.CategoricalDtype) or values.dtype == object:
            nonmissing = set(values.dropna().astype(str).unique())
            if nonmissing <= {"Yes", "No"}:
                values = values.astype(object).map({"Yes": 1.0, "No": 0.0})
        matched = candidates[exact_or_close(values, row[column])]
        if matched.empty:
            raise RuntimeError(f"Frozen measured-field mismatch: {row.country}, profile {row.get('profile_index')}, {column}")
        candidates = matched
    design = candidates[["pw", "strataid", "ea_id_merge", "ea_id_obs", "hh_id_merge", "plot_id_merge", "season"]].drop_duplicates()
    if len(design) != 1:
        raise RuntimeError(f"Source match not unique for {row.country} profile {row.get('profile_index')}: {len(design)} distinct design records")
    return candidates.iloc[0]


def load_samples() -> pd.DataFrame:
    frames = []
    for panel, path in (("original_discovery", ORIGINAL),
                        ("prospective_extension_v2", EXTENSION)):
        frame = pd.read_csv(path).copy()
        frame["panel"] = panel
        frame["profile_index"] = frame.index.astype(int)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def prepare_pool(raw: pd.DataFrame, country: str) -> pd.DataFrame:
    wave = COUNTRY_WAVES[country]
    if country in {"Nigeria", "Ethiopia", "Tanzania", "Malawi"}:
        pool = original_builder.load_country(raw, country, wave)
        eligible = pool[
            pool["female_manager"].notna()
            & pool["formal_education_manager"].notna()
            & pool["age_manager"].notna()
            & pool["main_crop"].notna()
            & pool["nitrogen_kg"].notna()
        ].copy()
    else:
        pool = extension_builder.prep(raw, country, wave)
        eligible = pool[
            pool["female_manager"].notna()
            & pool["formal_education_manager"].notna()
            & pool["age_manager"].notna()
            & pool["main_crop"].notna()
            & pool["nitrogen_kg"].notna()
            & pool["nitrogen_kg_per_ha"].notna()
        ].copy()
    eligible = eligible[
        eligible["pw"].notna() & np.isfinite(eligible["pw"]) & (eligible["pw"] > 0)
    ].copy()
    for column in STRATA_COLUMNS:
        eligible[column] = eligible[column].astype(int)
    return eligible


def population_targets(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    target_rows = []
    cell_rows = []
    for country in COUNTRY_WAVES:
        pool = prepare_pool(raw, country)
        def weighted_mean(values: pd.Series) -> float:
            values = values.astype(float)
            ok = np.isfinite(values) & np.isfinite(pool["pw"]) & (pool["pw"] > 0)
            return float(np.average(values[ok], weights=pool.loc[ok, "pw"]))
        target_rows.append({
            "country": country,
            "wave": COUNTRY_WAVES[country],
            "eligible_plots": len(pool),
            "household_weight_coverage": float(pool["pw"].notna().mean()),
            "unweighted_fert_user_prevalence": float(pool["fert_user"].mean()),
            "survey_weighted_fert_user_prevalence": float(
                np.average(pool["fert_user"], weights=pool["pw"])),
            "survey_weighted_mean_n_kg_per_ha": weighted_mean(pool["nitrogen_kg_per_ha"]),
            "survey_weighted_mean_n_kg_per_plot": weighted_mean(
                pool["nitrogen_kg_per_ha"] * pool["plot_area_GPS"]),
        })
        grouped = pool.groupby(list(STRATA_COLUMNS), dropna=False)
        for stratum, frame in grouped:
            cell_rows.append({
                "country": country,
                **dict(zip(STRATA_COLUMNS, stratum)),
                "population_cell_n": len(frame),
                "population_cell_weight_total": float(frame["pw"].sum()),
            })
    return pd.DataFrame(target_rows), pd.DataFrame(cell_rows)


def weighted_prevalence_sensitivity(raw: pd.DataFrame) -> pd.DataFrame:
    """Match the frozen broad prevalence universe, adding household survey weights.

    The frozen primary ordering file uses every country-wave plot with GPS area in
    [0.05, 20] ha and a nonmissing inorganic-fertilizer response. This sensitivity
    uses that identical universe and definition, then applies ``pw``.
    """
    rows = []
    for country, wave in COUNTRY_WAVES.items():
        frame = raw[(raw["country"] == country)
                    & (raw["wave"].astype(float) == float(wave))
                    & (raw["plot_area_GPS"] >= 0.05)
                    & (raw["plot_area_GPS"] <= 20)].copy()
        response = frame["inorganic_fertilizer"]
        if pd.api.types.is_numeric_dtype(response):
            inorganic = pd.to_numeric(response, errors="coerce")
        else:
            inorganic = response.astype(object).map({"Yes": 1.0, "No": 0.0})
        valid = inorganic.notna() & frame["pw"].notna() & np.isfinite(frame["pw"]) & (frame["pw"] > 0)
        if not valid.any():
            raise RuntimeError(f"No weighted inorganic-fertilizer records for {country}")
        rows.append({
            "country": country,
            "wave": wave,
            "area_filtered_plots": int(len(frame)),
            "weighted_nonmissing_inorganic_fertilizer": int(valid.sum()),
            "unweighted_fertilizer_prevalence_check": float(inorganic[valid].mean()),
            "survey_weighted_fertilizer_prevalence": float(
                np.average(inorganic[valid].astype(float), weights=frame.loc[valid, "pw"])),
            "definition": (
                "inorganic_fertilizer Yes among nonmissing plots with GPS area 0.05-20 ha; "
                "weighted by household survey weight pw"
            ),
        })
    return pd.DataFrame(rows)


def main() -> None:
    global RAW, ORIGINAL, EXTENSION, OUT_DIR, OUT_DESIGN, OUT_TARGETS, OUT_PREVALENCE_SENSITIVITY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plot-data", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    RAW = args.plot_data
    ORIGINAL = args.repo / "data/profiles/lsms_4country_full.csv"
    EXTENSION = args.repo / "data/profiles/lsms_extension_3country.csv"
    OUT_DIR = args.output_dir
    OUT_DESIGN = OUT_DIR / "profile_survey_design.csv"
    OUT_TARGETS = OUT_DIR / "paper2_country_wave_population_targets.csv"
    OUT_PREVALENCE_SENSITIVITY = OUT_DIR / "paper2_country_wave_prevalence_weighted_sensitivity.csv"
    raw = pd.read_stata(RAW, convert_categoricals=True)
    samples = load_samples()
    design_rows = []
    for row in samples.itertuples(index=False):
        series = pd.Series(row._asdict())
        match = select_raw_record(raw, series)
        design_rows.append({
            "panel": series["panel"],
            "profile_index": int(series["profile_index"]),
            "country": series["country"],
            "wave": int(float(series["wave"])),
            "hh_id_merge": normalize_id(match["hh_id_merge"]),
            "plot_id_merge": normalize_id(match["plot_id_merge"]),
            "season": match["season"],
            "household_weight_pw": float(match["pw"]),
            "strataid": match["strataid"],
            "ea_id_merge": normalize_id(match["ea_id_merge"]),
            "ea_id_obs": normalize_id(match["ea_id_obs"]),
            "fert_user": int(series["fert_user"]),
            "female_manager": int(series["female_manager"]),
            "formal_education_manager": int(series["formal_education_manager"]),
        })
    design = pd.DataFrame(design_rows)
    if len(design) != 490 or design.duplicated(["panel", "profile_index"]).any():
        raise RuntimeError("Recovered design rows do not match the 490 frozen profiles")

    targets, cells = population_targets(raw)
    prevalence_sensitivity = weighted_prevalence_sensitivity(raw)
    design = design.merge(
        cells,
        on=["country", *STRATA_COLUMNS],
        how="left",
        validate="many_to_one",
    )
    design["sample_cell_weight_total"] = design.groupby(
        ["panel", "country", *STRATA_COLUMNS])["household_weight_pw"].transform("sum")
    design["poststratification_factor"] = (
        design["population_cell_weight_total"] / design["sample_cell_weight_total"])
    design["population_analysis_weight"] = (
        design["household_weight_pw"] * design["poststratification_factor"])
    if design[["population_cell_weight_total", "population_analysis_weight"]].isna().any().any():
        raise RuntimeError("At least one sampled post-stratum is absent from the target population")

    # Audit whether any eligible population cell is missing from a country's frozen sample.
    sampled_cells = design[["country", *STRATA_COLUMNS]].drop_duplicates()
    coverage = cells.merge(sampled_cells.assign(sampled=True),
                           on=["country", *STRATA_COLUMNS], how="left")
    targets = targets.merge(
        coverage.groupby("country").agg(
            population_poststrata=("population_cell_n", "size"),
            covered_poststrata=("sampled", "count"),
            uncovered_population_weight=(
                "population_cell_weight_total",
                lambda values: float(values[coverage.loc[values.index, "sampled"].isna()].sum()),
            ),
        ).reset_index(),
        on="country", how="left",
    )
    targets["poststrata_complete"] = targets["population_poststrata"] == targets["covered_poststrata"]

    OUT_DESIGN.parent.mkdir(parents=True, exist_ok=True)
    design.to_csv(OUT_DESIGN, index=False)
    targets.to_csv(OUT_TARGETS, index=False)
    prevalence_sensitivity.to_csv(OUT_PREVALENCE_SENSITIVITY, index=False)
    print(targets.to_string(index=False))
    print(f"Wrote {OUT_DESIGN} ({len(design)} frozen profiles)")
    print(f"Wrote {OUT_TARGETS}")
    print(f"Wrote {OUT_PREVALENCE_SENSITIVITY}")


if __name__ == "__main__":
    main()
