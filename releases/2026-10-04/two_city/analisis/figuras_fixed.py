from pathlib import Path
import shutil,json
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
ROOT=Path(__file__).resolve().parents[1];DST=ROOT
data=pd.read_json(ROOT/'fixed/summary.json');select=pd.read_parquet(ROOT/'fixed/inspection_a1.parquet')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42})
colors=['#0072B2','#D55E00','#009E73'];modes=['network','connectors_sun','connectors_shade'];names=['Network','Sun connections','Shade connections']
fig,axs=plt.subplots(2,2,figsize=(8.2,6.5),sharex=True,sharey=True,layout='constrained')
for i,city in enumerate(['Valencia','Madrid']):
    for j,w in enumerate(['Morning','Afternoon']):
        ax=axs[i,j]
        for mode,color,mark,label in zip(modes,colors,['o','^','s'],names):
            d=data.query('city==@city and window==@w and mode==@mode').sort_values('amplitude')
            ax.plot(d.amplitude,d.minimum_loss,color=color,marker=mark,ms=4,lw=1.5,label=label)
        ax.axhline(1,color='black',linestyle='--',lw=1)
        ax.set_title(f'({chr(97+i*2+j)}) {city}: {w.lower()}');ax.set_xticks([0,.5,1,1.5,2]);ax.set_ylim(0,8);ax.grid(axis='y',alpha=.16)
        if i==1:ax.set_xlabel('Grid amplitude a (°C)')
        if j==0:ax.set_ylabel('Minimum worst loss (%)')
h,l=axs[0,0].get_legend_handles_labels();fig.legend(h,l,loc='outside lower center',ncol=3,frameon=False)
fig.savefig(DST/'figuras/F10_fixed_margin.pdf');fig.savefig(DST/'figuras/F10_fixed_margin.eps');fig.savefig(DST/'figuras/F10_fixed_margin.png',dpi=200);plt.close(fig)

rows=[];summary=[]
for city in ['Valencia','Madrid']:
    for w in ['Morning','Afternoon']:
        for mode,name in zip(modes,names):
            d=data.query('city==@city and window==@w and mode==@mode').sort_values('amplitude')
            bad=d[d.lower_bound_loss>1+1e-7]
            first=float(bad.amplitude.min()) if len(bad) else None
            l1=float(d[d.amplitude.eq(1)].minimum_loss.iloc[0]);l2=float(d[d.amplitude.eq(2)].minimum_loss.iloc[0])
            f=f'{first:.2f}' if first is not None else 'None to 2.00'
            rows.append(f'{city} & {w} & {name} & {f} & {l1:.2f} & {l2:.2f}'+r'\\')
            summary.append(dict(city=city,window=w,mode=mode,first_incompatible_grid_amplitude=first,loss_a1=l1,loss_a2=l2))
(DST/'tablas/fixed_margins.tex').write_text(r'''\begin{table}[htbp]\centering\small
\caption{Compatibility margins on the fixed perturbation grid, using all six summers. Every amplitude includes both fields shifted in 0.25~$^\circ$C steps from $-a$ to $+a$. The first incompatible amplitude is the first evaluated set for which no list attains 99\% in every scenario; it is not a continuous or physically calibrated error bound. Loss is relative to each scenario's own optimum.}\label{tab:fixed}
\begin{tabular}{lllrrr}\toprule
City & Window & Connections & First failure & Loss at $a=1$ & Loss at $a=2$\\
 & & & ($^\circ$C) & (\%) & (\%)\\\midrule
'''+ '\n'.join(rows)+r'''
\bottomrule\end{tabular}\end{table}
''',encoding='utf-8')

