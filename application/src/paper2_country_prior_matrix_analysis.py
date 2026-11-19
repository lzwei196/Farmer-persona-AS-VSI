"""Analyze Paper 2's complete seven-country label matrix.

The independent units for the prevalence-ordering test are the seven assigned
country labels. Profile-level resampling is used for label contrasts and for the
crossed label-versus-profile variance comparison.

Usage
-----
    /usr/bin/python3 src/paper2_country_prior_matrix_analysis.py
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, rankdata, spearmanr, ttest_1samp

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "profiles" / "lsms_4country_full.csv"
PREVALENCE_FILE = ROOT / "data" / "processed" / "paper2_country_wave_prevalence.csv"
PREVALENCE_WEIGHTED_FILE = (
    ROOT / "data" / "processed" / "paper2_country_wave_prevalence_weighted_sensitivity.csv"
)
SURVEY_DESIGN_FILE = ROOT / "data" / "processed" / "profile_survey_design.csv"
PUBLIC_RESPONSES = ROOT / "data" / "model_outputs" / "country_prior_matrix_predictions.csv"
MATRIX_RESULTS = ROOT / "results" / "paper2_country_prior_matrix"
PRIOR_RESULTS = ROOT / "results" / "paper2_country_label_ablation"
OUT_RESPONSES = ROOT / "reproduced" / "analysis" / "paper2_country_prior_matrix_responses.csv"
OUT_LABELS = ROOT / "reproduced" / "analysis" / "paper2_country_prior_matrix_label_summary.csv"
OUT_VARIANCE = ROOT / "reproduced" / "analysis" / "paper2_country_prior_matrix_variance.csv"
OUT_COMPONENTS = ROOT / "reproduced" / "analysis" / "paper2_country_prior_matrix_components.csv"
OUT_RANKING = ROOT / "reproduced" / "analysis" / "paper2_country_prior_matrix_ranking.csv"
OUT_JSON = ROOT / "reproduced" / "analysis" / "paper2_country_prior_matrix_results.json"
OUT_REPORT = ROOT / "reproduced" / "analysis" / "paper2_country_prior_matrix_results.md"
PROVIDERS = ("claude", "codex", "kimi")
LABELS = ("Ethiopia", "Malawi", "Mali", "Niger", "Nigeria", "Tanzania", "Uganda")
REUSE = {"Tanzania": "true_country", "Nigeria": "swapped_country"}
HIGH = ("Ethiopia", "Malawi", "Nigeria")
LOW = ("Niger", "Tanzania", "Uganda")
SEED = 20260827


def response_path(provider: str, label: str, farmer_idx: int) -> Path:
    if label in REUSE:
        return PRIOR_RESULTS / provider / REUSE[label] / f"Tanzania_{farmer_idx}.json"
    return MATRIX_RESULTS / provider / label / f"Tanzania_{farmer_idx}.json"


def load_responses() -> pd.DataFrame:
    """Load the public consolidated matrix and restore analysis-only grouping fields."""
    responses = pd.read_csv(PUBLIC_RESPONSES)
    responses = responses[responses["provider"].isin(PROVIDERS)].copy()
    responses["farmer_idx"] = responses["profile_key"].str.rsplit("_", n=1).str[-1].astype(int)
    weights = pd.read_csv(SURVEY_DESIGN_FILE)
    weights = weights[
        (weights["panel"] == "original_discovery")
        & (weights["country"] == "Tanzania")
    ][[
        "profile_index", "household_weight_pw", "population_analysis_weight",
        "strataid", "ea_id_merge", "fert_user",
    ]].rename(columns={"profile_index": "farmer_idx"})
    responses = responses.drop(
        columns=[
            "household_weight_pw", "population_analysis_weight", "strataid",
            "ea_id_merge", "fert_user",
        ],
        errors="ignore",
    ).merge(weights, on="farmer_idx", how="left", validate="many_to_one")
    responses["source_file"] = "public consolidated response table"
    expected = len(PROVIDERS) * 70 * len(LABELS)
    if len(responses) != expected:
        raise RuntimeError(f"Expected {expected} provider cells, found {len(responses)}")
    if responses["population_analysis_weight"].isna().any():
        raise RuntimeError("Survey weights did not merge to every public matrix profile")
    return responses


def add_ensemble(responses: pd.DataFrame) -> pd.DataFrame:
    keys = [
        "profile_key", "farmer_idx", "assigned_country", "observed_n", "observed_adoption", "plot_area_ha",
        "household_weight_pw", "population_analysis_weight", "strataid", "ea_id_merge",
        "fert_user",
    ]
    ensemble = responses.groupby(keys, as_index=False, dropna=False).agg(
        predicted_n=("predicted_n", "mean"),
        predicted_adoption=("predicted_adoption", "mean"),
        predicted_quantity_kg=("predicted_quantity_kg", "mean"),
    )
    ensemble["provider"] = "ensemble"
    ensemble["source_file"] = "mean of three provider cells"
    return pd.concat([responses, ensemble[responses.columns]], ignore_index=True)


def safe_corr(x, y, kind="pearson") -> float:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 4 or np.std(x[ok]) < 1e-12 or np.std(y[ok]) < 1e-12:
        return np.nan
    return float(pearsonr(x[ok], y[ok])[0] if kind == "pearson"
                 else spearmanr(x[ok], y[ok])[0])


def exact_permutation_p(x, y, kind="pearson") -> tuple[float, float]:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    if kind == "spearman":
        x = rankdata(x)
        y = rankdata(y)
    observed = safe_corr(x, y, "pearson")
    permutations = np.asarray(list(itertools.permutations(y)), float)
    x_centered = x - x.mean()
    permutation_centered = permutations - permutations.mean(axis=1, keepdims=True)
    denominator = np.sqrt(
        np.sum(x_centered ** 2) * np.sum(permutation_centered ** 2, axis=1))
    null = np.divide(
        permutation_centered @ x_centered, denominator,
        out=np.full(len(permutations), np.nan), where=denominator > 1e-12)
    return observed, float(np.mean(np.abs(null) >= abs(observed) - 1e-12))


def label_summary(all_responses: pd.DataFrame) -> pd.DataFrame:
    prevalence = pd.read_csv(PREVALENCE_FILE).set_index("country")
    rows = []
    for provider in PROVIDERS + ("ensemble",):
        provider_data = all_responses[all_responses["provider"] == provider]
        for label in LABELS:
            frame = provider_data[provider_data["assigned_country"] == label]
            weights = frame["population_analysis_weight"].to_numpy(float)
            rows.append({
                "provider": provider,
                "assigned_country": label,
                "n_profiles": len(frame),
                "country_wave_prevalence": float(
                    prevalence.loc[label, "unweighted_fertilizer_prevalence"]),
                "mean_predicted_n": float(frame["predicted_n"].mean()),
                "mean_predicted_adoption": float(frame["predicted_adoption"].mean()),
                "mean_predicted_quantity_kg": float(frame["predicted_quantity_kg"].mean()),
                "population_weighted_predicted_n": float(np.average(
                    frame["predicted_n"], weights=weights)),
                "population_weighted_predicted_adoption": float(np.average(
                    frame["predicted_adoption"], weights=weights)),
                "population_weighted_predicted_quantity_kg": float(np.average(
                    frame["predicted_quantity_kg"], weights=weights)),
                "eligible_plot_population_quantity_tonnes": float(
                    np.sum(frame["predicted_quantity_kg"].to_numpy(float) * weights) / 1000),
                "farmer_r": safe_corr(frame["predicted_n"], frame["observed_n"], "pearson"),
                "farmer_rho": safe_corr(frame["predicted_n"], frame["observed_n"], "spearman"),
            })
    return pd.DataFrame(rows)


def marginal_variance_values(values: np.ndarray) -> dict:
    label_means = values.mean(axis=0)
    profile_means = values.mean(axis=1)
    grand = values.mean()
    residual = values - profile_means[:, None] - label_means[None, :] + grand
    label_variance = float(np.var(label_means, ddof=1))
    profile_variance = float(np.var(profile_means, ddof=1))
    interaction_variance = float(np.var(residual, ddof=1))
    return {
        "label_marginal_variance": label_variance,
        "profile_marginal_variance": profile_variance,
        "label_to_profile_ratio": label_variance / profile_variance
        if profile_variance > 0 else np.inf,
        "profile_label_interaction_variance": interaction_variance,
    }


def marginal_values(frame: pd.DataFrame, outcome: str) -> np.ndarray:
    matrix = frame.pivot(index="farmer_idx", columns="assigned_country", values=outcome)
    matrix = matrix.loc[:, list(LABELS)]
    if matrix.isna().any().any() or matrix.shape != (70, 7):
        raise RuntimeError(f"Incomplete crossed matrix for {outcome}: {matrix.shape}")
    return matrix.to_numpy(float)


def marginal_variances(frame: pd.DataFrame, outcome: str) -> dict:
    return marginal_variance_values(marginal_values(frame, outcome))


def bootstrap_variance(frame: pd.DataFrame, outcome: str, repetitions: int,
                       rng: np.random.Generator) -> dict:
    farmers = np.sort(frame["farmer_idx"].unique())
    draws = {name: [] for name in (
        "label_marginal_variance", "profile_marginal_variance", "label_to_profile_ratio")}
    values = marginal_values(frame, outcome)
    adoption_by_farmer = frame.drop_duplicates("farmer_idx").set_index("farmer_idx")[
        "observed_adoption"]
    for _ in range(repetitions):
        sampled_blocks = []
        for adoption in sorted(adoption_by_farmer.unique()):
            stratum = farmers[adoption_by_farmer.loc[farmers].to_numpy() == adoption]
            sampled_blocks.append(rng.choice(stratum, size=len(stratum), replace=True))
        sampled = np.concatenate(sampled_blocks)
        positions = np.searchsorted(farmers, sampled)
        result = marginal_variance_values(values[positions, :])
        for name in draws:
            draws[name].append(result[name])
    intervals = {}
    for name, values in draws.items():
        intervals[f"{name}_lo"], intervals[f"{name}_hi"] = [
            float(value) for value in np.quantile(values, [0.025, 0.975])
        ]
    return intervals


def variance_table(all_responses: pd.DataFrame, repetitions: int) -> pd.DataFrame:
    rows = []
    outcomes = ("predicted_n", "predicted_adoption", "predicted_quantity_kg")
    for provider_index, provider in enumerate(PROVIDERS + ("ensemble",)):
        frame = all_responses[all_responses["provider"] == provider]
        for outcome_index, outcome in enumerate(outcomes):
            result = {"provider": provider, "outcome": outcome,
                      **marginal_variances(frame, outcome)}
            result.update(bootstrap_variance(
                frame, outcome, repetitions,
                np.random.default_rng(SEED + provider_index * 100 + outcome_index)))
            rows.append(result)
    return pd.DataFrame(rows)


def crossed_values(frame: pd.DataFrame, outcome: str) -> np.ndarray:
    farmers = np.sort(frame["farmer_idx"].unique())
    index = pd.MultiIndex.from_product([PROVIDERS, farmers], names=["provider", "farmer_idx"])
    matrix = frame.pivot(index=["provider", "farmer_idx"],
                         columns="assigned_country", values=outcome)
    matrix = matrix.reindex(index=index, columns=list(LABELS))
    if matrix.isna().any().any():
        raise RuntimeError(f"Incomplete provider-profile-label matrix for {outcome}")
    return matrix.to_numpy(float).reshape(len(PROVIDERS), len(farmers), len(LABELS))


def crossed_effect_components_values(values: np.ndarray) -> dict:
    grand = values.mean()
    provider = values.mean(axis=(1, 2)) - grand
    profile = values.mean(axis=(0, 2)) - grand
    label = values.mean(axis=(0, 1)) - grand
    provider_profile = values.mean(axis=2) - grand - provider[:, None] - profile[None, :]
    provider_label = values.mean(axis=1) - grand - provider[:, None] - label[None, :]
    profile_label = values.mean(axis=0) - grand - profile[:, None] - label[None, :]
    three_way = (
        values - grand - provider[:, None, None] - profile[None, :, None]
        - label[None, None, :] - provider_profile[:, :, None]
        - provider_label[:, None, :] - profile_label[None, :, :]
    )
    components = {
        "provider_component": float(np.mean(provider ** 2)),
        "profile_component": float(np.mean(profile ** 2)),
        "label_component": float(np.mean(label ** 2)),
        "provider_profile_component": float(np.mean(provider_profile ** 2)),
        "provider_label_component": float(np.mean(provider_label ** 2)),
        "profile_label_component": float(np.mean(profile_label ** 2)),
        "three_way_or_residual_component": float(np.mean(three_way ** 2)),
    }
    total = float(np.mean((values - grand) ** 2))
    reconstructed = sum(components.values())
    if not np.isclose(total, reconstructed, rtol=1e-10, atol=1e-10):
        raise RuntimeError(f"Crossed decomposition failed: {total} != {reconstructed}")
    components["total_variance"] = total
    components["label_share"] = components["label_component"] / total if total > 0 else np.nan
    components["profile_share"] = components["profile_component"] / total if total > 0 else np.nan
    components["label_to_profile_ratio"] = (
        components["label_component"] / components["profile_component"]
        if components["profile_component"] > 0 else np.inf
    )
    return components


def crossed_effect_components(frame: pd.DataFrame, outcome: str) -> dict:
    """Descriptive orthogonal decomposition of the complete P x F x L matrix.

    With one response per provider-profile-label cell, the three-way term also
    contains cell-level residual variation. Providers are the three evaluated
    interfaces, not a random sample of an abstract provider population.
    """
    return crossed_effect_components_values(crossed_values(frame, outcome))


def crossed_components_table(responses: pd.DataFrame, repetitions: int) -> pd.DataFrame:
    provider_responses = responses[responses["provider"].isin(PROVIDERS)]
    farmers = np.sort(provider_responses["farmer_idx"].unique())
    adoption = provider_responses.drop_duplicates("farmer_idx").set_index("farmer_idx")[
        "observed_adoption"].loc[farmers].to_numpy(int)
    rows = []
    for outcome_index, outcome in enumerate(("predicted_n", "predicted_adoption",
                                             "predicted_quantity_kg")):
        point = crossed_effect_components(provider_responses, outcome)
        values = crossed_values(provider_responses, outcome)
        rng = np.random.default_rng(SEED + 5000 + outcome_index)
        draws = {name: [] for name in (
            "label_component", "profile_component", "label_share", "profile_share",
            "label_to_profile_ratio")}
        for _ in range(repetitions):
            sampled_positions = []
            for value in np.unique(adoption):
                positions = np.flatnonzero(adoption == value)
                sampled_positions.append(rng.choice(positions, size=len(positions), replace=True))
            sampled_positions = np.concatenate(sampled_positions)
            draw = crossed_effect_components_values(values[:, sampled_positions, :])
            for name in draws:
                draws[name].append(draw[name])
        row = {"outcome": outcome, **point}
        for name, values in draws.items():
            row[f"{name}_lo"], row[f"{name}_hi"] = [
                float(value) for value in np.quantile(values, [0.025, 0.975])
            ]
        rows.append(row)
    return pd.DataFrame(rows)


def high_low_differences(frame: pd.DataFrame, outcome: str) -> np.ndarray:
    matrix = frame.pivot(index="farmer_idx", columns="assigned_country", values=outcome)
    return (matrix[list(HIGH)].mean(axis=1) - matrix[list(LOW)].mean(axis=1)).to_numpy(float)


def bootstrap_difference(values: np.ndarray, adoption: np.ndarray, repetitions: int,
                         rng: np.random.Generator, weights: np.ndarray | None = None
                         ) -> tuple[float, float]:
    draws = np.empty(repetitions)
    for index in range(repetitions):
        sampled = []
        for stratum_value in np.unique(adoption):
            stratum = np.flatnonzero(adoption == stratum_value)
            sampled.append(rng.choice(stratum, size=len(stratum), replace=True))
        sampled = np.concatenate(sampled)
        if weights is None:
            draws[index] = values[sampled].mean()
        else:
            draws[index] = np.average(values[sampled], weights=weights[sampled])
    return tuple(float(value) for value in np.quantile(draws, [0.025, 0.975]))


def holm_adjust(p_values: list[float]) -> list[float]:
    values = np.asarray(p_values, float)
    order = np.argsort(values)
    adjusted = np.empty_like(values)
    running = 0.0
    count = len(values)
    for rank, index in enumerate(order):
        candidate = (count - rank) * values[index]
        running = max(running, candidate)
        adjusted[index] = min(1.0, running)
    return adjusted.tolist()


def contrast_table(all_responses: pd.DataFrame, repetitions: int) -> pd.DataFrame:
    rows = []
    for outcome_index, outcome in enumerate(("predicted_n", "predicted_adoption",
                                             "predicted_quantity_kg")):
        provider_rows = []
        for provider_index, provider in enumerate(PROVIDERS + ("ensemble",)):
            frame = all_responses[all_responses["provider"] == provider]
            differences = high_low_differences(frame, outcome)
            profile_rows = frame.drop_duplicates("farmer_idx").sort_values("farmer_idx")
            adoption = profile_rows["observed_adoption"].to_numpy(int)
            weights = profile_rows["population_analysis_weight"].to_numpy(float)
            lo, hi = bootstrap_difference(
                differences, adoption, repetitions,
                np.random.default_rng(SEED + 1000 + outcome_index * 100 + provider_index))
            weighted_lo, weighted_hi = bootstrap_difference(
                differences, adoption, repetitions,
                np.random.default_rng(SEED + 2000 + outcome_index * 100 + provider_index),
                weights=weights)
            p_value = float(ttest_1samp(differences, 0).pvalue)
            provider_rows.append({
                "provider": provider,
                "outcome": outcome,
                "mean_high_minus_low": float(differences.mean()),
                "ci_lo": lo,
                "ci_hi": hi,
                "population_weighted_high_minus_low": float(np.average(
                    differences, weights=weights)),
                "population_weighted_ci_lo": weighted_lo,
                "population_weighted_ci_hi": weighted_hi,
                "eligible_plot_population_total_difference": float(
                    np.sum(differences * weights)),
                "eligible_plot_population_total_difference_lo": float(
                    weighted_lo * weights.sum()),
                "eligible_plot_population_total_difference_hi": float(
                    weighted_hi * weights.sum()),
                "paired_t_p": p_value,
            })
        adjusted = holm_adjust([row["paired_t_p"] for row in provider_rows[:3]])
        for row, adjusted_p in zip(provider_rows[:3], adjusted):
            row["holm_p_across_providers"] = adjusted_p
        provider_rows[3]["holm_p_across_providers"] = np.nan
        rows.extend(provider_rows)
    return pd.DataFrame(rows)


def column_correlations(predictions: np.ndarray, observed: np.ndarray) -> np.ndarray:
    observed_centered = observed - observed.mean()
    predictions_centered = predictions - predictions.mean(axis=0, keepdims=True)
    numerator = np.sum(predictions_centered * observed_centered[:, None], axis=0)
    denominator = np.sqrt(
        np.sum(predictions_centered ** 2, axis=0) * np.sum(observed_centered ** 2))
    return np.divide(numerator, denominator, out=np.full(predictions.shape[1], np.nan),
                     where=denominator > 1e-12)


def ranking_stability_table(all_responses: pd.DataFrame, repetitions: int) -> pd.DataFrame:
    rows = []
    high_positions = [LABELS.index(label) for label in HIGH]
    low_positions = [LABELS.index(label) for label in LOW]
    for provider_index, provider in enumerate(PROVIDERS + ("ensemble",)):
        frame = all_responses[all_responses["provider"] == provider]
        matrix = frame.pivot(index="farmer_idx", columns="assigned_country",
                             values="predicted_n").loc[:, list(LABELS)]
        profile_rows = frame.drop_duplicates("farmer_idx").set_index("farmer_idx").loc[matrix.index]
        observed = profile_rows["observed_n"].to_numpy(float)
        adoption = profile_rows["observed_adoption"].to_numpy(int)
        predictions = matrix.to_numpy(float)
        correlations = column_correlations(predictions, observed)
        high_low = float(np.nanmean(correlations[high_positions])
                         - np.nanmean(correlations[low_positions]))
        pairwise_rho = matrix.corr(method="spearman").to_numpy(float)
        pairwise_rho = float(np.nanmean(
            pairwise_rho[np.triu_indices_from(pairwise_rho, k=1)]))
        rng = np.random.default_rng(SEED + 3000 + provider_index)
        high_low_draws = []
        range_draws = []
        for _ in range(repetitions):
            positions = []
            for value in np.unique(adoption):
                stratum = np.flatnonzero(adoption == value)
                positions.append(rng.choice(stratum, size=len(stratum), replace=True))
            positions = np.concatenate(positions)
            draw = column_correlations(predictions[positions], observed[positions])
            finite = draw[np.isfinite(draw)]
            if (finite.size > 0 and np.isfinite(draw[high_positions]).any()
                    and np.isfinite(draw[low_positions]).any()):
                high_low_draws.append(float(
                    np.nanmean(draw[high_positions]) - np.nanmean(draw[low_positions])))
                range_draws.append(float(finite.max() - finite.min()))
        high_low_lo, high_low_hi = (np.quantile(high_low_draws, [0.025, 0.975])
                                    if high_low_draws else (np.nan, np.nan))
        range_lo, range_hi = (np.quantile(range_draws, [0.025, 0.975])
                              if range_draws else (np.nan, np.nan))
        rows.append({
            "provider": provider,
            "minimum_label_farmer_r": float(np.nanmin(correlations)),
            "maximum_label_farmer_r": float(np.nanmax(correlations)),
            "range_label_farmer_r": float(np.nanmax(correlations) - np.nanmin(correlations)),
            "range_label_farmer_r_lo": float(range_lo),
            "range_label_farmer_r_hi": float(range_hi),
            "high_minus_low_label_farmer_r": high_low,
            "high_minus_low_label_farmer_r_lo": float(high_low_lo),
            "high_minus_low_label_farmer_r_hi": float(high_low_hi),
            "mean_pairwise_prediction_spearman": pairwise_rho,
        })
    return pd.DataFrame(rows)


def ordering_table(labels: pd.DataFrame) -> pd.DataFrame:
    rows = []
    weighted = pd.read_csv(PREVALENCE_WEIGHTED_FILE).set_index("country")
    for provider in PROVIDERS + ("ensemble",):
        frame = labels[labels["provider"] == provider].set_index("assigned_country").loc[list(LABELS)]
        prevalence_versions = {
            "frozen_unweighted": frame["country_wave_prevalence"].to_numpy(float),
            "survey_weighted_sensitivity": weighted.loc[
                list(LABELS), "survey_weighted_fertilizer_prevalence"].to_numpy(float),
        }
        for prevalence_basis, prevalence in prevalence_versions.items():
            for outcome in ("mean_predicted_n", "mean_predicted_adoption",
                            "mean_predicted_quantity_kg"):
                predicted = frame[outcome].to_numpy(float)
                pearson, pearson_p = exact_permutation_p(prevalence, predicted, "pearson")
                spearman, spearman_p = exact_permutation_p(prevalence, predicted, "spearman")
                rows.append({
                    "provider": provider,
                    "prevalence_basis": prevalence_basis,
                    "outcome": outcome,
                    "pearson_slope_per_prevalence_unit": float(
                        np.polyfit(prevalence, predicted, 1)[0]),
                    "pearson_r": pearson,
                    "pearson_exact_p": pearson_p,
                    "spearman_rho": spearman,
                    "spearman_exact_p": spearman_p,
                })
    return pd.DataFrame(rows)


def fmt(value, digits=3) -> str:
    return "NA" if not np.isfinite(value) else f"{value:.{digits}f}"


def build_report(labels: pd.DataFrame, variances: pd.DataFrame, components: pd.DataFrame,
                 contrasts: pd.DataFrame, ranking: pd.DataFrame,
                 ordering: pd.DataFrame) -> str:
    lines = [
        "# Paper 2 — seven-country label matrix",
        "",
        "Seventy frozen Tanzanian farmer profiles were crossed with all seven country labels while",
        "all non-location profile fields were held fixed. Tanzania and Nigeria reuse the completed",
        "randomized experiment; the other five labels were added prospectively under the frozen npj",
        "design.", "",
        "## Label-specific provider-ensemble predictions", "",
        "| assigned label | country-wave prevalence | predicted adoption | mean N kg/ha | mean N kg/plot | farmer r |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    ensemble_labels = labels[labels["provider"] == "ensemble"].set_index("assigned_country")
    for label in LABELS:
        row = ensemble_labels.loc[label]
        lines.append(
            f"| {label} | {row['country_wave_prevalence']:.1%} | "
            f"{row['mean_predicted_adoption']:.3f} | {row['mean_predicted_n']:.2f} | "
            f"{row['mean_predicted_quantity_kg']:.2f} | {fmt(row['farmer_r'])} |"
        )
    lines += ["", "## Exact seven-label ordering tests", "",
              "| provider | prevalence basis | outcome | slope per prevalence unit | Pearson r (exact p) | Spearman rho (exact p) |",
              "|---|---|---|---:|---:|---:|"]
    for row in ordering.itertuples(index=False):
        lines.append(
            f"| {row.provider} | {row.prevalence_basis} | {row.outcome} | "
            f"{row.pearson_slope_per_prevalence_unit:+.3f} | {row.pearson_r:+.3f} "
            f"({row.pearson_exact_p:.4f}) | {row.spearman_rho:+.3f} "
            f"({row.spearman_exact_p:.4f}) |"
        )
    lines += ["", "## Label-versus-profile variance", "",
              "Marginal variances compare variation across seven label means with variation across",
              "seventy profile means in the same complete crossed matrix.", "",
              "| provider | outcome | label variance [95% CI] | profile variance [95% CI] | ratio [95% CI] |",
              "|---|---|---:|---:|---:|"]
    for row in variances.itertuples(index=False):
        lines.append(
            f"| {row.provider} | {row.outcome} | {row.label_marginal_variance:.3f} "
            f"[{row.label_marginal_variance_lo:.3f}, {row.label_marginal_variance_hi:.3f}] | "
            f"{row.profile_marginal_variance:.3f} [{row.profile_marginal_variance_lo:.3f}, "
            f"{row.profile_marginal_variance_hi:.3f}] | {row.label_to_profile_ratio:.3f} "
            f"[{row.label_to_profile_ratio_lo:.3f}, {row.label_to_profile_ratio_hi:.3f}] |"
        )
    lines += ["", "## Crossed provider-profile-label decomposition", "",
              "These descriptive components partition variation across the three evaluated",
              "providers, 70 profiles, and seven labels. The three-way term includes cell residual",
              "variation because there is one response per cell.", "",
              "| outcome | label share [95% CI] | profile share [95% CI] | label/profile ratio [95% CI] | provider-label share |",
              "|---|---:|---:|---:|---:|"]
    for row in components.itertuples(index=False):
        provider_label_share = row.provider_label_component / row.total_variance
        lines.append(
            f"| {row.outcome} | {row.label_share:.3f} [{row.label_share_lo:.3f}, "
            f"{row.label_share_hi:.3f}] | {row.profile_share:.3f} "
            f"[{row.profile_share_lo:.3f}, {row.profile_share_hi:.3f}] | "
            f"{row.label_to_profile_ratio:.3f} [{row.label_to_profile_ratio_lo:.3f}, "
            f"{row.label_to_profile_ratio_hi:.3f}] | {provider_label_share:.3f} |"
        )
    lines += ["", "## Higher-use minus lower-use labels", "",
              f"Higher-use labels: {', '.join(HIGH)}. Lower-use labels: {', '.join(LOW)}. "
              "Mali is prespecified as the middle label and excluded.", "",
              "| provider | outcome | mean difference [95% CI] | paired p | Holm p |",
              "|---|---|---:|---:|---:|"]
    for row in contrasts.itertuples(index=False):
        lines.append(
            f"| {row.provider} | {row.outcome} | {row.mean_high_minus_low:+.3f} "
            f"[{row.ci_lo:+.3f}, {row.ci_hi:+.3f}] | {row.paired_t_p:.3g} | "
            f"{fmt(row.holm_p_across_providers, 4)} |"
        )
    lines += ["", "## Farmer-ranking stability across labels", "",
              "The high-minus-low statistic compares farmer correlations under higher-use versus",
              "lower-use labels using the same stratified profile bootstrap. Pairwise Spearman rho",
              "measures how similarly the seven arms rank the 70 identical profiles.", "",
              "| provider | min–max farmer r | r range [95% CI] | high-minus-low r [95% CI] | mean pairwise ranking rho |",
              "|---|---:|---:|---:|---:|"]
    for row in ranking.itertuples(index=False):
        lines.append(
            f"| {row.provider} | {row.minimum_label_farmer_r:+.3f} to "
            f"{row.maximum_label_farmer_r:+.3f} | {row.range_label_farmer_r:.3f} "
            f"[{row.range_label_farmer_r_lo:.3f}, {row.range_label_farmer_r_hi:.3f}] | "
            f"{row.high_minus_low_label_farmer_r:+.3f} "
            f"[{row.high_minus_low_label_farmer_r_lo:+.3f}, "
            f"{row.high_minus_low_label_farmer_r_hi:+.3f}] | "
            f"{row.mean_pairwise_prediction_spearman:.3f} |"
        )
    lines += ["", "## Population-calibrated agricultural consequence", "",
              "Household survey weights were recovered from the harmonized plot file and calibrated",
              "within the sampling cells used to construct the adopter-balanced profiles. The table",
              "reports the provider-ensemble higher-use minus lower-use label contrast after that",
              "calibration.", "",
              "| outcome | weighted difference [95% profile-bootstrap CI] | expanded eligible-plot total difference |",
              "|---|---:|---:|"]
    ensemble_contrasts = contrasts[contrasts["provider"] == "ensemble"]
    units = {
        "predicted_n": "kg N/ha",
        "predicted_adoption": "probability",
        "predicted_quantity_kg": "kg N/plot",
    }
    for row in ensemble_contrasts.itertuples(index=False):
        total = (
            f"{row.eligible_plot_population_total_difference/1000:,.0f} "
            f"[{row.eligible_plot_population_total_difference_lo/1000:,.0f}, "
            f"{row.eligible_plot_population_total_difference_hi/1000:,.0f}] tonnes N"
            if row.outcome == "predicted_quantity_kg" else "not additive")
        lines.append(
            f"| {row.outcome} | {row.population_weighted_high_minus_low:+.3f} "
            f"[{row.population_weighted_ci_lo:+.3f}, {row.population_weighted_ci_hi:+.3f}] "
            f"{units[row.outcome]} | {total} |"
        )
    n_variance = variances[variances["outcome"] == "predicted_n"].set_index("provider")
    provider_dominance = {
        provider: bool(n_variance.loc[provider, "label_marginal_variance"]
                       > n_variance.loc[provider, "profile_marginal_variance"])
        for provider in PROVIDERS
    }
    ensemble_dominance = bool(
        n_variance.loc["ensemble", "label_marginal_variance"]
        > n_variance.loc["ensemble", "profile_marginal_variance"])
    title_allowed = ensemble_dominance and sum(provider_dominance.values()) >= 2
    lines += ["", "## Prespecified title decision", "",
              f"- Label variance exceeds profile variance by provider: {provider_dominance}.",
              f"- Provider-ensemble dominance: {ensemble_dominance}.",
              f"- The word **dominate** is {'SUPPORTED' if title_allowed else 'NOT SUPPORTED'} "
              "under the frozen rule.", "", "## Interpretation boundaries", "",
              "- The assigned labels are controlled prompt interventions, not samples from the",
              "  assigned countries.",
              "- The primary prevalence values are frozen unweighted country-wave plot estimates,",
              "  not national estimates; an identically filtered household-weighted sensitivity is",
              "  reported separately.",
              "- Expanded quantity totals apply only to the eligible plot population represented by",
              "  the harmonized survey and the recovered household weights; they are not all-sector",
              "  fertilizer sales totals.",
              "- Label sensitivity does not identify proprietary training-data composition.",
              "- Farmer correlations use observed Tanzanian outcomes and assess ranking stability",
              "  under counterfactual labels."]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=int, default=10_000)
    args = parser.parse_args()
    provider_responses = load_responses()
    responses = add_ensemble(provider_responses)
    labels = label_summary(responses)
    variances = variance_table(responses, args.bootstrap)
    components = crossed_components_table(responses, args.bootstrap)
    contrasts = contrast_table(responses, args.bootstrap)
    ranking = ranking_stability_table(responses, args.bootstrap)
    ordering = ordering_table(labels)
    report = build_report(labels, variances, components, contrasts, ranking, ordering)
    OUT_RESPONSES.parent.mkdir(parents=True, exist_ok=True)
    responses.to_csv(OUT_RESPONSES, index=False)
    labels.to_csv(OUT_LABELS, index=False)
    variances.to_csv(OUT_VARIANCE, index=False)
    components.to_csv(OUT_COMPONENTS, index=False)
    ranking.to_csv(OUT_RANKING, index=False)
    payload = {
        "label_summary": labels.replace({np.nan: None}).to_dict("records"),
        "variance": variances.replace({np.nan: None}).to_dict("records"),
        "crossed_components": components.replace({np.nan: None}).to_dict("records"),
        "contrasts": contrasts.replace({np.nan: None}).to_dict("records"),
        "ranking_stability": ranking.replace({np.nan: None}).to_dict("records"),
        "ordering": ordering.replace({np.nan: None}).to_dict("records"),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    OUT_REPORT.write_text(report)
    print(report)
    print(f"Wrote {OUT_RESPONSES}")
    print(f"Wrote {OUT_LABELS}")
    print(f"Wrote {OUT_VARIANCE}")
    print(f"Wrote {OUT_COMPONENTS}")
    print(f"Wrote {OUT_RANKING}")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_REPORT}")


if __name__ == "__main__":
    main()
