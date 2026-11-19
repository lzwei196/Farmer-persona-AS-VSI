"""Profile-level diagnostics for the Paper 2 country-label contrast."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "reproduced" / "historical"
OUT = ROOT / "手稿" / "figures"

HIGH_LABELS = ["Ethiopia", "Malawi", "Nigeria"]
LOW_LABELS = ["Niger", "Tanzania", "Uganda"]
PROFILE_FIELDS = [
    "country", "main_crop", "plot_area_GPS", "farm_size", "age_manager",
    "female_manager", "formal_education_manager", "fert_user",
    "nitrogen_kg_per_ha", "intercropped", "plot_owned",
]


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    valid = values.notna() & weights.notna()
    if not valid.any():
        return np.nan
    return float(np.average(values[valid], weights=weights[valid]))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    responses = pd.read_csv(ANALYSIS / "paper2_country_prior_matrix_responses.csv")
    profiles = pd.read_csv(ROOT / "data" / "lsms" / "lsms_4country_full.csv")
    profiles = profiles.reset_index(names="farmer_idx")
    profiles = profiles[["farmer_idx", *PROFILE_FIELDS]]

    profile_provider = (
        responses.assign(
            label_group=np.select(
                [responses["assigned_country"].isin(HIGH_LABELS),
                 responses["assigned_country"].isin(LOW_LABELS)],
                ["high", "low"],
                default="middle",
            )
        )
        .query("label_group in ['high', 'low']")
        .groupby(["farmer_idx", "provider", "label_group"], as_index=False)
        .agg(
            predicted_n=("predicted_n", "mean"),
            predicted_adoption=("predicted_adoption", "mean"),
            predicted_quantity_kg=("predicted_quantity_kg", "mean"),
            population_analysis_weight=("population_analysis_weight", "first"),
            observed_n=("observed_n", "first"),
            observed_adoption=("observed_adoption", "first"),
            plot_area_ha=("plot_area_ha", "first"),
        )
    )
    wide_provider = profile_provider.pivot(
        index=["farmer_idx", "provider"],
        columns="label_group",
        values=["predicted_n", "predicted_adoption", "predicted_quantity_kg"],
    )
    wide_provider.columns = [f"{metric}_{group}" for metric, group in wide_provider.columns]
    wide_provider = wide_provider.reset_index()
    meta = (
        profile_provider.groupby(["farmer_idx", "provider"], as_index=False)
        .agg(
            population_analysis_weight=("population_analysis_weight", "first"),
            observed_n=("observed_n", "first"),
            observed_adoption=("observed_adoption", "first"),
            plot_area_ha=("plot_area_ha", "first"),
        )
    )
    provider_effects = meta.merge(wide_provider, on=["farmer_idx", "provider"], how="left")
    for metric in ["predicted_n", "predicted_adoption", "predicted_quantity_kg"]:
        provider_effects[f"delta_{metric}"] = (
            provider_effects[f"{metric}_high"] - provider_effects[f"{metric}_low"]
        )
    provider_effects["expanded_delta_tonnes"] = (
        provider_effects["delta_predicted_quantity_kg"]
        * provider_effects["population_analysis_weight"] / 1000.0
    )
    provider_effects = provider_effects.merge(profiles, on="farmer_idx", how="left")
    provider_effects.to_csv(OUT / "Figure6_profile_provider_effects.csv", index=False)

    ensemble = (
        provider_effects.groupby("farmer_idx", as_index=False)
        .agg(
            delta_predicted_n=("delta_predicted_n", "mean"),
            delta_predicted_adoption=("delta_predicted_adoption", "mean"),
            delta_predicted_quantity_kg=("delta_predicted_quantity_kg", "mean"),
            population_analysis_weight=("population_analysis_weight", "first"),
            observed_n=("observed_n", "first"),
            observed_adoption=("observed_adoption", "first"),
            plot_area_ha=("plot_area_ha", "first"),
            main_crop=("main_crop", "first"),
            farm_size=("farm_size", "first"),
            age_manager=("age_manager", "first"),
            female_manager=("female_manager", "first"),
            formal_education_manager=("formal_education_manager", "first"),
            intercropped=("intercropped", "first"),
            plot_owned=("plot_owned", "first"),
        )
    )
    ensemble["expanded_delta_tonnes"] = (
        ensemble["delta_predicted_quantity_kg"]
        * ensemble["population_analysis_weight"] / 1000.0
    )
    ensemble["plot_area_quartile"] = pd.qcut(
        ensemble["plot_area_ha"], 4, labels=["Q1 smallest", "Q2", "Q3", "Q4 largest"]
    )
    ensemble["observed_n_group"] = pd.cut(
        ensemble["observed_n"],
        bins=[-0.001, 0, 10, 30, np.inf],
        labels=["0", "0-10", "10-30", ">30"],
    )
    ensemble = ensemble.sort_values("expanded_delta_tonnes", ascending=False)
    total = ensemble["expanded_delta_tonnes"].sum()
    ensemble["cumulative_tonnes"] = ensemble["expanded_delta_tonnes"].cumsum()
    ensemble["cumulative_share"] = ensemble["cumulative_tonnes"] / total
    ensemble.to_csv(OUT / "Figure6_profile_ensemble_effects.csv", index=False)

    summaries: list[dict[str, object]] = []
    for name, frame in [
        ("all", ensemble),
        ("observed_adopter", ensemble[ensemble["observed_adoption"].eq(1)]),
        ("observed_non_adopter", ensemble[ensemble["observed_adoption"].eq(0)]),
    ]:
        summaries.append({
            "group": name,
            "n_profiles": len(frame),
            "mean_delta_n": frame["delta_predicted_n"].mean(),
            "median_delta_n": frame["delta_predicted_n"].median(),
            "share_delta_n_positive": (frame["delta_predicted_n"] > 0).mean(),
            "mean_delta_adoption": frame["delta_predicted_adoption"].mean(),
            "mean_delta_quantity_kg": frame["delta_predicted_quantity_kg"].mean(),
            "weighted_delta_quantity_kg": weighted_mean(
                frame["delta_predicted_quantity_kg"],
                frame["population_analysis_weight"],
            ),
            "expanded_delta_tonnes": frame["expanded_delta_tonnes"].sum(),
        })
    for group_col in ["plot_area_quartile", "observed_n_group", "formal_education_manager",
                      "female_manager", "main_crop"]:
        for group, frame in ensemble.groupby(group_col, observed=False):
            summaries.append({
                "group": f"{group_col}={group}",
                "n_profiles": len(frame),
                "mean_delta_n": frame["delta_predicted_n"].mean(),
                "median_delta_n": frame["delta_predicted_n"].median(),
                "share_delta_n_positive": (frame["delta_predicted_n"] > 0).mean(),
                "mean_delta_adoption": frame["delta_predicted_adoption"].mean(),
                "mean_delta_quantity_kg": frame["delta_predicted_quantity_kg"].mean(),
                "weighted_delta_quantity_kg": weighted_mean(
                    frame["delta_predicted_quantity_kg"],
                    frame["population_analysis_weight"],
                ),
                "expanded_delta_tonnes": frame["expanded_delta_tonnes"].sum(),
            })
    pd.DataFrame(summaries).to_csv(OUT / "Figure6_diagnostic_summary.csv", index=False)

    top_10_share = ensemble.head(10)["expanded_delta_tonnes"].sum() / total
    top_20_share = ensemble.head(20)["expanded_delta_tonnes"].sum() / total
    positive_share = (ensemble["delta_predicted_n"] > 0).mean()
    print(f"profiles: {len(ensemble)}")
    print(f"mean delta N: {ensemble['delta_predicted_n'].mean():.3f}")
    print(f"median delta N: {ensemble['delta_predicted_n'].median():.3f}")
    print(f"share positive delta N: {positive_share:.3f}")
    print(f"weighted quantity delta: {weighted_mean(ensemble['delta_predicted_quantity_kg'], ensemble['population_analysis_weight']):.3f} kg/plot")
    print(f"expanded total: {total:.1f} tonnes")
    print(f"top 10 profile share: {top_10_share:.3f}")
    print(f"top 20 profile share: {top_20_share:.3f}")
    print("by observed adoption:")
    print(pd.DataFrame(summaries).head(3).to_string(index=False))


if __name__ == "__main__":
    main()
