# SEGAN-D-26-03850: dónde está el paper y qué hay que decidir

Documento único para la conversación de estrategia. Se lee solo, no necesita
adjuntos. Todos los números salen de archivos de resultados versionados y se
regeneran con un comando; ninguno está escrito a mano.

---

## 1. La situación en un párrafo

El paper se envió proponiendo un método de calibración conforme adaptativa
(transporte de scores + shrinkage de cola + ACI) y reportando que reduce el ancho
de los intervalos en un tercio bajo cambio de régimen. El Revisor 1 pidió
probarlo con otro modelo base. Al hacerlo, **la ganancia no se replica**. El
paper está hoy reencuadrado alrededor de ese hallazgo, como resultado
diagnóstico, y esa reescritura ya está hecha y verificada. La pregunta abierta no
es técnica: es si ese reencuadre basta para publicar en esta revista.

---

## 2. Lo que muestran los datos

### 2.1 La ganancia era del modelo base, no de la capa

Ventana de máxima divergencia (oct–dic 2024), nominal 90%. Split estático contra
el método propuesto:

| Modelo base | Split estático | Transporte+ACI | Cambio de ancho |
|---|---|---|---|
| Hurdle, σ constante (el del paper) | 95.3% / 1203 MWh | 90.9% / 806 MWh | **−33.1%** |
| Hurdle, σ(x) | 91.7% / 770 MWh | 89.5% / 733 MWh | −4.8% |
| GBM multi-cuantil | 90.6% / 410 MWh | 90.5% / 425 MWh | **+3.6%** |

Con un modelo base bien calibrado el split estático ya está en el nivel nominal y
la capa adaptativa **ensancha**. Lo que la capa recuperaba era la sobre-dispersión
del hurdle.

### 2.2 La relación es cuantificable y robusta

Sobre 40 celdas (8 modelos base × 5 ventanas), con bootstrap por bloques de día:

| | Valor | IC 95% |
|---|---|---|
| Correlación de Pearson | −0.873 | [−0.912, −0.645] |
| Pendiente (% de ancho por punto de sobre-cobertura) | −4.89 | [−5.62, −3.30] |
| Intercepto (%) | +5.76 | [+1.60, +9.84] |

Dejar fuera cualquier celda mueve r dentro de [−0.889, −0.820]. Dejar fuera un
brazo entero, dentro de [−0.899, −0.792]. **No lo sostiene ningún punto ni ningún
modelo en particular.**

### 2.3 Los dos componentes distintivos del método no se pagan

Aporte marginal al interval score sobre el test completo, en MWh, negativo es
mejor:

| Componente | Efecto | IC 95% | Significativo |
|---|---|---|---|
| Adaptación online (ACI sobre el split estático) | −37.8 | [−60, −10] | sí |
| **Transporte, sobre el ACI ya presente** | **+74.2** | [+47, +105] | **sí, empeora** |
| **Shrinkage de cola, sobre el transporte** | **−6.5** | [−10, −3] | sí, pero es 0.6% |
| Pipeline completo sobre el split estático | +32.4 | [−5, +75] | no |

El transporte empeora una vez que la adaptación está. El shrinkage, que es el
dispositivo más intrincado de la construcción, aporta seis décimas de uno por
ciento y consume el 91% del tiempo de cómputo.

### 2.4 Un método estándar de 2019 lo domina

Test completo, mismo nivel nominal, mismas filas:

| Método | Cobertura | Ancho | Interval score |
|---|---|---|---|
| CQR unilateral (Romano et al. 2019) sobre el GBM | 89.8% | **276 MWh** | **601** |
| Transporte+ACI, el método propuesto | 90.1% | 596 MWh | 1030 |
| Split estático | 92.5% | 678 MWh | 973 |

### 2.5 Forma del modelo contra presupuesto, separado experimentalmente

La objeción previsible era que el GBM gana por tener 54 modelos contra 2. Se
midió:

