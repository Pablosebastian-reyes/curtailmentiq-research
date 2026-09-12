# HALLAZGOS CRITICOS — revision SEGAN-D-26-03850

Resultados de la revision que **contradicen una afirmacion central** de la
version enviada. Se documentan aqui sin reescribir la conclusion del paper: la
decision cientifica sobre como reencuadrar el trabajo es de los autores.

---

## H1. La ventaja de Transport+ACI no sobrevive al cambio de modelo base

**Estado:** confirmado, reproducible.
**Fase:** 0 (comentario R1.1).
**Afirmacion afectada:** abstract, seccion 5.2 y conclusion. Textual de la
version vigente del manuscrito:

> "an adaptive scheme that combines a probability-integral-transform score with
> online recalibration and a transport of the calibration scores restores
> sharpness while holding coverage near the nominal level through the transition
> window, **narrowing the transition intervals by about a third**."

**Comando que lo reproduce:**

```
<venv>/bin/python flagship/revision/fase0_entrenar_qgbm.py
<venv>/bin/python flagship/revision/fase0_model_agnostic.py
<venv>/bin/python flagship/revision/fase0_diagnostico.py
```

Archivos: `resultados/fase0/fase0_tabla_por_modelo.csv`,
`resultados/fase0/fase0_diagnostico.csv`,
`resultados/fase0/fase0_diferencias_bootstrap.csv`.

**Control de validez de la comparacion.** La rama del hurdle de este
experimento reproduce `conformal_v3_tabla.csv` de la version enviada en las 30
celdas x 4 metricas, verificado por asercion en el propio script
(`verificar_reproduccion`). Lo unico que cambia entre ramas es la predictiva
base: mismo score PIT, mismas fronteras de ventana, mismo embargo de 7 dias,
misma semilla 20260720, mismos gamma, misma ventana reciente de 60 dias, mismo
shrinkage de cola.

### El resultado

Ventana de transicion (oct-dic 2024), nominal 90%:

| Modelo base | Split estatico | Transport+ACI (γ=0.05) | Cambio de ancho |
|---|---|---|---|
| hurdle, σ constante (oficial) | 95.3% / 1203 MWh | 90.9% / 806 MWh | **-33.1%** |
| hurdle, σ(x) | 91.7% / 770 MWh | 89.5% / 733 MWh | -4.8% |
| GBM multi-cuantil (R1.1) | 90.6% / 410 MWh | 90.5% / 425 MWh | **+3.6%** |

Con el modelo base alternativo la ganancia **no se replica**: Transport+ACI
produce intervalos ligeramente mas anchos, no mas angostos. La diferencia de
ancho en la ventana de transicion es +15.1 MWh con un intervalo bootstrap por
bloques de dia de [+0.0, +30.3], que apenas excluye el cero; la diferencia de
interval score, +13.9 con intervalo [-10.7, +37.8], si lo contiene. En
cualquiera de las dos lecturas el signo es el contrario del reportado y la
reduccion no esta.

### El diagnostico

Sobre las 15 celdas (3 modelos base x 5 ventanas), el recorte de ancho de
Transport+ACI esta **linealmente asociado a cuanto sobre-cubre el split
estatico** en esa celda:

- correlacion de Pearson r = **-0.757**
- pendiente **-4.39%** de ancho por punto porcentual de sobre-cobertura
- intercepto **+5.49%**: cuando el split estatico ya esta en el nivel nominal,
  Transport+ACI **ensancha** los intervalos en torno a un 5%

La lectura que sostienen estos numeros es que la capa adaptativa no esta
corrigiendo el cambio de regimen: esta reparando la sobre-dispersion del hurdle
de σ constante. El -33% es la magnitud de esa mala calibracion, no la magnitud
del cambio distribucional.

### El agravante

El modelo base alternativo no solo anula la ganancia: **domina al hurdle en
toda metrica propia y en toda ventana.**

- CRPS: entre 18% y 30% mas bajo que el hurdle en las cinco ventanas
  (92.9 contra 133.5 MWh en la transicion).
- Interval score del limite unilateral: el mejor de las 18 combinaciones
  (modelo x metodo) en las cinco ventanas es siempre el GBM multi-cuantil, y
  en tres de las cinco es el GBM multi-cuantil **con el split estatico**, sin
  ninguna capa adaptativa.
