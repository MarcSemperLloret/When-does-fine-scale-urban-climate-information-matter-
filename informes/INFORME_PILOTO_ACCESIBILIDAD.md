# Piloto de accesibilidad — ¿cambia la decisión la representación térmica?

**Fecha:** 6 de agosto de 2026
**Diseño:** prueba deliberadamente destructiva de la hipótesis, previa a cualquier descarga de LiDAR.

---

## 0. Resultado

**La hipótesis sobrevive, pero no por donde el plan esperaba.**

| Criterio de continuidad | Umbral | Resultado | |
|---|---|---|---|
| Cambio en cobertura agregada | ≥ 5 puntos | **0,18–1,14 puntos** | ✗ |
| Cambio relativo en cobertura | > 10 % | 0,05–3,98 % | ✗ |
| Secciones que cambian de categoría | «número material» | **43 de 81 prioritarias (53 %)** | ✓ |
| Alteración del ranking de barrios | — | **solapamiento 2/5–3/5 en el top-5 de distritos** | ✓ |
| Dependencia de la hora | — | tarde > mañana, pero moderada | parcial |

Dicho en una frase, que es además la frase del artículo:

> Una representación térmica espacialmente uniforme reproduce la exposición media de la población mayor con un error de un punto porcentual, y sin embargo identifica un conjunto distinto de barrios prioritarios: el 53 % de las secciones señaladas cambia, y con ellas unas **17.400 personas de 65 o más años, el 10 % del total municipal**.

Eso no es la conclusión de que «los datos gruesos pierden microclima», que es cierta por construcción y ya está publicada. Es la conclusión de que **la media se conserva y la prioridad no**, que es una afirmación sobre estabilidad de decisiones y no sobre resolución.

---

## 1. Diseño

Se ejecutó sobre **todo el municipio**, no sobre dos barrios. La razón es sencilla: el Jaccard de secciones clasificadas y el ranking de barrios no se pueden calcular con dos zonas. El coste computacional adicional era casi nulo una vez construida la red.

| Componente | Fuente | Cifra |
|---|---|---|
| Secciones censales | INE, seccionado 2024 | 591 |
| Población | INE ADRH 2023, por sección | 813.957 hab, **174.665 de 65+** |
| Red peatonal | OpenStreetMap | 65.887 nodos, 201.386 aristas |
| Centros de atención primaria | OpenStreetMap | 64 |
| Temperatura | AVAMET, 6 estaciones intramunicipales | 523 h (mañana) y 517 h (tarde) comunes |

Distancia de red al centro de salud más próximo: mediana **654 m**. Con velocidad estándar (1,25 m/s) el 93,2 % de la población de 65+ está a menos de 15 minutos; con velocidad adaptada (0,90 m/s), el **68,6 %**. Esa caída de 24 puntos por el solo hecho de caminar más despacio ya es un resultado, y no depende de la temperatura.

### Por qué el calor entra por el umbral y no por la velocidad

Conviene decirlo antes que nada porque decide todo lo demás.

- **Por velocidad de marcha, la temperatura no entra.** Con 1,2 °C de contraste intramunicipal y cualquier penalización plausible por grado, la diferencia de tiempo de recorrido es del orden del 1 %. No mueve ninguna decisión, y nunca la va a mover.
- **Por cruce de umbral sí entra, y mucho.** La distribución de temperatura es empinada cerca de los 30 °C, de modo que 1,2 °C de diferencia en la media separan un 22 % de horas por encima del umbral de un 9 %:

| Ventana | % de horas ≥ 30 °C | Col·legi Diocesà | Camins al Grau | Factor |
|---|---|---:|---:|---:|
| 10–12 h | | 22,0 % | 9,2 % | **2,4×** |
| 16–18 h | | 32,9 % | 11,8 % | **2,8×** |
| 16–18 h, ≥ 32 °C | | 7,7 % | 1,5 % | **5,1×** |

Ese es el mecanismo por el que una señal media modesta se vuelve decisional. Es un argumento de no linealidad, no de magnitud, y creo que es el argumento que diferencia este trabajo.

La variable de decisión no es entonces «se llega en quince minutos» sino **«durante qué fracción del verano se llega en quince minutos sin superar el umbral de calor»**, que es como se formula una política de acceso.

---

## 2. Cobertura agregada: la representación gruesa acierta

Población de 65+ que alcanza un centro de salud por debajo del umbral, ponderada por la fracción del verano en que ocurre:

| Ventana | Umbral | Uniforme | Uniforme + media diaria | Observada | Diferencia |
|---|---|---:|---:|---:|---:|
| 10–12 h | 30 °C | 57,74 % | 58,01 % | 58,30 % | +0,56 / +0,29 pp |
| 10–12 h | 32 °C | 65,88 % | 65,49 % | 65,91 % | +0,03 / +0,43 pp |
| 16–18 h | 30 °C | 50,31 % | 49,39 % | 51,35 % | +1,04 / +1,96 pp |
| 16–18 h | 32 °C | 65,32 % | 64,92 % | 65,70 % | +0,38 / +0,78 pp |

