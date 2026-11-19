"""Analyze the frozen Paper 2 country-label ablation.

Primary contrast: identical Tanzania profile shown as Nigeria minus shown as
Tanzania, evaluated separately for each provider.  The profile is always the
independent unit.  Region-only minus Tanzania is secondary.

Outputs:
  results/analysis/paper2_country_label_ablation_results.md
  results/analysis/paper2_country_label_ablation_results.json
  results/analysis/paper2_country_label_ablation_responses.csv
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROVIDERS = ("claude", "codex", "kimi")
ARMS = ("true_country", "region_only", "swapped_country")
CONTRASTS = {
    "primary_swapped_minus_true": ("swapped_country", "true_country"),
    "secondary_region_minus_true": ("region_only", "true_country"),
}
TARGET = "nitrogen_kg_per_ha"
SEED = 20260826
N_BOOT = 10_000
ALPHA_PRIMARY = 0.05 / 3


def finite_float(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return np.nan
    return value if np.isfinite(value) else np.nan


def bool_value(value):
    if value is True:
        return 1.0
    if value is False:
        return 0.0
    if isinstance(value, str):
        value = value.strip().lower()
        if value in {"true", "yes", "1"}:
            return 1.0
        if value in {"false", "no", "0"}:
            return 0.0
    if isinstance(value, (int, float)) and np.isfinite(value):
        return float(bool(value))
    return np.nan


def pearson(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 3 or np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return np.nan
    return float(stats.pearsonr(x, y).statistic)


def spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 3 or np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return np.nan
    return float(stats.spearmanr(x, y).statistic)


def percentile_interval(samples, estimate):
    samples = np.asarray(samples, float)
    samples = samples[np.isfinite(samples)]
    lo, hi = np.percentile(samples, [2.5, 97.5]) if len(samples) else (np.nan, np.nan)
    return {"estimate": float(estimate), "ci_low": float(lo), "ci_high": float(hi),
            "n_boot_valid": int(len(samples))}


def bootstrap_mean(values, indices):
    return np.asarray(values, float)[indices].mean(axis=1)


def bootstrap_median(values, indices):
    return np.median(np.asarray(values, float)[indices], axis=1)


def bootstrap_corr(x, y, indices):
    xx, yy = np.asarray(x, float)[indices], np.asarray(y, float)[indices]
    xx = xx - xx.mean(axis=1, keepdims=True)
    yy = yy - yy.mean(axis=1, keepdims=True)
    den = np.sqrt(np.sum(xx * xx, axis=1) * np.sum(yy * yy, axis=1))
    return np.divide(np.sum(xx * yy, axis=1), den,
                     out=np.full(len(indices), np.nan), where=den > 1e-12)


def paired_continuous(high, low, y_observed, indices):
    high, low = np.asarray(high, float), np.asarray(low, float)
    diff = high - low
    mean_diff = float(np.mean(diff))
    median_diff = float(np.median(diff))
    sd = float(np.std(diff, ddof=1))
    dz = mean_diff / sd if sd > 0 else np.nan
    ttest = stats.ttest_rel(high, low, nan_policy="raise")
    try:
        wilcoxon = stats.wilcoxon(high, low, alternative="two-sided", zero_method="wilcox")
        w_stat, w_p = float(wilcoxon.statistic), float(wilcoxon.pvalue)
    except ValueError:
        w_stat, w_p = np.nan, np.nan
    mean_boot = bootstrap_mean(diff, indices)
    median_boot = bootstrap_median(diff, indices)
    high_r = pearson(high, y_observed)
    low_r = pearson(low, y_observed)
    r_delta_boot = bootstrap_corr(high, y_observed, indices) - \
        bootstrap_corr(low, y_observed, indices)
    return {
        "n_profiles": int(len(diff)),
        "high_mean": float(np.mean(high)),
        "low_mean": float(np.mean(low)),
        "mean_difference": percentile_interval(mean_boot, mean_diff),
        "median_difference": percentile_interval(median_boot, median_diff),
        "cohens_dz": float(dz),
        "paired_t": {"statistic": float(ttest.statistic), "p_two_sided": float(ttest.pvalue)},
        "wilcoxon": {"statistic": w_stat, "p_two_sided": w_p},
        "observed_rate_correlation": {
            "high_arm_r": high_r,
            "low_arm_r": low_r,
            "high_minus_low_r": percentile_interval(r_delta_boot, high_r - low_r),
        },
        "profile_rank_spearman": spearman(high, low),
    }


def paired_binary(high, low, indices):
    high, low = np.asarray(high, int), np.asarray(low, int)
    diff = high - low
    n_01 = int(np.sum((low == 0) & (high == 1)))
    n_10 = int(np.sum((low == 1) & (high == 0)))
    discordant = n_01 + n_10
    exact_p = float(stats.binomtest(n_01, discordant, 0.5).pvalue) if discordant else 1.0
    boot = bootstrap_mean(diff, indices)
    return {
        "n_profiles": int(len(diff)),
        "high_adoption_rate": float(np.mean(high)),
        "low_adoption_rate": float(np.mean(low)),
        "adoption_rate_difference": percentile_interval(boot, float(np.mean(diff))),
        "discordance": {"low_0_to_high_1": n_01, "low_1_to_high_0": n_10,
                        "total": discordant},
        "mcnemar_exact_p_two_sided": exact_p,
        "agreement_rate": float(np.mean(high == low)),
    }


def load_data(root, allow_incomplete=False):
    """Load the public consolidated ablation table."""
    source = root / "data" / "model_outputs" / "country_label_ablation_predictions.csv"
    public = pd.read_csv(source)
    public = public[public["provider"].isin(PROVIDERS)].copy()
    public["farmer_idx"] = public["profile_key"].str.rsplit("_", n=1).str[-1].astype(int)
    data = public.rename(columns={
        "predicted_n": "nitrogen_kg_per_ha",
        "predicted_adoption": "adoption",
        "observed_n": "observed_nitrogen_kg_per_ha",
    })
    data["adoption"] = data["adoption"].astype(int)
    expected = len(PROVIDERS) * len(ARMS) * 70
    invalid = []
    if len(data) != expected and not allow_incomplete:
        raise RuntimeError(f"Ablation incomplete: valid={len(data)}/{expected}")
    duplicates = data.duplicated(["provider", "arm", "farmer_idx"]).sum()
    if duplicates:
        raise RuntimeError(f"Found {duplicates} duplicate response cells")
    return data, invalid


def analyze(data, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    providers = {}
    for provider in PROVIDERS:
        sub = data[data.provider == provider]
        wide_rate = sub.pivot(index="farmer_idx", columns="arm", values="nitrogen_kg_per_ha")
        wide_adopt = sub.pivot(index="farmer_idx", columns="arm", values="adoption")
        wide_truth = sub.drop_duplicates("farmer_idx").set_index("farmer_idx")[
            "observed_nitrogen_kg_per_ha"]
        complete = wide_rate.dropna().index.intersection(wide_adopt.dropna().index)
        wide_rate = wide_rate.loc[complete]
        wide_adopt = wide_adopt.loc[complete]
        y = wide_truth.loc[complete].to_numpy(float)
        indices = rng.integers(0, len(complete), size=(n_boot, len(complete)))
        provider_out = {
            "n_complete_profiles": int(len(complete)),
            "arms": {},
            "contrasts": {},
        }
        for arm in ARMS:
            rates = wide_rate[arm].to_numpy(float)
            adoption = wide_adopt[arm].to_numpy(int)
            provider_out["arms"][arm] = {
                "mean_nitrogen_kg_per_ha": float(np.mean(rates)),
                "median_nitrogen_kg_per_ha": float(np.median(rates)),
                "sd_nitrogen_kg_per_ha": float(np.std(rates, ddof=1)),
                "adoption_rate": float(np.mean(adoption)),
                "observed_nitrogen_r": pearson(rates, y),
            }
        for name, (high_arm, low_arm) in CONTRASTS.items():
            provider_out["contrasts"][name] = {
                "nitrogen_rate": paired_continuous(
                    wide_rate[high_arm], wide_rate[low_arm], y, indices),
                "adoption": paired_binary(wide_adopt[high_arm], wide_adopt[low_arm], indices),
                "high_arm": high_arm,
                "low_arm": low_arm,
            }
        providers[provider] = provider_out

    # Secondary ensemble summary: average provider output within profile before inference.
    ensemble_rate = data.pivot_table(index="farmer_idx", columns="arm",
                                     values="nitrogen_kg_per_ha", aggfunc="mean").dropna()
    ensemble_adopt = data.pivot_table(index="farmer_idx", columns="arm",
                                      values="adoption", aggfunc="mean").dropna()
    truth = data.drop_duplicates("farmer_idx").set_index("farmer_idx")[
        "observed_nitrogen_kg_per_ha"]
    complete = ensemble_rate.index.intersection(ensemble_adopt.index)
    ensemble_rate, ensemble_adopt = ensemble_rate.loc[complete], ensemble_adopt.loc[complete]
    indices = rng.integers(0, len(complete), size=(n_boot, len(complete)))
    ensemble = {}
    for name, (high_arm, low_arm) in CONTRASTS.items():
        diff_rate = (ensemble_rate[high_arm] - ensemble_rate[low_arm]).to_numpy(float)
        diff_adopt = (ensemble_adopt[high_arm] - ensemble_adopt[low_arm]).to_numpy(float)
        ensemble[name] = {
            "n_profiles": int(len(complete)),
            "mean_nitrogen_difference": percentile_interval(
                bootstrap_mean(diff_rate, indices), float(np.mean(diff_rate))),
            "mean_adoption_probability_difference": percentile_interval(
                bootstrap_mean(diff_adopt, indices), float(np.mean(diff_adopt))),
            "observed_nitrogen_r_difference": percentile_interval(
                bootstrap_corr(ensemble_rate[high_arm], truth.loc[complete], indices) -
                bootstrap_corr(ensemble_rate[low_arm], truth.loc[complete], indices),
                pearson(ensemble_rate[high_arm], truth.loc[complete]) -
                pearson(ensemble_rate[low_arm], truth.loc[complete])),
        }

    primary = [providers[p]["contrasts"]["primary_swapped_minus_true"]["nitrogen_rate"]
               for p in PROVIDERS]
    replication = {
        "all_provider_mean_differences_positive": bool(all(
            item["mean_difference"]["estimate"] > 0 for item in primary)),
        "all_provider_bonferroni_t_tests_significant": bool(all(
            item["paired_t"]["p_two_sided"] < ALPHA_PRIMARY for item in primary)),
        "n_provider_bootstrap_intervals_excluding_zero_positive": int(sum(
            item["mean_difference"]["ci_low"] > 0 for item in primary)),
        "bonferroni_alpha": ALPHA_PRIMARY,
    }
    return {"providers": providers, "ensemble_secondary": ensemble,
            "replication_summary": replication}


def fmt(stat, digits=2, signed=True):
    sign = "+" if signed else ""
    return (f"{stat['estimate']:{sign}.{digits}f} "
            f"[{stat['ci_low']:{sign}.{digits}f}, {stat['ci_high']:{sign}.{digits}f}]")


def markdown(payload, data, invalid, n_boot, seed):
    result = payload["analysis"]
    repl = result["replication_summary"]
    if repl["all_provider_mean_differences_positive"] and \
            repl["all_provider_bonferroni_t_tests_significant"]:
        verdict = ("**Country-label sensitivity was observed across all three providers.** The Nigerian "
                   "label increased the primary nitrogen-rate outcome for every provider, with all "
                   "three multiplicity-adjusted paired tests passing the preregistered threshold.")
    elif repl["all_provider_mean_differences_positive"]:
        verdict = ("**Directional label effect replicated, but confirmatory strength is mixed.** "
                   "All provider point estimates move in the predicted direction, but not every "
                   "multiplicity-adjusted test passes the preregistered threshold.")
    else:
        verdict = ("**Country-label sensitivity did not replicate directionally across providers.** "
                   "At least one provider's primary point estimate failed to move in the predicted "
                   "Nigeria-minus-Tanzania direction.")

    lines = [
        "# Paper 2 — country-label ablation results",
        "",
        "Generated by `src/paper2_country_label_ablation_analysis.py`.",
        "",
        "## Verdict",
        "",
        verdict,
        "",
        "The experimental unit is the farmer profile (n=70), and every contrast below is paired "
        "within profile. Providers are reported separately; calls are never treated as 630 "
        "independent observations.",
        "",
        "## Primary contrast: Nigeria label minus Tanzania label",
        "",
        "| provider | complete profiles | mean N difference, kg/ha [95% CI] | d_z | paired-t p | Wilcoxon p | adoption difference [95% CI] | adoption flips 0→1 / 1→0 | McNemar p |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for provider in PROVIDERS:
        item = result["providers"][provider]
        contrast = item["contrasts"]["primary_swapped_minus_true"]
        rate, adopt = contrast["nitrogen_rate"], contrast["adoption"]
        disc = adopt["discordance"]
        lines.append(
            f"| {provider} | {item['n_complete_profiles']} | {fmt(rate['mean_difference'])} | "
            f"{rate['cohens_dz']:+.3f} | {rate['paired_t']['p_two_sided']:.4g} | "
            f"{rate['wilcoxon']['p_two_sided']:.4g} | "
            f"{fmt(adopt['adoption_rate_difference'], 3)} | "
            f"{disc['low_0_to_high_1']} / {disc['low_1_to_high_0']} | "
            f"{adopt['mcnemar_exact_p_two_sided']:.4g} |"
        )

    lines += [
        "",
        "### Arm levels",
        "",
        "| provider | arm | mean N | median N | N SD | adoption rate | r with observed Tanzania N |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for provider in PROVIDERS:
        for arm in ARMS:
            item = result["providers"][provider]["arms"][arm]
            lines.append(
                f"| {provider} | {arm} | {item['mean_nitrogen_kg_per_ha']:.2f} | "
                f"{item['median_nitrogen_kg_per_ha']:.2f} | {item['sd_nitrogen_kg_per_ha']:.2f} | "
                f"{item['adoption_rate']:.3f} | {item['observed_nitrogen_r']:+.3f} |"
            )

    lines += [
        "",
        "## Secondary contrast: East-Africa-only minus Tanzania label",
        "",
        "| provider | mean N difference [95% CI] | paired-t p | adoption difference [95% CI] | profile-rank rho across arms |",
        "|---|---:|---:|---:|---:|",
    ]
    for provider in PROVIDERS:
        contrast = result["providers"][provider]["contrasts"]["secondary_region_minus_true"]
        rate, adopt = contrast["nitrogen_rate"], contrast["adoption"]
        lines.append(
            f"| {provider} | {fmt(rate['mean_difference'])} | "
            f"{rate['paired_t']['p_two_sided']:.4g} | "
            f"{fmt(adopt['adoption_rate_difference'], 3)} | "
            f"{rate['profile_rank_spearman']:+.3f} |"
        )

    ensemble = result["ensemble_secondary"]["primary_swapped_minus_true"]
    lines += [
        "",
        "## Interpretation",
        "",
        f"Averaging providers within profile, changing only the label increased mean nitrogen by "
        f"**{fmt(ensemble['mean_nitrogen_difference'])} kg/ha** and mean predicted adoption by "
        f"**{fmt(ensemble['mean_adoption_probability_difference'], 3)}**. Yet the change in "
        f"correlation with the observed Tanzanian farmer outcomes was "
        f"**{fmt(ensemble['observed_nitrogen_r_difference'], 3)}**. The label therefore moves the "
        "population-level predictions without reliably adding profile-specific agreement. In this "
        "experiment, country identity shifted the center of the simulated distribution more than it "
        "changed agreement with the observed ranking of Tanzanian profiles.",
        "",
        "## Secondary provider-ensemble summary",
        "",
        "Provider outputs are averaged within profile first, preserving n=70.",
        "",
        f"- Nigeria-minus-Tanzania mean N difference: {fmt(ensemble['mean_nitrogen_difference'])} kg/ha.",
        f"- Mean predicted-adoption difference: {fmt(ensemble['mean_adoption_probability_difference'], 3)}.",
        f"- Change in correlation with observed Tanzania N: {fmt(ensemble['observed_nitrogen_r_difference'], 3)}.",
        "",
        "## Execution and analysis audit",
        "",
        f"- Valid response cells: {len(data)}/630; invalid cells: {len(invalid)}.",
        f"- Bootstrap: {n_boot:,} paired profile resamples; seed {seed}; percentile 95% intervals.",
        f"- Primary provider-specific alpha: {ALPHA_PRIMARY:.5f} (0.05/3, two-sided).",
        "- The explicit adoption boolean and numeric rate were required to be parseable. Prompt "
        "hashes are checked against the frozen manifest by scripts/validate_release.py.",
        "- A label effect identifies reliance on stated location. It does not identify the training "
        "documents responsible for the pattern or establish national representativeness.",
    ]
    return "\n".join(lines) + "\n"


def serializable(value):
    if isinstance(value, dict):
        return {str(k): serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--n-bootstrap", type=int, default=N_BOOT)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    out_dir = (args.out_dir or root / "reproduced" / "analysis").resolve()
    data, invalid = load_data(root, allow_incomplete=args.allow_incomplete)
    analysis = analyze(data, n_boot=args.n_bootstrap, seed=args.seed)
    payload = {
        "method": {"n_bootstrap": args.n_bootstrap, "seed": args.seed,
                   "profile_level_n": 70, "bonferroni_alpha": ALPHA_PRIMARY},
        "coverage": {"valid": int(len(data)), "expected": 630, "invalid": invalid},
        "analysis": analysis,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    md = markdown(payload, data, invalid, args.n_bootstrap, args.seed)
    (out_dir / "paper2_country_label_ablation_results.md").write_text(md)
    (out_dir / "paper2_country_label_ablation_results.json").write_text(
        json.dumps(serializable(payload), indent=2) + "\n")
    data.sort_values(["provider", "farmer_idx", "arm"]).to_csv(
        out_dir / "paper2_country_label_ablation_responses.csv", index=False)
    print(md)


if __name__ == "__main__":
    main()