- Ancho medio en la transicion: 410 MWh con cobertura 90.6%, frente a los
  806 MWh con 90.9% del pipeline completo del paper. La mitad de ancho a la
  misma cobertura.

El hurdle conserva una ventaja: el Brier del evento {Y>0} es mejor
(0.0721 contra 0.1027 en la transicion). Ese contraste no es equivalente, sin
embargo, porque la probabilidad de ocurrencia del GBM multi-cuantil se lee de
la rejilla de cuantiles con resolucion 0.02 y no de un clasificador dedicado.
Se reporta como descriptivo.

### Que NO dice este hallazgo

- No dice que el score PIT sea incorrecto. Es el que hace comparables centrales
  de tamanos distintos y trata el atomo, y funciona igual de bien con las dos
  predictivas.
- No dice que ACI o el transporte esten mal implementados. La rama del hurdle
  reproduce exactamente la corrida oficial.
- No dice que no haya cambio distribucional. La Fase 6 evalua eso por separado
  y no depende de este resultado.
- No dice que la capa adaptativa sea inutil en general. Dice que **en este
  registro, con un modelo base bien calibrado, no aporta**, y que la ganancia
  reportada es atribuible al modelo base.

### Decision que corresponde a los autores

Este hallazgo cambia el alcance del trabajo y es por tanto condicion de parada
tipo (c) ademas de (a). Las opciones que se ven desde los datos, sin que este
documento elija ninguna:

1. **Reencuadrar la contribucion metodologica** como un diagnostico: la
   ganancia de una capa conformal adaptativa mide la mala calibracion del
   modelo base, y la relacion es cuantificable. Es un resultado negativo util y
   publicable, y el experimento de la Fase 0 es la evidencia.
2. **Cambiar el modelo base oficial** al GBM multi-cuantil y rehacer las tablas
   3 y 4. El paper pierde su resultado adaptativo y gana intervalos que son la
   mitad de anchos.
3. **Acotar la afirmacion** al modelo base evaluado, declarando explicitamente
   que no se replica con un GBM multi-cuantil. Es lo minimo defendible si se
   conserva la estructura actual.

Las fases 1 a 9 se ejecutan igualmente: ninguna depende de cual de las tres se
elija, y todas mejoran el manuscrito bajo cualquiera de ellas.


---

## H3. Ni el transporte ni el shrinkage de cola se pagan a si mismos

**Estado:** confirmado, reproducible.
**Fase:** 2 (comentario R1.3) y 4 (comentarios R1.5, R2.6).
**Afirmacion afectada:** la contribucion metodologica central del manuscrito es
la combinacion transporte + shrinkage + ACI. Las ablaciones dicen que las dos
primeras piezas no aportan.

**Comandos:**

```
<venv>/bin/python flagship/revision/fase2_ablaciones.py
<venv>/bin/python flagship/revision/fase4_metricas_benchmarks.py
```

### Aporte marginal de cada componente sobre el interval score

Test completo, bootstrap de 2000 remuestreos de dias completos. Negativo mejora.

| Componente | Diferencia de IS | IC 95% | Significativo | Costo |
|---|---|---|---|---|
| Adaptacion online, ACI sobre el split estatico | -37.8 | [-60.3, -10.1] | si | +0.2 s |
| Transporte sobre el ACI ya presente | **+74.2** | [+46.7, +105.0] | **si** | +0.4 s |
| Shrinkage de cola sobre el transporte | -0.3 | [-2.9, +1.8] | **no** | +6.1 s |
| Pipeline completo sobre el split estatico | +29.3 | [-8.0, +71.6] | no | +6.7 s |

El transporte **empeora** de forma significativa una vez que el ACI ya esta
presente, y lo hace en cuatro de las cinco ventanas. El shrinkage de cola no
tiene efecto distinguible de cero sobre el test completo y multiplica por doce
el tiempo de ejecucion del metodo: es el 91% del costo computacional del
pipeline y compra una diferencia de -0.3 MWh de interval score con un intervalo
de confianza que contiene el cero.

La ganancia del pipeline se concentra en la ventana de transicion (-176.3,
significativo) y se pierde en 2025-S1 y 2025-S2 (+100.0 y +104.2, ambos
significativos), de modo que sobre el test completo el pipeline **no mejora** al
split estatico.

