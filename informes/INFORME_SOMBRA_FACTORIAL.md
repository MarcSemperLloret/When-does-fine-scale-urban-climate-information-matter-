# Sombra de edificios y diseño factorial

> **Corregido por `INFORME_ARBOLADO.md`.** Este informe usa la capa de **solo edificios**, que es
> la cota inferior de sombra. Al añadir el arbolado del `MDSnV2,5`, la sombra deja de absorber el
> efecto de la representación térmica: la conclusión de que «lo reduce a la mitad» vale para la
> cota inferior, no para la sombra real. Léase junto con aquel informe.

**Fecha:** 7 de agosto de 2026
**Pregunta:** ¿la mejora que aporta la meteorología local sigue existiendo cuando la ruta ya conoce la sombra?

---

## 0. Respuesta

**La sombra domina, reduce a la mitad el efecto de la representación térmica, y no lo elimina.**

Sobre las 9 configuraciones no saturadas del factorial (umbral térmico × presupuesto solar):

| Magnitud | Sin sombra | Con sombra |
|---|---:|---:|
| Jaccard del 20 % prioritario, ERA5 vs AVAMET | 0,473–0,688 (mediana **0,500**) | 0,636–1,000 (mediana **0,800**) |
| Población 65+ reclasificada por la representación térmica | 5.512–10.258 | **0–6.975** (mediana 3.602) |
| Población 65+ reclasificada por **añadir sombra** | — | **6.261–18.146** (mediana 13.582) |

Cifras calculadas con **altura de edificación observada de LiDAR** (§1.0). Rehacer la cadena completa con altura observada en vez del supuesto de 3 m/planta mueve las medianas muy poco —Jaccard de 0,82 a 0,80, reclasificación por meteorología de 3.377 a 3.602, reclasificación por sombra de 14.622 a 13.582— de modo que **las conclusiones y ahora también las magnitudes están ancladas a altura medida**.

Es el escenario intermedio de los tres previstos: la diferencia se reduce pero no desaparece, lo que permite cuantificar la contribución de cada fuente en vez de tener que elegir entre ellas.

---

## 1. La capa de sombra

Catastro INSPIRE, municipio 46900. **Hay que usar `buildingpart.gml`, no `building.gml`**: en este municipio el segundo trae `numberOfFloorsAboveGround` vacío al 100 %, y su campo `value` es **superficie construida en m²** (`officialAreaReference = grossFloorArea`), no altura. Tomarlo por altura da una mediana de 80 m para València, que es absurda, y descarta el 89 % del parque por filtro de rango. Es el mismo patrón que `D-018`: un número perfectamente válido que entra sin avisar.

`buildingpart.gml` da **214.000 partes** con plantas informadas al 100 %, mediana 4 plantas y máximo 36. Además por parte y no por edificio, lo que conserva la variación de altura dentro de una manzana.

**Catastro no publica altura medida.** La altura es `3,0 m/planta + 1,0 m` de sobrealzado.

### 1.0. Altura observada de LiDAR: el supuesto era bueno para edificios altos y malo para bajos

Marc obtuvo del CNIG los nDSM normalizados **MDSnE2,5 de 2.ª cobertura** para las tres hojas MTN50 del área (0696, 0722, 0747): COG a 2,5 m en EPSG:25830 con altura de edificación sobre el terreno. Sustituyen el supuesto, y las secciones 1.1 y 1.2 quedan como registro de lo que se hizo mientras no estaban.

Estadística zonal del nDSM dentro de cada huella catastral. Se usa el **P75**, no la mediana: el borde de la huella no coincide con el borde real del edificio y una celda de borde mezcla tejado con calle, de modo que la mediana subestima. 94.132 de las 214.000 partes (44 %) tienen huella suficiente para una estadística utilizable —el resto son partes de menos de 25 m²—.

| Tramo | n | Plantas medias | H catastral | H LiDAR | Sesgo | MAE | Error rel. | **m/planta real** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1–3 | 44.665 | 1,5 | 5,5 m | 9,7 m | **−4,18 m** | 4,58 | 27,9 % | **4,13** |
| 4–6 | 21.769 | 5,2 | 16,6 m | 17,9 m | −1,34 m | 2,19 | 9,7 % | 3,23 |
| 7–10 | 24.371 | 8,2 | 25,6 m | 25,8 m | **−0,23 m** | 2,10 | 6,2 % | **2,99** |
| >10 | 3.327 | 13,3 | 40,9 m | 40,5 m | **+0,49 m** | 3,11 | 5,1 % | **2,93** |

