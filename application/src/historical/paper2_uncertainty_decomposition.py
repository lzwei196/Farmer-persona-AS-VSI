"""Paper 2 task 1: uncertainty and two-part decomposition of the Tanzania gap.

This analysis starts from the trusted v2 rival test and adds the row-level
uncertainty calculation requested in PAPER2_HANDOFF_v2.md:

* paired, adoption-stratified bootstrap intervals for each country's Pearson r;
* paired intervals for transfer-r minus the median r across the 12 LLM cells;
* an adoption/intensity decomposition using the hurdle transfer model;
* a household-cluster bootstrap sensitivity for the overall-r comparison.

The LLM estimand follows Paper 1: the median metric across the 3 providers x 4
prompt tiers.  The transfer estimand follows rival-test v2: the better of the
hurdle and constrained-RF predictions in each country, with that selection held
fixed during resampling.  Decomposition always uses the hurdle components,
because they provide P(adopt) and E[N | adopt] separately.

Usage (when installed under src/):
    python src/paper2_uncertainty_decomposition.py

For staging/testing from another directory:
    python paper2_uncertainty_decomposition.py \
        --root /path/to/agriagent --out-dir /tmp/paper2-task1
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")

TARGET = "nitrogen_kg_per_ha"
PROVIDERS = ("claude", "codex", "kimi")
TIERS = (1, 2, 3, 4)
COUNTRIES = ("Ethiopia", "Malawi", "Nigeria", "Tanzania")
EXPECTED_AGENT_R = {
    "Ethiopia": 0.2949534761554949,
    "Malawi": 0.3093328280953941,
    "Nigeria": 0.3513746566750881,
    "Tanzania": 0.07624611970509472,
}
EXPECTED_TRANSFER_R = {
    "Ethiopia": 0.3891973586663431,
    "Malawi": 0.15649129143178506,
    "Nigeria": 0.4209479559137166,
    "Tanzania": 0.2746155865817379,
}


def finite_float(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return np.nan
    return out if np.isfinite(out) else np.nan


def bool_score(value):
    if value is True:
        return 1.0
    if value is False:
        return 0.0
    if isinstance(value, str):
        value = value.strip().lower()
        if value in {"yes", "true", "1"}:
            return 1.0
        if value in {"no", "false", "0"}:
            return 0.0
    if isinstance(value, (int, float)) and np.isfinite(value):
        return float(bool(value))
    return np.nan


def pearson(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 3 or np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return np.nan
    x = x - x.mean()
    y = y - y.mean()
    return float(np.sum(x * y) / np.sqrt(np.sum(x * x) * np.sum(y * y)))


def spearman(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 3:
        return np.nan
    return pearson(rankdata(x), rankdata(y))


def auc(y, score):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    ok = np.isfinite(score)
    y, score = y[ok], score[ok]
    n_pos = int(y.sum())
    n_neg = int(len(y) - n_pos)
    if n_pos == 0 or n_neg == 0:
        return np.nan
    ranks = rankdata(score)
    return float((ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def brier(y, score):
    y = np.asarray(y, dtype=float)
    score = np.asarray(score, dtype=float)
    ok = np.isfinite(score) & np.isfinite(y)
    return float(np.mean((score[ok] - y[ok]) ** 2)) if ok.any() else np.nan


def rowwise_corr(x, y):
    """Pearson correlations across columns for two equally shaped matrices."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x = x - np.mean(x, axis=1, keepdims=True)
    y = y - np.mean(y, axis=1, keepdims=True)
    den = np.sqrt(np.sum(x * x, axis=1) * np.sum(y * y, axis=1))
    return np.divide(np.sum(x * y, axis=1), den,
                     out=np.full(len(x), np.nan), where=den > 1e-12)


def boot_corr(pred, y, indices):
    return rowwise_corr(np.asarray(pred)[indices], np.asarray(y)[indices])


def boot_spearman(pred, y, indices):
    px = rankdata(np.asarray(pred)[indices], axis=1)
    py = rankdata(np.asarray(y)[indices], axis=1)
    return rowwise_corr(px, py)


