from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))

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



def main():
    data=pd.read_csv(HERE/'data/Fig6_trait_coefficients_snapshot.csv')
    explained=pd.read_csv(HERE/'data/Fig6_explained_variation_snapshot.csv')
    traits=['Maize main crop','Formal education','Plot area (×2)','Female manager','Age (+10 years)','Intercropped','Plot owned','Farm size (×2)']
    assert len(data)==48 and len(explained)==4
    fig,axes=plt.subplots(1,3,figsize=(7.2,3.7),gridspec_kw={'width_ratios':[1,1,1]})
    fig.subplots_adjust(left=.16,right=.985,bottom=.18,top=.74,wspace=.54)
    fig.suptitle('Observed and predicted trait associations',fontsize=10,fontweight='bold',x=.52,y=.99)
    y=np.arange(8)
    for ax,outcome,label in [(axes[0],'Adoption','a'),(axes[1],'N rate','b')]:
        ax.axvline(0,color=COLORS['zero'],lw=.8,zorder=0)
        for source,offset,color,face,legend in [('LLM ensemble',-.13,COLORS['orange'],COLORS['orange'],'LLM ensemble (95% CI)'),('Survey',.13,COLORS['ink'],'white','Survey (95% CI)')]:
            vals=data[(data.outcome==outcome)&(data.source==source)].set_index('trait').loc[traits]
            beta=vals.coefficient.to_numpy(float); low=vals.ci_low.to_numpy(float);high=vals.ci_high.to_numpy(float)
            assert np.all(low<=beta) and np.all(beta<=high)
            ax.errorbar(beta,y+offset,xerr=np.vstack([beta-low,high-beta]),fmt='o',mfc=face,mec=color,color=color,ecolor=color,ms=4.3,elinewidth=.9,capsize=2.1,label=legend,zorder=3)
        if outcome=='N rate':
            cap=data[(data.outcome=='N rate, capped')&(data.source=='Survey')].set_index('trait').loc[traits]
            ax.scatter(cap.coefficient,y+.13,marker='D',s=18,color='#8a8a8a',label='Survey, rates capped at 300',zorder=4)
            ax.set_xlim(-10.5,33)
            ax.set_xticks([0,20])
            ax.set_xlabel('Nitrogen-rate coefficient\n(kg N ha$^{-1}$)',fontsize=9.5)
            ax.set_title('Nitrogen rate',pad=6)
        else:
            ax.set_xlim(-.20,.56);ax.set_xticks([0,.2,.4]);ax.set_title('Adoption',pad=6)
            ax.set_xlabel('Adoption coefficient\n(proportion points)')
        ax.set_yticks(y,traits if outcome=='Adoption' else ['']*8)
        ax.tick_params(axis='y',length=0)
        ax.invert_yaxis();style_axis(ax,None);panel_label(ax,label,x=-.20,y=1.10)
    ax=axes[2]
    for row,outcome in enumerate(['Adoption','N rate']):
        for source,offset,color,face in [('LLM ensemble',-.17,COLORS['orange'],COLORS['orange']),('Survey',.17,COLORS['ink'],'white')]:
            value=float(explained[(explained.outcome==outcome)&(explained.source==source)].percent_variation_explained.iloc[0])
            ax.barh(row+offset,value,height=.29,color=face,edgecolor=color,linewidth=.9)
            ax.text(value+3.0,row+offset,f'{value:.1f}%',va='center',fontsize=7.2)
    ax.set_yticks([0,1],['Adoption','Nitrogen rate']);ax.tick_params(axis='y',length=0)
    ax.invert_yaxis();ax.set_xlim(0,55);ax.set_xticks([0,20,40]);ax.set_xlabel('Within-country variation (%)')
    ax.set_title('Variance explained (%)',pad=6);style_axis(ax,None);panel_label(ax,'c',x=-.20,y=1.10)
    handles,labels=axes[1].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.54,.92),ncol=3,handlelength=1.35,columnspacing=.7,fontsize=7.1)
    export_figure(fig,HERE/'outputs','Fig6')


if __name__=='__main__':main()
