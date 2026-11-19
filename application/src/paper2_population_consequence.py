"""Population-calibrated fertilizer consequences for Paper 2.

Post-stratifies the deliberately balanced synthetic-farmer evaluation profiles
back to each country-wave eligible plot-record population using recovered LSMS
household weights. Full-pool observed targets are kept fixed; bootstrap intervals
represent uncertainty from the sampled synthetic profiles, not full survey-design
uncertainty.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESPONSES_FILE = ROOT / "data" / "model_outputs" / "benchmark_predictions.csv"
DESIGN_FILE = ROOT / "data" / "processed" / "profile_survey_design.csv"
TARGETS_FILE = ROOT / "data" / "processed" / "paper2_country_wave_population_targets.csv"
OUT_METRICS = ROOT / "reproduced" / "analysis" / "paper2_population_consequence.csv"
OUT_REPORT = ROOT / "reproduced" / "analysis" / "paper2_population_consequence.md"
PROVIDERS = ("claude", "codex", "kimi", "ensemble")
COUNTRIES = ("Ethiopia", "Malawi", "Mali", "Niger", "Nigeria", "Tanzania", "Uganda")
STRATA = ("fert_user", "female_manager", "formal_education_manager")
SEED = 20260827


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    responses = pd.read_csv(RESPONSES_FILE)
    provider_rows = responses[responses["provider"].isin(PROVIDERS[:3])].copy()
    ensemble = provider_rows.groupby(
        ["panel", "profile_index", "country", "plot_area_ha"], as_index=False
    ).agg(
        predicted_n=("predicted_n", "mean"),
        predicted_adoption=("predicted_adoption", "mean"),
    )
    ensemble["provider"] = "ensemble"
    responses = pd.concat([
        provider_rows[["panel", "profile_index", "country", "plot_area_ha", "predicted_n",
                       "predicted_adoption", "provider"]],
        ensemble,
    ], ignore_index=True)
    design = pd.read_csv(DESIGN_FILE)[[
        "panel", "profile_index", "population_analysis_weight", *STRATA,
    ]]
    responses = responses.merge(
        design, on=["panel", "profile_index"], how="left", validate="many_to_one")
    if responses["population_analysis_weight"].isna().any():
        raise RuntimeError("Survey-design weights did not merge to all response rows")
    responses["predicted_quantity_kg"] = (
        responses["predicted_n"] * responses["plot_area_ha"])
    targets = pd.read_csv(TARGETS_FILE).set_index("country")
    return responses, targets


def weighted_mean(values, weights) -> float:
    values = np.asarray(values, float)
    weights = np.asarray(weights, float)
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    return float(np.average(values[valid], weights=weights[valid]))


def point_metrics(frame: pd.DataFrame, target: pd.Series) -> dict:
    weights = frame["population_analysis_weight"].to_numpy(float)
    weight_total = float(weights.sum())
    predicted_n = weighted_mean(frame["predicted_n"], weights)
    predicted_adoption = weighted_mean(frame["predicted_adoption"], weights)
    predicted_quantity = weighted_mean(frame["predicted_quantity_kg"], weights)
    observed_n = float(target["survey_weighted_mean_n_kg_per_ha"])
    observed_adoption = float(target["survey_weighted_fert_user_prevalence"])
    observed_quantity = float(target["survey_weighted_mean_n_kg_per_plot"])
    return {
        "eligible_plot_weight_total": weight_total,
        "predicted_n_kg_per_ha": predicted_n,
        "observed_n_kg_per_ha": observed_n,
        "n_error_kg_per_ha": predicted_n - observed_n,
        "predicted_adoption": predicted_adoption,
        "observed_adoption": observed_adoption,
        "adoption_error": predicted_adoption - observed_adoption,
        "predicted_n_kg_per_plot": predicted_quantity,
        "observed_n_kg_per_plot": observed_quantity,
        "quantity_error_kg_per_plot": predicted_quantity - observed_quantity,
        "predicted_eligible_plot_n_tonnes": predicted_quantity * weight_total / 1000,
        "observed_eligible_plot_n_tonnes": observed_quantity * weight_total / 1000,
        "eligible_plot_n_error_tonnes": (
            (predicted_quantity - observed_quantity) * weight_total / 1000),
    }


def bootstrap(frame: pd.DataFrame, target: pd.Series, repetitions: int,
              rng: np.random.Generator) -> dict:
    draws = {name: [] for name in (
        "predicted_n_kg_per_ha", "n_error_kg_per_ha", "predicted_adoption",
        "adoption_error", "predicted_n_kg_per_plot", "quantity_error_kg_per_plot",
        "eligible_plot_n_error_tonnes")}
    grouped_positions = [group.index.to_numpy() for _, group in frame.reset_index(drop=True).groupby(
        list(STRATA), dropna=False)]
    reset = frame.reset_index(drop=True)
    for _ in range(repetitions):
        positions = np.concatenate([
            rng.choice(group, size=len(group), replace=True) for group in grouped_positions
        ])
        result = point_metrics(reset.iloc[positions], target)
        for name in draws:
            draws[name].append(result[name])
    intervals = {}
    for name, values in draws.items():
        intervals[f"{name}_lo"], intervals[f"{name}_hi"] = [
            float(value) for value in np.quantile(values, [0.025, 0.975])
        ]
    return intervals


def analyze(responses: pd.DataFrame, targets: pd.DataFrame,
            repetitions: int) -> pd.DataFrame:
    rows = []
    for provider_index, provider in enumerate(PROVIDERS):
        for country_index, country in enumerate(COUNTRIES):
            frame = responses[(responses["provider"] == provider)
                              & (responses["country"] == country)].copy()
            if frame.empty:
                continue
            result = {
                "provider": provider,
                "country": country,
                "n_profiles": len(frame),
                **point_metrics(frame, targets.loc[country]),
            }
            result.update(bootstrap(
                frame, targets.loc[country], repetitions,
                np.random.default_rng(SEED + provider_index * 100 + country_index)))
            rows.append(result)
    return pd.DataFrame(rows)


def interval(row: pd.Series, name: str, digits=2) -> str:
    return (f"{row[name]:+,.{digits}f} [{row[f'{name}_lo']:+,.{digits}f}, "
            f"{row[f'{name}_hi']:+,.{digits}f}]")


def build_report(metrics: pd.DataFrame) -> str:
    ensemble = metrics[metrics["provider"] == "ensemble"].set_index("country")
    lines = [
        "# Paper 2 — population-calibrated agricultural consequence", "",
        "The deliberately balanced evaluation profiles are post-stratified to each survey's",
        "eligible plot-record population using recovered household weights. Observed targets use",
        "the full eligible country-wave pool; intervals resample only the 70 synthetic profiles",
        "within the sample-construction post-strata.", "",
        "| country | adoption: predicted / observed (error) | N kg/ha: predicted / observed (error) | N kg/plot: predicted / observed (error) | expanded eligible-plot N error, tonnes |",
        "|---|---:|---:|---:|---:|",
    ]
    for country in COUNTRIES:
        row = ensemble.loc[country]
        lines.append(
            f"| {country} | {row['predicted_adoption']:.3f} / "
            f"{row['observed_adoption']:.3f} ({interval(row, 'adoption_error', 3)}) | "
            f"{row['predicted_n_kg_per_ha']:.2f} / {row['observed_n_kg_per_ha']:.2f} "
            f"({interval(row, 'n_error_kg_per_ha')}) | "
            f"{row['predicted_n_kg_per_plot']:.2f} / {row['observed_n_kg_per_plot']:.2f} "
            f"({interval(row, 'quantity_error_kg_per_plot')}) | "
            f"{interval(row, 'eligible_plot_n_error_tonnes', 0)} |"
        )
    lines += ["", "## Boundaries", "",
              "- Expanded totals describe the harmonized survey's eligible weighted plot records;",
              "  they are not national fertilizer sales or a complete national nitrogen budget.",
              "- Household weights are applied to plot records; no separate within-household plot",
              "  selection weight was available.",
              "- Intervals capture synthetic-profile sampling only and omit survey-design target",
              "  uncertainty, backend drift, and prompt uncertainty.",
              "- The original four-country calls and current three-country extension were collected",
              "  at different dates, so cross-panel aggregate comparisons are supporting evidence."]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=int, default=10_000)
    args = parser.parse_args()
    responses, targets = load_data()
    metrics = analyze(responses, targets, args.bootstrap)
    report = build_report(metrics)
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(OUT_METRICS, index=False)
    OUT_REPORT.write_text(report)
    print(report)
    print(f"Wrote {OUT_METRICS}")
    print(f"Wrote {OUT_REPORT}")


if __name__ == "__main__":
    main()