def boot_auc(score, y, indices):
    """AUC per bootstrap row, including the usual half-credit for ties."""
    yy = np.asarray(y, dtype=int)[indices]
    ss = np.asarray(score, dtype=float)[indices]
    ranks = rankdata(ss, axis=1)
    n_pos = yy.sum(axis=1)
    n_neg = yy.shape[1] - n_pos
    rank_sum = np.sum(ranks * yy, axis=1)
    num = rank_sum - n_pos * (n_pos + 1) / 2
    den = n_pos * n_neg
    return np.divide(num, den, out=np.full(len(indices), np.nan), where=den > 0)


def interval(samples, point):
    samples = np.asarray(samples, dtype=float)
    samples = samples[np.isfinite(samples)]
    if not len(samples):
        return {"estimate": finite_float(point), "ci_low": np.nan, "ci_high": np.nan,
                "n_boot_valid": 0}
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return {"estimate": finite_float(point), "ci_low": float(lo), "ci_high": float(hi),
            "n_boot_valid": int(len(samples))}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_agents(root, rows):
    """Return aligned rate/adoption arrays for all 12 provider-tier cells."""
    idx_to_pos = {int(idx): pos for pos, idx in enumerate(rows["farmer_idx"])}
    rates, adoption, files_used = {}, {}, []
    for provider in PROVIDERS:
        for tier in TIERS:
            cell = f"{provider}_T{tier}"
            rate = np.full(len(rows), np.nan)
            adopt = np.full(len(rows), np.nan)
            pattern = root / "results" / "full" / "lsms" / provider / f"tier{tier}" / "*.json"
            for filename in sorted(glob.glob(str(pattern))):
                with open(filename) as f:
                    item = json.load(f)
                idx = item.get("farmer_idx")
                if idx not in idx_to_pos:
                    continue
                decision = item.get("decision") or {}
                pos = idx_to_pos[int(idx)]
                rate[pos] = finite_float(decision.get(TARGET))
                adopt[pos] = bool_score(decision.get("inorganic_fertilizer"))
                files_used.append(filename)
            if np.isfinite(rate).sum() != len(rows):
                raise RuntimeError(f"Incomplete numeric-rate coverage for {cell}: "
                                   f"{np.isfinite(rate).sum()}/{len(rows)}")
            if np.isfinite(adopt).sum() != len(rows):
                raise RuntimeError(f"Incomplete adoption coverage for {cell}: "
                                   f"{np.isfinite(adopt).sum()}/{len(rows)}")
            rates[cell] = rate
            adoption[cell] = adopt
    return rates, adoption, files_used


def hurdle_components(rival, x_train, y_train, x_test):
    """Exact v2 hurdle fit, returning expected rate, adoption p, and E[N|N>0]."""
    y_train = np.asarray(y_train, dtype=float)
    adopted = (y_train > 0).astype(int)
    if len(set(adopted)) < 2:
        p = np.full(len(x_test), float(adopted.mean()))
        mu = np.full(len(x_test), float(y_train[y_train > 0].mean())
                     if np.any(y_train > 0) else 0.0)
        return p * mu, p, mu

    classifier = Pipeline([
        ("p", rival.pre()),
        ("m", LogisticRegression(max_iter=2000, C=0.5)),
    ]).fit(x_train, adopted)
    p = classifier.predict_proba(x_test)[:, 1]
    positive = np.where(y_train > 0)[0]
    if len(positive) < 8:
        mu = np.full(len(x_test), float(y_train[positive].mean()) if len(positive) else 0.0)
    else:
        regression = Pipeline([
            ("p", rival.pre()),
            ("m", Ridge(alpha=1.0)),
        ]).fit(x_train.iloc[positive], np.log1p(y_train[positive]))
        mu = np.expm1(regression.predict(x_test)).clip(0)
    return p * mu, p, mu


