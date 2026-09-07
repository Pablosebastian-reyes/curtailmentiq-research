# CHANGELOG_REVISION — SEGAN-D-26-03850

Todo cambio de la revision mayor, con el comando que lo reproduce.

**Rama:** `revision/reframing`
**Entorno:** `$VENV = /Users/pabloreyescerda/Desktop/PROYECTO-CURLTAIMENT/curtailmentiq-model/venv/bin/python`
python 3.12.3, pandas 3.0.3, numpy 2.4.6, scikit-learn 1.9.0, xgboost 3.2.0,
ruptures 1.1.10, statsmodels 0.15.0. LaTeX: TinyTeX (TeX Live 2026).
**Semillas:** 42 (entrenamiento), 20260720 (atomo PIT y bootstrap del mapa),
11 (CRPS), 20260901 (bootstrap por bloques de dia y nulos de permutacion).

Las dependencias nuevas de la revision son `ruptures` y `statsmodels`, ambas
solo para la Fase 6, y estan declaradas en `environment.yml`.

---

## 0. Preservacion de la version enviada

Antes de tocar nada se congelaron los resultados de la version enviada y se
verifico que el entorno los reproduce bit a bit.

```
mkdir -p resultados/v_enviada
cp flagship/conformal_v3_tabla.csv flagship/conformal_v3_salida.txt \
   flagship/conformal_v3_hallazgos.txt flagship/conformal_v3_hetero_comparacion.csv \
   flagship/conformal_v2_tabla.csv flagship/conformal_v2_cierre_tabla.csv \
   flagship/entrenar_hurdle_hetero_salida.txt resultados/v_enviada/
$VENV flagship/conformal_v3_real.py
git diff --stat flagship/conformal_v3_tabla.csv      # sin diferencias
```

Ningun script de la revision escribe sobre `resultados/v_enviada/`.

---

## 1. Codigo nuevo

| Archivo | Que hace | Comentario que responde |
|---|---|---|
| `flagship/revision/rev_lib.py` | Generaliza la capa conformal a una interfaz de predictiva con dos operaciones, `cdf(y)` e `inv(q)`. Implementa `PredictivaHurdle` y `PredictivaCuantilica`, el interval score unilateral, el bootstrap por bloques de dia y la cota de alpha | R1.1, R1.5, R2.5, R2.6 |
| `flagship/revision/fase0_entrenar_qgbm.py` | Entrena el GBM multi-cuantil de 54 niveles con disciplina identica al hurdle. Escribe `pred_qgbm_multi.csv.gz` | R1.1 |
| `flagship/revision/fase0_model_agnostic.py` | Corre el protocolo conformal completo sobre tres modelos base; verifica por asercion que la rama del hurdle reproduce la tabla enviada | R1.1 |
| `flagship/revision/fase0_diagnostico.py` | Cuantifica la relacion entre sobre-cobertura del split estatico y recorte de ancho | R1.1 |
| `flagship/revision/fase1_hiperparametros.py` | Lee las constantes del codigo fuente y emite la tabla de hiperparametros como float completo | R1.2, R2.4 |
| `flagship/revision/fase2_ablaciones.py` | Cinco grupos de ablacion con aporte marginal, IC bootstrap y costo en segundos | R1.3 |
| `flagship/revision/fase3_seleccion_hiperparametros.py` | Origen rodante dentro de la calibracion; sensibilidad 6x5 sobre el test como exhibicion | R1.4 |
| `flagship/revision/fase4_metricas_benchmarks.py` | Interval score, cota de alpha en cuatro niveles, cuatro benchmarks probabilisticos, IC de todas las diferencias | R1.5, R2.6 |
| `flagship/revision/fase5_dependencia_panel.py` | ICC y efecto de diseno; conformal por bloques, por grupos y por central; cobertura desagregada en cuatro ejes | R2.5 |
| `flagship/revision/fase6_cronologia.py` | Cronologia unica, 180 configuraciones de deteccion, W1 con IC y nulo, descomposicion estacional, seis fronteras alternativas y verificacion de 24 afirmaciones | R2.3 |
| `flagship/revision/fase8_buscar_referencias.py` | Busca y VERIFICA referencias contra Crossref; nada entra sin DOI resuelto | R2.1 |
| `flagship/revision/fase9_figuras_revision.py` | Figuras 4, 7 y 9 del manuscrito (el diagrama de flujo, la comparacion entre modelos base y el aporte por componente) | Q4, R1.2, R1.3 |
| `flagship/revision/fase9_tablas_tex.py` | Emite los diez floats de tabla desde los CSV de resultados | Regla Dura 1 |
| `flagship/revision/verificar_manuscrito.py` | Comprueba las 43 afirmaciones numericas en prosa del manuscrito contra su archivo de resultados | Regla Dura 1 |

