from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from figure_style import (COLORS, COUNTRY_CODES, LABEL_ORDER, PROVIDERS, PROVIDER_NAMES,
                          export_figure, panel_label, plt, style_axis)


def heatmap_grid(ax) -> None:
    ax.tick_params(length=0, colors=COLORS["muted"], labelcolor=COLORS["muted"])
    ax.set_xticks(np.arange(-0.5, len(LABEL_ORDER), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(PROVIDERS), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.0)
    for spine in ax.spines.values():
        spine.set_visible(False)


def main() -> None:
    df = pd.read_csv(HERE / "data" / "Fig5_provider_label_matrix.csv")
    df["provider"] = pd.Categorical(df["provider"], PROVIDERS, ordered=True)
    df["assigned_country"] = pd.Categorical(df["assigned_country"], LABEL_ORDER, ordered=True)
    df = df.sort_values(["provider", "assigned_country"])
    n_matrix = df.pivot(index="provider", columns="assigned_country", values="mean_predicted_n").loc[PROVIDERS, LABEL_ORDER]
    r_matrix = df.pivot(index="provider", columns="assigned_country", values="farmer_r").loc[PROVIDERS, LABEL_ORDER]
    prevalence = df[df["provider"].astype(str).eq("ensemble")].set_index("assigned_country").loc[LABEL_ORDER, "country_wave_prevalence"]

    fig = plt.figure(figsize=(7.2, 4.55))
    gs = fig.add_gridspec(3, 2, height_ratios=[0.54, 1.45, 1.45], width_ratios=[1, 0.028],
                          left=0.11, right=0.965, bottom=0.10, top=0.94, hspace=0.36, wspace=0.06)
    ax_bar = fig.add_subplot(gs[0, 0])
    ax_n = fig.add_subplot(gs[1, 0])
    cax_n = fig.add_subplot(gs[1, 1])
    ax_r = fig.add_subplot(gs[2, 0])
    cax_r = fig.add_subplot(gs[2, 1])
    x = np.arange(len(LABEL_ORDER))

    ax_bar.bar(x, prevalence.to_numpy(), color=COLORS["orange"], width=0.62)
    ax_bar.set_ylim(0, 0.60)
    ax_bar.set_yticks([0, 0.3, 0.6])
    ax_bar.set_ylabel("Prevalence")
    ax_bar.set_xticks(x, [])
    ax_bar.set_title("Assigned-label fertilizer prevalence", loc="left", pad=3)
    style_axis(ax_bar, "y")
    panel_label(ax_bar, "a", x=-0.12, y=1.20)

    n_cmap = LinearSegmentedColormap.from_list("n_rate", ["#F7FAFC", COLORS["blue_light"], "#F2B35B", COLORS["orange"]])
    im_n = ax_n.imshow(n_matrix.to_numpy(), cmap=n_cmap, aspect="auto", vmin=0, vmax=36)
    ax_n.set_yticks(np.arange(len(PROVIDERS)), [PROVIDER_NAMES[p] for p in PROVIDERS])
    ax_n.set_xticks(x, [COUNTRY_CODES[label] for label in LABEL_ORDER])
    ax_n.set_title("Mean predicted nitrogen (kg N ha$^{-1}$)", pad=4)
    for i, provider in enumerate(PROVIDERS):
        for j, label in enumerate(LABEL_ORDER):
            value = n_matrix.loc[provider, label]
            ax_n.text(j, i, f"{value:.1f}", ha="center", va="center", fontsize=7.0,
                      color="white" if value >= 24 else COLORS["ink"], fontweight="bold")
    cb_n = fig.colorbar(im_n, cax=cax_n)
    cb_n.set_ticks([0, 12, 24, 36])
    cb_n.ax.tick_params(labelsize=7, width=0.5, length=2.5)
    heatmap_grid(ax_n)

    im_r = ax_r.imshow(r_matrix.to_numpy(), cmap="RdBu_r",
                       norm=TwoSlopeNorm(vmin=-0.22, vcenter=0, vmax=0.22), aspect="auto")
    ax_r.set_yticks(np.arange(len(PROVIDERS)), [PROVIDER_NAMES[p] for p in PROVIDERS])
    ax_r.set_xticks(x, [COUNTRY_CODES[label] for label in LABEL_ORDER])
    ax_r.set_title("Farmer-level fidelity under each label (Pearson $r$)", pad=4)
    for i, provider in enumerate(PROVIDERS):
        for j, label in enumerate(LABEL_ORDER):
            value = r_matrix.loc[provider, label]
            ax_r.text(j, i, f"{value:+.2f}", ha="center", va="center", fontsize=7.0,
                      color="white" if abs(value) >= 0.14 else COLORS["ink"], fontweight="bold")
    cb_r = fig.colorbar(im_r, cax=cax_r)
    cb_r.set_ticks([-0.2, 0, 0.2])
    cb_r.ax.tick_params(labelsize=7, width=0.5, length=2.5)
    heatmap_grid(ax_r)
    panel_label(ax_r, "b", x=-0.12, y=1.18)
    export_figure(fig, HERE / "outputs", "Fig5")


if __name__ == "__main__":
    main()