Ninguna combinación llega a un punto y medio.

**Corrección de la primera versión de este informe.** Allí se atribuyó esto a que «sustituir un campo por su mediana conserva el promedio». Es falso: la mediana no conserva la media. Lo que ocurre es una **cancelación entre dos flujos de signo contrario**:

$$\Delta C_{\text{neto}} = P(0\to1) - P(1\to0), \qquad C_{\text{bruto}} = P(0\to1) + P(1\to0)$$

y el neto puede ser casi nulo con un bruto grande. Ésa es la afirmación interesante, y es distinta de la que se hizo.

**Pero hay una limitación estructural para medirla aquí, y es seria.** Una representación espacialmente uniforme asigna a todas las secciones el mismo valor, de modo que las coloca a todas del mismo lado de cualquier corte. Los dos flujos **no pueden coexistir**: al descomponerla, sale 0 secciones en un sentido y 174–202 en el otro, en las cuatro combinaciones de ventana y umbral. La descomposición bidireccional no es computable contra un baseline uniforme; requiere un baseline que tenga variación espacial propia.

Eso convierte el uniforme sintético en lo que un revisor diría que es: un límite inferior de información, útil como control extremo y no como comparación. **La descomposición real queda pendiente de ERA5-Land**, que es el único baseline de esta serie con estructura espacial propia.

Lo que sí se sostiene sin baseline alguno: si lo que se quiere es una cifra de exposición media de la ciudad, una representación gruesa basta. Ese resultado replica lo ya publicado y delimita qué usos municipales no necesitan datos finos.

---

## 3. Priorización: la representación gruesa falla

Aquí hay que ser preciso sobre qué se compara con qué, porque hay una degeneración estructural que estuvo a punto de producir un resultado falso.

**Una representación espacialmente uniforme no puede ordenar barrios en absoluto.** Asigna a cada sección la misma temperatura, así que su ranking de prioridad es, exactamente, el ranking de la distancia. No tiene sentido calcular su Jaccard contra el observado como si fueran dos ordenaciones: una de ellas no existe. Por eso la comparación correcta es:

- **Regla vigente** — priorizar donde más personas mayores caminan más lejos. Es lo que hace hoy un planificador, y es también lo que haría con datos térmicos gruesos, porque estos no aportan nada al orden.
- **Regla térmica** — priorizar donde más personas mayores pasan más horas del verano por encima del umbral en su trayecto.

Entre las **405 secciones alcanzables**, comparando el 20 % prioritario de cada regla:

| Ventana | Umbral | Jaccard | Entran | Salen | Pob. 65+ reclasificada | ρ distritos | Top-5 distritos |
|---|---|---:|---:|---:|---:|---:|---|
| 10–12 h | 30 °C | 0,317 | 42 | 42 | 17.212 (9,9 %) | 0,690 | 2/5 |
| 10–12 h | 32 °C | 0,296 | 44 | 44 | 17.545 (10,1 %) | 0,699 | 2/5 |
| 16–18 h | 30 °C | 0,306 | 43 | 43 | 17.563 (10,1 %) | 0,721 | 3/5 |
| 16–18 h | 32 °C | 0,296 | 44 | 44 | 17.376 (10,0 %) | 0,478 | 2/5 |

Solo un tercio de las secciones prioritarias coincide. Dos de cada cinco distritos del top-5 son los mismos.

### Los tres denominadores, sin esconder ninguno

«43 de 81, el 53 %» es correcto pero mide una cosa concreta, y hay que dar las tres:

| Denominador | Cifra | Qué mide |
|---|---|---|
| 43 de 81 secciones prioritarias | **53 %** | inestabilidad condicionada: de las señaladas, cuántas dependen de la representación |
| 43 de 591 secciones del municipio | **7,3 %** | alcance territorial sobre toda la ciudad |
| 17.400 de 174.665 personas de 65+ | **10,0 %** | impacto poblacional |

La primera es la más llamativa y la más fácil de malinterpretar; la tercera es la que debe encabezar cualquier afirmación de política.

---

## 4. Sensibilidad

27 combinaciones de velocidad de marcha (0,80 / 0,90 / 1,00 m/s), presupuesto de caminata (10 / 15 / 20 min) y umbral de calor (28 / 30 / 32 °C):

| Métrica | Mínimo | Mediana | Máximo | Combinaciones que superan el listón |
|---|---:|---:|---:|---|
| Cambio en cobertura agregada (pp) | 0,18 | 0,58 | 1,14 | **0 de 27** superan 5 pp |
| Jaccard del top-20 % | 0,292 | 0,333 | 0,407 | — |
| Población 65+ reclasificada (%) | 3,72 | 9,95 | 13,35 | **24 de 27** superan el 5 % |

