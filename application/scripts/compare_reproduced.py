from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ARCHIVED = ROOT / "data" / "analysis"
REPRODUCED = ROOT / "reproduced" / "analysis"


def compare_csv(filename: str, keys: list[str]) -> dict:
    archived = pd.read_csv(ARCHIVED / filename)
    reproduced = pd.read_csv(REPRODUCED / filename)
    archived = archived.sort_values(keys).reset_index(drop=True)
    reproduced = reproduced.sort_values(keys).reset_index(drop=True)
    if len(archived) != len(reproduced):
        raise AssertionError(f"{filename}: row count {len(reproduced)} != {len(archived)}")
    point_columns = [
        column for column in archived.columns.intersection(reproduced.columns)
        if column not in keys
        and not column.endswith(("_lo", "_hi"))
        and "bootstrap" not in column.lower()
    ]
    compared = []
    numeric_tolerances = {}
    for column in point_columns:
        if pd.api.types.is_numeric_dtype(archived[column]):
            left = archived[column].to_numpy(float)
            right = reproduced[column].to_numpy(float)
            # Three matched-model correlations show small retained numerical
            # differences (<7.3e-6 on this platform). Keep a narrow fitted-column
            # tolerance and independently require the reported3-decimal values.
            fitted = filename == "paper2_matched_baseline_results.csv" and column in {"matched_r", "matched_minus_agent", "matched_minus_rich"}
            atol = 1e-4 if fitted else 1e-9
            if fitted and not np.array_equal(np.round(left,3),np.round(right,3),equal_nan=True):
                raise AssertionError(f"{filename}:{column} changes the reported3-decimal values")
            numeric_tolerances[column] = atol
            if not np.allclose(left, right, rtol=0 if fitted else 1e-9, atol=atol, equal_nan=True):
                difference = float(np.nanmax(np.abs(left - right)))
                raise AssertionError(f"{filename}:{column} differs; max abs diff={difference}")
            compared.append(column)
        elif column in {"panel", "outcome"}:
            if archived[column].fillna("").tolist() != reproduced[column].fillna("").tolist():
                raise AssertionError(f"{filename}:{column} differs")
            compared.append(column)
    return {"file": filename, "rows": len(archived), "point_columns": compared, "absolute_tolerances": numeric_tolerances}


def compare_rich_baseline_json() -> dict:
    filename = "paper2_rival_confirmatory_results.json"
    archived = json.loads((ARCHIVED / filename).read_text(encoding="utf-8"))
    reproduced = json.loads((REPRODUCED / filename).read_text(encoding="utf-8"))
    archived = {row["country"]: row for row in archived}
    reproduced = {row["country"]: row for row in reproduced}
    if archived.keys() != reproduced.keys():
        raise AssertionError("Rich-input baseline country keys differ")
    for country in archived:
        left = archived[country]
        right = reproduced[country]
        if left["selected_model"] != right["selected_model"]:
            raise AssertionError(f"Rich-input selected model differs for {country}")
        for column in ["conventional_r", "agent_r", "r_gap"]:
            # Random-forest predictions can differ at the fifth decimal across
            # scikit-learn builds while preserving the reported three-decimal result.
            if not np.isclose(left[column], right[column], rtol=0, atol=1e-4):
                raise AssertionError(f"Rich-input {column} differs for {country}")
    return {"file": filename, "rows": len(archived), "point_columns": [
        "selected_model", "conventional_r", "agent_r", "r_gap"
    ]}


def compare_ablation_responses() -> dict:
    archived = pd.read_csv(
        ROOT / "data" / "model_outputs" / "country_label_ablation_predictions.csv"
    )
    archived = archived[archived["provider"].isin(["claude", "codex", "kimi"])].copy()
    archived["farmer_idx"] = archived["profile_key"].str.rsplit("_", n=1).str[-1].astype(int)
    reproduced = pd.read_csv(REPRODUCED / "paper2_country_label_ablation_responses.csv")
    merged = archived.merge(
        reproduced,
        on=["provider", "arm", "farmer_idx"],
        how="outer",
        suffixes=("_archived", "_reproduced"),
        validate="one_to_one",
        indicator=True,
    )
    if not (merged["_merge"] == "both").all():
        raise AssertionError("Ablation response keys differ")
    columns = ["nitrogen_kg_per_ha", "adoption", "observed_nitrogen_kg_per_ha"]
    for column in columns:
        if not np.allclose(
            merged[f"{column}_archived"], merged[f"{column}_reproduced"],
            rtol=0,
            atol=1e-12,
        ):
            raise AssertionError(f"Ablation responses differ: {column}")
    return {"file": "paper2_country_label_ablation_responses.csv", "rows": len(merged)}


def compare_matrix_responses() -> dict:
    archived = pd.read_csv(
        ROOT / "data" / "model_outputs" / "country_prior_matrix_predictions.csv"
    )
    archived = archived[archived["provider"].isin(["claude", "codex", "kimi"])].copy()
    archived["farmer_idx"] = archived["profile_key"].str.rsplit("_", n=1).str[-1].astype(int)
    reproduced = pd.read_csv(REPRODUCED / "paper2_country_prior_matrix_responses.csv")
    reproduced = reproduced[
        reproduced["provider"].isin(["claude", "codex", "kimi"])
    ].copy()
    merged = archived.merge(
        reproduced,
        on=["provider", "assigned_country", "farmer_idx"],
        how="outer",
        suffixes=("_archived", "_reproduced"),
        validate="one_to_one",
        indicator=True,
    )
    if not (merged["_merge"] == "both").all():
        raise AssertionError("Country-prior matrix response keys differ")
    for column in ["predicted_n", "predicted_adoption", "predicted_quantity_kg"]:
        if not np.allclose(
            merged[f"{column}_archived"], merged[f"{column}_reproduced"],
            rtol=0, atol=1e-12,
        ):
            raise AssertionError(f"Country-prior responses differ: {column}")
    return {"file": "paper2_country_prior_matrix_responses.csv", "rows": len(merged)}


def main() -> None:
    checks = [
        compare_csv("paper2_extension_confirmatory_metrics.csv", ["provider", "country"]),
        compare_rich_baseline_json(),
        compare_csv("paper2_matched_baseline_results.csv", ["country"]),
        compare_csv("paper2_population_consequence.csv", ["provider", "country"]),
        compare_csv(
            "paper2_country_prior_matrix_label_summary.csv",
            ["provider", "assigned_country"],
        ),
        compare_csv("paper2_country_prior_matrix_variance.csv", ["provider", "outcome"]),
        compare_csv("paper2_country_prior_matrix_components.csv", ["outcome"]),
        compare_csv("paper2_country_prior_matrix_ranking.csv", ["provider"]),
        compare_csv("paper2_observed_variable_consistency.csv", ["country"]),
        compare_csv("paper2_calibration_diagnostics.csv", ["country"]),
        compare_csv("paper2_influence_sensitivity.csv", ["method"]),
        compare_csv("paper2_semantic_audit.csv", ["scope", "experiment", "provider"]),
        compare_ablation_responses(),
        compare_matrix_responses(),
    ]
    report = {"status": "pass", "checks": checks}
    REPRODUCED.mkdir(parents=True, exist_ok=True)
    (REPRODUCED / "comparison_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Reproduced analyses match archived point estimates across {len(checks)} checks.")


if __name__ == "__main__":
    main()
