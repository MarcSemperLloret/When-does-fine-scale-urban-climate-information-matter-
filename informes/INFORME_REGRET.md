# Regla de exposición anclada y regret presupuestario

**Fecha:** 7 de agosto de 2026 · **cifras definitivas con centros oficiales de la GVA**

> **Reejecutado sobre la capa oficial de destinos** (48 centros, 442 secciones alcanzables). Las
> cifras anteriores, calculadas con los 56 centros de OSM y 405 secciones, quedan archivadas en
> `salidas/tablas_osm_sensibilidad/` como análisis de sensibilidad de la capa de destinos.
> **Una conclusión se retiró en el proceso**: ver §2.2.

---

## 1. El último parámetro de conveniencia, resuelto

El presupuesto en **minutos absolutos** era el último número elegido porque funcionaba, y además no era comparable entre trayectos: ocho minutos al sol no significan lo mismo en un recorrido de nueve minutos que en uno de quince.

La búsqueda de anclaje externo da dos referencias utilizables, y ninguna en minutos:

- **Tomasi et al. (2023)**, *Int J Biometeorol* 68(1):17–31, definen el umbral máximo de exposición a radiación solar directa para peatones por **balance energético** y lo expresan como **porcentaje máximo de exposición del trayecto**, no como duración. Sitúan el presupuesto de una persona mayor en **0,5 met frente a 2,1 met** de un adulto joven —del orden de un tercio—, lo que justifica trabajar en el extremo estricto del rango para 65+.
- Los trabajos de diseño de sombreado de itinerarios peatonales usan como objetivo de desempeño **el 60 % del recorrido en sombra**, es decir **φ ≤ 0,40** de fracción expuesta.

Se adopta por tanto la **fracción expuesta del recorrido** como restricción, que es adimensional y comparable, con **φ = 0,40 como valor anclado**. Y se reporta la curva completa, porque ninguno de los dos anclajes es normativo en sentido estricto.

### La curva en φ (umbral 30 °C, capa completa de sombra)

| φ máx | Cumplen | Jaccard | Pob. 65+ reclasificada | |
|---:|---:|---:|---:|---|
| 0,10 | 38–46 % | 1,000 | 0 | saturada |
| 0,20 | 46–71 % | 1,000 | 0 | |
| 0,30 | 69–87 % | 0,742–0,761 | 4.653–4.996 | |
| **0,40** | **86–96 %** | **0,573–0,742** | **4.996–8.140** | **anclada** |
| 0,50 | 94–98 % | 0,543–0,620 | 7.135–8.584 | |
| 0,70 | 98–100 % | 0,486–0,514 | 9.268–10.130 | |
| 1,00 (sin filtro) | ~100 % | 0,486–0,500 | 9.586–9.897 | |

La fracción expuesta mediana observada va de 0,126 a 0,473 según ventana y capa, de modo que φ = 0,40 es una restricción que muerde sin llegar a saturar.

**La respuesta a la pregunta de para qué políticas la decisión depende de la representación térmica**: para las que fijan φ ≥ 0,30. Por debajo, la restricción solar es tan exigente que decide sola.

---

## 2. Regret presupuestario

Un ayuntamiento puede intervenir en el *k* por ciento de las secciones. Cada representación selecciona unas; el beneficio de cualquier selección se evalúa **siempre con la representación completa**, que hace de verdad de campo:

$$R(k) = B\bigl(S_{\text{completa}}(k)\bigr) - B\bigl(S_{\text{repr}}(k)\bigr)$$

con $B(S) = \sum_{i \in S} \text{pob}_{65+,i} \times (1 - \text{frac servida}_i)$, la carga vulnerable capturada.

### Regret relativo (%), φ = 0,40, umbral 30 °C

