# Robustez final: bloques móviles y dominancia bajo el presupuesto

Dos sensibilidades pedidas antes de enviar, y una auditoría de cifras. Ninguna
cambia una conclusión; las tres cambian lo que se puede afirmar con qué margen.

---

## 1. Auditoría numérica del texto contra las tablas

`analisis/verificar_cifras.py`. Recalcula diecinueve magnitudes desde su CSV de
origen y las busca literalmente en el `.tex`.

Encontró **cuatro cifras anteriores a la reejecución** de la frontera convergida:

| Magnitud | En el texto | Real | Dónde |
|---|---|---|---|
| Eficiencia ERA5+sombra, k = 15 % | 96,0–100,0 % | **94,6–99,8 %** | §4.3 (el resumen ya estaba bien) |
| Jaccard estacional a 8 min | 0,796–1,000 | **0,814–0,978** | §4.2 |
| Reclasificados en τ plausible | 5322–10199 | **5119–10199** | §4.2 |
| Exposición de la ruta sombreada, 17 h | 1,23 min | **1,07 min** | §4.2 |

Las dos primeras tocaban exactamente los topes que la tabla de fallos marca como
sospechosos —100,0 y 1,000—. Es el caso 15 de esa tabla: **una cifra obsoleta es
plausible por construcción, porque fue correcta**. Leer el texto no la detecta.

El barrido está en el repositorio y debe volver a pasarse tras cualquier
reejecución. Ahora pasa con cero discrepancias.

---

## 2. Bootstrap por bloques móviles

`analisis/p4f_bootstrap_bloques.py`. Bloques de 3 y 7 días consecutivos,
muestreados **dentro de cada verano** —un bloque a caballo entre dos agostos
separados por un año no es continuidad temporal, es un artefacto del indexado—,
1000 remuestreos. L = 1 se incluye como control y reproduce el bootstrap
principal.

**Los intervalos se ensanchan y las estimaciones no se mueven.**

| | L = 1 | L = 3 | L = 7 |
|---|---|---|---|
| Amplitud del IC, factor sobre L = 1 | 1,00 | ~1,30 | **1,58** (máx. 1,66) |
| Desplazamiento de la eficiencia | — | — | mediana **0,16 pp**, máx. 1,38 pp |

Eficiencia a k = 15 % con bloques de 7 días:

| Representación | Mañana | Tarde |
|---|---|---|
| ERA5 corregido + sombra completa | 99,83 [99,71–99,93] | 94,28 [92,10–96,36] |
| meteorología local sin sombra | 37,92 [27,86–49,23] | 80,11 [68,53–87,67] |
| ERA5 corregido sin sombra | 38,24 [29,35–48,76] | 69,44 [56,95–79,43] |
| local + sombra de edificios | 45,32 [37,11–54,27] | 73,53 [67,02–78,63] |

La separación que sostiene el resultado central **no se toca**: el intervalo de
la representación con sombra completa no solapa con el de ninguna otra, ni en la
mañana ni en la tarde. Ninguna comparación de la Figura 5 cambia de signo.

Conclusión operativa: el bootstrap diario es **anticonservador** por un factor de
alrededor de 1,6 en amplitud, y así queda declarado en Métodos y en Limitaciones.
Los intervalos publicados son cota inferior de la incertidumbre total. No se
sustituye el principal porque la comparación no depende de ello y el esquema de
día completo es el que corresponde al diseño horario.

---

## 3. Régimen de dominancia bajo los nueve presupuestos

`analisis/p5b_dominancia_presupuesto.py`. Es la sensibilidad más directamente
ligada al cuarto claim, porque el presupuesto de marcha mueve **los dos** términos
de la frontera $N_\text{fallo} \geq kN$:

- ampliar el presupuesto alcanza más secciones → sube el cupo $kN$;
- pero también alcanza secciones peor conectadas y más expuestas → sube $N_\text{fallo}$.

Cuál gana no se razona de cabeza. **Gana el cupo**: ampliar el presupuesto
*libera* capacidad de decisión.

### Control

A 0,90 m/s y 15 min reproduce la tabla principal casi exactamente: 64 secciones
incumplen frente a 62, y 15 frente a 16 en la tarde —la diferencia es que p5b usa
solo el 15 de julio y la cadena principal promedia las fechas del parquet—. Los
diez regímenes coinciden uno a uno.

### Resultado

| | 10 min | 15 min | 20 min |
|---|---|---|---|
| Secciones alcanzables (0,8–1,0 m/s) | 201–290 | 367–493 | 522–561 |
| Mañana pasa a mixta en | k = 20–25 % | k = 15–20 % | k = 10–15 % |
| Tarde ya sensible a térmica en | k = 20 % | k = 10 % | k = 5–10 % |

Y lo que importa para el claim:

- **Cero violaciones en 45 celdas.** En toda combinación de ventana, capacidad,
  presupuesto y velocidad, la mañana está **al menos tan dominada por el sol**
  como la tarde. Nunca menos.
- La mañana está dominada por el sol a k = 5 % en **9 de 9** configuraciones.
- La tarde es sensible a la térmica a k ≥ 20 % en **9 de 9**.

> El **umbral numérico** del régimen es función del supuesto de movilidad.
> La **existencia de los dos regímenes y su dirección** no lo son.

Esto es más fuerte que lo que el artículo afirmaba antes, que era un único punto
del espacio de supuestos.

---

## Lo que queda

Nada de análisis. Afiliación, URL del repositorio y lectura final de lengua.
