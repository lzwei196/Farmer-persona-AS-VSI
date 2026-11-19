from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from figure_style import COLORS, COUNTRIES, export_figure, panel_label, plt, style_axis


def main() -> None:
    df = pd.read_csv(HERE / "data" / "Fig3_population_calibration.csv")
    df = df.set_index("country").loc[COUNTRIES].reset_index()
    y = np.arange(len(df))
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.35), sharey=True)
    fig.subplots_adjust(left=0.105, right=0.985, bottom=0.20, top=0.79, wspace=0.25)
    specs = [
        ("a", "Adoption", "observed_adoption", "predicted_adoption", "predicted_adoption_lo",
         "predicted_adoption_hi", "Mean adoption", (0, 0.9), [0, 0.3, 0.6, 0.9]),
        ("b", "Nitrogen rate", "observed_n_kg_per_ha", "predicted_n_kg_per_ha",
         "predicted_n_kg_per_ha_lo", "predicted_n_kg_per_ha_hi", "kg N ha$^{-1}$", (0, 42), [0, 14, 28, 42]),
        ("c", "Nitrogen quantity", "observed_n_kg_per_plot", "predicted_n_kg_per_plot",
         "predicted_n_kg_per_plot_lo", "predicted_n_kg_per_plot_hi", "kg N plot$^{-1}$", (0, 62), [0, 20, 40, 60]),
    ]
    for ax, (label, title, obs_col, pred_col, lo_col, hi_col, xlabel, xlim, xticks) in zip(axes, specs):
        tza_idx = int(df.index[df["country"].eq("Tanzania")][0])
        ax.axhspan(tza_idx - 0.45, tza_idx + 0.45, color=COLORS["highlight"], zorder=-2)
        obs, pred = df[obs_col].to_numpy(), df[pred_col].to_numpy()
        lo, hi = df[lo_col].to_numpy(), df[hi_col].to_numpy()
        for idx in range(len(df)):
            ax.plot([obs[idx], pred[idx]], [idx, idx], color=COLORS["zero"], lw=1.0, zorder=1)
        ax.errorbar(pred, y, xerr=np.vstack([pred - lo, hi - pred]), fmt="o",
                    color=COLORS["orange"], ecolor=COLORS["orange"], ms=4.2,
                    elinewidth=0.9, capsize=2.1, label="LLM ensemble", zorder=3)
        ax.scatter(obs, y, s=25, facecolor="white", edgecolor=COLORS["ink"],
                   linewidth=0.85, zorder=4, label="Observed target")
        ax.set_xlim(*xlim)
        ax.set_xticks(xticks)
        ax.set_xlabel(xlabel)
        ax.set_title(title, pad=6)
        ax.set_ylim(len(df) - 0.5, -0.5)
        style_axis(ax, "x")
        panel_label(ax, label, x=-0.22 if label == "a" else -0.14, y=1.15)
    axes[0].set_yticks(y, df["country"])
    axes[1].tick_params(axis="y", left=False, labelleft=False)
    axes[2].tick_params(axis="y", left=False, labelleft=False)
    handles, labels = axes[0].get_legend_handles_labels()
    order = [1, 0]
    fig.legend([handles[i] for i in order], [labels[i] for i in order],
               loc="upper center", bbox_to_anchor=(0.54, 0.97), ncol=2)
    export_figure(fig, HERE / "outputs", "Fig3")


if __name__ == "__main__":
    main()
