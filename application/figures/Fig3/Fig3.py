from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).absolute().parent
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
    df = pd.read_csv(HERE / "data" / "Fig3_country_benchmark.csv")
    df = df.set_index("country").loc[COUNTRIES].reset_index()
    # Slightly expand the country rows so the three estimates remain distinct
    # after the full figure is reduced to journal column width.
    y = np.arange(len(df)) * 1.14
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.55), gridspec_kw={"width_ratios": [1.14, 1.0, 1.04]})
    fig.subplots_adjust(left=0.11, right=0.985, bottom=0.17, top=0.78, wspace=0.46)

    ax = axes[0]
    ax.axvline(0, color=COLORS["zero"], lw=0.8)
    for offset, prefix, label, color, marker, face in [
        (-0.19, "agent", "LLM ensemble", COLORS["orange"], "o", COLORS["orange"]),
        (0.00, "matched", "Matched-input baseline", COLORS["teal"], "^", "white"),
        (0.19, "conventional", "Rich-input baseline", COLORS["blue"], "s", "white"),
    ]:
        val = df[f"{prefix}_r"].to_numpy()
        lo = df[f"{prefix}_r_lo"].to_numpy()
        hi = df[f"{prefix}_r_hi"].to_numpy()
        ax.errorbar(val, y + offset, xerr=np.vstack([val - lo, hi - val]), fmt=marker,
                    color=color, ecolor=color, mfc=face, mec=color, ms=4.3,
                    elinewidth=0.9, capsize=2.1, label=label, zorder=3)
    ax.set_yticks(y, df["country"])
    ax.set_xlim(-0.40, 0.82)
    ax.set_xticks([-0.25, 0, 0.25, 0.50, 0.75])
    ax.invert_yaxis()
    ax.set_xlabel("Farmer-level nitrogen correlation, $r$")
    ax.set_title("Individual-level transfer skill", pad=6)
    style_axis(ax, "x")
    panel_label(ax, "a", x=-0.30, y=1.12)

    ax = axes[1]
    prevalence_sorted = df.sort_values("fertilizer_prevalence")
    ax.plot(prevalence_sorted["fertilizer_prevalence"], prevalence_sorted["agent_r"],
            color=COLORS["orange"], marker="o", ms=4.2, lw=1.25,
            label="LLM ensemble", zorder=3)
    ax.plot(prevalence_sorted["fertilizer_prevalence"], prevalence_sorted["matched_r"],
            color=COLORS["teal"], marker="^", ms=4.2, lw=1.15,
            markerfacecolor="white", markeredgewidth=1.0,
            label="Matched-input baseline", zorder=2)
    ax.plot(prevalence_sorted["fertilizer_prevalence"], prevalence_sorted["conventional_r"],
            color=COLORS["blue"], marker="s", ms=4.2, lw=1.25,
            markerfacecolor="white", markeredgewidth=1.0,
            label="Rich-input baseline", zorder=2)
    label_positions = {
        "Uganda": (0.020, -0.028), "Tanzania": (0.155, -0.030), "Niger": (0.190, 0.120),
        "Mali": (0.250, 0.455), "Nigeria": (0.390, 0.510), "Ethiopia": (0.455, 0.420), "Malawi": (0.405, -0.060),
    }
    for _, row in prevalence_sorted.iterrows():
        ax.annotate(COUNTRY_CODES[row["country"]], (row["fertilizer_prevalence"], row["agent_r"]),
                    xytext=label_positions[row["country"]], textcoords="data",
                    fontsize=6.6, color=COLORS["muted"],
                    arrowprops={"arrowstyle":"-", "color":COLORS["zero"], "lw":.45, "shrinkA":10, "shrinkB":3})
    ax.set_xlim(0, 0.60)
    ax.set_ylim(-0.10, 0.58)
    ax.set_xticks([0, 0.2, 0.4, 0.6])
    ax.set_yticks([0, 0.2, 0.4])
    ax.set_xlabel("Fertilizer-use prevalence")
    ax.set_ylabel("Farmer-level Pearson $r$")
    ax.set_title("Cross-country skill patterns", pad=6)
    style_axis(ax, None)
    panel_label(ax, "b", x=-0.24, y=1.12)

    ax = axes[2]
    ax.axvline(0, color=COLORS["zero"], lw=0.8)
    for idx, row in df.iterrows():
        is_tza = row["country"] == "Tanzania"
        color = COLORS["orange"] if is_tza else COLORS["ink"]
        marker = "D" if is_tza else "o"
        value = row["quantity_error_kg_per_plot"]
        ax.errorbar(value, y[idx],
                    xerr=[[value - row["quantity_error_kg_per_plot_lo"]],
                          [row["quantity_error_kg_per_plot_hi"] - value]],
                    fmt=marker, color=color, ecolor=color, ms=4.2, elinewidth=0.9,
                    capsize=2.1, zorder=3)
    ax.set_yticks(y, df["country"])
    ax.set_xlim(-12, 30)
    ax.set_xticks([-10, 0, 10, 20, 30])
    ax.invert_yaxis()
    ax.set_xlabel("Nitrogen error (kg per eligible plot)")
    ax.set_title("Post-stratified quantity error", pad=6)
    style_axis(ax, "x")
    panel_label(ax, "c", x=-0.29, y=1.12)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.50, 0.98), ncol=3)
    export_figure(fig, HERE / "outputs", "Fig3")


if __name__ == "__main__":
    main()
