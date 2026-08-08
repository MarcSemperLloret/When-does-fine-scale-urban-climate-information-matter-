# Arbolado: el factor que faltaba, y que cambia la conclusión del factorial

**Fecha:** 7 de agosto de 2026
**Fuente:** nDSM `MDSnV2,5` de 2.ª cobertura, hojas MTN50 0696, 0722 y 0747 (CNIG)

---

## 0. Resultado

**Con el arbolado dentro, la sombra deja de absorber el efecto de la representación térmica.**

La conclusión anterior —«la sombra reduce a la mitad el efecto térmico»— era **un artefacto de una capa de sombra incompleta**. Sin árboles, la exposición solar quedaba sobreestimada (5,19 min al sol a las 17 h frente a 2,41 con árboles), la condición solar se volvía muy restrictiva y se comía la señal térmica. Con la vegetación real:

| Presupuesto solar | Cumplen (solo edificios) | Cumplen (+ arbolado) | Efecto térmico, edificios | Efecto térmico, + arbolado |
|---|---:|---:|---:|---:|
| 3 min | 27–44 % | 67–85 % | 0 (saturado) | 0–4.899 |
| 5 min | 58–72 % | 90–96 % | 0–1.428 | 4.038–8.555 |
| 8 min | 84–91 % | 98–100 % | 3.571–6.975 | **5.523–10.185** |

(Población de 65+ reclasificada al cambiar ERA5-Land corregido por el campo local.)

Sin sombra alguna, ese efecto es de 5.512 a 10.258 personas. **Con arbolado y presupuesto de 8 minutos es prácticamente el mismo**: 5.523–10.185. Es decir, la sombra y la representación térmica funcionan como **dos filtros que apenas interfieren**, no como uno que sustituye al otro.

El mecanismo es transparente y conviene decirlo así: el grado en que la sombra absorbe el efecto térmico **no es una propiedad del clima urbano, sino de cuánto aprieta la restricción solar**. Cuando casi todas las secciones la cumplen, deja de discriminar y decide la temperatura.

---

## 1. Cuánta sombra aporta el arbolado

Copa tratada como **opaca**, que es la cota superior. Fracción de la red peatonal en sombra, ponderada por longitud, 15 de julio:

| Hora | Solo edificios | + arbolado | Aporte | Relativo |
|---|---:|---:|---:|---:|
| 10 | 14,25 % | 41,46 % | +27,21 pp | +191 % |
| 12 | 7,14 % | 21,33 % | +14,19 pp | +199 % |
| 17 | 13,59 % | 40,29 % | +26,70 pp | +197 % |
| 18 | 17,42 % | 48,91 % | +31,49 pp | +181 % |

**El arbolado prácticamente triplica la sombra de la red.** Es el mayor factor individual de todo el estudio.

### Validación por contexto (17 h, 15 de julio)

| Zona | Solo edificios | + arbolado | Aporte |
|---|---:|---:|---:|
| Jardí del Turia | 31,7 % | 74,0 % | **+42,3 pp** |
| Camins al Grau | 40,5 % | 76,2 % | +35,7 pp |
| Benicalap | 38,6 % | 67,9 % | +29,4 pp |
| Eixample/Russafa | 47,7 % | 73,5 % | +25,8 pp |
| Malva-rosa (playa) | 12,5 % | 36,3 % | +23,8 pp |
| Ciutat Vella | 57,6 % | 80,8 % | +23,2 pp |
| El Saler / Albufera | 0,5 % | 18,4 % | +17,8 pp |
| Horta nord | 0,7 % | 17,0 % | +16,4 pp |

El Jardí del Turia es el que más gana, que es lo que debe pasar en un parque lineal arbolado sobre un cauce sin edificios.

**Comprobación del ráster en puntos concretos** (fracción de celdas con vegetación > 2 m en 400 m):

