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

---

## 11. Cinco cambios de cierre

### 11.1 Alcance del diagnostico en la Seccion 7 y en Q7 de la carta

Decia "tres modelos base... quince celdas de tres predictivas". Pasa a ocho
predictivas y cuarenta celdas, con la precision de que las ocho no son ocho
clases de modelo: tres son variantes de la familia hurdle y cinco son variantes
de presupuesto de una sola familia cuantilica. El diseno abarca dos formas
funcionales, no ocho. Espejado en la lista de Q7 de la carta.

### 11.2 Los tres valores del diagnostico en prosa

`r = -0.757`, pendiente `-4.39`, intercepto `+5.49` pasan a −0.755, −4.36 y
+5.45, que es lo que dan la Tabla 5, la Tabla 6, la Figura 7 y el calculo sobre
los arrays sin redondear. Corregidos en 5.3 del manuscrito, en la respuesta a
R1.1 y en la carta al editor de la primera plana.

### 11.3 Robustez del quiebre

`flagship/revision/fase0c_robustez_quiebre.py`, salidas en `resultados/fase0c/`.
Los cinco valores de contraste reproducen exacto. Ver `HALLAZGOS_CRITICOS.md`,
H8.

```
$VENV flagship/revision/fase0c_robustez_quiebre.py
# salto -11.797 con las 40, F(1,37) = 12.982
# salto -13.587 sin qgbm_54x15, F(1,32) = 15.608
# con efecto fijo: salto -11.478, F(1,30) = 9.405
# fuera de muestra en x = -8.42: +54.2 con quiebre, +55.7 observado, +43.0 recta unica
# cuadratica: p = 0.7117 sobre las 40; F(1,32) = 27.942 sobre las 35
```

### 11.4 Tres parrafos nuevos

- **5.3**, al final del bloque que cierra con la tasa comun de −6.50: la robustez
  del quiebre, con la declaracion de que los test F tratan las celdas como
  independientes y que por eso se reportan como razon para no ampliar la
  afirmacion.
- **5.4**, tras el de saturacion: ningun brazo usa detencion temprana, lo que
  deja al hurdle agrandado libre de sobreajustar; el orden se establece al
  presupuesto propio del hurdle, donde el sobreajuste no esta en juego.
- **7**, item de la escalera: ademas del eje unico, la ausencia de detencion
  temprana.

### 11.5 Tabla 9 y el reenvio de 5.3

**La convencion del delta se verifico contra el codigo antes de escribirla y es
la declarada:** la columna de IS finito promedia sobre las filas finitas de CADA
metodo (`IS[np.isfinite(U)].mean()`), mientras el delta es una comparacion
pareada sobre las filas finitas en AMBOS (`np.isfinite(isa) & np.isfinite(isr)`).
La nota al pie lo declara y da la fraccion maxima descartada, 5.9%.

**Pero esa no era la causa del desajuste entre el +27 de la Tabla 9 y el +29.3 de
la Tabla 8.** La causa era el orden de consumo del generador: `fase2` y `fase4`
creaban generadores frescos para el transporte en vez de continuar el que
aleatorizo el score, y ninguno reproducia la corrida canonica. Alineados, los
tres coinciden y los dos deltas dan +32.4. Ver `HALLAZGOS_CRITICOS.md`, H7, que
documenta ademas el unico resultado que esto cambio: la ablacion del shrinkage.

```
$VENV flagship/revision/fase2_ablaciones.py
$VENV flagship/revision/fase4_metricas_benchmarks.py
# los tres dan ancho 595.9, 5.9% de infinitos, IS finito 1029.9
```

El reenvio de 5.3 sobre la separacion entre forma y capacidad mandaba a la
Seccion 7; va a la 5.4, que es donde se separa. El mismo reenvio en 4.1 ahora
apunta a las dos: a 5.4 por la separacion y a la 7 por lo que licencia.

### 11.6 Verificadores desacoplados de los valores cableados

Cuatro chequeos de `verificar_manuscrito.py` llevaban el valor esperado escrito
en el propio verificador, asi que al cambiar un resultado habia que editarlo a
mano. Ahora construyen la frase esperada desde el CSV. Es el mismo criterio que
ya se aplico a los patrones semanticos del verificador de referencias: una
comprobacion no puede depender de lo que comprueba.

