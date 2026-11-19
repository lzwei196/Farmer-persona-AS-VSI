from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from figure_style import (COLORS, COUNTRY_CODES, PROVIDERS, PROVIDER_COLORS, PROVIDER_NAMES,
                          export_figure, panel_label, plt, style_axis)


def main() -> None:
    labels = pd.read_csv(HERE / "data" / "Fig4a_label_means.csv")
    components = pd.read_csv(HERE / "data" / "Fig4b_variance_components.csv").set_index("outcome")
    contrasts = pd.read_csv(HERE / "data" / "Fig4c_high_low_contrasts.csv")
    ranking = pd.read_csv(HERE / "data" / "Fig4d_ranking_change.csv").set_index("provider")

    fig = plt.figure(figsize=(7.2, 4.85))
    gs = fig.add_gridspec(
        2, 3, width_ratios=[1.45, 1.0, 1.0], height_ratios=[1.0, 1.0],
        left=0.09, right=0.985, bottom=0.12, top=0.94, wspace=0.43, hspace=0.52,
    )
    ax_a = fig.add_subplot(gs[:, 0])
    ax_b = fig.add_subplot(gs[0, 1:])
    ax_c = fig.add_subplot(gs[1, 1])
    ax_d = fig.add_subplot(gs[1, 2])
    provider_style = {"claude": ("o", "-"), "codex": ("s", "--"),
                      "kimi": ("^", ":"), "ensemble": ("D", "-")}
    for provider in PROVIDERS:
        frame = labels[labels["provider"].eq(provider)].sort_values("country_wave_prevalence")
        marker, ls = provider_style[provider]
        ensemble = provider == "ensemble"
        ax_a.plot(frame["country_wave_prevalence"], frame["mean_predicted_n"], marker=marker,
                  ls=ls, color=PROVIDER_COLORS[provider], lw=1.8 if ensemble else 1.0,
                  ms=4.8 if ensemble else 3.4, alpha=1 if ensemble else 0.82,
                  label=PROVIDER_NAMES[provider], zorder=4 if ensemble else 2)
    ensemble_rows = labels[labels["provider"].eq("ensemble")]
    label_offsets = {
        "UGA": (5, 5), "TZA": (-18, 8), "NER": (6, -13), "MLI": (7, -14),
        "NGA": (7, 8), "ETH": (-17, 10), "MWI": (7, -13),
    }
    for _, row in ensemble_rows.iterrows():
        code = COUNTRY_CODES[row["assigned_country"]]
        ax_a.annotate(code, (row["country_wave_prevalence"], row["mean_predicted_n"]),
                      xytext=label_offsets[code], textcoords="offset points",
                      fontsize=6.6, color=COLORS["ink"],
                      arrowprops={"arrowstyle": "-", "color": COLORS["zero"],
                                  "lw": 0.45, "shrinkA": 1.5, "shrinkB": 2.5})
    ax_a.set_xlim(0, 0.60)
    ax_a.set_ylim(0, 38)
    ax_a.set_xticks([0, 0.2, 0.4, 0.6])
    ax_a.set_yticks([0, 10, 20, 30])
    ax_a.set_xlabel("Assigned-country fertilizer prevalence")
    ax_a.set_ylabel("Predicted nitrogen (kg N ha$^{-1}$)")
    ax_a.set_title("Country-label sensitivity", pad=6)
    ax_a.legend(loc="upper left", ncol=2)
    style_axis(ax_a, "both")
    panel_label(ax_a, "a", x=-0.23, y=1.07)

    outcomes = ["predicted_n", "predicted_adoption", "predicted_quantity_kg"]
    outcome_labels = ["N rate", "Adoption", "N per plot"]
    ypos = np.arange(3)
    for offset, component, label, color in [
        (-0.16, "label_share", "Country label", COLORS["orange"]),
        (0.16, "profile_share", "Farmer profile", COLORS["blue"]),
    ]:
        val = components.loc[outcomes, component].to_numpy()
        lo = components.loc[outcomes, f"{component}_lo"].to_numpy()
        hi = components.loc[outcomes, f"{component}_hi"].to_numpy()
        ax_b.barh(ypos + offset, val, height=0.29, color=color, edgecolor="white", lw=0.4,
                  xerr=np.vstack([val - lo, hi - val]), capsize=2,
                  error_kw={"elinewidth": 0.8, "capthick": 0.8, "ecolor": COLORS["ink"]}, label=label)
    ax_b.set_yticks(ypos, outcome_labels)
    ax_b.invert_yaxis()
    ax_b.set_xlim(0, 0.72)
    ax_b.set_xticks([0, 0.25, 0.50])
    ax_b.set_xlabel("Share of prediction variance")
    ax_b.set_title("Variance attribution", pad=6)
    ax_b.legend(loc="upper right", ncol=2)
    style_axis(ax_b, "x")
    panel_label(ax_b, "b", x=-0.12, y=1.15)

    n_contrasts = contrasts[contrasts["outcome"].eq("predicted_n")].set_index("provider").loc[PROVIDERS]
    yy = np.arange(len(PROVIDERS))
    for idx, provider in enumerate(PROVIDERS):
        row = n_contrasts.loc[provider]
        value = row["mean_high_minus_low"]
        ax_c.errorbar(value, idx, xerr=[[value - row["ci_lo"]], [row["ci_hi"] - value]],
                      fmt="o", color=PROVIDER_COLORS[provider], ecolor=PROVIDER_COLORS[provider],
                      ms=4.6, elinewidth=1.0, capsize=2.2)
    ax_c.axvline(0, color=COLORS["zero"], lw=0.8)
    ax_c.set_yticks(yy, [PROVIDER_NAMES[p] for p in PROVIDERS])
    ax_c.invert_yaxis()
    ax_c.set_xlim(-2, 28)
    ax_c.set_xticks([0, 10, 20])
    ax_c.set_xlabel("High-use minus low-use labels\n(kg N ha$^{-1}$)")
    ax_c.set_title("Nitrogen-rate contrast", pad=6)
    style_axis(ax_c, "x")
    panel_label(ax_c, "c", x=-0.31, y=1.16)

    for idx, provider in enumerate(PROVIDERS):
        row = ranking.loc[provider]
        value = row["high_minus_low_label_farmer_r"]
        ax_d.errorbar(value, idx,
                      xerr=[[value - row["high_minus_low_label_farmer_r_lo"]],
                            [row["high_minus_low_label_farmer_r_hi"] - value]],
                      fmt="o", color=PROVIDER_COLORS[provider], ecolor=PROVIDER_COLORS[provider],
                      ms=4.6, elinewidth=1.0, capsize=2.2)
    ax_d.axvline(0, color=COLORS["zero"], lw=0.8)
    ax_d.set_yticks(yy, [])
    ax_d.tick_params(axis="y", left=False)
    ax_d.invert_yaxis()
    ax_d.set_xlim(-0.15, 0.42)
    ax_d.set_xticks([-0.1, 0.0, 0.2, 0.4])
    ax_d.set_xlabel("Change in farmer-level\nPearson $r$")
    ax_d.set_title("Change in farmer-level agreement", pad=6)
    style_axis(ax_d, "x")
    panel_label(ax_d, "d", x=-0.22, y=1.16)
    export_figure(fig, HERE / "outputs", "Fig4")


if __name__ == "__main__":
    main()
