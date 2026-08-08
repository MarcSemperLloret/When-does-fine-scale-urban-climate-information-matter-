# Puerta 2 — ERA5-Land como baseline real

**Fecha:** 6 de agosto de 2026
**Pregunta:** ¿el mecanismo central sobrevive frente a una representación gruesa de verdad, o el uniforme sintético era un straw man?

---

## 0. Respuesta

**El uniforme sintético no era demasiado extremo. ERA5-Land se comporta casi igual que él.**

Sobre las 591 secciones censales de València, ERA5-Land asigna **4 celdas distintas**, y una vez agregadas a fracción de horas seguras a lo largo de 517 horas de tarde, colapsan a **2 o 3 valores distinguibles**. El campo observado produce **91**.

| Ventana / umbral | Representación | sd espacial | Rango | Valores distintos |
|---|---|---:|---:|---:|
| tarde, 30 °C | R1 uniforme | 0,0000 | 0,000 | **1** |
| | R2 ERA5-Land bruto | 0,0119 | 0,045 | **3** |
| | R3 + sesgo global | 0,0059 | 0,027 | **2** |
| | R4 + sesgo por hora | 0,0050 | 0,023 | **3** |
| | **R5 AVAMET** | **0,0561** | **0,209** | **91** |
| mañana, 30 °C | R1 uniforme | 0,0000 | 0,000 | 1 |
| | R2 ERA5-Land bruto | 0,0038 | 0,010 | 3 |
| | **R5 AVAMET** | **0,0336** | **0,130** | **60** |

La dispersión espacial de ERA5-Land es entre **5 y 11 veces menor** que la observada. A efectos de clasificar secciones censales, a 9 km el producto regional es indistinguible de un campo plano. Ésa es la respuesta empírica a la objeción del straw man, y es más fuerte que el argumento teórico: no hace falta suponer que 9 km no resuelve barrios, se mide cuánto no los resuelve.

**Criterio de continuidad superado**: el efecto no desaparece con ERA5-Land. Se puede seguir hacia sombra.

---

## 1. Un hallazgo de primer orden que no estaba previsto

**Corrección de signo respecto a la primera versión de este informe.** Allí se describió como «sesgo frío de −1,85 °C». Es al revés: ERA5-Land está **+1,85 °C por encima** del campo observado en la ventana de tarde, es decir **sesgo cálido**, y −0,31 °C por debajo en la de mañana. El error venía de leer como sesgo la corrección que hay que sumarle. Importa porque **invierte la dirección del error de política**: ERA5-Land no subestima la exposición al calor, la sobreestima, y por tanto señalaría como inseguras secciones que no lo son.

Aun con el signo corregido, el punto se mantiene y es de primer orden: **el sesgo del producto es mayor que toda la señal intraurbana que este estudio mide** (1,2 °C de rango entre barrios).

La magnitud de la sobreestimación se ve mejor sin interpolador de por medio, en las propias estaciones (§1.1): ERA5-Land dice que el 51,6–53,8 % de las horas de tarde superan 30 °C, cuando lo observado va del **11,8 % al 32,9 %**.

Sus consecuencias sobre la cobertura agregada son de otro orden de magnitud que todo lo anterior:

| Ventana | Umbral | Representación | Diferencia de cobertura |
|---|---|---|---:|
| tarde | 30 °C | ERA5-Land bruto | **18,58 pp** |
| tarde | 32 °C | ERA5-Land bruto | **14,45 pp** |
| tarde | 30 °C | + sesgo global | 1,39 pp |
| tarde | 30 °C | + sesgo por hora | 1,54 pp |
| mañana | 30 °C | ERA5-Land bruto | 0,83 pp |

Sin corregir, ERA5-Land se equivoca en 14–19 puntos porcentuales de población mayor cubierta en la ventana de tarde. Corregido el sesgo, baja a 1,4–3,5 pp.

