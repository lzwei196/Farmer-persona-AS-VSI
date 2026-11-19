"""Redraw Fig. 2 from documented archived and reported plotting values.

This is a portable redraw prepared for the unified October 17 code release,
not the original script that rendered the accepted manuscript image. It does
not refit the national-statistics regression or reproduce its bootstrap.
See data/Fig2_input_provenance.csv for the precision and source of each cell.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from figure_style import COLORS, COUNTRIES, export_figure, panel_label, plt, style_axis
from audit_panel_alignment import require_matplotlib_panel_alignment
import os


def main() -> None:
    df = pd.read_csv(HERE / "data" / "Fig2_plotting_values.csv")
    df = df.set_index("country").loc[COUNTRIES].reset_index()
    y = np.arange(len(df))
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.55), sharey=True)
    fig.subplots_adjust(left=0.105, right=0.985, bottom=0.25, top=0.76, wspace=0.28)
    specs = [
        ("a", "Adoption", "observed_adoption", "predicted_adoption", "Mean adoption", (0, .9), [0, .3, .6, .9]),
        ("b", "Nitrogen rate", "observed_n_kg_per_ha", "predicted_n_kg_per_ha", "kg N ha$^{-1}$", (0, 42), [0, 14, 28, 42]),
        ("c", "Nitrogen quantity", "observed_n_kg_per_plot", "predicted_n_kg_per_plot", "kg N plot$^{-1}$", (0, 62), [0, 20, 40, 60]),
    ]
    for ax, (label, title, obs_col, pred_col, xlabel, xlim, xticks) in zip(axes, specs):
        tz = int(df.index[df.country.eq("Tanzania")][0])
        ax.axhspan(tz-.45, tz+.45, color=COLORS["highlight"], zorder=-2)
        obs, pred = df[obs_col].to_numpy(), df[pred_col].to_numpy()
        lo, hi = df[pred_col+"_lo"].to_numpy(), df[pred_col+"_hi"].to_numpy()
        for i in range(len(df)):
            ax.plot([obs[i], pred[i]], [i,i], color=COLORS["zero"], lw=1.0, zorder=1)
        ax.errorbar(pred, y, xerr=np.vstack([pred-lo,hi-pred]), fmt="o", color=COLORS["orange"],
                    ms=4.2, elinewidth=.9, capsize=2.1, zorder=3)
        ax.scatter(obs, y, s=25, facecolor="white", edgecolor=COLORS["ink"], linewidth=.85, zorder=4)
        if label == "a":
            ax.scatter(df.regression_adoption, y, marker="D", s=20, color="#8064b3", zorder=5)
        else:
            cap = "capped_n_kg_per_ha" if label == "b" else "capped_n_kg_per_plot"
            ax.scatter(df[cap], y, marker="|", s=55, color="#888888", linewidths=1.1, zorder=5)
            if label == "b":
                ax.scatter(df.regression_n_kg_per_ha, y, marker="D", s=20, color="#8064b3", zorder=5)
        if label in ["a", "b"]:
            text = "MAE: LLM 0.16; regression 0.05" if label == "a" else "MAE (kg N ha$^{-1}$):\nLLM 3.70; regression 4.69"
            ax.text(.5,-.31,text,transform=ax.transAxes,ha="center",va="top",fontsize=7.5,clip_on=False)
        ax.set_xlim(*xlim);ax.set_xticks(xticks);ax.set_xlabel(xlabel);ax.set_title(title,pad=6)
        ax.set_ylim(len(df)-.5,-.5);style_axis(ax,"x")
        panel_label(ax,label,x=-.22 if label=="a" else -.14,y=1.16)
    axes[0].set_yticks(y,[c+("†" if c in ["Ethiopia","Niger"] else "") for c in df.country])
    for ax in axes[1:]:ax.tick_params(axis="y",left=False,labelleft=False)
    handles=[
        Line2D([],[],color=COLORS["orange"],marker="o",lw=.9,label="LLM ensemble (95% CI)"),
        Line2D([],[],color=COLORS["ink"],marker="o",mfc="white",lw=0,label="Observed target"),
        Line2D([],[],color="#888888",marker="|",lw=0,label="Observed, rates capped at 300"),
        Line2D([],[],color="#8064b3",marker="D",lw=0,label="Regression on national statistics"),
    ]
    fig.legend(handles=handles,loc="upper center",bbox_to_anchor=(.54,.99),ncol=2,
               fontsize=6.9,columnspacing=1.8,handletextpad=.5)
    alignment_dir = Path(os.environ["FIGURE_OUTPUT_ROOT"]) / "Fig2" if os.environ.get("FIGURE_OUTPUT_ROOT") else HERE / "outputs"
    alignment_dir.mkdir(parents=True, exist_ok=True)
    require_matplotlib_panel_alignment(fig, json_out=alignment_dir / "Fig2.alignment.json", overlay_svg=alignment_dir / "Fig2.alignment.svg", tolerance_pt=1.5, gutter_tolerance_pt=1.5, require_panel_labels=True, strict=True)
    export_figure(fig,HERE/"outputs","Fig2")


if __name__ == "__main__":
    main()
