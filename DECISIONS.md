# Bitácora de decisiones metodológicas

Formato: fecha · decisión · alternativas consideradas · justificación · responsable.

---

## 2026-07-03 · Arquitectura de publicación en dos papers
**Decisión:** secuencia data paper (Data in Brief) → flagship (SEGAN: hurdle + conformal + Wasserstein/OT para drift BESS).
**Alternativas:** un solo paper aplicado; paper "causal" de transmisión vs generación.
**Justificación:** el data paper desriesga y funda el DOI citable; el ángulo causal puro contradice la atribución oficial del CEN y carece de estrategia de identificación; la fusión método+drift convierte el quiebre BESS 2025 de amenaza en contribución.
**Responsable:** Pablo + Kerven (pendiente ratificación en sesión de definición).

## 2026-07-03 · Herramientas
**Decisión:** flagship en Overleaf (elsarticle) · data paper en template Word oficial DiB (obligatorio) · datos en Zenodo con DOI reservado · referencias en Zotero grupal · repo GitHub privado.

## 2026-07-04 · Corte v1.0 y backfill horario completo
**Decisión:** dataset v1.0 con corte 2026-05-31 en AMBAS tablas (curtailment_diario y curtailment_horario); serie horaria completa con los 53 reportes mensuales del CEN (enero-2022 a mayo-2026).
**Alternativas:** congelar solo años cerrados 2022-2025; mantener horario parcial (solo diciembres).
**Justificación:** los 53 reportes mensuales existen y fueron verificados en el portal del CEN; el corte idéntico en ambas tablas evita cortes incoherentes (antes: diario a feb-2026, horario a abr-2026). Junio-2026 aún no publicado al momento del corte.
**Responsable:** Pablo.

## 2026-07-04 · Política de versiones de archivos CEN: "última publicada gana"
**Decisión:** cuando el CEN publicó más de una versión de un reporte mensual se usa la última (sufijos v2/_2/Final): Diciembre-2023_v2, Enero-24_v2, Marzo-24_publicar_2, Junio-24_publicar_v2, Agosto/Septiembre/Octubre-24_publicar_v2, Abril-25_Final.
**Alternativas:** primera versión publicada; comparar y elegir por mes.
**Justificación:** la versión más reciente incorpora las correcciones del propio CEN; regla simple y determinística.
**Responsable:** Pablo.

## 2026-07-04 · data-raw/ como fuente canónica del ETL
**Decisión:** los loaders leen exclusivamente de curtailmentiq-research/data-raw/ (53 archivos, inmutables, SHA-256 + fecha de descarga en CHECKSUMS.sha256).
**Justificación:** trazabilidad y reproducibilidad para el data paper; las copias dispersas (DATOS/, datos 2022-2026/) quedan como respaldo histórico.
**Responsable:** Pablo.

## 2026-07-04 · Días faltantes: recuperación determinística en el ETL (no ediciones manuales)
**Decisión:** los días ausentes del desglose diario por erratas de plantilla del CEN (2022-05-31 todas las tecnologías; 2025-05-31 solo Solar) se recuperan agregando la hoja horaria del reporte mensual del propio mes (PARCHES_DIARIO en parsers.py), con contraste contra la columna "Total" por central del bloque errado. Detalle en ERRATA_LOG.md.
**Alternativas:** dejar los días ausentes y documentarlos; imputar.
**Justificación:** el dato existe en otra hoja oficial del mismo origen (no es imputación); dos vías independientes coinciden al milésimo de MWh; la recuperación es código reproducible, no edición manual.
**Responsable:** Pablo.

## 2026-07-18 · Ética y licencia del depósito: respuesta SAIP del CEN
**Decisión:** con la respuesta SAIP del CEN recibida el 13-jul-2026 (uso académico permitido citando la fuente, sin licencia particular sobre los datos), el depósito en Zenodo se publica bajo licencia CC BY 4.0.
**Alternativas:** CC0; CC BY-NC 4.0; esperar un pronunciamiento formal adicional del CEN.
**Justificación:** el CEN no impone licencia y solo exige cita de la fuente; CC BY 4.0 es la licencia estándar recomendada para datasets académicos, maximiza reutilización y hace obligatoria la atribución, coherente con la condición del CEN. Cierra el punto de ética del data paper.
**Responsable:** Pablo.

