import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
d=pd.read_csv('amplificacion_288.csv')
d['simple']=(d.pop_loss_both<=1+1e-9)|(d.uni_loss_both<=1+1e-9)
d['simple_both']=(d.pop_loss_both<=1+1e-9)|(d.uni_loss_both<=1+1e-9)
d['station_ok']=d.station_list_loss_under_a<=1+1e-9
d['frac_changed_vs_station']=d.changed_vs_station/d.k
g=d.groupby(['a']).agg(simple=('simple','sum'),simple_both=('simple_both','sum'),uniform_ok=('uni_loss',lambda x:(x<=1+1e-9).sum()),station_list_ok=('station_ok','sum'))
print('Totales (288 casos)');print(g.to_string())
t=d.pivot_table(index=['city','window'],columns='a',values='simple',aggfunc='sum');print('\nSimple (P o U, pérdida local <=1%) por ciudad y franja (72 casos c/u)');print(t.to_string())
t=d.pivot_table(index=['city','window'],columns='a',values='uni_loss',aggfunc='median');print('\nPérdida mediana de la lista uniforme (%)');print(t.round(2).to_string())
t=d.pivot_table(index=['city','window'],columns='a',values='frac_changed_vs_station',aggfunc='median');print('\nFracción mediana de la lista que cambia respecto a la lista de estaciones (a=1)');print(t.round(3).to_string())
t=d.pivot_table(index=['city','window'],columns='a',values='station_list_loss_under_a',aggfunc='median');print('\nPérdida mediana de la lista de estaciones evaluada con el campo amplificado (%)');print(t.round(2).to_string())
c=d[(d.threshold==30)&(d.phi==0.4)]
print('\nCasos centrales (30 °C, phi 0.4): secciones que cambian vs lista de estaciones / k, y pérdida de la lista uniforme')
c=c.assign(cell=c.changed_vs_station.astype(str)+'/'+c.k.astype(str)+' ('+c.uni_loss.round(2).astype(str)+')')
print(c.pivot_table(index=['city','window','mode'],columns='a',values='cell',aggfunc='first').to_string())
for a,gr in d.groupby('a'):pass
d.groupby(['a','city','window']).agg(simple=('simple','sum'),simple_both=('simple_both','sum'),median_uniform_loss=('uni_loss','median'),median_changed_vs_station=('frac_changed_vs_station','median'),median_station_list_loss=('station_list_loss_under_a','median')).reset_index().to_csv('resumen_amplificacion.csv',index=False)