### 11.7 Comprobaciones al cierre

```
$VENV flagship/revision/verificar_manuscrito.py             # 51 de 51, exit 0
$VENV flagship/revision/verificar_referencias_cruzadas.py   # 184 refs, exit 0
# manuscrito 34 paginas, carta 19, cero errores y cero referencias sin resolver
# numeracion sin cambios: no se anadieron floats, solo texto y una nota al pie
```

---

## 12. Cierre previo al reenvio del 14 de septiembre

### 12.1 El aporte del shrinkage, en los sitios que faltaban

Dos afirmaciones de supervivencia seguian diciendo que ni la combinacion ni el
dispositivo sobreviven su ablacion. La combinacion no sobrevive, porque el
transporte empeora +74.2 sobre el ACI; **el dispositivo si sobrevive**, con -6.5
e IC [-10, -3], lo que no sobrevive es su precio. Corregido en 4.6 del manuscrito
y en R2.4 de la carta. El resto de los sitios (introduccion, 5.5, primera plana,
prosa y fila de R1.3) ya estaba corregido de la tanda anterior y se verifico.

### 12.2 Numeros del pipeline

591 MWh e interval score 1026 pasan a 596 y 1030; +29.3 pasa a +32.4. Quedaban
cuatro ocurrencias, todas en la carta: la fila y la prosa de R1.3, R2.6 y **la
primera plana**, que es la que estuvo a punto de escaparse.

### 12.3 Verificado que ya estaba bien

- La Seccion 7 ya decia "dos familias de modelos... cuarenta celdas de ocho
  predictivas", con la precision de las tres variantes hurdle y las cinco de
  presupuesto. Su espejo en Q7 tambien.
- Los tres valores del diagnostico ya eran -0.755, -4.36 y +5.45 en los tres
  documentos: cero ocurrencias de los viejos.

### 12.4 Abstract (opcional 5)

Cierra ahora con la recomendacion operativa: arreglar el modelo base domina
arreglar la capa de calibracion. **La distincion de garantias NO se elimino**,
porque responde de forma literal al comentario R2.7; se fundio con la oracion
anterior y se movio una posicion arriba. 250 palabras exactas.

### 12.5 Deteccion temprana (opcional 6)

`flagship/revision/verificacion/obj1d_hurdle_deteccion_temprana.py`. Ver
`HALLAZGOS_CRITICOS.md`, H9. El resultado contradice la concesion que el
manuscrito hacia por escrito: la detencion temprana no devuelve al hurdle a su
rendimiento de 800 arboles, lo supera en 5.7% con solo 105 arboles.

```
$VENV flagship/revision/verificacion/obj1d_hurdle_deteccion_temprana.py
# elige 59 arboles de ocurrencia y 46 de magnitud
# CRPS test 89.52 -> 84.38; transicion 133.52 -> 124.03
```

Reportado en prosa dentro de 5.4 y en el item de la escalera de la Seccion 7.
**Sin fila nueva en la Tabla 7**, como se pidio: la numeracion no se movio.

### 12.6 Comprobaciones al cierre

```
$VENV flagship/revision/verificar_manuscrito.py             # 54 de 54, exit 0
$VENV flagship/revision/verificar_referencias_cruzadas.py   # 192 refs, exit 0
# abstract 250 palabras exactas, manuscrito 35 paginas, carta 19
# cero errores de compilacion y cero referencias sin resolver
```

---

## 13. Ultima pasada antes de Editorial Manager

Seis correcciones de texto. Ningun numero de archivo de resultados cambia, no se
regenera ninguna tabla ni figura, la numeracion no se mueve.

| # | Cambio | Donde |
|---|---|---|
| 1 | La frase de sigma del brazo con detencion temprana atribuia el alza a "un mu menos sobreajustado que deja mas variacion en el residuo", lo que contradice 4.1: sigma se estima fuera de fold DENTRO del entrenamiento, donde mas arboles si reducen el residuo. Se reemplaza por la redaccion que reporta los tres puntos y los ata al mecanismo | \S5.4 |
| 2 | Cortada la subordinada que remitia a un borrador que los revisores nunca vieron | \S5.4 |
| 3 | **Ya estaba bien.** El texto decia 33, no 34 | \S5.4 |
| 4a | "The practical ordering follows" apuntaba al antecedente equivocado; pasa a "The practical implication is that..." | abstract |
| 4b | "Panel dependence is severe, with an intraclass correlation by date of 0.238, and we separate" pasa a "Panel dependence is severe: intraclass correlation by date 0.238. We separate" | abstract |
| 5 | El descuento del modelo base se extiende con la lista completa de lo calculado sobre el hurdle **y tres tablas que faltaban** | \S7 |
| 6 | "an interval that also excludes zero" pasa a "with a bootstrap interval" | \S4.6, \S5.5, R2.4 |