## 2026-07-18 · Reformulación del problema del flagship: de cobertura a sharpness
**Decisión:** a la luz del prototipo conformal sobre datos sintéticos (flagship/conformal_prototype.py), el problema central del flagship se reformula: no es pérdida de cobertura bajo el quiebre BESS, sino pérdida de sharpness.
**Evidencia (sintética, no citable):** el conformal split estándar mantiene cobertura post-quiebre (97-99% vs 90% nominal) con intervalos sobreanchos; el weighted conformal no corrige por falta de solapamiento entre regímenes (ESS 1.203 de 9.760 en calibración).
**Justificación:** el quiebre BESS reduce las magnitudes, así que el intervalo calibrado pre-quiebre sobrecubre en vez de subcubrir; la contribución metodológica pasa a ser recuperar intervalos ajustados (sharp) con garantía bajo cambio de régimen, línea que conecta con la pieza OT/drift de Kerven.
**Responsable:** Pablo.

## 2026-07-19 · Diseño metodológico del flagship definido por el audit de Kerven
**Decisión:** el diseño de trabajo del flagship queda definido por el audit metodológico de Kerven (flagship/AUDIT_METODOLOGICO.md): score distribucional/PIT como geometría del score de no-conformidad, ventana deslizante de 60 días como mecanismo de recalibración, y ACI sobre scores transportados (mapa monótono OT) como contribución teórica; el weighted conformal en su versión por-punto correcta (intervalos infinitos en ~46% de los casos) queda como negative result que motiva el paper.
**Alternativas:** mantener el weighted conformal pooled del prototipo (descartado: es un artefacto que oculta el fallo del método); calibración estática recalibrada una vez (descartada: el quiebre BESS es una rampa de 15 meses y ninguna calibración estática la rastrea).
**Justificación:** el audit verificó empíricamente sobre el panel sintético (mismo seed) que la ventana deslizante con score multiplicativo/PIT restaura cobertura y sharpness (91.5% de cobertura, ancho 212), mientras toda alternativa estática deriva con la rampa. Ratificación formal y calendario en la sesión del martes.
**Adicional:** por la dependencia transversal detectada en el audit (las 40 centrales comparten el estado sistémico diario, ~244 bloques efectivos en calibración), los errores estándar de toda cobertura reportada se clusterizan por fecha.
**Responsable:** Kerven (diseño) + Pablo (implementación del prototipo v2); pendiente ratificación martes.

## 2026-07-20 · Cierre del experimento central del flagship (datos reales) e inicio de redacción
**Decisión:** el experimento central del flagship sobre datos reales (predicciones/pred_hurdle.csv del dataset v1.0, corridas en flagship/conformal_v3_real.py, consolidado en flagship/RESULTADOS_REALES.md) queda cerrado; el paper entra en fase de redacción. Los hallazgos: el pronóstico de punto está agotado (gana el naive estacional, MAE total 85.10 MWh); la sobrecobertura severa del sintético no aparece en real porque el modelo base absorbe el quiebre BESS (estático entre 89% y 95% en todos los periodos); la adaptatividad paga sobre todo en la rampa (transporte + ACI baja el ancho de 1203 a 732 MWh con 90.7% de cobertura) y es ambigua fuera de ella; con sigma = 1.70 buena parte de la falta de sharpness es del modelo base, no del conformal; y las diferencias de 1 a 3 puntos entre métodos están dentro del error estándar clusterizado por fecha.
**Asuntos técnicos abiertos (a decidir con el co-autor):**
1. Embargo de horizonte. Los métodos online y de ventana usan calibración hasta la fecha t sin el embargo de 7 días que implica un pronóstico a 7 días (la calibración para el target t solo debería usar outcomes conocidos en t menos 7); falta cuantificar el optimismo que introduce esta omisión, común a v2 y v3 por comparabilidad. Primera corrección a evaluar.
2. Modelo base heterocedástico sigma(x). El techo de sharpness lo fija sigma = 1.70; la capa conformal no puede ser más sharp que la predictiva del hurdle. Conviene medir cuánto del ancho (455 a 1203 MWh) es irreducible dado el hurdle actual y cuánto bajaría con un sigma heterocedástico o una predictiva de magnitud más rica.
3. Detección de change-point. Hay una caída de cobertura rodante común a todos los métodos alrededor de mayo a julio de 2025 (todos bajan a cerca de 85%) que ningún método anticipa; apunta a una adaptación condicional al régimen o gatillada por quiebre, en vez de ventana o ACI uniformes.
**Responsable:** Pablo (implementación) + Kerven (diseño); los tres asuntos se deciden en sesión conjunta.

