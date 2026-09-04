# REVISION_PLAN — SEGAN-D-26-03850

Triage de los quince comentarios de revision mayor, mapeados a los archivos que
hay que tocar y al comando que regenera cada resultado.

**Manuscrito:** `flagship/segan/SEGAN_paper_FINAL.tex`
**Informe de los revisores, literal:** `revision/informe_revisores_SEGAN-D-26-03850.md`
**Rama:** `revision/reframing`
**Entorno:** `/Users/pabloreyescerda/Desktop/PROYECTO-CURLTAIMENT/curtailmentiq-model/venv/bin/python`
(python 3.12.3, pandas 3.0.3, numpy 2.4.6, scikit-learn 1.9.0, xgboost 3.2.0,
ruptures 1.1.10, statsmodels 0.15.0)

**Decision de alcance tomada por los autores (2026-09-01):** ante el hallazgo H1
de `HALLAZGOS_CRITICOS.md`, la contribucion metodologica se reencuadra como
**resultado diagnostico**: la ganancia de una capa conformal adaptativa mide la
mala calibracion del modelo base, y esa relacion es cuantificable. Se conservan
las tablas de la version enviada como el caso del hurdle y se anaden los brazos
del GBM multi-cuantil y del hurdle con sigma(x).

---

## Estado de la reproducibilidad de partida

Antes de tocar nada se verifico que el entorno reproduce la tabla oficial de la
version enviada, bit a bit:

```
<venv>/bin/python flagship/conformal_v3_real.py
git diff --stat flagship/conformal_v3_tabla.csv     # sin diferencias
```

Ademas, la rama del hurdle del experimento de la Fase 0 reproduce
`conformal_v3_tabla.csv` en las 30 celdas x 4 metricas, verificado por asercion
dentro del propio script (`verificar_reproduccion`). Los resultados de la version
enviada quedan congelados en `resultados/v_enviada/` y ningun script de la
revision escribe sobre ellos.

---

## Los quince comentarios

Leyenda de estado: `hecho` / `en curso` / `pendiente` / `refutado`.

### Revisor 1, comentarios numerados

| # | Tema | Accion tomada | Ubicacion del cambio | Esfuerzo | Estado |
|---|---|---|---|---|---|
| **R1.1** | Solo se usa el hurdle; no se puede saber si la ventaja de Transport+ACI es de la capa o del modelo base. Sugiere un GBM multi-cuantil y repetir **todos** los experimentos | GBM multi-cuantil de 54 cuantiles entrenado con disciplina identica, mas el hurdle sigma(x) como tercer brazo. Protocolo conformal completo sobre los tres. **La ganancia no se replica.** Ver H1 | `flagship/revision/rev_lib.py`, `fase0_entrenar_qgbm.py`, `fase0_model_agnostic.py`, `fase0_diagnostico.py`; `resultados/fase0_model_agnostic.md`; .tex seccion 5 nueva y abstract | alto (8 min de entrenamiento + reescritura de la contribucion) | **hecho** |
| **R1.2** | La descripcion de Transport+ACI es conceptual: faltan largo de ventana, regla de cuantiles, interpolacion, repeticiones bootstrap, funcion e intensidad del shrinkage, orden de ejecucion. Pide diagrama de flujo | Pseudocodigo completo, diagrama de flujo, tabla unica de hiperparametros con semillas, y declaracion explicita del orden transporte/ACI | .tex apendice nuevo y seccion 4.3; `resultados/fase1/hiperparametros.csv`; figura `fig6_diagrama_flujo.pdf` | medio | **hecho** |
| **R1.3** | Ablaciones inadecuadas: pide ACI puro, Transport+ACI sin shrinkage y Transport+ACI completo, y verificar si la complejidad computacional se justifica | Cinco grupos (se anaden split estatico y transporte sin ACI para cerrar el factorial), con aporte marginal e IC bootstrap por bloques de dia y costo en segundos. **El transporte empeora y el shrinkage no aporta.** Ver H3 | `flagship/revision/fase2_ablaciones.py`; `resultados/fase2/`; .tex seccion 5 y Tabla nueva | medio | **hecho** |
| **R1.4** | La seleccion de hiperparametros no esta validada. Pide validacion independiente o de origen rodante dentro de train y calibracion, sensibilidad a ventana y gamma, y test reservado a una sola evaluacion | Origen rodante dentro de la calibracion (interna ene-abr 2024, validacion may-ago 2024), criterio interval score. Selecciona gamma = 0.005 y ventana de 120 d, no los del paper. Sensibilidad 6x5 sobre el test declarada como exhibicion posterior | `flagship/revision/fase3_seleccion_hiperparametros.py`; `resultados/fase3/`; .tex seccion 4.4 | medio | **hecho** |
| **R1.5** | El marco de evaluacion es insuficiente. El ancho medio sobre finitos da lectura optimista; el CRPS no distingue esquemas de calibracion. Pide metricas para limites unilaterales y decir como se tratan los limites infinitos | Interval score del limite unilateral superior, que vale +inf si hay algun intervalo infinito. Cota inferior de alpha evaluada en cuatro niveles: **alpha_min = 0.005 elimina todos los infinitos**. Cuatro benchmarks probabilisticos. IC bootstrap de todas las diferencias | `flagship/revision/rev_lib.py`, `fase4_metricas_benchmarks.py`; `resultados/fase4/`; .tex secciones 4.5 y 5 | alto | **hecho** |