### Los benchmarks simples ganan

Test completo, ordenado por interval score. El CQR unilateral es la regresion
cuantilica conformalizada de Romano et al. sobre el GBM, es decir una capa de
calibracion estandar desde 2019 y mucho mas simple que la del manuscrito.

| Metodo | Cobertura | Ancho | % infinitos | Interval score |
|---|---|---|---|---|
| B2 distribucion movil 60d por central | 86.5 | 282 | 0.0 | **583** |
| B3 CQR unilateral sobre el GBM | **89.8** | **276** | 0.0 | **601** |
| B1 cuantil empirico 365d por central | 87.2 | 317 | 0.0 | 656 |
| ACI (g=0.02), hurdle | 90.2 | 551 | 0.0 | 936 |
| Split estatico (PIT), hurdle | 92.5 | 678 | 0.0 | 973 |
| Transporte+ACI (g=0.05), hurdle | 90.1 | 591 | **6.1** | 1026 |
| Transporte+ACI (g=0.02), hurdle | 90.1 | 663 | 0.5 | 1079 |

Lectura con cuidado: B1, B2 y B4 compran su interval score bajo a costa de
cobertura, entre 86.5% y 82.4% frente al 90% nominal, y un operador que necesite
el nivel declarado no puede usarlos. **B3 no.** El CQR unilateral sobre el GBM
llega a 89.8% de cobertura, dentro de medio punto del nominal, con 276 MWh de
ancho medio frente a los 591 del metodo del manuscrito. Es la segunda
confirmacion independiente de H1: la capa de calibracion no es donde esta el
problema.

### Aporte que si sobrevive

Acotar la actualizacion de alpha por abajo (alpha_min = 0.005) **elimina por
completo los intervalos infinitos** en las cinco ventanas y en las cuatro
configuraciones adaptativas, a un costo de cobertura de a lo mas cuatro decimas
de punto. Es una correccion barata, y responde al encargo explicito del
comentario R1.5.

---

## H4. Seis afirmaciones descriptivas de la seccion 3.3 y 4.4 no reproducen

**Estado:** confirmado. **Fase:** 6.
**Comando:** `<venv>/bin/python flagship/revision/fase6_cronologia.py`
**Archivo:** `resultados/fase6/fase6_verificacion_afirmaciones.csv`
(24 afirmaciones verificadas, 18 reproducen).

Ninguna toca un resultado; todas son descripciones del dataset que hay que
corregir en el texto.

| Seccion | Dice el texto | Regenerado |
|---|---|---|
| 4.4 | W1 de las demas ventanas contra la calibracion: "0.28 a 0.76" | 0.278 a **0.947**; `test_pre` vale 0.947 y queda fuera del rango citado |
| 3.3 | umbral del nulo de permutacion del contraste oct-dic 2024 contra oct-dic 2025: 0.105 | **0.115**; el veredicto (0.085, no distinguible de cero) no cambia |
| 3.3 | ocurrencia de solar norte "entre 0.71 y 0.85 durante 2024 a 2026" | cierto para los promedios **por ventana** (0.750 a 0.815); a nivel **mensual** el rango es 0.635 a 0.877 |
| 3.3 | "la hora pico del perfil intradiario es la 16 en cada semestre del registro" | es la 16 hasta 2025-H1 y la **17** en 2025-H2 y 2026-H1; las dos horas estan casi empatadas |
| 3.3 | distancia de variacion total entre semestres consecutivos "entre 0.04 y 0.06, nunca sobre el 0.08" | **0.032 a 0.079** desde 2023-H1 |
| 3.3 | el centroide del perfil "se mueve menos de quince minutos entre semestres" | se mueve hasta **22 minutos** (0.369 h) |

Ademas, dos precisiones de procedimiento que el texto no daba y que la Fase 1
declara:

- La penalizacion de los algoritmos de punto de cambio es **BIC con k = 1**,
  `pen = sigma^2 log n`. La bitacora interna la describia como `3 sigma^2 log n`,
  y con ese factor solo se detecta 2023-05. Con k = 1, PELT y segmentacion
  binaria devuelven los dos puntos de cambio publicados, 2023-05 y 2024-01, con
  saltos +1.049 y +0.762, que son los +1.05 y +0.76 del texto. **El resultado
  publicado es correcto; la descripcion interna de la penalizacion estaba mal.**
