"""Figure 5 of the revision: simple-rule sufficiency under contrast amplification and residual-informed errors."""
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':11,'axes.labelsize':10,'pdf.fonttype':42,'ps.fonttype':42})
SER=[('Valencia','Afternoon','#AA3377','Valencia PM'),('Valencia','Morning','#CCBB44','Valencia AM'),('Madrid','Morning','#4477AA','Madrid AM'),('Madrid','Afternoon','#66CCEE','Madrid PM')]
e=1+1e-7
st=pd.read_csv(R/'capacidad/estados_amplificacion.csv');st['state']=np.select([st.pop_loss<=e,st.uni_loss<=e,st.minimum_common_loss<=e],['P','U','C'],'X')
am=pd.read_csv(R/'amplificacion/amplificacion_288.csv');am['simple']=(am.pop_loss<=e)|(am.uni_loss<=e)
pe=pd.read_parquet(R/'perturbaciones/perturbaciones_100.parquet');pe['simple']=(pe.pop_loss<=e)|(pe.uni_loss<=e)
fig,axs=plt.subplots(1,2,figsize=(7.4,3.4),sharey=True)
ax=axs[0]
ax.axvspan(0.75,1.34,color='0.85',lw=0,zorder=0);ax.axvspan(1.34,2.24,color='0.93',lw=0,zorder=0)
ax.text(1.17,2,'PM',ha='center',va='bottom',fontsize=8,color='0.3');ax.text(1.79,2,'AM',ha='center',va='bottom',fontsize=8,color='0.3')
for c,w,col,lab in SER:
    s=am[(am.city==c)&(am.window==w)].groupby('a').simple.sum()
    ax.plot(s.index,s.values,'-o',color=col,ms=3.5,lw=1.6,label=lab)
    t=st[(st.city==c)&(st.window==w)].assign(ok=lambda x:x.state!='X').groupby('a').ok.sum()
    ax.plot(t.index,t.values,'--',color=col,lw=1)
ax.axvline(1,color='0.4',lw=.8,ls=':')
ax.set_xlabel('Amplification of station-field anomalies, $a$');ax.set_ylabel('Cases (of 72)')
ax.set_title('(a) Contrast amplification',loc='left');ax.set_xlim(-0.1,4.1);ax.set_ylim(0,80)
ax=axs[1];x0={0:0,1000:1,2500:2,5000:3}
for k,(c,w,col,lab) in enumerate(SER):
    for sig,mk,ls,off in [(0.4,'o','-',-0.08),(0.6,'s','--',0.08)]:
        g=pe[(pe.city==c)&(pe.window==w)&(pe.sigma==sig)&(pe.hourly_sd==0)].groupby(['range_m','real']).simple.sum().groupby('range_m')
        m=g.mean();lo=g.quantile(.05);hi=g.quantile(.95);xx=np.array([x0[v] for v in m.index])+off+(k-1.5)*0.03
        ax.errorbar(xx,m.values,yerr=[np.clip(m.values-lo.values,0,None),np.clip(hi.values-m.values,0,None)],fmt=mk,ls=ls,color=col,ms=3.5,lw=1,capsize=1.5,mfc=col if sig==0.4 else 'white')
    a1=am[(am.city==c)&(am.window==w)&(am.a==1)].simple.sum();ax.plot([-0.4],[a1],marker='D',color=col,ms=4)
ax.set_xticks([-0.4,0,1,2,3],['None','0','1','2.5','5']);ax.set_xlim(-0.7,3.4)
ax.set_xlabel('Correlation length of added error (km)');ax.set_title('(b) Residual-informed errors',loc='left')
from matplotlib.lines import Line2D
h=[Line2D([],[],color=col,lw=1.6,label=lab) for _,_,col,lab in SER]
h+=[Line2D([],[],color='0.3',lw=1.6,label='Simple rule (a)'),Line2D([],[],color='0.3',lw=1,ls='--',label='Common list exists (a)'),
    Line2D([],[],color='0.3',marker='o',ls='-',lw=1,label='σ = 0.4 °C (b)'),Line2D([],[],color='0.3',marker='s',mfc='white',ls='--',lw=1,label='σ = 0.6 °C (b)')]
fig.legend(handles=h,loc='lower center',ncol=4,frameon=False,fontsize=8,bbox_to_anchor=(0.5,-0.13))
fig.tight_layout()
out=R/'figuras';out.mkdir(exist_ok=True);fig.savefig(out/'Figure_5.pdf',bbox_inches='tight');fig.savefig(out/'Figure_5.png',dpi=220,bbox_inches='tight')