Esto matiza mucho el mensaje. La afirmación «la representación gruesa acierta en la media» **solo es cierta después de corregir el sesgo**, y la corrección requiere las observaciones que supuestamente no se necesitan. Es un argumento circular que hay que declarar: sin red local no se sabe que hay un sesgo de +1,85 °C, y sin saberlo no se puede corregir.

### 1.0. Validación temporal: la corrección generaliza para la media y no para nada más

La corrección se ajustaba sobre las mismas horas en que después se evaluaba. Resuelto con **leave-one-summer-out**: cinco veranos ajustan, el sexto evalúa. Solo cuatro veranos son evaluables (2021, 2022, 2023, 2025), porque el panel común de seis estaciones exige l'Olivereta, que arranca en 2021. 2024 sigue cerrado.

| Ventana | Corrección | Sesgo residual | RMSE | Rango de excedencia obs. | Rango ERA5 corregido | Spearman espacial |
|---|---|---:|---:|---:|---:|---:|
| mañana | global | +0,003 | 1,24 | 13,1 pp | **1,35 pp** | **−0,59** |
| mañana | por hora | +0,002 | 1,11 | 13,1 pp | **0,53 pp** | **−0,52** |
| tarde | global | −0,007 | 1,66 | 21,2 pp | **0,40 pp** | **−0,01** |
| tarde | por hora | −0,007 | 1,66 | 21,2 pp | **0,38 pp** | **0,00** |

Tres lecturas, en orden de importancia.

1. **La corrección aditiva generaliza bien para la media**: sesgo residual fuera de muestra prácticamente nulo, máximo 0,57 °C en el peor verano. La afirmación «corregir el sesgo recupera los totales» sobrevive a la validación temporal.
2. **No recupera nada de la estructura espacial.** El rango de excedencias entre estaciones es de 13–21 puntos observados y de **0,4–1,4 puntos** en ERA5-Land corregido. Refinar la corrección de global a por hora **empeora** este aspecto, porque estrecha aún más el campo.
3. **El orden espacial es ruido o está invertido**: Spearman de **−0,59 a 0,00** fuera de muestra. No es que ERA5-Land ordene peor los barrios; es que no los ordena.

Ese punto 3, fuera de muestra, es la versión más fuerte del resultado central del artículo.

**Alcance de la afirmación.** Se limita a *«en València y durante las ventanas estivales evaluadas, ERA5-Land presentó un sesgo cálido vespertino que requirió calibración observacional local»*. No se afirma que ERA5-Land necesite siempre estaciones locales en cualquier ciudad.

**Blindaje de signo.** Tras la inversión del informe anterior, las tres magnitudes tienen nombres inequívocos y una aserción que falla si dejan de cumplir su definición:

```
raw_error_era5_minus_obs           = T_era5 − T_obs      (positivo ⇒ ERA5-Land cálido)
additive_correction_obs_minus_era5 = T_obs − T_era5      (es lo que se SUMA a ERA5-Land)
corrected_era5                     = T_era5 + additive_correction
```

### 1.1. El control que descarta el artefacto del interpolador

El contraste «3 niveles frente a 91» podía deberse a la ponderación inversa, no a los datos: los 91 salen de interpolar seis estaciones sobre 591 secciones. La comparación **en las propias estaciones, sin interpolador de por medio**, lo resuelve:

| Estación | T obs. media | T ERA5 media | ERA5 − obs. | % horas ≥30 °C obs. | % ERA5 |
|---|---:|---:|---:|---:|---:|
| Col·legi Diocesà | 28,47 | 29,91 | +1,43 | **32,9** | 51,6 |
| Altocúmulo | 28,40 | 29,91 | +1,50 | 32,1 | 51,6 |
| Micalet | 28,32 | 29,91 | +1,59 | 29,4 | 51,6 |
| l'Olivereta | 28,23 | 29,91 | +1,68 | 27,1 | 51,6 |
| Penya-roja | 27,93 | 29,91 | +1,98 | 22,4 | 51,6 |
| Camins al Grau | 27,24 | 30,01 | +2,77 | **11,8** | 53,8 |

