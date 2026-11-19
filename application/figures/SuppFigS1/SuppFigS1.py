from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).absolute().parent
os.environ.setdefault("MPLCONFIGDIR", str(PACKAGE_ROOT / ".matplotlib"))

import matplotlib as mpl  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from audit_panel_alignment import require_matplotlib_panel_alignment
from matplotlib import font_manager  # noqa: E402

FONT_FILES = [
    Path(r"C:\Windows\Fonts\times.ttf"),
    Path(r"C:\Windows\Fonts\timesbd.ttf"),
    Path(r"C:\Windows\Fonts\timesi.ttf"),
    Path(r"C:\Windows\Fonts\timesbi.ttf"),
]
for font_file in FONT_FILES:
    if font_file.exists():
        font_manager.fontManager.addfont(font_file)

COLORS = {
    "ink": "#000000",
    "muted": "#000000",
    "grid": "#DCE3E9",
    "zero": "#A8B3BE",
    "blue": "#2A6F9E",
    "blue_dark": "#194C72",
    "blue_light": "#BFD7E6",
    "orange": "#D66A0A",
    "orange_light": "#F4D5B8",
    "teal": "#1B8A82",
    "rose": "#B45A7A",
    "gold": "#D6A12B",
    "highlight": "#FFF2D8",
    "paper": "#FFFFFF",
}

COUNTRIES = ["Ethiopia", "Malawi", "Mali", "Niger", "Nigeria", "Tanzania", "Uganda"]
LABEL_ORDER = ["Uganda", "Tanzania", "Niger", "Mali", "Nigeria", "Ethiopia", "Malawi"]
PROVIDERS = ["claude", "codex", "kimi", "ensemble"]
PROVIDER_NAMES = {"claude": "Claude", "codex": "Codex", "kimi": "Kimi", "ensemble": "Ensemble"}
PROVIDER_COLORS = {
    "claude": COLORS["blue"],
    "codex": COLORS["teal"],
    "kimi": COLORS["rose"],
    "ensemble": COLORS["ink"],
}
COUNTRY_CODES = {
    "Uganda": "UGA", "Tanzania": "TZA", "Niger": "NER", "Mali": "MLI",
    "Nigeria": "NGA", "Ethiopia": "ETH", "Malawi": "MWI",
}


def configure_style() -> None:
    mpl.rcParams.update({
        "figure.dpi": 300,
        "savefig.dpi": 600,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Arial", "Helvetica", "DejaVu Serif"],
        "font.size": 8.0,
        "axes.titlesize": 9.0,
        "axes.titleweight": "bold",
        "axes.labelsize": 8.5,
        "axes.linewidth": 0.65,
        "axes.edgecolor": COLORS["ink"],
        "axes.labelcolor": COLORS["ink"],
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "xtick.color": COLORS["muted"],
        "ytick.color": COLORS["muted"],
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "legend.fontsize": 7.2,
        "legend.frameon": False,
        "legend.handlelength": 1.5,
        "legend.handletextpad": 0.5,
        "legend.columnspacing": 1.0,
        "lines.linewidth": 1.2,
        "mathtext.fontset": "stix",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "axes.unicode_minus": False,
    })


def panel_label(ax: plt.Axes, label: str, x: float = -0.14, y: float = 1.10) -> None:
    ax.text(x, y, label, transform=ax.transAxes, ha="left", va="top",
            fontsize=11, fontweight="bold", color=COLORS["ink"], clip_on=False)


def style_axis(ax: plt.Axes, grid_axis: str | None = "x") -> None:
    ax.tick_params(colors=COLORS["muted"], labelcolor=COLORS["muted"])
    ax.title.set_color(COLORS["ink"])
    if grid_axis:
        ax.grid(True, axis=grid_axis, color=COLORS["grid"], lw=0.45, alpha=0.8, zorder=0)
    ax.set_axisbelow(True)


def export_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    # Redirect fresh renders without replacing the archived submission assets.
    if os.environ.get("FIGURE_OUTPUT_ROOT"):
        output_dir = Path(os.environ["FIGURE_OUTPUT_ROOT"]).expanduser().resolve() / stem
    output_dir.mkdir(parents=True, exist_ok=True)
    exemptions=[]
    if stem=='Fig3':
        exemptions=[{'panels':['a','c'],'checks':['panel-width'],'reason':'Retained archived unequal-width grid: extra width accommodates forest-plot and country-label reading.'}]
    elif stem=='SuppFigS1':
        exemptions=[{'panels':['a'],'checks':['panel-width'],'reason':'Retained archived first-panel width for 70 profile ranks.'}]
    require_matplotlib_panel_alignment(fig,json_out=output_dir/f'{stem}.alignment.json',overlay_svg=output_dir/f'{stem}.alignment.svg',tolerance_pt=1.5,gutter_tolerance_pt=1.5,require_panel_labels=True,strict=True,exemptions=exemptions)
    fig.savefig(output_dir / f"{stem}.pdf", facecolor=COLORS["paper"])
    fig.savefig(output_dir / f"{stem}.svg", facecolor=COLORS["paper"])
    fig.savefig(output_dir / f"{stem}.png", facecolor=COLORS["paper"], dpi=600)
    fig.savefig(output_dir / f"{stem}.tiff", facecolor=COLORS["paper"], dpi=600, pil_kwargs={"compression":"tiff_lzw"})
    plt.close(fig)


