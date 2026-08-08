# Informe de viabilidad — exposición térmica y accesibilidad de personas mayores en València

**Fecha:** 6 de agosto de 2026
**Plan ejecutado:** `plan_viabilidad_articulo_valencia.md`
**Alcance de esta ejecución:** Bloque A completo (Puertas 0 y 1). Bloques B, C y D no ejecutados; al final se detalla qué necesita cada uno.

---

## 0. Veredicto

**Continuar**, pero con la señal separada por escala espacial y por ventana horaria, porque no son el mismo fenómeno.

Hay heterogeneidad térmica, es estable entre veranos y es físicamente interpretable. Pero **el mecanismo depende de la escala a la que se mire**, y la primera versión de este informe los había mezclado:

| Escala | Dispersión nocturna | Dispersión diurna (10–18 h) |
|---|---:|---:|
| Barrios de València (6 estaciones) | **0,50 °C** | **0,98 °C** |
| Municipio completo, con l'Albufera (7) | 0,78 °C | 1,41 °C |
| Área metropolitana (16) | 1,95 °C | 1,75 °C |

Entre barrios de València, **la señal diurna dobla a la nocturna**. La relación se invierte al ampliar a la corona metropolitana, donde el contraste ciudad-huerta domina de noche.

De esto se siguen dos cosas.

1. **El artículo de accesibilidad se apoya en la señal diurna, no en la nocturna.** El contraste intramunicipal diurno útil es de **0,98 °C de dispersión P90−P10 y 1,35 °C de rango entre barrios** (P90 de las horas: 2,17 °C). Es una señal real y todas sus anomalías son significativas, pero está justo en la banda de 1–1,5 °C a partir de la cual habría que exigirle que mueva una decisión concreta. No es un cheque en blanco.
2. **Un mapa único de «barrios calientes» sería incorrecto.** Entre las seis estaciones intramunicipales, la correlación de Spearman entre el ranking nocturno y el diurno es **−0,66**: el orden térmico se invierte. Penya-roja es la más cálida de noche y la quinta de seis por el día; el Col·legi Diocesà es la primera por el día y la quinta de noche.

Esta ejecución **no demuestra** que la accesibilidad cambie. Demuestra que existe una señal diurna intramunicipal de amplitud suficiente para que merezca la pena probarlo.

### Corrección respecto a la primera versión de este informe

La versión del 6 de agosto encabezaba con el contraste **34,0 % frente a 5,1 %** de noches tórridas entre Penya-roja y Almàssera, presentándolo como el resultado central para accesibilidad. **Es un gradiente entre municipios**, no heterogeneidad entre barrios de València: Almàssera es otro término municipal y un entorno abierto de huerta. Las cifras equivalentes dentro del municipio son mucho más modestas:

| Contraste de noches tórridas | Máximo | Mínimo |
|---|---:|---:|
| Entre barrios de València (6) | 37,2 % | 29,1 % |
| Municipio completo, con l'Albufera (7) | 37,2 % | 15,1 % |
| Área metropolitana (16) | 47,7 % | 5,8 % |

Ocho puntos porcentuales entre barrios, no veintinueve. El resultado metropolitano sigue siendo válido y sigue siendo fuerte; lo que no es válido es llamarlo intraurbano.

---

## 1. Restricción de diseño que se ha respetado

**El verano de 2024 no se ha mirado.** El archivo AVAMET del proyecto está partido en un split `development` y un split `locked` que contiene el año 2024 completo, reservado como única muestra confirmatoria limpia del proyecto de reventones. Leerlo aquí lo habría destruido para aquel uso.

Los seis veranos utilizados son **2019, 2020, 2021, 2022, 2023 y 2025**. No supone pérdida material: quedan seis veranos y 12 793 horas de panel válido.

---

## 2. Puerta 0 — Viabilidad de los datos

### 2.1. Qué hay

De las 57 estaciones AVAMET con datos estivales dentro de 30 km del centro de València:

| Ámbito | Evaluadas | Utilizables |
|---|---:|---:|
| Municipio de València | 9 | **7** |
| Área metropolitana (< 12 km) | 14 | **9** |
| Periurbano (12–30 km) | 34 | **25** |
| **Total** | **57** | **41** |

El plan preveía «aproximadamente 13 estaciones en el municipio». El inventario oficial de AVAMET tiene 14 con código `c15m250`, pero **solo 9 están en el archivo local**: las otras cinco no se descargaron en su día. Recuperarlas es el aumento de muestra más barato que tiene este estudio, aunque conviene ver cuánto añade cada una:

