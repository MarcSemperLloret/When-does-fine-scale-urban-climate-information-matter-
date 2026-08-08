# Fallos silenciosos y salvaguardas

Material suplementario. Cada fila es un fallo que **produjo un resultado con apariencia perfectamente razonable** y que solo se detectó al comprobarlo expresamente. El patrón común es el que da título al trabajo: **la plausibilidad agregada no garantiza la validez de la decisión**.

---

## 1. Defectos de fuente

| # | Fallo | Cómo se manifestaba | Consecuencia si no se detecta | Salvaguarda |
|---|---|---|---|---|
| 1 | **AVAMET codifica el dato ausente de temperatura como `0,0`** | De 6.918 valores fuera de rango, 6.914 son exactamente el cero. Tasa del 0,001 % al 5,5 % **según estación** | Sesgo espacialmente estructurado de hasta 1,2 °C — del mismo orden que la señal buscada, e **imitándola** | Control de calidad a nivel de observación, no de estación; cobertura contada sobre temperatura validada, no sobre filas |
| 2 | **Catastro: `value` parece altura y es superficie construida** | `officialAreaReference = grossFloorArea`, `value_uom = m2`. Daba mediana de **80 m** para València y descartaba el 89 % del parque | Sombras absurdas o parque residual | Leer la semántica INSPIRE antes que el nombre del campo; y `numberOfFloorsAboveGround` está vacío al 100 % en `building.gml`, hay que usar `buildingpart.gml` |
| 3 | **Espejo de Overpass con otro extracto geográfico** | `overpass.osm.ch` responde **200 con cero elementos** a cualquier consulta española: sirve solo Suiza | «València no tiene centros de salud», y el conjunto vacío se propaga | Consulta de control **antes** de cualquier otra: si el centro de València no tiene farmacias, abortar |
| 4 | **OSM: 20 de 56 «centros de primaria» no lo son** | Filtro por nombre; clínicas privadas y duplicados que casan con el patrón | Con **más** centros se obtiene **menos** población accesible (68,6 % → 74,4 % de 65+ al pasar a los 48 oficiales): el error era de distribución espacial, invisible en el recuento. **Y llegó a invertir el signo de una comparación entre representaciones meteorológicas**: con OSM, «la meteorología local sin sombra es peor que la regional» salía significativa en las cinco capacidades de la ventana de mañana; con los centros oficiales los cinco intervalos cruzan cero y en la tarde la diferencia se invierte y es significativa a favor de la local | Contrastar con el registro oficial y medir el efecto **sobre la decisión**, no sobre el recuento. Un error en la capa de destinos no es preprocesamiento: puede cambiar qué se concluye sobre otras capas |
| 5 | **Día y mes transpuestos en parte del archivo AVAMET** | `2023-10-01` almacenado como `2023-01-10`; el 39,8 % de las fechas son ambiguas | Observaciones desplazadas meses sin aviso | Reconstruir la marca de tiempo desde el campo original del payload (`D-006` del proyecto) |

---

## 2. Artefactos de método