### 13.1 Verificacion del punto 1: la monotonia se sostiene

```
$VENV -c "leer resultados/verificacion/obj1d_deteccion_temprana.json"
#  arboles   105     800    4000
#  sigma   1.8274  1.7016  1.6641   decreciente
#  CRPS     84.38   89.52   95.46   creciente (test completo)
#  CRPS    124.03  133.52  141.07   creciente (transicion)
```

Los tres puntos son monotonos en las dos direcciones, asi que se escribe
"monotonically" sin salvedad.

### 13.2 Verificacion del punto 5: faltaban tres tablas

La lista propuesta nombraba las Tablas 3, 9 y 11 y las Figuras 5, 6 y 9. Auditando
que predictiva alimenta cada objeto, **faltaban tres**, todas calculadas
integramente sobre el hurdle:

- **Tabla 8**, las ablaciones (`fase2_ablaciones.py`, solo `pred_hurdle`)
- **Tabla 10**, la cota de alpha (`fase4_metricas_benchmarks.py`)
- **Tabla 12**, la sensibilidad de la frontera (`fase6_cronologia.py`)

Se anadieron. **Queda fuera a proposito la Tabla 2**, el MAE de los modelos base:
su fila del hurdle tambien se moveria, pero es exactitud puntual y no un nivel de
la capa de calibracion, y sobre todo el descuento ahi NO corre en una sola
direccion, porque un hurdle mejor acercaria su MAE al del naive estacional en vez
de alejarlo. Meterla en esa oracion la volveria falsa.

Las Tablas 4 a 7 y las Figuras 7 y 8 incluyen al hurdle como un brazo entre
varios, pero son justamente las comparaciones donde su identidad es el objeto de
estudio, y el descuento ahi es lo que \S5.4 discute. No entran en la lista.

### 13.3 Comprobaciones al cierre

```
$VENV flagship/revision/verificar_manuscrito.py             # 54 de 54, exit 0
$VENV flagship/revision/verificar_referencias_cruzadas.py   # 195 refs, exit 0
# abstract: 246 palabras contando la expresion matematica como una, 247 como tres
# manuscrito 35 paginas, carta 19, cero errores y cero referencias sin resolver
# numeracion de tablas y figuras sin cambios
```

## 14. Control de robustez del orden puntual

Un solo calculo y dos ediciones de texto, decididas tras medirlo.

**El calculo.** `flagship/revision/verificacion/obj1e_mae_hurdle_es.py` (nuevo)
genera las predicciones puntuales del hurdle con detencion temprana de H9 sobre
las mismas 104.420 filas y el mismo periodo fuera de muestra de la Tabla 2, con
la misma mediana de la mixtura. Escribe
`resultados/verificacion/obj1e_mae_hurdle_es.json`.

MAE total 108.55 MWh contra 104.08 del hurdle oficial (4.3% peor) y 85.1 del
naive estacional (27.6% por detras). Queda ultimo entre las siete filas.
Detalle en H10 de `HALLAZGOS_CRITICOS.md`.

**Control obligatorio.** El script aborta si no reproduce antes la fila oficial
del hurdle de la Tabla 2 celda por celda. Paso con desvio maximo de 0.005 MWh.
Las filas de referencia se leen de `resultados/tablas_tex/tab_mae.tex`, no se
escriben en el script: una version anterior las tenia escritas a mano y por eso
omitio la fila del GBM multi-cuantil (87.6) al listar el orden. Regla 1.

**Edicion 1, Seccion 5.1.** Parrafo nuevo despues del parrafo de alcance, con el
control de robustez y su lectura como instancia medida de dependencia del
criterio. Sin fila nueva en la Tabla 2: en prosa, igual que la escalera en 5.4.