| Ausente del archivo | Distancia a la estación útil más próxima |
|---|---:|
| el Saler – Platja de la Garrofera | 2,46 km |
| Sant Isidre | 2,00 km |
| Jesús | 1,55 km |
| el Pla del Real | 1,44 km |
| Col·legi San Pedro Pascual | 0,45 km |

Las tres primeras densifican el cuadrante suroeste y el cordón litoral, que hoy dependen de una sola estación cada uno. San Pedro Pascual está prácticamente colocalizada con Altocúmulo y aporta poco espacialmente, aunque serviría como par de validación entre instrumentos.

Aparte, Benimaclet y Pureza de María-Grau **sí están** en el archivo pero arrancan en 2025 y no llegan a dos veranos útiles; entrarán solas con el paso del tiempo.

### 2.2. Criterios de la Puerta 0

| Criterio del plan | Umbral | Resultado | |
|---|---|---|---|
| Estaciones útiles | ≥ 8 | 16 urbanas (7 municipales) | ✅ |
| Veranos comunes | ≥ 2 | 6 | ✅ |
| Cobertura estival | > 80 % | 7 estaciones municipales con ≥ 4 veranos al 80 % | ✅ |
| Tipologías urbanas distintas | ≥ 4 | centro histórico, ensanche, litoral/puerto, humedal, huerta norte, corredor oeste | ✅ |
| Sin dependencia de una única estación | — | verificado en la Puerta 1 (§3.5) | ✅ |

**Decisión: continuar**, sin cautelas.

### 2.3. Un defecto de datos que había que encontrar antes de nada

19 estaciones codifican el dato de temperatura ausente como **`0,0`**. De 6 918 valores fuera de rango, 6 914 son exactamente el cero.

Esto importa más de lo que parece. Un 0,0 °C en un verano valenciano no es una medida, pero es un número válido: entra en cualquier media sin avisar y la arrastra hacia abajo en proporción a lo averiada que esté cada estación. En la peor (Puçol - Alfinach, 5,5 % de centinelas) el sesgo sobre la media estival ronda 1,2 °C — **del mismo orden que toda la señal de isla de calor que este estudio busca medir**. Y como la tasa varía por estación, el sesgo es espacialmente estructurado: imita exactamente lo que se quiere detectar.

La primera versión del filtro descartaba la estación entera al encontrar cualquier valor imposible, y tiraba siete de las nueve del municipio por tener dos ceros en medio millón de partes. Corregido: se enmascara a nivel de observación y la estación solo cae si la fracción enmascarada supera el 5 %. Queda registrado como `D-018` en `docs/HALLAZGOS_DATOS.md`.

---

## 3. Puerta 1 — Señal térmica intraurbana

Método: anomalía de cada estación frente a la **mediana de la propia red en cada hora**, lo que elimina la evolución meteorológica regional y deja la estructura espacial relativa. Dos paneles, porque la red crece con el tiempo y mezclarlos confundiría un cambio de señal con un cambio de muestra:

- **panel largo** — 7 estaciones con ≥ 5 veranos útiles, 2019–2023 y 2025.
- **panel denso** — las 16 urbanas, 2023 y 2025.

### 3.1. Dispersión intraurbana

| Métrica (panel largo) | Valor |
|---|---:|
| Dispersión nocturna P90−P10, mediana | **2,17 °C** |
| Dispersión nocturna, P90 de las horas | 3,54 °C |
| Dispersión nocturna P75−P25, mediana | 1,34 °C |
| Dispersión diurna P90−P10, mediana | 1,38 °C |
| Máximo del ciclo horario (05–06 h local) | 2,58 °C |
| Mínimo del ciclo horario (20–21 h local) | 0,89 °C |

El listón del plan era **1 °C de dispersión nocturna típica**. Se dobla. Y se dobla también con el rango intercuartílico, que es la medida honesta cuando el panel es de siete estaciones (con n = 7, P90 y P10 caen prácticamente sobre el máximo y el mínimo).

### 3.2. Anomalías por estación

Panel largo, ventana nocturna 00–06 h local, intervalos bootstrap por bloques de día (1 000 réplicas):