## 2026-07-20 · Cierre de alcance del flagship sobre las tres cuestiones abiertas
**Decisión:** tras el análisis del co-autor sobre las tres cuestiones abiertas del 2026-07-20 (embargo de horizonte, detección de change-point, modelo base heterocedástico), se cierra el alcance del paper metodológico:
1. **Embargo de horizonte de 7 días: ENTRA.** Es un requisito de validez del backtesting, no una opción: la calibración para el target t solo puede usar outcomes conocidos en t menos 7 (el pronóstico se emite a 7 días). Se implementa en flagship/conformal_v3_real.py (constante EMBARGO_DIAS): las ventanas de calibración online terminan 7 días antes del target y la retroalimentación de alpha del ACI se retrasa 7 pasos. Su efecto empírico está dentro del error estándar clusterizado por fecha y sin sesgo direccional (delta de cobertura en el rango -1.4 a +1.2 puntos sobre los métodos online, estático idéntico), ver Parte F de conformal_v3_hallazgos.txt.
2. **Detección de change-point para la caída de mayo a julio de 2025: TRABAJO FUTURO.** Se reporta en el paper como limitación caracterizada, acompañada de un diagnóstico corto del episodio (caída de cobertura rodante común a todos los métodos alrededor de mayo a julio de 2025, que ningún método anticipa; ver Parte C.5 de los hallazgos). No entra en el alcance de esta iteración.
3. **Modelo base heterocedástico sigma(x): ENTRA condicionalmente.** Entra si el equipo del modelo base lo entrega dentro del plazo del paper; si no, queda como el trabajo futuro de mayor prioridad (el techo de sharpness lo fija sigma = 1.70, y la capa conformal no puede ser más sharp que la predictiva base). La especificación queda en flagship/ESPECIFICACION_SIGMA_X.md. La decisión de compromiso (entra ahora o pasa a futuro) queda pendiente de la sesión de coordinación.
**Responsable:** Pablo (implementación) + Kerven (diseño y análisis); el punto 3 se resuelve en la sesión de coordinación.

## 2026-07-22 · sigma(x) heterocedástico probado y descartado como modelo base [SUPERADA]
**SUPERADA por la entrada siguiente del 2026-07-22 (reetiquetación de sigma(x)).** Esta entrada se apoyaba solo en los diagnósticos del modelo base (PIT crudo, CRPS, log-score y cobertura del cuantil propio), que sugerían una ganancia marginal. La prueba end-to-end posterior (flagship/conformal_v3_hetero.py), que pasa sigma(x) por la capa conformal completa, corrigió el veredicto: la ganancia de sharpness es sustancial (17 a 36% más angosto) y el costo es de cobertura condicional en las centrales grandes, no un descarte plano. No se borra: se conserva por trazabilidad de la bitácora.
**Decisión:** el modelo base heterocedástico sigma(x) (especificado en flagship/ESPECIFICACION_SIGMA_X.md, implementado en flagship/entrenar_hurdle_hetero.py, predicciones en flagship/predicciones/pred_hurdle_hetero.csv) se prueba y se descarta como modelo base del experimento central. El hurdle con sigma constante (predicciones/pred_hurdle.csv) sigue siendo el modelo base oficial.
**Evidencia:** sobre datos reales OOS 2024 a 2026, sigma(x) mejora solo de forma marginal los scores propios de la predictiva (CRPS 79.06 vs 81.77 MWh; log-score 4.9819 vs 4.9924), no mejora la calibración global (KS del PIT 0.1724 vs 0.1667) e introduce sub-cobertura del cuantil 90% propio concentrada en las centrales grandes (tercil grande 83.0% vs 87.4% con sigma constante, contra un nominal de 90%). El diagnóstico condicional que aísla la dispersión (PIT sobre positivos, train OOF sin quiebre vs OOS con quiebre) muestra que el gap OOS es idéntico con y sin sigma(x) (KS 0.1822 vs 0.1829) y que en train la dispersión ya estaba bien calibrada (KS cercano a 0.09): el quiebre BESS actúa como shift de ubicación de la predictiva, no de dispersión, así que un modelo de varianza no cierra el gap.
**Justificación:** el techo de sharpness es consecuencia del shift de ubicación bajo el quiebre, no de la especificación de la varianza; enriquecer la varianza del modelo base no es la palanca. Se reporta como resultado negativo publicable y refuerza que la contribución del flagship está en la adaptación conformal al régimen. Cierra el punto 3 (condicional) de la decisión de alcance del 2026-07-20: sigma(x) no entra al experimento central.
**Responsable:** Pablo (implementación) + Kerven (diseño y análisis).

