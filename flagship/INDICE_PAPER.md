# Índice del paper metodológico (flagship)

Estructura de secciones propuesta para el manuscrito, en formato IMRyD extendido. Sirve de esqueleto para la redacción y de mapa entre cada sección y los artefactos ya producidos en flagship/. El alcance está cerrado (ver DECISIONS.md 2026-07-20 y la reetiquetación de sigma(x) del 2026-07-22): el resultado positivo es la adaptación por ventana deslizante y transporte de scores más ACI bajo el cambio de regimen; el resultado negativo es el weighted conformal por punto; el modelo base heterocedástico sigma(x) se reporta como un estudio del trade-off entre sharpness marginal y cobertura condicional (se mantiene sigma constante como modelo base por confiabilidad por central).

Objetivo de venue: revista o conferencia de métodos aplicados a energía o de predicción con cuantificación de incertidumbre (línea SEGAN según DECISIONS.md 2026-07-03).

## 1. Introduction

- Problema aplicado: predicción de vertimiento (curtailment) por central en el sistema eléctrico chileno, con cuantificación de incertidumbre útil para operación.
- El giro metodológico: el pronóstico de punto está agotado (un baseline estacional trivial gana en MAE), así que el valor está en la capa de incertidumbre, no en el error de punto.
- El desafío central: el cambio de regimen (rampa de 15 meses, no un escalón) rompe la intercambiabilidad y obsoleta toda calibración estática.
- Contribuciones, enumeradas: (i) diagnóstico del quiebre como rampa y no como covariate shift; (ii) resultado negativo del weighted conformal por punto; (iii) resultado positivo de adaptación por recencia y transporte de scores más ACI; (iv) la línea teórica de transporte del score entre regímenes.

## 2. Related work

- Conformal prediction: split conformal y CQR (Romano, Patterson y Candès 2019).
- Score distribucional o PIT (Chernozhukov, Wüthrich y Zhu 2021).
- Cambio de distribución: weighted conformal bajo covariate shift (Tibshirani et al. 2019); conformal más allá de la intercambiabilidad y pesos de recencia (Barber, Candès, Ramdas y Tibshirani 2023).
- Conformal adaptativo online: ACI (Gibbs y Candès 2021), DtACI (2022), conformal PID (Angelopoulos, Candès y Tibshirani 2023).
- Descomposición de shifts: Ai y Ren (2024); alternativa DRO (Cauchois, Gupta, Ali y Duchi 2024); variante series de tiempo (Xu y Xie, EnbPI).
- Transporte óptimo y conformal: la línea de center-outward ranks para scores multivariados (deslinde: usan OT para construir el score, aquí se usa para adaptarlo entre regímenes).

## 3. Data

- Fuente: dataset v1.0 de vertimiento por central del Sistema Eléctrico Nacional de Chile (2022 a 2026), corregido por erratas. Referencia al data paper y al depósito Zenodo (evita duplicar la descripción del dataset).
- Panel sintético: proceso generador calibrado al EDA del release v1.0 (proporción de ceros, cola lognormal, persistencia AR(1) 0.85, ciclo semanal, ventana de transicion), usado como banco de pruebas controlado y no citable como evidencia empírica.
- Predicciones reales: salida del modelo base hurdle entrenado solo hasta 2023-12-31, con sigma out-of-fold = 1.70 (flagship/predicciones/).
- Cortes temporales: calibración, test_pre, test_transition y los semestres 2025-S1, 2025-S2, 2026-S1.

## 4. Methods

### 4.1 Modelo base hurdle
Ocurrencia (clasificador de P(Y mayor que 0)) más magnitud lognormal; predictiva de mezcla y su cuantil superior.

### 4.2 Score de no-conformidad PIT
Score distribucional en [0,1] con randomización en el átomo de cero; por qué es homogéneo entre centrales chicas y grandes y por qué corrige la descalibración en unidades de probabilidad.

### 4.3 Conformal split y corrección de muestra finita
Estadístico de orden, garantía bajo intercambiabilidad, manejo conservador de la cola.

### 4.4 Dependencia y errores estándar clusterizados
Violación de la intercambiabilidad por dependencia serial (AR(1), y_lag1) y transversal (estado sistémico compartido por central el mismo día); todos los errores estándar de cobertura se clusterizan por fecha.

### 4.5 Adaptación por recencia: ventana deslizante y pesos
Ventana deslizante de 60 días con refresco; pesos de recencia (Barber et al. 2023) como formalización del colapso del pool fijo.

### 4.6 Conformal adaptativo online (ACI)
ACI sobre el score PIT; el rol de gamma.

### 4.7 Transporte de scores entre regímenes
Mapa monótono 1D T = F_new inversa compuesta con F_old (increasing rearrangement) sobre los scores de calibración; transporte más ACI; validez vía cota en distancia TV o vía control online; banda de bootstrap del mapa.

### 4.8 Weighted conformal por punto (comparador)
Formulación correcta por punto de test (Tibshirani et al. 2019), como comparador que sostiene el resultado negativo.

### 4.9 Embargo de horizonte
Embargo de 7 días en las ventanas de calibración online y en la retroalimentación de alpha del ACI, como requisito de validez del backtesting (DECISIONS.md 2026-07-20).

### 4.10 Métricas
Cobertura empírica con error estándar clusterizado por fecha, ancho medio (sharpness), CRPS y log-score, diagnóstico PIT con distancia KS a la uniforme.

## 5. Results