**Edicion 2, Seccion 7.** El item del descuento cierra declarando que la Tabla 2
**no** esta en esa lista, con la razon, y remite a 5.1. El descuento tiene
direccion incorporada y aqui la direccion es la contraria; ponerla en la misma
lista obligaria al lector a deshacer una oracion que se contradice sola.

**Guardias nuevas.** Cuatro comprobaciones en `verificar_manuscrito.py` para los
numeros de 5.1 (mejora de CRPS, el par 104.1 a 108.6, el margen de 27.6% y que
"last in this table" solo se pueda escribir si de hecho es el peor de
`orden_tabla2`), mas una salida con error si el control de reproduccion de la
Tabla 2 no consta en el JSON.

**Al cierre:** 58 de 58 afirmaciones en prosa verifican, 206 referencias
cruzadas cuadran contra el `.aux`, manuscrito de 35 paginas y carta de 19 sin
errores ni referencias sin resolver, abstract intacto y por debajo de 250
palabras con los dos criterios de conteo (249 y 246). La numeracion no se movio:
la Tabla 2 sigue siendo la 2, la Seccion 5.1 sigue siendo 5.1.

## 15. Entregables para Editorial Manager: fuentes y version marcada

Editorial Manager no acepta PDF para el manuscrito en revision.

**Paquete de fuentes.** `flagship/revision/empaquetar_fuentes.sh` (nuevo) arma
`entrega_revision/11_fuentes_latex.zip`: 25 archivos planos, 558.506 bytes.
Todo se extrae del commit con `git show`, no del arbol de trabajo, para que el
zip corresponda demostrablemente a un estado versionado.

```
bash flagship/revision/empaquetar_fuentes.sh 77f8625
```

Contiene el .tex principal, los 13 .tex que entran por `\input` (12 tablas mas
`hiperparametros.tex`), las 9 figuras PDF, `elsarticle.cls` v3.5 y un README de
compilacion. Los demas paquetes son de TeX Live estandar y no van incluidos.

**No hay .bbl y no hace falta.** La bibliografia son 43 `\bibitem` en un
`thebibliography` escrito en linea en el .tex. No se corre BibTeX en ningun
momento, asi que el build no puede depender de un .bst en el servidor. El script
lo comprueba y **falla** si algun dia el .tex pasa a usar `\bibliography{}` sin
que se incluya el .bbl.

**La prueba.** El script extrae el zip en un directorio temporal con `TEXINPUTS`
restringido al directorio actual y al arbol del sistema, compila tres veces y
exige 35 paginas, cero errores, cero referencias sin resolver y cero archivos no
encontrados. Si falta algo en el zip, ahi se descubre, porque no hay camino de
vuelta al repo. Resultado: 35 paginas, todo en cero, y el texto del PDF aislado
es identico caracter por caracter al del build del repo (1.974 lineas de
`pdftotext -layout`). Las 9 figuras del zip son byte a byte las que produjeron
ese PDF.

**Control negativo.** El mismo zip sin `tab_mae.tex` y sin `fig7` no produce PDF
y el log declara el archivo que falta. La prueba que pasa, entonces, discrimina.

**Version marcada: el diff crudo no compila.** Baseline `submitted-segan-v1`
(commit 4af5ea7, 2026-07-28, VERSION 5.0), que es la efectivamente enviada.
`latexdiff` con las opciones por omision produce un .tex que da 32 errores de
LaTeX, todos de `\UL@stop`: el subrayado de `ulem` no puede cruzar limites de
parrafo, ni `\caption{}`, ni celdas de `tabular`, ni ecuaciones en display. Se
conserva en `resultados/latexdiff/marcado_crudo_NO_COMPILA.tex` con su log.

Dos tipos de marcado que no usan `ulem` compilan limpios en 37 paginas, cero
errores y cero referencias sin resolver: `-t CCHANGEBAR` y `-t CFONT`, ambos con
`--math-markup=off --graphics-markup=none` y excluyendo `caption` y los
comandos de seccion. Quedan en `resultados/latexdiff/` y como candidatos
`12_` y `13_` en `entrega_revision/`.

