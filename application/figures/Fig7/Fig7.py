from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

HERE = Path(__file__).absolute().parent
sys.path.insert(0, str(HERE.parent))
from figure_style import (COLORS, COUNTRY_CODES, LABEL_ORDER, export_figure, panel_label,
                          plt, style_axis)


def main() -> None:
    grouped = pd.read_csv(HERE / "data" / "Fig7_profile_label_predictions.csv")
    observed = grouped[["farmer_idx", "observed_n", "observed_adoption"]].drop_duplicates()
    observed = observed.sort_values(["observed_n", "farmer_idx"]).reset_index(drop=True)
    rank_lookup = {farmer: idx + 1 for idx, farmer in enumerate(observed["farmer_idx"])}
    grouped["rank"] = grouped["farmer_idx"].map(rank_lookup)

    fig = plt.figure(figsize=(7.2, 4.45))
    gs = fig.add_gridspec(2, 2, width_ratios=[2.15, 0.95], height_ratios=[1, 1],
                          left=0.105, right=0.985, bottom=0.12, top=0.94,
                          hspace=0.52, wspace=0.38)
    left = gs[:, 0].subgridspec(
        2, 2, width_ratios=[1.0, 0.045], height_ratios=[0.36, 1.0],
        hspace=0.08, wspace=0.06,
    )
    ax_obs = fig.add_subplot(left[0, 0])
    ax_heat = fig.add_subplot(left[1, 0], sharex=ax_obs)
    ax_cbar = fig.add_subplot(left[1, 1])
    ax_cbar_spacer = fig.add_subplot(left[0, 1])
    ax_cbar_spacer.axis("off")
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 1])

    x = np.arange(1, len(observed) + 1)
    obs_n = observed["observed_n"].to_numpy()
    ax_obs.fill_between(x, 0, obs_n, color=COLORS["orange_light"], alpha=0.75, zorder=1)
    ax_obs.plot(x, obs_n, color=COLORS["orange"], lw=1.25, zorder=3)
    ax_obs.scatter(x, obs_n, s=8, facecolor=np.where(observed["observed_adoption"].to_numpy() > 0,
                                                    COLORS["orange"], "white"),
                   edgecolor=COLORS["orange"], lw=0.35, zorder=4)
    ax_obs.set_yscale("symlog", linthresh=1.0, linscale=0.55)
    ax_obs.set_ylim(0, 230)
    ax_obs.set_yticks([0, 10, 50, 200], ["0", "10", "50", "200"])
    ax_obs.tick_params(axis="x", labelbottom=False)
    ax_obs.set_ylabel("Observed\nkg N ha$^{-1}$")
    ax_obs.set_title("Observed ranking is not recovered", pad=5)
    style_axis(ax_obs, "y")
    panel_label(ax_obs, "a", x=-0.15, y=1.18)

    heat = grouped.pivot(index="assigned_country", columns="rank", values="ensemble_predicted_n").loc[LABEL_ORDER].to_numpy()
    cmap = LinearSegmentedColormap.from_list("prediction", ["#F8FAFC", "#DCEAF2", "#8CB8D1", COLORS["blue_dark"]])
    im = ax_heat.imshow(heat, aspect="auto", interpolation="nearest", cmap=cmap, vmin=0, vmax=65,
                        extent=(0.5, len(observed) + 0.5, len(LABEL_ORDER) - 0.5, -0.5))
    ax_heat.set_yticks(np.arange(len(LABEL_ORDER)), [COUNTRY_CODES[label] for label in LABEL_ORDER])
    ax_heat.set_xticks([1, 10, 20, 40, 60, 70])
    ax_heat.set_xlim(0.5, 70.5)
    ax_heat.set_xlabel("Tanzanian profiles ranked by observed nitrogen")
    ax_heat.set_ylabel("Assigned label")
    for ypos in np.arange(0.5, len(LABEL_ORDER), 1):
        ax_heat.axhline(ypos, color="white", lw=0.8)
    for spine in ax_heat.spines.values():
        spine.set_visible(False)
    ax_heat.tick_params(length=0, colors=COLORS["ink"], labelcolor=COLORS["ink"])
    cbar = fig.colorbar(im, cax=ax_cbar)
    cbar.set_ticks([0, 20, 40, 60])
    cbar.set_label("Predicted kg N ha$^{-1}$", fontsize=7.5)
    cbar.ax.tick_params(labelsize=7, width=0.5, length=2.5)

    label_summary = grouped.groupby("assigned_country").apply(
        lambda frame: frame["ensemble_predicted_n"].corr(frame["observed_n"]), include_groups=False
    ).reindex(LABEL_ORDER)
    y = np.arange(len(LABEL_ORDER))
    colors = [COLORS["orange"] if value >= 0 else COLORS["blue"] for value in label_summary]
    ax_b.axvline(0, color=COLORS["zero"], lw=0.8)
    ax_b.hlines(y, 0, label_summary.to_numpy(), color=COLORS["zero"], lw=1.0)
    ax_b.scatter(label_summary.to_numpy(), y, c=colors, s=28, edgecolor="white", lw=0.4, zorder=3)
    ax_b.set_yticks(y, [COUNTRY_CODES[label] for label in LABEL_ORDER])
    ax_b.set_xlim(-0.16, 0.16)
    ax_b.set_xticks([-0.15, 0, 0.15])
    ax_b.invert_yaxis()
    ax_b.set_xlabel("Pearson $r$")
    ax_b.set_title("Farmer-level fidelity", pad=5)
    style_axis(ax_b, "x")
    panel_label(ax_b, "b", x=-0.24, y=1.16)

    box_data = [grouped[grouped["assigned_country"].eq(label)]["ensemble_predicted_n"].to_numpy()
                for label in LABEL_ORDER]
    box = ax_c.boxplot(box_data, orientation="horizontal", patch_artist=True,
                       widths=0.60, showfliers=False,
                       medianprops={"color": COLORS["ink"], "lw": 1.0},
                       boxprops={"lw": 0.7, "color": COLORS["blue"]},
                       whiskerprops={"lw": 0.7, "color": COLORS["muted"]},
                       capprops={"lw": 0.7, "color": COLORS["muted"]})
    for patch, label in zip(box["boxes"], LABEL_ORDER):
        patch.set_facecolor(COLORS["orange_light"] if label == "Tanzania" else COLORS["blue_light"])
        patch.set_alpha(0.9)
    ax_c.set_yticks(y + 1, [COUNTRY_CODES[label] for label in LABEL_ORDER])
    ax_c.invert_yaxis()
    ax_c.set_xlim(0, 72)
    ax_c.set_xticks([0, 25, 50, 75])
    ax_c.set_xlabel("Predicted kg N ha$^{-1}$")
    ax_c.set_title("Prediction distribution", pad=5)
    style_axis(ax_c, "x")
    panel_label(ax_c, "c", x=-0.24, y=1.16)
    export_figure(fig, HERE / "outputs", "Fig7")


if __name__ == "__main__":
    main()
