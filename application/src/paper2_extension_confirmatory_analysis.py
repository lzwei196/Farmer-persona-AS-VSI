"""Analyze the clean three-provider extension and combine it with original T1 results.

Outputs
-------
results/analysis/paper2_extension_confirmatory_responses.csv
results/analysis/paper2_extension_confirmatory_metrics.csv
results/analysis/paper2_extension_confirmatory_metrics.json
results/analysis/paper2_extension_confirmatory_results.md

Usage
-----
    /usr/bin/python3 src/paper2_extension_confirmatory_analysis.py
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_RESPONSES = ROOT / "data" / "model_outputs" / "benchmark_predictions.csv"
SURVEY_DESIGN_FILE = ROOT / "data" / "processed" / "profile_survey_design.csv"
ORIGINAL_RESULTS = ROOT / "results" / "full" / "lsms"
EXTENSION_RESULTS = ROOT / "results" / "full" / "lsms_extension_confirmatory_v2"
ORIGINAL_SAMPLE = ROOT / "data" / "profiles" / "lsms_4country_full.csv"
EXTENSION_SAMPLE = ROOT / "data" / "profiles" / "lsms_extension_3country.csv"
PREVALENCE_FILE = ROOT / "data" / "processed" / "paper2_country_wave_prevalence.csv"
PREVALENCE_WEIGHTED_FILE = (
    ROOT / "data" / "processed" / "paper2_country_wave_prevalence_weighted_sensitivity.csv"
)
OUT_RESPONSES = ROOT / "reproduced" / "analysis" / "paper2_extension_confirmatory_responses.csv"
OUT_METRICS = ROOT / "reproduced" / "analysis" / "paper2_extension_confirmatory_metrics.csv"
OUT_JSON = ROOT / "reproduced" / "analysis" / "paper2_extension_confirmatory_metrics.json"
OUT_REPORT = ROOT / "reproduced" / "analysis" / "paper2_extension_confirmatory_results.md"
PROVIDERS = ("claude", "codex", "kimi")
COUNTRY_ORDER = ("Ethiopia", "Malawi", "Nigeria", "Tanzania", "Mali", "Niger", "Uganda")
METRIC_NAMES = ("r", "auc", "brier", "rho_positive", "mae_positive", "quantity_mae")
SEED = 20260827


def finite_number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if np.isfinite(value) else None


def parse_decision(payload: dict) -> tuple[float, float] | None:
    decision = payload.get("decision")
    if not isinstance(decision, dict):
        return None
    nitrogen = finite_number(decision.get("nitrogen_kg_per_ha"))
    adoption = decision.get("inorganic_fertilizer")
    if nitrogen is None or not isinstance(adoption, bool):
        return None
    return nitrogen, float(adoption)


def load_original() -> list[dict]:
    sample = pd.read_csv(ORIGINAL_SAMPLE)
    rows = []
    for provider in PROVIDERS:
        for path in (ORIGINAL_RESULTS / provider / "tier1").glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            parsed = parse_decision(payload)
            idx = payload.get("farmer_idx")
            if parsed is None or not isinstance(idx, int) or idx not in sample.index:
                continue
            truth = sample.loc[idx]
            nitrogen, adoption = parsed
            rows.append({
                "panel": "original_discovery",
                "provider": provider,
                "profile_key": f"original_{idx}",
                "profile_index": idx,
                "profile_id": payload.get("farmer_id", f"{truth.country}_{idx}"),
                "country": truth["country"],
                "hh_id": str(truth["hh_id_merge"]),
                "plot_id": str(truth["plot_id_merge"]),
                "plot_area_ha": float(truth["plot_area_GPS"]),
                "observed_n": float(truth["nitrogen_kg_per_ha"]),
                "observed_adoption": float(truth["fert_user"]),
                "predicted_n": nitrogen,
                "predicted_adoption": adoption,
                "source_file": str(path),
            })
    return rows


def load_extension() -> list[dict]:
    sample = pd.read_csv(EXTENSION_SAMPLE)
    rows = []
    for provider in PROVIDERS:
        for path in (EXTENSION_RESULTS / provider).glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            parsed = parse_decision(payload)
            idx = payload.get("profile_index")
            if parsed is None or not isinstance(idx, int) or idx not in sample.index:
                continue
            truth = sample.loc[idx]
            nitrogen, adoption = parsed
            rows.append({
                "panel": "prospective_extension_v2",
                "provider": provider,
                "profile_key": f"extension_{idx}",
                "profile_index": idx,
                "profile_id": payload.get("profile_id", f"{truth.country}_{idx}"),
                "country": truth["country"],
                "hh_id": str(truth["hh_id_merge"]),
                "plot_id": str(truth["plot_id_merge"]),
                "plot_area_ha": float(truth["plot_area_GPS"]),
                "observed_n": float(truth["nitrogen_kg_per_ha"]),
                "observed_adoption": float(truth["fert_user"]),
                "predicted_n": nitrogen,
                "predicted_adoption": adoption,
                "source_file": str(path),
            })
    return rows


def make_ensemble(responses: pd.DataFrame) -> pd.DataFrame:
    key = [name for name in [
        "panel", "profile_key", "profile_index", "profile_id", "country", "hh_id", "plot_id",
        "plot_area_ha", "observed_n", "observed_adoption",
    ] if name in responses.columns]
    valid = responses.groupby("profile_key")["provider"].nunique()
    complete_keys = valid[valid == len(PROVIDERS)].index
    complete = responses[responses["profile_key"].isin(complete_keys)].copy()
    # Missing N outcomes do not invalidate observed adoption labels.
    ensemble = complete.groupby(key, as_index=False, dropna=False).agg(
        predicted_n=("predicted_n", "mean"),
        predicted_adoption=("predicted_adoption", "mean"),
    )
    ensemble["provider"] = "ensemble"
    ensemble["source_file"] = "mean of three provider responses"
    return ensemble[responses.columns]


def safe_corr(x, y, method: str) -> float:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 4 or np.std(x[ok]) < 1e-12 or np.std(y[ok]) < 1e-12:
        return np.nan
    return float(pearsonr(x[ok], y[ok])[0] if method == "pearson"
                 else spearmanr(x[ok], y[ok])[0])


def metrics(frame: pd.DataFrame) -> dict:
    observed = frame["observed_n"].to_numpy(float)
    predicted = frame["predicted_n"].to_numpy(float)
    observed_adoption = frame["observed_adoption"].to_numpy(float)
    predicted_adoption = frame["predicted_adoption"].to_numpy(float)
    valid_target = np.isfinite(observed) & np.isfinite(predicted)
    positive = valid_target & (observed > 0)
    auc = np.nan
    if len(np.unique(observed_adoption)) == 2:
        auc = float(roc_auc_score(observed_adoption, predicted_adoption))
    sd_obs = float(np.std(observed[valid_target], ddof=1)) if valid_target.sum() > 1 else np.nan
    sd_pred = float(np.std(predicted[valid_target], ddof=1)) if valid_target.sum() > 1 else np.nan
    observed_quantity = observed * frame["plot_area_ha"].to_numpy(float)
    predicted_quantity = predicted * frame["plot_area_ha"].to_numpy(float)
    return {
        "n": int(len(frame)),
        "n_adoption": int(len(observed_adoption)),
        "n_observed_n": int(valid_target.sum()),
        "n_positive": int(positive.sum()),
        "r": safe_corr(predicted, observed, "pearson"),
        "auc": auc,
        "brier": float(np.mean((predicted_adoption - observed_adoption) ** 2)),
        "rho_positive": safe_corr(predicted[positive], observed[positive], "spearman"),
        "mae_positive": float(np.mean(np.abs(predicted[positive] - observed[positive])))
        if positive.any() else np.nan,
        "quantity_mae": float(np.mean(np.abs(
            predicted_quantity[valid_target] - observed_quantity[valid_target]))),
        "mean_observed_n": float(np.mean(observed[valid_target])),
        "mean_predicted_n": float(np.mean(predicted[valid_target])),
        "observed_zero_fraction": float(np.mean(observed[valid_target] == 0)),
        "predicted_zero_fraction": float(np.mean(predicted[valid_target] == 0)),
        "sd_ratio": sd_pred / sd_obs if sd_obs > 0 else np.nan,
    }


def stratified_boot_indices(frame: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    adoption = frame["observed_adoption"].to_numpy(int)
    sampled = []
    for value in np.unique(adoption):
        indexes = np.flatnonzero(adoption == value)
        sampled.append(rng.choice(indexes, size=len(indexes), replace=True))
    return np.concatenate(sampled)


def bootstrap_intervals(frame: pd.DataFrame, repetitions: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    draws = {name: [] for name in METRIC_NAMES}
    for _ in range(repetitions):
        sampled = frame.iloc[stratified_boot_indices(frame, rng)]
        result = metrics(sampled)
        for name in METRIC_NAMES:
            draws[name].append(result[name])
    intervals = {}
    for name, values in draws.items():
        values = np.asarray(values, float)
        finite = values[np.isfinite(values)]
        if len(finite) < max(100, repetitions // 10):
            intervals[f"{name}_lo"] = np.nan
            intervals[f"{name}_hi"] = np.nan
        else:
            intervals[f"{name}_lo"], intervals[f"{name}_hi"] = [
                float(value) for value in np.quantile(finite, [0.025, 0.975])
            ]
    return intervals


def adoption_bootstrap_intervals(frame: pd.DataFrame, repetitions: int, seed: int) -> dict:
    """Adoption-only intervals over every profile with an observed adoption label."""
    rng = np.random.default_rng(seed)
    observed = frame["observed_adoption"].to_numpy(float)
    predicted = frame["predicted_adoption"].to_numpy(float)
    draws = {name: [] for name in ("auc", "brier")}
    for _ in range(repetitions):
        sampled = stratified_boot_indices(frame, rng)
        draws["auc"].append(float(roc_auc_score(observed[sampled], predicted[sampled])))
        draws["brier"].append(float(np.mean((predicted[sampled] - observed[sampled]) ** 2)))
    return {
        f"{name}_{suffix}": float(value)
        for name, values in draws.items()
        for suffix, value in zip(("lo", "hi"), np.quantile(values, [0.025, 0.975]))
    }


def household_cluster_r_interval(frame: pd.DataFrame, repetitions: int,
                                 seed: int) -> tuple[float, float]:
    """Sensitivity interval resampling whole sampled households.

    Households are stratified by their observed adoption pattern across sampled
    plots (all non-user, all user, or mixed), retaining the balanced design as
    closely as possible while keeping repeated plots together.
    """
    rng = np.random.default_rng(seed)
    households = {
        household: group.copy()
        for household, group in frame.groupby("hh_id", sort=False)
    }
    strata: dict[str, list[str]] = {}
    for household, group in households.items():
        pattern = "".join(str(value) for value in sorted(
            group["observed_adoption"].astype(int).unique()))
        strata.setdefault(pattern, []).append(household)
    draws = []
    for _ in range(repetitions):
        blocks = []
        for household_ids in strata.values():
            sampled = rng.choice(household_ids, size=len(household_ids), replace=True)
            blocks.extend(households[household] for household in sampled)
        sampled_frame = pd.concat(blocks, ignore_index=True)
        value = safe_corr(sampled_frame["predicted_n"], sampled_frame["observed_n"], "pearson")
        if np.isfinite(value):
            draws.append(value)
    if len(draws) < max(100, repetitions // 10):
        return np.nan, np.nan
    return tuple(float(value) for value in np.quantile(draws, [0.025, 0.975]))


def exact_permutation_p(x, y, statistic: str = "pearson") -> tuple[float, float]:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    observed = safe_corr(x, y, statistic)
    permutations = np.array([
        safe_corr(x, permuted, statistic) for permuted in itertools.permutations(y)
    ])
    p_value = float(np.mean(np.abs(permutations) >= abs(observed) - 1e-12))
    return observed, p_value


def summarize(responses: pd.DataFrame, repetitions: int) -> pd.DataFrame:
    rows = []
    provider_order = PROVIDERS + ("ensemble",)
    for provider_index, provider in enumerate(provider_order):
        for country_index, country in enumerate(COUNTRY_ORDER):
            frame = responses[(responses["provider"] == provider)
                              & (responses["country"] == country)].copy()
            if frame.empty:
                continue
            result = {
                "provider": provider,
                "country": country,
                "panel": frame["panel"].iloc[0],
                **metrics(frame),
            }
            seed = SEED + 1000 * provider_index + country_index
            # Preserve the published ensemble rate/positive-user/quantity
            # confidence intervals and household-cluster cohort. Before the
            # adoption correction, make_ensemble excluded missing N outcomes.
            rate_frame = frame
            if provider == "ensemble":
                rate_frame = frame[
                    np.isfinite(frame["observed_n"]) & np.isfinite(frame["predicted_n"])
                ]
            result.update(bootstrap_intervals(rate_frame, repetitions, seed))
            if provider == "ensemble" and len(rate_frame) != len(frame):
                result.update(adoption_bootstrap_intervals(frame, repetitions, seed))
            result["r_household_cluster_lo"], result["r_household_cluster_hi"] = (
                household_cluster_r_interval(
                    rate_frame, repetitions,
                    SEED + 100_000 + 1000 * provider_index + country_index)
            )
            rows.append(result)
    return pd.DataFrame(rows)


def fmt(value, digits=3) -> str:
    return "NA" if not np.isfinite(value) else f"{value:.{digits}f}"


def interval(row, name, digits=3) -> str:
    value, lo, hi = row[name], row[f"{name}_lo"], row[f"{name}_hi"]
    if not all(np.isfinite([value, lo, hi])):
        return fmt(value, digits)
    return f"{value:.{digits}f} [{lo:.{digits}f}, {hi:.{digits}f}]"


def build_report(metrics_table: pd.DataFrame, responses: pd.DataFrame) -> str:
    prevalence = pd.read_csv(PREVALENCE_FILE).set_index("country")
    weighted_prevalence = pd.read_csv(PREVALENCE_WEIGHTED_FILE).set_index("country")
    lines = [
        "# Paper 2 — clean three-provider country extension",
        "",
        "The prospective extension uses the exact T1 template without an added system prompt and",
        "runs every provider in an empty working directory. Original four-country T1 results are",
        "shown as discovery evidence; they were collected earlier and may represent older provider",
        "backends. All samples are adopter-balanced, so population calibration is not estimated from",
        "these rows.",
        "",
        "## Provider-ensemble farmer-level results",
        "",
        "| country | panel | n | area-filtered inorganic-use prevalence | overall r [95% CI] | adoption AUC [95% CI] | Brier [95% CI] | positive-N rho [95% CI] |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    ensemble = metrics_table[metrics_table["provider"] == "ensemble"].set_index("country")
    for country in COUNTRY_ORDER:
        if country not in ensemble.index:
            continue
        row = ensemble.loc[country]
        prev = prevalence.loc[country, "unweighted_fertilizer_prevalence"]
        lines.append(
            f"| {country} | {row['panel']} | {int(row['n'])} | {prev:.1%} | "
            f"{interval(row, 'r')} | {interval(row, 'auc')} | {interval(row, 'brier')} | "
            f"{interval(row, 'rho_positive')} |"
        )
    lines += ["", "## Provider-specific overall r", "",
              "| country | Claude | Codex | Kimi | ensemble |",
              "|---|---:|---:|---:|---:|"]
    indexed = metrics_table.set_index(["country", "provider"])
    for country in COUNTRY_ORDER:
        values = []
        for provider in PROVIDERS + ("ensemble",):
            if (country, provider) in indexed.index:
                values.append(interval(indexed.loc[(country, provider)], "r"))
            else:
                values.append("NA")
        lines.append(f"| {country} | " + " | ".join(values) + " |")
    lines += ["", "## Household-cluster sensitivity for the provider ensemble", "",
              "The primary intervals resample profiles within adoption strata. These sensitivity",
              "intervals keep repeated plots from the same sampled household together.", "",
              "| country | r | household-cluster 95% CI |",
              "|---|---:|---:|"]
    for country in COUNTRY_ORDER:
        if country not in ensemble.index:
            continue
        row = ensemble.loc[country]
        lines.append(
            f"| {country} | {row['r']:+.3f} | [{fmt(row['r_household_cluster_lo'])}, "
            f"{fmt(row['r_household_cluster_hi'])}] |"
        )

    available = [country for country in COUNTRY_ORDER if country in ensemble.index]
    if len(available) == 7:
        x = prevalence.loc[available, "unweighted_fertilizer_prevalence"].to_numpy(float)
        y = ensemble.loc[available, "r"].to_numpy(float)
        if np.isfinite(y).all():
            pearson, pearson_p = exact_permutation_p(x, y, "pearson")
            spearman, spearman_p = exact_permutation_p(x, y, "spearman")
            weighted_x = weighted_prevalence.loc[
                available, "survey_weighted_fertilizer_prevalence"].to_numpy(float)
            weighted_pearson, weighted_pearson_p = exact_permutation_p(
                weighted_x, y, "pearson")
            weighted_spearman, weighted_spearman_p = exact_permutation_p(
                weighted_x, y, "spearman")
            lines += [
                "", "## Descriptive prevalence–fidelity ordering", "",
                "The country label is the independent unit (n=7); repeated profiles do not increase",
                "the country-level sample size.", "",
                f"- Frozen unweighted prevalence: Pearson r = {pearson:+.3f}, exact p = "
                f"{pearson_p:.4f}; Spearman rho = {spearman:+.3f}, exact p = "
                f"{spearman_p:.4f}.",
                f"- Survey-weighted sensitivity: Pearson r = {weighted_pearson:+.3f}, exact p = "
                f"{weighted_pearson_p:.4f}; Spearman rho = {weighted_spearman:+.3f}, exact p = "
                f"{weighted_spearman_p:.4f}.",
            ]
    counts = responses.groupby(["provider", "panel"])["profile_key"].nunique()
    lines += ["", "## Completeness", "", "```", counts.to_string(), "```", "",
              "## Boundaries", "",
              "- The frozen country-wave prevalence is an unweighted, area-filtered survey estimate,",
              "  not a national estimate; survey-weighted ordering is reported as a sensitivity.",
              "- Adoption AUROC and Brier use the survey inorganic-fertilizer indicator used for",
              "  sampling; positive-intensity metrics use reported nitrogen greater than zero.",
              "- Discovery and extension calls may use different provider backend versions.",
              "- The samples are balanced on observed adoption; mean and zero-mass errors in this",
              "  report describe the experimental samples, not country populations.",
              "- Uganda may be intrinsically difficult for both LLMs and conventional transfer",
              "  models; an agent failure there is not mechanism evidence by itself."]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=int, default=10_000)
    args = parser.parse_args()
    responses = pd.read_csv(PUBLIC_RESPONSES)
    design = pd.read_csv(SURVEY_DESIGN_FILE)[
        ["panel", "profile_index", "hh_id_merge"]
    ].rename(columns={"hh_id_merge": "hh_id"})
    responses = responses.merge(
        design, on=["panel", "profile_index"], how="left", validate="many_to_one"
    )
    if responses["hh_id"].isna().any():
        raise RuntimeError("Pseudonymized household IDs did not merge to every profile")
    # Released benchmark_predictions.csv contains an archived ensemble. Rebuild
    # it from provider rows so this fix also affects public-data reruns.
    provider_responses = responses[responses["provider"].isin(PROVIDERS)].copy()
    responses = pd.concat([
        provider_responses, make_ensemble(provider_responses)
    ], ignore_index=True)
    metrics_table = summarize(responses, args.bootstrap)
    OUT_RESPONSES.parent.mkdir(parents=True, exist_ok=True)
    responses.to_csv(OUT_RESPONSES, index=False)
    metrics_table.to_csv(OUT_METRICS, index=False)
    OUT_JSON.write_text(
        json.dumps(metrics_table.replace({np.nan: None}).to_dict("records"), indent=2) + "\n"
    )
    report = build_report(metrics_table, responses)
    OUT_REPORT.write_text(report)
    print(f"Wrote {OUT_RESPONSES}")
    print(f"Wrote {OUT_METRICS}")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_REPORT}")


if __name__ == "__main__":
    main()