**Legibilidad, medida.** Del cuerpo del marcado sin bibliografia, 17.669
palabras: **72,8% marcado como añadido** y solo 11 de 149 parrafos de mas de 25
palabras quedan sin marca alguna. Las secciones nuevas enteras se leen bien. El
titulo, el abstract y el arranque de 4.1, que se reescribieron en su lugar,
salen como intercalado rojo/azul palabra por palabra. Decision pendiente del
autor.

**Nota de trazabilidad.** El comentario del preambulo dice "Cambios respecto de
la version 6.0 enviada". Es inexacto: la 6.0 se escribio el 10 y 12 de agosto,
despues del envio, y es ya parte del reencuadre. La enviada es la 5.0. Es un
comentario de LaTeX y no sale en el PDF, pero el baseline del diff se tomo del
tag, no de ese comentario.

## 16. Version marcada: configuracion de bloques atomicos

Segunda pasada sobre la version marcada. La primera se reporto como rota solo en
el titulo y el abstract, y estaba mal: el autor encontro ocho lugares mas, dos de
ellos con la Tabla 3 completa derramada dentro de un parrafo de resultados.

**Causa.** La version enviada traia las tablas en linea en el .tex; la actual las
trae por `\input`. Al diffear, latexdiff desarmaba la tabla vieja celda por
celda y **comentaba** los separadores `&`, de modo que el contenido de la tabla
quedaba como texto corrido dentro del flotante. Medido: 66 separadores `&`
comentados y 84 celdas sueltas marcadas (`DIFdelFL`) en el marcado anterior.

**Configuracion nueva.** `flagship/revision/generar_marcado.py` (nuevo):

```
python flagship/revision/generar_marcado.py
```

Baseline sin cambios: `submitted-segan-v1` = commit 4af5ea7 del 28 de julio de
2026, la version 5.0, la efectivamente enviada.

- `--config PICTUREENV=` extendido con `table`, `tabular`, `figure`,
  `algorithm`, `algorithmic`, `equation` y `thebibliography`, conservando los
  tres del default. latexdiff convierte cada uno en un token unico
  (`\PICTUREBLOCK...`, linea 3256 del fuente), asi que el entorno se marca
  entero. Tras el cambio: **0** separadores comentados y 1 celda suelta.
- `--math-markup=whole`: cada ecuacion como bloque.
- `--disable-citation-markup`: sin marcado de citas.
- `-t CCHANGEBAR`, sin cambios.

**Bibliografia.** Se sustituye por la nueva en ambos archivos antes de diffear,
de modo que aparezca una sola vez y sin marcas. El script comprueba antes que
las 10 claves de la enviada sean subconjunto de las 43 nuevas, y lo son, asi que
no queda ninguna cita sin resolver. Los cuatro defectos reportados quedaron
resueltos: 43 entradas, ninguna vacia, ningun DOI duplicado y Gneiting una sola
vez, en [41]. **Ninguno era un defecto del manuscrito**: la bibliografia real ya
estaba limpia y todos eran artefactos del diff palabra por palabra.

**Nota de cabecera.** Se inserta tras `\end{frontmatter}`, sin marcado de diff,
con reglas arriba y abajo. Declara el reencuadre, el porcentaje de cuerpo nuevo,
el crecimiento de la bibliografia y que el recuento cambio por cambio esta en la
carta de respuesta.

Dos numeros de la nota difieren de los que se habian pedido, y por que:

- **70% y no 73%.** El 72,8% se midio sobre el marcado anterior, donde la
  bibliografia se diffeaba palabra por palabra. Con la bibliografia fuera del
  cuerpo marcado la medicion de este documento da 70,1%.
- **4.753 a 15.804 palabras, y no 5.712 a 18.032.** Aquellos eran `wc -w` del
  .tex entero, que cuenta comandos y comentarios de LaTeX: ya habia derivado a
  18.092 solo por agregar cuatro lineas de comentario al preambulo, que no es un
  cambio del manuscrito. El conteo de la nota es prosa del cuerpo sin
  bibliografia, que es lo que describe el porcentaje de la misma frase.

**Estado del PDF marcado:** 38 paginas, 0 errores, 0 referencias o citas sin
resolver. Queda en `resultados/latexdiff/` y como `12_` en `entrega_revision/`.