`resultados/fase0_model_agnostic.md` se redacto a partir de los CSV de la Fase 0
en la misma corrida que los genera; sus cifras son las de
`fase0_tabla_por_modelo.csv`, `fase0_diagnostico.csv` y
`fase0_diferencias_bootstrap.csv`, y se pueden re-cotejar contra ellos.

---

## 2. Orden de ejecucion completo

```
$VENV flagship/revision/fase0_entrenar_qgbm.py             # ~8 min
$VENV flagship/revision/fase0_model_agnostic.py            # ~1 min
$VENV flagship/revision/fase0_diagnostico.py               # <1 s
$VENV flagship/revision/fase2_ablaciones.py                # ~30 s
$VENV flagship/revision/fase3_seleccion_hiperparametros.py # ~4 min
$VENV flagship/revision/fase4_metricas_benchmarks.py       # ~2 min
$VENV flagship/revision/fase5_dependencia_panel.py         # ~12 s
$VENV flagship/revision/fase6_cronologia.py                # ~2 min
$VENV flagship/revision/fase1_hiperparametros.py           # <1 s
$VENV flagship/revision/fase9_figuras_revision.py          # ~10 s
$VENV flagship/revision/fase9_tablas_tex.py                # ~5 s
$VENV flagship/revision/verificar_manuscrito.py            # ~2 s, debe dar 43/43
```

Compilacion:

```
mkdir -p build
cp flagship/segan/SEGAN_paper_FINAL.tex flagship/segan/response_to_reviewers.tex build/
cp flagship/segan/figuras/*.pdf resultados/tablas_tex/*.tex resultados/fase1/hiperparametros.tex build/
cd build
pdflatex SEGAN_paper_FINAL.tex     # x3, por las referencias cruzadas
pdflatex response_to_reviewers.tex # x2
```

---

## 3. Cambios en el codigo existente

**Renombre de `test_ramp` a `test_transition`** (comentario R2.2).

```
for f in flagship/conformal_metodos.py flagship/conformal_v2.py \
         flagship/conformal_v2_cierre.py flagship/conformal_prototype.py \
         flagship/conformal_v3_real.py flagship/conformal_v3_hetero.py \
         flagship/generar_figuras_paper.py flagship/ESPECIFICACION_TECNICA.md; do
  sed -i '' "s/test_ramp/test_transition/g" "$f"
done
sed -i '' "s/rampa BESS/ventana de transicion/g; s/quiebre BESS/cambio de regimen/g" flagship/*.py flagship/*.md
$VENV flagship/conformal_v3_real.py
$VENV flagship/conformal_v3_hetero.py
```

**Verificacion de que el renombre solo cambio etiquetas:**

```
$VENV -c "
import pandas as pd
a=pd.read_csv('flagship/conformal_v3_tabla.csv')
b=pd.read_csv('resultados/v_enviada/conformal_v3_tabla.csv')
b['periodo']=b.periodo.replace({'test_ramp':'test_transition'})
assert a.equals(b), 'el renombre cambio algun numero'
print('identico salvo la etiqueta')"
```