**Para siete plantas o más el supuesto de 3,0 m era casi exacto** —sesgo de −0,2 a +0,5 m, metros por planta implícitos de 2,93 a 2,99—. Para una a tres plantas era malo: −4,18 m y 4,13 m por planta.

**No es contaminación de borde.** Se cruzó tramo de plantas con número de celdas: en el tramo de 1–3 plantas el sesgo se mantiene entre −2,5 y −5,6 m *independientemente del tamaño de la huella*, y el metro por planta implícito entre 3,85 y 5,26. Si fuese mezcla con la calle, el sesgo caería al crecer la huella, y no cae. Son plantas altas de verdad: naves, locales comerciales y edificación industrial.

**Consecuencia:** la capa de sombra anterior **subestimaba sistemáticamente la sombra de la edificación baja**, que es la que domina la periferia y las áreas industriales.

**Altura de trabajo definitiva:** P75 del nDSM donde hay estadística utilizable (44 % de las partes) y metros por planta **calibrados por tramo** —4,13 / 3,23 / 2,99 / 2,93— donde no. La altura mediana pasa de 13,0 a 14,2 m y la media de 14,1 a 15,7 m, un **factor 1,12**, que cae dentro del ±20 % explorado en §4.4.

### 1.1. Cómo se hizo mientras el LiDAR no estaba disponible

La validación correcta sería contra el modelo digital de **superficies** de PNOA-LiDAR. No se ha podido hacer:

- El WCS del IGN (`servicios.idee.es/wcs-inspire/mdt`) publica únicamente **Modelos Digitales del Terreno** —suelo desnudo, sin edificios— en 17 coberturas de 1000 a 5 m. Ninguna sirve para altura de edificación.
- `wms-lidar.idee.es` y `cog-pnoa.ign.es` no resuelven desde esta máquina.

**Pero el producto adecuado existe y está identificado.** El catálogo del CNIG publica `MDSE2` (Modelo Digital de Superficies **Edificación** MDSnE2,5, 2.ª cobertura) y `MDSV2` (el equivalente de **vegetación**): COG a 2,5 m normalizados a altura sobre el terreno, derivados de PNOA-LiDAR. Resuelven a la vez la altura de edificio y la de arbolado, y con la misma definición de altura, que es más limpio que combinar plantas catastrales con árboles estimados.

El obstáculo es la entrega: el Centro de Descargas usa una cesta con sesión y el POST de búsqueda devuelve siempre la página del buscador, sin URL directa por hoja. Las hojas MTN50 necesarias están identificadas —**0696 Burjassot, 0722 València y 0747 Sueca**, porque el área cruza tres bandas de 10′ de latitud— y la petición está redactada en `PETICION_CNIG_LIDAR.md`.

### 1.2. Contraste independiente con OpenStreetMap

Más débil que el LiDAR, pero **no circular** respecto a Catastro.

**Metros por planta.** La estimación fiable es la que no cruza fuentes: los **107 edificios de OSM que llevan a la vez `height` y `building:levels`**. Mediana **3,00 m/planta** (P25 3,00, P75 4,00), y por tramos 3,00 (1–3 plantas), 3,00 (4–6), 2,72 (7–10), 3,57 (>10). **El supuesto de 3,0 m queda respaldado.**

Un primer intento cruzando la altura de OSM con las plantas de Catastro daba 3,5 m y un sesgo de −8,9 m en edificios de 1–3 plantas, que es imposible: el punto de OSM caía sobre una parte baja del edificio equivocado. Esa vía está contaminada por el emparejamiento y **no se usa**.

**Recuento de plantas** (20.579 emparejamientos): MAE 1,14 plantas, **58,7 % idénticas, 84 % dentro de ±1**, Spearman 0,671. El sesgo aparente, en cambio, **cambia de signo según la regla de emparejamiento**: −0,98 plantas tomando la parte que contiene el punto, +0,96 tomando el máximo en 10 m, +1,76 en 20 m. No es identificable con este método, así que **no se aplica corrección**.

