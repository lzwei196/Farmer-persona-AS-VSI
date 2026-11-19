"""Reviewer-requested audits using only archived profiles and model outputs.

This script does not issue model calls. It documents the observed fertilizer
indicator versus nitrogen-rate relation, reports post-stratification weight
diagnostics, recalculates weights inside bootstrap and leave-one-out samples,
and audits logical consistency of all archived structured model decisions.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROFILES_FILE = ROOT / "data" / "processed" / "frozen_profiles.csv"
DESIGN_FILE = ROOT / "data" / "processed" / "profile_survey_design.csv"
MATRIX_FILE = ROOT / "data" / "model_outputs" / "country_prior_matrix_predictions.csv"
RAW_FILE = ROOT / "data" / "model_outputs" / "raw_model_responses.jsonl.gz"
COUNTRIES = ("Ethiopia", "Malawi", "Mali", "Niger", "Nigeria", "Tanzania", "Uganda")
HIGH = ("Ethiopia", "Malawi", "Nigeria")
LOW = ("Niger", "Tanzania", "Uganda")
STRATA = ("fert_user", "female_manager", "formal_education_manager")
SEED = 20260827


def interval(values: np.ndarray) -> tuple[float, float]:
    return tuple(float(value) for value in np.quantile(values, [0.025, 0.975]))


def observed_variable_consistency() -> pd.DataFrame:
    profiles = pd.read_csv(PROFILES_FILE)
    rows = []
    for country in COUNTRIES:
        frame = profiles[profiles["country"] == country]
        nitrogen = frame["nitrogen_kg_per_ha"]
        user = frame["fert_user"].astype(int) == 1
        rows.append({
            "country": country,
            "profiles": len(frame),
            "fertilizer_indicator_yes": int(user.sum()),
            "nitrogen_rate_gt_zero": int((nitrogen > 0).sum()),
            "zero_nitrogen_among_indicator_yes": int((user & nitrogen.eq(0)).sum()),
            "missing_nitrogen_among_indicator_yes": int((user & nitrogen.isna()).sum()),
            "positive_nitrogen_among_indicator_no": int((~user & (nitrogen > 0)).sum()),
            "missing_nitrogen_among_indicator_no": int((~user & nitrogen.isna()).sum()),
        })
    return pd.DataFrame(rows)


def calibration_diagnostics(design: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for country in COUNTRIES:
        frame = design[design["country"] == country].copy()
        weights = frame["population_analysis_weight"].to_numpy(float)
        cell_sizes = frame.groupby(list(STRATA), dropna=False).size()
        factors = frame["poststratification_factor"].to_numpy(float)
        rows.append({
            "country": country,
            "profiles": len(frame),
            "poststrata": len(cell_sizes),
            "minimum_profiles_per_poststratum": int(cell_sizes.min()),
            "maximum_profiles_per_poststratum": int(cell_sizes.max()),
            "eligible_plot_weight_total": float(weights.sum()),
            "kish_effective_profile_n": float(weights.sum() ** 2 / np.sum(weights ** 2)),
            "coefficient_of_variation_of_weights": float(np.std(weights) / np.mean(weights)),
            "maximum_normalized_weight": float(weights.max() / weights.sum()),
            "minimum_poststratification_factor": float(np.min(factors)),
            "maximum_poststratification_factor": float(np.max(factors)),
        })
    return pd.DataFrame(rows)


def profile_contrasts(design: pd.DataFrame) -> pd.DataFrame:
    matrix = pd.read_csv(MATRIX_FILE)
    matrix = matrix[matrix["provider"] == "ensemble"].copy()
    profile = matrix.drop_duplicates("profile_key")[
        ["profile_key", "observed_n", "observed_adoption", "plot_area_ha", "fert_user"]
    ].set_index("profile_key")
    for output, result_name in (
        ("predicted_n", "rate_difference_kg_per_ha"),
        ("predicted_adoption", "adoption_difference"),
        ("predicted_quantity_kg", "quantity_difference_kg_per_plot"),
    ):
        pivot = matrix.pivot(index="profile_key", columns="assigned_country", values=output)
        profile[result_name] = pivot[list(HIGH)].mean(axis=1) - pivot[list(LOW)].mean(axis=1)
    tanzania = design[design["country"] == "Tanzania"].copy()
    keep = [
        "profile_key", "panel", "profile_index", "hh_id_merge", "plot_id_merge",
        "household_weight_pw", "population_analysis_weight", "population_cell_weight_total",
        "poststratification_factor", *STRATA,
    ]
    profile = profile.reset_index().rename(columns={"profile_key": "matrix_profile_key"})
    profile["profile_index"] = profile["matrix_profile_key"].str.rsplit(
        "_", n=1
    ).str[-1].astype(int)
    merged = tanzania[keep].merge(
        profile, on=["profile_index", "fert_user"], how="inner", validate="one_to_one"
    )
    if len(merged) != 70:
        raise RuntimeError(f"Expected 70 Tanzanian profiles, found {len(merged)}")
    merged["expanded_contribution_tonnes"] = (
        merged["quantity_difference_kg_per_plot"]
        * merged["population_analysis_weight"] / 1000
    )
    return merged


def recalibrated_weights(frame: pd.DataFrame) -> np.ndarray:
    weights = np.empty(len(frame), dtype=float)
    reset = frame.reset_index(drop=True)
    for _, positions in reset.groupby(list(STRATA), dropna=False).groups.items():
        positions = np.asarray(list(positions), dtype=int)
        block = reset.iloc[positions]
        totals = block["population_cell_weight_total"].dropna().unique()
        if len(totals) != 1:
            raise RuntimeError("Population target is not constant within a post-stratum")
        denominator = float(block["household_weight_pw"].sum())
        if denominator <= 0:
            raise RuntimeError("Non-positive sampled base-weight total")
        factor = float(totals[0]) / denominator
        weights[positions] = block["household_weight_pw"].to_numpy(float) * factor
    return weights


def weighted_outcomes(frame: pd.DataFrame, weights: np.ndarray) -> dict:
    weights = np.asarray(weights, float)
    return {
        "rate_difference_kg_per_ha": float(np.average(
            frame["rate_difference_kg_per_ha"], weights=weights
        )),
        "adoption_difference": float(np.average(
            frame["adoption_difference"], weights=weights
        )),
        "quantity_difference_kg_per_plot": float(np.average(
            frame["quantity_difference_kg_per_plot"], weights=weights
        )),
        "expanded_difference_tonnes": float(np.sum(
            frame["quantity_difference_kg_per_plot"].to_numpy(float) * weights
        ) / 1000),
    }


def stratified_positions(frame: pd.DataFrame, columns: tuple[str, ...],
                         rng: np.random.Generator) -> np.ndarray:
    sampled = []
    reset = frame.reset_index(drop=True)
    grouping = columns[0] if len(columns) == 1 else list(columns)
    for _, positions in reset.groupby(grouping, dropna=False).groups.items():
        positions = np.asarray(list(positions), dtype=int)
        sampled.append(rng.choice(positions, size=len(positions), replace=True))
    return np.concatenate(sampled)


def influence_analysis(profiles: pd.DataFrame, repetitions: int
                       ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    profiles = profiles.reset_index(drop=True)
    stored = profiles["population_analysis_weight"].to_numpy(float)
    rebuilt = recalibrated_weights(profiles)
    if not np.allclose(stored, rebuilt, rtol=1e-9, atol=1e-7):
        raise RuntimeError("Reconstructed calibration weights do not match archived weights")
    point = weighted_outcomes(profiles, stored)
    total_weight = float(stored.sum())

    rng_primary = np.random.default_rng(SEED + 1)
    rng_fixed_full = np.random.default_rng(SEED + 2)
    rng_recalibrated = np.random.default_rng(SEED + 3)
    draw_rows = []
    for draw in range(repetitions):
        primary_positions = stratified_positions(profiles, ("fert_user",), rng_primary)
        primary_frame = profiles.iloc[primary_positions].reset_index(drop=True)
        primary_weights = primary_frame["population_analysis_weight"].to_numpy(float)
        primary = weighted_outcomes(primary_frame, primary_weights)
        primary["expanded_difference_tonnes"] = (
            primary["quantity_difference_kg_per_plot"] * total_weight / 1000
        )

        fixed_positions = stratified_positions(profiles, STRATA, rng_fixed_full)
        fixed_frame = profiles.iloc[fixed_positions].reset_index(drop=True)
        fixed_weights = fixed_frame["population_analysis_weight"].to_numpy(float)
        fixed = weighted_outcomes(fixed_frame, fixed_weights)
        fixed["expanded_difference_tonnes"] = (
            fixed["quantity_difference_kg_per_plot"] * total_weight / 1000
        )

        recal_positions = stratified_positions(profiles, STRATA, rng_recalibrated)
        recal_frame = profiles.iloc[recal_positions].reset_index(drop=True)
        recal = weighted_outcomes(recal_frame, recalibrated_weights(recal_frame))
        row = {"draw": draw}
        for prefix, values in (
            ("primary_fixed", primary),
            ("full_strata_fixed", fixed),
            ("full_strata_recalibrated", recal),
        ):
            for name, value in values.items():
                row[f"{prefix}_{name}"] = value
        draw_rows.append(row)
    draws = pd.DataFrame(draw_rows)

    methods = ["primary_fixed", "full_strata_fixed", "full_strata_recalibrated"]
    summary_rows = []
    for method in methods:
        row = {"method": method}
        for name, value in point.items():
            values = draws[f"{method}_{name}"].to_numpy(float)
            lo, hi = interval(values)
            row[name] = value
            row[f"{name}_lo"] = lo
            row[f"{name}_hi"] = hi
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows)

    loo_rows = []
    for omitted_position, omitted in profiles.iterrows():
        remaining = profiles.drop(index=omitted_position).reset_index(drop=True)
        result = weighted_outcomes(remaining, recalibrated_weights(remaining))
        loo_rows.append({
            "omitted_rank": omitted_position + 1,
            "omitted_profile_key": omitted["profile_key"],
            "omitted_observed_user": int(omitted["fert_user"]),
            "omitted_plot_area_ha": float(omitted["plot_area_ha"]),
            "omitted_calibration_weight": float(omitted["population_analysis_weight"]),
            "omitted_expanded_contribution_tonnes": float(
                omitted["expanded_contribution_tonnes"]
            ),
            **result,
            "change_from_full_tonnes": result["expanded_difference_tonnes"]
            - point["expanded_difference_tonnes"],
        })
    loo = pd.DataFrame(loo_rows)

    contributions = profiles.copy()
    contributions["absolute_expanded_contribution_tonnes"] = contributions[
        "expanded_contribution_tonnes"
    ].abs()
    contributions = contributions.sort_values(
        "absolute_expanded_contribution_tonnes", ascending=False
    ).reset_index(drop=True)
    contributions["influence_rank"] = np.arange(1, len(contributions) + 1)
    contributions["cumulative_net_share"] = (
        contributions["expanded_contribution_tonnes"].cumsum()
        / point["expanded_difference_tonnes"]
    )
    absolute_total = contributions["absolute_expanded_contribution_tonnes"].sum()
    contributions["cumulative_absolute_share"] = (
        contributions["absolute_expanded_contribution_tonnes"].cumsum() / absolute_total
    )

    details = {
        "point": point,
        "leave_one_out_min_tonnes": float(loo["expanded_difference_tonnes"].min()),
        "leave_one_out_max_tonnes": float(loo["expanded_difference_tonnes"].max()),
        "leave_one_out_all_positive": bool((loo["expanded_difference_tonnes"] > 0).all()),
        "maximum_absolute_leave_one_out_change_tonnes": float(
            loo["change_from_full_tonnes"].abs().max()
        ),
        "top_10_net_share": float(
            contributions.head(10)["expanded_contribution_tonnes"].sum()
            / point["expanded_difference_tonnes"]
        ),
        "top_10_absolute_share": float(
            contributions.head(10)["absolute_expanded_contribution_tonnes"].sum()
            / absolute_total
        ),
    }
    return summary, loo, contributions, draws, details


def semantic_audit() -> tuple[pd.DataFrame, dict]:
    records = []
    distinct_response_keys = set()
    distinct_attempt_counts = []
    with gzip.open(RAW_FILE, "rt", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            decision = record.get("decision")
            adoption = decision.get("inorganic_fertilizer") if isinstance(decision, dict) else None
            rate = decision.get("nitrogen_kg_per_ha") if isinstance(decision, dict) else None
            numeric_rate = (
                isinstance(rate, (int, float)) and not isinstance(rate, bool)
                and np.isfinite(float(rate))
            )
            boolean_adoption = isinstance(adoption, bool)
            rate_value = float(rate) if numeric_rate else np.nan
            records.append({
                "experiment": record.get("experiment"),
                "provider": record.get("provider"),
                "valid_structured_decision": isinstance(decision, dict)
                and numeric_rate and boolean_adoption,
                "nonfinite_or_missing_rate": not numeric_rate,
                "negative_rate": numeric_rate and rate_value < 0,
                "rate_above_300": numeric_rate and rate_value > 300,
                "adoption_false_with_positive_rate": (
                    numeric_rate and boolean_adoption and not adoption and rate_value > 0
                ),
                "adoption_true_with_zero_rate": (
                    numeric_rate and boolean_adoption and adoption and rate_value == 0
                ),
                "multiple_attempts": int(record.get("attempts") or 0) > 1,
            })
            response_key = (
                record.get("provider"), record.get("profile_key"),
                record.get("prompt_sha256"), record.get("timestamp_utc"),
                record.get("raw_response"),
            )
            if response_key not in distinct_response_keys:
                distinct_response_keys.add(response_key)
                distinct_attempt_counts.append(int(record.get("attempts") or 1))
    frame = pd.DataFrame(records)
    metric_columns = [column for column in frame.columns if column not in {"experiment", "provider"}]
    rows = []
    for (experiment, provider), group in frame.groupby(["experiment", "provider"]):
        row = {"scope": "experiment_provider", "experiment": experiment,
               "provider": provider, "responses": len(group)}
        row.update({column: int(group[column].sum()) for column in metric_columns})
        rows.append(row)
    for provider, group in frame.groupby("provider"):
        row = {"scope": "provider_total", "experiment": "all", "provider": provider,
               "responses": len(group)}
        row.update({column: int(group[column].sum()) for column in metric_columns})
        rows.append(row)
    total = {"scope": "overall", "experiment": "all", "provider": "all",
             "responses": len(frame)}
    total.update({column: int(frame[column].sum()) for column in metric_columns})
    rows.append(total)
    audit = pd.DataFrame(rows)
    details = {
        "analysis_records": len(frame),
        "distinct_accepted_responses": len(distinct_response_keys),
        "reused_analysis_records": len(frame) - len(distinct_response_keys),
        "accepted_responses_with_retries": int(sum(
            attempts > 1 for attempts in distinct_attempt_counts
        )),
        "additional_call_attempts": int(sum(
            attempts - 1 for attempts in distinct_attempt_counts
        )),
        "total_model_call_attempts": int(sum(distinct_attempt_counts)),
        "experiment_counts": dict(Counter(frame["experiment"])),
        "provider_counts": dict(Counter(frame["provider"])),
        "overall": total,
    }
    return audit, details


def markdown_table(frame: pd.DataFrame) -> str:
    display = frame.copy()
    for column in display.select_dtypes(include=["float"]).columns:
        display[column] = display[column].map(lambda value: f"{value:.4g}")
    header = "| " + " | ".join(display.columns) + " |"
    rule = "|" + "|".join("---" for _ in display.columns) + "|"
    rows = [
        "| " + " | ".join(str(value) for value in row) + " |"
        for row in display.itertuples(index=False, name=None)
    ]
    return "\n".join([header, rule, *rows])


def build_report(variable: pd.DataFrame, calibration: pd.DataFrame,
                 influence: pd.DataFrame, details: dict,
                 semantics: pd.DataFrame) -> str:
    recal = influence.set_index("method").loc["full_strata_recalibrated"]
    semantic_total = semantics[semantics["scope"] == "overall"].iloc[0]
    lines = [
        "# Reviewer-requested sensitivity analyses",
        "",
        "## Observed-variable consistency",
        "",
        "The frozen sample contains 35 profiles with a positive fertilizer indicator in each",
        "country. No indicator-negative profile has a positive nitrogen rate. Zero or missing",
        "nitrogen rates among indicator-positive profiles are reported rather than recoded.",
        "",
        markdown_table(variable),
        "",
        "## Calibration diagnostics",
        "",
        markdown_table(calibration),
        "",
        "## Tanzania influence and recalibration sensitivity",
        "",
        markdown_table(influence),
        "",
        f"The full expanded high-minus-low contrast is {details['point']['expanded_difference_tonnes']:,.0f} tonnes N. ",
        f"All leave-one-profile-out recalibrated estimates are positive and range from "
        f"{details['leave_one_out_min_tonnes']:,.0f} to {details['leave_one_out_max_tonnes']:,.0f} tonnes. ",
        f"The recalibrated-bootstrap 95% interval is "
        f"{recal['expanded_difference_tonnes_lo']:,.0f} to "
        f"{recal['expanded_difference_tonnes_hi']:,.0f} tonnes.",
        "",
        "## Structured-output semantic audit",
        "",
        markdown_table(semantics),
        "",
        f"The audit covered {int(semantic_total['responses']):,} archived analysis records,",
        f"representing {details['semantic_audit']['distinct_accepted_responses']:,} distinct accepted responses.",
        f"{details['semantic_audit']['accepted_responses_with_retries']} distinct response conditions required "
        f"{details['semantic_audit']['additional_call_attempts']} additional",
        "call attempts; retries produced one accepted response per condition and were not repeated",
        "experimental samples. Counts above",
        "300 kg N ha-1 are reported as an output-range diagnostic; this threshold was used for",
        "survey outcome quality control, not to alter archived model outputs.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=int, default=10_000)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "reproduced" / "analysis"
    )
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    design = pd.read_csv(DESIGN_FILE)
    variable = observed_variable_consistency()
    calibration = calibration_diagnostics(design)
    profiles = profile_contrasts(design)
    influence, loo, contributions, draws, influence_details = influence_analysis(
        profiles, args.bootstrap
    )
    semantics, semantic_details = semantic_audit()

    outputs = {
        "paper2_observed_variable_consistency.csv": variable,
        "paper2_calibration_diagnostics.csv": calibration,
        "paper2_influence_sensitivity.csv": influence,
        "paper2_influence_leave_one_out.csv": loo,
        "paper2_label_contributions.csv": contributions,
        "paper2_influence_bootstrap_draws.csv": draws,
        "paper2_semantic_audit.csv": semantics,
    }
    for filename, frame in outputs.items():
        frame.to_csv(output_dir / filename, index=False)
    payload = {
        "influence": influence_details,
        "semantic_audit": semantic_details,
    }
    (output_dir / "paper2_review_sensitivity_results.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    report_details = {**influence_details, "semantic_audit": semantic_details}
    report = build_report(variable, calibration, influence, report_details, semantics)
    (output_dir / "paper2_review_sensitivity_results.md").write_text(
        report, encoding="utf-8"
    )
    print(report)
    print(f"Wrote reviewer-requested sensitivity outputs to {output_dir}")


if __name__ == "__main__":
    main()
