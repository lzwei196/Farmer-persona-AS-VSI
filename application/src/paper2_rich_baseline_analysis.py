"""Target-blind rich-input conventional baseline for the seven-country benchmark.

For each held-out target country, model class is chosen using only the other six
countries: each source country is held out in turn, candidate transfer models
are scored there, and the candidate with the higher mean Pearson correlation is
selected. The selected model is then refit on all six source countries and
evaluated once on the untouched target country.

This public version reads the archived three-interface benchmark predictions and
writes all regenerated analysis files under ``reproduced/analysis``.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL_SAMPLE = ROOT / "data" / "profiles" / "lsms_4country_full.csv"
EXTENSION_SAMPLE = ROOT / "data" / "profiles" / "lsms_extension_3country.csv"
AGENT_RESPONSES = ROOT / "data" / "model_outputs" / "benchmark_predictions.csv"
PREVALENCE_FILE = ROOT / "data" / "processed" / "paper2_country_wave_prevalence.csv"
PREVALENCE_WEIGHTED_FILE = (
    ROOT / "data" / "processed" / "paper2_country_wave_prevalence_weighted_sensitivity.csv"
)
TARGET = "nitrogen_kg_per_ha"
COUNTRIES = ("Ethiopia", "Malawi", "Mali", "Niger", "Nigeria", "Tanzania", "Uganda")
MODELS = ("hurdle", "random_forest")
NUMERIC = (
    "age_manager", "plot_area_GPS", "farm_size", "dist_popcenter", "elevation",
    "total_family_labor_days", "total_hired_labor_days", "family_labor_d_per_ha",
    "female_manager", "formal_education_manager", "primary_education_manager",
    "married_manager", "plot_owned", "irrigated", "intercropped",
    "drought_shock", "pests_shock", "flood_shock", "crop_shock",
)
CATEGORICAL = ("main_crop",)
SEED = 20260827


def load_data() -> pd.DataFrame:
    frames = []
    for panel, path in (("original_discovery", ORIGINAL_SAMPLE),
                        ("prospective_extension_v2", EXTENSION_SAMPLE)):
        frame = pd.read_csv(path).copy()
        frame["panel"] = panel
        frame["profile_index"] = frame.index.astype(int)
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    data = data.dropna(subset=[TARGET]).copy()
    if len(data) != 485 or set(data["country"]) != set(COUNTRIES):
        raise RuntimeError(
            "Expected 485 profiles with observed N from seven countries "
            "(five original-panel profiles have capped/missing N/ha)")
    return data


def preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("numeric", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), list(NUMERIC)),
        ("categorical", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("one_hot", OneHotEncoder(handle_unknown="ignore", min_frequency=5)),
        ]), list(CATEGORICAL)),
    ])


def predict_hurdle(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    features = list(NUMERIC + CATEGORICAL)
    y = train[TARGET].to_numpy(float)
    adoption = (y > 0).astype(int)
    classifier = Pipeline([
        ("preprocess", preprocessor()),
        ("model", LogisticRegression(max_iter=3000, C=0.5)),
    ]).fit(train[features], adoption)
    probability = classifier.predict_proba(test[features])[:, 1]
    positive = y > 0
    if positive.sum() < 8:
        conditional = np.full(len(test), y[positive].mean() if positive.any() else 0.0)
    else:
        regressor = Pipeline([
            ("preprocess", preprocessor()),
            ("model", Ridge(alpha=1.0)),
        ]).fit(train.loc[positive, features], np.log1p(y[positive]))
        conditional = np.expm1(regressor.predict(test[features])).clip(0)
    return probability * conditional


def predict_random_forest(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    features = list(NUMERIC + CATEGORICAL)
    model = Pipeline([
        ("preprocess", preprocessor()),
        ("model", RandomForestRegressor(
            n_estimators=500, min_samples_leaf=7, max_depth=6,
            random_state=SEED, n_jobs=-1)),
    ])
    return model.fit(train[features], train[TARGET]).predict(test[features])


def predict(model: str, train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    if model == "hurdle":
        return predict_hurdle(train, test)
    if model == "random_forest":
        return predict_random_forest(train, test)
    raise ValueError(model)


def correlation(observed, predicted, kind="pearson") -> float:
    observed = np.asarray(observed, float)
    predicted = np.asarray(predicted, float)
    valid = np.isfinite(observed) & np.isfinite(predicted)
    if valid.sum() < 4 or np.std(observed[valid]) < 1e-12 or np.std(predicted[valid]) < 1e-12:
        return np.nan
    if kind == "pearson":
        return float(pearsonr(observed[valid], predicted[valid])[0])
    return float(spearmanr(observed[valid], predicted[valid])[0])


def exact_permutation(x, y, kind="pearson") -> tuple[float, float]:
    observed = correlation(x, y, kind)
    null = np.asarray([
        correlation(x, permutation, kind) for permutation in itertools.permutations(y)
    ])
    return observed, float(np.mean(np.abs(null) >= abs(observed) - 1e-12))


def select_model_without_target(data: pd.DataFrame, target_country: str) -> tuple[str, dict]:
    source_countries = [country for country in COUNTRIES if country != target_country]
    scores = {model: [] for model in MODELS}
    by_fold = []
    for validation_country in source_countries:
        train = data[(data["country"] != target_country)
                     & (data["country"] != validation_country)]
        validation = data[data["country"] == validation_country]
        for model in MODELS:
            predicted = predict(model, train, validation)
            value = correlation(validation[TARGET], predicted)
            scores[model].append(value)
            by_fold.append({
                "validation_country": validation_country,
                "model": model,
                "r": value,
            })
    mean_scores = {
        model: float(np.nanmean(values)) for model, values in scores.items()
    }
    # Deterministic tie break follows MODELS order (hurdle first).
    selected = max(MODELS, key=lambda model: (mean_scores[model], -MODELS.index(model)))
    audit = {"mean_source_validation_r": mean_scores, "folds": by_fold}
    return selected, audit


def stratified_bootstrap(frame: pd.DataFrame, repetitions: int,
                         rng: np.random.Generator) -> dict:
    adoption = frame["fert_user"].to_numpy(int)
    observed = frame[TARGET].to_numpy(float)
    conventional = frame["conventional_predicted_n"].to_numpy(float)
    agent = frame["agent_predicted_n"].to_numpy(float)
    draws = {"conventional_r": [], "agent_r": [], "r_gap": []}
    for _ in range(repetitions):
        indexes = []
        for value in np.unique(adoption):
            stratum = np.flatnonzero(adoption == value)
            indexes.append(rng.choice(stratum, size=len(stratum), replace=True))
        sampled = np.concatenate(indexes)
        conventional_r = correlation(observed[sampled], conventional[sampled])
        agent_r = correlation(observed[sampled], agent[sampled])
        if np.isfinite(conventional_r) and np.isfinite(agent_r):
            draws["conventional_r"].append(conventional_r)
            draws["agent_r"].append(agent_r)
            draws["r_gap"].append(conventional_r - agent_r)
    intervals = {}
    for name, values in draws.items():
        intervals[f"{name}_lo"], intervals[f"{name}_hi"] = [
            float(value) for value in np.quantile(values, [0.025, 0.975])
        ]
    return intervals


def load_agent_ensemble() -> pd.DataFrame:
    responses = pd.read_csv(AGENT_RESPONSES)
    ensemble = responses.groupby(
        ["panel", "profile_index"], as_index=False
    )["predicted_n"].mean()
    if len(ensemble) != 490:
        raise RuntimeError(
            f"Expected 490 provider-ensemble rows, found {len(ensemble)}")
    return ensemble[["panel", "profile_index", "predicted_n"]].rename(
        columns={"predicted_n": "agent_predicted_n"})


def build_report(results: list[dict]) -> str:
    lines = [
        "# Paper 2 - target-blind rich-input conventional baseline", "",
        "For each target country, the hurdle-versus-random-forest choice uses only transfer",
        "performance among the other six countries. The target country's outcomes are untouched",
        "until the selected model is refit and evaluated once.", "",
        "| target | selected model | source-validation r: hurdle / RF | conventional r [95% CI] | agent ensemble r [95% CI] | r gap [95% CI] |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in results:
        validation = row["selection_audit"]["mean_source_validation_r"]
        lines.append(
            f"| {row['country']} | {row['selected_model']} | {validation['hurdle']:+.3f} / "
            f"{validation['random_forest']:+.3f} | {row['conventional_r']:+.3f} "
            f"[{row['conventional_r_lo']:+.3f}, {row['conventional_r_hi']:+.3f}] | "
            f"{row['agent_r']:+.3f} [{row['agent_r_lo']:+.3f}, {row['agent_r_hi']:+.3f}] | "
            f"{row['r_gap']:+.3f} [{row['r_gap_lo']:+.3f}, {row['r_gap_hi']:+.3f}] |"
        )
    frame = pd.DataFrame(results).set_index("country").loc[list(COUNTRIES)]
    prevalence = pd.read_csv(PREVALENCE_FILE).set_index("country").loc[
        list(COUNTRIES), "unweighted_fertilizer_prevalence"].to_numpy(float)
    weighted_prevalence = pd.read_csv(PREVALENCE_WEIGHTED_FILE).set_index("country").loc[
        list(COUNTRIES), "survey_weighted_fertilizer_prevalence"].to_numpy(float)
    agent_conventional_r = correlation(frame["agent_r"], frame["conventional_r"])
    agent_conventional_rho = correlation(frame["agent_r"], frame["conventional_r"], "spearman")
    lines += ["", "## Post-result descriptive country diagnostics", "",
              "These diagnostics were added after the seven target-country results were seen and",
              "are therefore descriptive, not confirmatory.", "",
              f"- Agent and conventional skill across countries: Pearson r = "
              f"{agent_conventional_r:+.3f}; Spearman rho = {agent_conventional_rho:+.3f}."]
    for label, values in (("frozen unweighted prevalence", prevalence),
                          ("survey-weighted prevalence", weighted_prevalence)):
        agent_r, agent_p = exact_permutation(values, frame["agent_r"], "pearson")
        conventional_r, conventional_p = exact_permutation(
            values, frame["conventional_r"], "pearson")
        lines.append(
            f"- {label}: agent r = {agent_r:+.3f} (exact p = {agent_p:.4f}); "
            f"conventional r = {conventional_r:+.3f} (exact p = {conventional_p:.4f})."
        )
    lines += ["", "## Interpretation boundary", "",
              "This test asks whether observable farmer covariates contain transferable signal.",
              "It does not identify model training-data composition. A conventional failure is weak",
              "evidence because source-country transfer can itself fail under distribution shift."]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=int, default=10_000)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "reproduced" / "analysis"
    )
    args = parser.parse_args()
    data = load_data()
    agent = load_agent_ensemble()
    prediction_frames = []
    results = []
    for country_index, country in enumerate(COUNTRIES):
        selected, audit = select_model_without_target(data, country)
        train = data[data["country"] != country]
        test = data[data["country"] == country].copy()
        test["selected_model"] = selected
        test["conventional_predicted_n"] = predict(selected, train, test)
        test = test.merge(agent, on=["panel", "profile_index"], how="left", validate="one_to_one")
        if test["agent_predicted_n"].isna().any():
            raise RuntimeError(f"Agent ensemble did not merge for {country}")
        conventional_r = correlation(test[TARGET], test["conventional_predicted_n"])
        agent_r = correlation(test[TARGET], test["agent_predicted_n"])
        intervals = stratified_bootstrap(
            test, args.bootstrap, np.random.default_rng(SEED + country_index))
        results.append({
            "country": country,
            "selected_model": selected,
            "conventional_r": conventional_r,
            "agent_r": agent_r,
            "r_gap": conventional_r - agent_r,
            **intervals,
            "selection_audit": audit,
        })
        prediction_frames.append(test)
    predictions = pd.concat(prediction_frames, ignore_index=True)
    report = build_report(results)
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    out_predictions = output_dir / "paper2_rival_confirmatory_predictions.csv"
    out_json = output_dir / "paper2_rival_confirmatory_results.json"
    out_report = output_dir / "paper2_rival_confirmatory_results.md"
    predictions.to_csv(out_predictions, index=False)
    out_json.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    out_report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {out_predictions}")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_report}")


if __name__ == "__main__":
    main()