def fit_transfer(root, rows):
    sys.path.insert(0, str(root / "src" / "historical"))
    import paper2_rival_test_v2 as rival  # pylint: disable=import-outside-toplevel

    features = rival.NUM + rival.CAT
    out = {}
    for country in COUNTRIES:
        train = rows[rows["country"] != country]
        test = rows[rows["country"] == country]
        expected, p, mu = hurdle_components(
            rival, train[features], train[TARGET].values, test[features])
        rf = rival.rf_fit_predict(train[features], train[TARGET].values, test[features])
        y = test[TARGET].to_numpy(float)
        r_hurdle, r_rf = pearson(expected, y), pearson(rf, y)
        selected_model = "hurdle" if r_hurdle >= r_rf else "rf"
        selected = expected if selected_model == "hurdle" else rf
        out[country] = {
            "row_positions": test["row_position"].to_numpy(int),
            "hurdle_expected": expected,
            "hurdle_probability": p,
            "hurdle_conditional_intensity": mu,
            "rf": rf,
            "selected": selected,
            "selected_model": selected_model,
            "r_hurdle": r_hurdle,
            "r_rf": r_rf,
        }
    return out


def stratified_boot_indices(adopted, n_boot, rng):
    adopted = np.asarray(adopted, dtype=int)
    zero = np.flatnonzero(adopted == 0)
    positive = np.flatnonzero(adopted == 1)
    z_boot = rng.choice(zero, size=(n_boot, len(zero)), replace=True)
    p_boot = rng.choice(positive, size=(n_boot, len(positive)), replace=True)
    return np.concatenate([z_boot, p_boot], axis=1), p_boot