Resultado: identico. Lo mismo para `conformal_v3_hetero_comparacion.csv`.

Los documentos internos fechados (`AUDIT_METODOLOGICO.md`, `HANDOFF_KERVEN.md`)
**no se reescriben**, porque son registro de lo que se penso en su momento. Se
les anadio una nota de nomenclatura al inicio.

**Corrección de la penalizacion de los puntos de cambio.** La bitacora interna
describia la penalizacion como `3*sigma^2*log n`; con ese factor solo se detecta
2023-05. La penalizacion BIC estandar `sigma^2*log n` devuelve los dos puntos de
cambio publicados con los saltos publicados. El resultado publicado era correcto;
la descripcion interna no. Corregido en `fase6_cronologia.py:puntos_de_cambio`
y declarado en el manuscrito.

---

## 4. Cambios en el manuscrito

`flagship/segan/SEGAN_paper_FINAL.tex`, version 6.0 a 7.0. De 375 a 987 lineas.

| Cambio | Comentario | Ubicacion |
|---|---|---|
| Titulo de 26 a 13 palabras, sin el pais; el sistema pasa al abstract | Nota editorial | frontmatter |
| Abstract reescrito: el hallazgo diagnostico, los tres regimenes de garantia, la afirmacion del pronostico puntual acotada | R1.1, R2.7 | abstract |
| Seccion 2 reescrita en cuatro subsecciones, sin citas agrupadas | R2.1, nota del editor | \S2 |
| Seis afirmaciones descriptivas corregidas | auditoria propia | \S3.3 |
| Cronologia unica, 180 configuraciones de robustez, penalizacion declarada | R2.3 | \S3.4 |
| Tres modelos base descritos | R1.1 | \S4.1 |
| Subseccion nueva: los tres regimenes de garantia, con ICC y efecto de diseno | R2.5, R2.7 | \S4.3 |
| Subseccion nueva: el algoritmo en detalle, con los siete items pedidos | R1.2 | \S4.5 |
| Subseccion nueva: que es nuevo y que viene de la literatura | R2.4 | \S4.5 |
| Subseccion nueva: seleccion por origen rodante | R1.4 | \S4.6 |
| Metricas: interval score unilateral y tratamiento de los infinitos | R1.5 | \S4.7 |
| Alcance del resultado del pronostico puntual | R2.7 | \S5.1 |
| **Subseccion nueva: el agnosticismo al modelo base** | R1.1 | \S5.3 |
| Subseccion nueva: ablaciones | R1.3 | \S5.5 |
| Subseccion nueva: benchmarks, metricas e infinitos | R1.5, R2.6 | \S5.6 |
| Subseccion nueva: dependencia de panel y cobertura condicional | R2.5 | \S5.7 |
| Subseccion nueva: sensibilidad de la frontera | R2.3 | \S5.8 |
| Discusion reescrita alrededor del diagnostico | R1.1, Q5 | \S6 |
| **Seccion nueva de limitaciones, diez items** | Q7 | \S7 |
| Conclusion reescrita | R1.1, R2.7, Q5 | \S8 |
| Apendice C nuevo: hiperparametros; apendice D nuevo: reproducibilidad | R1.2, R2.4 | apendices |
| Bibliografia de 10 a 43 entradas, todas con DOI verificado | R2.1 | bibliografia |
| Algoritmo 1 y figuras 4, 7 y 8 nuevas | R1.2, R1.3, Q4 | varias |
| Diez de las doce tablas se generan desde CSV por `\input` | Regla Dura 1 | varias |

**Nota tecnica de LaTeX.** Las tablas se incluyen como floats completos y no como
cuerpos, porque TeX no acepta un `\input` cuyo primer token sea `\multicolumn`
dentro de un `tabular`: al empezar la celda inserta la plantilla antes de
ejecutar el `\input` y `\omit` queda fuera de lugar.