### Revisor 2, comentarios numerados

| # | Tema | Accion tomada | Ubicacion del cambio | Esfuerzo | Estado |
|---|---|---|---|---|---|
| **R2.1** | Diez referencias es inadecuado; falta pronostico de vertimiento, operacion de BESS, congestion, capacidad de red, ampacidad, restricciones termicas y modelado hibrido fisico-datos. Pide literatura independiente | Bibliografia ampliada, cada referencia discutida por su aporte especifico, **sin citas agrupadas** (restriccion textual del editor). Solo DOI verificados | .tex seccion 2 reescrita; `resultados/fase8/referencias_verificadas.md` | alto | **hecho** |
| **R2.2** | El cambio de regimen atribuido a BESS no esta demostrado; o se aporta la evidencia o se cambia la redaccion | **No se construye un estudio causal.** El manuscrito ya no hace la atribucion: lo que quedaba era residuo de nomenclatura. Se renombra `test_ramp` a `test_transition` en codigo, resultados, tablas y figuras; se elimina la nota al pie de storage deployment; se audita cada mencion a almacenamiento | `flagship/conformal_metodos.py`, `flagship/revision/rev_lib.py`, todos los CSV, .tex Tabla 3 y figuras 3 y 4 | medio | **hecho** |
| **R2.3** | La cronologia es inconsistente: el texto habla de 2025 y la evaluacion define oct-dic 2024. Pide una cronologia unica y sensibilidad a fechas alternativas de punto de cambio | Cronologia unica regenerada con script versionado. Sensibilidad sobre **180 configuraciones** de deteccion: ninguna detecta un punto de cambio en 2025 ni en octubre de 2024. Seis fronteras alternativas de la ventana de transicion evaluadas | `flagship/revision/fase6_cronologia.py`; `resultados/fase6/`; .tex secciones 3.3 y 4.4 | alto | **hecho** |
| **R2.4** | Novedad metodologica y reproducibilidad poco claras. Pide decir que es nuevo en la combinacion PIT + transporte + shrinkage + ACI, y algoritmo completo, parametros, largo de ventana, bootstrap, semilla y ablacion | Declaracion explicita de que proviene de la literatura y que es nuevo, junto con el algoritmo y la tabla de hiperparametros de R1.2 y las ablaciones de R1.3 | .tex seccion 4.6 nueva y apendice | medio | **hecho** |
| **R2.5** | Los errores estandar clusterizados no restauran intercambiabilidad. Pide conformal por bloques, grupos y central, con cobertura por tecnologia, tamano, region y eventos de alto vertimiento | **Se le da la razon.** ICC por fecha = 0.238, efecto de diseno 26.67, n efectivo 996 y no 26.552. Cuatro remedios probados y cobertura desagregada en cuatro ejes. Mondrian por region **empeora** la cobertura condicional | `flagship/revision/fase5_dependencia_panel.py`; `resultados/fase5/`; .tex secciones 4.3 y 5 | alto | **hecho** |
| **R2.6** | Ampliar benchmarking: cuantiles empiricos, CQR, distribuciones historicas moviles y parametricos inflados en cero. Reportar interval score, CRPS, Brier, cobertura condicional, frecuencia de infinitos e incertidumbre de las diferencias | Los cuatro benchmarks implementados y las seis metricas reportadas. El CQR unilateral sobre el GBM llega a 89.8% de cobertura con 276 MWh contra 591 del metodo del paper | igual que R1.5, mas `fase5` para la cobertura condicional | alto | **hecho** |
| **R2.7** | Moderar las afirmaciones: la conclusion sobre el pronostico puntual vale solo para los modelos, features, horizonte y metrica evaluados. Abstract y conclusion deben distinguir validez en muestra finita, control adaptativo de largo plazo y cobertura empirica en panel dependiente | Afirmacion acotada explicitamente. Los tres regimenes de garantia separados en abstract, seccion 4 y conclusion. Seccion de limitaciones ampliada | .tex abstract, seccion 4.3, seccion 6 y conclusion | medio | **hecho** |

### Preguntas estructuradas y nota editorial

