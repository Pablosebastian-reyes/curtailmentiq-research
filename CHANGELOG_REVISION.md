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
| `flagship/revision/fase8_buscar_referencias.py` | Busca referencias en Crossref; con `cotejar`, resuelve los DOI de la bibliografia (Crossref y DataCite) y coteja cada registro contra su entrada | R2.1 |
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
| Bibliografia de 10 a 43 entradas; los 40 DOI verificados, tres de NeurIPS sin DOI | R2.1 | bibliografia |
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
| Tabla de hiperparametros | `Tabla 12` (x2) | `Tabla C.13` |
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

### 8.2 Numero viejo en la `Tabla C.13`

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

## 19. `Tabla C.13`: de table* a longtable

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

*Corregido en la seccion 22: el conteo de fusiones y la clasificacion de los
parrafos que no quedaron en bloque estaban mal.*

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

## 22. Correccion: el conteo de fusiones y lo que queda sin convertir

La seccion 21 dice que las fusiones impresas bajaron de 14 a 3 y que, de los
parrafos que no quedaron en bloque, seis eran lineas de encabezado legibles.
Las dos cosas estaban mal.

**Fusiones: de 32 a 9, no de 14 a 3.** El detector solo miraba bordes entre dos
regiones marcadas. Hay otro tipo, texto sin marcar pegado a una region marcada
("attentionthan", "unaffectedby", "inference(ACI"), que no veia. Ademas el 14
se conto con la regex que solo admitia letras y el 3 con la ampliada, asi que no
eran comparables. `flagship/revision/auditar_marcado.py` (nuevo) cuenta los
tres tipos de borde y **confirma cada candidata contra el texto del PDF**: la
que no sale pegada no cuenta.

```
<venv>/bin/python flagship/revision/auditar_marcado.py --antes cc39ef5
```

Antes de convertir, 32 (19 entre regiones marcadas y 13 de texto sin marcar
contra una region marcada). Ahora 9, y las nueve estan fuera de lo convertido:
6 en 4.4, 1 en 2.1, 1 en 4.3 (se pidio solo el encabezado) y 1 en 4.2, en un
parrafo omitido por contener matematica en display.

**Los 15 parrafos mezclados que no quedaron en bloque**, clasificados uno por
uno y verificados a la vista sobre el PDF:

| Cuantos | Donde | Estado |
|---|---|---|
| 4 | 4.1, 4.2 (dos), 4.8 | omitidos a proposito: contienen matematica en display |
| 4 | 4.4 | intercalados; 4.4 no estaba en la lista |
| 1 | 4.3 | intercalado; se pidio solo el encabezado |
| 1 | 2.1 | intercalado; no estaba en la lista |
| 1 | 6.3, segundo parrafo | intercalado; no estaba en la lista |
| 1 | 3.3, segundo parrafo | legible: sustitucion de una expresion corta |
| 1 | 6.2 | legible: borrado y despues agregado |
| 2 | 6.4 y 6.5, lineas de encabezado | legibles |

4.4 tiene cuatro parrafos intercalados, no tres. 6.2, que si estaba en la
lista, quedo bien: se reviso por la duda y se lee como bloque.

**El conversor no se toco.** Su criterio (`ilegible()` en `bloques_marcado.py`)
sigue viendo solo el primer tipo de borde. Ampliarlo cambiaria que parrafos se
convierten dentro de las secciones barridas, y con eso el marcado entero; queda
para cuando se decida si se convierten 2.1, 4.3, 4.4 y 6.3.

## 23. Cierre: suplementario en PDF, divulgacion del hurdle detenido y ultimos bloques

**Pandoc.** Homebrew no pudo instalarlo: exige actualizar las Command Line Tools
de Xcode. Se instalo el binario oficial del release de GitHub, sin pasar por
brew:

```
https://github.com/jgm/pandoc/releases/download/3.11/pandoc-3.11-x86_64-macOS.zip
zip     26.145.603 bytes, sha256 3b1c1b57f160112c821d02f23d946ede8b7f57a6ccf4632a25a512d334a9291f
binario ~/.local/bin/pandoc (pandoc 3.11), sha256 aec1331ed5eea2b6d497ac3610b6ad35dc1f10b4d41b6deac38e2dd005354e12
```

Paquetes de LaTeX agregados con tlmgr: `caption` y `xurl`.

**Suplementario en PDF.** `flagship/revision/suplementario_pdf.py` (nuevo)
convierte `SUPPLEMENTARY_storage_registry.md` a
`entrega_revision/13_suplementario_registro_almacenamiento.pdf`, 4 paginas. El
PDF sale de compilar con pdflatex el .tex que genera pandoc, para poder leer el
log. Falla si: falta el titulo actual del manuscrito o aparece el viejo; no hay
una longtable por cada tabla del Markdown; la primera celda con texto de alguna
tabla no llega al PDF; alguna URL del Markdown no llega entera; hay errores de
LaTeX o algun desborde de linea de mas de 2pt.

Al renderizar se encontraron tres defectos de formato del suplementario, los
tres corregidos en el Markdown sin tocar su contenido:

- Las URLs estaban entre backticks. Pandoc las emite como `\texttt{}`, que no
  tiene puntos de corte, y se salian del margen, cortadas en el borde de la
  pagina. Las seis URLs reales pasan a enlaces, que pandoc emite como `\url{}`
  y `xurl` parte.
- Una de las siete no es una URL sino un patron con marcadores,
  `..._-_<month>_<year>.pdf`. Como enlace, pandoc lo cortaba en el primer `>` y
  el PDF imprimia `%3Cmonth_.pdf>`. Vuelve a su forma literal con `\url{}` en
  crudo, que imprime los marcadores tal cual y se parte igual.
- El registro tenia nueve columnas de igual ancho, y "ContourGlobal" y
  "Metropolitana" se salian 10,1pt y 8,0pt sobre la columna vecina. Pandoc toma
  los anchos de los guiones de la linea separadora; ahora son proporcionales.