---

## 5. Numeros corregidos durante la revision

Detectados por `verificar_manuscrito.py` sobre un borrador y corregidos:

| Afirmacion | Borrador | Corregido |
|---|---|---|
| IC de la diferencia de ancho con el GBM multi-cuantil | $[-1.0,+29.0]$, compatible con cero | $+15.1$, IC $[+0.0,+30.3]$, que apenas excluye el cero; el IC del interval score, $+13.9$ $[-10.7,+37.8]$, si lo contiene |
| Costo de cobertura de la cota de alpha | a lo mas 0.4 puntos | a lo mas medio punto (0.5) |
| Lectura del IC en `resultados/fase0_model_agnostic.md` | "contiene el cero" | "apenas excluye el cero por el lado equivocado"; el IC del interval score si lo contiene |

**Ademas, alineamiento de la penalizacion de la figura de puntos de cambio (Fig. 3).**
`generar_figuras_paper.py` calculaba los puntos de cambio con un estimador
robusto del ruido y un factor 3; devolvia los mismos dos quiebres, pero la
especificacion no coincidia con la declarada en el manuscrito. Ahora usa la
misma convencion BIC que `fase6_cronologia.py`, `pen = sigma^2 log n` con
`sigma^2` la varianza de la serie. Reproducir:

```
$VENV flagship/generar_figuras_paper.py
# figura de puntos de cambio: quiebres ['2023-05', '2024-01'], penalizacion 3.0269
```

El primero venia de una corrida previa al alineamiento del orden de consumo del
generador aleatorio con el de la corrida oficial. Reproducir:

```
$VENV flagship/revision/verificar_manuscrito.py   # 43 de 43
```

---

## 5b. Compresion del CSV de predicciones del GBM multi-cuantil

La matriz de 54 cuantiles x 104.420 filas pesa 53.6 MB sin comprimir, por encima
del limite blando de GitHub y del criterio del propio repo de no versionar
binarios grandes. Se guarda comprimida, 23.9 MB. Se probo parquet, que sale peor
(44 MB con zstd, 36.7 con gzip) porque los cuantiles ya vienen redondeados a seis
decimales y comprimen mejor como texto.

`pandas` lee y escribe `.gz` de forma transparente por la extension, asi que solo
cambia la ruta en el escritor y en los cuatro lectores
(`fase0_model_agnostic.py`, `fase3_seleccion_hiperparametros.py`,
`fase4_metricas_benchmarks.py`, `fase9_tablas_tex.py`).

Comprobado que no cambia ningun resultado:

```
$VENV flagship/revision/fase0_model_agnostic.py
$VENV flagship/revision/fase4_metricas_benchmarks.py
# fase0_tabla_por_modelo.csv y fase4_metricas_completas.csv identicos salvo la
# columna `segundos`, que es tiempo de reloj y varia entre corridas
```

---

## 6. Documentos nuevos en la raiz

- `REVISION_PLAN.md`: triage de los quince comentarios.
- `HALLAZGOS_CRITICOS.md`: cuatro hallazgos, dos de ellos contradicen afirmaciones de la version enviada.
- `CHANGELOG_REVISION.md`: este archivo.
- `revision/informe_revisores_SEGAN-D-26-03850.md`: informe literal de los revisores.
- `flagship/segan/response_to_reviewers.tex`: carta punto por punto.
- `resultados/`: todos los resultados regenerados, con log fechado por corrida.
- `build/`: los dos PDF compilados.

---

## 7. Lo que NO cambio

- Las fronteras temporales de calibracion y de las cinco ventanas de evaluacion.
- El dataset y su alcance.
- El modelo base oficial de la Tabla 3, que sigue siendo el hurdle con sigma constante.
- Las figuras 1 a 8, salvo la renumeracion que introdujo el diagrama de flujo.
- Los resultados de `conformal_v3_tabla.csv`, salvo la etiqueta de la ventana.
- El encuadre agnostico sobre las causas del cambio de regimen, que es deliberado
  y anterior a esta revision.


