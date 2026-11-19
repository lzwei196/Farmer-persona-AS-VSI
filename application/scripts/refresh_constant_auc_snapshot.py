"""Correct archived AUC cells for constant binary-adoption scores.

An ROC AUC is defined when both observed classes are present even if every
predicted score is identical. In that case all positive-negative pairs are ties
and AUC is exactly 0.5. Pearson correlation remains undefined for a constant
continuous prediction. This script updates only those AUC fields and preserves
the archived 10,000-draw intervals for every other metric.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
RESPONSES = ROOT / "data" / "model_outputs" / "benchmark_predictions.csv"
METRICS_CSV = ROOT / "data" / "analysis" / "paper2_extension_confirmatory_metrics.csv"
METRICS_JSON = ROOT / "data" / "analysis" / "paper2_extension_confirmatory_metrics.json"


def main() -> None:
    responses = pd.read_csv(RESPONSES)
    metrics = pd.read_csv(METRICS_CSV)
    corrected = []
    for (provider, country), frame in responses.groupby(["provider", "country"]):
        observed = frame["observed_adoption"].to_numpy(float)
        predicted = frame["predicted_adoption"].to_numpy(float)
        if len(np.unique(observed)) != 2 or np.std(predicted) > 1e-12:
            continue
        auc = float(roc_auc_score(observed, predicted))
        mask = (metrics["provider"] == provider) & (metrics["country"] == country)
        if mask.sum() != 1:
            raise RuntimeError(f"Expected one metric row for {provider}/{country}")
        metrics.loc[mask, ["auc", "auc_lo", "auc_hi"]] = auc
        corrected.append({"provider": provider, "country": country, "auc": auc})
    if corrected != [{"provider": "claude", "country": "Uganda", "auc": 0.5}]:
        raise RuntimeError(f"Unexpected constant-score cells: {corrected}")
    metrics.to_csv(METRICS_CSV, index=False)
    METRICS_JSON.write_text(
        json.dumps(metrics.replace({np.nan: None}).to_dict("records"), indent=2) + "\n",
        encoding="utf-8",
    )
    print("Updated Claude/Uganda adoption AUC to the exact constant-score value 0.5.")


if __name__ == "__main__":
    main()