def analyze_country(country, rows, transfer, agent_rates, agent_adoption, n_boot, rng):
    positions = transfer["row_positions"]
    sub = rows.iloc[positions]
    y = sub[TARGET].to_numpy(float)
    adopted = (y > 0).astype(int)
    cells = list(agent_rates)
    rate = {cell: agent_rates[cell][positions] for cell in cells}
    adopt_score = {cell: agent_adoption[cell][positions] for cell in cells}

    all_boot, positive_boot = stratified_boot_indices(adopted, n_boot, rng)

    # Overall Pearson r: fixed v2-selected transfer versus median of the 12 LLM cells.
    transfer_r_point = pearson(transfer["selected"], y)
    agent_r_points = np.array([pearson(rate[cell], y) for cell in cells])
    transfer_r_boot = boot_corr(transfer["selected"], y, all_boot)
    agent_r_boot_cells = np.vstack([boot_corr(rate[cell], y, all_boot) for cell in cells])
    agent_r_boot = np.nanmedian(agent_r_boot_cells, axis=0)
    agent_r_point = float(np.nanmedian(agent_r_points))
    delta_r_point = transfer_r_point - agent_r_point
    delta_r_boot = transfer_r_boot - agent_r_boot

    # Adoption: hurdle probability versus each LLM cell's explicit binary decision.
    transfer_auc_point = auc(adopted, transfer["hurdle_probability"])
    transfer_brier_point = brier(adopted, transfer["hurdle_probability"])
    agent_auc_points = np.array([auc(adopted, adopt_score[cell]) for cell in cells])
    agent_brier_points = np.array([brier(adopted, adopt_score[cell]) for cell in cells])
    transfer_auc_boot = boot_auc(transfer["hurdle_probability"], adopted, all_boot)
    transfer_brier_boot = np.mean(
        (transfer["hurdle_probability"][all_boot] - adopted[all_boot]) ** 2, axis=1)
    agent_auc_boot_cells = np.vstack([
        boot_auc(adopt_score[cell], adopted, all_boot) for cell in cells
    ])
    agent_brier_boot_cells = np.vstack([
        np.mean((adopt_score[cell][all_boot] - adopted[all_boot]) ** 2, axis=1)
        for cell in cells
    ])
    agent_auc_boot = np.nanmedian(agent_auc_boot_cells, axis=0)
    agent_brier_boot = np.nanmedian(agent_brier_boot_cells, axis=0)
    agent_auc_point = float(np.nanmedian(agent_auc_points))
    agent_brier_point = float(np.nanmedian(agent_brier_points))

    # Conditional intensity: observed positive-rate plots only.  For the transfer model this is
    # E[N | N>0], not p*E[N | N>0].  LLMs emit only one rate, so their stated numeric rate is used;
    # zero predictions remain zero, making false-negative adoption visible in this fixed subset.
    positive = np.flatnonzero(adopted == 1)
    y_positive = y[positive]
    transfer_mu = transfer["hurdle_conditional_intensity"]
    transfer_rho_point = spearman(transfer_mu[positive], y_positive)
    transfer_mae_point = float(np.mean(np.abs(transfer_mu[positive] - y_positive)))
    agent_rho_points = np.array([spearman(rate[cell][positive], y_positive) for cell in cells])
    agent_mae_points = np.array([
        np.mean(np.abs(rate[cell][positive] - y_positive)) for cell in cells
    ])
    transfer_rho_boot = boot_spearman(transfer_mu, y, positive_boot)
    transfer_mae_boot = np.mean(
        np.abs(transfer_mu[positive_boot] - y[positive_boot]), axis=1)
    agent_rho_boot_cells = np.vstack([
        boot_spearman(rate[cell], y, positive_boot) for cell in cells
    ])
    agent_mae_boot_cells = np.vstack([
        np.mean(np.abs(rate[cell][positive_boot] - y[positive_boot]), axis=1)
        for cell in cells
    ])
    agent_rho_boot = np.nanmedian(agent_rho_boot_cells, axis=0)
    agent_mae_boot = np.nanmedian(agent_mae_boot_cells, axis=0)
    agent_rho_point = float(np.nanmedian(agent_rho_points))
    agent_mae_point = float(np.nanmedian(agent_mae_points))

    # Positive advantage always means the transfer model performed better.
    adoption_auc_adv = transfer_auc_boot - agent_auc_boot
    adoption_brier_adv = agent_brier_boot - transfer_brier_boot
    intensity_rho_adv = transfer_rho_boot - agent_rho_boot
    intensity_mae_adv = agent_mae_boot - transfer_mae_boot

    result = {
        "n_plots": int(len(sub)),
        "n_households": int(sub["hh_id_merge"].nunique()),
        "n_adopters": int(adopted.sum()),
        "n_nonadopters": int(len(adopted) - adopted.sum()),
        "transfer_model_for_overall_r": transfer["selected_model"],
        "candidate_transfer_r": {
            "hurdle": transfer["r_hurdle"],
            "rf": transfer["r_rf"],
        },
        "overall_r": {
            "transfer": interval(transfer_r_boot, transfer_r_point),
            "agent_median": interval(agent_r_boot, agent_r_point),
            "transfer_minus_agent": interval(delta_r_boot, delta_r_point),
            "agent_cell_range": [float(np.nanmin(agent_r_points)),
                                 float(np.nanmax(agent_r_points))],
        },
        "adoption": {
            "auc": {
                "transfer_hurdle": interval(transfer_auc_boot, transfer_auc_point),
                "agent_median": interval(agent_auc_boot, agent_auc_point),
                "transfer_advantage": interval(adoption_auc_adv,
                                               transfer_auc_point - agent_auc_point),
            },
            "brier": {
                "transfer_hurdle": interval(transfer_brier_boot, transfer_brier_point),
                "agent_median": interval(agent_brier_boot, agent_brier_point),
                "transfer_advantage": interval(adoption_brier_adv,
                                               agent_brier_point - transfer_brier_point),
            },
        },
        "conditional_intensity_on_observed_positive_plots": {
            "spearman_rho": {
                "transfer_hurdle": interval(transfer_rho_boot, transfer_rho_point),
                "agent_median": interval(agent_rho_boot, agent_rho_point),
                "transfer_advantage": interval(intensity_rho_adv,
                                               transfer_rho_point - agent_rho_point),
            },
            "mae_kg_per_ha": {
                "transfer_hurdle": interval(transfer_mae_boot, transfer_mae_point),
                "agent_median": interval(agent_mae_boot, agent_mae_point),
                "transfer_advantage": interval(intensity_mae_adv,
                                               agent_mae_point - transfer_mae_point),
            },
        },
        "agent_adoption_rate_disagreement": {
            cell: float(np.mean(adopt_score[cell] != (rate[cell] > 0))) for cell in cells
        },
    }
    boot = {
        "transfer_r": transfer_r_boot,
        "agent_r": agent_r_boot,
        "delta_r": delta_r_boot,
    }
    return result, boot


