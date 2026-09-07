# Verificacion independiente del resultado central de SEGAN-D-26-03850

**Objeto.** Reproducir a ciegas la Fase 0 (agnosticismo al modelo base) y evaluar
tres objeciones previsibles en segunda ronda.

**Veredicto en una frase.** El resultado se reproduce **exactamente**, hasta el
ultimo decimal publicado, en un clon limpio con un entorno reconstruido; el
diagnostico sobrevive con holgura a la incertidumbre que el paper no reportaba; y
de las tres objeciones, **una tiene fuerza real y obliga a corregir una
afirmacion del manuscrito**, aunque no la conclusion.

---

## 0. Alcance y limite de esta verificacion

Lo que es genuinamente independiente: el clon limpio, el entorno reconstruido
desde cero, la re-ejecucion mecanica, la validacion de los datos contra los
checksums versionados, y el contraste contra el PDF compilado.

Lo que **no** lo es: quien verifica tuvo exposicion previa a los valores
esperados. La ceguera del paso 4 es procedimental (los numeros se escribieron
antes de abrir nada), no cognitiva. Una verificacion realmente ciega la tendria
que hacer un tercero sin ese contexto. Se declara para que se pondere en
consecuencia.

---

## 1. Procedencia

```
git clone --branch revision/reframing <repo> && commit 123ee6a
arbol limpio, sin modificaciones
```

**Los datos no vienen en el clon.** `release/v1.0/` esta en `.gitignore` y vive
en Zenodo. El README lo documenta como paso 1 del procedimiento de
reproduccion, asi que no es un descuido, pero **un verificador necesita una
descarga externa antes de poder ejecutar nada de la Fase 0**. Los archivos se
tomaron de una copia local y se validaron contra `release/v1.0/CHECKSUMS.sha256`,
que si esta versionado en el clon: **10 de 10 archivos OK, 0 fallidos.** La
cadena de integridad se sostiene sin confiar en la copia.

## 2. Entorno: declarado contra efectivo

Construido con `conda env create -f environment.yml`. Cuatro de cinco paquetes
quedaron en una version distinta de la declarada en el README:

| Paquete | Declarado | Efectivo | |
|---|---|---|---|
| python | 3.12.3 | 3.12.12 | difiere |
| pandas | 3.0.3 | 3.0.0 | difiere |
| numpy | 2.4.6 | 2.4.2 | difiere |
| scikit-learn | 1.9.0 | 1.8.0 | **difiere en version menor** |
| xgboost | 3.2.0 | 3.2.0 | igual |

`environment.yml` no fija versiones, solo nombres de paquete, asi que el entorno
reconstruido no es el de referencia y no puede serlo. Que aun asi reproduzca es
un resultado, no una obviedad. **Recomendacion:** publicar un `environment.lock`
o congelar las versiones en el `.yml`, porque hoy la reproducibilidad exacta
depende de que el solver resuelva igual, y no lo hara indefinidamente.

## 3. Reproduccion

### 3.1 Entrenamiento del modelo base alternativo

`fase0_entrenar_qgbm.py` produjo un `pred_qgbm_multi.csv.gz` **identico bit a
bit** al versionado en el repo:

```
sha256 mio:  b46f70b15435c478b29f3e1e0843bd4a3a1f543b51a9822ca25bcb5262df6e37
sha256 repo: b46f70b15435c478b29f3e1e0843bd4a3a1f543b51a9822ca25bcb5262df6e37
0 celdas distintas de 5.638.680
```

Reproduccion exacta pese a las diferencias de version, porque la ruta de
entrenamiento solo depende de xgboost, que si coincide, y de operaciones
deterministas de pandas.

### 3.2 Mis numeros, registrados antes de comparar

En `verificacion_independiente/paso4_mis_numeros.md`. Resumen:

- **r de Pearson = −0.756730, pendiente = −4.386020, intercepto = +5.486406**
- Diferencias de ancho en la transicion, Transporte+ACI(0.05) menos estatico:
  hurdle **−396.1** MWh [−462.8, −333.1]; sigma(x) **−36.8** [−96.7, +25.9];
  GBM **+15.1** [+0.0, +30.3]
- Tabla de 18 filas (3 modelos x 6 metodos) en la ventana de transicion

### 3.3 Comparacion contra lo versionado y contra el manuscrito