---

## 8. Correcciones de una auditoria externa del paquete

Cuatro problemas detectados sobre el paquete ya compilado. Todos corregidos y
verificados. Ningun resultado experimental cambia.

### 8.1 Referencias cruzadas corridas en la carta de respuesta

El manuscrito era internamente consistente, pero la carta apuntaba a una
numeracion anterior. Dos inserciones la corrieron: la subseccion 4.6 (novedad),
que empujo la seleccion de hiperparametros a 4.7 y la evaluacion a 4.8; y el
diagrama de flujo, que entro como Figura 4 y empujo la cobertura rodante a 5 y
el trade-off a 6. Ademas, la tabla de cobertura desagregada quedo fundida dentro
de la Tabla 11, de modo que la sensibilidad de la frontera es la 10 y la de
hiperparametros es la C.11 del apendice, no la 11 y la 12.

**28 correcciones en `flagship/segan/response_to_reviewers.tex`.** La columna
"Decia" va entre comillas de codigo a proposito: el verificador de referencias
trata lo que esta entre comillas como cita literal y no como referencia viva, de
modo que esta tabla puede documentar la numeracion vieja sin dispararlo.

| Objeto | Decia | Es |
|---|---|---|
| Seleccion por origen rodante | `\S4.6` | \S4.7 |
| Metrica y tratamiento de infinitos | `\S4.7` (x3) | \S4.8 |
| Atribucion y novedad | `\S4.5` (x5) | \S4.6 |
| Diagrama de flujo | `Figura 6` (x3) | Figura 4 |
| Cobertura rodante y trade-off | `Figuras 3--4` (x2) | Figuras 5--6 |
| Puntos de cambio | `Figura 5` | Figura 3 |
| Tabla de hiperparametros | `Tabla 12` (x2) | Tabla C.13 |
| Sensibilidad de la frontera | `Tabla 11` (x2) | Tabla 12 |
| Cobertura condicional | `Tabla 10`, `Tablas 9--10` | Tabla 11 |
| Las figuras nuevas | `Figs. 6--8` | Figs. 4, 7, 8 y 9 |

Dos correcciones de contenido que salieron al revisar:

- La carta decia `Figure~5, unchanged` de la figura de puntos de cambio. No solo
  era la 3: tampoco estaba sin cambios, porque se regenero al alinear la
  penalizacion. Ahora dice que se regenero y que devuelve los mismos dos quiebres.
- La respuesta a Q4 anunciaba ocho tablas nuevas y enumeraba nueve, porque
  contaba la cobertura desagregada como tabla aparte. Se fundio en la 9.

**En `REVISION_PLAN.md`** se corrigio el inventario de tablas 9 a 11 y el de
figuras 3 a 6. **En `CHANGELOG_REVISION.md`**, las tres menciones a `figuras 6, 7 y 8` y la de la figura de puntos de cambio.

**Verificador nuevo: `flagship/revision/verificar_referencias_cruzadas.py`.**
Hace tres cosas. Numera el manuscrito parseando el `.tex` y resolviendo los
`\input` de los cuerpos de tabla, que es donde viven los floats; se autochequea
contra `build/SEGAN_paper_FINAL.aux` y aborta si discrepa de lo que numero
LaTeX; comprueba que toda referencia literal apunte a un objeto existente, en
las formas larga, abreviada (`\S`, `Fig.~`, `App.~`, `Alg.~`), de rango
(`Tables 9--10`) y en espanol de los `.md`; y comprueba la semantica contra un
mapa de frase distintiva a etiqueta, porque una referencia puede existir y aun
asi apuntar al lugar equivocado.

```
$VENV flagship/revision/verificar_referencias_cruzadas.py
# 54 etiquetas coinciden con LaTeX; 139 referencias literales; 0 problemas
```

