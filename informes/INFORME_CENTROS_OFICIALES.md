# Centros de salud oficiales frente a OpenStreetMap

**Fecha:** 7 de agosto de 2026
**Fuente oficial:** `ca_centros_salud` de la Generalitat Valenciana (dadesobertes.gva.es), localizada vía el catálogo de datos.gob.es. 248 centros en la Comunitat.

---

## 0. Resultado

**La capa de servicios importa más que la representación térmica.** Sustituir los centros de OSM por los oficiales cambia el alcance de **87 secciones**, que contienen **26.440 personas de 65 o más años, el 15,1 % del total municipal**, y reordena el **37,5 % del conjunto prioritario**.

A modo de comparación, cambiar ERA5-Land corregido por el campo local reclasificaba entre 5.500 y 10.200 personas. **La calidad del inventario de destinos pesa más que la de la información meteorológica.**

---

## 1. Las dos capas no describen lo mismo

| | OSM (filtrado por nombre) | Oficial GVA |
|---|---:|---:|
| Centros en el municipio (+1,5 km) | 56 | **48** |
| Distancia mediana de red | 654 m | 616 m |
| Distancia P90 | 1.045 m | 1.000 m |
| Secciones alcanzables en 15 min | 405 | **442** |
| Población 65+ alcanzable | 68,64 % | **74,41 %** |

**Solo 36 de los 56 centros de OSM tienen un oficial a menos de 150 m.** Los otros 20 no corresponden a atención primaria pública: son clínicas privadas cuyo nombre casaba con el filtro, duplicados o consultorios que no figuran en el registro. Y a la inversa, 12 centros oficiales no aparecen en OSM.

Lo llamativo es la dirección del efecto: **con menos centros se alcanza más población** (48 frente a 56, y 74,4 % frente a 68,6 %). No es una paradoja — significa que la capa de OSM añadía equipamientos donde ya había cobertura y omitía los que cubrían huecos. El error no era de volumen sino de **distribución espacial**, que es justo el tipo de error que sesga un análisis de accesibilidad y no se ve en un recuento.

---

## 2. Efecto sobre las decisiones

| Métrica | Valor |
|---|---:|
| Jaccard del conjunto de secciones alcanzables | 0,814 |
| Secciones que cambian de estado de alcance | **87** |
| Población 65+ afectada | **26.440 (15,1 %)** |
| Jaccard del conjunto prioritario (20 % peor) | **0,625** |

---

## 3. Consecuencia: hay que rehacer los resultados

Esto afecta a `alcanzable`, que es la base de todo lo demás: la frontera de Pareto, el factorial, la curva en φ y el regret se calcularon sobre 405 secciones alcanzables y ahora son 442.

**Las conclusiones cualitativas no deberían moverse** —la comparación entre representaciones es interna a cada capa de destinos— pero las cifras sí, y no se pueden publicar las actuales. La cadena a rehacer es:

1. Rutas y frontera de Pareto (edificios, y edificios + vegetación)
2. Factorial
3. Curva en φ
4. Regret con bootstrap

Es exactamente el paso «repetir análisis definitivo» de la secuencia acordada, y ahora tiene una razón concreta.

---

## 4. Y una lectura que merece entrar en el artículo

Este resultado no es solo higiene de datos. Encaja en el marco general del trabajo: **la capa de destinos es una capa de información más**, y resulta ser la que más pesa de todas las examinadas. Un artículo sobre qué información hace falta para decidir estaría incompleto si no dijera que **la fuente del inventario de servicios cambia la decisión más que la resolución meteorológica**.

Refuerza además el patrón de fallos silenciosos que este estudio ha ido acumulando: un filtro por nombre sobre OSM produce 56 centros con aspecto perfectamente razonable, y 20 de ellos no son lo que dicen ser.

---

## 5. Reproducción

```bash
PYTHONIOENCODING=utf-8 py -3.11 manuscrito3/analisis/p4e_centros_oficiales.py
```

Tablas: `p4e_comparacion_centros.csv`, `p4e_resumen.json`. Capa descargada en `datos/centros_salud_gva.geojson`.
