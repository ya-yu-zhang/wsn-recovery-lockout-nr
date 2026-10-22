"""Scientific figures from all 40 completed cases; no selected inputs or CIs."""
from pathlib import Path
import json, statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'figures'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':600,'ps.fonttype':42,'pdf.fonttype':42})

def save(fig,n):
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT/f'Fig{n}.png',dpi=600,bbox_inches='tight')
    fig.savefig(OUT/f'Fig{n}.eps',bbox_inches='tight')
    plt.close(fig)

def main():
    r=json.loads((ROOT/'results/reanalysis.json').read_text())
    facts=json.loads((ROOT/'results/recovery_mechanism_findings.json').read_text())
    assert facts['closing']['gate_blocked']==15 and facts['closing']['shadow_known']==11
    f,ax=plt.subplots(figsize=(7.2,3.6));ax.set_xlim(0,10);ax.set_ylim(0,5);ax.axis('off')
    boxes=[(.2,3.1,4.3,1.4,'225 s  Relay 6 removed\nSource 0 retains version 2\nRoute 0–8–6–9'),
           (5.5,3.1,4.3,1.4,'235 s and 240 s  Installation\nSource 0 requests admitted\nChannel access fails before DATA'),
           (5.5,1.15,4.3,1.35,'245 s  Transaction closes\nSource 0 reports version 2\nSource 1 reports version 3'),
           (.2,1.15,4.3,1.35,'245–315 s  Recovery blocked\nCandidates available at 15/15 checks\nGlobal service predicate unknown')]
    for x,y,w,h,text in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.04',linewidth=.8,edgecolor='#344054',facecolor='white'))
        ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=10,linespacing=1.6)
    for start,end in(((4.55,3.8),(5.4,3.8)),((7.65,3.02),(7.65,2.6)),((5.4,1.825),(4.6,1.825))):
        ax.annotate('',xy=end,xytext=start,arrowprops=dict(arrowstyle='->',lw=1,color='#344054'))
    ax.text(5,.48,'265 s received-only audit: offered [36, 60], timely [0, 59]\nHistorical deficit identified; no recovery action executed',ha='center',va='center',fontsize=10,linespacing=1.4)
    f.tight_layout();save(f,2)
    models=['full_v2','horizon','cohort','closing'];labels=['Full v2','Horizon','Cohort','Closing']
    colors={'multi_failure':'#1E6B80','overload':'#B35A35'}
    f,axes=plt.subplots(2,2,figsize=(7.2,5.4))
    for row,n in enumerate((10,20)):
        for col,field in enumerate(('service_vs_legacy_pp','control_reduction_vs_legacy_percent')):
            ax=axes[row,col]
            for y,m in enumerate(models):
                pp=[x for x in r['paired_results']if x['nodes']==n and x['model']==m]
                for k,p in enumerate(pp):ax.plot(p[field],y+(k-1.5)*.07,'o',ms=4,color=colors[p['scenario']],zorder=3)
                ax.plot(statistics.mean(p[field]for p in pp),y,'D',color='black',ms=4,zorder=4)
            ax.set_yticks(range(4),labels);ax.invert_yaxis();ax.grid(axis='x',color='#DDDDDD',lw=.6)
            ax.axvline(-.5 if col==0 else 20,color='black',ls=':',lw=1)
            ax.set_title(f'{n} nodes',loc='left',fontsize=10,fontweight='bold')
            ax.set_xlabel('Service difference (percentage points)'if col==0 else'Control DATA reduction (%)')
            if col==0:ax.set_xlim((-30.5,3)if n==10 else(-.8,3.2))
            else:ax.set_xlim((8,38)if n==10 else(18,40))
    handles=[Line2D([0],[0],marker='o',ls='',color=colors[s],label=l)for s,l in(('multi_failure','Relay removals'),('overload','Overload'))]+[Line2D([0],[0],marker='D',ls='',color='black',label='Four-cell mean')]
    f.legend(handles=handles,loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(.5,-.012))
    f.tight_layout(rect=(0,.04,1,1));save(f,1)
    print('Created two PNG and EPS figures from all matched cells')

if __name__=='__main__':main()