Las seis estaciones caen en **2 celdas distintas** de ERA5-Land. El rango entre ellas es de **1,24 °C observado frente a 0,10 °C en ERA5-Land**, y en fracción de horas por encima de 30 °C, **21,1 puntos observados frente a 2,2**. La compresión espacial es de un factor diez y **se mide sin interpolar nada**.

Nótese además que el sesgo de ERA5-Land **crece hacia la costa** (+2,77 °C en Camins al Grau frente a +1,43 en el interior). La sección siguiente pone a prueba si eso es realmente brisa marina no resuelta.

### 1.1b. El mecanismo costero: predicción fallida, mecanismo corregido

La prueba de falsación prevista era comparar la pendiente costera del error entre régimen de brisa y de poniente. **No se puede correr**: en la ventana de tarde hay **6 horas de poniente sobre 517** (1,2 %), y el 92 % son brisa. La tarde estival valenciana es un régimen de brisa casi por definición, así que no existe el contraste. Es una limitación de la muestra, no un resultado.

Como sustituto se estratificó por **intensidad** de la brisa, con la predicción de que un flujo marino más fuerte dejaría un error mayor. **La predicción salió al revés**, de forma monótona y con intervalos que no se solapan:

| Ventana | Estrato de brisa | Velocidad media | β observado | β ERA5-Land | β del error |
|---|---|---:|---:|---:|---:|
| mañana | flojo | 6,7 km/h | **+0,201** | −0,012 | −0,213 |
| mañana | medio | 8,3 km/h | +0,148 | −0,019 | −0,167 |
| mañana | fuerte | 11,0 km/h | **+0,068** | −0,022 | −0,091 |
| tarde | flojo | 8,2 km/h | **+0,234** | −0,009 | −0,243 |
| tarde | medio | 10,1 km/h | +0,190 | −0,012 | −0,203 |
| tarde | fuerte | 12,4 km/h | **+0,154** | −0,017 | −0,171 |

(β en °C por km de distancia al mar; positivo = más cálido tierra adentro.)

La descomposición explica por qué. **El error es el espejo del gradiente real**: β del error ≈ −β observado, porque el β de ERA5-Land es prácticamente cero —y marginalmente del signo contrario— en los seis estratos. Y el gradiente **real** se debilita al reforzarse la brisa: +0,234 con brisa floja frente a +0,154 con brisa fuerte.

La interpretación coherente con eso, y que **no es la que se predijo**, es que lo que ERA5-Land no resuelve no es la intensidad del enfriamiento marino sino su **agudeza espacial**: con brisa floja el aire marino queda confinado a una franja estrecha y el gradiente térmico es abrupto en pocos kilómetros, justo por debajo de la celda de 9 km; con brisa fuerte penetra tierra adentro, el gradiente se reparte y el producto grueso lo aproxima mejor.

Hay que decir con claridad que esto es **una reinterpretación a posteriori**. Lo que está demostrado es que el error del producto reproduce, con signo cambiado, un gradiente costero real y medible que ERA5-Land representa como cero. Que la causa sea la agudeza del frente de brisa es plausible y consistente con las tres estratificaciones, pero necesita una prueba independiente antes de escribirse como mecanismo en el artículo.

### 1.2. La estructura no la sostiene la estación más próxima

Reconstruyendo el campo de cada sección **sin su estación más cercana**, y variando el interpolador:

| Variante | sd espacial | Valores distintos | Jaccard vs referencia | Spearman |
|---|---:|---:|---:|---:|
| IDW p=2, las seis (referencia) | 0,0561 | 91 | 1,000 | 1,000 |
| IDW p=1 | 0,0345 | 74 | 0,841 | 0,978 |
| IDW p=3 | 0,0659 | 88 | 0,952 | 0,992 |
| IDW p=2, k=3 vecinos | 0,0669 | 91 | 0,929 | 0,963 |
| **IDW p=2 sin la más próxima** | **0,0282** | **60** | **0,705** | **0,763** |
| IDW p=2, k=3, sin la más próxima | 0,0401 | 75 | 0,723 | 0,730 |
| **ERA5-Land con sesgo corregido** | **0,0059** | **2** | **0,500** | **−0,085** |