| # | Fallo | Cómo se manifestaba | Consecuencia | Salvaguarda |
|---|---|---|---|---|
| 6 | **Descarte de estación por valores sueltos** | La primera regla tiraba una estación por dos ceros en medio millón de partes: quedaban 1 de 9 municipales | Panel inutilizable, y por la razón equivocada | Descartar solo por defecto **sistémico** (tasa enmascarada, inercia, rango diurno), nunca por observaciones aisladas |
| 7 | **Saturación por alcance** | El quintil «peor» lo llenaban íntegramente secciones inalcanzables, donde la temperatura no juega. Jaccard 1,000 y cero cambios | Se habría concluido que la representación térmica no cambia nada | Restringir la comparación a las secciones donde la variable en estudio puede actuar |
| 8 | **Corte en la mediana** | Maximiza la reclasificación por construcción: 36,3 % en la mediana frente a 4,8 % en el decil | Una cifra de efecto elegida, no medida | Reportar la curva completa del corte; fijar el punto principal con una regla externa |
| 9 | **Saturación solar** | Con presupuesto estricto solo el 23–39 % cumple; el resto queda a cero y el Jaccard vuelve a salir 1,000 | «La sombra elimina el efecto térmico» — falso | Indicador de cumplimiento y bandera de saturación **en la tabla de resultados**, no en una comprobación posterior |
| 10 | **Dominancia de restricción** | En capacidades pequeñas, dos representaciones seleccionan idénticamente porque el cupo lo llenan las que incumplen la restricción activa | Regret 0 % leído como equivalencia de información | Formalizado: si $N_{\text{fallo}} \geq kN$, la segunda condición es **no identificable para la decisión**. Se declara el régimen por cada $k$ |
| 11 | **Signo de la corrección invertido** | Se describió un sesgo cálido de +1,85 °C como «sesgo frío de −1,85 °C», por leer como sesgo la corrección a aplicar | **Invierte la dirección del error de política**: sobreestimar pasa a subestimar | Nombres inequívocos (`raw_error_era5_minus_obs`, `additive_correction_obs_minus_era5`) y aserción que falla si dejan de cumplir su definición |
| 12 | **Emparejamiento espacial entre inventarios** | Cruzar altura de OSM con plantas de Catastro daba 3,5 m/planta y un sesgo **imposible** de −8,9 m en edificios de 1–3 plantas | Calibración contaminada | Preferir la validación **intrafuente** (los 107 edificios de OSM con altura y plantas a la vez dieron exactamente 3,00 m) |
| 13 | **Capa de sombra incompleta** | Sin arbolado, la exposición solar quedaba sobreestimada (5,19 min frente a 2,41), la restricción apretaba de más y absorbía la señal térmica | «La sombra reduce a la mitad el efecto térmico» — artefacto | Acotar por los dos extremos (sin vegetación / copa opaca) y barrer la transmitancia |
| 14 | **Referencia tomada por verdad** | Llamar *ground truth* a la representación de mayor información | Presenta como error del resto lo que en parte es error propio | Nombrarla **referencia de mayor información disponible** y enumerar sus incertidumbres |
| 15 | **Cifras anteriores a una reejecución sobreviviendo en el texto** | Al converger la frontera de Pareto se rehizo toda la cadena, pero cuatro magnitudes quedaron en su valor viejo: eficiencia **96,0–100,0 %** por 94,6–99,8, Jaccard estacional **0,796–1,000** por 0,814–0,978, reclasificados 5322 por 5119, exposición sombreada 1,23 min por 1,07 | Un resumen y un apartado de resultados afirmando cifras **distintas del mismo experimento**; y las dos versiones viejas tocaban justo los topes que la propia tabla marca como sospechosos (100,0 y 1,000) | `analisis/verificar_cifras.py`: cada magnitud publicada se recalcula desde su CSV de origen y se busca literalmente en el `.tex`. Leer el texto no basta — una cifra obsoleta es plausible por construcción, porque **fue** correcta |

---

## 3. Lo que tienen en común

En trece de los quince casos, el resultado erróneo era **más limpio** que el correcto: un Jaccard de 1,000, un efecto del 36 %, una mediana de altura redonda, un conjunto vacío bien formado. La señal de alarma no fue nunca una excepción o un valor imposible a la vista, sino la **falta de una razón mecánica** para el resultado observado.

De ahí las tres reglas que se acabaron adoptando:

1. **Toda métrica de estabilidad va acompañada del denominador y del indicador de saturación**, en la misma tabla.
2. **Ningún corte, umbral ni peso se elige por el resultado**: o tiene anclaje externo, o se reporta la curva completa.
3. **Antes de creer un resultado limpio, comprobar que la variable en estudio podía haberlo producido.**