La conclusión es la misma en las 27: la cobertura agregada nunca se mueve, la priorización siempre sí. El caso menos favorable a la hipótesis (0,8 m/s, 10 min, 32 °C) deja solo 191 secciones alcanzables y aun así reclasifica al 3,7 % de la población mayor.

---

## 5. Limitaciones que hay que arreglar antes de enviar nada

Las digo sin adornos, porque varias son serias.

1. **Sin sombra ni radiación.** Todo el piloto usa temperatura del aire. Es la limitación mayor y es exactamente la que un revisor de *SCS* señalará después de leer el artículo de Phoenix, que sí usa temperatura radiante. Mientras no entre la sombra, la afirmación defendible es «la heterogeneidad de temperatura del aire cambia la priorización», no «esta es la ruta térmicamente segura».
2. **Seis estaciones para 591 secciones.** El campo térmico es una ponderación inversa de distancia desde seis puntos. Es pobre, y es justo lo que la Puerta 3 vendría a resolver. Que la señal sobreviva a un campo tan burdo es tranquilizador, pero no sustituye al modelo.
3. **Centros de salud de OpenStreetMap.** 64 equipamientos filtrados por nombre. La completitud de OSM en equipamiento sanitario no está garantizada y el portal municipal de datos abiertos no responde desde esta máquina. Contrastar con el listado oficial de la Conselleria de Sanitat es obligatorio antes de publicar.
4. **No hay 80+.** El ADRH del INE da población, porcentaje de 65+ y hogares unipersonales por sección, pero no llega a 80+. Hace falta el fichero de secciones del Censo 2021.
5. **Sin pendiente.** València es esencialmente llana (0–50 m en todo el término), así que el escenario de pendiente del plan no añade nada aquí. Conviene decirlo explícitamente en el artículo en vez de omitirlo: es una característica del caso, y limita la transferibilidad a ciudades con relieve.
6. **Umbral y dosis-respuesta estipulados.** Los 30 °C y el presupuesto de 15 minutos son convenciones razonables, no una relación dosis-respuesta medida. La sensibilidad de la §4 acota el problema pero no lo elimina.
7. **Verano de 2024 excluido**, por la reserva confirmatoria. Es una ventaja de diseño, no una carencia.

---

## 6. Qué significa para el artículo

El piloto autoriza a seguir, y sugiere que el marco correcto es el que ya estaba apuntado:

> **From thermal data resolution to policy stability: age-specific access to essential urban services under heat**

con el mensaje central de que **la media se conserva y la prioridad no**, y con el mecanismo de no linealidad de umbral como explicación de por qué una señal de 1 °C basta.

La diferencia frente al artículo de Phoenix de julio de 2026 queda nítida y hay que declararla en la introducción, no esconderla: ellos varían resolución espacial sobre rutas individuales con temperatura radiante simulada en un día despejado; aquí se varía **agregación espacial y temporal** sobre **cobertura territorial de servicios** con **temperatura del aire observada durante seis veranos**, y el resultado se mide en **estabilidad de la priorización**, no en desvíos frescos.

Lo que falta para que sea defendible en *SCS*, por orden:

1. **Sombra y radiación**, al menos una aproximación por sky-view factor. Sin esto el artículo es atacable.
2. **Población de 80+** desde el Censo 2021.
3. **Servicios oficiales** de la Conselleria, y ampliar a farmacias, centros de mayores y refugios climáticos.
4. **ERA5-Land real** en lugar del uniforme sintético, para que la representación gruesa sea una representación gruesa de verdad y no una construcción nuestra.
5. **Campo térmico de la Puerta 3**, que sustituya la ponderación inversa por un modelo con covariables.
6. **Validación en 2024** con el diseño ya congelado.

Y una advertencia sobre el orden: el punto 4 es el que más cambia el resultado. Nuestro escenario «uniforme» es el peor caso para los datos gruesos, porque no tiene ninguna variación espacial. ERA5-Land, con una o dos celdas sobre el municipio, se le parecerá mucho —pero conviene comprobarlo antes de afirmarlo.

---

## 7. Reproducción

```bash
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p4_descargar_datos.py
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p4_piloto_accesibilidad.py
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p4_figuras.py
```

Tablas en `salidas/tablas/p4_*.csv`, figura 8 en `salidas/figuras/`.

Nota sobre Overpass: `overpass-api.de` responde 406 desde esta máquina y `overpass.osm.ch` sirve **solo el extracto suizo**, de modo que devuelve 200 con cero elementos para cualquier consulta española. Es un fallo silencioso que parece «no hay centros de salud en València». Se usa `maps.mail.ru`.