- El quiebre de la tasa de crecimiento reproduce en fecha (2025-01 en solar
  norte, 2024-12 en el sistema) y en el valor posterior (+0.088 y +0.010). El
  valor **previo** depende del convenio: el +0.89 citado para solar norte es la
  media acumulada de toda la serie previa, mientras que el +0.90 citado para el
  sistema es la media del segmento inmediatamente anterior. El texto mezcla los
  dos convenios y hay que unificarlo.

### Robustez que si se confirma, y con holgura

El punto central de la cronologia queda mas firme que en la version enviada:
sobre **180 configuraciones** de deteccion (dos estratos x tres metodos de
desestacionalizacion x cinco penalizaciones x tres tamanos minimos de segmento x
dos algoritmos), **ninguna** detecta un punto de cambio en 2025 y **ninguna** lo
detecta en octubre de 2024.

---

## H2. Deuda de trazabilidad en la Tabla 1 y en la seccion 3.3

**Estado:** confirmado.
**Fase:** inventario previo, resuelto en Fase 6.

Los valores de la Tabla 1 (descomposicion estacional), de los puntos de cambio
de la seccion 3.3, de las distancias de Wasserstein y de los umbrales de
permutacion **no salian de ningun archivo de resultados versionado en este
repositorio** al iniciar la revision. Provenian de un analisis cuyo script
intermedio escribia en `/tmp`. Esto viola la Regla Dura 1. La Fase 6 los
regenera con un script versionado, `flagship/revision/fase6_cronologia.py`, que
deja los CSV en `resultados/fase6/`. **Deuda saldada.** Los valores que no
reproducen estan en H4.

---

## Estado final de la revision

Los cuatro hallazgos estan documentados y todos los experimentos que los
sostienen se reproducen con un comando. La decision de alcance de los autores,
tomada el 2026-09-01 ante H1, fue reencuadrar la contribucion metodologica como
**resultado diagnostico**: la ganancia de una capa conformal adaptativa mide la
mala calibracion del modelo base, y esa relacion es cuantificable. El manuscrito
revisado esta escrito sobre esa base, y la carta de respuesta lo declara en el
primer parrafo, antes de responder a ningun comentario.

Comprobacion de que ningun numero del manuscrito quedo sin respaldo:

```
$VENV flagship/revision/verificar_manuscrito.py    # 43 de 43
```

---

## H5. El diagnostico se REFUERZA al ampliarlo a cuarenta celdas

**Estado:** confirmado. **Fase:** 0b.
**No es una contradiccion:** se anota aqui porque cambia una cifra central del
manuscrito y porque la condicion de parada obligaba a mirarlo antes de escribir.

**Comando:**

```
<venv>/bin/python flagship/revision/verificacion/obj1_capacidad_contra_forma.py
<venv>/bin/python flagship/revision/verificacion/obj1b_escalera_capacidad.py
<venv>/bin/python flagship/revision/fase0b_diagnostico_ampliado.py
```

Archivos: `resultados/fase0b/fase0b_celdas.csv`, `fase0b_diagnostico.json`.

### De donde salieron las celdas nuevas

El `evaluar()` del experimento de capacidad recorre las cinco ventanas, no solo
la de transicion, asi que cada brazo de la escalera ya estaba evaluado con la
capa conformal completa. Ocho modelos base por cinco ventanas dan cuarenta
celdas donde el manuscrito usaba quince. Se excluye el brazo de rejilla gruesa,
cuyo split estatico devuelve 100% de intervalos infinitos y no produce celda.

### El resultado

| | Quince celdas | Cuarenta celdas |
|---|---|---|
| r de Pearson | −0.755 | **-0.873**, IC [-0.912, -0.645] |
| Pendiente | −4.36 | **-4.89**, IC [-5.62, -3.30] |
| Intercepto | +5.45, IC [+0.07, +11.25] | **+5.76**, IC [+1.60, +9.84] |
| Rango de sobre-cobertura | [−2.06, +5.34] pp | **[-8.42, +5.34] pp** |

El intercepto, que con quince celdas apenas excluia el cero, pasa a excluirlo con
holgura. Dejar una celda fuera mueve r dentro de [-0.889, -0.820];
dejar un modelo base entero, dentro de [-0.899, -0.792].

