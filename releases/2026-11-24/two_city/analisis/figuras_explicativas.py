"""Publication figures and tables from the audited explanatory outputs only."""
from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
R=Path(__file__).resolve().parents[1]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.titlesize':12,'axes.labelsize':11,'pdf.fonttype':42,'ps.fonttype':42})
D=pd.read_csv(R/'tablas/mechanism_summary.csv')
B=pd.read_csv(R/'tablas/practical_benchmarks.csv')
Y=pd.read_csv(R/'tablas/mechanism_annual_central.csv')
MODES=['network','connectors_sun','connectors_shade'];CITIES=['Valencia','Madrid'];WINDOWS=['Morning','Afternoon']
LABEL={'network':'Network','connectors_sun':'Sun conn.','connectors_shade':'Shade conn.'}
WLABEL={'Morning':'AM','Afternoon':'PM'}
PARTS=['solar_failure','shared_thermal_failure','local_only_failure']
COLORS=['#4477AA','#EEAA33','#AA3377']
STAGES=['Population sufficient','Uniform sufficient','Other common selection','Incompatible']
SCOL=['#228833','#66CCEE','#CCBB44','#AA3377']
def save(fig,name):
    fig.savefig(R/f'figuras/{name}.pdf',bbox_inches='tight')
    fig.savefig(R/f'figuras/{name}.eps',bbox_inches='tight')
    fig.savefig(R/f'figuras/{name}.png',dpi=220,bbox_inches='tight');plt.close(fig)
def central(w):
    z=D[D.threshold.eq(30)&D.phi.eq(.4)&D.window.eq(w)].set_index(['city','mode'])
    return z.loc[[(c,m) for c in CITIES for m in MODES]].reset_index()