Dos lecturas. La primera: la conclusión **no depende del interpolador** — potencia 1, 2 o 3 y tres o seis vecinos dan Spearman de 0,96 a 0,99 frente a la referencia. La segunda, que es la que responde a la objeción: quitar la estación más próxima degrada el campo (Jaccard 0,705) pero lo deja **cinco veces más estructurado que ERA5-Land** (sd 0,0282 frente a 0,0059) y mucho más cerca de la referencia (Jaccard 0,705 frente a 0,500; Spearman 0,763 frente a **−0,085**).

Ese −0,085 es el número que conviene retener: el orden espacial que produce ERA5-Land corregido **no guarda relación alguna** con el observado. No es que sea peor; es que es otro.

---

## 2. Priorización: corregir el sesgo no ayuda

Jaccard del 20 % de secciones prioritarias frente al campo observado:

| Ventana | Umbral | R1 uniforme | R2 ERA5 bruto | R3 + sesgo | R4 + sesgo/hora |
|---|---|---:|---:|---:|---:|
| mañana | 30 °C | 0,528 | 0,486 | 0,473 | 0,528 |
| mañana | 32 °C | 0,514 | 0,588 | 0,514 | 0,500 |
| tarde | 30 °C | 0,528 | 0,486 | 0,500 | 0,514 |
| tarde | 32 °C | 0,500 | 0,459 | 0,473 | 0,446 |

**ERA5-Land no mejora al uniforme en ninguna combinación**, y en la mitad es ligeramente peor. Lo mismo en el ranking de distritos (Spearman 0,57–0,81 para todos, 3/5 o 4/5 de solapamiento en el top-5, sin diferencia entre representaciones).

La corrección de sesgo arregla la media y no toca el orden, que era lo esperable: una corrección común a toda la ciudad desplaza todas las secciones por igual.

---

## 3. Corrección: la cancelación bidireccional no ocurre

En el intercambio previo se propuso que el pequeño cambio neto de cobertura escondía dos flujos que se cancelan:

$$\Delta C_{\text{neto}} = P(0\to1) - P(1\to0), \qquad C_{\text{bruto}} = P(0\to1) + P(1\to0)$$

**Los datos no lo sostienen.** En 14 de las 16 combinaciones de ventana, umbral y representación, uno de los dos flujos es exactamente **cero**: neto y bruto coinciden en magnitud. Solo dos filas (tarde, 30 °C, R3 y R4) son bidireccionales, y con 20 frente a 195 secciones.

El mecanismo real es otro, y es más simple: **una representación casi plana cae entera a un lado del corte de elegibilidad**. No hay compensación entre errores de signo contrario; hay una clasificación sistemática en un solo sentido. La discrepancia entre un cambio de cobertura pequeño y una reclasificación grande no viene de cancelación sino de la diferencia entre **promediar una fracción continua** y **clasificar con un corte binario**: la media se parece, el lado del corte no.

### Y la magnitud depende mucho del corte, que yo elegí mal

El corte en la mediana no era neutral: **maximiza** la reclasificación, porque coloca el valor plano justo en el centro de la distribución observada. Barrido completo (tarde, 30 °C):

| Cuantil del corte | Suben | Bajan | Bruto | Población 65+ reclasificada |
|---:|---:|---:|---:|---:|
| 0,1 | 0 | 28 | 28 | 4,8 % |
| 0,2 | 0 | 74 | 74 | 12,4 % |
| 0,3 | 20 | 112 | 132 | 22,0 % |
| 0,4 | 20 | 158 | 178 | 29,3 % |
| **0,5** | 20 | 195 | 215 | **36,3 %** |
| 0,6 | 163 | 0 | 163 | 27,8 % |
| 0,7 | 127 | 0 | 127 | 22,2 % |
| 0,8 | 82 | 0 | 82 | 14,4 % |
| 0,9 | 43 | 0 | 43 | 8,3 % |

