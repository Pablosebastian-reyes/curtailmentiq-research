# Resultados sobre datos reales (experimento conformal v3)

Consolidación en prosa de los hallazgos del experimento central del flagship sobre datos reales, lista para redactar el paper. Fuentes: `conformal_v3_hallazgos.txt`, `conformal_v3_tabla.csv`, `conformal_v3_salida.txt`, la figura `conformal_v3_cobertura_rodante.png` y la tabla de MAE de `predicciones/README.md`. Diseño metodológico de Kerven Cea; implementación en `conformal_v3_real.py` sobre `predicciones/pred_hurdle.csv` (modelo base hurdle sobre el dataset congelado v1.0, entrenado solo hasta 2023-12-31). El código de métodos es común al cierre sintético (`conformal_metodos.py`), de modo que lo único que cambia entre sintético y real son los datos.

El tono de este documento es deliberadamente sobrio: las diferencias reportadas son pequeñas y se interpretan a la luz de su error estándar.

> **Nota de vigencia (2026-07-28):** los valores válidos son los de `conformal_v3_tabla.csv`, generados con EMBARGO_DIAS=7 en `conformal_v3_real.py`. El embargo de 7 días es requisito de validez del backtest a 7 días, según la decisión de alcance del 2026-07-20 (ver `DECISIONS.md`).

## 1. El pronóstico de punto está agotado

Sobre el conjunto común de evaluación, el mejor pronóstico puntual es el baseline más simple. El MAE total (MWh) por modelo es:

| modelo | 2024 | 2025 | 2026 | total |
|---|---|---|---|---|
| naive estacional | 84.25 | 86.25 | 84.18 | 85.10 |
| gbm cuantílico (q50) | 88.52 | 89.89 | 84.30 | 88.33 |
| persistencia | 88.44 | 96.32 | 90.68 | 92.23 |
| xgboost punto | 92.68 | 94.65 | 89.69 | 92.97 |
| hurdle (mediana de la mezcla) | 104.43 | 104.82 | 101.60 | 104.08 |

El naive estacional (promedio del mismo día de semana en las cuatro semanas previas) gana en los tres años, y ningún modelo entrenado lo mejora de forma apreciable. La lectura es que la señal de punto de esta serie está prácticamente extraída por un baseline estacional trivial, y que la ganancia marginal de un mejor predictor puntual es escasa. Esto ubica la contribución del flagship en la capa de incertidumbre (la calidad y la adaptatividad de los intervalos), no en el error de punto.

## 2. La sobrecobertura severa del sintético no aparece en real

En el panel sintético, el conformal estático trepaba de forma monótona hasta 99.8% de cobertura en 2026-S1, señal de intervalos cada vez más sobreanchos a medida que la rampa BESS reducía las magnitudes. En datos reales esa deriva no ocurre: el estático se mantiene entre 89% y 95% de cobertura en todos los periodos (test_pre 93.5, test_ramp 95.3, 2025-S1 89.4, 2025-S2 94.0, 2026-S1 92.5). El modelo base real absorbe el quiebre BESS mucho mejor que el proceso generador sintético, con toda probabilidad porque sus features de rezago y media móvil trasladan buena parte del cambio de régimen a la propia predictiva del hurdle. La consecuencia es que, fuera de la rampa, la tensión entre cobertura y sharpness que motivó los métodos adaptativos es bastante más leve en real que en el sintético.

## 3. La adaptatividad paga sobre todo en la rampa BESS

Donde la adaptatividad rinde con claridad es en la transición (test_ramp, octubre a diciembre de 2024). Ahí el estático da 95.3% de cobertura con un ancho medio de 1203 MWh; la ventana deslizante de 60 días baja a 92.0% con 834 MWh; y el transporte de scores más ACI (gamma 0.05) baja a 90.9% con 806 MWh. Es decir, el transporte más ACI entrega intervalos 33% más angostos que el estático a cambio de ceder 4.4 puntos de sobrecobertura, acercándose al nominal. En este periodo la adaptatividad recupera sharpness sin sacrificar cobertura por debajo de lo aceptable.

Fuera de la rampa el balance es ambiguo. En 2025-S1, con el estático ya cerca del nominal (89.4% con 455 MWh), los métodos adaptativos sobre todo canjean cobertura por ancho y pueden subcubrir: la ventana baja a 85.4% con 323 MWh, y el transporte (gamma 0.05) queda en 87.4% con 446 MWh, apenas más angosto que el estático. En 2026-S1 el canje vuelve a ser favorable y leve (ventana y ACI cerca de 90% con 419 a 446 MWh, frente a 92.5% y 535 MWh del estático). El resumen honesto es que la adaptatividad es útil en la rampa y ambigua después.

