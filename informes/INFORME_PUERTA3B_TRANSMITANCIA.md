# Puerta 3b — Transmitancia de copa y estabilidad estacional

**Fecha:** 7 de agosto de 2026
**Pregunta:** ¿en qué rango físicamente plausible de transmitancia sobrevive la conclusión?

---

## 0. Respuesta

**Sobrevive en todo el rango plausible, y con holgura.**

Sustituida la copa opaca por una transmitancia $\tau$ —fracción de radiación directa que atraviesa la copa— la exposición de un tramo pasa a ser

$$E = t\,\bigl(f_{\text{abierto}} + \tau\,f_{\text{copa}}\bigr)$$

con $\tau = 0$ para el edificio, que sí es opaco, y $\tau = 1$ para cielo abierto. No es un peso arbitrario: $\tau$ es una magnitud física medible, y lo que se reporta es la curva completa.

Los tres estados salen de las dos capas ya calculadas, sin rehacer sombras: $f_{\text{edificio}} = f_{\text{ed}}$, $f_{\text{copa}} = f_{\text{veg}} - f_{\text{ed}}$, $f_{\text{abierto}} = 1 - f_{\text{veg}}$.

### La curva, umbral 30 °C, presupuesto 8 min

| τ | Exposición mediana | Cumplen solar | Jaccard | Pob. 65+ reclasificada |
|---:|---:|---:|---:|---:|
| 0,00 (opaca) | 2,04 / 1,20 min | 98,0 / 99,8 % | 0,486 / 0,500 | 10.185 / 9.586 |
| **0,05** | 2,15 / 1,38 | 98,0 / 99,8 | 0,486 / 0,500 | **10.185 / 9.586** |
| **0,10** | 2,30 / 1,50 | 97,8 / 99,8 | 0,486 / 0,500 | **10.221 / 9.586** |
| **0,20** | 2,65 / 1,74 | 97,5 / 99,5 | 0,486 / 0,500 | **10.236 / 9.586** |
| **0,30** | 2,89 / 1,97 | 97,3 / 99,5 | 0,500 / 0,500 | **9.910 / 9.586** |
| 0,50 | 3,48 / 2,44 | 93,8 / 97,8 | 0,588 / 0,558 | 7.916 / 8.306 |
| 1,00 (sin árbol) | 4,42 / 3,31 | 83,7 / 91,4 | 0,820 / 0,688 | 3.602 / 5.982 |

*(mañana / tarde)*

Sobre las tres temperaturas umbral y el rango **τ = 0,05–0,30**: Jaccard **0,473–0,688**, población reclasificada **5.523–10.236**.

Compárese con **no aplicar filtro solar en absoluto**: 5.512–10.258.

> **En todo el rango plausible de transmitancia, el efecto de la representación térmica sobre la priorización es indistinguible del que tiene sin filtro solar alguno.** La conclusión no depende de τ.

El efecto solo se degrada en $\tau \geq 0{,}50$, que es una copa implausiblemente transparente, y colapsa al valor de «solo edificios» en $\tau = 1$.

---

## 1. Lo que esto obliga a corregir

### La jerarquía queda retirada

Sería tentador escribir `arbolado > edificios > térmica local > ERA5`. **No está justificado**, y ahora se ve por qué con más claridad: en el rango plausible de τ, con presupuesto de 8 minutos, el filtro solar **apenas discrimina** —lo cumple entre el 97 y el 100 % de las secciones alcanzables—. Un filtro que casi nadie incumple no puede ordenarse frente a uno que sí discrimina.

Lo que queda establecido, y **no depende de τ porque es geométrico**:

> El arbolado es un componente de primer orden de la sombra peatonal y no se puede omitir: pasar de solo edificios a edificios más vegetación añade entre 14 y 31 puntos porcentuales de sombra según la hora, y reduce la exposición mediana de la ruta de 4,42 a 2,30 minutos.

Y lo que queda establecido sobre la interacción:

> Con la vegetación real de València, la sombra **no absorbe** el efecto de la representación térmica. Los dos tipos de información actúan como filtros que apenas interfieren. La absorción que se observó con la capa de solo edificios era un artefacto de sobreestimar la exposición solar.

### Dónde está de verdad la sensibilidad

No en τ, sino en el **presupuesto de exposición solar**. Con 5 minutos el resultado sí se mueve con τ —en la ventana de mañana, de 6.538 reclasificados en τ = 0,05 a **cero** en τ = 0,30, por saturación— mientras que con 8 minutos es plano. El parámetro que hay que fijar con una norma externa sigue siendo el presupuesto, no la transmitancia.

---

## 2. Estabilidad estacional

Jaccard del 20 % prioritario entre pares de fechas, τ = 0,10, umbral 30 °C:

| Ventana | Presupuesto | jun–jul | jun–ago | jul–ago |
|---|---:|---:|---:|---:|
| mañana | **8 min** | **0,976** | **0,884** | **0,906** |
| mañana | 5 min | 0,670 | **0,409** | 0,636 |
| tarde | **8 min** | **1,000** | **1,000** | **1,000** |
| tarde | 5 min | 0,884 | 0,636 | 0,688 |

**Con presupuesto de 8 minutos, usar fechas representativas está justificado**: los conjuntos prioritarios coinciden entre el 88 y el 100 %, y en la ventana de tarde son idénticos. **Con 5 minutos no lo está**: el par junio–agosto baja a 0,409, y ahí haría falta sombra día a día.

Es coherente con el resto: cuanto más aprieta la restricción solar, más manda la geometría solar concreta del día. La exposición mediana de mañana pasa de 2,52 min el 15 de junio a 1,83 el 15 de agosto, porque el sol más bajo alarga las sombras.

---

## 3. Lo que no se ha hecho, y por qué

**No se ha usado el inventario municipal de arbolado.** La idea de cruzarlo con el nDSM para asignar intervalos de τ por grupo de especie —perennifolias densas, caducifolias densas, caducifolias medias, palmeras— es buena y sigue en pie, pero **ha dejado de ser urgente**: la conclusión es plana en todo el rango 0,05–0,30, de modo que afinar τ dentro de ese rango no cambiaría nada. Pasa a ser refinamiento, no requisito.

**No se ha inferido τ de la altura.** El nDSM informa de dónde puede proyectarse geométricamente una sombra, no de la densidad óptica de la copa. Un árbol de 12 m no da necesariamente más sombra efectiva que uno de 8 m con copa densa. Las dos variables se mantienen separadas: el nDSM decide la geometría y τ la atenuación.

**Estacionalidad de la copa.** El plátano de sombra, dominante en el Eixample, es caduco, pero en las ventanas estivales analizadas está en hoja. El sesgo va en la dirección segura.

---

## 4. Reproducción

```bash
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p3b_transmitancia.py
```

Tablas: `p3b_curva_transmitancia.csv`, `p3b_estabilidad_estacional.csv`, `p3b_estacional_detalle.csv`.
