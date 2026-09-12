# SEGAN-D-26-03850: estado al 12 de septiembre

Documento único para la conversación de estrategia. Reemplaza al briefing
anterior, que quedó desfasado y se contradecía en sus propios conteos. Todo
número sale de un archivo versionado o de un build y se regenera con un
comando. Reenvío: **14 de septiembre de 2026**.

---

## 1. En una línea

Lo técnico está cerrado y probado. Quedan tres decisiones de contenido y un
archivo que falta en la entrega.

---

## 2. Qué recibe Editorial Manager

| Pieza | Archivo | Estado |
|---|---|---|
| Fuentes LaTeX | `11_fuentes_latex.zip` | 25 archivos. Compila en un directorio que contiene solo el zip: 36 páginas, 0 errores, 0 referencias sin resolver |
| Versión marcada | `12_marcado_CCHANGEBAR.pdf` | 40 páginas, contra la versión enviada el 28 de julio |
| Carta de respuesta | `2_carta_respuesta.pdf` | 19 páginas |
| Suplementario | `13_suplementario_registro_almacenamiento.md` | **no estaba en la entrega**; ver 4.1 |

No hay `.bbl` y no hace falta: las 43 referencias están escritas en línea en el
`.tex`, así que el servidor no tiene que correr BibTeX. El README del zip lo
explica.

---

## 3. Qué cambió desde el briefing anterior

### 3.1 Control de robustez de la Tabla 2

El hurdle con detención temprana (105 árboles) mejora el CRPS en 5.7% pero
empeora el error absoluto medio de 104.1 a 108.6 MWh y queda último en la
Tabla 2, 27.6% detrás del naive estacional (85.1). El orden del pronóstico
puntual no es un artefacto del hurdle que ajustamos. Entró en §5.1 en prosa, sin
fila nueva, y la Tabla 2 quedó explícitamente fuera de la lista de descuento de
§7, porque ese descuento tiene dirección incorporada y aquí la dirección es la
contraria.

### 3.2 La Tabla C.13 perdía sus cuatro filas de semillas

La tabla de hiperparámetros era un flotante más alto que la página, y LaTeX
descartaba en silencio sus cuatro últimas filas: sin error, con un solo aviso en
el log. Ahora se parte entre páginas. El manuscrito pasa de 35 a 36 páginas y
ninguna numeración se movió.

Las semillas nunca faltaron del manuscrito: el Apéndice D las enuncia en prosa.
Lo que era falso es una remisión de la carta, que manda dos veces a esa tabla
por las semillas (la fila de R1.2 del cuadro resumen y la respuesta a R2.4).
Con el arreglo es cierta. No hay nada que divulgar: la versión de julio no tenía
Apéndice C, así que los revisores nunca vieron la tabla truncada.

### 3.3 La versión marcada

El `latexdiff` crudo no compilaba (32 errores) y donde compilaba era ilegible.
Se configuró para tratar tablas, figuras, ecuaciones y bibliografía como
bloques enteros, y la bibliografía se muestra una sola vez sin marcas. Los 40
pasajes que se reescribieron completos se convirtieron a reemplazo de bloque: el
texto viejo entero tachado y después el nuevo entero, sin intercalar. Cada
bloque se comprobó automáticamente, el lado viejo literal contra la versión de
julio y el nuevo literal contra el final.

Al inicio lleva una nota de media página, sin marcas: reencuadre sustancial y
no corrección incremental, alrededor del 72% del cuerpo es texto nuevo, el
cuerpo pasó de 4.753 a 15.805 palabras sin contar la bibliografía, la
bibliografía pasó de 10 a 43 entradas, y el recuento cambio por cambio está en
la carta.

Resultado: las palabras que salen fundidas en el PDF bajaron de 32 a 9, y de 61
párrafos con texto viejo y nuevo mezclado, 46 quedaron en forma de bloque. Las
9 fusiones que quedan están todas fuera de lo que se convirtió (ver 4.3).

### 3.4 Un dato falso que viajaba en las fuentes

El preámbulo del `.tex` decía "cambios respecto de la versión 6.0 enviada". La
enviada es la 5.0; la 6.0 se escribió en agosto y nunca se envió. Es un
comentario que no se imprime, pero va dentro del zip que recibe la editorial.
Corregido.

---

## 4. Lo que falta decidir

### 4.1 El suplementario

El manuscrito lo promete tres veces (§6.3, §7 y la declaración de
disponibilidad de datos) y la carta una vez, en la respuesta a R2.2, que es la
del almacenamiento. Es el registro de sistemas de almacenamiento con sus fechas
de operación comercial, 1.921 palabras y cuatro tablas, y es agnóstico en causas:
dice por escrito que ninguna afirmación causal del manuscrito descansa en él.

Tenía el título viejo del paper; se corrigió hoy tomándolo del `\title` del
manuscrito. Está en Markdown y no hay `pandoc` instalado.

**Recomendación:** subirlo como PDF. El revisor que abra la respuesta a R2.2 va
a ir a buscarlo, y un `.md` en Editorial Manager se ve como texto plano.
Convertirlo toma minutos una vez instalado `pandoc`.

