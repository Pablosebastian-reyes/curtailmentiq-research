# Resultados sobre datos reales (experimento conformal v3)

Consolidación en prosa de los hallazgos del experimento central del flagship sobre datos reales, lista para redactar el paper. Fuentes: `conformal_v3_hallazgos.txt`, `conformal_v3_tabla.csv`, `conformal_v3_salida.txt`, la figura `conformal_v3_cobertura_rodante.png` y la tabla de MAE de `predicciones/README.md`. Diseño metodológico de Kerven Cea; implementación en `conformal_v3_real.py` sobre `predicciones/pred_hurdle.csv` (modelo base hurdle sobre el dataset congelado v1.0, entrenado solo hasta 2023-12-31). El código de métodos es común al cierre sintético (`conformal_metodos.py`), de modo que lo único que cambia entre sintético y real son los datos.

El tono de este documento es deliberadamente sobrio: las diferencias reportadas son pequeñas y se interpretan a la luz de su error estándar.

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

Donde la adaptatividad rinde con claridad es en la transición (test_ramp, octubre a diciembre de 2024). Ahí el estático da 95.3% de cobertura con un ancho medio de 1203 MWh; la ventana deslizante de 60 días baja a 91.9% con 811 MWh; y el transporte de scores más ACI (gamma 0.05) baja a 90.7% con 732 MWh. Es decir, el transporte más ACI entrega intervalos 39% más angostos que el estático a cambio de ceder 4.6 puntos de sobrecobertura, acercándose al nominal. En este periodo la adaptatividad recupera sharpness sin sacrificar cobertura por debajo de lo aceptable.

Fuera de la rampa el balance es ambiguo. En 2025-S1, con el estático ya cerca del nominal (89.4% con 455 MWh), los métodos adaptativos sobre todo canjean cobertura por ancho y pueden subcubrir: la ventana baja a 85.9% con 343 MWh, y el transporte (gamma 0.05) queda en 88.8% pero con 557 MWh, más ancho que el estático. En 2026-S1 el canje vuelve a ser favorable y leve (ventana y ACI cerca de 90% con 423 a 426 MWh, frente a 92.5% y 535 MWh del estático). El resumen honesto es que la adaptatividad es útil en la rampa y ambigua después.

Nota sobre la banda de bootstrap del transporte: no se activa en real (desviación estándar del mapa en la cola de 0.003 en unidades PIT, regularización de cola prácticamente en transporte pleno), el mismo diagnóstico del cierre sintético. El ancho de la transición no es ruido de muestreo que una banda pueda encoger, es el costo legítimo de restaurar cobertura mezclando regímenes en la ventana reciente.

## 4. Con sigma = 1.70, buena parte de la falta de sharpness es del modelo base

La dispersión de la log-magnitud del hurdle real, estimada out-of-fold, es sigma = 1.70, frente a 0.839 en el sintético (el doble). Por sí sola, esa diferencia ensancha el percentil 90 de la magnitud en un factor cercano a 3, y explica que los anchos reales vayan de 455 a 1203 MWh cuando en el sintético iban de 120 a 525. El problema de sharpness es, por tanto, primero un problema del modelo base (su dispersión) y solo después un problema de adaptación de régimen: la capa conformal calibra la dispersión, no la reduce, y no puede producir intervalos más angostos que la predictiva del hurdle. La palanca de mayor impacto para el ancho no está en el conformal sino en el modelo de magnitud (un sigma heterocedástico sigma(x) o una predictiva más rica). Esa vía se probó y se descartó como modelo base del experimento central; el diagnóstico está en la sección 6.

## 5. Las diferencias de 1 a 3 puntos están dentro del error estándar

Todos los errores estándar de cobertura de la tabla real están clusterizados por fecha (columna `se_cluster` de `conformal_v3_tabla.csv`), en reconocimiento de la dependencia transversal entre centrales el mismo día. En los periodos post rampa esos errores rondan 1.0 a 1.1 puntos porcentuales. En consecuencia, las diferencias de cobertura de 1 a 3 puntos entre métodos están cerca del ruido y no deben sobreinterpretarse: las comparaciones sólidas son las de orden de magnitud del ancho en la rampa (732 frente a 1203 MWh) y la dirección del canje cobertura por ancho, no el ranking fino entre variantes de gamma.

