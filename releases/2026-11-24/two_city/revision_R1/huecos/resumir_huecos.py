import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
E=1+1e-7
d=pd.read_csv('red_estaciones.csv');d['simple']=((d.pop_loss<=E)&(d.pop_loss_R<=E))|((d.uni_loss<=E)&(d.uni_loss_R<=E))
b=d[d.variant=='baseline_same_hours'].groupby(['city','excluded']).simple.sum()
a=d[d.variant!='baseline_same_hours'].groupby(['city','excluded']).simple.sum()
t=pd.DataFrame({'baseline_same_hours':b,'alternative':a})
a2=d[d.variant!='baseline_same_hours'].assign(f=lambda x:x.changed_vs_base/x.k).groupby(['city','excluded']).f.median()
t['median_changed']=a2;h=d.groupby(['city','excluded']).hours_kept.first()/d.groupby(['city','excluded']).hours_total.first();t['hours_share']=h
print('Red de estaciones: casos simples (de 144 por ciudad)');print(t.round(3).to_string())
cw=d[d.variant!='baseline_same_hours'].groupby(['city','excluded','window']).simple.sum().unstack();print(cw.to_string())
cb=d[d.variant=='baseline_same_hours'].groupby(['city','excluded','window']).simple.sum().unstack();print(cb.to_string())
tr=pd.read_csv('transmitancia.csv');tr['simple']=((tr.pop_loss<=E)&(tr.pop_loss_R<=E))|((tr.uni_loss<=E)&(tr.uni_loss_R<=E))
print('\nTransmitancia (network, 24 casos por ciudad y franja)')
print(tr.groupby(['city','window','tau']).simple.sum().unstack('tau').to_string())
print(tr.assign(f=tr.changed_vs_base/tr.k).groupby(['city','window','tau']).f.median().unstack('tau').round(3).to_string())
c=tr[(tr.threshold==30)&(tr.phi==.4)];print(c.pivot_table(index=['city','window'],columns='tau',values=['changed_vs_base','rho_shade_only']).round(3).to_string())
