from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from figure_style import COLORS, export_figure, panel_label, plt, style_axis


def main() -> None:
    df = pd.read_csv(HERE / "data" / "Fig8_profile_population_effects.csv").sort_values("rank").reset_index(drop=True)
    total_tonnes = float(df["expanded_delta_tonnes"].sum())
    top10 = float(df.head(10)["expanded_delta_tonnes"].sum() / total_tonnes)
    top20 = float(df.head(20)["expanded_delta_tonnes"].sum() / total_tonnes)
    positive_share = float((df["delta_predicted_n"] > 0).mean())
    median_delta = float(df["delta_predicted_n"].median())
    quartiles = df.groupby("plot_area_quartile", observed=False)["expanded_delta_tonnes"].sum().reindex(
        ["Q1 smallest", "Q2", "Q3", "Q4 largest"])

    fig = plt.figure(figsize=(7.2, 4.35))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.42, 1.0], left=0.10, right=0.985,
                          bottom=0.12, top=0.94, hspace=0.55, wspace=0.38)
    ax_a = fig.add_subplot(gs[:, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 1])

    x = df["rank"].to_numpy()
    cumulative = df["cumulative_share"].to_numpy() * 100
    ax_a.axvspan(0.5, 10.5, color=COLORS["highlight"], lw=0, zorder=0)
    ax_a.fill_between(x, 0, cumulative, color=COLORS["blue_light"], alpha=0.55, zorder=1)
    ax_a.plot(x, cumulative, color=COLORS["blue"], lw=1.8, zorder=3)
    ax_a.scatter([10, 20], [top10 * 100, top20 * 100], s=34,
                 color=[COLORS["orange"], COLORS["ink"]], edgecolor="white", lw=0.5, zorder=4)
    ax_a.axvline(10, color=COLORS["orange"], lw=0.8, ls="--")
    ax_a.axvline(20, color=COLORS["muted"], lw=0.8, ls="--")
    ax_a.annotate(f"Top 10: {top10:.0%}", (10, top10 * 100), xytext=(6, -24),
                  textcoords="offset points", color=COLORS["orange"], fontsize=8, fontweight="bold")
    ax_a.annotate(f"Top 20: {top20:.0%}", (20, top20 * 100), xytext=(8, -22),
                  textcoords="offset points", color=COLORS["ink"], fontsize=8, fontweight="bold")
    ax_a.text(0.97, 0.08, f"Net contrast: {total_tonnes / 1000:.0f} thousand tonnes N",
              transform=ax_a.transAxes, ha="right", va="bottom", fontsize=7.6, color=COLORS["ink"])
    ax_a.set_xlim(1, len(df))
    ax_a.set_ylim(0, 105)
    ax_a.set_xticks([1, 10, 20, 40, 70])
    ax_a.set_yticks([0, 25, 50, 75, 100])
    ax_a.set_xlabel("Profiles ranked by expanded label effect")
    ax_a.set_ylabel("Cumulative share of net label contrast (%)")
    ax_a.set_title("Concentration of population-scaled impact", pad=5)
    style_axis(ax_a, "both")
    panel_label(ax_a, "a", x=-0.17, y=1.10)

    groups = [
        ("Observed non-user", df[df["observed_adoption"].eq(0)], COLORS["orange"]),
        ("Observed user", df[df["observed_adoption"].eq(1)], COLORS["teal"]),
    ]
    violin = ax_b.violinplot(
        [frame["delta_predicted_n"].to_numpy() for _, frame, _ in groups],
        positions=[0, 1], orientation="horizontal", widths=0.72,
        showmeans=False, showmedians=False, showextrema=False,
    )
    for body, (_, _, color) in zip(violin["bodies"], groups):
        body.set_facecolor(color)
        body.set_edgecolor("none")
        body.set_alpha(0.18)
    rng = np.random.default_rng(42)
    for pos, (_, frame, color) in enumerate(groups):
        values = frame["delta_predicted_n"].to_numpy()
        weights = frame["population_analysis_weight"].to_numpy()
        sizes = 11 + 24 * np.sqrt(weights / weights.max())
        jitter = rng.normal(0, 0.045, len(values))
        ax_b.scatter(values, np.full(len(values), pos) + jitter, s=sizes, color=color,
                     edgecolor="white", lw=0.35, alpha=0.72, zorder=2)
        q1, median, q3 = np.percentile(values, [25, 50, 75])
        ax_b.plot([q1, q3], [pos, pos], color=COLORS["ink"], lw=2.0, zorder=4)
        ax_b.scatter([median], [pos], marker="|", s=105, color=COLORS["ink"], zorder=5)
    ax_b.axvline(0, color=COLORS["zero"], lw=0.8)
    ax_b.set_yticks([0, 1], [g[0] for g in groups])
    ax_b.set_xlim(-8, 45)
    ax_b.set_xticks([0, 15, 30, 45])
    ax_b.set_xlabel("High-use minus low-use labels\n(kg N ha$^{-1}$)")
    ax_b.set_title("Profile-level displacement", pad=5)
    ax_b.text(0.04, 0.50, f"All profiles: {positive_share:.0%} positive; median {median_delta:+.1f}",
              transform=ax_b.transAxes, ha="left", va="center", fontsize=7.2, color=COLORS["ink"])
    style_axis(ax_b, "x")
    panel_label(ax_b, "b", x=-0.25, y=1.16)

    values = quartiles.to_numpy() / 1000
    y = np.arange(4)
    colors = ["#DDEAF2", "#BFD7E6", "#79A8C6", COLORS["blue"]]
    ax_c.barh(y, values, color=colors, edgecolor="white", lw=0.5)
    for idx, value in enumerate(values):
        share = value / (total_tonnes / 1000)
        ax_c.text(value + max(values) * 0.025, idx, f"{share:.0%}", va="center", fontsize=7.4,
                  color=COLORS["ink"], fontweight="bold" if idx == 3 else "normal")
    ax_c.set_yticks(y, ["Q1", "Q2", "Q3", "Q4"])
    ax_c.set_xlim(0, max(values) * 1.28)
    ax_c.set_xlabel("Thousand tonnes N")
    ax_c.set_title("Impact by plot-area quartile", pad=5)
    style_axis(ax_c, "x")
    panel_label(ax_c, "c", x=-0.25, y=1.16)
    ax_c.text(0, -0.28, "Q1 is the smallest plot-area quartile; Q4 is the largest.",
              transform=ax_c.transAxes, ha="left", va="top", fontsize=6.7, color=COLORS["muted"])
    export_figure(fig, HERE / "outputs", "Fig8")


if __name__ == "__main__":
    main()