fig,axs=plt.subplots(2,2,figsize=(8.2,8.2),layout='constrained')
palette={'both':'#0072B2','added':'#009E73','removed':'#D55E00','neither':'#eeeeee','unreachable':'#ffffff'}
maps=ROOT/'fixed/mapas';maps.mkdir(exist_ok=True)
changes=[]
for i,city in enumerate(['Valencia','Madrid']):
    p=ROOT/f'fixed/mapas/{city}_a1.gpkg'
    geo=gpd.read_file(p)[['CUSEC','geometry']];geo['CUSEC']=geo.CUSEC.astype(str)
    layer=geo.copy()
    for w in ['Morning','Afternoon']:
        for mode in modes:
            q=select.query('city==@city and window==@w and mode==@mode').copy()
            column=w+'_'+mode
            q[column]=np.select([q.local&q.maximin,~q.local&q.maximin,q.local&~q.maximin],['both','added','removed'],default='neither')
            layer=layer.merge(q[['CUSEC',column]],on='CUSEC',how='left',validate='one_to_one');layer[column]=layer[column].fillna('unreachable')
    # Source geometry remains unchanged during figure regeneration.
    bounds=layer.loc[layer.Morning_network.ne('unreachable')].total_bounds
    for j,w in enumerate(['Morning','Afternoon']):
        ax=axs[i,j];col=w+'_network'
        layer.plot(ax=ax,color=layer[col].map(palette),edgecolor='#a7a7a7',linewidth=.15)
        for cat,hatch in [('added','///'),('removed','\\\\\\')]:
            sub=layer[layer[col].eq(cat)]
            if len(sub):sub.plot(ax=ax,facecolor=palette[cat],edgecolor='#333333',linewidth=.2,hatch=hatch)
        n=int(layer[col].eq('added').sum());q=select.query('city==@city and window==@w and mode=="network"');k=int(q.maximin.sum())
        changes.append(dict(city=city,window=w,mode='network',quota=k,exchanges=n))
        ax.set_title(f'({chr(97+i*2+j)}) {city}: {w.lower()}\n{k} slots; {n} replacements',fontsize=11)
        ax.set_xlim(bounds[0]-300,bounds[2]+300);ax.set_ylim(bounds[1]-300,bounds[3]+300);ax.set_axis_off();ax.set_aspect('equal')
        length=2000 if city=='Valencia' else 5000
        x=bounds[0]+.055*(bounds[2]-bounds[0]);y=bounds[1]+.045*(bounds[3]-bounds[1]);ax.plot([x,x+length],[y,y],color='black',lw=1.5);ax.text(x+length/2,y+.018*(bounds[3]-bounds[1]),f'{length//1000} km',ha='center',fontsize=8);ax.text(.98,.93,'N ↑',transform=ax.transAxes,ha='right',fontsize=9)
legend=[Patch(facecolor=palette[c],edgecolor='#555555',hatch=h,label=label) for c,h,label in [('both',None,'Selected by both'),('added','///','Added by maximin'),('removed','\\\\\\','Original local only'),('neither',None,'Other reachable'),('unreachable',None,'Unreachable')]]
fig.legend(handles=legend,loc='outside lower center',ncol=3,frameon=False,fontsize=10)
fig.savefig(DST/'figuras/F11_fixed_maps.pdf');fig.savefig(DST/'figuras/F11_fixed_maps.eps');fig.savefig(DST/'figuras/F11_fixed_maps.png',dpi=200);plt.close(fig)
(ROOT/'fixed/margins.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
(ROOT/'fixed/map_changes.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')
bench=pd.read_parquet(ROOT/'fixed/benchmarks.parquet').query('amplitude==1')
rows=[]
for city in ['Valencia','Madrid']:
    for w in ['Morning','Afternoon']:
        for mode,label in zip(modes,['Network','Sun','Shade']):
            q=bench.query('city==@city and window==@w and mode==@mode').set_index('rule')
            vals=[q.loc[rule,'minimum_capture'] for rule in ['Population','Uniform','Shared','Local','Regional','Two-reference pooling','All-scenario pooling','Maximin']]
            rows.append(f'{city} & {w[:2]} & {label} & '+' & '.join(f'{v:.2f}' for v in vals)+r'\\')
(DST/'tablas/fixed_baselines.tex').write_text(r'''\begin{table}[htbp]\centering\scriptsize
\caption{Minimum capture across the 18 fixed-grid scenarios at $a=1~^\circ$C. P: population; U: uniform; S: shared; L/R: original local/regional; Pool2: original two-reference pooling; PoolAll: pooling all active scenarios. Maximin is the best achievable minimum. Values are percentages of each scenario's own optimum.}\label{tab:fixedbaselines}
\setlength{\tabcolsep}{3pt}\begin{tabular}{lllrrrrrrrr}\toprule
City & Time & Connections & P & U & S & L & R & Pool2 & PoolAll & Maximin\\\midrule
'''+ '\n'.join(rows)+r'''\bottomrule\end{tabular}\end{table}''',encoding='utf-8')
print('Margins and maps prepared:',changes)
