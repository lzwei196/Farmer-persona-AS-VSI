"""Reproduce the revised farmer-persona figures from the accompanying CSV files."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from audit_panel_alignment import require_matplotlib_panel_alignment

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
QA=ROOT/'qa';QA.mkdir(exist_ok=True)
for font in Path('/System/Library/Fonts/Supplemental').glob('Times New Roman*.ttf'):
    font_manager.fontManager.addfont(str(font))
plt.rcParams.update({'font.family':'Times New Roman','font.serif':['Times New Roman'],'font.size':9,'axes.labelsize':9,'axes.titlesize':9.5,'xtick.labelsize':8.5,'ytick.labelsize':8.5,'legend.fontsize':8.5,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,'xtick.major.width':.65,'ytick.major.width':.65,'xtick.major.size':3,'ytick.major.size':3,'svg.fonttype':'none','pdf.fonttype':42,'text.usetex':False,'mathtext.fontset':'custom','mathtext.rm':'Times New Roman','mathtext.it':'Times New Roman:italic','mathtext.bf':'Times New Roman:bold','savefig.facecolor':'white'})
PROVIDERS=['claude','codex','kimi'];COLORS={'claude':'#39768C','codex':'#C17C42','kimi':'#5D8C74'};MARKERS={'claude':'o','codex':'s','kimi':'^'}
TIERS=['T1','T2','T3','T4'];OUTCOMES=['nitrogen_kg_per_ha','family_labor_days','hired_labor_days'];OUTCOME_LABELS=['Nitrogen','Family labor','Hired labor']
WIDTH=180/25.4

def read(name):
    with (DATA/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
AFRICA=read('african_configurations.csv');N=[r for r in AFRICA if r['outcome']=='nitrogen_kg_per_ha'];REFERENCE=read('african_nitrogen_reference.csv')[0]

def label(ax,letter,title=None):
    ax.annotate(letter,(0,1),xycoords='axes fraction',xytext=(-27,9),textcoords='offset points',weight='bold',fontsize=10,ha='left',va='bottom',annotation_clip=False)
    if title:ax.set_title(title,pad=10,loc='center')

def legend(fig,refs=None,y=.97):
    handles=[Line2D([],[],color=COLORS[p],marker=MARKERS[p],markersize=4,lw=1,label=p.capitalize()) for p in PROVIDERS]
    if refs:handles+=refs
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.53,y),ncol=len(handles),frameon=False,handlelength=2,columnspacing=1.7)

def design_axis(ax):
    ax.set_xlim(.8,4.2);ax.set_xticks(range(1,5),TIERS);ax.set_xlabel('Prompt design')

def curves(ax,rows,key):
    for p in PROVIDERS:
        selected={r['tier']:r for r in rows if r['provider']==p}
        ax.plot(range(1,5),[float(selected[t][key]) for t in TIERS],color=COLORS[p],marker=MARKERS[p],ms=4,lw=1,label=p.capitalize())
    design_axis(ax)

def save(fig,name):
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=QA/(name+'.alignment.json'),overlay_svg=QA/(name+'.alignment.svg'),tolerance_pt=1.5,gutter_tolerance_pt=1.5,require_panel_labels=True,strict=True)
    fig.savefig(ROOT/(name+'.pdf'))
    fig.savefig(ROOT/(name+'.svg'))
    fig.savefig(ROOT/(name+'.png'),dpi=600)
    plt.close(fig)

# Complementary distribution diagnostics for all configurations.
fig,axs=plt.subplots(1,3,figsize=(WIDTH,4.0));fig.subplots_adjust(left=.17,right=.98,bottom=.15,top=.86,wspace=.32)
order=[p+'_'+t for p in PROVIDERS for t in TIERS];data={r['provider']+'_'+r['tier']:r for r in N}
y=np.arange(len(order))
fields=['mean','ks_similarity','share_at_least_observed_p90'];titles=['Mean nitrogen','Distribution similarity','Upper-tail coverage'];xlabs=['kg N ha$^{-1}$','1 − KS statistic','At or above observed P90 (%)'];refs=[float(REFERENCE['real_mean']),float(REFERENCE['null_shape']),100*28/275]
for k,ax in enumerate(axs):
    for j,key in enumerate(order):
        p,t=key.split('_');value=float(data[key][fields[k]])*(100 if k==2 else 1)
        ax.scatter(value,j,color=COLORS[p],marker=MARKERS[p],s=20,zorder=3)
    ax.axvline(refs[k],color='.45',lw=.8,ls='--',zorder=0)
    ax.set_ylim(11.6,-.6);ax.set_yticks(y,[key.split('_')[0].capitalize()+' '+key.split('_')[1] for key in order] if k==0 else [])
    ax.set_xlabel(xlabs[k]);label(ax,chr(97+k),titles[k])
    ax.tick_params(axis='y',length=0)
axs[0].set_xlim(0,30);axs[0].set_xticks([0,10,20,30]);axs[1].set_xlim(.65,1);axs[1].set_xticks([.7,.8,.9,1]);axs[2].set_xlim(-.5,11.5);axs[2].set_xticks([0,5,10]);save(fig,'Fig_S1')

# Variation and upper-tail size across three distinct management outcomes.
fig,axs=plt.subplots(3,2,figsize=(WIDTH,5.7));fig.subplots_adjust(left=.10,right=.98,bottom=.09,top=.90,wspace=.35,hspace=.65)
for row,outcome in enumerate(OUTCOMES):
    records=[r for r in AFRICA if r['outcome']==outcome]
    for col,(key,ylabel) in enumerate([('sd_ratio','SD ratio'),('p90_ratio','P90 ratio')]):
        ax=axs[row,col];curves(ax,records,key);ax.set_ylabel(ylabel);ax.set_ylim(0,1.12);ax.set_yticks([0,.5,1]);ax.axhline(1,color='.45',lw=.8,ls='--',zorder=0)
        label(ax,chr(97+row*2+col),OUTCOME_LABELS[row]);
        if row<2:ax.set_xlabel('')
legend(fig,[Line2D([],[],color='.45',ls='--',lw=.8,label='Observed parity')],y=.99);save(fig,'Fig_S2')

# Country differences in the same four prompt designs.
fig,axs=plt.subplots(2,2,figsize=(WIDTH,4.35));fig.subplots_adjust(left=.10,right=.98,bottom=.12,top=.84,wspace=.35,hspace=.65)
countrydata=read('african_country_configurations.csv')
for i,country in enumerate(['Ethiopia','Malawi','Nigeria','Tanzania']):
    records=[r for r in countrydata if r['country']==country];ax=axs.flat[i];curves(ax,records,'pearson_r');ax.set_ylim(-.2,.5);ax.set_yticks([-.2,0,.2,.4]);ax.axhline(0,color='.7',lw=.65,ls=':',zorder=0);ax.set_ylabel('Pearson correlation');label(ax,chr(97+i),f'{country} (n = {records[0]["n"]})')
legend(fig);save(fig,'Fig_S3')

# Percentile ratios: band represents the range of configurations, not an interval.
quantiles=read('african_percentile_ratios.csv')
fig,axs=plt.subplots(1,3,figsize=(WIDTH,2.9));fig.subplots_adjust(left=.09,right=.98,bottom=.19,top=.79,wspace=.30)
for i,outcome in enumerate(OUTCOMES):
    rows=[r for r in quantiles if r['outcome']==outcome and r['display']=='True'];ps=sorted(set(int(r['percentile']) for r in rows));vals=[[float(r['ratio']) for r in rows if int(r['percentile'])==q] for q in ps]
    ax=axs[i];ax.fill_between(ps,[min(v) for v in vals],[max(v) for v in vals],color='#39768C',alpha=.17,lw=0);ax.plot(ps,[np.median(v) for v in vals],color='#39768C',lw=1.3);ax.axhline(1,color='.5',ls='--',lw=.8);ax.set_ylim(0,2);ax.set_xlim(60,100);ax.set_xticks([60,80,99]);ax.set_xlabel('Observed percentile');label(ax,chr(97+i),OUTCOME_LABELS[i]);ax.set_ylabel('Simulated / observed' if i==0 else '')
save(fig,'Fig_S4')

# Empirical CDFs retain all matched values and the full observed range.
ecdf=read('african_nitrogen_ecdf.csv');obs=[r for r in ecdf if r['provider']=='observed'];obsx=[0]+[float(r['value']) for r in obs];obsy=[0]+[float(r['ecdf']) for r in obs]
tiercolors=['#2E4F63','#5D8298','#8B6C43','#A8AB70'];linestyles=['-','--','-.',':']
fig,axs=plt.subplots(1,3,figsize=(WIDTH,2.95));fig.subplots_adjust(left=.09,right=.98,bottom=.20,top=.76,wspace=.30)
maximum=max(float(r['value']) for r in ecdf)
for i,p in enumerate(PROVIDERS):
    ax=axs[i]
    for t,color,ls in zip(TIERS,tiercolors,linestyles):
        rows=[r for r in ecdf if r['provider']==p and r['tier']==t];ax.step([0]+[float(r['value']) for r in rows],[0]+[float(r['ecdf']) for r in rows],where='post',color=color,lw=.95,ls=ls)
    ax.step(obsx,obsy,where='post',color='.1',lw=1.3);ax.set_xlim(0,maximum*1.02);ax.set_ylim(0,1.02);ax.set_yticks([0,.25,.5,.75,1]);ax.set_xlabel('Nitrogen rate (kg N ha$^{-1}$)');ax.set_ylabel('Cumulative fraction' if i==0 else '');label(ax,chr(97+i),p.capitalize())
handles=[Line2D([],[],color=c,lw=1,ls=l,label=t) for t,c,l in zip(TIERS,tiercolors,linestyles)]+[Line2D([],[],color='.1',lw=1.3,label='Observed')]
fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.53,.97),ncol=5,frameon=False);save(fig,'Fig_S5')

print('Rendered five African data figures with panel alignment checks.')
