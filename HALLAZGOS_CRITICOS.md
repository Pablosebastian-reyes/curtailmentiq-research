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