configure_style()



def main() -> None:
    loo = pd.read_csv(HERE / "data" / "paper2_influence_leave_one_out.csv")
    summary = pd.read_csv(HERE / "data" / "paper2_influence_sensitivity.csv")
    contributions = pd.read_csv(HERE / "data" / "paper2_label_contributions.csv")
    full = float(summary.iloc[0]["expanded_difference_tonnes"]) / 1000

    fig, axes = plt.subplots(
        1, 3, figsize=(7.2, 2.72), gridspec_kw={"width_ratios": [1.12, 1.0, 1.0]}
    )
    fig.subplots_adjust(left=0.085, right=0.985, bottom=0.23, top=0.77, wspace=0.78)

    ax = axes[0]
    ordered = loo.sort_values("expanded_difference_tonnes").reset_index(drop=True)
    values = ordered["expanded_difference_tonnes"].to_numpy(float) / 1000
    ax.axhline(full, color=COLORS["orange"], lw=1.1)
    ax.scatter(np.arange(1, len(values) + 1), values, s=10, color=COLORS["blue"],
               edgecolor="white", linewidth=0.25, zorder=3, label="One profile omitted")
    ax.set_xlim(0, 71)
    ax.set_xticks([1, 20, 40, 60, 70])
    ax.set_xlabel("Leave-one-out estimate rank")
    ax.set_ylabel("Expanded contrast (kt N)")
    ax.set_title("Profile deletion")
    ax.text(0.05, 0.08, "Full sample", transform=ax.transAxes, color=COLORS["orange"],
            ha="left", va="bottom", fontsize=6.8)
    style_axis(ax, "y")
    panel_label(ax, "a", x=-0.23, y=1.16)

    ax = axes[1]
    method_labels = {
        "primary_fixed": "Primary",
        "full_strata_fixed": "Fixed, full strata",
        "full_strata_recalibrated": "Weights recalculated",
    }
    colors = [COLORS["orange"], COLORS["blue"], COLORS["teal"]]
    y = np.arange(3)
    for index, method in enumerate(method_labels):
        row = summary[summary["method"] == method].iloc[0]
        value = row["expanded_difference_tonnes"] / 1000
        lo = row["expanded_difference_tonnes_lo"] / 1000
        hi = row["expanded_difference_tonnes_hi"] / 1000
        ax.errorbar(value, index, xerr=[[value - lo], [hi - value]], fmt="o",
                    color=colors[index], ecolor=colors[index], mfc=colors[index],
                    ms=4.2, elinewidth=1.0, capsize=2.3, zorder=3)
    ax.set_yticks(y, list(method_labels.values()))
    ax.invert_yaxis()
    ax.set_xlim(100, 375)
    ax.set_xticks([100, 200, 300])
    ax.set_xlabel("Expanded contrast (kt N)")
    ax.set_title("Bootstrap sensitivity")
    style_axis(ax, "x")
    panel_label(ax, "b", x=-0.31, y=1.16)

    ax = axes[2]
    rank = contributions["influence_rank"].to_numpy(int)
    ax.plot(rank, 100 * contributions["cumulative_net_share"],
            color=COLORS["orange"], lw=1.45, label="Scenario concentration")
    ax.plot(rank, 100 * rank / len(rank), color=COLORS["blue"], lw=1.0,
            ls="--", label="Equal-share reference")
    ax.axhline(100, color=COLORS["zero"], lw=0.7)
    ax.axvline(10, color=COLORS["zero"], lw=0.7, ls="--")
    ax.set_xlim(1, 70)
    ax.set_xticks([1, 10, 30, 50, 70])
    ax.set_xlabel("Profiles ranked by contribution")
    ax.set_ylabel("Cumulative share (%)")
    ax.set_title("Contribution concentration")
    style_axis(ax, "y")
    panel_label(ax, "c", x=-0.24, y=1.16)

    handles, labels = axes[2].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.78, 0.98), ncol=2)
    export_figure(fig, HERE / "outputs", "SuppFigS1")


if __name__ == "__main__":
    main()