| Estación | ΔT noche (°C) | IC 95 % | ΔT tarde (°C) |
|---|---:|---|---:|
| València – Penya-roja | **+0,60** | [0,56 ; 0,64] | −0,06 |
| València – Micalet | **+0,57** | [0,54 ; 0,61] | +0,47 |
| València – Camins al Grau | +0,38 | [0,35 ; 0,42] | −0,49 |
| València – Col·legi Diocesà | +0,07 | [0,05 ; 0,09] | +0,83 |
| València – l'Albufera | −0,42 | [−0,46 ; −0,38] | −0,99 |
| Albalat dels Sorells | −1,11 | [−1,16 ; −1,05] | −0,08 |
| Almàssera | **−1,95** | [−2,02 ; −1,89] | +0,65 |

**Las siete son significativas**, y el rango completo es de 2,55 °C. Frente a una referencia periurbana externa (estaciones a 12–30 km con ≥ 5 veranos), la isla de calor nocturna del núcleo urbano alcanza **+2,63 °C**.

### 3.3. Dos mecanismos, no uno

Esto es lo que hace el resultado publicable y no meramente correcto. Las anomalías nocturnas y las de tarde **tienen geometrías distintas**:

| Correlación de Spearman | ΔT noche | ΔT tarde |
|---|---:|---:|
| Distancia al centro | **−0,61** (denso: −0,75) | −0,57 (denso: +0,13) |
| Distancia al mar | −0,21 | **+0,68** (denso: +0,72) |
| Altitud | +0,04 | **+0,86** (denso: +0,72) |

De noche manda la **isla de calor urbana**, alineada con la distancia al centro. De tarde manda el **gradiente de brisa marina**, alineado con la distancia a la costa y la altitud. Almàssera lo muestra en una sola fila: +0,65 °C de tarde y −1,95 °C de noche — la firma clásica de un emplazamiento abierto de huerta, con fuerte enfriamiento radiativo nocturno. No es un fallo de sensor; es física, y es la comprobación de interpretabilidad que el plan exigía.

Consecuencia de diseño para el artículo: **una sola covariable no va a servir**, y un modelo de la Puerta 3 que ignore la hora del día estará promediando dos mecanismos opuestos.

### 3.4. Estabilidad entre veranos

Correlación de Spearman entre los rankings de anomalía nocturna de cada par de veranos: **15 pares, todos entre 0,964 y 1,000**. El orden térmico de las estaciones es esencialmente el mismo en 2019 y en 2025. Esto es lo que el plan llamaba «rankings espaciales estables», y difícilmente podría salir mejor.

### 3.5. Controles de robustez

Advertencia sobre el alcance de estos controles, antes de enumerarlos: demuestran que la señal **no depende de una sola estación**, que es **estable en el tiempo** y que sus relaciones espaciales son **físicamente plausibles**. No demuestran que esté libre de sesgo instrumental. Un sesgo de emplazamiento —sensor junto a una pared, azotea con ventilación propia, altura distinta del abrigo, proximidad a una unidad de climatización, jardín frente a pavimento— puede ser perfectamente estable durante seis veranos y pasar los tres controles sin inmutarse. El hallazgo `D-018` (§2.3) es la prueba de que este archivo contiene peculiaridades capaces de producir sesgos espacialmente estructurados del mismo orden que la señal buscada. **Descartar el sesgo de emplazamiento exige una ficha documental de cada estación** —instalación, altura, abrigo, entorno inmediato, fotografía cuando exista— y esa ficha no está hecha.

- **Leave-one-station-out.** Excluyendo cada estación por turno, la dispersión nocturna P90−P10 va de 1,40 a 2,23 °C. El extremo bajo es Almàssera, el ancla fría: con siete estaciones, quitar el extremo mueve mucho un P90−P10. El rango intercuartílico, que no tiene ese problema, se mueve solo entre 0,67 y 1,50 °C, y en el panel denso entre 0,81 y 0,99 °C. **La señal no la sostiene ninguna estación individual**, y aun el peor caso queda por encima del listón de 1 °C.
- **Noches comunes.** Restringido a las 256 noches en que reportan las siete estaciones, el contraste de noches tórridas se mantiene: 34,0 % frente a 5,1 %.
- **Episodios cálidos.** La heterogeneidad **se intensifica** cuando más importa: 2,73 °C en los días del percentil 90 frente a 2,10 °C en días ordinarios (+30 %). En el panel denso, +44 %.
- **Régimen de viento.** La dispersión nocturna apenas depende del régimen (brisa 2,19 °C, poniente 2,08 °C, sur 1,87 °C). La señal **no** es un artefacto de poniente, lo que descarta uno de los escenarios de reformulación previstos.