| # | Origen | Tema | Accion tomada | Estado |
|---|---|---|---|---|
| **Q3** | R1 marca **No** en "¿son apropiados y estan bien descritos los analisis estadisticos?" | Reporte estadistico insuficiente | Cubierto por R1.4 (seleccion), R1.5 (metricas propias e IC de las diferencias) y R2.5 (dependencia de panel cuantificada). Todo IC de diferencia entre metodos ahora es bootstrap por bloques de dia | **hecho** |
| **Q5** | R1 marca **No** en "¿la interpretacion y las conclusiones estan sostenidas por los datos?"; R2 pide expansion | La conclusion excedia lo que los datos sostienen | Es el mismo problema que detecta H1. La contribucion se reencuadra como diagnostico y la afirmacion de la reduccion de un tercio se acota al modelo base evaluado | **hecho** |
| **Q4** | Ambos: "¿se beneficiaria de tablas o figuras adicionales?" | Faltan figuras | Tres figuras nuevas: diagrama de flujo del algoritmo (fig. 6), comparacion entre modelos base (fig. 7) y aporte marginal por componente (fig. 8) | **hecho** |
| **Q7** | Ambos marcan **No** en "¿se declaran las limitaciones?" | Limitaciones insuficientes | Seccion 7 nueva y dedicada, con diez limitaciones declaradas | **hecho** |
| **Q8/Q9** | Ambos: estructura, flujo y edicion de lenguaje | Reestructuracion y edicion | Secciones reordenadas, subsecciones anadidas y edicion de lenguaje en todo el manuscrito | **hecho** |
| **ED** | Nota editorial | Titulo muy largo; cuestiona la mencion a Chile | Tres titulos alternativos sin el pais; la descripcion del sistema se mueve al abstract | **hecho** |

---

## Inventario: que script genera cada tabla y figura

| Objeto del manuscrito | Archivo de resultados | Script |
|---|---|---|
| Tabla 1, descomposicion estacional | `resultados/fase6/fase6_descomposicion_estacional.csv` | `fase6_cronologia.py` |
| Tabla 2, MAE de los modelos base | `flagship/predicciones/README.md` | `entrenar_baselines.py` |
| Tabla 3, cobertura y ancho (hurdle) | `flagship/conformal_v3_tabla.csv` | `conformal_v3_real.py` |
| Tabla 4, comparacion entre modelos base | `resultados/fase0/fase0_tabla_por_modelo.csv` | `fase0_model_agnostic.py` |
| Tabla 5, diagnostico de la Fase 0 | `resultados/fase0/fase0_diagnostico.csv` | `fase0_diagnostico.py` |
| Tabla 6, ablaciones | `resultados/fase2/fase2_aporte_por_componente.csv` | `fase2_ablaciones.py` |
| Tabla 7, benchmarks y metricas | `resultados/fase4/fase4_metricas_completas.csv` | `fase4_metricas_benchmarks.py` |
| Tabla 8, cota de alpha | `resultados/fase4/fase4_cota_alpha.csv` | `fase4_metricas_benchmarks.py` |
| Tabla 9, dependencia de panel y cobertura desagregada | `resultados/fase5/fase5_remedios.csv`, `fase5_diagnostico_dependencia.csv`, `fase5_cobertura_desagregada.csv` | `fase5_dependencia_panel.py` |
| Tabla 10, sensibilidad de la frontera | `resultados/fase6/fase6_sensibilidad_frontera.csv` | `fase6_cronologia.py` |
| Tabla C.11, hiperparametros (apendice C) | `resultados/fase1/hiperparametros.csv` | `fase1_hiperparametros.py` |
| Fig. 1 mapa, Fig. 2 distribucion | `release/v1.0/` | `generar_figuras_paper.py` |
| Fig. 3 puntos de cambio | `resultados/fase6/fase6_serie_mensual_*.csv` | `generar_figuras_paper.py` |
| Fig. 4 diagrama de flujo | (esquematica) | `fase9_figuras_revision.py` |
| Fig. 5 cobertura rodante, Fig. 6 cobertura y ancho | `flagship/conformal_v3_tabla.csv` | `generar_figuras_paper.py` |
| Fig. 7 comparacion de modelos base | `resultados/fase0/fase0_diagnostico.csv` | `fase9_figuras_revision.py` |
| Fig. 8 aporte por componente | `resultados/fase2/fase2_aporte_por_componente.csv` | `fase9_figuras_revision.py` |

---

## Orden de ejecucion completo

```
<venv>/bin/python flagship/revision/fase0_entrenar_qgbm.py            # ~8 min
<venv>/bin/python flagship/revision/fase0_model_agnostic.py           # ~1 min
<venv>/bin/python flagship/revision/fase0_diagnostico.py              # <1 s
<venv>/bin/python flagship/revision/fase2_ablaciones.py               # ~30 s
<venv>/bin/python flagship/revision/fase3_seleccion_hiperparametros.py # ~4 min
<venv>/bin/python flagship/revision/fase4_metricas_benchmarks.py      # ~2 min
<venv>/bin/python flagship/revision/fase5_dependencia_panel.py        # ~12 s
<venv>/bin/python flagship/revision/fase6_cronologia.py               # ~2 min
<venv>/bin/python flagship/revision/fase1_hiperparametros.py          # <1 s
<venv>/bin/python flagship/revision/fase9_figuras_revision.py         # ~10 s
```