### El enunciado simetrico NO se adopta

Se evaluo el enunciado mas general, que la capa transfiere entre cobertura y
ancho en las dos direcciones. Las dos condiciones acordadas:

- **(i) al menos cinco celdas por debajo de −2 pp: NO SE CUMPLE.** Hay 4.
- **(ii) sin quiebre entre tramos: NO SE CUMPLE.** F(2,36) = 6.778, p = 0.0032.

Se conserva el enunciado acotado a la sobre-cobertura. El quiebre, eso si, es de
**nivel y no de pendiente**: dejar variar solo la ordenada lo explica
(F(1,37) = 12.982, p = 0.0009) y dejar variar tambien la pendiente no anade nada
(F(1,36) = 0.685, p = 0.41). La tasa a la que la capa convierte
desviacion de cobertura en ancho es la misma a ambos lados, -6.50 por punto
porcentual; lo que difiere es el desplazamiento.

---

## H6. La afirmacion de dominacion mezclaba forma con capacidad

**Estado:** confirmado. **Fase:** C.
**Afirmacion afectada:** "su CRPS es 18 a 30 por ciento mas bajo", junto a la de
disciplina identica de entrenamiento.

**Comando:** `<venv>/bin/python flagship/revision/verificacion/obj1b_escalera_capacidad.py`

| Modelo | Arboles | CRPS transicion | CRPS test | Contra la referencia |
|---|---|---|---|---|
| Hurdle 2x400 | 800 | 133.52 | 89.52 | referencia |
| Hurdle 2x2000 | 4.000 | 141.07 | 95.46 | **+6.6%** |
| GBM 54x15 | 810 | 131.18 | 87.40 | −2.4% |
| GBM 54x50 | 2.700 | 100.58 | 71.38 | −20.3% |
| GBM 54x100 | 5.400 | 94.03 | 68.33 | −23.7% |
| GBM 54x400 | 21.600 | 92.96 | 67.97 | −24.1% |

**A presupuesto identico la ventaja casi desaparece** (−2.4%, no −24%). El 18 a
30 por ciento requiere unos 5.400 arboles. La afirmacion anterior atribuia a la
forma lo que en parte es presupuesto, y se corrige.

**Lo que sobrevive es mas fuerte que la limitacion que reemplaza:** el hurdle no
puede comprar la paridad. A 4.000 arboles EMPEORA. A presupuesto comparable
(2.700 contra 4.000) el GBM da 100.58 contra 141.07.

### El mecanismo, verificado

Al agrandar el hurdle su dispersion BAJA (sigma 1.7016 a 1.6641) y sus intervalos
se ENSANCHAN 292 MWh. La causa no puede ser sigma. Es el cuantil conformal, que
pasa de 0.9242 a 0.9532; cruzando los componentes, sustituir solo mu lo lleva a
0.9512, el **93% del desplazamiento**, y sustituir solo sigma a 0.9270.

Un primer intento de esta descomposicion fijaba el cuantil conformal y daba el
signo contrario. Estaba mal planteado: al fijar q se elimina el mecanismo. Queda
anotado porque el resultado correcto se obtuvo solo despues de detectarlo.

Es la contraparte experimental de lo que el manuscrito ya reporta del modelo con
sigma(x): el problema esta en la localizacion, no en la dispersion. Alli venia de
un modelo que mejoraba la dispersion y no ayudaba; aqui, de uno que la mejora y
perjudica.

---

## H7. Alinear el generador cambio el resultado de la ablacion del shrinkage

**Estado:** confirmado. **Fase:** 5 de esta tanda.
**Afirmacion afectada:** "el shrinkage de cola no aporta nada medible", en la
introduccion, en 5.5 y en la carta.

**Origen.** Al reconciliar el $+27$ de la Tabla 9 con el $+29.3$ de la Tabla 8 se
descubrio que la causa no era la convencion del delta, que estaba bien, sino que
`fase2_ablaciones.py` y `fase4_metricas_benchmarks.py` creaban generadores
frescos para el transporte en vez de continuar el que aleatorizo el score.
Ninguno de los dos reproducia la corrida canonica:

