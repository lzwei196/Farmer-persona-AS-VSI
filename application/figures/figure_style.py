from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).absolute().parent
os.environ.setdefault("MPLCONFIGDIR", str(PACKAGE_ROOT / ".matplotlib"))

import matplotlib as mpl  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
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
        "figure.dpi": 140,
        "savefig.dpi": 600,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
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
    requested = os.environ.get("FIGURE_FORMATS", "pdf,svg,png")
    formats = {item.strip().lower() for item in requested.split(",") if item.strip()}
    if "all" in formats:
        formats = {"pdf", "svg", "png", "tiff"}
    unsupported = formats.difference({"pdf", "svg", "png", "tiff"})
    if unsupported:
        raise ValueError(f"Unsupported FIGURE_FORMATS: {sorted(unsupported)}")
    for suffix in ["pdf", "svg", "png"]:
        if suffix in formats:
            kwargs = {"dpi": 600} if suffix == "png" else {}
            fig.savefig(output_dir / f"{stem}.{suffix}", facecolor=COLORS["paper"], **kwargs)
    if "tiff" in formats:
        fig.savefig(
            output_dir / f"{stem}.tiff", facecolor=COLORS["paper"], dpi=600,
            pil_kwargs={"compression": "tiff_lzw"},
        )
    plt.close(fig)


configure_style()