**Conclusión operativa:** la altura de un edificio típico lleva del orden de ±1 planta de incertidumbre, es decir **±3 m sobre una mediana de 13 m, un ±23 %**. De ahí el análisis de sensibilidad de ±20 % de la sección 4.4.

### Método y verificación

Método ráster estándar a 3 m de resolución: se rasteriza la altura y, para cada posición solar, se recorre el ráster hacia el sol comparando la altura encontrada con `n · paso · tan(elevación)`. Con 8.803 km de red y 214.000 partes, trazar rayos punto a punto no era viable.

**Verificación sintética**: edificio de 30 m, sol a 45°. Las cuatro direcciones cardinales salen correctas y la sombra mide 30 m, que es el valor exacto.

**Validación por contexto urbano** (15 de julio, ponderada por longitud de red):

| Zona | 12 h | 17 h | 18 h |
|---|---:|---:|---:|
| Ciutat Vella | 32,3 % | 52,1 % | 55,7 % |
| Eixample/Russafa | 23,2 % | 41,7 % | 58,7 % |
| Camins al Grau | 18,7 % | 38,4 % | 46,2 % |
| Benicalap | 13,6 % | 34,8 % | 49,0 % |
| Malva-rosa (playa) | 4,4 % | 10,0 % | 15,0 % |
| El Saler / Albufera | 0,7 % | **0,6 %** | 0,8 % |

El orden es el que predice la geometría urbana. El Saler al 0,6 % es pinada: **ahí la omisión del arbolado no es un matiz, es la limitación principal**.

---

## 2. Sombra y temperatura del aire aportan informacion en buena medida no redundante

En el entorno de las seis estaciones intramunicipales:

| | Rango |
|---|---:|
| Anomalía diurna de temperatura del aire | **1,23 °C** |
| Fracción sombreada a las 17 h | **35,2 puntos** |
| **Spearman entre ambas** | **0,058** |

Micalet tiene la mayor sombra (51,8 %) y anomalía térmica casi nula; el Col·legi Diocesà tiene el aire más cálido y **la menor sombra** (20,9 %).

**Cuidado con la palabra «ortogonales».** Con seis estaciones, un ρ de 0,058 demuestra que en esos seis emplazamientos no hay asociación monotónica apreciable, y nada más. La formulación defendible es: *la sombra de edificios y la anomalía local de temperatura del aire aportaron información espacial en buena medida no redundante en los puntos de medida*. La redundancia a escala de toda la ciudad no se puede afirmar hasta tener un campo morfológico y térmico mejor validado.

Para lo que sirve el dato es para el diseño: basta para que el término de interacción del factorial no sea colineal, que es la condición para que el factorial informe de algo.

---

## 3. Frontera tiempo–sombra, sin peso arbitrario

No se combina tiempo y sol en un coste con un parámetro `k` inventado. Se recorre una rejilla de pesos, se retiene la frontera de Pareto y la decisión se formula como problema restringido: **de entre las rutas que llegan en ≤ 15 min, la de menos minutos al sol**. El peso solo genera candidatos y no aparece en ningún resultado.

Medianas sobre las 405 secciones alcanzables:

| Hora | Ruta rápida | | Ruta sombreada | | Ahorro de sol | Coste de tiempo |
|---|---:|---:|---:|---:|---:|---:|
| | min | sol | min | sol | | |
| 10 | 9,48 | 5,32 | 11,35 | 3,46 | **35,0 %** | +19,7 % |
| 12 | 9,48 | 7,07 | 10,79 | 5,41 | 23,5 % | +13,8 % |
| 17 | 9,48 | 5,19 | 11,19 | 3,22 | **38,0 %** | +18,0 % |
| 18 | 9,48 | 4,22 | 11,19 | 2,61 | **38,2 %** | +18,0 % |

**Aceptar entre un 14 y un 20 % más de tiempo recorta la exposición solar entre un 24 y un 38 %.** El tramo continuo al sol más largo cae de 2,4–5,4 min a 1,3–2,9 min, aproximadamente la mitad.

Ése es el tipo de afirmación que se puede llevar a un pliego municipal sin haber elegido ninguna constante a conveniencia.

---

## 4. El factorial