| | ancho test completo | % infinitos | IS finito |
|---|---|---|---|
| Canonica (Tablas 3 a 5, Fig. 7) | 595.9 | 5.9 | 1029.9 |
| Tabla 8, antes | 593.4 | 6.1 | 1028.2 |
| Tabla 9, antes | 591.4 | 6.1 | 1026.1 |
| **las tres, ahora** | **595.9** | **5.9** | **1029.9** |

**Lo que cambio.** El grupo A4 de la ablacion es el metodo del manuscrito, asi
que tenia que ser el mismo objeto. Al alinearlo:

| Componente | Antes | Ahora |
|---|---|---|
| Adaptacion online (A1 − A0) | −37.8 [−60, −10], si | sin cambio |
| Transporte sobre ACI (A3 − A1) | +74.2 [+47, +105], si | sin cambio |
| **Shrinkage de cola (A4 − A3)** | **−0.3 [−3, +2], NO significativo** | **-6.5 [-10, -3], SI significativo** |
| Pipeline completo (A4 − A0) | +29.3 [−8, +72], no | +32.4 [−5, +75], no |

El shrinkage pasa de "nada medible" a un aporte pequeno pero detectable. En
2025-S2 cambia de signo, de +6.3 (peor) a −12.4 (mejor).

**La conclusion cualitativa no cambia:** 6.5 MWh sobre un interval score
de unos 1.030 es el 0.6%, por el 91% del tiempo de computo. Pero la redaccion
anterior era incorrecta y se corrigio en los tres sitios: "no aporta nada
medible" pasa a "no se paga a si mismo".

---

## H8. El quiebre del diagnostico existe pero la forma no esta determinada

**Estado:** confirmado. **Fase:** 0c.
**No contradice ninguna conclusion:** refuerza la decision, ya tomada, de no
enunciar el diagnostico de forma simetrica.

**Comando:** `<venv>/bin/python flagship/revision/fase0c_robustez_quiebre.py`

La sospecha era que el quiebre lo sostuviera el brazo de menor capacidad, que
aporta 5 de las 15 celdas bajo el nominal y 3 de las 4 por debajo de −2 pp.
No lo sostiene:

- Quitandolo el salto CRECE, de -11.80 a -13.59, y F sube de 12.982 a 15.608.
- Dejar cualquier brazo fuera deja el salto entre -10.63 y -13.59.
- Con efecto fijo por modelo base, que identifica el quiebre solo con variacion
  dentro de brazo, queda en -11.48 con F(1,30) = 9.405.

**Pero la forma funcional no esta determinada, y eso es lo que decide la
redaccion.** Ajustando sin el brazo extremo y prediciendolo fuera de muestra, la
especificacion con quiebre acierta su celda mas extrema casi exacto (+54.2 contra
+55.7 observado, donde la recta unica da +43.0) pero es peor en las otras
cuatro, y el RMSE fuera de muestra queda empatado, 8.85 contra 8.82. Un termino
cuadratico cuenta lo mismo desde el otro lado: es indistinguible de cero sobre
las cuarenta celdas (p = 0.71) y fuertemente significativo sobre las treinta y
cinco (F(1,32) = 27.9).

Un diseno cuya forma funcional preferida cambia al quitar un brazo no determina
esa forma. Es una razon mas fuerte para no generalizar que el estadistico del
quiebre por si solo, y asi se escribio en 5.3.

**Advertencia declarada en el manuscrito:** estos test F tratan las cuarenta
celdas como independientes, y no lo son. Los p son optimistas y se reportan solo
como razon para NO ampliar la afirmacion, direccion en la que un p optimista es
conservador.

---

## H9. El modelo base del paper no es el mejor hurdle disponible

**Estado:** confirmado. **Fase:** cierre.
**Afirmacion afectada:** la concesion escrita en 5.4 y en la Seccion 7 de que la
detencion temprana "plausiblemente devolveria al hurdle a su rendimiento de 800
arboles". Se midio y es falsa por el lado bueno: lo supera.

**Comando:**
`<venv>/bin/python flagship/revision/verificacion/obj1d_hurdle_deteccion_temprana.py`

**Protocolo.** Los ultimos seis meses del periodo de entrenamiento se apartan
como validacion temporal; cada etapa del hurdle se ajusta con techo de 4.000
arboles y paciencia de 50; con el presupuesto elegido se reajusta sobre el train
completo. Ningun modelo ve datos posteriores a 2023-12-31.

