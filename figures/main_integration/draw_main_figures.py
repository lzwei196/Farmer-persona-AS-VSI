"""AS-focused study route and compact African prompt-design comparison.

Run with NumPy, Matplotlib and installed Times New Roman fonts.
All quantitative inputs are read from the sibling data directory.
"""
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, FancyArrowPatch
from audit_panel_alignment import require_matplotlib_panel_alignment

ROOT = Path(__file__).resolve().parent
QA = ROOT / 'qa'
QA.mkdir(exist_ok=True)
for font in Path('/System/Library/Fonts/Supplemental').glob('Times New Roman*.ttf'):
    font_manager.fontManager.addfont(str(font))
plt.rcParams.update({
    'font.family': 'Times New Roman', 'font.size': 9,
    'axes.labelsize': 9, 'axes.titlesize': 9.5,
    'xtick.labelsize': 8.5, 'ytick.labelsize': 8.5,
    'legend.fontsize': 8.5, 'axes.spines.top': False,
    'axes.spines.right': False, 'axes.linewidth': .65,
    'xtick.major.width': .65, 'ytick.major.width': .65,
    'xtick.major.size': 3, 'ytick.major.size': 3,
    'svg.fonttype': 'none', 'pdf.fonttype': 42,
    'mathtext.fontset': 'custom', 'mathtext.rm': 'Times New Roman',
    'mathtext.it': 'Times New Roman:italic',
    'mathtext.bf': 'Times New Roman:bold', 'savefig.facecolor': 'white',
})
WIDTH = 180 / 25.4
COLORS = {'claude': '#39768C', 'codex': '#C17C42', 'kimi': '#5D8C74'}
MARKERS = {'claude': 'o', 'codex': 's', 'kimi': '^'}
PROVIDERS = ['claude', 'codex', 'kimi']
TIERS = ['T1', 'T2', 'T3', 'T4']


def read_csv(name):
    with (ROOT / 'data' / name).open(encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))


def save_figure(fig, name, **alignment_options):
    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig, json_out=QA / (name + '.alignment.json'),
        overlay_svg=QA / (name + '.alignment.svg'),
        tolerance_pt=1.5, gutter_tolerance_pt=1.5,
        require_panel_labels=True, strict=True, **alignment_options,
    )
    fig.savefig(ROOT / (name + '.pdf'))
    fig.savefig(ROOT / (name + '.svg'))
    fig.savefig(ROOT / (name + '.png'), dpi=600)
    plt.close(fig)


def draw_prompt_comparison():
    records = [r for r in read_csv('african_configurations.csv')
               if r['outcome'] == 'nitrogen_kg_per_ha']
    reference = read_csv('african_nitrogen_reference.csv')[0]
    specification = [
        ('r', 'Pearson correlation', (0, .4), None),
        ('mae', 'MAE (kg N ha$^{-1}$)', (24, 29),
         float(records[0]['median_null_mae'])),
        ('ks_similarity', '1 − KS statistic', (.65, 1),
         float(reference['null_shape'])),
        ('sd_ratio', 'SD ratio', (0, 1.1), 1),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH, 4.6))
    fig.subplots_adjust(left=.10, right=.98, bottom=.12, top=.86,
                        wspace=.35, hspace=.55)
    for i, (key, ylabel, ylim, baseline) in enumerate(specification):
        ax = axes.flat[i]
        for provider in PROVIDERS:
            selected = {r['tier']: r for r in records if r['provider'] == provider}
            ax.plot(range(1, 5), [float(selected[t][key]) for t in TIERS],
                    color=COLORS[provider], marker=MARKERS[provider],
                    ms=4, lw=1)
        if baseline is not None:
            ax.axhline(baseline, color='.45', lw=.8, ls='--', zorder=0)
        ax.set(xlim=(.8, 4.2), ylim=ylim, ylabel=ylabel,
               xlabel='Prompt design')
        ax.set_xticks(range(1, 5), TIERS)
        ax.annotate(chr(97 + i), (0, 1), xycoords='axes fraction',
                    xytext=(-27, 9), textcoords='offset points',
                    weight='bold', fontsize=10, ha='left', va='bottom',
                    annotation_clip=False)
    axes[0, 0].set_yticks(np.arange(0, .41, .1))
    axes[1, 0].set_yticks([.7, .8, .9, 1])
    axes[1, 1].set_yticks([0, .5, 1])
    handles = [Line2D([], [], color=COLORS[p], marker=MARKERS[p],
                      markersize=4, lw=1, label=p.capitalize())
               for p in PROVIDERS]
    fig.legend(handles=handles, loc='upper center',
               bbox_to_anchor=(.53, .98), ncol=3, frameon=False,
               handlelength=2, columnspacing=2)
    save_figure(fig, 'Fig_2')


def draw_study_route():
    from draw_study_design import render
    render(ROOT)


if __name__ == '__main__':
    draw_study_route()
    draw_prompt_comparison()
    print('Exported Fig_1 and Fig_2 with strict panel-alignment checks.')
