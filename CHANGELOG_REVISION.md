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
| `flagship/revision/fase9_figuras_revision.py` | Figuras 6, 7 y 8 | Q4, R1.2, R1.3 |
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
| Subseccion nueva: ablaciones | R1.3 | \S5.4 |
| Subseccion nueva: benchmarks, metricas e infinitos | R1.5, R2.6 | \S5.5 |
| Subseccion nueva: dependencia de panel y cobertura condicional | R2.5 | \S5.6 |
| Subseccion nueva: sensibilidad de la frontera | R2.3 | \S5.7 |
| Discusion reescrita alrededor del diagnostico | R1.1, Q5 | \S6 |
| **Seccion nueva de limitaciones, nueve items** | Q7 | \S7 |
| Conclusion reescrita | R1.1, R2.7, Q5 | \S8 |
| Apendice C nuevo: hiperparametros; apendice D nuevo: reproducibilidad | R1.2, R2.4 | apendices |
| Bibliografia de 10 a 43 entradas, todas con DOI verificado | R2.1 | bibliografia |
| Algoritmo 1 y figuras 6, 7 y 8 nuevas | R1.2, R1.3, Q4 | varias |
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

**Ademas, alineamiento de la penalizacion de la figura 5.**
`generar_figuras_paper.py` calculaba los puntos de cambio con un estimador
robusto del ruido y un factor 3; devolvia los mismos dos quiebres, pero la
especificacion no coincidia con la declarada en el manuscrito. Ahora usa la
misma convencion BIC que `fase6_cronologia.py`, `pen = sigma^2 log n` con
`sigma^2` la varianza de la serie. Reproducir:

```
$VENV flagship/generar_figuras_paper.py
# fig5: quiebres ['2023-05', '2024-01'], penalizacion 3.0269
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
- Las figuras 1 a 5.
- Los resultados de `conformal_v3_tabla.csv`, salvo la etiqueta de la ventana.
- El encuadre agnostico sobre las causas del cambio de regimen, que es deliberado
  y anterior a esta revision.
