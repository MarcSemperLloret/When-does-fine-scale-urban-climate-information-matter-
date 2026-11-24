import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
d=pd.read_csv('capacidad_288x5.csv')
print('MILP status',d.milp_status.value_counts().to_dict())
e=1+1e-7
d['state']=np.select([d.pop_loss_both<=e,d.uni_loss_both<=e,d.minimum_common_loss<=e],['P','U','C'],'X')
t=d.pivot_table(index='capacity',columns='state',values='k',aggfunc='count',fill_value=0)[list('PUCX')];t['simple']=t.P+t.U
print('Estados por capacidad (288 casos)');print(t.to_string())
cw=d.assign(simple=d.state.isin(['P','U'])).pivot_table(index=['city','window'],columns='capacity',values='simple',aggfunc='sum');print('\nSimple por ciudad y franja');print(cw.to_string())
x=d.assign(X=d.state.eq('X')).pivot_table(index=['city','window'],columns='capacity',values='X',aggfunc='sum');print('\nSin lista común (X)');print(x.to_string())
d['f_lr']=d.changed_local_regional/d.k;d['f_lu']=d.changed_local_uniform/d.k
o=d.pivot_table(index=['city','window'],columns='capacity',values='f_lr',aggfunc='median');print('\nFracción mediana de la lista local que cambia con la regional');print(o.round(3).to_string())
o2=d.pivot_table(index=['city','window'],columns='capacity',values='f_lu',aggfunc='median');print('\nFracción mediana de la lista local que cambia con la uniforme');print(o2.round(3).to_string())
# Score vs overlap within the 212 simple cases at 15%
s=d[(d.capacity==.15)&d.state.isin(['P','U'])]
s=s.assign(changed=np.where(s.state=='P',s.changed_local_population,s.changed_local_uniform)/s.k)
print('\nCasos simples al 15 %: fracción de la lista que cambia respecto a la local; cuantiles',s.changed.quantile([.5,.75,.9,1]).round(3).to_dict(),'| casos con 0 cambios',int((s.changed==0).sum()))
print(s.groupby(['city','window']).changed.describe()[['count','50%','max']].round(3).to_string())
c=d[(d.threshold==30)&(d.phi==.4)]
print('\nCentrales: secciones local≠regional / k')
print(c.assign(v=c.changed_local_regional.astype(str)+'/'+c.k.astype(str)+' '+c.state).pivot_table(index=['city','window','mode'],columns='capacity',values='v',aggfunc='first').to_string())
t.to_csv('estados_capacidad.csv');d.to_csv('capacidad_288x5_estados.csv',index=False)
