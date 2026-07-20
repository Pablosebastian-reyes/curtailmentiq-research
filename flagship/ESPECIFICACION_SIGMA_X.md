# Especificación del modelo base heterocedástico: sigma(x)

Especificación del modelo base con varianza condicional para el flagship. Motivación: en datos reales el techo de sharpness lo fija la dispersión de la predictiva del hurdle, hoy constante en sigma = 1.70 (out-of-fold). La capa conformal calibra esa dispersión, no la reduce: no puede producir intervalos más angostos que la predictiva base. La palanca de mayor impacto para el ancho, por tanto, está en el modelo base, sustituyendo sigma constante por sigma(x). Este documento fija la forma del modelo, los drivers candidatos de la varianza y el protocolo de evaluación, para que la pieza sea comparable con el hurdle homocedástico actual sin cambiar nada de la capa conformal.

Ámbito: solo la parte de magnitud del hurdle (Y dado Y mayor que 0, modelada como lognormal en el espacio log). La parte de ocurrencia (clasificador de P(Y mayor que 0)) no cambia. La capa conformal PIT y el resto del pipeline (conformal_metodos.py, conformal_v3_real.py) permanecen idénticos: solo cambia de dónde sale sigma en cada fila.

## 1. Forma del modelo

### 1.1 Opción base: dos etapas (media y dispersión)

Estructura en dos etapas sobre los positivos, en el espacio log:

1. Etapa de media. Se conserva el regresor actual de mu(x) (GBM sobre log(y) en los positivos), sin cambios, para no confundir la ganancia de sigma(x) con un cambio de la media.
2. Etapa de dispersión. Se ajusta un segundo modelo para la varianza condicional de los residuos de la etapa 1. Sea r(x) = log(y) menos mu_hat(x) el residuo out-of-fold de la etapa de media. Se modela log(sigma^2)(x) por regresión de los residuos al cuadrado, es decir, un GBM (o modelo equivalente) con target log(r^2) y enlace exponencial para garantizar sigma^2 positivo. La predictiva de magnitud pasa a ser LogNormal(mu(x), sigma(x)).

Esta forma es deliberadamente conservadora: reutiliza la media ya validada y aísla el efecto de la varianza condicional. Es el modelo de referencia para la comparación.

Nota sobre insesgadez: los residuos para la etapa 2 deben ser out-of-fold (los residuos in-sample de un GBM subestiman la dispersión, el mismo motivo por el que el sigma constante actual se estima out-of-fold, ver AUDIT_METODOLOGICO.md). La etapa 2 se ajusta con la misma partición de folds que produjo los residuos, sin reusar folds entre media y varianza.

### 1.2 Alternativa: NGBoost o GAMLSS (distribución completa en una pasada)

Como alternativa de una sola etapa que estima media y dispersión de forma conjunta y coherente:

- NGBoost (Natural Gradient Boosting). Boosting probabilístico que ajusta los parámetros de una distribución paramétrica (aquí LogNormal, o Normal en el espacio log) minimizando un score propio (log-score o CRPS) por natural gradient. Entrega mu(x) y sigma(x) en una sola pasada, con la ventaja de optimizar directamente la calidad probabilística y no solo el ajuste de la media.
- GAMLSS (Generalized Additive Models for Location, Scale and Shape). Marco clásico donde cada parámetro de la distribución (localización, escala y, si se quiere, forma) tiene su propio predictor aditivo. Más interpretable y con inferencia estadística estándar, a costa de menos flexibilidad que el boosting ante interacciones complejas.

Criterio de elección entre las tres: si la ganancia de la forma de dos etapas sobre el sigma constante ya es marginal en el protocolo de la sección 3, no se justifica la complejidad de NGBoost/GAMLSS y se documenta el resultado como negativo. Si la ganancia es material, NGBoost es el candidato principal por optimizar el score probabilístico de extremo a extremo; GAMLSS queda como variante interpretable para el apéndice.

## 2. Drivers candidatos de la varianza

Conjunto de features candidatas para sigma(x), a seleccionar por el protocolo de la sección 3 (no todas entran; se parte del subconjunto con soporte teórico y se poda por ganancia out-of-fold):

- Volatilidad móvil del vertimiento de la central. Desviación estándar (o rango intercuartil) de y en una ventana móvil reciente por central (por ejemplo 14, 28 y 60 días, con embargo de horizonte de 7 días, coherente con DECISIONS.md 2026-07-20). Es el driver con mayor prior: la dispersión del vertimiento es fuertemente heterocedástica en el tiempo y entre centrales, y una central que viene volátil tiende a seguir volátil. Es el feature de volatilidad móvil de referencia.
- Tamaño de central (log de la capacidad instalada). La cola de la magnitud escala con el tamaño; centrales grandes tienen colas absolutas más pesadas.
- Nivel esperado de vertimiento, mu(x) o p_occ(x). La dispersión suele crecer con el nivel (relación media a varianza), así que la propia salida de la etapa de media es un driver natural.
- Estacionalidad y régimen. seas (estacional), trend y el indicador o rampa de BESS: el quiebre de régimen cambia no solo el nivel sino la dispersión.
- Persistencia reciente. y_lag1 y occ_lag1, ya presentes en el modelo de media, como candidatos también para la varianza.