### 8.2 Numero viejo en la Tabla C.13

El campo de descripcion de la cota de alpha decia "a lo mas 0.4 puntos de
cobertura" cuando el manuscrito, la carta y la Tabla 10 ya decian medio punto. El
valor correcto es 0.5, la caida de Transporte+ACI con gamma 0.05 al pasar de
alpha sin cota a alpha_min = 0.005 (90.1 a 89.6).

No se corrigio escribiendo 0.5 a mano. `fase1_hiperparametros.py` ahora lo
calcula desde `resultados/fase4/fase4_cota_alpha.csv`, que es el mismo archivo
que alimenta la Tabla 10, asi que los dos no pueden volver a divergir.

`verificar_manuscrito.py` no lo detecto porque solo auditaba la prosa del `.tex`,
y ese numero vive en un campo de descripcion de una tabla generada. Se extendio
a esos campos: ahora comprueba el costo de cobertura, el gamma y la ventana
seleccionados, y lista todo campo de descripcion que contenga un decimal para
inspeccion. Pasa de 43 a 46 afirmaciones.

La guardia se probo reintroduciendo el 0.4 a proposito: el verificador falla con
exit 1 y nombra la fila. Restaurado, vuelve a 0.

```
$VENV flagship/revision/fase1_hiperparametros.py
$VENV flagship/revision/verificar_manuscrito.py
# 46 de 46 afirmaciones verifican
```

### 8.3 La afirmacion de disciplina identica estaba expuesta

El manuscrito decia que el GBM multi-cuantil se entreno con "identical training
discipline". Es cierto en features, filas, corte temporal, hiperparametros por
modelo y semilla, pero no en capacidad: son 54 modelos boosted de 400 arboles
contra los 2 del hurdle. Un revisor podia objetar que la comparacion confunde
forma del modelo con capacidad del modelo, y habria tenido razon.

Se declara antes de que lo declaren ellos:

- **Abstract, introduccion, 6.2 y conclusion:** "identical training discipline"
  pasa a enumerar lo que efectivamente es identico. La afirmacion de dominacion
  de 6.2 se enuncia ahora con su costo de capacidad.
- **Seccion 4.1:** al describir el modelo se dice que el protocolo no fija la
  capacidad, con las cifras, y se remite a las limitaciones.
- **Seccion 5.3:** se acota la atribucion. "Modelo base" pasa a significar la
  pareja forma-capacidad conjuntamente, y se dice que el diseno no las separa.
- **Seccion 7, limitacion nueva (la sexta de diez):** la comparacion no separa
  forma de capacidad; la dominacion es una afirmacion sobre estos tres objetos
  ajustados y no sobre la regresion cuantilica como clase; y se describe el
  diseno que lo zanjaria, con hurdle de presupuesto de arboles equiparado o
  rejilla adelgazada, declarando que no se corrio.
- **Carta, respuesta a R1.1:** se declara la limitacion en el cuerpo de la
  respuesta, no escondida en la seccion de limitaciones.

**El diagnostico no se toca.** La relacion entre sobre-cobertura y recorte es un
contraste DENTRO de cada brazo, medido bajo una predictiva fija a la vez, y se
sostiene por separado en los tres. Lo que queda acotado es la afirmacion de
dominacion entre brazos.

El conteo de limitaciones pasa de nueve a diez en el manuscrito, la carta,
`REVISION_PLAN.md` y este archivo.

### 8.4 El titulo perdio el dominio

El titulo anterior, "Adaptive conformal calibration under regime change: the
gain measures base-model miscalibration", no contenia curtailment, renewable,
power ni grid. El editor pidio generalidad, no que el paper dejara de ser
identificable como de sistemas electricos.

Nuevo titulo, que ya estaba en la carta como alternativa 1:

> An open curtailment dataset and a diagnostic for adaptive conformal
> calibration under regime change