### 3.6. Decisión de la Puerta 1

| Criterio del plan | Resultado |
|---|---|
| Dispersión nocturna ≥ 1 °C | 2,17 °C ✅ |
| Anomalías estables de 0,5–1 °C | 7 de 7 significativas, rango 2,55 °C ✅ |
| Diferencias materiales en noches tropicales/tórridas | 34,0 % vs 5,1 % ✅ |
| Rankings espaciales estables | Spearman ≥ 0,964 ✅ |
| Mayor heterogeneidad en episodios cálidos | +30 % ✅ |
| Coherencia con mar, densidad, vegetación | dos gradientes separados y coherentes ✅ |

Ninguno de los criterios de descarte se cumple: la señal no desaparece con el control de calidad, no es del orden del error instrumental (2,17 °C frente a ~0,2 °C) y no está dominada por una sola estación. El criterio «diferencias dominadas por problemas instrumentales» queda **pendiente**, no descartado, por lo dicho en §3.5.

Y una salvedad que la separación por escalas obliga a añadir: **estas cifras son metropolitanas**. Aplicado solo a los barrios de València, el criterio de dispersión nocturna ≥ 1 °C **no se cumple** (0,50 °C). Un artículo formulado como «isla de calor nocturna entre barrios de València» fracasaría en su propia Puerta 1. El que sí pasa es el diurno intramunicipal (0,98 °C, rango 1,35 °C) y el nocturno a escala metropolitana (1,95 °C).

**Decisión: continuar**, con la pregunta reformulada. Ya no es si existe señal, sino si el contraste diurno de ~1 °C entre barrios basta para mover una decisión de accesibilidad.

### 3.7. La escala intramunicipal, que es la del artículo de accesibilidad