**Lo que la configuracion no puede arreglar.** Cinco de los siete lugares del
cuerpo siguen rotos, mas el titulo y el abstract, y no por tablas: latexdiff
alinea palabras y cuando un parrafo se reescribio completo empareja palabras
incidentales de parrafos distintos e intercala. Eso solo se resuelve
convirtiendo el bloque en reemplazo completo. Detalle en la seccion 17.

**Correccion del preambulo.** El comentario decia "Cambios respecto de la
version 6.0 enviada". Falso: la 6.0 se escribio el 10 y 12 de agosto, despues
del envio, y es parte del reencuadre. Ahora declara la version 5.0, el tag, el
commit y la fecha. Importa porque el .tex viaja dentro del zip que va al editor.

## 17. Reemplazo de bloque completo en la version marcada

Los ocho pasajes que el intercalado de latexdiff dejaba ilegibles se convierten
a reemplazo de bloque: el pasaje viejo entero marcado como borrado y despues el
nuevo entero marcado como agregado, sin intercalado dentro del bloque.

`flagship/revision/bloques_marcado.py` (nuevo), llamado desde
`generar_marcado.py`. No toca las fuentes: opera sobre el `.tex` que produce
latexdiff. Baseline sin cambios, `submitted-segan-v1`, y sigue en CCHANGEBAR.

**Como se de-intercala.** latexdiff ya emparejo viejo con nuevo, asi que el
pasaje se proyecta dos veces: borrando los grupos `\DIFadd` se obtiene el texto
viejo, y borrando los `\DIFdel` el nuevo. La unidad es la natural: el argumento
de `\title`, el entorno `abstract`, o el parrafo completo que contiene el ancla.

**El texto emitido sale de la fuente, no de la proyeccion.** La proyeccion se
usa para ubicar el pasaje por sus dos extremos, y se emite lo que hay en la
fuente entre ellos. Hizo falta porque latexdiff pierde caracteres: en el
abstract de la version enviada se come el espacio de "system operator figures" y
lo emite como "operatorfigures", dentro de un unico `\DIFdel`.

**Verificacion automatica, no a ojo.** Cada bloque se compara contra las dos
fuentes: el lado viejo tiene que aparecer literal en 4af5ea7 y el nuevo en el
manuscrito final, normalizando solo el espacio en blanco, que LaTeX trata como
equivalente. `generar_marcado.py` **aborta** si algun bloque no verifica. Los
ocho verifican: siete exactos en los dos lados y el abstract con el lado viejo
reconstruido desde la fuente, en 2.137 caracteres, que es el largo completo del
abstract de la 5.0.

**Tres defectos propios, encontrados y corregidos en el camino.**

- La proyeccion conservaba el contenido del otro lado cuando el parrafo empieza
  a mitad de una region, porque latexdiff abre el `\DIFaddbegin` en el parrafo
  anterior si la adicion abarca varios. Se borra por comando y no por region.
- Al reemplazar ese parrafo quedaba un `\DIFaddbegin` sin cierre. Se preservan
  los cierres colgantes contandolos en el fragmento.
- El separador entre el bloque borrado y el agregado va DENTRO del grupo de
  `\DIFdel`. Puesto entre `\DIFdelend` y `\DIFaddbegin`, TeX lo descarta por
  venir despues de una palabra de control, y quedaba
  "...Electricity SystemAn open curtailment dataset".

**Estado:** 38 paginas, 0 errores, 0 referencias o citas sin resolver, 70,2% del
cuerpo marcado como añadido.

**Auditoria pagina por pagina.** Se reviso el PDF completo, las 38 paginas. Las
ocho conversiones se leen como bloque. La Tabla 3 se imprime entera y alineada,
con `test_transition`, y `test_ramp` no aparece ninguna vez. La bibliografia sale
sin marcar, con las 43 entradas completas. Tablas, figuras, ecuaciones y el
Algoritmo 1 salen intactos. La auditoria encontro dos cosas mas, en las
secciones 18 y H11.

## 18. Pasajes ilegibles fuera de la lista de ocho

La auditoria encontro daño de intercalado en pasajes que no estaban en la lista.
Se reportan y no se tocan: la lista era de ocho.

Detectados mecanicamente, no a ojo: 14 fusiones de palabra impresas en el borde
de un cambio, mas los parrafos donde un fragmento viejo corto queda inyectado en
medio de texto nuevo.

