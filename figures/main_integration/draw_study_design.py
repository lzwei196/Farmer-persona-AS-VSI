"""Editable study-design schematic, styled after the supplied original figure.

Python/Matplotlib only. All numbers describe the documented experiment; icons
are schematic and do not encode measurements. Shared calls are counted once.
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import (FancyBboxPatch, Rectangle, Circle, Ellipse,
                                Polygon, Arc, FancyArrowPatch)
from audit_panel_alignment import require_matplotlib_panel_alignment

INK = '#19384C'
BLUE = '#287FA9'
EDGE = '#8AB6CE'
PALE_BLUE = '#DDEFF9'
CREAM = '#FFF4D1'
GREEN = '#E4F0D9'
GREEN_INK = '#467B61'
WHITE = '#FFFFFF'
W, H = 180, 153


def box(ax, x, y, w, h, fill=WHITE, edge=EDGE, radius=1.2, lw=.6):
    p = FancyBboxPatch((x, y), w, h,
                      boxstyle=f'round,pad=0,rounding_size={radius}',
                      facecolor=fill, edgecolor=edge, lw=lw, clip_on=False)
    ax.add_patch(p)
    return p


def text(ax, x, y, s, size=8, bold=False, ha='left', color=INK, **kwargs):
    return ax.text(x, y, s, fontsize=size, weight='bold' if bold else 'normal',
                   ha=ha, va='center', color=color, linespacing=1.15, **kwargs)


def line(ax, xy, color=BLUE, lw=.7):
    ax.plot([p[0] for p in xy], [p[1] for p in xy], color=color, lw=lw,
            solid_capstyle='round', clip_on=False)


def arrow(ax, start, end, color=BLUE, lw=.8, ms=6):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle='-|>',
                                mutation_scale=ms, lw=lw, color=color,
                                shrinkA=0, shrinkB=0, clip_on=False))


def document(ax, x, y, w=6, h=8, person=False):
    old_children = set(ax.get_children())
    box(ax, x, y, w, h, radius=.25, edge=INK, lw=.65)
    if person:
        ax.add_patch(Circle((x+w*.25, y+h*.25), w*.095, color=INK))
        box(ax, x+w*.11, y+h*.37, w*.28, h*.25, INK, INK, .45, .4)
        for yy in [.20, .35, .50]:
            line(ax, [(x+w*.53, y+h*yy), (x+w*.86, y+h*yy)], EDGE, .55)
        for yy in [.73, .87]:
            line(ax, [(x+w*.14, y+h*yy), (x+w*.86, y+h*yy)], EDGE, .55)
    else:
        for yy in [.20, .36, .52, .68, .84]:
            line(ax, [(x+w*.18, y+h*yy), (x+w*.82, y+h*yy)], EDGE, .55)
    # Keep each card's marks above its own paper, and stacked cards opaque.
    base = getattr(ax, '_card_zorder', 4)
    for artist in ax.get_children():
        if artist not in old_children:
            artist.set_zorder(base + artist.get_zorder()/100)
    ax._card_zorder = base+1


def database(ax, x, y, w=9, h=15):
    ax.add_patch(Rectangle((x, y+1.7), w, h-3.4, fc=CREAM, ec=INK, lw=.65))
    for yy in [y+h-1.7, y+h*.65, y+h*.38]:
        ax.add_patch(Arc((x+w/2, yy), w, 3.4, theta1=0, theta2=180,
                         ec=INK, lw=.65))
    ax.add_patch(Ellipse((x+w/2, y+1.7), w, 3.4, fc=CREAM, ec=INK, lw=.65))


def farmer(ax, x, y, scale=1):
    def p(xx, yy): return (x+xx*scale, y+yy*scale)
    ax.add_patch(Polygon([p(1.6, 7), p(.4, 9), p(.3, 15), p(8.4, 15),
                          p(8.3, 9), p(7.1, 7)], fc='#9AAEB6', ec=INK, lw=.65))
    ax.add_patch(Rectangle(p(3.0, 7.2), 2.8*scale, 7.8*scale,
                           fc=CREAM, ec=INK, lw=.55))
    ax.add_patch(Ellipse(p(4.4, 5.5), 4.6*scale, 5.4*scale,
                         fc='#FFE4B9', ec=INK, lw=.65))
    ax.add_patch(Polygon([p(.2, 3.2), p(2.0, 2.3), p(2.7, .3),
                          p(4.5, .7), p(6.5, .6), p(7.1, 2.3), p(8.7, 3.2)],
                         fc='#E7DCBC', ec=INK, lw=.65))
    line(ax, [p(12, 15), p(12, 8)], GREEN_INK, 1.2)
    for yy, dx in [(9, 1), (11, -1), (12.5, 1)]:
        ax.add_patch(Ellipse(p(12+dx*.9, yy), 3.1*scale, 1.4*scale,
                             angle=-32*dx, fc=GREEN_INK, ec='none'))


def lock(ax, x, y, w=3.4):
    old_children = set(ax.get_children())
    ax.add_patch(Arc((x+w/2, y+1.2), w*.65, 3.8, theta1=180, theta2=360,
                     ec=INK, lw=.65))
    box(ax, x, y+1, w, 3.1, '#FFE1A0', INK, .4, .55)
    ax.add_patch(Circle((x+w/2, y+2.05), .22, fc=INK))
    line(ax, [(x+w/2, y+2.05), (x+w/2, y+2.9)], INK, .5)
    for artist in ax.get_children():
        if artist not in old_children:
            artist.set_zorder(20+artist.get_zorder()/100)


def bag(ax, x, y, w=6, h=9, label='N', fill=WHITE):
    ax.add_patch(Polygon([(x+w*.15, y+1), (x+w*.85, y+1),
                          (x+w, y+h), (x, y+h)], fc=fill, ec=GREEN_INK, lw=.75))
    box(ax, x+w*.12, y, w*.76, 1.1, fill, GREEN_INK, .25, .6)
    text(ax, x+w/2, y+h*.59, label, size=9, bold=True, ha='center', color=GREEN_INK)


def weight(ax, x, y, w=6, h=7):
    ax.add_patch(Arc((x+w*.5, y+1.4), w*.45, 3, theta1=180, theta2=360,
                     ec=INK, lw=.6))
    ax.add_patch(Polygon([(x+w*.25, y+1), (x+w*.75, y+1),
                          (x+w, y+h), (x, y+h)], fc='#718A98', ec=INK, lw=.6))
    text(ax, x+w/2, y+4.6, 'w', size=8, bold=True, ha='center', color=WHITE)


def scatter_icon(ax, x, y, w=9, h=9):
    line(ax, [(x, y), (x, y+h), (x+w, y+h)], INK, .65)
    line(ax, [(x+1, y+h-1), (x+w-1, y+1.3)], BLUE, .75)
    for xx, yy in [(1.5, 7.3), (3.7, 4.3), (5.1, 5.0), (7.3, 2.0)]:
        ax.add_patch(Circle((x+xx*w/9, y+yy*h/9), .5, fc=GREEN_INK, ec='none'))


def traits(ax, x, y):
    cx, cy = x+4.8, y+4.8
    for angle in np.linspace(0, 2*np.pi, 7, endpoint=False):
        px, py = cx+4.6*np.cos(angle), cy+4.6*np.sin(angle)
        line(ax, [(cx, cy), (px, py)], '#8AAFC5', .45)
        ax.add_patch(Circle((px, py), .65, fc=PALE_BLUE, ec=BLUE, lw=.5))
    ax.add_patch(Circle((cx, cy-1.4), 1, fc=INK, zorder=3))
    box(ax, cx-1.5, cy, 3, 2.4, INK, INK, .7, .4).set_zorder(3)


def field(ax, x, y, w=8, h=5):
    ax.add_patch(Polygon([(x+1, y), (x+w, y), (x+w-1, y+h), (x, y+h)],
                         fc='#E9CB83', ec='#B99B59', lw=.45))
    for xx in [2.3, 4.4, 6.5]:
        for yy in [1.2, 3.1]:
            line(ax, [(x+xx, y+yy+1), (x+xx, y+yy),
                      (x+xx-.55, y+yy-.2)], GREEN_INK, .45)
            line(ax, [(x+xx, y+yy+.25), (x+xx+.55, y+yy-.1)], GREEN_INK, .45)


def render(output_dir):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    qa = root/'qa'
    qa.mkdir(exist_ok=True)
    for f in Path('/System/Library/Fonts/Supplemental').glob('Times New Roman*.ttf'):
        font_manager.fontManager.addfont(str(f))
    with plt.rc_context({'font.family': 'Times New Roman', 'font.size': 8,
                         'svg.fonttype': 'none', 'pdf.fonttype': 42,
                         'savefig.facecolor': 'white'}):
        fig = plt.figure(figsize=(W/25.4, H/25.4), facecolor=WHITE)
        canvas = fig.add_axes([0, 0, 1, 1], zorder=3)
        canvas.set(xlim=(0, W), ylim=(H, 0)); canvas.axis('off')
        panels = {}
        specs = {'a': (1, 12, 32, 103), 'b': (39, 12, 88, 25),
                 'c': (39, 41, 88, 74), 'd': (133, 12, 46, 103)}
        titles = {'a':'Survey data', 'b':'Prompt assessment',
                  'c':'Cross-country application', 'd':'Comparisons and scaling'}
        fills = {'a':CREAM, 'b':'#F4F7FA', 'c':'#F4F7FA', 'd':'#FFF0DF'}
        for key, (x, y, w, h) in specs.items():
            ax = fig.add_axes([x/W, (H-y-h)/H, w/W, h/H], zorder=2)
            ax.set(xlim=(0, w), ylim=(h, 0)); ax.axis('off')
            box(ax, 0, 0, w, h, fills[key], '#C6AD69' if key=='a' else EDGE,
                radius=1.6, lw=.75)
            text(ax, 2.1, 4.0, key, 9.3, True)
            text(ax, 6.2, 4.0, titles[key], 9.3 if key!='d' else 8.7, True)
            panels[key] = ax

        # Survey observations enter the comparison independently of LLM inputs.
        line(canvas, [(17, 12), (17, 4.5), (156, 4.5), (156, 10.0)])
        arrow(canvas, (156, 10.0), (156, 12))
        text(canvas, 87, 2, 'Survey outcomes for comparison', 8, True,
             ha='center', color=BLUE)
        arrow(canvas, (33, 25), (39, 25))
        arrow(canvas, (33, 69), (39, 69))
        arrow(canvas, (83, 37), (83, 41))

        a = panels['a']
        text(a, 16, 11, 'LSMS–ISA', 10.5, True, ha='center')
        database(a, 5, 17, 8, 13)
        document(a, 8.5, 24, 5.2, 7.5)
        farmer(a, 17.3, 17.3, .82)
        text(a, 16, 37.5, '7 African countries', 9.3, True, ha='center')
        text(a, 16, 48, 'Ethiopia, Malawi, Mali\nNiger, Nigeria, Tanzania\nand Uganda',
             8.0, ha='center')
        text(a, 16, 60, '490 plot profiles', 10, True, ha='center')
        text(a, 16, 65.5, '70 per country', 8.6, ha='center')
        text(a, 16, 75, 'Balanced fertilizer users\nand non-users', 8, ha='center')
        line(a, [(3, 82), (29, 82)], '#C6AD69', .6)
        document(a, 3.2, 86.5, 5.2, 7.6)
        text(a, 10, 87.5, 'Survey outcomes', 8, True)
        text(a, 10, 92.5, 'Adoption and N rate', 7.4)
        text(a, 16, 99, 'Plot areas and weights', 8, ha='center')

        b = panels['b']
        document(b, 3, 10, 6, 8.4, True)
        text(b, 12, 10.6, '280 profiles · 4 countries · 3 interfaces', 8.4)
        for i, label in enumerate(['T1', 'T2', 'T3', 'T4']):
            box(b, 12+i*8, 14, 6.3, 4.3,
                '#FFE3A0' if i==0 else WHITE, EDGE, .45, .5)
            text(b, 15.15+i*8, 16.2, label, 8, True, ha='center', color=BLUE)
        text(b, 49, 16.3, '3,360 responses', 8.8, True)
        text(b, 44, 22.3, 'T1 used as the common application setting', 8.3, ha='center')

        c = panels['c']
        box(c, 2, 9, 30, 42, PALE_BLUE)
        box(c, 34, 9, 52, 42, PALE_BLUE)
        text(c, 17, 15, 'Seven-country\nT1 benchmark', 8.8, True, ha='center')
        document(c, 11.5, 21.8, 6, 8.2, True)
        document(c, 14, 24, 6, 8.2, True)
        text(c, 17, 36, '490 profiles', 9.0, True, ha='center')
        text(c, 17, 41.4, '1,470 records', 8.5, True, ha='center')
        text(c, 17, 46.8, '840 shared T1\n+ 630 extension', 7.6, ha='center')
        text(c, 60, 12.8, 'Paired country-label experiment', 8.5, True, ha='center')
        text(c, 60, 18, '70 fixed Tanzanian profiles', 8.4, True, ha='center')
        document(c, 36.5, 22, 6.1, 8.7, True)
        lock(c, 41.5, 27.2, 3.2)
        arrow(c, (45.6, 27), (49.4, 27), ms=5)
        for i, label in enumerate(['ETH', 'MWI', 'MLI', 'NER', 'NGA', 'TZA', 'UGA']):
            row, col = divmod(i, 4)
            xx, yy = 50.6+col*8.4+row*4.2, 22.3+row*5.8
            box(c, xx, yy, 7.4, 4.2, '#FFE3A0' if label=='TZA' else WHITE,
                EDGE, .45, .45)
            text(c, xx+3.7, yy+2.1, label, 7.5, True, ha='center', color=BLUE)
        text(c, 60, 36.0, 'Country label alone varies', 8.5, True, ha='center')
        text(c, 60, 40.7, 'Region omitted; other fields fixed', 7.7, ha='center')
        text(c, 60, 45.0, '70 profiles × 7 labels × 3 interfaces', 7.6, ha='center')
        text(c, 60, 49.0, '1,470 records (420 reused)', 7.7, True, ha='center')
        text(c, 44, 54, 'East Africa label: same 70 profiles; 210 additional responses',
             7.6, ha='center')
        box(c, 2, 57, 84, 15, GREEN, '#9ABD83')
        text(c, 5, 60.4, '3 LLM interfaces', 8.7, True)
        # Functional interface symbols, rather than raster brand marks.
        for i, label in enumerate(['Claude', 'Codex', 'Kimi']):
            xx = 5+i*13
            box(c, xx, 63, 11, 4.9, WHITE, '#92AF94', .65, .5)
            text(c, xx+5.5, 65.5, label, 8.0, True, ha='center', color=GREEN_INK)
        arrow(c, (44, 65.5), (50, 65.5), ms=6)
        document(c, 53, 60.5, 4.6, 6.6)
        text(c, 55.3, 69.3, 'Fertilizer use', 7.4, ha='center')
        bag(c, 73, 60, 4.8, 7.2)
        text(c, 75.4, 69.3, 'N rate', 7.6, ha='center')

        d = panels['d']
        for y, h in [(10, 22), (35, 20), (58, 18), (79, 22)]:
            box(d, 2, y, 42, h, '#FFFCF7', '#FFFCF7', 1.3, 0)
        text(d, 4, 13.5, 'National estimates', 9.1, True)
        scatter_icon(d, 4.5, 19, 8, 8)
        text(d, 15, 21, 'Survey-calibrated\nadoption and N rates', 7.8)
        text(d, 4, 29.5, 'Public-statistics benchmark', 7.8)
        text(d, 4, 38.5, 'Individual agreement', 9, True)
        document(d, 4.5, 43, 4.8, 7)
        axc, ayc = 12, 46
        d.add_patch(Circle((axc, ayc), 1.9, fc='none', ec=INK, lw=.7))
        line(d, [(axc+1.3, ayc+1.3), (axc+3.3, ayc+3.5)], INK, .8)
        text(d, 18, 46, 'r, AUC and\nprediction errors', 7.9)
        text(d, 4, 61.6, 'Farmer and plot associations', 8.4, True)
        traits(d, 4.5, 64.3)
        text(d, 17, 69.5, 'Trait relationships\nin the full surveys', 7.8)
        text(d, 4, 82.6, 'Nitrogen quantities', 9, True)
        field(d, 4, 86.5, 8, 5)
        text(d, 16, 88.9, '×', 12, ha='center')
        weight(d, 20, 85.5, 5, 6.3)
        text(d, 29, 88.8, 'Weighted\nquantities', 7.7)
        text(d, 4, 95, 'N rate × plot area × survey weight', 7.6)
        text(d, 4, 99, 'Eligible survey records', 7.6)
        # Model outputs branch to comparisons; survey outcomes enter from above.
        line(canvas, [(127, 106.5), (130, 106.5), (130, 34)])
        for yy in [34, 58, 80, 102]:
            arrow(canvas, (130, yy), (135, yy), ms=5.5)

        # Same horizontal analytical-check strip as the original design.
        box(canvas, 1, 119, 178, 29, '#F4F7FA', EDGE, 1.6, .75)
        text(canvas, 3, 122.7, 'Analytical checks', 9.5, True)
        widths = [41.5, 41.5, 41.5, 41.5]
        xs = [3, 47, 91, 135]
        fills2 = [PALE_BLUE, GREEN, CREAM, '#EBEFF5']
        heads = ['Transfer benchmarks', 'Paired-label contrasts',
                 'Statistical inference', 'Sensitivity analyses']
        for x, ww, fill, head in zip(xs, widths, fills2, heads):
            box(canvas, x, 126, ww, 20.3, fill, fill, 1, 0)
            text(canvas, x+2, 129.2, head, 8.5, True)
        for i in range(6):
            document(canvas, 5+(i%3)*3.8, 132+(i//3)*4.0, 2.7, 3.3)
        arrow(canvas, (17, 136), (23, 136), ms=5)
        document(canvas, 25, 132, 4.4, 7.5)
        text(canvas, 5, 143.2, 'Train on 6 countries; test on 1', 7.6)
        document(canvas, 49, 132, 4.6, 6.6, True)
        document(canvas, 72, 132, 4.6, 6.6, True)
        arrow(canvas, (55, 134.2), (70, 134.2), ms=5)
        arrow(canvas, (70, 137.2), (55, 137.2), ms=5)
        lock(canvas, 61.1, 132, 3.0)
        text(canvas, 49, 143.2, 'Same profile; different country labels', 7.3)
        document(canvas, 95, 132.1, 3.8, 5.8)
        document(canvas, 96.2, 133, 3.8, 5.8)
        arrow(canvas, (101, 132.3), (101, 138.5), ms=5)
        for i in range(4):
            box(canvas, 108, 132.5+i*1.8, 2.6, 1, ['#7BA9C7','#B1BE89','#DAB878','#8DB3A0'][i],
                INK, 0, .35)
            box(canvas, 122, 132.5+i*1.8, 2.6, 1, ['#DAB878','#8DB3A0','#7BA9C7','#B1BE89'][i],
                INK, 0, .35)
            line(canvas, [(110.6,133+i*1.8), (122,133+((i+2)%4)*1.8)], EDGE, .5)
        text(canvas, 93, 143, 'Bootstrap and permutation\nHolm adjustment', 7.6)
        document(canvas, 139, 132, 4.6, 6.6, True)
        document(canvas, 145, 133, 4.6, 6.6, True)
        arrow(canvas, (152, 136), (158, 136), ms=5)
        weight(canvas, 161, 132, 5, 6.4)
        text(canvas, 137, 143, 'Profile influence and weights\nPrompt context', 7.6)
        text(canvas, 90, 151, '5,670 distinct African responses; shared calls counted once',
             8, ha='center')

        fig.canvas.draw()
        require_matplotlib_panel_alignment(
            fig, axes=list(panels.values()), panel_ids=list(panels),
            row_groups=[['a','d']], column_groups=[['b','c']],
            tolerance_pt=1.5, gutter_tolerance_pt=1.5,
            require_panel_labels=True, strict=True,
            json_out=qa/'Fig_1.alignment.json', overlay_svg=qa/'Fig_1.alignment.svg')
        fig.savefig(root/'Fig_1.pdf')
        fig.savefig(root/'Fig_1.svg')
        fig.savefig(root/'Fig_1.png', dpi=600)
        plt.close(fig)
    contract = {
        'archetype':'schematic-led composite',
        'purpose':'Relate African prompt assessment to the country-label application and its comparisons.',
        'style':'Original rounded blue/cream panels, functional line icons and routed blue arrows.',
        'font':'Times New Roman, user preference', 'size_mm':[W,H],
        'response_counts':{'prompt_assessment':3360,'shared_T1':840,
                           'extension':630,'country_label_matrix':1470,
                           'reused_within_label_matrix':420,'regional_label':210,
                           'distinct':5670},
        'distinct_count_equation':'3360 + 630 + 1470 + 210 = 5670',
        'T1_description':'common application setting, not a best-prompt claim',
        'icons':'Schematic line drawings, not measured data or vendor logos.',
        'analytical_strip':'Four equal cards; intentionally subordinate to the main flow.',
    }
    (qa/'Fig_1.design_contract.json').write_text(json.dumps(contract,indent=2))


if __name__=='__main__':
    render(Path(__file__).resolve().parent)