| Representación | k=5 % | k=10 % | k=15 % | k=20 % | k=25 % |
|---|---:|---:|---:|---:|---:|
| **Mañana** | | | | | |
| R1 ERA5, sin sombra | 62,8 | 62,4 | 58,5 | 51,8 | 44,6 |
| R2 ERA5 + sombra completa | **0,0** | **0,0** | 0,7 | 1,5 | 1,9 |
| R3 local, sin sombra | 77,4 | 71,7 | 67,2 | 55,3 | 47,0 |
| R4 local + sombra de edificios | 63,6 | 60,8 | 53,5 | 45,1 | 34,1 |
| R5 local + sombra completa | 0 | 0 | 0 | 0 | 0 |
| **Tarde** | | | | | |
| R1 ERA5, sin sombra | 49,9 | 29,8 | 25,9 | 24,9 | 17,7 |
| R2 ERA5 + sombra completa | 2,0 | 3,5 | 5,5 | 6,9 | 6,3 |
| R3 local, sin sombra | 44,9 | 32,5 | 23,8 | 18,1 | 16,2 |
| R4 local + sombra de edificios | 46,3 | 35,2 | 26,9 | 23,5 | 21,2 |

### 2.1. Mejor comunicado como eficiencia

Regret y eficiencia son la misma cifra, pero la segunda se entiende sola. **Porcentaje del beneficio de priorización alcanzable que retiene cada representación** (mediana de 400 remuestreos de días, centros oficiales):

| Representación | k=5 % | k=10 % | k=15 % | k=20 % | k=25 % |
|---|---:|---:|---:|---:|---:|
| **Mañana** | | | | | |
| ERA5 + sombra completa | 100,0 | 100,0 | **100,0** | 99,6 | 99,1 |
| local + sombra de edificios | 34,2 | 44,5 | 49,0 | 58,6 | 67,7 |
| local, sin sombra | 31,6 | 35,8 | **38,5** | 45,0 | 53,8 |
| ERA5, sin sombra | 30,1 | 37,3 | 39,8 | 47,1 | 55,6 |
| **Tarde** | | | | | |
| ERA5 + sombra completa | 100,0 | 97,8 | **96,0** | 95,2 | 95,0 |
| local, sin sombra | 56,2 | 69,5 | **79,7** | 83,6 | 86,9 |
| local + sombra de edificios | 51,6 | 65,4 | 77,8 | 77,5 | 78,8 |
| ERA5, sin sombra | 49,6 | 61,8 | 69,2 | 75,0 | 80,6 |

En una frase:

> **Con capacidad para priorizar el 15 % de las secciones, ERA5-Land corregido con la sombra completa retiene el 96,0–100,0 % del beneficio alcanzable. Cualquier representación sin capa de sombra retiene el 38,5–79,7 %.**

### 2.2. Retirada: «la meteorología local sin sombra es peor que la regional»

Con la capa de OSM, la diferencia emparejada R3 − R1 salía **positiva y significativa en las cinco capacidades de la ventana de mañana** (+3,6 a +9,8 pp), y se concluyó que mejorar solo la meteorología podía ser contraproducente. **Con los centros oficiales esa conclusión no se sostiene:**

| Ventana | k=5 | k=10 | k=15 | k=20 | k=25 |
|---|---:|---:|---:|---:|---:|
| Mañana | −0,6 | +2,2 | +1,0 | +2,2 | +1,7 |
| IC 95 % | [−8,2; 4,9] | [−2,3; 5,0] | [−4,3; 5,2] | [−0,5; 4,4] | [−0,5; 5,3] |
| **Tarde** | **−7,6** | **−7,5** | **−10,6** | **−8,9** | **−6,2** |
| IC 95 % | [−12,3; −2,2] | [−10,9; −5,7] | [−13,6; −7,6] | [−12,6; −5,4] | [−9,3; −3,5] |

En la mañana **los cinco intervalos cruzan cero**: no hay diferencia. En la tarde la diferencia es **negativa y significativa en las cinco**, es decir, la meteorología local sin sombra es **mejor** que la regional sin sombra, entre 6,2 y 10,6 puntos.

**El hallazgo anterior era un artefacto de la capa de destinos de OSM**, cuyos errores espacialmente estructurados desplazaban el conjunto prioritario de la mañana. Queda retirado, y la afirmación defendible pasa a ser la contraria y más intuitiva: *sin capa de sombra, mejorar la meteorología aporta poco, y lo poco que aporta es positivo*.

Es el mejor argumento posible a favor de haber rehecho todo con la capa oficial: no era higiene, cambiaba una conclusión.

---

## 3. Dominancia de restricción

