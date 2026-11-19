"""Target-blind conventional baseline restricted to the LLM profile fields.

The baseline uses only variables shown in the least-context profile prompt. For
each target country, hurdle and constrained-random-forest candidates are chosen
using leave-one-source-country-out validation among the other six countries.
The selected model is then fitted to all six source countries and evaluated on
the untouched target country. Archived richer-covariate and LLM predictions are
read from the public release so all three methods are compared on identical
rows.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
PROFILES_FILE = ROOT / "data" / "processed" / "frozen_profiles.csv"
RICH_PREDICTIONS_FILE = ROOT / "data" / "model_outputs" / "rival_test_predictions.csv"
TARGET = "nitrogen_kg_per_ha"
COUNTRIES = ("Ethiopia", "Malawi", "Mali", "Niger", "Nigeria", "Tanzania", "Uganda")
MODELS = ("hurdle", "random_forest")
NUMERIC = (
    "age_manager", "female_manager", "formal_education_manager",
    "plot_area_GPS", "farm_size", "plot_owned", "intercropped",
)
CATEGORICAL = ("country", "region_clean", "main_crop")
SEED = 20260827


def load_data() -> pd.DataFrame:
    profiles = pd.read_csv(PROFILES_FILE).copy()
    profiles["profile_index"] = profiles["profile_key"].str.rsplit("_", n=1).str[-1].astype(int)
    profiles["panel"] = profiles["panel"].map({
        "original": "original_discovery",
        "extension": "prospective_extension_v2",
    })
    profiles = profiles.dropna(subset=[TARGET]).copy()
    rich = pd.read_csv(RICH_PREDICTIONS_FILE)[[
        "panel", "profile_index", "selected_model", "conventional_predicted_n",
        "agent_predicted_n",
    ]].rename(columns={
        "selected_model": "rich_selected_model",
        "conventional_predicted_n": "rich_predicted_n",
    })
    data = profiles.merge(
        rich, on=["panel", "profile_index"], how="inner", validate="one_to_one"
    )
    if len(data) != 485 or set(data["country"]) != set(COUNTRIES):
        raise RuntimeError(f"Expected 485 valid profiles from seven countries, found {len(data)}")
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
    adopted = (y > 0).astype(int)
    if len(np.unique(adopted)) < 2:
        probability = np.full(len(test), adopted.mean())
    else:
        classifier = Pipeline([
            ("preprocess", preprocessor()),
            ("model", LogisticRegression(max_iter=3000, C=0.5)),
        ]).fit(train[features], adopted)
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
            random_state=SEED, n_jobs=-1,
        )),
    ])
    return model.fit(train[features], train[TARGET]).predict(test[features])


def predict(model: str, train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    if model == "hurdle":
        return predict_hurdle(train, test)
    if model == "random_forest":
        return predict_random_forest(train, test)
    raise ValueError(model)


def correlation(observed, predicted) -> float:
    observed = np.asarray(observed, float)
    predicted = np.asarray(predicted, float)
    valid = np.isfinite(observed) & np.isfinite(predicted)
    if valid.sum() < 4 or np.std(observed[valid]) < 1e-12 or np.std(predicted[valid]) < 1e-12:
        return np.nan
    return float(pearsonr(observed[valid], predicted[valid])[0])


def select_model_without_target(data: pd.DataFrame, target_country: str) -> tuple[str, dict]:
    source_countries = [country for country in COUNTRIES if country != target_country]
    scores = {model: [] for model in MODELS}
    folds = []
    for validation_country in source_countries:
        train = data[(data["country"] != target_country)
                     & (data["country"] != validation_country)]
        validation = data[data["country"] == validation_country]
        for model in MODELS:
            value = correlation(validation[TARGET], predict(model, train, validation))
            scores[model].append(value)
            folds.append({
                "validation_country": validation_country,
                "model": model,
                "r": value,
            })
    mean_scores = {model: float(np.nanmean(values)) for model, values in scores.items()}
    selected = max(MODELS, key=lambda model: (mean_scores[model], -MODELS.index(model)))
    return selected, {"mean_source_validation_r": mean_scores, "folds": folds}


def bootstrap(frame: pd.DataFrame, repetitions: int, rng: np.random.Generator) -> dict:
    adoption = frame["fert_user"].to_numpy(int)
    observed = frame[TARGET].to_numpy(float)
    predictions = {
        "matched_r": frame["matched_predicted_n"].to_numpy(float),
        "rich_r": frame["rich_predicted_n"].to_numpy(float),
        "agent_r": frame["agent_predicted_n"].to_numpy(float),
    }
    draws = {name: [] for name in predictions}
    draws.update({"matched_minus_agent": [], "matched_minus_rich": []})
    for _ in range(repetitions):
        sampled = []
        for value in np.unique(adoption):
            positions = np.flatnonzero(adoption == value)
            sampled.append(rng.choice(positions, size=len(positions), replace=True))
        sampled = np.concatenate(sampled)
        values = {
            name: correlation(observed[sampled], predicted[sampled])
            for name, predicted in predictions.items()
        }
        for name, value in values.items():
            draws[name].append(value)
        draws["matched_minus_agent"].append(values["matched_r"] - values["agent_r"])
        draws["matched_minus_rich"].append(values["matched_r"] - values["rich_r"])
    intervals = {}
    for name, values in draws.items():
        finite = np.asarray(values, float)
        finite = finite[np.isfinite(finite)]
        intervals[f"{name}_lo"], intervals[f"{name}_hi"] = [
            float(value) for value in np.quantile(finite, [0.025, 0.975])
        ]
    return intervals


def fmt_interval(row: dict, name: str) -> str:
    return f"{row[name]:+.3f} [{row[name + '_lo']:+.3f}, {row[name + '_hi']:+.3f}]"


def build_report(results: list[dict]) -> str:
    lines = [
        "# Matched-input target-blind conventional baseline",
        "",
        "The matched baseline uses only the fields visible in the least-context LLM profile:",
        "country, administrative location, manager age, sex and formal education, GPS plot area,",
        "farm size, main crop, plot ownership and intercropping. Target-country outcomes are",
        "excluded from candidate selection and fitting.",
        "",
        "| Country | Selected matched model | Matched-input r [95% CI] | Rich-input r [95% CI] | LLM ensemble r [95% CI] | Matched minus LLM [95% CI] |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['country']} | {row['matched_selected_model']} | "
            f"{fmt_interval(row, 'matched_r')} | {fmt_interval(row, 'rich_r')} | "
            f"{fmt_interval(row, 'agent_r')} | {fmt_interval(row, 'matched_minus_agent')} |"
        )
    lines += [
        "",
        "The matched-input benchmark removes the information advantage of the richer transfer",
        "model but does not make the learning procedures equivalent: the conventional baseline",
        "is fitted on labeled source-country records, whereas the LLM is used without local",
        "fine-tuning. Confidence intervals are paired, adoption-stratified profile bootstraps.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=int, default=10_000)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "reproduced" / "analysis"
    )
    args = parser.parse_args()
    data = load_data()
    prediction_frames = []
    results = []
    for country_index, country in enumerate(COUNTRIES):
        selected, audit = select_model_without_target(data, country)
        train = data[data["country"] != country]
        test = data[data["country"] == country].copy()
        test["matched_selected_model"] = selected
        test["matched_predicted_n"] = predict(selected, train, test)
        point = {
            "country": country,
            "n": len(test),
            "matched_selected_model": selected,
            "matched_r": correlation(test[TARGET], test["matched_predicted_n"]),
            "rich_r": correlation(test[TARGET], test["rich_predicted_n"]),
            "agent_r": correlation(test[TARGET], test["agent_predicted_n"]),
            "selection_audit": audit,
        }
        point["matched_minus_agent"] = point["matched_r"] - point["agent_r"]
        point["matched_minus_rich"] = point["matched_r"] - point["rich_r"]
        point.update(bootstrap(
            test, args.bootstrap, np.random.default_rng(SEED + country_index)
        ))
        results.append(point)
        prediction_frames.append(test[[
            "panel", "profile_index", "profile_key", "country", TARGET, "fert_user",
            "matched_selected_model", "matched_predicted_n", "rich_selected_model",
            "rich_predicted_n", "agent_predicted_n",
        ]])

    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = [{key: value for key, value in row.items() if key != "selection_audit"}
                    for row in results]
    pd.DataFrame(summary_rows).to_csv(
        output_dir / "paper2_matched_baseline_results.csv", index=False
    )
    pd.concat(prediction_frames, ignore_index=True).to_csv(
        output_dir / "paper2_matched_baseline_predictions.csv", index=False
    )
    (output_dir / "paper2_matched_baseline_results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "paper2_matched_baseline_results.md").write_text(
        build_report(results), encoding="utf-8"
    )
    print(build_report(results))
    print(f"Wrote matched-baseline outputs to {output_dir}")


if __name__ == "__main__":
    main()