Catorce palabras, sin el pais, con las dos contribuciones a la vista. El
anterior baja a alternativa 1 en la carta, con su desventaja anotada. La fila de
la tabla resumen pasa de "26 to 13 words" a "26 to 14 words".

**Longitud del abstract.** La guia para autores de SEGAN pide un maximo de 250
palabras. El abstract tenia 431. Se recorto a 248 conservando las tres
separaciones de garantia (validez en muestra finita bajo intercambiabilidad,
control adaptativo de largo plazo, cobertura empirica en panel dependiente), el
resultado diagnostico, la relacion ajustada con sus tres cifras, y la
descripcion del sistema que habia bajado del titulo. Se comprimieron las
ablaciones a una oracion y se quitaron el CQR y la cota de alpha, que estan en
el cuerpo. Comprobado por conteo automatico y por presencia de cada elemento
obligatorio.

---

## 9. Comprobaciones que pasan al cierre

```
$VENV flagship/revision/verificar_manuscrito.py             # 46 de 46, exit 0
$VENV flagship/revision/verificar_referencias_cruzadas.py   # 139 refs, exit 0
cd build && pdflatex x3 SEGAN_paper_FINAL && pdflatex x2 response_to_reviewers
# 0 errores, 0 referencias sin resolver
# manuscrito 32 paginas, carta 19 paginas
```


---

## 10. Verificacion independiente del coautor, y lo que salio de ella

La Fase 0 se reprodujo desde un clon limpio con el entorno reconstruido. Sus
scripts corrieron en una ruta temporal, asi que sus resultados no quedaban
versionados. Se incorporaron al repositorio.

### 10.1 Los scripts de la verificacion entran al repo

Cinco scripts en `flagship/revision/verificacion/`, escribiendo en
`resultados/verificacion/`. Se corrieron aqui y reproducen los veinte valores de
contraste que reporto el verificador, y los tres controles pasan.

```
$VENV flagship/revision/verificacion/paso4_registro_ciego.py
$VENV flagship/revision/verificacion/obj1_capacidad_contra_forma.py
$VENV flagship/revision/verificacion/obj1b_escalera_capacidad.py
$VENV flagship/revision/verificacion/obj2_incertidumbre_diagnostico.py
$VENV flagship/revision/verificacion/obj3_control_del_brazo_nuevo.py
# 20 de 20 valores de contraste; C1, C2 y C3 pasan
```

**Un cambio de fondo en C2.** El control comparaba la cobertura cruda del GBM
contra un umbral absoluto de 8 pp y la marcaba como sospechosa. Era un falso
positivo: en la ventana de calibracion todos los modelos sub-cubren, porque estan
entrenados hasta 2023 y las magnitudes suben en 2024. El hurdle sub-cubre MAS que
el GBM (−13.87 pp contra −6.68 en tau = 0.5). C2 se reescribio como control
comparativo: exige que el GBM no sub-cubra mas que el hurdle por encima de 5 pp
en ningun nivel. Un error de indice, que daria decenas de puntos, sigue saltando;
la sub-cobertura comun al regimen ya no dispara nada.

### 10.2 El diagnostico sobre cuarenta celdas

Ver `HALLAZGOS_CRITICOS.md`, H5. El hallazgo que el verificador no exploto: cada
brazo de la escalera ya estaba evaluado en las cinco ventanas, asi que habia
ocho modelos base disponibles y no tres.

```
$VENV flagship/revision/fase0b_diagnostico_ampliado.py
# 40 celdas: r = -0.873 [-0.912, -0.645], pendiente -4.89, intercepto +5.76 [+1.60, +9.84]
# restringido a las 15 originales: r = -0.755, identico al publicado
```

Para que el remuestreo por bloques de dia pudiera recomputar las cuarenta celdas
sin reentrenar en cada replica, `evaluar()` y `fase0_model_agnostic.py` ahora
persisten las series por fila de `U_est`, `U_tr`, `y` y `fecha` en
`resultados/verificacion/series/` y `resultados/fase0/series/`.