| Modelo | Arboles | sigma | CRPS transicion | CRPS test |
|---|---|---|---|---|
| hurdle_400, el del paper | 800 | 1.7016 | 133.52 | 89.52 |
| hurdle_2000 | 4000 | 1.6641 | 141.07 | 95.46 |
| **hurdle con detencion temprana** | **105** (59+46) | 1.8274 | **124.03** | **84.38** |

La detencion temprana elige 105 arboles, **un octavo** del presupuesto del modelo
base del paper, y mejora su CRPS en 5.7%. La dispersion sube de
1.7016 a 1.8274, que es lo esperable cuando un mu menos sobreajustado deja
mas variacion en el residuo.

**Lo que cambia.** El modelo base oficial del paper no es el mejor hurdle
disponible en este problema, y los niveles que se reportan para el deben leerse
con ese descuento. Se declara en 5.4 y en la Seccion 7.

**Lo que no cambia.** El orden contra la forma cuantilica se mantiene con margen:
el hurdle detenido da 124.03 en la transicion contra 92.92 del GBM
multi-cuantil, todavia 33% por detras. Y el diagnostico es un contraste
dentro de cada brazo, asi que no lo toca.

**Lectura adicional.** La forma hurdle satura muy temprano en este problema, en
torno a los cien arboles. Ni anadir presupuesto ni gastarlo con mas cuidado
cierra la brecha con la forma cuantilica, que es un enunciado mas fuerte que el
que habia.

## H10. El orden puntual de la Tabla 2 no es artefacto del hurdle elegido

**Estado:** confirmado. **Fase:** cierre. **Consecuencia de:** H9.

**Afirmacion afectada:** ninguna se cae. H9 declaro que el hurdle del paper no es
el mejor disponible y que sus niveles cargan un descuento. La pregunta abierta
era si ese descuento alcanzaba a la Tabla 2, es decir, si el naive estacional le
gana al hurdle solo porque ajustamos un hurdle malo.

**Comando:**
`<venv>/bin/python flagship/revision/verificacion/obj1e_mae_hurdle_es.py`

**Protocolo.** Se generan las predicciones puntuales del hurdle con detencion
temprana (105 arboles, el de H9) sobre exactamente las mismas 104.420 filas y el
mismo periodo fuera de muestra de la Tabla 2, y se toma la mediana de la mixtura
igual que para el hurdle oficial. El script **aborta** si antes no reproduce la
fila oficial del hurdle celda por celda; el control paso con desvio maximo de
0.005 MWh sobre la particion anual 40.549 / 44.725 / 19.146.

| Fila | 2024 | 2025 | 2026 | Total |
|---|---|---|---|---|
| Naive estacional (semanal) | 84.3 | 86.3 | 84.2 | **85.1** |
| Hurdle oficial (mediana de la mixtura) | 104.4 | 104.8 | 101.6 | 104.1 |
| **Hurdle con detencion temprana** | 110.1 | 108.8 | 104.6 | **108.6** |