| Comparacion | Resultado |
|---|---|
| `fase0_tabla_por_modelo.csv` | idéntico salvo la columna `segundos` (reloj), max 1.3 s |
| `fase0_diagnostico.csv` | **idéntico**, 15 filas x 12 columnas |
| `fase0_diferencias_bootstrap.csv` | **idéntico**, 60 filas x 14 columnas |
| Tabla 4 del PDF | **108 celdas comparadas, 0 discrepancias** |
| Tabla 5 del PDF | **60 celdas comparadas, 0 discrepancias** |
| Figura 7 del PDF | 9 anotaciones y la recta ajustada, todas coincidentes |

**Una sola discrepancia, y es de redondeo declarable.** El r publicado se
calcula sobre el CSV de diagnostico, cuyas entradas vienen redondeadas a un
decimal. Sobre los arrays sin redondear:

| | r | pendiente | intercepto |
|---|---|---|---|
| publicado, entradas redondeadas | −0.7567 | −4.3860 | +5.4864 |
| desde los arrays crudos | −0.7547 | −4.3647 | +5.4487 |
| diferencia | 0.0020 | 0.0213 | 0.0377 |

Inmaterial para toda conclusion, pero es la unica diferencia numerica que
encontre y queda anotada porque se pidieron todas.

---

## 4. Objecion 1, capacidad contra forma: **TIENE FUERZA, y obliga a corregir**

El manuscrito ya declara la limitacion (Seccion 7) y dice que el diseno no puede
separar forma de capacidad. **Puede.** Cuesta unos 25 minutos de computo y lo
corri.

### Escalera de capacidad, rejilla fija de 54 niveles

| Modelo | Arboles | CRPS transicion | CRPS test | Cobertura estatica |
|---|---|---|---|---|
| Hurdle (referencia) | 800 | 133.52 | 89.52 | 92.5% |
| Hurdle x5 | 4000 | **141.07** | **95.46** | 92.1% |
| GBM 54 x 15 | 810 | 131.18 | 87.40 | 87.0% |
| GBM 54 x 50 | 2700 | 100.58 | 71.38 | 89.4% |
| GBM 54 x 100 | 5400 | 94.03 | 68.33 | 90.1% |
| GBM 54 x 200 | 10800 | 92.77 | 67.84 | 90.2% |
| GBM 54 x 400 (el del paper) | 21600 | 92.96 | 67.97 | 90.2% |

### Lo que dice

1. **A presupuesto estrictamente igualado (810 contra 800 arboles), la ventaja
   del GBM casi desaparece: −1.8% de CRPS en la transicion, no −30.4%.** La cifra
   de 18 a 30 por ciento que el manuscrito reporta **no sobrevive** al
   igualamiento estricto. La objecion acierta en esto.

2. **Pero el hurdle no puede comprar la paridad con capacidad: a 4000 arboles
   EMPEORA** (CRPS 89.52 a 95.46 en el test, +6.6%). Sobreajusta el regimen de
   2023. El deficit del hurdle no es de presupuesto.

3. **La ventaja satura hacia los 5400 arboles.** A 2700, un presupuesto del mismo
   orden que los 4000 del hurdle agrandado, el GBM ya da 100.58 contra 141.07:
   una ventaja del 29%. Es decir, **a presupuesto comparable la dominacion se
   mantiene**; solo se pierde en el punto exacto de 800 arboles, donde 54 cabezas
   cuantilicas se quedan con 15 arboles cada una y el modelo esta hambreado.

### Veredicto