|  | Sin sombra | Con sombra |
|---|---|---|
| ERA5-Land corregido | **A** | **C** |
| Campo AVAMET | **B** | **D** |

Las dos condiciones se combinan con un Y lógico, sin pesos entre grados y minutos de sol: térmica `T < umbral`, solar `minutos al sol ≤ presupuesto`. Ambos umbrales se barren (28/30/32 °C × 3/5/8 min).

### 4.1. Una saturación que había que ver antes de interpretar

Con presupuesto de 3 minutos solo el **23 % (mañana) y el 39 % (tarde)** de las secciones alcanzables cumple la condición solar. El resto queda a cero pase lo que pase con la temperatura, el 20 % peor lo llenan íntegramente las que fallan al sol, y **el Jaccard sale 1,000 sin que eso signifique nada**.

Es el tercer episodio del mismo modo de fallo en este estudio —ya ocurrió con la saturación por alcance y con el corte en la mediana— así que ahora la fracción que cumple la condición y una bandera `solar_saturada` van **en la propia tabla de resultados**, no en una comprobación posterior. Solo se interpretan las 9 configuraciones con ≥ 60 % de cumplimiento.

Conviene añadir que la saturación es continua, no binaria: cuanto más se aprieta el presupuesto solar, más absorbe el efecto térmico. Las dos configuraciones de tarde a 5 minutos (69 % de cumplimiento) todavía dan Jaccard 1,000, apenas por encima del corte.

### 4.2. Efectos sobre la cobertura

| Efecto | Rango (puntos porcentuales) |
|---|---|
| Meteorología local, sin sombra (B − A) | −0,93 a +3,48 |
| Meteorología local, con sombra (D − C) | −0,81 a +3,10 |
| **Añadir sombra (D − B)** | **−3,5 a −50,7** |
| Interacción (D − C) − (B − A) | −2,29 a +0,66 |

El efecto de la sombra sobre la cobertura agregada es **un orden de magnitud mayor** que el de la representación térmica. La interacción es pequeña: la sombra no cambia sustancialmente *cuánta* diferencia hace la meteorología local sobre el agregado.

### 4.3. Efectos sobre la priorización, que es lo que importa

Aquí sí hay interacción, y es la respuesta a la pregunta del bloque:

| Configuración (no saturada) | Jaccard sin sombra | Jaccard con sombra | Recl. sin sombra | Recl. con sombra |
|---|---:|---:|---:|---:|
| mañana, 28 °C, 8 min | 0,688 | 0,800 | 5.518 | 3.930 |
| mañana, 30 °C, 8 min | 0,473 | 0,820 | 10.258 | 3.602 |
| mañana, 32 °C, 8 min | 0,514 | 0,800 | 8.665 | 3.615 |
| tarde, 28 °C, 8 min | 0,688 | 0,800 | 5.512 | 3.571 |
| tarde, 30 °C, 8 min | 0,500 | 0,688 | 9.558 | 5.982 |
| tarde, 32 °C, 8 min | 0,473 | 0,636 | 9.811 | 6.975 |

**Cuando la ruta conoce la sombra, la elección entre ERA5-Land y el campo local reclasifica aproximadamente la mitad de personas mayores.** El efecto no desaparece —en 7 de las 9 configuraciones sigue reclasificando entre 2.700 y 5.700 personas— pero deja de ser el factor principal.

Y la sombra por sí sola reclasifica **7.372–17.538 personas**, más que la meteorología en cualquier configuración.

### 4.4. Sensibilidad al supuesto de altura

Toda la cadena —sombra, rutas, factorial— rehecha con la altura multiplicada por 0,8 y por 1,2, que es el ±23 % de incertidumbre que deja el contraste con OSM (§1.2). Umbral 30 °C, presupuesto 8 min:

| Factor | Ventana | Cumplen solar | Sol mediano | Jaccard C–D | Pob. 65+ reclasificada |
|---:|---|---:|---:|---:|---:|
| 0,8 | mañana | 77,0 % | 5,22 min | 1,000 | **0** |
| 1,0 | mañana | 83,2 % | 4,63 min | 0,862 | 2.676 |
| 1,2 | mañana | 86,2 % | 4,19 min | 0,742 | **4.996** |
| 0,8 | tarde | 84,0 % | 4,21 min | 0,841 | 3.263 |
| 1,0 | tarde | 88,9 % | 3,62 min | 0,742 | 4.903 |
| 1,2 | tarde | 92,8 % | 3,02 min | 0,670 | **6.243** |