Y tres falsos negativos en las comprobaciones del propio script, tambien
corregidos: la clave de la tabla del registro era "1", el numero de fila, que
esta en cualquier texto; el respaldo unia la fila entera, que nunca sale
contiguo; y el cotejo de URLs fallaba porque `pdftotext` quita el guion de final
de linea ("CEN-" + "Reporte" sale "CENReporte"), asi que ahora ignora espacios y
guiones. Un control confirma que ese cotejo sigue detectando el enlace con
`%3C`.

El `.md` sigue siendo la fuente en `flagship/segan/`; su copia en
`entrega_revision/` se retiro, porque el PDF la reemplaza.

**Carta.** Tres oraciones al final del "third point of disclosure": el modelo
base del paper no es el mejor hurdle disponible; detenido temprano, elige un
octavo de los arboles y lo supera en 5.7% de CRPS; la Seccion 7 lista lo que hay
que leer con ese descuento; y el descuento no cambia ningun orden reportado,
incluido el del pronostico puntual, donde el hurdle detenido es peor en MAE,
como mide la Seccion 5.1. Los numeros se toman de `obj1d_deteccion_temprana.json`
al insertar, y la insercion aborta si 800/105 no redondea a un octavo. La
apertura del parrafo, sobre un borrador anterior de la respuesta, no se toco. La
carta sigue en 19 paginas.

**Version marcada.** En la tabla de politica de `bloques_marcado.py` entran 2.1,
4.4 y 6.3 como seccion entera, y 4.3 pasa de solo encabezado a seccion entera.
9 bloques nuevos, 49 en total, y todos verifican contra las dos fuentes; se
siguen omitiendo a proposito los 4 parrafos con matematica en display.
Las palabras fundidas impresas bajan de 9 a 1; la que queda esta en uno de esos
parrafos omitidos, en 4.2.

## 24. Carta: el third point of disclosure, sin el borrador

La primera mitad del "third point of disclosure" de la carta a la editora
divulgaba un error de un borrador de esta revision que los revisores nunca
vieron ("An earlier draft of this revision claimed..."). La divulgacion tiene
que ser sobre el manuscrito, no sobre versiones previas de la respuesta. Se
reescribio esa mitad y sale solo la referencia al borrador.

La sustancia se conserva entera: la ventaja de CRPS del predictivo
multi-cuantil, de dieciocho a treinta por ciento, exige un presupuesto del
orden de cinco mil arboles y casi desaparece al presupuesto propio del hurdle,
de ochocientos; los dos brazos comparten protocolo y no presupuesto; y la
Seccion 5.4 separa forma de presupuesto y reporta los dos efectos. Las tres
oraciones sobre el hurdle con deteccion temprana siguen igual.

Los numeros se derivan al insertar y la insercion aborta si no calzan con su
palabra: el 18 y el 30, de `fase0_tabla_por_modelo.csv` con el mismo calculo que
usa `verificar_manuscrito.py` para 5.3; el cinco mil, del brazo mas chico de la
escalera cuyo CRPS del test completo queda a menos de 0.5 MWh del mas grande
(5.400 arboles, la formulacion de 6.1); el ochocientos, del hurdle de
referencia. Lo que ocurre a presupuesto igual se dice con la frase del propio
manuscrito, "nearly disappears".

## 25. Cierre del 14 de septiembre (rama revision/cierre-14sep)

Arreglos de la auditoria de cierre del 12 de septiembre, un commit por bloque.
Cada bloque cierra con build limpio, `verificar_manuscrito.py` y
`verificar_referencias_cruzadas.py`.

### B1. Corridas no canonicas en fase4 (cota de alpha) y fase5

H7 alineo el generador en `fase2` y en la seccion de metricas de `fase4`, pero
quedaban dos llamadas con generador fresco: la cota de alpha de
`fase4_metricas_benchmarks.py` y la referencia Transporte+ACI de
`fase5_dependencia_panel.py`. Las dos continuan ahora el generador que
aleatorizo el score y consumen gamma = 0.02 antes que 0.05, como la corrida
canonica. Cada script aborta si su fila sin cota, o su referencia, no reproduce
la corrida canonica de `fase4_metricas_completas.csv`.

```
$VENV flagship/revision/fase4_metricas_benchmarks.py   # log fase4_20260913T050035
$VENV flagship/revision/fase5_dependencia_panel.py     # log fase5_20260913T050229
$VENV flagship/revision/fase1_hiperparametros.py
$VENV flagship/revision/fase9_tablas_tex.py
```

Lo que se mueve:

- Tabla 10, Transport+ACI (g=0.05): sin cota, 593 / 6.1% / 1028 pasa a
  596 / 5.9% / 1030, que es la fila de la Tabla 9. Con alpha_min = 0.005 el
  ancho pasa de 640 a 641, con 0.01 de 597 a 598. El costo de cobertura de la
  cota sigue en 0.5 puntos.
- Tabla 11, referencia Transport+ACI: 593 / 1028 pasa a 596 / 1030. Su peor
  desvio por tecnologia pasa de 0.28 a 0.29; se imprime 0.3 en los dos casos.
- Sin cambio: `fase4_metricas_completas.csv`, `fase4_diferencias_bootstrap.csv`,
  `fase5_diagnostico_dependencia.csv`, y en `fase5_cobertura_desagregada.csv`
  la cobertura en dias de alto vertimiento (86.72%) y el peor desvio regional
  (7.18). El ACI conserva la mejor cobertura condicional, 4.66 contra 4.83.

Texto: la carta (R1.5) decia "up to 6.1 per cent"; ahora 5.9, leido de
`fase4_metricas_completas.csv` al insertar. En la carta y en 5.6 sale "on one
case in sixteen", que venia del 6.1 y no tiene archivo fuente.

### B2. Cifras por ventana del pipeline completo