Nota sobre la banda de bootstrap del transporte: no se activa en real (desviación estándar del mapa en la cola de 0.003 en unidades PIT, regularización de cola prácticamente en transporte pleno), el mismo diagnóstico del cierre sintético. El ancho de la transición no es ruido de muestreo que una banda pueda encoger, es el costo legítimo de restaurar cobertura mezclando regímenes en la ventana reciente.

## 4. Con sigma = 1.70, buena parte de la falta de sharpness es del modelo base

La dispersión de la log-magnitud del hurdle real, estimada out-of-fold, es sigma = 1.70, frente a 0.839 en el sintético (el doble). Por sí sola, esa diferencia ensancha el percentil 90 de la magnitud en un factor cercano a 3, y explica que los anchos reales vayan de 455 a 1203 MWh cuando en el sintético iban de 120 a 525. El problema de sharpness es, por tanto, primero un problema del modelo base (su dispersión) y solo después un problema de adaptación de régimen: la capa conformal calibra la dispersión, no la reduce, y no puede producir intervalos más angostos que la predictiva del hurdle. La palanca de mayor impacto para el ancho no está en el conformal sino en el modelo de magnitud (un sigma heterocedástico sigma(x) o una predictiva más rica). Esa vía se probó end-to-end: da una mejora de sharpness real con un costo de cobertura condicional, y se mantiene sigma constante como modelo base por confiabilidad por central; el estudio está en la sección 6.

## 5. Las diferencias de 1 a 3 puntos están dentro del error estándar

Todos los errores estándar de cobertura de la tabla real están clusterizados por fecha (columna `se_cluster` de `conformal_v3_tabla.csv`), en reconocimiento de la dependencia transversal entre centrales el mismo día. En los periodos post rampa esos errores rondan 1.0 a 1.1 puntos porcentuales. En consecuencia, las diferencias de cobertura de 1 a 3 puntos entre métodos están cerca del ruido y no deben sobreinterpretarse: las comparaciones sólidas son las de orden de magnitud del ancho en la rampa (806 frente a 1203 MWh) y la dirección del canje cobertura por ancho, no el ranking fino entre variantes de gamma.

## 6. El sigma(x) heterocedástico: mejora de sharpness con costo de cobertura condicional

Siguiendo la especificación de `ESPECIFICACION_SIGMA_X.md`, se entrenó un modelo base heterocedástico que sustituye el sigma constante de la magnitud por un sigma(x) predicho por una segunda etapa (XGBoost sobre residuos out-of-fold en el espacio log), con la misma media, la misma disciplina de split y la misma capa conformal. Los drivers de la varianza tienen importancia repartida y ninguno domina (p_occ 23.1%, volatilidad móvil 20.8%, tecnología 20.6%, día del año 18.7%, log de potencia 16.8%), y el sigma(x) resultante es genuinamente heterocedástico (mediana 1.63, percentil 10 en 0.96, percentil 90 en 2.45, contra el 1.70 constante). El veredicto no es un descarte plano: mirado solo con las métricas del modelo base la ganancia parece marginal, pero al pasar por la capa conformal se amplifica en un resultado mixto, sharpness sustancialmente mejor a cambio de un costo de cobertura condicional.

Primero, los diagnósticos del propio modelo base (antes de conformal), que explican el porqué:

1. Calibración global de la predictiva (PIT crudo, distancia KS a la uniforme, OOS 2024 a 2026): sigma constante KS = 0.1667, sigma(x) KS = 0.1724. El sigma(x) no mejora la calibración global; la empeora de forma marginal.
2. Scores propios de la predictiva base (OOS 2024 a 2026): sigma(x) mejora levemente, CRPS 79.06 frente a 81.77 MWh y log-score 4.9819 frente a 4.9924. La mejora existe pero es de segundo orden.
3. Cobertura del cuantil 90% propio por tercil de tamaño de central (nominal 90%): con sigma constante los tres terciles quedan cerca del nominal (chica 89.2%, media 89.7%, grande 87.4%); con sigma(x) los tres bajan y el tercil grande cae a 83.0% (chica 87.3%, media 87.5%). La dispersión condicional pre quiebre no transfiere bien a las centrales grandes.

El diagnóstico condicional que aísla la dispersión (PIT condicional sobre los positivos, Phi de (log y menos mu) sobre sigma), comparando el train out-of-fold (sin quiebre) contra el OOS (con quiebre BESS), fija el porqué:

- train OOF, sin quiebre: KS = 0.0966 con sigma constante, 0.0944 con sigma(x).
- OOS 2024 a 2026, con quiebre: KS = 0.1829 con sigma constante, 0.1822 con sigma(x).