| Punto | > 2 m | > 5 m | Mediana |
|---|---:|---:|---:|
| Jardí del Turia | 83,0 % | 62,2 % | 7,4 m |
| **Devesa del Saler (pinada)** | **66,1 %** | 35,6 % | 5,3 m |
| Ciutat Vella | 68,9 % | 48,1 % | 7,4 m |
| El Saler poblado | 6,3 % | 0,1 % | 2,6 m |
| Horta nord | 8,3 % | 2,1 % | 3,3 m |

La Devesa aparece correctamente como masa forestal. La cifra baja de «El Saler / Albufera» en la tabla anterior venía de que el punto de muestreo estaba en el poblado y el marjal, no en la pinada — era un problema de muestreo mío, no del dato.

---

## 2. La frontera tiempo–sombra, con árboles

| Hora | Sol en ruta rápida | | Sol en ruta sombreada | | Ahorro |
|---|---:|---:|---:|---:|---:|
| | edificios | + árboles | edificios | + árboles | + árboles |
| 10 | 5,32 | **2,25** | 3,46 | **1,17** | 48,0 % |
| 12 | 7,07 | 5,31 | 5,41 | 3,13 | 41,1 % |
| 17 | 5,19 | **2,41** | 3,22 | **1,07** | 55,6 % |
| 18 | 4,22 | 1,54 | 2,61 | 0,56 | 63,6 % |

Con arbolado, elegir la ruta sombreada ahorra entre el **41 % y el 64 %** de los minutos al sol, por un coste de tiempo del 13 al 20 %. A las 18 h el tramo continuo al sol de la ruta sombreada baja a **cero**.

---

## 3. Qué hay que corregir del informe anterior

La afirmación «la sombra domina y reduce a la mitad el efecto de la representación térmica» **solo vale para la capa de solo edificios**, que es la cota inferior de sombra. Formulación corregida:

> El grado en que la sombra absorbe el efecto de la representación térmica está acotado entre **aproximadamente la mitad** (solo edificios, cota inferior de sombra) y **prácticamente nada** (edificios y copa opaca, cota superior). Con la vegetación real de València y un presupuesto de exposición solar realista, está mucho más cerca del segundo extremo: los dos tipos de información actúan como filtros casi independientes.

Y la jerarquía de información se mantiene, pero con el arbolado arriba del todo:

$$\text{arbolado} > \text{geometría edificada} > \text{estructura térmica local} > \text{temperatura regional corregida}$$

con la diferencia de que **ninguno sustituye al anterior**: quitar cualquiera cambia qué barrios se priorizan.

---

## 4. Limitaciones

1. **Copa opaca.** Una copa transmite entre el 5 y el 30 % de la radiación según especie y época. Se reportan los dos extremos y el resultado real está dentro, pero el intervalo es ancho y en este caso **la conclusión cualitativa cambia entre extremos**, así que no es una limitación menor: es la principal.
2. **Umbral de 2 m para vegetación con sombra útil.** Elegido, no calibrado. Por debajo, la sombra cae sobre la propia mata.
3. **Sin estacionalidad de la copa.** El arbolado de València es en buena parte perenne, pero el plátano de sombra, que es el árbol de calle dominante en el Eixample, es caduco. Para las ventanas estivales analizadas está en hoja, así que el sesgo va en la dirección segura.
4. **Sin cielo real** ni temperatura radiante. Sigue siendo exposición solar geométrica.
5. **Resampleo por máximo** del nDSM de 2,5 m a la rejilla de sombra de 3 m: infla ligeramente la cobertura arbolada.

---

## 5. Reproducción

```bash
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p3_sombra_vegetacion.py
SOMBRA_PARQUET=sombra_aristas_veg.parquet RUTAS_PARQUET=rutas_sombra_veg.parquet \
  SUFIJO_SALIDA=_veg PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p3_rutas_sombra.py
RUTAS_PARQUET=rutas_sombra_veg.parquet SUFIJO_SALIDA=_veg \
  PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p3_factorial.py
```

Tablas: `p3_sombra_vegetacion.csv`, `p3_rutas_frontera_veg.csv`, `p3_factorial_veg.csv`.