Por seccion, lo que un lector no puede leer:

| Seccion | Ejemplo |
|---|---|
| 1, Introduction, casi completa | "informative settingcase at hand", "regions in the northnorthern regions", "post-storage regimeone part", "core of this workTwo properties", "highly variablevary widely", "adaptive layerupdate", "its constructiondates" |
| 2.4, tres parrafos | "a density ratiobetween", "integral transformfollowing", "probabilistic forecastsmap" |
| 3.3, tercer parrafo | "storage deployment shifted change in the distribution" |
| 4.1, dos parrafos | "means ending at twe predict curtailment" |
| 4.2, dos parrafos | "under regime changemotivated", "(probit) scaletranslation", "inverting the mixturein closed form" |
| 4.3, encabezado y primer parrafo | "Coverage under regime changeThree guarantees", "by all plantsIt is easy" |
| 4.4 | "structure aboveof Section 4.2" |
| 4.5, encabezado y primer parrafo | "EvaluationThe adaptive scheme in full" |
| 4.8, tres parrafos | "January to August 2024; the 2024. The first test month , September is September 2024" |
| 5.1, encabezado y primer parrafo | `littlemarginal value`, `Section 33.3` |
| 5.2, encabezado y dos parrafos | "regime changehurdle base model", "in the ramptransition window" |
| 5.5, primer parrafo | "can be isolated: the per-point implementation..." |
| 6.2, 6.3 continuacion, 6.4, 6.5 | "reported with Two operational details", "conditional reliability matters : a method", "preferable1.334" |
| 8, Conclusion, dos parrafos | "into over-coveredand , wider bands", "the method negative result" |
| Apendice B | "efectivo n is about 1,which is why" y "clustered by date000 rather than 26,552" |

`bloques_marcado.BLOQUES` es una lista: agregar un ancla por pasaje los convierte
con la misma verificacion contra las dos fuentes.

## 19. Tabla C.13: de table* a longtable

Arreglo de H11. `fase1_hiperparametros.py` emitia la tabla como `table*`, un
flotante, y un flotante no se parte entre paginas: con 38 filas era mas alto que
la caja de texto y LaTeX descartaba las ultimas cuatro en silencio, dejando solo
`Float too large for page by 173.5222pt` en el log.

Ahora emite un `longtable`, con `\endfirsthead`, `\endhead`, `\endfoot` y
`\endlastfoot`, de modo que se parte sola y **no vuelve a fallar si la tabla
crece**. Se agrego `\usepackage{longtable}` al preambulo; es un paquete de TeX
Live estandar y no hay que empaquetarlo.

```
<venv>/bin/python flagship/revision/fase1_hiperparametros.py
```

**Comprobado sobre el texto del PDF, no sobre el .tex.** Las cuatro filas de
semillas se imprimen, con su valor, y las 37 filas de la tabla llegan al PDF.
La numeracion no se movio: la tabla sigue siendo C.13 y las tablas 2 a 12 siguen
en su lugar. El manuscrito pasa de 35 a 36 paginas.

**Guardas.** Dos comprobaciones nuevas en `verificar_manuscrito.py`, que leen el
texto extraido del PDF con `pdftotext`: que cada fila de semillas aparezca junto
a su valor, y que ninguna fila de la tabla se quede fuera. Se coteja la etiqueta
por sus primeras cuatro palabras porque la celda se parte dentro de su columna.
La guarda de `empaquetar_fuentes.sh` se mantiene. Control negativo: las dos
comprobaciones **fallan** contra el PDF anterior, el de 35 paginas, reportando
las cuatro semillas y las cuatro filas perdidas.

**El verificador de referencias abortaba** tras el cambio, y con razon: su parser
no conocia `longtable` y calculaba "C" en vez de "C.13" para `tab:hiper`. El
autochequeo contra el `.aux` lo detuvo antes de auditar con una numeracion
equivocada, que es para lo que se escribio. Se le enseño `longtable`.

**Barrido del log completo.** Ningun otro aviso que descarte contenido:
`Float too large` 0, `Overfull \vbox` 0, `No room for a new` 0, `Too many
unprocessed floats` 0, `Missing character` 0, y ningun `LaTeX Warning`. Quedan
un `Overfull \hbox` de 1,30pt, 17 `Underfull \hbox` y cuatro avisos de hyperref
que quitan `\cnotenum` y `\@corref` de los metadatos del PDF, de la maquinaria
de autores de elsarticle. Ninguno descarta contenido ni se ve en la pagina.

