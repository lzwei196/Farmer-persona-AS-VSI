from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from scipy.stats import pearsonr

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EXPECTED = {
    "high_minus_low_kg_n_ha": 17.565079365079363,
    "weighted_kg_n_per_plot": 19.459027251172994,
    "expanded_tonnes_n": 226464.34772335505,
    "label_prevalence_correlation": 0.9344029850719262,
    "farmer_correlation_min": -0.13209559691163397,
    "farmer_correlation_max": 0.12011654382995837,
}


def calculate() -> dict[str, float]:
    matrix = pd.read_csv(DATA / "model_outputs" / "country_prior_matrix_predictions.csv")
    prevalence = pd.read_csv(DATA / "processed" / "paper2_country_wave_prevalence.csv")

    ensemble = matrix[matrix["provider"] == "ensemble"].copy()
    label_means = ensemble.groupby("assigned_country", as_index=False)["predicted_n"].mean()
    prevalence_col = next(
        col for col in prevalence.columns if "preval" in col.lower() and col != "country"
    )
    prevalence_country = prevalence.groupby("country", as_index=False)[prevalence_col].mean()
    merged = label_means.merge(
        prevalence_country, left_on="assigned_country", right_on="country", how="inner"
    )

    high = ["Ethiopia", "Malawi", "Nigeria"]
    low = ["Niger", "Tanzania", "Uganda"]
    contrasts = ensemble[ensemble["assigned_country"].isin(high + low)].copy()
    contrasts["label_group"] = contrasts["assigned_country"].map(
        lambda value: "high" if value in high else "low"
    )
    profile_values = contrasts.groupby(["profile_key", "label_group"], as_index=False).agg(
        predicted_n=("predicted_n", "mean"),
        predicted_quantity_kg=("predicted_quantity_kg", "mean"),
        population_analysis_weight=("population_analysis_weight", "first"),
    )
    wide = profile_values.pivot(index="profile_key", columns="label_group")
    n_contrast = wide["predicted_n"]["high"] - wide["predicted_n"]["low"]
    quantity_contrast = (
        wide["predicted_quantity_kg"]["high"]
        - wide["predicted_quantity_kg"]["low"]
    )
    weights = wide["population_analysis_weight"]["high"]
    high_low = float(n_contrast.mean())
    weighted = float((quantity_contrast * weights).sum() / weights.sum())
    tonnes = float((quantity_contrast * weights).sum() / 1000)

    farmer_correlations = []
    for _, group in ensemble.groupby("assigned_country"):
        farmer_correlations.append(float(pearsonr(group["observed_n"], group["predicted_n"]).statistic))

    return {
        "high_minus_low_kg_n_ha": float(high_low),
        "weighted_kg_n_per_plot": weighted,
        "expanded_tonnes_n": tonnes,
        "label_prevalence_correlation": float(
            pearsonr(merged[prevalence_col], merged["predicted_n"]).statistic
        ),
        "farmer_correlation_min": min(farmer_correlations),
        "farmer_correlation_max": max(farmer_correlations),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    values = calculate()
    print(json.dumps(values, indent=2))
    if args.check:
        for key, expected in EXPECTED.items():
            if abs(values[key] - expected) > max(1e-8, abs(expected) * 1e-8):
                raise SystemExit(f"Mismatch for {key}: {values[key]} != {expected}")
        print("All headline values match the archived release.")


if __name__ == "__main__":
    main()
