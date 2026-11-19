from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script: str, *arguments: str) -> None:
    command = [sys.executable, str(ROOT / script), *arguments]
    print("Running:", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recompute core Paper 2 analyses from public consolidated data."
    )
    parser.add_argument(
        "--bootstrap",
        type=int,
        default=1_000,
        help="Bootstrap repetitions; use 10000 for the archived analysis.",
    )
    args = parser.parse_args()
    repetitions = str(args.bootstrap)
    run("src/paper2_extension_confirmatory_analysis.py", "--bootstrap", repetitions)
    run("src/paper2_rich_baseline_analysis.py", "--bootstrap", repetitions)
    run("src/paper2_matched_baseline_analysis.py", "--bootstrap", repetitions)
    run("src/paper2_population_consequence.py", "--bootstrap", repetitions)
    run(
        "src/paper2_country_label_ablation_analysis.py",
        "--n-bootstrap",
        repetitions,
    )
    run("src/paper2_country_prior_matrix_analysis.py", "--bootstrap", repetitions)
    run("src/paper2_review_sensitivity_analysis.py", "--bootstrap", repetitions)
    run("scripts/compare_reproduced.py")
    print("Core analyses reproduced successfully.")


if __name__ == "__main__":
    main()