En capacidades pequeñas, R2 y R5 seleccionan **exactamente las mismas secciones** (eficiencia 100,0 %, solapamiento 40/40). No es que ERA5-Land iguale al campo local: es que el cupo lo llenan íntegramente las secciones que **incumplen la condición solar**, y esa condición es idéntica en ambas.

Es la cuarta aparición del mismo modo de fallo en este estudio —saturación por alcance, corte en la mediana, saturación solar y ahora esta—, y a estas alturas conviene dejar de tratarla como incidencia y darle nombre, porque **no es un defecto del análisis sino una propiedad de la regla de política**:

> **Dominancia de restricción.** Cuando el número de secciones que incumplen la restricción activa iguala o supera el cupo, $N_{	ext{fallo}} \geq kN$, toda la capacidad de priorización se consume antes de que la segunda condición entre en juego, y esa segunda condición queda **no identificable para la decisión**.

Operativizado sobre este caso:

| Ventana | k=5 | k=10 | k=15 | k=20 | k=25 |
|---|---|---|---|---|---|
| Mañana (73 incumplen de 442) | dominada por sol (3,32) | dominada por sol (1,66) | dominada por sol (1,11) | mixta (0,83) | mixta (0,66) |
| Tarde (22 incumplen) | dominada por sol (1,00) | mixta (0,50) | sensible a térmica (0,33) | sensible a térmica (0,25) | sensible a térmica (0,20) |

Los puntos de transición **se desplazan** respecto a la versión con OSM —la mañana sigue dominada por el sol hasta k=15 en vez de hasta k=10— lo que confirma que la tabla de regímenes es específica de la capa de destinos y hay que recalcularla con ella. El concepto se mantiene intacto.

*(entre paréntesis, el cociente $N_{	ext{fallo}}/kN$)*

Y en efecto, el regret de R2 solo empieza a informar donde el régimen deja de estar dominado por el sol, y ahí crece de forma monótona: 0,7 → 1,4 → 2,0 % en mañana. **Esa monotonía es la evidencia de que el efecto térmico existe, es pequeño frente al de la sombra, y aparece justo cuando la restricción solar deja de mandar.**

La distinción vale más allá de este caso: permite decir de cualquier regla de política qué restricción está activa a cada capacidad, y por tanto qué capa de información puede llegar a cambiar algo.

---

## 4. Cómo encaja con el factorial

El factorial y el regret responden preguntas distintas y ambos resultados son ciertos:

| | Pregunta | Respuesta |
|---|---|---|
| **Factorial** | Con el mismo tratamiento de sombra, ¿la representación térmica cambia quién se prioriza? | Sí: 5.500–10.200 personas de 65+ |
| **Regret** | ¿Qué capa de información, si se omite, cuesta más carga vulnerable? | La sombra, con diferencia |

Omitir la sombra es catastrófico para la selección; incluida la sombra, la representación térmica todavía reordena bastantes secciones, pero esas permutaciones cuestan poca carga vulnerable.

Esto es exactamente la formulación general del artículo: **la importancia de cada capa de información depende de la restricción de política bajo la que se toma la decisión**.

---

## 5. Limitaciones

1. **El anclaje de φ = 0,40 es un objetivo de diseño, no una norma.** Por eso se reporta la curva completa. Y el propio Tomasi et al. sugiere que para 65+ el valor debería ser más estricto que para población general, lo que llevaría hacia φ = 0,30 — donde el resultado empieza a saturar.
2. **La carga vulnerable se define con la representación completa**, que es la única forma de calcular un regret, pero implica aceptar que esa representación es la verdad. Sus propios errores —τ, altura, campo térmico de seis estaciones— no entran en el cálculo.
3. **Selección voraz por sección**, sin restricción de contigüidad ni coste de intervención. Un plan real no elige secciones sueltas.
4. Sigue siendo **exposición solar geométrica**, no confort térmico.

---

## 6. Reproducción

```bash
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p4c_regret.py
```

Tablas: `p4c_curva_phi.csv`, `p4c_regret.csv`.

**Fuentes del anclaje:** Tomasi et al. (2023), *Definition of a maximum threshold of direct solar radiation exposure for pedestrians of diverse walking abilities*, Int J Biometeorol 68(1):17–31; y la literatura de diseño de sombreado de itinerarios peatonales que fija el 60 % del recorrido en sombra como objetivo.