Son catorce parquet, 26.3 MB, y se versionan con el mismo criterio con que se
versiona `pred_qgbm_multi.csv.gz`: son regenerables, pero cuestan cuarenta
minutos de computo y sin ellos ni el diagnostico ampliado ni el ajuste exacto de
la Fase 0 se pueden rehacer. Se probo float32 con zstd, que bajaria a 15 MB, y se
descarto: la perdida de precision cambiaria el bootstrap y con el la
reproducibilidad exacta, que es justamente lo que estos archivos existen para
sostener. Ningun archivo individual pasa de 2 MB.

### 10.3 La escalera de capacidad entra al manuscrito

Ver `HALLAZGOS_CRITICOS.md`, H6. Seccion 5.4 nueva, Tabla 7, Figura 8. La
limitacion de la Seccion 7 que declaraba la cuestion sin resolver se reemplaza
por el experimento.

### 10.4 Correcciones puntuales

| # | Correccion | Reproduce |
|---|---|---|
| D1 | El ajuste del diagnostico se calculaba sobre un CSV redondeado a un decimal, dando r = −0.757 en vez de −0.755. `fase0_model_agnostic.py` persiste las series y `fase0_diagnostico.py` ajusta sobre valores exactos; tabla, figura y verificador leen ese ajuste en vez de recalcularlo | `$VENV flagship/revision/fase0_diagnostico.py` |
| D2 | El control de equivalencia del brazo nuevo pasa a asercion permanente en `fase0_model_agnostic.py`, y corre siempre, no solo para el hurdle | `$VENV flagship/revision/fase0_model_agnostic.py` |
| D3 | El brazo de rejilla gruesa, con 100% de intervalos infinitos porque el cuantil conformal cae sobre el nivel maximo de la rejilla, entra como nota de la limitacion de la Seccion 7 | (texto) |
| D4 | Los tres estadisticos del diagnostico se reportan con su intervalo bootstrap, en la Tabla 5 y en la Tabla 6 | `$VENV flagship/revision/fase9_tablas_tex.py` |
| D5 | `environment.yml` con versiones congeladas; el README declara que los datos viven en Zenodo y que sin ellos la Fase 0 no corre, y lista los pasos 8 a 11 | (configuracion) |
| D6 | El Apendice D registra la reproduccion independiente: clon limpio, entorno con versiones distintas, coincidencia de checksum del modelo entrenado, sin discrepancias contra las tablas | (texto) |

### 10.5 Renumeracion

Las dos tablas y la figura nuevas volvieron a correr la numeracion. El
verificador de referencias cruzadas la detecto y el remapeo se aplico a la
carta, `REVISION_PLAN.md` y este archivo: secciones 5.4 a 5.7 pasan a 5.5 a 5.8,
tablas 6 a 10 pasan a 8 a 12, la de hiperparametros de C.11 a C.13, y la figura
de ablaciones de 8 a 9.

Un intento previo del remapeo encadenaba sustituciones y convirtio
"Tables 6 and 7" en "Tables 8 and 11" en vez de "8 and 9". Se rehizo en una sola
pasada. Se anadieron ademas los alias en espanol, que la primera version no
cubria.

Dos patrones semanticos del verificador llevaban numeros de seccion cableados y
se corrieron con la insercion. Se reescribieron sin ellos: un verificador de
numeracion no puede depender de la numeracion.

### 10.6 Comprobaciones al cierre

```
$VENV flagship/revision/verificar_manuscrito.py             # 51 de 51, exit 0
$VENV flagship/revision/verificar_referencias_cruzadas.py   # 166 refs, exit 0
# abstract 244 palabras (limite 250)
# manuscrito 34 paginas, carta 19, cero errores y cero referencias sin resolver
```