def cluster_bootstrap_r(rows, transfer, agent_rates, n_boot, rng):
    """Household-cluster sensitivity; model selection remains fixed as in the primary analysis."""
    positions = transfer["row_positions"]
    sub = rows.iloc[positions].reset_index(drop=True)
    y = sub[TARGET].to_numpy(float)
    pred = transfer["selected"]
    rates = np.vstack([agent_rates[cell][positions] for cell in agent_rates])
    clusters = [g.index.to_numpy(int) for _, g in sub.groupby("hh_id_merge", sort=False)]
    out_transfer = np.full(n_boot, np.nan)
    out_agent = np.full(n_boot, np.nan)
    for b in range(n_boot):
        chosen = rng.integers(0, len(clusters), size=len(clusters))
        idx = np.concatenate([clusters[i] for i in chosen])
        out_transfer[b] = pearson(pred[idx], y[idx])
        out_agent[b] = np.nanmedian([pearson(cell[idx], y[idx]) for cell in rates])
    return out_transfer, out_agent, out_transfer - out_agent


def validate_reproduction(results):
    problems = []
    for country in COUNTRIES:
        ar = results[country]["overall_r"]["agent_median"]["estimate"]
        tr = results[country]["overall_r"]["transfer"]["estimate"]
        if abs(ar - EXPECTED_AGENT_R[country]) > 5e-4:
            problems.append(f"{country} agent r: {ar} != {EXPECTED_AGENT_R[country]}")
        if abs(tr - EXPECTED_TRANSFER_R[country]) > 5e-4:
            problems.append(f"{country} transfer r: {tr} != {EXPECTED_TRANSFER_R[country]}")
    if problems:
        raise RuntimeError("Failed to reproduce trusted v2 values:\n" + "\n".join(problems))


def fmt(stat, digits=3):
    return (f"{stat['estimate']:+.{digits}f} "
            f"[{stat['ci_low']:+.{digits}f}, {stat['ci_high']:+.{digits}f}]")