5.5 y la carta (R1.3) daban 176.3 / 100.0 / 104.2, los valores de
`fase2_aporte_por_componente.csv` anteriores a la alineacion del generador
(commit 5559072). Ahora -177.0 / +96.0 / +119.0, insertados desde el CSV en los
dos documentos; la Tabla 8 ya imprimia -177.0. Los tres intervalos siguen
excluyendo el cero ([-249.6, -106.8], [+16.0, +195.9], [+20.3, +242.9]), asi que
"all three significant" se mantiene. Chequeo nuevo en `verificar_manuscrito.py`:
la frase se arma desde el CSV y exige que las tres diferencias sean
significativas.

### B3. Tiempos de la Tabla 8, leidos del CSV

`fase9_tablas_tex.py` escribia la columna de costo de la Tabla 8 desde un
diccionario tipeado (+0.2, +7.1, +0.4, +6.1, +6.7). Ahora la lee de `d_segundos`
en `fase2_aporte_por_componente.csv`: el transporte solo pasa de +7.1 a +6.7 y el
pipeline completo de +6.7 a +6.6.

Texto, en 4.6, 5.5 y en la carta (parrafo inicial, tabla de R1.3, R1.3 y R2.4):
"6.1 of the 6.7 seconds" pasa a "6.1 of the 6.6 seconds"; "roughly ninety per
cent" y "ninety per cent of the runtime" pasan a "ninety-two per cent"
(6.1 / 6.6 = 92.4); "thirty-five times the runtime" pasa a "thirty-four times"
(6.7 / 0.2 = 33.5, redondeo hacia arriba en decimal exacto). Los dos se calculan
sobre los valores redondeados que imprime la tabla, para que el lector pueda
comprobarlos; con los segundos a dos decimales de `fase2_ablaciones.csv` el
multiplo seria del orden de 37, porque el 0.2 de la adaptacion es 0.18.

El chequeo de estos segundos en `verificar_manuscrito.py` leia
`fase2_ablaciones.csv` y toleraba 0.6 s, que es por donde paso el 6.7. Ahora arma
la frase desde `d_segundos` y la exige tal cual; se agrega el chequeo del
multiplo, que no existia.

### B4. R1.4: la sensibilidad gamma x ventana, ahora en el manuscrito

4.7 prometia la exhibicion de la rejilla 6x5 "in Section 5 ... and we say so
there" y la Seccion 5 no la tenia; la carta remitia a 5.8, que trataba solo la
frontera. `fase9_tablas_tex.py` emite ahora `tab_sensibilidad_hiper.tex`
(Tabla 13) desde `fase3_sensibilidad_test.csv`, en un bloque propio al final de
5.8, rotulada en la leyenda y en el texto como exhibicion posterior al cierre de
la seleccion, nunca como criterio. El titulo de 5.8 suma "the calibration
hyperparameters". Las remisiones de 4.7 y de la carta (R1.4 y su fila del cuadro
resumen) apuntan a la Tabla 13.

La rejilla tenia el bug de H7 en la unica celda que es configuracion de la
version enviada: (0.05, 60 dias) daba 593.4 / 6.08% / 1028.2 y contradecia a la
Tabla 9. `fase3_seleccion_hiperparametros.py` evalua ahora (0.02, 60) y
(0.05, 60) en el orden canonico y aborta si esas dos, o la seleccionada
(0.005, 120), no reproducen la Tabla 9. La seleccion no cambia:
`fase3_seleccion_validacion.csv` y `fase3_hiperparametros_elegidos.json` son
identicos.

Numeros de 5.8 y de la carta, desde el CSV: cobertura del transporte entre 89.9 y
90.1% en las treinta celdas; ningun infinito con gamma <= 0.01; entre 21.9 y
23.0% con gamma = 0.20, donde la carta decia "22 per cent". Dos chequeos nuevos
en `verificar_manuscrito.py` y tres anclas en `verificar_referencias_cruzadas.py`.

Con la Tabla 13, la tabla del Apendice C pasa a ser la C.14: se corrigen las dos
remisiones de la carta, el README del paquete, los mensajes del empaquetador y
`REVISION_PLAN.md`. Las menciones historicas de `Tabla C.13` en este changelog
quedan entre comillas de codigo, que es el convenio del verificador para citas
de numeracion vieja. Manuscrito 36 paginas; carta 20.

### B9. Tabla C.14 en ingles