Seis estaciones de tejido urbano de València (se excluye l'Albufera, que está en el término municipal pero es marjal a 13 km del centro). Anomalías frente a la mediana de esas seis, IC bootstrap por bloques de día:

| Estación | ΔT día 10–18 (°C) | IC 95 % | ΔT mañana 10–12 | ΔT tarde 16–18 | ΔT noche 00–06 | Rango día → noche |
|---|---:|---|---:|---:|---:|---|
| Col·legi Diocesà San Juan Bosco | **+0,45** | [0,42 ; 0,48] | +0,53 | +0,36 | −0,16 | 1.º → 5.º |
| Altocúmulo | +0,18 | [0,16 ; 0,20] | +0,14 | +0,14 | −0,27 | 2.º → 6.º |
| Micalet | +0,08 | [0,07 ; 0,09] | +0,06 | +0,11 | +0,21 | 3.º → 2.º |
| l'Olivereta | −0,03 | [−0,05 ; −0,02] | −0,10 | +0,01 | −0,14 | 4.º → 4.º |
| Penya-roja | −0,40 | [−0,44 ; −0,36] | −0,33 | −0,33 | **+0,23** | 5.º → 1.º |
| Camins al Grau | **−0,78** | [−0,82 ; −0,74] | −0,46 | −0,91 | +0,05 | 6.º → 3.º |

Las seis anomalías diurnas son significativas. El rango diurno es de **1,23 °C** frente a **0,50 °C** en el nocturno, y las dos estaciones más marítimas —Penya-roja y Camins al Grau, a 2,3 y 2,0 km de la costa— son las más frescas por el día y las más cálidas de noche. Es la brisa marina invirtiendo el orden respecto a la isla de calor, ahora medida dentro de un solo municipio.

Consecuencia operativa para el piloto del paso 6: **el par de barrios contrastados por el día es Col·legi Diocesà (norte, interior) frente a Camins al Grau (este, litoral)**, con 1,23 °C de separación media diurna y 1,27 °C en la ventana de tarde. Ese par maximiza el contraste sin salir del municipio.

---

## 4. Matriz de decisión, con lo que ya se sabe

| Resultado | Estado tras el Bloque A |
|---|---|
| Señal térmica fuerte y cambia accesibilidad | **Vivo, con la carga en la señal diurna** (0,98 °C entre barrios), pendiente del piloto |
| Señal fuerte, accesibilidad cambia poco | **Vivo y reforzado** — el hallazgo de las dos geografías térmicas ya sostiene un artículo propio |
| Señal principalmente nocturna | **Cierto solo a escala metropolitana.** Entre barrios de València es al revés: diurna 0,98 °C frente a nocturna 0,50 °C |
| Producto regional falla y el modelo urbano generaliza | **Sin evaluar** — Puertas 2 y 3 |
| Temperatura importa poco y domina la sombra | **Abierto** — 1,35 °C de rango diurno intramunicipal es modesto; la sombra podría dominar |
| Diferencias por sensores dudosos | **No descartado**, solo acotado: falta la ficha de emplazamiento (§3.5) |
| Menos de 5–6 estaciones fiables | **Descartado** — 16 urbanas, 7 municipales, 6 de tejido urbano |

### Los dos artículos posibles, tras la separación por escalas

- **Escenario A — la accesibilidad se mueve.** *Scale-dependent urban heat exposure and age-sensitive accessibility in a Mediterranean city*. Aporta: dos mecanismos térmicos con geografías distintas según la hora, comparación entre representación regional y observacional, consecuencias sobre población mayor, e identificación de qué información hace falta para cada decisión. Destino: *Sustainable Cities and Society* o *CEUS*.
- **Escenario B — la accesibilidad se mueve poco.** No es un fracaso: el Bloque A ya contiene el núcleo de *Contrasting daytime and nighttime thermal geographies in a coastal Mediterranean metropolitan area*. La isla de calor gobierna la noche, la brisa marina reorganiza la tarde, **los rankings térmicos dependen de la hora** (ρ = −0,66 intramunicipal) y los episodios cálidos amplifican la heterogeneidad. Destino: *Urban Climate*, reforzado si se valida en 2024 y se conecta con morfología.

El resultado del ρ = −0,66 es lo bastante limpio como para ser la figura central del escenario B por sí solo.

---

## 5. Lo que no se ha ejecutado, y qué necesita

### Puerta 2 — Productos de rejilla

No bloqueada por capacidad: hay credenciales de CDS en el `.env` del repo. Bloqueada por volumen y por decisiones que no me corresponden.

- **ERA5-Land**: 6 veranos horarios sobre una caja pequeña. Descarga larga y en cola. Faltan `cdsapi` y `xarray` en el entorno (instalables, hay red).
- **CERRA**: atención — la serie publicada de CERRA **termina en 2021**, de modo que solaparía solo con los veranos 2019 y 2020 de este estudio. Hay que confirmar la ventana exacta en el catálogo del CDS antes de nada, porque si se confirma, el plan tiene un problema: trata CERRA como producto regional principal y quedaría reducido a dos veranos. O se acepta esa comparación corta, o el producto principal pasa a ser otro.
- A 9 km, ERA5-Land cubre el municipio con una o dos celdas. Es de esperar que la dispersión intraurbana reproducida sea **cero por construcción**, que es justamente el resultado que el artículo quiere cuantificar.

### Puerta 3 — Morfología urbana

Faltan `geopandas` y `shapely` (instalables), y las descargas de Catastro, PNOA-LiDAR y Urban Atlas.

Hay que decir un riesgo de diseño que el plan reconoce pero conviene cuantificar: con **16 estaciones urbanas y 12 covariables candidatas**, un random forest o un gradient boosting no va a generalizar, y el leave-one-station-out lo dirá. La ruta realista es un modelo lineal regularizado o un GAM con dos o tres covariables elegidas *a priori* — y §3.3 ya dice cuáles: distancia al centro para la noche, distancia al mar y altitud para la tarde. Recuperar las cinco estaciones municipales que faltan del archivo mejoraría esto más que cualquier elección de modelo.

### Puerta 4 — Accesibilidad piloto

Faltan `osmnx` y `geopandas`, la red peatonal de OSM, la población por sección censal del INE y los inventarios de servicios. Es el bloque más largo, y es el único que decide entre *Sustainable Cities and Society* y *Urban Climate*.

### Coste aproximado

| Bloque | Trabajo | Principal incertidumbre |
|---|---|---|
| B — rejillas | ~1 día, casi todo espera de cola CDS | ventana de CERRA |
| C — morfología | ~2–3 días | descarga de LiDAR; n = 16 |
| D — accesibilidad | ~4–5 días | completitud de los inventarios de servicios |

---

## 6. Orden de trabajo acordado

1. **Recuperar las cinco estaciones municipales ausentes** (prioridad: el Saler, Sant Isidre, Jesús, Pla del Real; San Pedro Pascual como par de control instrumental). Ver el coste en §6.1: no es gratis.
2. **Repetir el Bloque A completo** sin tocar métricas ni criterios.
3. **Documentar la exposición de cada estación** — instalación, altura, abrigo, entorno inmediato. Sin esto no se puede hablar de temperaturas de barrio (§3.5).
4. **Mantener 2024 cerrado** hasta congelar estaciones, filtros, ventanas horarias, definición de episodio, modelos, covariables, métricas primarias e hipótesis de accesibilidad.
5. **Puerta 2 reducida, solo ERA5-Land.** Cuatro escenarios: sin corregir, corrección global, corrección por entorno, observaciones AVAMET. Métricas: qué parte del ciclo reproduce, sesgo en máximas y mínimas, heterogeneidad espacial eliminada, cambio en el recuento de noches tórridas, cambio en población clasificada como expuesta. No se trata de «descubrir» que 9 km no resuelve barrios, que es cierto por construcción.
6. **Piloto mínimo de accesibilidad**: dos barrios intramunicipales de contraste diurno opuesto, un solo destino (centros de salud), dos ventanas (10–12 y 16–18), cuatro escenarios (distancia; velocidad adaptada; + pendiente; + temperatura observada). Pregunta: ¿la heterogeneidad observada de temperatura del aire cambia materialmente la accesibilidad estimada? Todavía no «cuál es la ruta térmicamente segura», que sin radiación ni sombra sería una afirmación excesiva.
7. **Solo si el piloto responde**, procesar Catastro, LiDAR, vegetación, pendiente, sombra horaria y sky-view factor.
8. **Abrir 2024** únicamente con el diseño completo congelado.

Criterio de continuidad del paso 6: ≥ 5 puntos porcentuales de cambio en cobertura, > 10 % de cambio relativo, cambios de categoría en secciones censales, alteración del ranking de barrios, o dependencia clara de la hora. Si un contraste diurno de ~1–1,35 °C no mueve nada, la temperatura del aire no sostiene la parte de accesibilidad.

Modelos de la Puerta 3, predefinidos **antes** de mirar correlaciones, y separados por mecanismo:

- **Nocturno:** distancia al centro, fracción edificada o sky-view factor, vegetación.
- **Diurno:** distancia al mar, altitud, sombra o vegetación, régimen de viento.

Regresión regularizada, GAM o modelo jerárquico sencillo. Ni random forest como modelo principal ni deep learning: hay muchas horas pero muy pocas unidades espaciales independientes.

### 6.1. El paso 1 no es gratis, y hay que decidirlo

El formulario de AVAMET admite consulta agrupada por comarca, y una petición sirve todas las estaciones de una comarca durante un día entero. Las cinco estaciones ausentes están en la comarca `c15`. Recuperarlas con la misma profundidad que el resto del panel —seis veranos completos— cuesta **6 × 92 = 552 peticiones**.

Eso choca con la condición explícita de la autorización de AVAMET: *volumen de consultas moderado*. Como referencia, la extracción del conjunto gold del proyecto anterior se consideró aceptable tras bajarla de 372 a **38** peticiones. 552 es un orden de magnitud por encima.

Tres salidas, y la elección es de Marc porque es su relación con AVAMET:

- **Reducir la ventana** a los dos o tres veranos que sostienen el panel denso (2023 y 2025: 184 peticiones), aceptando que las nuevas estaciones tengan menos histórico que las viejas.
- **Pedir a AVAMET una ampliación del volcado histórico** con las cinco estaciones, que es una petición única en vez de cientos de consultas.
- **Renunciar a las cinco** y trabajar con seis barrios, asumiendo que el panel intramunicipal se queda corto para la Puerta 3.

La segunda parece la correcta: es la que menos carga su servidor y la que da más datos.

---

## 7. Reproducción

```bash
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/extraer_subconjunto_valencia.py
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p0_inventario.py
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p1_senal_termica.py
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p1b_escalas.py
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p1_figuras.py
```

Tablas en `salidas/tablas/`, figuras en `salidas/figuras/` (7, en PNG y PDF), cubriendo los puntos 1–6 de las figuras mínimas del plan y 1–5 de las tablas mínimas. La figura 7 (descomposición por escala y ventana horaria) no estaba en el plan: la obligó la separación de escalas. El resto depende de los bloques no ejecutados.

El defecto de datos encontrado en la Puerta 0 queda registrado como `D-018` en `downbursts-cv-pilot/docs/HALLAZGOS_DATOS.md`, siguiendo la convención del proyecto.