## 6. Resultado negativo: el sigma(x) heterocedástico no reduce el techo de sharpness

Siguiendo la especificación de `ESPECIFICACION_SIGMA_X.md`, se entrenó un modelo base heterocedástico que sustituye el sigma constante de la magnitud por un sigma(x) predicho por una segunda etapa (XGBoost sobre residuos out-of-fold en el espacio log), con la misma media, la misma disciplina de split y sin tocar la capa conformal. Los drivers de la varianza tienen importancia repartida y ninguno domina (p_occ 23.1%, volatilidad móvil 20.8%, tecnología 20.6%, día del año 18.7%, log de potencia 16.8%), y el sigma(x) resultante es genuinamente heterocedástico (mediana 1.63, percentil 10 en 0.96, percentil 90 en 2.45, contra el 1.70 constante). Pese a ello, el modelo se descarta como modelo base del experimento central. Tres diagnósticos, sobrios:

1. Calibración global de la predictiva (PIT crudo, distancia KS a la uniforme, OOS 2024 a 2026): sigma constante KS = 0.1667, sigma(x) KS = 0.1724. El sigma(x) no mejora la calibración global; la empeora de forma marginal.
2. Scores propios de la predictiva base (OOS 2024 a 2026): sigma(x) mejora levemente, CRPS 79.06 frente a 81.77 MWh y log-score 4.9819 frente a 4.9924. La mejora existe pero es de segundo orden.
3. Cobertura del cuantil 90% propio por tercil de tamaño de central (nominal 90%): con sigma constante los tres terciles quedan cerca del nominal (chica 89.2%, media 89.7%, grande 87.4%); con sigma(x) los tres bajan y el tercil grande cae a 83.0% (chica 87.3%, media 87.5%). El sigma(x) introduce sub-cobertura, concentrada en las centrales grandes, que es justamente donde el intervalo importa en MWh absolutos.

El porqué está en el diagnóstico condicional que aísla la dispersión (PIT condicional sobre los positivos, Phi de (log y menos mu) sobre sigma), comparando el train out-of-fold (sin quiebre) contra el OOS (con quiebre BESS):

- train OOF, sin quiebre: KS = 0.0966 con sigma constante, 0.0944 con sigma(x).
- OOS 2024 a 2026, con quiebre: KS = 0.1829 con sigma constante, 0.1822 con sigma(x).

En el train la dispersión ya está bien calibrada (KS cercano a 0.09) y sigma(x) no aporta nada material. En el OOS ambos se deterioran por igual (KS cercano a 0.18) y sigma(x) es indistinguible del constante (0.1822 frente a 0.1829). Es decir, el desajuste que aparece bajo el quiebre no es un problema de dispersión mal especificada, que sigma(x) podría corregir, sino un desplazamiento de la ubicación de la predictiva: el quiebre BESS actúa como un shift de la media condicional (en el espacio log, una traslación), no como un shift de la varianza. Un modelo de varianza refina lo que ya estaba bien (la dispersión) y no toca lo que se rompió (la ubicación), y al reasignar dispersión termina encogiendo los intervalos donde no debe, de ahí la sub-cobertura en el tercil grande.

Implicancia para el paper: el techo de sharpness de la sección 4 es consecuencia del shift de ubicación bajo el quiebre, no de la especificación de la varianza del modelo base. Modelar sigma(x) no es la palanca correcta para bajar el ancho. El resultado es publicable como negativo (un modelo base más flexible en la varianza no ayuda cuando el cambio de régimen es de ubicación), y refuerza que la contribución del flagship está en la adaptación conformal al régimen y no en enriquecer la predictiva base. El modelo base oficial del experimento central sigue siendo el hurdle con sigma constante (`predicciones/pred_hurdle.csv`); el heterocedástico queda documentado en `predicciones/pred_hurdle_hetero.csv` como el comparador de este resultado negativo.

## Observación estructural para la discusión

La figura de cobertura rodante a 90 días muestra una caída común a todos los métodos alrededor de mayo a julio de 2025 (todos bajan a cerca de 85%), que ningún método anticipa. Sugiere un evento o cambio de régimen real de segundo orden en esa ventana, distinto de la rampa BESS principal, y es uno de los asuntos técnicos abiertos registrados en `DECISIONS.md`.