El cuerpo de la tabla de hiperparametros salia en espanol en el PDF ("Horizonte
de pronostico", "Semillas"). `fase1_hiperparametros.py` emite ahora las filas en
ingles, en el CSV y en el .tex, y la cabecera del .tex, que viaja en el paquete,
tambien en ingles y sin la mencion a H11. De paso dejan de estar tipeados los
valores que son resultados y no constantes: gamma y ventana elegidos por origen
rodante se leen de `fase3_hiperparametros_elegidos.json`, los dias y filas de la
calibracion de `fase5_diagnostico_dependencia.csv`, y las muestras del CRPS y del
bootstrap de las firmas de `crps_pred` y `bootstrap_diferencia`.

Las etiquetas de las semillas son cortas y no aparecen en la prosa ("Training of
the base models", "PIT atom and map bootstrap", "Sampling of the CRPS",
"Bootstrap of differences, blocks and permutations"), porque la guarda del
empaquetador y `verificar_manuscrito.py` las buscan en el PDF para comprobar que
cada fila se imprime. Se actualizan las dos, y las busquedas por nombre del
verificador.

### B7. Remisiones erradas en el cuerpo de la carta

- R1.2: "equation (5)" para el shrinkage pasa a (4); la (5) es el interval score.
  Ancla nueva en `verificar_referencias_cruzadas.py` para esa ecuacion.
- R1.3: "Section 4.6 closes by noting that neither survives its ablation" decia lo
  contrario de 4.6 y de la propia respuesta a R2.4. Ahora: la combinacion no
  sobrevive su ablacion y el shrinkage la sobrevive pero no paga su costo. Se
  actualiza el ancla del verificador, que fijaba la frase vieja.
- R2.7: la distincion de las tres garantias esta en la antepenultima oracion del
  abstract, no en las dos ultimas; se corrigen las dos menciones.
- Nota editorial: el pais no aparece en las keywords; sale esa mencion.
- Q8/Q9: las Secciones 4 y 5 tienen eight y eight subsecciones, no siete; el numero se
  cuenta sobre el .tex al insertar.
- Fronteras de la ventana: son cinco definiciones alternativas mas la oficial, no
  "six alternative". Criterio unico en la carta (cuadro resumen, R2.2, R2.3) y en
  5.8, que ahora dice "five alternative definitions of the window besides the one
  used"; el numero sale de `fase6_sensibilidad_frontera.csv` y lo chequea el
  verificador.
- Apendice D: da el entorno y las semillas y remite al repositorio para la
  secuencia de comandos. Las tres remisiones de la carta dicen ahora eso.
- Apendice C: la carta decia que las rejillas estaban en la tabla y no estaban.
  `fase1_hiperparametros.py` suma un bloque "Hyperparameter selection" con la
  rejilla de gamma, la de la ventana, la particion interna y el criterio, leidos
  de las constantes de `fase3_seleccion_hiperparametros.py`, y mueve ahi las dos
  filas de lo elegido.

### B5. Almacenamiento en la carta

El punto 3 de R2.2 decia "Storage now appears in three places" (2.2, 6.3 y la
declaracion de disponibilidad) y que en 6.3 el almacenamiento se referia al
quiebre de tendencia "not the distributional shift". Las dos cosas eran falsas:
aparece tambien en 1, 2.1, 5.1, 6.4 y tres veces en 7, y 1 y el primer parrafo de
6.3 lo nombran entre los mecanismos candidatos del cambio distribucional. El
manuscrito no se toca: enumerar mecanismos candidatos es lo honesto. La carta
dice ahora lo verificable: ninguna parte atribuye el cambio causalmente al
almacenamiento; aparece como uno de varios mecanismos candidatos (1 y 6.3), como
hipotesis acotada para el quiebre de tendencia (6.3 y 7), como literatura (2.1 y
2.2), y en el resto solo como informacion que el dataset no tiene (5.1 y 7), en
la observacion de que ningun sistema entro en operacion en junio de 2025 (6.4) y
en la declaracion de disponibilidad. Sale "not the distributional shift".

### B6. Referencias a versiones que los revisores nunca vieron

Carta: sale "the previous version of this response asserted it ... That was our
error and it is corrected" (R1.1), junto con "the part that goes against the
previous wording" y "than we first used", que aludian al mismo borrador; sale
"an earlier draft of this revision named only the method" (nota editorial); y
sale la cifra "from 431 words to 248", porque 431 era un borrador interno (el
abstract enviado tenia unas 290 palabras segun la regla de conteo) y el limite
de 250 se cumple con cualquier regla. Quedan "brought within the 250-word limit"
y la sustancia de cada parrafo.

Manuscrito: la leyenda de la Figura 8, la de la Tabla 6 y su fila decian "the
previous revision" o "the submitted revision"; la version enviada no tenia ese
analisis ni tres modelos base, asi que no se usa "submitted": las quince celdas
son "the three-model design of Table 5", que es lo que son. Lo mismo en las dos
menciones de "the original design" en 5.3, y en 7 "a question the previous
revision could only declare" pasa a "a question that the comparison of Section
5.3 leaves open". La leyenda quemada de la figura (`fase9_figuras_revision.py`)
dice ahora "Three-model design (15 cells)", con los conteos leidos de las celdas.

Numeros que estaban tipeados en el generador de la Tabla 6 y ahora se leen: el
rango de sobre-cobertura de las quince celdas, [-2.06, +5.34], de
`fase0_diagnostico.csv`; las 2,000 replicas y la semilla, de
`fase0b_diagnostico.json`. Chequeo nuevo del rango en la prosa de 5.3.

### B8. Cuadro resumen de la carta

- "We respond to each of the fifteen comments" pasa a los twelve comentarios
  numerados, mas la nota editorial y las preguntas estructuradas. El 12 se
  cuenta sobre `revision/informe_revisores_SEGAN-D-26-03850.md`.
- Q4 decia cuatro figuras y diez tablas nuevas; contra la version enviada (tag
  submitted-segan-v1: cuatro figuras, dos tablas) son five figuras, porque la
  Figura 3 tambien es nueva, y twelve tablas: la Tabla 1, las 4 a 13 y la C.14.
  El cuerpo y la fila del cuadro resumen dicen ahora eso; los dos conteos se
  calculan sobre los dos .tex al insertar.
- Q7: la Seccion 7 tiene ten items y la carta enumeraba nueve; se agrega el
  que faltaba, la separacion de forma y capacidad con el descuento del hurdle.
- Filas nuevas para Q3 y Q5 en el cuadro resumen, que tenian respuesta en el
  cuerpo y no tenian ubicacion.

### B10. Comentarios internos del .tex y restos de test_ramp

- La cabecera del manuscrito, 34 lineas de comentarios en espanol con
  `test_ramp`, "storage deployment", H1, la version 6.0 y una numeracion de
  secciones vieja, viajaba en el zip. Pasa a seis lineas en ingles sin
  referencias internas. En el cuerpo no habia otros comentarios que los
  separadores.
- Las cabeceras de los cuerpos de tabla generados, que tambien van en el zip,
  pasan al ingles (`fase9_tablas_tex.py`); la de la Tabla C.14 ya lo estaba desde
  B9. Los trece .tex de tabla cambian solo en esas dos lineas.
- Ninguno de los archivos de resultados con `test_ramp` entra en el zip, que
  lleva solo el .tex, los cuerpos de tabla, las figuras, la clase y el README; la
  unica aparicion de `test_ramp` en el paquete era ese comentario. Fuera del
  paquete, las salidas fechadas de `flagship/` que conservan la clave (siete
  .txt y dos .csv) se anotan con la politica que la carta declara en R2.2,
  punto 4: nota en la primera linea de cada .txt y
  `flagship/NOTA_RESULTADOS_FECHADOS.md` con la lista. El prototipo
  `conformal_prototype.py` lleva la misma nota.

### B11. README del paquete de fuentes

Decia "no numeric value in the manuscript is typed by hand", que B3 desmintio
y que en todo caso es demasiado amplio: la prosa se escribe y se coteja. Dice
ahora que cada cuerpo de tabla sale de un archivo de resultados y la Tabla C.14
del codigo, que los numeros de la prosa los coteja `verificar_manuscrito.py`, y
atribuye las Figuras 1, 2, 3, 5 y 6 a `flagship/generar_figuras_paper.py` y las
4, 7, 8 y 9 a `fase9_figuras_revision.py`; antes las atribuia todas a esta
ultima. El indice de tablas del README ya se habia actualizado en B4.

### C1. Interval score unilateral con multiplicador 1/alpha

`rev_lib.interval_score_unilateral` usaba `2/alpha`, el multiplicador del
interval score central, que pone alpha/2 en cada cola y queda minimizado por el
cuantil 1-alpha/2. En un limite unilateral [0,U] toda la masa alpha esta en la
cola superior: `IS = U + (1/alpha) max(y-U, 0)`, que es `pinball_{1-alpha}/alpha + y`
y lo minimiza el cuantil 1-alpha que calibran todos los metodos. El docstring
decia que la version con 2/alpha era "el pinball loss del cuantil 1-alpha
multiplicado por 2/alpha"; era falso, y queda anotado en el propio docstring.
`pinball` se deriva ahora del score. La formula cambia tambien en el docstring
de `fase4_metricas_benchmarks.py`, en la fila "Primary metric" de la Tabla C.14,
en la ecuacion de la Seccion 4.8 y en R1.5 de la carta; las dos ultimas ganan una
frase que justifica 1/alpha. No se reportan las dos metricas.

Corridas, sin reajustar ningun modelo base:

```
$VENV flagship/revision/fase0_model_agnostic.py
$VENV flagship/revision/fase0_diagnostico.py
$VENV flagship/revision/fase2_ablaciones.py
$VENV flagship/revision/fase4_metricas_benchmarks.py
$VENV flagship/revision/fase5_dependencia_panel.py
$VENV flagship/revision/fase3_seleccion_hiperparametros.py
$VENV flagship/revision/fase6_cronologia.py --solo-fronteras
$VENV flagship/revision/fase0b_diagnostico_ampliado.py
$VENV flagship/revision/fase1_hiperparametros.py
$VENV flagship/revision/fase9_tablas_tex.py
$VENV flagship/revision/fase9_figuras_revision.py
```

**Guarda de invariancia (C1.2), contra 62982f8 celda a celda.** Identicos: las U
y las y por fila de las tres series de la Fase 0; cobertura, error estandar,
anchos, fraccion de infinitos, conteos, CRPS y Brier en todas las tablas; el
bloque diagnostico de quince celdas y el de cuarenta completo (r = -0.873,
pendiente -4.89, intercepto, IC bootstrap, leave-one-out, rango y quiebre); la
seleccion de la Fase 3 (ACI gamma 0.005; Transporte+ACI gamma 0.005 con 120
dias); qhat = 0.9242 en el log de la Fase 5; las 41 filas de la Tabla C.14 salvo
la metrica principal. Cambian solo `IS_finitos`, `IS_total`, las diferencias de
IS con su IC y su significancia, y los segundos de reloj de la Fase 2, que se
miden de nuevo en cada corrida.

**C1.3a, H7 en las fronteras de la Fase 6.** La seccion de fronteras corria
Transporte+ACI con gamma 0.05 sin haber corrido antes gamma 0.02 sobre el mismo
generador, asi que su flujo aleatorio no era el canonico. Ahora corre 0.02 y
despues 0.05, como fase0, y una asercion exige que la ventana oficial reproduzca
la fila de fase0 (hurdle, test_transition). Se mueven solo los anchos de
Transporte+ACI en la Tabla 12, a lo sumo 3.8 MWh (oct 2024-feb 2025, 791.1 a
787.3; sep 2024-mar 2025, 772.2 a 768.8); cobertura y fraccion de infinitos no
cambian, y las filas del split estatico y de ACI son identicas.

**C1.3b.** Las Tablas 11 y 12 llevan la columna de fraccion de intervalos
infinitos junto al IS restringido a finitos.

**C1.5, frases escritas desde el CSV regenerado.**
- 5.5 y R1.3, parrafo final: el pipeline completo mejora 286.5 MWh en la
  transicion; en 2025-S1 y 2025-S2 las diferencias (+58.8 y +14.3) tienen IC que
  contienen el cero, y en 2026-S1 mejora 14.7 con IC que lo excluye; sobre todo
  el test neto -32.3 [-70, +9]. Donde decia "not better than the static split"
  dice "not distinguishable from the static split ... and we do not read that as
  a positive result". El "all three significant" de B2 desaparece porque ya no
  es cierto.
- 5.5 y R1.3: el transporte empeora sobre ACI en cuatro de las cinco ventanas,
  significativamente en tres (el conteo se emite del CSV).
- 5.3 y R1.1: la diferencia de IS con el GBM es +14.5 [+4.9, +24.0] y ahora
  tambien excluye el cero; el mejor de los dieciocho es el GBM con el split
  estatico en cuatro de las cinco ventanas (eran tres).
- 5.6 y R2.6: los cuatro benchmarks superan a todo esquema sobre el hurdle y cada
  uno difiere del split estatico con IC que excluye el cero (eran tres); tres de
  ellos compran el score con cobertura (433 a 86.5 %, 486 a 87.2 %, 639 a
  82.4 %); CQR 438 contra 596 MWh y 813 del pipeline enviado.
- 5.7 y R2.5: la calibracion por central y Mondrian por region tienen los dos
  mejores IS marginales del grupo.
- 5.8 y R2.3: el orden de los tres metodos se afirma por cobertura, que es lo que
  se sostiene en las seis ventanas; el split estatico sobre-cubre 4.0 a 5.3
  puntos y tiene el peor IS finito en las seis; Transporte+ACI da limites
  infinitos en tres, 5.5 a 8.1 %; la ganancia aparente sigue a la
  sobre-cobertura (Pearson r = -0.844 sobre las seis).
- Introduccion, 3, 4.6, 5.5, carta y R2.4: el shrinkage es ocho decimos de uno
  por ciento de un IS de unos 810 (eran seis de 1 030) y 6.16 de 6.79 segundos,
  noventa y uno por ciento (eran noventa y dos). Se borra la frase de "three
  orders of magnitude", que no salia de ningun archivo.
- C1.7: "thirty-seven times" sale de `d_segundos`, 7.75 / 0.21 = 36.9.

**C1.6.** Tablas 4 y 8 a 13 y Figura 9 regeneradas. La Tabla 8 y la carta dan
los segundos con dos decimales. La Figura 9 toma los limites del eje de los
datos y las etiquetas de costo del CSV; antes llevaban +7.1 y +6.7 tipeados.

**Verificador.** 66 a 76 afirmaciones. Los chequeos de IS que llevaban el valor
tipeado se arman ahora desde el CSV; los nuevos cubren las frases de C1.5 y la
afirmacion de 4.8 de que, con la cota de alpha, el transporte sigue peor que la
adaptacion pura en los seis pares cota x gamma.

**Lo que se mueve y no toca texto.** Con los hiperparametros de la Fase 3
(bloque propio de la Tabla 9), Transporte+ACI queda en 761.2 y ACI en 762.6; con
2/alpha eran 957.8 y 935.8. Ninguna frase compara esas dos filas; se reporta al
autor.

```
$VENV flagship/revision/verificar_manuscrito.py            # 76 de 76
$VENV flagship/revision/verificar_referencias_cruzadas.py  # exit 0
# manuscrito 37 paginas (eran 36: las columnas nuevas y las frases de C1.4 y
# C1.5 empujan la ultima referencia a la pagina 37), carta 21, cero errores y
# cero referencias sin resolver; el overfull de 1.3 pt de tab_benchmarks ya
# estaba en 62982f8
```

### C7. Verificacion de la bibliografia

R2.1 de la carta decia que cada DOI se habia resuelto contra Crossref y que el
script y la tabla estaban en el repositorio. La tabla,
`resultados/fase8/referencias_verificadas.csv`, tenia 19 de los 40 DOI, y el del
dataset no esta en Crossref: Zenodo registra en DataCite y Crossref devuelve 404.
`fase8_buscar_referencias.py` gana el modo `cotejar`, que lee la bibliografia del
manuscrito, resuelve los 40 DOI (39 en Crossref, el del dataset en DataCite) y
coteja titulo, primer autor, anio y revista contra la entrada. Cotejan los 40, y
los 40 titulos aparecen completos en su entrada. Econometrica 78(3)
(chernozhukov2010) no trae autores en Crossref; el primer autor se coteja contra
OpenAlex. Las tres entradas sin DOI son de NeurIPS (tibshirani2019, gibbs2021, romano2019) y
quedan listadas sin cotejo.

```
$VENV flagship/revision/fase8_buscar_referencias.py cotejar   # 40 de 40, exit 0
```

La frase de la carta se reescribe con los conteos de
`resultados/fase8/bibliografia_cotejada.csv` y pierde "Three candidate references
were dropped because their DOIs did not resolve cleanly", que no tiene respaldo en
ningun archivo. `referencias_verificadas.csv` queda como estaba. Las dos filas de
este CHANGELOG que decian "nada entra sin DOI resuelto" y "todas con DOI
verificado" se corrigen por las tres de NeurIPS.

Para el autor, sin cambio en el texto: OpenAlex da a dos de las entradas de NeurIPS
una paginacion corrida en cuatro o cinco paginas (tibshirani2019, 2526-2536
contra 2530-2540 en la entrada; romano2019, 3538-3548 contra 3543-3553).
NeurIPS circula con dos paginaciones.

### C2. El diagnostico en la region a la que se acota el enunciado

`fase0b_diagnostico_ampliado.py` agrega el ajuste sobre las 25 celdas en que el
split estatico sobre-cubre (sobre-cobertura >= 0), con su IC sobre las mismas
2 000 replicas de bloques de dia. El conjunto se fija en la muestra completa y no
consume numeros aleatorios, asi que todo lo anterior del json queda identico
(comprobado clave a clave contra 9981eb3, igual que `fase0b_celdas.csv`); la unica
clave nueva es `sobrecubren`. r = -0.870 [-0.928, -0.528], pendiente -6.97
[-7.90, -3.60], intercepto +11.97 [+3.06, +17.07].

```
$VENV flagship/revision/fase0b_diagnostico_ampliado.py
$VENV flagship/revision/fase9_tablas_tex.py      # solo cambia tab_diag_ampliado.tex
```

- Tabla 6: fila nueva con su intervalo; la leyenda la nombra.
- 5.3: una oracion, al final del parrafo que acota el enunciado a la
  sobre-cobertura: en esa region la pendiente es mas empinada y la relacion
  conserva signo y fuerza. Las tres cosas se exigen a los numeros en el
  verificador, no solo a la frase.
- Abstract: "is linear in" pasa a "grows with". El titular sigue en -4.89 sobre
  cuarenta celdas; lo que no sobrevivia era la forma lineal, que la Seccion 5.3
  declara no determinada por debajo del nominal.
- No se tocan las frases con "linearly related" de 5.3 (quince celdas), de la
  Seccion 8 ni de la carta (quince celdas, r = -0.755): las tres hablan de la
  sobre-cobertura, donde la relacion se sostiene.

```
$VENV flagship/revision/verificar_manuscrito.py   # 79 de 79
# manuscrito 37 paginas, carta 21, cero errores y cero referencias sin resolver
```

### C3 y C4. Afirmaciones acotadas a lo verificado

- Seccion 7 y carta al editor: "The discount runs in one direction ... and it
  changes no ordering reported here" afirmaba una direccion para tablas que nunca
  se re-corrieron con el hurdle detenido. Ahora dice que no se re-corrieron y que
  no se afirma direccion; la unica comparacion re-corrida, la Tabla 2, va en la
  direccion contraria (el detenido mejora el CRPS y empeora el MAE hasta quedar
  ultimo). Se conserva el margen de mas de veinte por ciento contra la forma
  cuantilica.
- Seccion 1: "To our knowledge no open curtailment dataset" pasa a "We are not
  aware of an open curtailment dataset".
- Abstract: "53 continuous months (hydropower from June 2024)". La fecha es la de
  la Seccion 3.1 y el verificador exige que sean la misma. 247 palabras contando la
  expresion matematica como una, 248 como tokens.
- 4.2: dos oraciones. La traslacion unica delta = log c / sigma que motiva el
  transporte existe porque el hurdle usa una sola dispersion; con dispersion
  condicional varia con x y con la predictiva multi-cuantil el desplazamiento
  depende de cada distribucion, asi que para esos dos modelos base el transporte es
  el mismo algoritmo sin esa motivacion.
- 4.4, panel sintetico: el encargo suponia que no existia como artefacto. Existe:
  `flagship/conformal_v2.py` corre el weighted conformal por punto sobre el panel
  sintetico de 40 centrales, y su salida congelada,
  `resultados/v_enviada/conformal_v2_tabla.csv`, da 76.0 % de limites infinitos en
  la ventana de transicion, 49.3 % en 2025-S1 y 19.9 % en 2025-S2. La frase se
  conserva y apunta al script; el verificador abre la tabla.
- 4.4, benchmark de recencia: se cumple la promesa identificandolo. La ventana
  deslizante es el esquema de pesos fijos de Barber et al. con pesos 0/1 (uno a
  los 60 dias previos al embargo): `ventana_deslizante` usa `q_conformal`, con
  k = ceil((n+1)(1-alpha)) sobre la ventana, que es el cuantil ponderado de Barber
  con esos pesos.

```
$VENV flagship/revision/verificar_manuscrito.py   # 81 de 81
# manuscrito 37 paginas, carta 21, cero errores y cero referencias sin resolver
```

### C5. Carta y texto contra sus archivos

Ya forzado por C1: R2.3 acota el orden a la cobertura y R2.6 dice que el
bootstrap es contra el split estatico. Lo demas:

- 5.2: el contraste de 2025-S1 se imprime desde `fase6_wasserstein.csv` con los
  cuatro decimales del archivo: W1 0.1722, IC [0.0703, 0.3665], umbral 0.1931. A
  tres decimales el 0.3665 se leia 0.367, y la propia verificacion de la Fase 6
  lo imprime 0.366; el valor sin redondear no esta guardado, asi que se imprime
  el del archivo. El verificador compara punto, IC, umbral y veredicto.
- R1.1: "100.6 against 141.1" queda rotulado como ventana de transicion
  (`obj1b_escalera.csv` y `obj1_capacidad.csv`, test_transition: 100.58 y 141.07).
- R1.1: "almost none" pasa a "9.5 per cent" (`obj1c_mecanismo.json`,
  `share_sigma` 9.53).
- **Retenido para decision del autor:** el umbral de 2025-S1, 0.215 a 0.193, no
  se agrega a la lista de correcciones de la carta. Ninguna de las seis filas de
  esa lista esta en la version enviada (tag `submitted-segan-v1`: el .tex no
  contiene "Wasserstein", "permutation", "0.28", "hour 16", "fifteen minutes" ni
  "0.04"). Son las seis filas con reproduce = NO de
  `fase6_verificacion_afirmaciones.csv`, que verifico el borrador de esta
  revision, y la tabla entro en 77556ca rotulada como version enviada. Agregar
  una septima con el mismo criterio repetiria el error.

```
$VENV flagship/revision/verificar_manuscrito.py   # 81 de 81
```

### C6. El verificador

Sobre la prueba de mutacion de la auditoria (60 chequeos, solo caian 2):

- (i) Las filas que solo buscaban la frase abren ahora su archivo y la arman
  desde el valor: ventaja del GBM a presupuesto equiparado y deterioro del hurdle
  al quintuplicar capacidad desde `obj1_capacidad.csv` y `obj1b_escalera.csv`
  (incluido el 100.6 contra 141.1 de 2 700 arboles); desplazamiento del cuantil
  conformal desde `obj1c_mecanismo.json`, que ademas recalcula el 93 %; CRPS de la
  transicion y mediana de positivos desde sus CSV.
- (ii) Las cuatro filas del diagnostico ampliado buscan solo en la prosa
  (`en_prosa`, el .tex sin expandir los cuerpos de tabla) y con la frase entera
  del abstract y de 5.3, no con la cifra suelta, que tambien esta en la Tabla 6.
- (iii) Contraste de 2025-S1: hecho en C5 (punto, IC, umbral y veredicto).
- (iv) Segundos del shrinkage: la tolerancia de 0.6 s ya se habia quitado en B3.
- (v) Cruce de la carta contra el manuscrito sobre los dos PDF: se corre como
  compuerta antes de empaquetar y no se commitea. Sobre el build de C5 marca siete
  numeros de la carta sin contraparte en el manuscrito: cinco son citas de la
  lista de correcciones (0.04, 0.06, 0.08, 0.105, 0.947), 0.59 es la concordancia
  de ancho del log de la Fase 0 y 9.5 es el reparto de `obj1c_mecanismo.json`, que
  el manuscrito da como 0.9270. Ninguno es un numero movido por el rerun.
- Etiquetas de seccion: la columna `seccion` del CSV ya no se escribe a mano.
  `chk` la toma de donde `en_tex` o `en_prosa` encontro la frase, numerando
  secciones y subsecciones con la regla de LaTeX, asi que no puede desfasarse; las
  filas de tabla conservan su etiqueta (Tabla 5, Tabla 6, C.14, antes C.11 y
  C.13).

```
$VENV flagship/revision/verificar_manuscrito.py   # 81 de 81
```

### C8. Documentos internos

- `HALLAZGOS_CRITICOS.md`: "Los cuatro hallazgos" pasa a H1 a H11 y el conteo del
  verificador a 81 de 81. H3 gana la nota posterior a H7 y a C1, con las cifras en
  1/alpha. H11 queda resuelto (longtable, 41 filas, hoy Tabla C.14, citada asi en
  R1.2 y R2.4) y ya no dice pendiente.
- `DECISIONS.md`: entradas del 1 de septiembre (reencuadre diagnostico) y del 14
  (1/alpha), y la ronda tres con las cuatro notas P2 y la comparacion de las
  configuraciones de la Fase 3.

### C5b. Fuera la lista de correcciones atribuida a la version enviada

Decision del autor, sobre el item retenido de C5. La subseccion "Corrections we
made on our own initiative" de la carta atribuia a la version enviada seis
afirmaciones descriptivas que no estan en ella: el .tex de `submitted-segan-v1` no
contiene ninguna, y salen del borrador de esta revision que verifico
`fase6_verificacion_afirmaciones.csv`. Lo mismo valia para sus dos "matters of
process" y para la linea de las veinticuatro afirmaciones. Se quita la
subseccion entera, y la carta al editor pierde la frase que remitia a ella y
queda con un solo punto de divulgacion, la seleccion de hiperparametros. El
umbral 0.215 a 0.193 queda sin efecto.

El manuscrito tenia la misma afirmacion como item de la Seccion 7 ("Six
descriptive statements of the submitted version did not reproduce ... twenty-four
in total") y se quita con el mismo criterio. La Seccion 7 pasa de diez a nueve
items; la carta lo dice asi en la fila Q7 del cuadro resumen y en la respuesta a
Q7, con el conteo hecho sobre el .tex. Las correcciones siguen en el texto (3.3 y
4.8); lo que se quita es la atribucion. HALLAZGOS H4 lleva la nota.

```
$VENV flagship/revision/verificar_manuscrito.py   # 81 de 81
# manuscrito 37 paginas, carta 21, cero errores y cero referencias sin resolver
# compuerta carta contra manuscrito: quedan 0.59 (log de la Fase 0) y 9.5
# (obj1c_mecanismo.json), los dos con fuente propia
```

### L1. Lectura pagina por pagina de los dos PDF

Comprobacion manual 2 del encargo, sobre el build de C5b. Lo que ningun
verificador ve:

- Manuscrito, Seccion 7: el item "Six descriptive statements of the submitted
  version did not reproduce", con la misma atribucion falsa de la carta. Se quito
  en C5b.
- Manuscrito, 5.8: "Calibration hyperparameters.." con doble punto; elsarticle
  agrega el punto al `\paragraph`. Se quita el del argumento.
- Manuscrito, Tabla C.14: `esc` de `fase1_hiperparametros.py` escapaba las llaves
  despues de insertar `\^{}`, y el PDF imprimia un acento sobre llaves literales
  en "(sd_boot(u)/tau)^2", "F_new^{-1}" y "sigma^2". Ademas no escapaba `~`, que
  LaTeX lee como espacio duro: "lambda ~ 1" salia "lambda   1" y "U ~ Uniform"
  salia "U   Uniform". Ahora las llaves van primero, `^` pasa a
  `\textasciicircum{}` y `~` a `$\sim$`. Cambian cuatro filas de
  `hiperparametros.tex`; el CSV no cambia.
- Carta: la pagina 3 estaba en blanco desde P0, por el `\clearpage` antes del
  cuadro resumen. Con `\newpage` el cuadro empieza en la pagina 3 y la carta queda
  en 20 paginas; probado contra la variante sin salto, que da lo mismo.
- Comprobacion manual 1: la carta cita la Tabla C.14 dos veces, en R1.2 y en R2.4,
  y el `.aux` la numera C.14.
- `empaquetar_fuentes.sh` espera 37 paginas.

```
$VENV flagship/revision/fase1_hiperparametros.py
$VENV flagship/revision/verificar_manuscrito.py   # 81 de 81
# manuscrito 37 paginas, carta 20, sin paginas en blanco, cero errores
```

### Notas en documentos internos y ronda tres (encima del tag `submission-2026-09-14`)

El tag `submission-2026-09-14` queda en a95d31b, que es lo enviado; esto viene
despues. Nada se regenera ni se recompila.

- `BRIEFING_ESTRATEGIA.md` y `resultados/fase0_model_agnostic.md` llevan una nota
  de cabecera en vez de reescribirse. Son documentos internos fechados, y es la
  misma politica que la carta declara en R2.2, punto 4: los documentos internos
  fechados se anotan, no se reescriben. La del segundo es la que importa: vive en
  el repositorio que cita el paper, y desde C1 decia que la diferencia de interval
  score del GBM contenia el cero cuando el paper dice que lo excluye. La nota da
  ademas la causa de su ajuste de quince celdas (-0.757, -4.39, +5.49): se calculo
  sobre las entradas de `fase0_diagnostico.csv` redondeadas a un decimal, lo que
  corrigio D1 (seccion 10.4). Comprobado reajustando esas dos columnas del CSV de
  77556ca: -0.7567, -4.386, +5.4864.
- `REVISION_PLAN.md`: la Seccion 7 tiene nueve limitaciones, no diez (C5b), y el
  inventario gana la fila de la Tabla 13, que B4 agrego al manuscrito y no al plan.
- `DECISIONS.md`, ronda tres: el empate de la Fase 3 (761.2 contra 762.6), el
  "statistically indistinguishable" sin bootstrap pareado y la paginacion de
  NeurIPS.
- `entrega_revision/`: las copias 4, 5, 8 y 9 quedan iguales a sus fuentes. La 6 y
  la 7 no cambian: la verificacion independiente declara el commit que verifico y
  el informe de los revisores es literal.