## 2026-07-22 · Reetiquetación de sigma(x): de resultado negativo a trade-off (sharpness contra cobertura condicional)
**Corrige:** la entrada previa del mismo día (sigma(x) descartado), que se apoyaba solo en los diagnósticos del modelo base. La prueba end-to-end (flagship/conformal_v3_hetero.py, salida en flagship/conformal_v3_hetero_salida.txt, comparación en flagship/conformal_v3_hetero_comparacion.csv) corre la capa conformal completa sobre pred_hurdle_hetero.csv contra pred_hurdle.csv con el mismo protocolo, semilla y embargo de 7 días, y cambia el veredicto.
**Evidencia (end-to-end):** al pasar por la capa conformal, la ganancia del modelo base se amplifica: intervalos 17 a 36% más angostos en todos los periodos, con cobertura marginal agregada que mejora de 92.5% a 90.9% (más cerca del 90 nominal); en la rampa BESS, de 95.3% con 1203 MWh a 91.7% con 769 MWh (36% más angosto). El costo es condicional: por tercil de tamaño, chicas 93.1% a 91.9% (248 a 188 MWh), medias 93.3% a 92.8% (678 a 470 MWh), grandes 91.1% a 87.8% (1120 a 881 MWh), con un spread condicional de 4.1 puntos. Segundo costo: el CRPS mejora en 4 de 5 periodos pero retrocede en la rampa (133.5 a 146.5) y el ACI agresivo (gamma 0.05) produce hasta cerca del 10% de intervalos infinitos con sigma(x). Los diagnósticos del modelo base de la entrada previa siguen siendo válidos y explican el porqué: el quiebre actúa como desplazamiento de ubicación, no de dispersión (PIT crudo KS 0.1667 constante contra 0.1724; condicional train OOF 0.0966 contra 0.0944, OOS 0.1829 contra 0.1822).
**Reetiquetación:** de "resultado negativo, sigma(x) descartado" a "mejora de sharpness con costo de cobertura condicional". Se reporta como subsección propia de resultados, no como negative result; el negative result del paper que se conserva es el del weighted conformal por punto.
**Decisión (autor principal, a informar al co-autor):** se mantiene sigma constante (predicciones/pred_hurdle.csv) como modelo base del experimento central, no por razones estadísticas sino operacionales: los usuarios del pronóstico evalúan cada central por separado, y un método más angosto en promedio pero menos confiable en las centrales grandes no cumple el requisito de confiabilidad por central.
**Responsable:** Pablo (decisión), Kerven (prueba end-to-end).

## PENDIENTES (completar en sesión Pablo-Kerven)
- [ ] Target exacto de predicción (MWh/central/día · prob. de evento · ambos).
- [ ] Definición de splits temporales train/calibración/test (fechas exactas) considerando tren alcista y quiebre BESS.
- [ ] Pieza de Kerven: OT/drift, conformal, o ambas. ¿Toma la línea teórica (cobertura bajo no-intercambiabilidad)?
- [ ] Baselines comprometidos: persistencia, naive estacional, XGBoost punto, GBM cuantílico. ¿LSTM sí/no?
- [x] Fecha de corte del dataset v1.0. → **2026-05-31** (decisión 2026-07-04, arriba).
