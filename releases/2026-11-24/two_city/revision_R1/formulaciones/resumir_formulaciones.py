import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
e=1+1e-7
c=pd.read_csv('continuas.csv');c['state']=np.select([c.pop_loss_both<=e,c.uni_loss_both<=e,c.minimum_common_loss<=e],['P','U','C'],'X')
c['cell']=c.state+' '+c.uni_loss.round(2).astype(str)+'% '+c.changed_local_regional.astype(str)+'/'+c.k.astype(str)
print('Formulaciones continuas: estado, pérdida lista uniforme, secciones local≠regional');print(c.pivot_table(index=['city','window','mode'],columns='form',values='cell',aggfunc='first').to_string())
print(c.groupby('form').state.value_counts().unstack(fill_value=0).to_string())
d=pd.read_csv('descomposicion.csv');print('\nSpearman del score local central');print(d.round(3).to_string())
u=pd.read_csv('umbral_sombra.csv');print('\nUmbral de sombra');print(u.round(4).to_string())
v=pd.read_csv('velocidad.csv');v['simple']=(v.pop_loss<=e)|(v.uni_loss<=e)
print('\nVelocidad: casos simples (288)');print(v.groupby(['speed','variant']).simple.sum().unstack().to_string())
print(v.groupby(['speed','variant','city','window']).simple.sum().unstack(['city','window']).to_string())
print(v.groupby(['speed','city','mode']).N.first().unstack(['city','mode']).to_string())