**Lo que cambia.** El hurdle detenido empeora el MAE en 4.3% respecto del
oficial y queda **ultimo** entre las siete filas, 27.6% por detras del naive
estacional. El orden de la Tabla 2 no depende del hurdle que ajustamos: el naive
sigue ganando con el mejor hurdle que sabemos ajustar en este problema. La Tabla
2 queda por eso **explicitamente fuera** de la lista de descuento de la Seccion
7, porque el descuento tiene direccion incorporada ("nuestros niveles serian
mejores con un hurdle mejor") y aqui la direccion es la contraria.

**Lectura adicional.** Es una instancia medida de dependencia del criterio, no una
anomalia: el mismo par de ajustes se ordena en un sentido por CRPS (el detenido
mejora 5.7%) y en el sentido opuesto por MAE (empeora 4.3%). Es lo esperable
cuando el ajuste detenido es la predictiva mas ancha y mejor calibrada, porque su
mediana condicional se aleja del valor realizado. La Seccion 5.1 ya conjeturaba
que un criterio distinto del MAE podria ordenar estos modelos de otro modo; esto
lo convierte de hipotetico en medido, y es donde vive el contenido.

**Lo que no cambia.** No se agrega fila a la Tabla 2: se reporta en prosa, igual
que la escalera de capacidad en 5.4. Ni el diagnostico ni la comparacion contra
la forma cuantilica se tocan.

## H11. La Tabla C.13 esta truncada y se lleva las cuatro filas de semillas

**Estado:** confirmado. **Fase:** auditoria de la version marcada, pagina por
pagina. **No es un defecto del marcado: esta en el manuscrito limpio.**

**Afirmacion afectada:** el Apendice C dice que "Table C.13 lists every constant
of the pipeline" y que se genera desde el codigo "so that it cannot drift from
the implementation". La tabla se genera bien; lo que falla es que no cabe.

**Comando:** `grep "Float too large for page" build/SEGAN_paper_FINAL.log`

**Lo que pasa.** `hiperparametros.tex` produce un `table*` con 38 filas cuyo
`tabular` es mas alto que la caja de texto. Un flotante no se parte entre
paginas, asi que LaTeX imprime lo que cabe y **descarta el resto en silencio**:
no hay error, el PDF se produce, y el unico rastro es un aviso en el log,
`Float too large for page by 173.5222pt on input line 62`. En el PDF el numero
de pagina queda encima de una fila de la tabla, que es la senal visible.

**Lo que se pierde.** De las 38 filas de la fuente, 4 no llegan al PDF, y son
justo las del bloque de semillas. El encabezado `Semillas` si se imprime, al pie
de la pagina, y debajo no hay nada:

| Fila de la fuente que no aparece | Valor |
|---|---|
| Entrenamiento de los modelos base | 42 |
| Aleatorizacion del atomo PIT y bootstrap del mapa | 20260720 |
| Muestreo del CRPS | 11 |
| Bootstrap de diferencias, bloques y permutaciones | 20260901 |

**Por que importa, y por que menos de lo que se dijo primero.** Las semillas
nunca faltaron del manuscrito: el Apendice D las enuncia en prosa ("The seeds
are 42 for base-model training, 20260720 for the randomisation of the PIT atom
and the bootstrap of the transport map, 11 for the CRPS sampling and 20260901
for the day-block bootstrap and the permutation nulls"), y ese parrafo si se
imprimia en el PDF de 35 paginas. La Regla 4 se cumplia.

Lo que fallaba era la tabla, y con ella una remision de la carta. El Apendice C
dice que la Tabla C.13 "lists every constant of the pipeline", y la carta, en la
respuesta a R1.2, remite a los revisores a "Appendix C, Table C.13, every
parameter and all four seeds". Con la tabla truncada esa remision era falsa: el
revisor que fuera a la tabla no encontraba las semillas. Con el arreglo de la
seccion 19 del changelog es cierta. El .tex con la tabla truncada viajaba ademas
dentro del zip de fuentes.

La version enviada en julio no tenia Apendice C ni Apendice D, ni semillas en
ninguna parte. No se perdieron ahi: no estaban.

*Correccion del 12 de septiembre de 2026.* La primera redaccion de este hallazgo
decia que las semillas no llegaban al PDF y que eso afectaba la Regla 4. Era
falso. Se verifico sobre el PDF de 35 paginas del commit 46ebfe0: el Apendice D
imprime las cuatro. Es tambien la razon por la que una guarda que buscaba los
valores desnudos no discriminaba (seccion 19 del changelog).

**Por que no lo detectaron los verificadores.** `verificar_manuscrito.py`
compara afirmaciones en prosa contra archivos de resultados y
`verificar_referencias_cruzadas.py` compara referencias contra el `.aux`.
Ninguno lee los avisos de maquetacion del log. Un numero puede estar correcto en
el `.tex`, verificar, y no llegar a imprimirse.

**Guarda nueva.** `empaquetar_fuentes.sh` ahora falla con estado distinto de
cero si el log trae `Float too large for page`, e imprime el aviso. Con eso el
paquete de fuentes queda **bloqueado** hasta que se decida el arreglo.

**Arreglo, pendiente de decision del autor.** No se toco: cambiarlo modifica el
manuscrito, que estaba excluido del encargo, y mueve el numero de paginas. La
salida natural es que `fase9_tablas_tex.py` emita esa tabla como `longtable`, que
si se parte entre paginas, o que la parta en dos `table*`. Cualquiera de las dos
cambia el conteo de 35 paginas.