### 5.1 Benchmark sintético
Cierre de la tabla comparativa sobre el panel sintético (no citable como evidencia empírica): el pool deslizante resuelve el colapso del pool fijo; la ventana y el ACI recuperan sharpness bajo la rampa; la banda del transporte es inerte porque el ancho de la transición no es ruido de muestreo.

### 5.2 Datos reales
La maquinaria PIT funciona de extremo a extremo (intervalos finitos en casi el 100% de los casos); la sobrecobertura severa del sintético no aparece porque el modelo base absorbe el quiebre; la adaptatividad paga sobre todo en la rampa (transporte más ACI baja el ancho de 1203 a 732 MWh con 90.7% de cobertura) y es ambigua fuera de ella; el techo de sharpness lo fija sigma = 1.70; las diferencias de 1 a 3 puntos entre métodos están dentro del error estándar clusterizado. Sensibilidad al embargo de horizonte (dentro del error estándar, sin sesgo direccional).

### 5.3 Resultado negativo: weighted conformal por punto
El weighted conformal por punto con score PIT entrega intervalos infinitos en una fracción alta de los casos (ESS de calibración colapsado); el fallo es por falta de solapamiento en las X (no por el score) y es robusto entre score aditivo y PIT. Es el resultado negativo que motiva la adaptación por recencia y transporte. Es el único negative result del paper; el estudio de sigma(x) de la subsección 5.4 no lo es.

### 5.4 Modelo base heterocedástico sigma(x): trade-off entre sharpness marginal y cobertura condicional
No es un resultado negativo, sino un estudio de trade-off. Las métricas del modelo base sugieren una ganancia marginal (CRPS y log-score levemente mejores, calibración global apenas peor), pero la capa conformal la amplifica: intervalos 17 a 36% más angostos en todos los periodos a cobertura marginal preservada (agregada de 92.5% a 90.9%; rampa de 95.3% con 1203 MWh a 91.7% con 769 MWh). El costo es condicional: sub-cobertura concentrada en las centrales grandes (tercil grande 91.1% a 87.8%, spread condicional de 4.1 puntos) y un CRPS que retrocede en la rampa, más ACI agresivo con intervalos infinitos. El diagnóstico condicional explica el porqué: el quiebre es un shift de ubicación, no de dispersión, y sigma(x) transfiere peor justo donde el quiebre pega. Se mantiene sigma constante como modelo base oficial por confiabilidad por central (razón operacional, no estadística).

## 6. Discussion

- Por qué la geometría del score (PIT o multiplicativa) convierte el quiebre en una traslación de la ley de scores, y por qué eso vuelve la adaptación un problema de drift-tracking de baja dimensión y no de reweighting.
- Por qué el modelo base real absorbe el quiebre mejor que el sintético (features de rezago y media móvil) y qué implica para la generalización a shifts en la dirección adversa (subcobertura silenciosa).
- Ubicación del cuello de botella de sharpness en el modelo base (sigma) y no en la capa conformal.

## 7. Limitations and future work

- Modelo base heterocedástico sigma(x): evaluado end-to-end y reportado en resultados (subsección 5.4) como trade-off; se mantiene sigma constante por confiabilidad por central. El trabajo futuro es cerrar el gap de cobertura condicional en las centrales grandes bajo el quiebre (dispersión consciente del régimen o por central), no la especificación de la varianza en sí.
- Detección de change-point: la caída de cobertura común a todos los métodos alrededor de mayo a julio de 2025 no es anticipada por ningún método; se reporta como limitación caracterizada con un diagnóstico corto del episodio.
- Validez exacta de muestra finita del transporte: se pierde por ser el mapa dato-dependiente; se recupera vía cota TV o vía control online.
- Alcance del panel sintético: banco de pruebas, no evidencia empírica.

## 8. Conclusion

Síntesis sobria: bajo un quiebre en rampa, la calibración estática pierde sharpness; la adaptación por recencia y el transporte de scores más ACI la recuperan a cobertura sostenida en la transición; el weighted conformal por punto es el comparador negativo; y enriquecer la varianza del modelo base (sigma(x)) da una mejora de sharpness real pero con costo de cobertura condicional en las centrales grandes, así que la dificultad operativa sigue siendo el shift de régimen y la palanca correcta es la adaptación conformal, no la especificación de la varianza.

## 9. Reproducibility

- Código: conformal_metodos.py (métodos compartidos), conformal_v2.py y conformal_v2_cierre.py (sintético), conformal_v3_real.py (real), entrenar_baselines.py (modelo base y predicciones).
- Datos: dataset v1.0 en Zenodo (DOI) y flagship/predicciones/.
- Salidas de referencia: conformal_v3_salida.txt, conformal_v3_tabla.csv, conformal_v3_hallazgos.txt, figura de cobertura rodante; semillas fijas y versiones de librerías documentadas.
- Auditoría metodológica: AUDIT_METODOLOGICO.md.

## 10. Appendices

- A. Derivación del cuantil superior de la mezcla hurdle.
- B. Detalle del score PIT randomizado en el átomo de cero.
- C. Construcción del mapa de transporte y su banda de bootstrap.
- D. Tablas completas por método y periodo (sintético y real) con errores estándar clusterizados por fecha.
- E. Diagnóstico del episodio de mayo a julio de 2025.
- F. Especificación y protocolo de sigma(x) (resumen de ESPECIFICACION_SIGMA_X.md).
- G. Variante GAMLSS interpretable del modelo base heterocedástico.