El feature de volatilidad móvil es candidato obligado; el resto se evalúa por aporte incremental. Todos los features móviles respetan el embargo de 7 días para no filtrar el futuro.

## 3. Protocolo de evaluación

Toda comparación es sigma(x) contra el sigma constante actual, con la misma media, los mismos datos y la misma capa conformal, para que la única variable sea la varianza condicional.

### 3.1 Disciplina de split

Misma disciplina out-of-fold que el modelo base actual: los residuos que alimentan la etapa de dispersión (o el ajuste de NGBoost/GAMLSS) son out-of-fold, con la misma partición de folds sobre el train (hasta 2023-12-31), sin fuga entre la estimación de media y la de varianza. La evaluación posterior usa los mismos cortes temporales de calibración y test que conformal_v3_real.py (calibración 2024-01 a 2024-08, test_pre, test_ramp, 2025-S1, 2025-S2, 2026-S1) y el mismo embargo de horizonte de 7 días.

### 3.2 Calibración de la predictiva base (antes de conformal)

Se evalúa la predictiva base por sí sola, sin la capa conformal, para aislar la calidad del modelo:

- Diagnóstico PIT crudo. Se computa el PIT de la predictiva base sobre cada conjunto de test y se mide su distancia a la uniforme con el estadístico de Kolmogorov-Smirnov (KS). El PIT del modelo bien calibrado es uniforme en [0,1]; se reporta el estadístico KS por periodo (menor es mejor) para sigma constante y para sigma(x). El manejo del átomo en cero es el mismo PIT randomizado que ya usa pit_score en conformal_metodos.py.
- CRPS y log-score de la predictiva base. Se reportan ambos scores propios por periodo. El CRPS ya se computa en conformal_v3_real.py (por muestreo de la mezcla hurdle); se agrega el log-score (log-verosimilitud negativa de la predictiva en el outcome), que penaliza con más fuerza la mala calibración de la cola, justo donde sigma importa. Ambos se comparan sigma(x) contra sigma constante.

### 3.3 Prueba end-to-end a cobertura igualada

La comparación de sharpness solo es legítima a cobertura igualada: un modelo más angosto no es mejor si subcubre. Se enchufa cada predictiva base (sigma constante y sigma(x)) a la misma capa conformal PIT y se compara el ancho medio de los intervalos condicionando a igual cobertura empírica por periodo (dentro de la tolerancia del error estándar clusterizado por fecha). La métrica de interés es la reducción de ancho a cobertura igualada; se reporta por periodo, con el error estándar de la cobertura clusterizado por fecha, como en la tabla real actual. La hipótesis a falsar es que sigma(x) reduce el ancho sin perder cobertura, sobre todo fuera de la rampa, donde la dispersión constante sobreancha a las centrales de baja varianza y subancha a las de alta.

### 3.4 Guardrail de piso positivo

sigma(x) puede colapsar a valores muy pequeños en regiones con pocos residuos, produciendo intervalos degenerados y sobreconfiados. Se impone un piso positivo sigma(x) mayor o igual que sigma_min, con sigma_min fijado como una fracción del sigma marginal (por ejemplo un cuantil bajo de la distribución de sigma(x) out-of-fold, no un valor arbitrario). El piso se calibra y se audita con un chequeo por tercil de tamaño de central (capacidad instalada): se verifica que la cobertura condicional se sostiene en los tres terciles (chico, mediano, grande) y que el piso no está saturando de forma sistemática ninguno de ellos. Un piso que se activa casi siempre en el tercil chico es señal de que sigma(x) no está identificado ahí y de que conviene volver a sigma constante para ese subgrupo. El chequeo por tercil es el mismo control de adaptatividad condicional que ya se usa para el score en el audit.

## 4. Criterio de decisión

sigma(x) entra al paper (decisión de alcance condicional, DECISIONS.md 2026-07-20) si, respetando el guardrail y la cobertura igualada, reduce el ancho medio de forma material fuera de la rampa y mejora, o al menos no empeora, el KS del PIT, el CRPS y el log-score de la predictiva base. Si la ganancia es marginal o se paga con pérdida de cobertura condicional en algún tercil, sigma(x) se reporta como el trabajo futuro de mayor prioridad con la evidencia de esta especificación, y el paper se mantiene con sigma constante.