La reclasificación va del **4,8 % al 36,3 %** según dónde se ponga el corte, y el sentido del flujo se invierte alrededor de q ≈ 0,55, que es donde cae el valor plano de ERA5-Land. La cifra del 36 % que aparecía en la tabla principal es el máximo de la curva, no un resultado.

**Consecuencia para el artículo:** cualquier cifra de reclasificación tiene que ir acompañada de la curva completa, y el corte tiene que fijarse por una razón de política —una norma de accesibilidad existente— y no por una propiedad de la muestra. Es el mismo problema que los 30 y 32 °C, y merece el mismo tratamiento.

---

## 4. Qué queda en pie, y con qué solidez

| Afirmación | Estado |
|---|---|
| ERA5-Land no resuelve la heterogeneidad intraurbana | **Sólida y sin depender del interpolador** — en las propias estaciones, 21,1 pp de rango observado frente a 2,2 pp |
| Los 91 niveles no son un artefacto de la IDW | **Sólida** — quitando la estación más próxima quedan 60 niveles y Spearman 0,76 con la referencia; ERA5-Land da 2 y −0,09 |
| El uniforme sintético no era un straw man | **Sólida** — ERA5-Land se comporta como él |
| ERA5-Land tiene un sesgo cálido mayor que la señal buscada | **Sólida** — +1,85 °C de tarde frente a 1,2 °C de rango |
| La corrección de sesgo recupera la media | **Sólida y validada fuera de muestra** — sesgo residual <0,01 °C en leave-one-summer-out |
| La corrección no recupera la estructura espacial | **Sólida y validada fuera de muestra** — rango de excedencias 0,4–1,4 pp frente a 13–21 pp; Spearman espacial −0,59 a 0,00 |
| El gradiente costero del error es brisa no resuelta | **Mecanismo sin demostrar** — no hay poniente en la muestra (6 h de 517); la predicción por intensidad salió invertida y la reinterpretación es post hoc |
| La representación gruesa reproduce la media | **Condicionada** — solo tras corregir el sesgo con las observaciones locales |
| La representación gruesa no reproduce la priorización | **Sólida** — Jaccard 0,45–0,59, sin mejora sobre el uniforme |
| Los flujos de reclasificación se cancelan | **Refutada** — son unidireccionales en 14 de 16 casos |
| La magnitud de la reclasificación | **Frágil** — 4,8–36,3 % según el corte; hay que fijarlo por política |

---

## 5. Siguiente paso

Sombra, como estaba acordado. Con dos cosas que este bloque añade a la lista:

1. **Fijar el corte de elegibilidad por una norma**, no por un cuantil de la muestra. Sin eso, la métrica principal del artículo es ajustable a voluntad y un revisor lo verá.
2. **El sesgo de ERA5-Land entra en el argumento**, no solo como control. La afirmación defendible pasa a ser: *una representación regional necesita observaciones locales para corregir su sesgo, y aun corregida no recupera el orden espacial*. Eso es más fuerte que «los datos gruesos pierden microclima» y es difícil de atacar.

---

## 6. Reproducción

```bash
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p2_descargar_era5land.py prueba
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p2_descargar_era5land.py completo
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p2_comparar_era5land.py
```

18 peticiones al CDS (una por año y mes; la petición única de seis veranos la rechaza con `cost limits exceeded`), 2,0 MB, 13.248 pasos horarios, 18 celdas de tierra de 25. **2024 no se descarga**: sigue siendo la muestra confirmatoria congelada.

Tablas: `p2_comparacion_era5land.csv`, `p2_priorizacion_era5land.csv`, `p2_dispersion_espacial.csv`, `p2_barrido_corte.csv`.