| Modelo | Árboles | CRPS |
|---|---|---|
| Hurdle | 800 | 89.52 |
| Hurdle | 4.000 | **95.46** (empeora) |
| GBM multi-cuantil | 810 | 87.40 |
| GBM multi-cuantil | 2.700 | 71.38 |
| GBM multi-cuantil | 5.400 | 68.33 |
| GBM multi-cuantil | 21.600 | 67.97 |

A presupuesto idéntico la ventaja casi desaparece (−2.4%, no −24%). **Pero el
hurdle no puede comprar la paridad: con cinco veces el presupuesto empeora.** El
mecanismo se verificó: el deterioro es de localización (μ), no de dispersión (σ),
que es la contraparte experimental de algo que el paper ya reportaba.

---

## 3. Lo que ya está hecho

Los quince comentarios están respondidos. El manuscrito y la carta compilan
limpios, 34 y 19 páginas. Dos verificadores automáticos pasan: 51 de 51
afirmaciones numéricas contrastadas contra su archivo de resultados, y 192
referencias cruzadas contra la numeración real del documento compilado.

La Fase 0 fue **reproducida de forma independiente** desde un clon limpio, en un
entorno donde cuatro de cinco librerías resolvieron en versiones distintas de las
de referencia. El modelo reentrenado coincidió por checksum SHA-256 y las tablas
publicadas coincidieron celda por celda. Eso está declarado en el Apéndice D como
credencial de reproducibilidad.

---

## 4. La decisión que hay que tomar

**El paper propone un método y termina mostrando que sus dos componentes
distintivos no se pagan, y que un método estándar de 2019 sobre un mejor modelo
base lo dobla en nitidez a la misma cobertura.**

El reencuadre diagnóstico es honesto y está bien sostenido. La contribución pasa
a ser: *la ganancia aparente de una capa conformal adaptativa mide la mala
calibración del modelo base, y la relación es cuantificable*. Más el dataset
abierto, que no cambió.

Las opciones, sin que este documento elija ninguna:

1. **Sostener el reencuadre diagnóstico tal como está.** Es lo que está escrito.
   Riesgo: un revisor puede leer que el paper ya no tiene un método propio y
   preguntarse si la contribución alcanza para SEGAN.
2. **Reposicionar como paper de dataset con estudio metodológico negativo
   anexo.** El dataset es sólido e independiente del hallazgo. Implica reescribir
   el encuadre completo otra vez.
3. **Retirar y reenviar a otra revista** donde un resultado negativo
   metodológico tenga mejor encaje.

---

## 5. Dos cosas que hay que saber al entrar

**El resultado del shrinkage cambió hace dos días.** Al reconciliar dos tablas se
descubrió que ninguna reproducía la corrida canónica, por el orden de consumo del
generador aleatorio. Al alinearlas, el shrinkage pasó de "no aporta nada medible"
a un aporte pequeño pero estadísticamente detectable. La conclusión cualitativa
se sostiene, pero la redacción anterior era incorrecta y se corrigió. Si alguien
leyó una versión previa, ese número cambió.

**La salvedad más delicada es la forma funcional del diagnóstico.** Hay un
quiebre de nivel en el nominal, y es robusto a dejar brazos fuera. Pero la forma
no está determinada: fuera de muestra el quiebre empata con la recta única
(RMSE 8.85 contra 8.82), y un término cuadrático pasa de irrelevante sobre las 40
celdas (p = 0.71) a fuertemente significativo sobre 35 (F = 27.9) según qué brazo
esté. Por eso la afirmación quedó acotada a la sobre-cobertura y no se enunció de
forma simétrica. Si alguien empuja por el enunciado simétrico, la respuesta es
que los datos no lo sostienen.

---

## 6. Pendiente técnico

El manuscrito concede que un hurdle con detención temprana probablemente
recuperaría su rendimiento a 800 árboles, y ese experimento no se corrió. Son
unos diez minutos de cómputo. No cambia ninguna conclusión: el orden se establece
al presupuesto propio del hurdle, donde el sobreajuste no está en juego.