La afirmacion de dominacion tal como esta escrita ("CRPS 18 a 30 por ciento mas
bajo", junto a "misma disciplina") **es enganosa y hay que corregirla**: mezcla
un efecto de forma con uno de capacidad y no distingue cual es cual.

La correccion no es retirar la afirmacion, es **reemplazar la limitacion por el
experimento**. Lo que se sostiene, y es mas fuerte que lo que hay ahora, es: la
forma multi-cuantil convierte capacidad en exactitud predictiva en este problema
y la forma hurdle no; a presupuesto comparable la ventaja es de alrededor del
30%; a presupuesto identico se anula porque el GBM queda sin arboles por cabeza.

**Nota tecnica.** Un cuarto brazo que corri, GBM de rejilla gruesa (9 niveles x
400), **hay que descartarlo para comparar CRPS**: al muestrear de una rejilla
truncada en tau = 0.9 toda la masa superior colapsa al cuantil 0.9 y el CRPS sale
sesgado a la baja. Su split estatico ademas devuelve 100% de intervalos
infinitos, porque el cuantil conformal (0.938) cae por encima del nivel maximo de
la rejilla. Es una confirmacion mecanica del limite que la Seccion 7 ya declara.

---

## 5. Objecion 2, la incertidumbre del diagnostico: **SOBREVIVE, con una salvedad**

### Esquema de remuestreo que corresponde

Las 15 celdas son un diseno **cruzado**, no anidado: las cinco de un modelo base
comparten la predictiva ajustada, y las tres de una ventana comparten los mismos
dias y desenlaces. Remuestrear celdas, modelos o ventanas seria incorrecto, y con
3 y 5 niveles no hay material para hacerlo.

La aleatoriedad comun esta en los **dias**: toda celda se calcula sobre el mismo
panel. El esquema correcto es remuestrear **dias completos una sola vez por
replica y recomputar las quince celdas sobre ese mismo remuestreo**, reajustando
la recta. Asi la dependencia cruzada queda preservada por construccion. Es el
mismo esquema que el paper ya usa para las diferencias de ancho, elevado al nivel
del ajuste.

Condiciona sobre los modelos ajustados y sobre la trayectoria secuencial de los
metodos online, que no se pueden re-correr sobre dias barajados. Es incertidumbre
de evaluacion, no de entrenamiento. Se declara.

### Resultado, 2000 replicas

| | Punto | IC 95% | |
|---|---|---|---|
| r de Pearson | −0.7547 | **[−0.8760, −0.4286]** | excluye el cero |
| Pendiente | −4.3647 | **[−6.0806, −2.2817]** | excluye el cero |
| Intercepto | +5.4487 | **[+0.0659, +11.2522]** | excluye el cero **por muy poco** |

### Robustez

- **Dejar una celda fuera:** r se mueve entre −0.8122 y −0.6756. La celda mas
  influyente es hurdle/transicion; al quitarla r sigue en −0.68.
- **Dejar un modelo base fuera**, que es la pregunta dura, porque el hurdle aporta
  el punto extremo:

| Se quita | n | r | pendiente | intercepto |
|---|---|---|---|---|
| hurdle | 10 | **−0.6714** | −3.124 | +6.848 |
| hurdle sigma(x) | 10 | −0.8252 | −4.744 | +4.214 |
| GBM | 10 | −0.7221 | −4.472 | +4.920 |

**Sin el hurdle la relacion se mantiene en r = −0.67.** No la sostiene el brazo
extremo.

### Salvedad, y es la unica de esta seccion

**El intercepto apenas excluye el cero: [+0.066, +11.25].** La afirmacion del
abstract y de la Seccion 5.3 de que "cuando el split ya esta en nominal,
Transport+ACI ensancha un 5.49%" esta al filo. El signo y la magnitud del
**diagnostico** (r y pendiente) sobreviven con holgura; **la lectura puntual del
intercepto, no.**

**Recomendacion:** reportar los tres intervalos, y enunciar el intercepto con el
suyo en lugar de como cifra puntual. Es un cambio de una frase que cierra la
inconsistencia que el revisor iba a senalar, y el paper no pierde nada: el
resultado que sostiene la conclusion es la pendiente.

### Prueba adicional, fuera de muestra

Las 15 celdas del paper solo cubren sobre-cobertura en [−2.0, +5.3] pp. El brazo
de capacidad equiparada de la Objecion 1 cae en **−8.5 pp**, muy por fuera:

| Celda | x observado | y observado | y predicho por la recta | residuo |
|---|---|---|---|---|
| GBM 54x15, transicion | −8.5 | +55.7% | +42.8% | +12.9 |
| GBM 54x15, test completo | −3.0 | +25.3% | +18.6% | +6.7 |

La relacion **extrapola en el signo y en el orden de magnitud** a una region que
no se uso para ajustarla. Es evidencia a favor del diagnostico que el paper no
tiene y podria incorporar.

---

## 6. Objecion 3, el control de reproduccion: **la objecion es correcta**

### Que controla la asercion existente, y que no

```python
if nombre == 'hurdle':
    verificar_reproduccion(tabla)
```

Se dispara **solo en el brazo del hurdle**. Ese brazo recorre
`PredictivaHurdle`, que delega en las funciones ya validadas de
`conformal_metodos.py`. El brazo del GBM recorre `PredictivaCuantilica`, una
clase **nueva**, con su propia interpolacion de rejilla, su propia lectura del
atomo en cero y su propio manejo de bordes.

**Un error en esa clase dejaria intacta la asercion y produciria en silencio
justo el resultado que es el titular del paper.** La objecion tiene razon: el
control es asimetrico, valida el protocolo compartido y no la predictiva nueva.

### El control que anadiria, y que corri

**C3, equivalencia con una predictiva conocida.** Se construye una
`PredictivaCuantilica` evaluando la funcion cuantil **del hurdle** sobre los
mismos 54 niveles. Salvo error de interpolacion, esa predictiva *es* el hurdle.
Se corre la capa conformal completa sobre ella y se compara contra el brazo del
hurdle ya validado. Si la clase nueva tiene un error, esto falla.

| Ventana | Cobertura hurdle | Cobertura cuantilica | dif | Ancho hurdle | Ancho cuantilica | dif |
|---|---|---|---|---|---|---|
| test_pre | 93.5 | 93.4 | −0.10 | 799.1 | 794.5 | −0.58% |
| test_transition | 95.3 | 95.3 | +0.00 | 1203.3 | 1196.4 | −0.57% |
| 2025-S1 | 89.4 | 89.4 | +0.00 | 454.8 | 452.1 | −0.59% |
| 2025-S2 | 94.0 | 93.9 | −0.10 | 750.1 | 745.7 | −0.59% |
| 2026-S1 | 92.5 | 92.4 | −0.10 | 534.9 | 531.8 | −0.58% |

**Pasa.** Desvio maximo 0.10 pp de cobertura y 0.59% de ancho, y el sesgo de
ancho es constante y negativo en las cinco ventanas, que es la firma esperable de
discretizar una funcion cuantil continua en 54 niveles. **No hay error detectable
en el brazo nuevo.**

Ademas, C1 (invariantes e ida y vuelta): las seis comprobaciones pasan, con error
maximo de ida y vuelta de 1.3e-13.

### Un falso positivo mio, que anoto por transparencia

C2 comprobaba la cobertura de la predictiva **cruda** y la marque como
sospechosa: el cuantil 0.7 del GBM cubre 61.6% en vez de 70%. Antes de reportarlo
compare contra los otros dos modelos:

| tau | hurdle | hurdle sigma(x) | GBM |
|---|---|---|---|
| 0.5 | 36.13 (−13.87) | 36.20 (−13.80) | 43.32 (−6.68) |
| 0.7 | 56.03 (−13.97) | 53.55 (−16.45) | 61.61 (−8.39) |
| 0.9 | 86.65 (−3.35) | 84.86 (−5.14) | 84.83 (−5.17) |

**El hurdle sub-cubre mas que el GBM.** Es el desplazamiento de regimen entre el
entrenamiento (hasta 2023) y la calibracion (2024), no un error de indice. Mi
umbral de 8 pp estaba mal puesto. **El GBM es el mejor calibrado de los tres en
crudo**, lo que por lo demas es coherente con la tesis del paper.

### Recomendacion

Anadir C3 al script como asercion permanente, junto a la del hurdle. Cuesta
menos de un minuto de ejecucion y cierra exactamente el hueco que la objecion
senala.

---

## 7. Juicio final

**El resultado se sostiene.** La reproduccion es exacta hasta el ultimo decimal
publicado en las tres tablas y la figura, con un entorno distinto del de
referencia. El diagnostico, que es la contribucion reencuadrada, sobrevive a un
esquema de remuestreo que respeta la dependencia cruzada del diseno, sobrevive a
dejar fuera cualquier celda, sobrevive a dejar fuera el brazo que aporta el punto
extremo, y extrapola correctamente a una region que no se uso para ajustarlo. El
brazo nuevo pasa un control de equivalencia que no existia.

**Tres cosas hay que arreglar antes de enviar, ninguna toca la conclusion:**

1. **La afirmacion de dominacion del GBM (prioridad alta).** Como esta escrita
   mezcla forma con capacidad. A presupuesto identico la ventaja de CRPS cae de
   30% a 1.8%. Correcion: reemplazar el parrafo de limitacion por la escalera de
   capacidad, que ademas es un resultado mas fuerte, porque muestra que el hurdle
   empeora al recibir mas presupuesto.

2. **El intercepto del diagnostico (prioridad media).** Enunciarlo con su
   intervalo [+0.07, +11.25], no como cifra puntual. El r y la pendiente van con
   los suyos y quedan holgados.

3. **El control del brazo nuevo (prioridad media).** Anadir la asercion de
   equivalencia C3.

Y dos de higiene: fijar versiones en `environment.yml`, y decir en el README de
la Fase 0 que hace falta bajar los datos de Zenodo antes de poder correrla.

**No encontre nada que invalide el resultado central ni que justifique retirar el
reencuadre.**
