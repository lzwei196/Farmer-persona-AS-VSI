"""Render all current manuscript figures from the archived figure inputs.

Fig. 1 is a supplied raster; its PDF export remains a raster PDF.
Fig. 2 is an explicitly documented redraw from archived/reported values.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "rendered",
                        help="fresh rendering directory (default: figures/rendered)")
    args = parser.parse_args()
    env = os.environ.copy()
    env["FIGURE_OUTPUT_ROOT"] = str(args.output_dir.expanduser().resolve())
    scripts = [ROOT / "Fig1" / "export_fig1.py"]
    scripts += [ROOT / f"Fig{i}" / f"Fig{i}.py" for i in range(2, 9)]
    scripts += [ROOT / "SuppFigS1" / "SuppFigS1.py"]
    for script in scripts:
        print(f"Rendering {script.relative_to(ROOT)}", flush=True)
        subprocess.run([sys.executable, str(script)], check=True, env=env)
    print(f"All figures written to {args.output_dir.expanduser().resolve()}")

if __name__ == "__main__":
    main()