Dos lecturas, y conviene no confundirlas.

**Lo que aguanta:** el orden de los efectos. En cinco de los seis casos la representación térmica sigue reclasificando miles de personas una vez incluida la sombra, y la sombra sigue siendo el factor mayor. El caso que da cero (mañana, ×0,8) es otra vez saturación: con edificios más bajos hay menos sombra, menos secciones pasan el filtro solar y el efecto térmico queda enmascarado.

**Lo que no aguanta: la magnitud.** La población reclasificada por la representación térmica va de 0 a 4.996 en la ventana de mañana y de 3.263 a 6.243 en la de tarde. Es aproximadamente **un factor de dos** por un supuesto de altura que no está calibrado.

De aquí salía la consecuencia de que **no se podían publicar magnitudes con la altura asumida**. **Resuelto**: el MDSnE2,5 llegó y la §1.0 sustituye el supuesto por altura observada. Este análisis de sensibilidad queda como lo que demuestra que el resultado no dependía de una constante afortunada — el factor real entre altura asumida y observada, 1,12, cae dentro del rango explorado aquí.

Advertencia sobre el alcance de este análisis: se ha recalculado la comparación C–D, no el efecto de la sombra frente a no tenerla, que también escalaría con la altura.

---

## 5. Qué significa para el artículo

El mensaje cambia de sitio, y a mejor. Ya no es un artículo sobre resolución meteorológica con la sombra como adorno; es un artículo sobre **qué información mínima hace falta para planificar accesibilidad térmica**, con un orden de prelación medido:

1. **La sombra es el primer factor.** Omitirla produce más inestabilidad decisional que usar una representación térmica regional.
2. **La representación térmica sigue importando después de la sombra**, a la mitad de magnitud. No es prescindible.
3. **No son redundantes entre sí** en los puntos medidos (ρ = 0,058, seis estaciones), así que de momento no se ve atajo: nada indica que uno pueda sustituir al otro.

Formulado para el resumen:

> Omitir la sombra desestabiliza la priorización más que usar temperatura regional; pero corregir la sombra no hace prescindible la observación local, porque las dos informaciones resultaron en buena medida no redundantes.

---

## 6. Limitaciones, en orden de gravedad

1. **Solo edificios, sin arbolado.** En El Saler la sombra modelizada es del 0,6 % y el suelo es pinada. En itinerarios peatonales arbolados de l'Eixample el sesgo va en la misma dirección. La contribución marginal del arbolado es el siguiente paso obligatorio, no opcional. Los nDSM de vegetación `MDSnV2,5` están disponibles para las hojas 0696 y 0722, **falta la 0747 (Sueca)**, que es precisamente la de El Saler y la Albufera.
2. ~~**Altura por supuesto.**~~ **Resuelta** con el MDSnE2,5 (§1.0): altura observada en el 44 % de las partes y metros por planta calibrados por tramo en el resto.
3. **Geometría solar de ruteo fija al 15 de julio.** La elevación a la misma hora varía unos 8° entre junio y agosto: suficiente para mover la exposición, poco para cambiar qué calle conviene. La sensibilidad no está medida.
4. **Sin cielo real.** Todo se calcula como si el cielo estuviera despejado. En verano valenciano es una aproximación razonable en las ventanas analizadas, pero es una aproximación.
5. **Condición solar binaria.** «Minutos al sol ≤ presupuesto» no es una relación dosis-respuesta. El barrido acota el problema; no lo resuelve.
6. **Sin temperatura radiante.** Esto sigue siendo exposición solar geométrica, no confort térmico. La afirmación defendible es *accesibilidad condicionada por exposición solar*, no *ruta térmicamente segura*.

---

## 7. Reproducción

```bash
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p3_descargar_edificios.py
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p3_sombra_edificios.py
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p3_rutas_sombra.py
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p3_factorial.py
```

Tablas: `p3_posiciones_solares.csv`, `p3_sombra_resumen.json`, `p3_rutas_frontera.csv`, `p3_factorial.csv`.