def markdown_report(payload):
    method = payload["method"]
    results = payload["countries"]
    contrasts = payload["contrasts"]
    tz = results["Tanzania"]
    tz_gap = tz["overall_r"]["transfer_minus_agent"]
    diff = contrasts["tanzania_gap_minus_other_three_gap"]

    if tz_gap["ci_low"] > 0 and diff["ci_low"] > 0:
        verdict = ("The Tanzania point gap survives both absolute and cross-country uncertainty "
                   "checks: both 95% intervals exclude zero.")
    elif tz_gap["ci_low"] > 0:
        verdict = ("The Tanzania transfer advantage itself excludes zero, but its excess over the "
                   "other-country gap does not; the country-specific contrast remains imprecise.")
    else:
        verdict = ("The Tanzania point estimate still favors transfer, but its 95% interval includes "
                   "zero. The v2 ordering is reproduced; finite-sample uncertainty does not support "
                   "a definitive country-specific gap claim on these 70 plots alone.")

    lines = [
        "# Paper 2 — Tanzania-gap uncertainty and two-part decomposition",
        "",
        "Generated by `src/paper2_uncertainty_decomposition.py`.",
        "",
        "## Result",
        "",
        verdict,
        "",
        f"Tanzania transfer-minus-agent r = **{fmt(tz_gap)}**.  The corresponding other-three "
        f"mean gap is **{fmt(contrasts['other_three_mean_gap'])}**, and the Tanzania-minus-others "
        f"difference is **{fmt(diff)}**.",
        "",
        "These are percentile bootstrap intervals, not null-hypothesis p-values. The selected "
        "transfer family is held fixed during resampling, so the intervals do not correct for "
        "the v2 model-selection step.",
        "",
        "## Overall Pearson r",
        "",
        "Agent = median across the 12 provider × tier cells. Transfer = the v2-selected "
        "leave-country-out prediction. Brackets are 95% bootstrap intervals.",
        "",
        "| country | plots / households | transfer model | transfer r | agent median r | transfer − agent | agent cell range |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for country in COUNTRIES:
        item = results[country]
        overall = item["overall_r"]
        cell_range = overall["agent_cell_range"]
        lines.append(
            f"| {country} | {item['n_plots']} / {item['n_households']} | "
            f"{item['transfer_model_for_overall_r']} | {fmt(overall['transfer'])} | "
            f"{fmt(overall['agent_median'])} | {fmt(overall['transfer_minus_agent'])} | "
            f"{cell_range[0]:+.3f} to {cell_range[1]:+.3f} |"
        )

    lines += [
        "",
        "### Cross-country contrasts",
        "",
        "| contrast | estimate [95% interval] |",
        "|---|---:|",
        f"| Other-three mean transfer r | {fmt(contrasts['other_three_transfer_r'])} |",
        f"| Other-three mean agent r | {fmt(contrasts['other_three_agent_r'])} |",
        f"| Other-three mean gap | {fmt(contrasts['other_three_mean_gap'])} |",
        f"| Tanzania gap minus other-three gap | {fmt(diff)} |",
        "",
        "## Decomposition",
        "",
        "The decomposition uses the hurdle model for every country: continuous P(adopt) for "
        "AUC/Brier, and E[N | N>0] on the observed positive-rate plots for intensity. LLM "
        "adoption is its explicit yes/no response; its intensity is its stated numeric rate. "
        "A positive advantage means transfer performed better for every metric below.",
        "",
        "### Adoption",
        "",
        "| country | transfer AUC | agent median AUC | AUC advantage | transfer Brier | agent median Brier | Brier advantage |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for country in COUNTRIES:
        adoption = results[country]["adoption"]
        lines.append(
            f"| {country} | {fmt(adoption['auc']['transfer_hurdle'])} | "
            f"{fmt(adoption['auc']['agent_median'])} | {fmt(adoption['auc']['transfer_advantage'])} | "
            f"{fmt(adoption['brier']['transfer_hurdle'])} | "
            f"{fmt(adoption['brier']['agent_median'])} | "
            f"{fmt(adoption['brier']['transfer_advantage'])} |"
        )

    lines += [
        "",
        "### Conditional intensity among observed adopters",
        "",
        "| country | positive plots | transfer rho | agent median rho | rho advantage | transfer MAE | agent median MAE | MAE advantage |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for country in COUNTRIES:
        intensity = results[country]["conditional_intensity_on_observed_positive_plots"]
        lines.append(
            f"| {country} | {results[country]['n_adopters']} | "
            f"{fmt(intensity['spearman_rho']['transfer_hurdle'])} | "
            f"{fmt(intensity['spearman_rho']['agent_median'])} | "
            f"{fmt(intensity['spearman_rho']['transfer_advantage'])} | "
            f"{fmt(intensity['mae_kg_per_ha']['transfer_hurdle'], 1)} | "
            f"{fmt(intensity['mae_kg_per_ha']['agent_median'], 1)} | "
            f"{fmt(intensity['mae_kg_per_ha']['transfer_advantage'], 1)} |"
        )

    tz_adopt = tz["adoption"]
    tz_int = tz["conditional_intensity_on_observed_positive_plots"]
    lines += [
        "",
        "### Tanzania reading",
        "",
        f"- Adoption: transfer AUC {fmt(tz_adopt['auc']['transfer_hurdle'])} versus agent "
        f"median {fmt(tz_adopt['auc']['agent_median'])}; transfer Brier "
        f"{fmt(tz_adopt['brier']['transfer_hurdle'])} versus agent median "
        f"{fmt(tz_adopt['brier']['agent_median'])}.",
        f"- Positive-rate intensity: transfer rho {fmt(tz_int['spearman_rho']['transfer_hurdle'])} "
        f"versus agent median {fmt(tz_int['spearman_rho']['agent_median'])}; transfer MAE "
        f"{fmt(tz_int['mae_kg_per_ha']['transfer_hurdle'], 1)} kg/ha versus agent median "
        f"{fmt(tz_int['mae_kg_per_ha']['agent_median'], 1)} kg/ha.",
        "",
        "## Household-cluster sensitivity",
        "",
        "The primary bootstrap preserves the experiment's approximately 50/50 adoption design. "
        "Because 6 households contribute a second plot, a secondary bootstrap resamples whole "
        "households; it does not force the adoption balance.",
        "",
        "| country | transfer − agent r, household-cluster bootstrap |",
        "|---|---:|",
    ]
    for country in COUNTRIES:
        lines.append(f"| {country} | {fmt(results[country]['cluster_sensitivity']['transfer_minus_agent'])} |")

    mismatch = np.array([
        value
        for country in COUNTRIES
        for value in results[country]["agent_adoption_rate_disagreement"].values()
    ])
    lines += [
        "",
        "## Method and cautions",
        "",
        f"- Primary bootstrap: {method['n_bootstrap']:,} paired resamples within each country's "
        "observed adoption strata; seed " + str(method["seed"]) + ".",
        f"- Cluster sensitivity: {method['n_cluster_bootstrap']:,} household resamples.",
        "- The four-country sample was deliberately balanced on adoption and is not weighted to "
        "national adoption prevalence. These metrics characterize this experimental sample.",
        "- The agent summary treats the 12 completed model×tier configurations as fixed and "
        "quantifies sampling uncertainty over plots; it does not treat model choice as a random effect.",
        "- Conditional-intensity comparison uses a common observed-positive subset. An LLM zero "
        "rate remains zero there, so its intensity metric includes false-negative adoption; this "
        "is transparent but cannot be a pure latent E[N | adopt] estimate because the LLM did not "
        "return one.",
        f"- Across country×cell combinations, disagreement between the LLM's explicit adoption "
        f"answer and whether its numeric rate was positive ranged from {mismatch.min():.1%} to "
        f"{mismatch.max():.1%}.",
        "- Nigeria's hurdle intensity model extrapolates badly in absolute-error terms; use the "
        "constrained RF for Nigeria's overall-r comparison, as v2 did.",
        "",
        "Machine-readable results and the aligned prediction table are written beside this report.",
    ]
    return "\n".join(lines) + "\n"


def serializable(value):
    if isinstance(value, dict):
        return {str(k): serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    if isinstance(value, np.ndarray):
        return [serializable(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    return value


def build_prediction_table(rows, transfer, agent_rates, agent_adoption):
    out = rows[["farmer_idx", "country", "hh_id_merge", "plot_id_merge", TARGET]].copy()
    out["observed_adoption"] = (out[TARGET] > 0).astype(int)
    for country in COUNTRIES:
        item = transfer[country]
        pos = item["row_positions"]
        out.loc[pos, "transfer_hurdle_expected"] = item["hurdle_expected"]
        out.loc[pos, "transfer_adoption_probability"] = item["hurdle_probability"]
        out.loc[pos, "transfer_conditional_intensity"] = item["hurdle_conditional_intensity"]
        out.loc[pos, "transfer_rf"] = item["rf"]
        out.loc[pos, "transfer_selected"] = item["selected"]
        out.loc[pos, "transfer_selected_model"] = item["selected_model"]
    for cell in agent_rates:
        out[f"agent_rate_{cell}"] = agent_rates[cell]
        out[f"agent_adopt_{cell}"] = agent_adoption[cell]
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[2]
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--n-bootstrap", type=int, default=10_000)
    parser.add_argument("--n-cluster-bootstrap", type=int, default=5_000)
    parser.add_argument("--seed", type=int, default=20260826)
    args = parser.parse_args()

    root = args.root.resolve()
    out_dir = (args.out_dir or root / "reproduced" / "historical").resolve()
    sample_path = root / "data" / "lsms" / "lsms_4country_full.csv"
    raw = pd.read_csv(sample_path)
    raw["farmer_idx"] = raw.index.astype(int)
    rows = raw.dropna(subset=[TARGET]).copy().reset_index(drop=True)
    rows["row_position"] = np.arange(len(rows), dtype=int)
    agent_rates, agent_adoption, files_used = load_agents(root, rows)
    transfer = fit_transfer(root, rows)

    rng = np.random.default_rng(args.seed)
    country_results, country_boot = {}, {}
    for country in COUNTRIES:
        country_results[country], country_boot[country] = analyze_country(
            country, rows, transfer[country], agent_rates, agent_adoption,
            args.n_bootstrap, rng)

    validate_reproduction(country_results)

    others = [country for country in COUNTRIES if country != "Tanzania"]
    other_transfer_boot = np.mean([country_boot[c]["transfer_r"] for c in others], axis=0)
    other_agent_boot = np.mean([country_boot[c]["agent_r"] for c in others], axis=0)
    other_gap_boot = other_transfer_boot - other_agent_boot
    tz_diff_boot = country_boot["Tanzania"]["delta_r"] - other_gap_boot
    other_transfer_point = float(np.mean([
        country_results[c]["overall_r"]["transfer"]["estimate"] for c in others
    ]))
    other_agent_point = float(np.mean([
        country_results[c]["overall_r"]["agent_median"]["estimate"] for c in others
    ]))
    other_gap_point = other_transfer_point - other_agent_point
    tz_gap_point = country_results["Tanzania"]["overall_r"]["transfer_minus_agent"]["estimate"]
    contrasts = {
        "other_three_transfer_r": interval(other_transfer_boot, other_transfer_point),
        "other_three_agent_r": interval(other_agent_boot, other_agent_point),
        "other_three_mean_gap": interval(other_gap_boot, other_gap_point),
        "tanzania_gap_minus_other_three_gap": interval(tz_diff_boot,
                                                       tz_gap_point - other_gap_point),
    }

    cluster_rng = np.random.default_rng(args.seed + 1)
    for country in COUNTRIES:
        trb, agb, db = cluster_bootstrap_r(
            rows, transfer[country], agent_rates, args.n_cluster_bootstrap, cluster_rng)
        point = country_results[country]["overall_r"]
        country_results[country]["cluster_sensitivity"] = {
            "transfer": interval(trb, point["transfer"]["estimate"]),
            "agent_median": interval(agb, point["agent_median"]["estimate"]),
            "transfer_minus_agent": interval(db, point["transfer_minus_agent"]["estimate"]),
        }

    payload = {
        "method": {
            "analysis": "paired adoption-stratified percentile bootstrap",
            "n_bootstrap": args.n_bootstrap,
            "cluster_sensitivity": "household cluster percentile bootstrap",
            "n_cluster_bootstrap": args.n_cluster_bootstrap,
            "seed": args.seed,
            "agent_estimand": "median metric across 3 providers x 4 tiers",
            "overall_transfer_estimand": "v2-selected leave-country-out model, selection fixed",
            "decomposition_transfer_estimand": "leave-country-out hurdle components",
            "sample_sha256": sha256(sample_path),
            "n_agent_result_files_used": len(files_used),
        },
        "countries": country_results,
        "contrasts": contrasts,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "paper2_uncertainty_decomposition.json"
    md_path = out_dir / "paper2_uncertainty_decomposition.md"
    csv_path = out_dir / "paper2_uncertainty_predictions.csv"
    with open(json_path, "w") as f:
        json.dump(serializable(payload), f, indent=2)
        f.write("\n")
    with open(md_path, "w") as f:
        f.write(markdown_report(payload))
    build_prediction_table(rows, transfer, agent_rates, agent_adoption).to_csv(csv_path, index=False)

    print(markdown_report(payload))
    print(f"JSON: {json_path}")
    print(f"Predictions: {csv_path}")


if __name__ == "__main__":
    main()
