import sys, pandas as pd, numpy as np
d=pd.read_parquet(sys.argv[1] if len(sys.argv)>1 else 'perturbaciones_100.parquet')
d['simple']=(d.pop_loss<=1+1e-9)|(d.uni_loss<=1+1e-9)
d['station_ok']=d.station_list_loss<=1+1e-9
d['frac_changed']=d.changed_vs_station/d.k
d['cfg']='σ='+d.sigma.astype(str)+' L='+(d.range_m/1000).astype(str)+'km'+np.where(d.hourly_sd>0,' +h'+d.hourly_sd.astype(str),'')
tot=d.groupby(['cfg','real']).simple.sum().groupby('cfg').agg(['mean',lambda x:x.quantile(.05),lambda x:x.quantile(.95)]);tot.columns=['media','p5','p95']
print('Casos con regla simple suficiente (de 288; publicado 212)');print(tot.round(1).to_string())
cw=d.groupby(['cfg','city','window','real']).simple.sum().groupby(['cfg','city','window']).mean().unstack(['city','window'])
print('\nMedia por ciudad y franja (de 72; publicado: Mad tarde 72, Mad mañana 48, Val tarde 33, Val mañana 59)');print(cw.round(1).to_string())
ch=d.groupby(['cfg','city','window']).frac_changed.median().unstack(['city','window'])
print('\nFracción mediana de la lista que cambia respecto a la de estaciones');print(ch.round(3).to_string())
sl=d.groupby(['cfg','city','window']).station_list_loss.median().unstack(['city','window'])
print('\nPérdida mediana de la lista de estaciones bajo el campo perturbado (%)');print(sl.round(2).to_string())
c=d[(d.threshold==30)&(d.phi==0.4)&(d['mode']=='network')]
cc=c.groupby(['cfg','city','window']).agg(cambia_mediana=('changed_vs_station','median'),cambia_p95=('changed_vs_station',lambda x:x.quantile(.95)),k=('k','first'),uni_loss_mediana=('uni_loss','median')).unstack(['city','window'])
print('\nCaso central (30 °C, φ 0,4, network)');print(cc.round(2).to_string())
st=d.groupby(['cfg','real'])[['simple','station_ok']].sum().groupby('cfg').mean()
st['uniform_better_or_equal']=d.assign(b=d.uni_loss<=d.station_list_loss+1e-9).groupby(['cfg','real']).b.sum().groupby('cfg').mean()
print('\nMedia de casos: regla simple ≤1 %, lista de estaciones ≤1 %, y casos en que la lista uniforme pierde igual o menos que la de estaciones');print(st.round(1).to_string());st.to_csv('resumen_valor_relativo.csv')
tot.to_csv('resumen_total.csv');cw.to_csv('resumen_ciudad_franja.csv');ch.to_csv('resumen_rotacion.csv');cc.to_csv('resumen_central.csv')