def main():
    for folder in ['figuras','tablas','qa']:(R/folder).mkdir(exist_ok=True)
    fig,axs=plt.subplots(2,2,figsize=(8.2,7.2),sharey='row',gridspec_kw={'height_ratios':[1,1.15]})
    for j,w in enumerate(WINDOWS):
        z=central(w);y=np.arange(6);labels=[f'{c[:3]} / {LABEL[m]}' for c,m in zip(z.city,z['mode'])]
        ax=axs[0,j];left=np.zeros(6)
        for p,col in zip(PARTS,COLORS):
            v=100*z[p+'_local_top_score_share'].to_numpy();ax.barh(y,v,left=left,color=col,height=.64)
            for i,x in enumerate(v):
                if x>=9:ax.text(left[i]+x/2,i,f'{x:.0f}',ha='center',va='center',fontsize=11,color='white' if col!='#EEAA33' else 'black')
            left+=v
        ax.set_xlim(0,100);ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_title(f'({chr(97+j)}) {w}');ax.set_xlabel('Share of local top-list score (%)')
        ax=axs[1,j]
        ax.scatter(z.population_min_capture,y-.10,marker='s',s=34,color='#228833',label='Population')
        ax.scatter(z.uniform_min_capture,y+.10,marker='D',s=28,color='#0077BB',label='Uniform temperature')
        ax.axvline(99,color='#555555',ls='--',lw=1);ax.set_xlim(53,101);ax.set_xticks([60,70,80,90,99])
        ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_title(f'({chr(99+j)}) Simple-list performance');ax.set_xlabel('Minimum capture across references (%)')
        ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
    handles,labels=axs[1,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.56,-.045),ncol=2,fontsize=10,frameon=False)
    for ax in axs.flat:ax.set_ylim(5.6,-.6)
    fig.legend(handles=[Patch(color=c,label=l) for c,l in zip(COLORS,['Solar criterion fails','Solar passes; both thermal criteria fail','Solar passes; local thermal criterion alone fails'])],loc='upper center',bbox_to_anchor=(.53,1.02),ncol=1,frameon=False,fontsize=10)
    fig.subplots_adjust(top=.84,bottom=.09,left=.19,right=.99,hspace=.4,wspace=.14)
    save(fig,'F4_score_partition')
    fig,axs=plt.subplots(1,2,figsize=(8.1,4.1),sharey=True)
    for j,w in enumerate(WINDOWS):
        z=central(w);ax=axs[j];y=np.arange(6)
        for i,row in z.iterrows():
            ax.plot([row.dual_TV,row.best_feasible_baseline_TV],[i,i],color='#777777',lw=1.4)
            ax.text(row.best_feasible_baseline_TV+.006,i,row.best_feasible_baseline,va='center',fontsize=10)
        ax.scatter(z.best_feasible_baseline_TV,y,facecolors='white',edgecolors='#0077BB',s=42,label='Best passing baseline')
        ax.scatter(z.dual_TV,y,color='#AA3377',s=35,label='District optimum')
        ax.set_yticks(y,[f'{c[:3]} / {LABEL[m]}' for c,m in zip(z.city,z['mode'])]);ax.invert_yaxis()
        ax.set_xlim(0,.44);ax.set_xticks([0,.1,.2,.3,.4]);ax.set_title(w);ax.set_xlabel('District deviation (TV)');ax.grid(axis='x',alpha=.2)
    axs[0].legend(loc='lower left',bbox_to_anchor=(0,-.38),frameon=False,ncol=2,fontsize=10)
    for ax in axs:ax.set_ylim(5.6,-.6)
    fig.subplots_adjust(left=.2,right=.99,bottom=.28,top=.88,wspace=.13);save(fig,'F5_baseline_representation')
    fig,axs=plt.subplots(4,3,figsize=(8.2,8),sharex=True,sharey=True)
    phi=[.1,.2,.3,.4,.5,.6,.7,1.]
    for i,(city,w) in enumerate([(c,w) for c in CITIES for w in WINDOWS]):
        for j,mode in enumerate(MODES):
            z=D[D.city.eq(city)&D.window.eq(w)&D['mode'].eq(mode)]
            arr=z.assign(code=z.stage.map(dict(zip(STAGES,range(4))))).pivot(index='threshold',columns='phi',values='code').loc[[28,30,32],phi].to_numpy()
            ax=axs[i,j];ax.imshow(arr,cmap=ListedColormap(SCOL),vmin=-.5,vmax=3.5,aspect='auto',origin='lower')
            for r in range(3):
                for k in range(8):ax.text(k,r,['P','U','C','X'][arr[r,k]],ha='center',va='center',fontsize=11,color='white' if arr[r,k] in [0,3] else 'black')
            ax.set_xticks(range(8),['.1','.2','.3','.4','.5','.6','.7','1'],rotation=45);ax.set_yticks(range(3),[28,30,32])
            if i==0:ax.set_title(LABEL[mode])
            if j==0:ax.set_ylabel(f'{city} / {WLABEL[w]}\nTemperature (°C)')
            if i==3:ax.set_xlabel('Exposed-fraction threshold')
    fig.legend(handles=[Patch(color=c,label=l) for c,l in zip(SCOL,['P: population passes','U: uniform passes, P fails','C: other common selection','X: no common selection'])],loc='lower center',ncol=2,frameon=False,fontsize=10)
    fig.subplots_adjust(left=.13,right=.99,bottom=.15,top=.95,wspace=.12,hspace=.17);save(fig,'F6_practical_states')
    z=D[D['mode'].eq('network')&D.threshold.eq(30)&D.phi.eq(.4)].set_index(['city','window']).loc[[(c,w) for c in CITIES for w in WINDOWS]].reset_index()
    lines=[r'\begin{table}[htbp]\centering\footnotesize',r'\caption{Central network-only decisions. AM and PM denote the morning and afternoon windows. Solar, Shared and Exclusive are solar-criterion failure, shared thermal failure and local-only thermal failure; they partition the local top-list score, up to rounding. P and U are the smaller captures under the two references for population and uniform-temperature rankings. TV shows best passing fixed baseline $\rightarrow$ district optimum; lower is better.}\label{tab:mechanisms}',r'\setlength{\tabcolsep}{3pt}\begin{tabular}{llrrrrrr}',r'\toprule City & Window & Solar (\%) & Shared heat (\%) & Local only (\%) & P (\%) & U (\%) & TV\\\midrule']
    for _,r in z.iterrows():
        vals=[100*r[p+'_local_top_score_share'] for p in PARTS]
        lines.append(f"{r.city} & {WLABEL[r.window]} & {vals[0]:.1f} & {vals[1]:.1f} & {vals[2]:.1f} & {r.population_min_capture:.2f} & {r.uniform_min_capture:.2f} & ${r.best_feasible_baseline_TV:.3f}\\!\\rightarrow\\!{r.dual_TV:.3f}$"+r'\\')
    lines += [r'\bottomrule\end{tabular}\end{table}'];(R/'tablas/mechanisms.tex').write_text('\n'.join(lines).replace('Shared heat (\\%)','Shared (\\%)').replace('Local only (\\%)','Exclusive (\\%)').replace('Window &','Time &'),encoding='utf8')
    lines=[r'\begin{table}[htbp]\centering\small',r'\caption{Hierarchical decision states across the designed grid. Uniform counts exclude cases already passing with population. Counts are not occurrence probabilities.}\label{tab:stages}',r'\begin{tabular}{llrrrr}\toprule City & Window & Population & Uniform & Other common & Incompatible\\\midrule']
    for city in CITIES:
        for w in WINDOWS:
            c=D[D.city.eq(city)&D.window.eq(w)].stage.value_counts()
            lines.append(f'{city} & {w} & '+' & '.join(str(c.get(s,0)) for s in STAGES)+r'\\')
    lines += [r'\midrule Total & & 50 & 162 & 44 & 32\\\bottomrule\end{tabular}\end{table}'];(R/'tablas/practical_states.tex').write_text('\n'.join(lines))
    lines=[r'\begin{table}[htbp]\centering\small',r'\caption{Annual central network-only ranges, with the pooled regional correction held fixed. Annual rankings and denominators are recalculated. Solar and shared heat are percentages of the annual local top-list score; P and U are the minimum captures across references for population and uniform-temperature rankings, respectively.}\label{tab:annual_mechanisms}',r'\begin{tabular}{llrrrr}\toprule City & Window & Solar (\%) & Shared heat (\%) & P (\%) & U (\%)\\\midrule']
    for city in CITIES:
        for w in WINDOWS:
            a=Y[Y.city.eq(city)&Y.window.eq(w)&Y['mode'].eq('network')];vals=[]
            for col,scale in [('solar_failure_local_top_score_share',100),('shared_thermal_failure_local_top_score_share',100),('population_min_capture',1),('uniform_min_capture',1)]:
                vals.append(f'{a[col].min()*scale:.2f}--{a[col].max()*scale:.2f}')
            lines.append(f'{city} & {w} & '+' & '.join(vals)+r'\\')
    lines += [r'\bottomrule\end{tabular}\end{table}'];(R/'tablas/annual_mechanisms.tex').write_text('\n'.join(lines))
    z[['city','window']].to_csv(R/'qa/figure_case_order.csv',index=False)
    print('Three figures and three tables written.',flush=True)
if __name__=='__main__':main()