### 4.2 La carta no dice que el modelo base del paper no es el mejor hurdle

§5.4 y §7 lo declaran: el hurdle con detención temprana supera al modelo base
en 5.7% de CRPS, y §7 lista las tablas y figuras que hay que leer con ese
descuento. La carta no lo menciona. Y la carta divulga, uno por uno, todo lo
demás que reduce el reclamo: la ganancia que no replica, el residuo de
nomenclatura de `test_ramp`, la ventaja del GBM a presupuesto igual, los
hiperparámetros que no se seleccionaron sobre datos reales y las seis
afirmaciones descriptivas que no reprodujeron. Un revisor que llegue a §7 va a
encontrar la concesión sin aviso, y la omisión rompe el patrón que la carta
misma estableció.

**Recomendación:** dos o tres oraciones al final del "third point of
disclosure" de la carta a la editora, que ya trata de §5.4. Con 3.1 como la
contracara tranquilizadora: el orden del pronóstico puntual no cambia. No toca
el manuscrito.

### 4.3 Cuánto más limpiar la versión marcada

Quedan 9 palabras fundidas impresas, todas fuera de lo que se convirtió:

| Dónde | Cuántas | Por qué sigue |
|---|---|---|
| §4.4 | 6 | no estaba en la lista; sus cuatro párrafos siguen intercalados |
| §2.1 | 1 | no estaba en la lista |
| §4.3 | 1 | se pidió convertir solo el encabezado |
| §4.2 | 1 | el párrafo contiene una ecuación en display; el texto viejo completo pondría la ecuación dentro de la marca de borrado, y eso no compila |

Sigue además intercalado el segundo párrafo de §6.3: sin fusiones, pero con un
fragmento viejo largo en medio de una oración nueva. Convertir §2.1, §4.3, §4.4
y §6.3 es una línea cada uno, se reverifica solo, y eliminaría 8 de las 9
fusiones. Los cuatro párrafos con ecuación en display exigen cambiar el diseño
del conversor.

**Recomendación:** convertir §2.1, §4.3, §4.4 y §6.3 y dejar los cuatro con
ecuación como están. La versión marcada es una ayuda de lectura, y su propia
nota remite a la carta para el recuento exacto.

---

## 5. Una corrección que hay que conocer

En el reporte anterior se dijo que las semillas no llegaban al PDF y que eso
afectaba la regla de registrar las semillas en el manuscrito. Era falso, y está
corregido en el registro de hallazgos: el Apéndice D siempre las imprimió. El
defecto real es el de 3.2, una tabla que perdía filas y una remisión de la carta
que por eso era falsa, y ya está arreglado. En esa misma corrección la cita de
la carta se atribuyó a R1.2; está en la respuesta a R2.4.

El conteo de palabras fundidas que se reportó, de 14 a 3, estaba subcontado en
los dos extremos. El detector solo miraba bordes entre dos regiones marcadas y
no veía texto sin marcar pegado a texto marcado ("attentionthan",
"unaffectedby"). Con los tres tipos de borde, y confirmando cada fusión en el
texto del PDF, son 32 antes de convertir y 9 ahora. También se dijo que §4.4
tenía tres párrafos intercalados; son cuatro.

---

## 6. Para quien entra sin contexto

El paper se envió proponiendo una capa de calibración conforme adaptativa que
reducía el ancho de los intervalos en un tercio bajo cambio de régimen. Al
probarla con otro modelo base, como pidió el Revisor 1, la ganancia no se
replicó, y el paper se reencuadró como resultado diagnóstico.

| Hecho | Número |
|---|---|
| Cambio de ancho en la ventana de transición, por modelo base | −33.1% hurdle, −4.8% hurdle σ(x), +3.6% GBM multi-cuantil |
| Diagnóstico sobre 40 celdas, correlación | −0.873, IC 95% [−0.912, −0.645] |
| Diagnóstico, pendiente (% de ancho por punto de sobre-cobertura) | −4.89, IC 95% [−5.62, −3.30] |
| Transporte sobre ACI, interval score | +74.2 MWh, IC [+47, +105], empeora |
| Shrinkage de cola, interval score | −6.5 MWh, IC [−10, −3] |
| CQR sobre el GBM contra el método propuesto | 276 contra 596 MWh de ancho, a 89.8% y 90.1% de cobertura |

---

## 7. Verificaciones al cierre

- `verificar_manuscrito.py`: 60 de 60 afirmaciones numéricas contra su archivo
  de resultados, incluidas dos nuevas que leen el texto del PDF y no el `.tex`.
- `verificar_referencias_cruzadas.py`: 221 referencias, todas cuadran, y su
  autochequeo contra la numeración real del documento compilado pasa.
- Abstract: 249 y 246 palabras con los dos criterios de conteo, límite 250.
- Log de compilación: ningún aviso que descarte contenido.
- `auditar_marcado.py`: regenera el conteo de fusiones y de párrafos en forma
  de bloque de la versión marcada.
- Todo en la rama `revision/reframing`.
