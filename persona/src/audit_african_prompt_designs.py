"""Recalculate archived African prompt-design metrics using shared T1 responses."""

import argparse
import csv
import gzip
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUTCOMES = {
    "nitrogen_kg_per_ha": "nitrogen_kg_per_ha",
    "family_labor_days": "total_family_labor_days",
    "hired_labor_days": "total_hired_labor_days",
}
PROVIDERS = ("claude", "codex", "kimi")


def read_archive(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def empirical_ks_similarity(simulated, observed):
    values = np.sort(np.concatenate((simulated, observed)))
    sim_cdf = np.searchsorted(np.sort(simulated), values, side="right") / simulated.size
    obs_cdf = np.searchsorted(np.sort(observed), values, side="right") / observed.size
    return float(1 - np.max(np.abs(sim_cdf - obs_cdf)))


def metrics(simulated, observed):
    keep = np.isfinite(simulated) & np.isfinite(observed)
    simulated, observed = simulated[keep], observed[keep]
    p90, p95 = np.quantile(observed, [0.9, 0.95])
    mae = np.mean(np.abs(simulated - observed))
    median_null_mae = np.mean(np.abs(np.median(observed) - observed))
    return {
        "n": observed.size,
        "r": float(np.corrcoef(simulated, observed)[0, 1]),
        "mae": float(mae),
        "median_null_mae": float(median_null_mae),
        "median_null_skill": float(1 - mae / median_null_mae),
        "ks_similarity": empirical_ks_similarity(simulated, observed),
        "observed_mean": float(np.mean(observed)),
        "mean": float(np.mean(simulated)),
        "zero_fraction": float(np.mean(simulated == 0)),
        "sd_ratio": float(np.std(simulated) / np.std(observed)),
        "p90_ratio": float(np.quantile(simulated, 0.9) / p90),
        "observed_p90": float(p90),
        "observed_p95": float(p95),
        "share_at_least_observed_p90": float(np.mean(simulated >= p90)),
        "share_at_least_observed_p95": float(np.mean(simulated >= p95)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-responses", required=True, type=Path)
    args = parser.parse_args()
    with (ROOT / "data/lsms/lsms_4country_full.csv").open(encoding="utf-8") as stream:
        profiles = list(csv.DictReader(stream))

    shared = [
        {**row, "tier": 1}
        for row in read_archive(args.shared_responses)
        if row["experiment"] == "benchmark_original"
    ]
    added = read_archive(ROOT / "results/full/lsms/archived_T2_T3_T4.jsonl.gz")
    cell_responses = {}
    for row in shared + added:
        index = int(row["profile_key"].rsplit("_", 1)[1])
        assert row["country"] == profiles[index]["country"]
        key = row["provider"], row["tier"], index
        assert key not in cell_responses
        cell_responses[key] = row["decision"]

    output = {}
    for agent_field, survey_field in OUTCOMES.items():
        observed = np.array([float(row[survey_field] or "nan") for row in profiles])
        output[agent_field] = {}
        for provider in PROVIDERS:
            for tier in range(1, 5):
                simulated = np.array([
                    float(cell_responses[provider, tier, index][agent_field])
                    for index in range(len(profiles))
                ])
                output[agent_field][f"{provider}_T{tier}"] = metrics(simulated, observed)
    print(json.dumps(output, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