## 20. Reemplazo de bloque en los pasajes fuera de la lista de ocho

`bloques_marcado.py` pasa de una lista de ocho anclas a una tabla de politica
por seccion, porque el encargo pedia cosas distintas en cada una: de 4.3 y 4.5
solo el encabezado, de 5.5 solo el primer parrafo, de 3.3 solo el tercero, y de
1, 2.4, 4.1, 4.2, 4.8, 6.2, 6.4, 6.5, 8 y el apendice B la seccion entera. Las
secciones se identifican por su encabezado en el manuscrito final y no por
numero, porque la numeracion se corre en el marcado.

**40 bloques convertidos**, los 8 explicitos mas 32 del barrido: 4 encabezados y
28 parrafos. Los 40 verifican contra las dos fuentes.

**Cuatro pasajes omitidos a proposito**, y se reportan: contienen matematica en
display. El texto viejo completo incluiria un `equation*`, y eso dentro de
`\DIFdel{}` no compila. Son dos de 4.2, uno de 4.1 y uno de 4.8.

**La verificacion se endurecio.** Antes comprobaba que el texto emitido
apareciera en su fuente, lo que era casi una tautologia desde que el texto se
extrae de la fuente. Ahora son dos: que este literal en su fuente, y que sea EL
pasaje, cotejado contra la proyeccion del diff con `_cotejan`.

**Tres defectos propios mas, encontrados por esa verificacion.**

- `norm` corria antes de quitar llaves, y quedaba "approximate , which" con
  espacio antes de la coma. Las tres normalizaciones (llaves, espacio en blanco,
  espacio antes de puntuacion) se unificaron en `canon()`, en una sola pasada y
  con mapa de indices al original.
- El separador de miles del manuscrito, escrito `{,}`, lo parte latexdiff:
  `1{,}000` sale como `\DIFadd{...1}{\DIFaddend ,` ... `}\DIFadd{000...}`, y esas
  llaves terminaban del lado viejo de la proyeccion aunque pertenezcan solo al
  texto nuevo. `canon()` las ignora al cotejar y el texto se emite desde la
  fuente, donde las llaves estan donde corresponde.
- La firma de fusion exigia letra a ambos lados y no veia `preferable1.334` ni
  `1,which`. Ahora admite digitos y puntuacion.

## 21. Estado al cierre de la version marcada

**Manuscrito** 36 paginas, 0 errores, 0 referencias o citas sin resolver.
**Marcado** 40 paginas, 0 errores, 0 sin resolver, 71,6% del cuerpo marcado.
**Zip** 36 paginas en aislamiento, y en cero los errores, las referencias sin
resolver, los archivos no hallados, los flotantes sobredimensionados y las
semillas sin imprimir.
**verificar_manuscrito.py** 60 de 60. **verificar_referencias_cruzadas.py**
todas cuadran, y su autochequeo contra el `.aux` pasa.

**Fusiones de palabra impresas: de 14 a 3.** Las tres quedan explicadas, no
sueltas:

| Fusion | Seccion | Por que sigue |
|---|---|---|
| `mixturein closed form` | 4.2 | el pasaje tiene un `equation*`: omitido a proposito |
| `plantsIt is easy` | 4.3 | de 4.3 se pidio solo el encabezado |
| `structure aboveof Section` | 4.4 | 4.4 no estaba en la lista |

**Parrafos mezclados en el cuerpo: 61.** De esos, 46 estan en forma de bloque
(un borrado, despues un agregado, sin intercalar) y 9 siguen intercalados: los
4 omitidos por matematica en display, el de 4.3, los 3 de 4.4, y el segundo
parrafo de 6.3, que tampoco estaba en la lista. Los 6 restantes son lineas de
encabezado donde el titulo viejo se imprime como borrado junto al nuevo, que se
verifico a la vista y se lee bien.

Convertir los cuatro con matematica en display exige emitir el bloque partido a
ambos lados de la ecuacion, que es un cambio de diseño y no un ajuste; 4.4 y el
segundo parrafo de 6.3 solo necesitan una linea en la tabla de politica.