En el train la dispersión ya está bien calibrada (KS cercano a 0.09) y sigma(x) no aporta nada material. En el OOS ambos se deterioran por igual (KS cercano a 0.18) y sigma(x) es indistinguible del constante (0.1822 frente a 0.1829). El desajuste que aparece bajo el quiebre no es un problema de dispersión mal especificada, que sigma(x) podría corregir, sino un desplazamiento de la ubicación de la predictiva: el quiebre BESS actúa como un shift de la media condicional (en el espacio log, una traslación), no como un shift de la varianza. Modelar sigma(x), ajustado antes de la rampa, no cierra ese gap.

Segundo, la prueba end-to-end, que es la que corrige el veredicto. Corriendo el pipeline completo (estático, ventana deslizante, ACI, transporte más ACI) con protocolo, semilla y embargo de 7 días idénticos, y cambiando solo la dispersión de entrada, la capa conformal propaga sigma(x) en una ganancia de sharpness que las métricas del modelo base subestiman: los intervalos del estático quedan 17 a 36% más angostos en los cinco periodos, con la cobertura marginal preservada. Agregando sobre el periodo de test, la cobertura del estático pasa de 92.5% con sigma constante a 90.9% con sigma(x), más cerca del 90 nominal y con intervalos más angostos. En la rampa BESS la mejora es más nítida: de 95.3% (sobrecobertura) con 1203 MWh a 91.7% (todavía sobre el nominal) con 769 MWh, un 36% más angosto.

El costo es condicional, no marginal. La cobertura del estático por tercil de tamaño de central, sobre todo el periodo de test, es:

| tercil | n | cobertura const | cobertura sigma(x) | ancho const | ancho sigma(x) |
|---|---|---|---|---|---|
| chica  | 25,986 | 93.1% | 91.9% | 248.0 | 188.5 |
| media  | 26,549 | 93.3% | 92.8% | 678.0 | 470.2 |
| grande | 25,333 | 91.1% | 87.8% | 1120.3 | 881.5 |

Las centrales chicas y medias conservan su cobertura y quedan 24% y 31% más angostas; las grandes quedan 21% más angostas pero caen a 87.8%, unos dos puntos bajo el nominal, con un spread de cobertura condicional de 4.1 puntos entre el tercil chico y el grande. Es consistente con el diagnóstico 3 del modelo base (el cuantil propio de las grandes subcubría a 83.0%): la recalibración conformal lo levanta a 87.8% pero no lo cierra, porque la dispersión condicional pre quiebre de las centrales más vertidas no transfiere a través de la rampa. Un segundo costo, localizado en el tiempo, aparece en el mismo lugar: el CRPS por periodo mejora con sigma(x) en 4 de 5 periodos pero retrocede en la rampa (133.5 a 146.5 MWh), y el ACI agresivo (gamma 0.05) produce una fracción mayor de intervalos infinitos con sigma(x) en dos periodos post rampa (hasta cerca del 10%).

Implicancia para el paper: modelar la varianza condicional sí baja el techo de sharpness end-to-end, entre un quinto y un tercio del ancho a cobertura marginal preservada, un efecto mayor que el que sugieren el log-score o el CRPS del modelo base. No resuelve el problema de fondo, que es el shift de ubicación de la rampa BESS, y transfiere peor justo donde el quiebre pega, en las centrales grandes y en la transición. Por eso se reetiqueta de resultado negativo a un estudio del trade-off entre sharpness marginal y cobertura condicional, y se reporta como subsección propia de resultados, no como negative result (ese rol lo mantiene el weighted conformal por punto, sección 5.3). La decisión es mantener el hurdle con sigma constante (`predicciones/pred_hurdle.csv`) como modelo base oficial del experimento central, no por razones estadísticas sino operacionales: los usuarios del pronóstico evalúan cada central por separado, y un método más angosto en promedio pero menos confiable en las centrales grandes no cumple el requisito de confiabilidad por central. El heterocedástico queda documentado en `predicciones/pred_hurdle_hetero.csv`, con la comparación end-to-end en `conformal_v3_hetero_comparacion.csv`, como el comparador de este trade-off.

## Observación estructural para la discusión

La figura de cobertura rodante a 90 días muestra una caída común a todos los métodos alrededor de mayo a julio de 2025 (todos bajan a cerca de 85%), que ningún método anticipa. Sugiere un evento o cambio de régimen real de segundo orden en esa ventana, distinto de la rampa BESS principal, y es uno de los asuntos técnicos abiertos registrados en `DECISIONS.md`.
