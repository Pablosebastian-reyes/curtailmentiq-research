# Especificación técnica del sistema
## Pronóstico probabilístico de curtailment con garantías bajo cambio de régimen

Versión de trabajo, 22 de julio de 2026. Documento interno de referencia.
Autores del sistema: Pablo Reyes Cerda (capa A, datos), Kerven Cea Morales (capa B, incertidumbre).

---

## 1. Qué es esto, en una frase

No es un modelo. Es un sistema de **dos capas apiladas**: un modelo estadístico
que estima la distribución del curtailment, y un procedimiento algorítmico que
convierte esa distribución en un intervalo con garantía de cobertura, y que se
adapta cuando el sistema eléctrico cambia de régimen.

```
   Datos CEN            CAPA A                    CAPA B                 Salida
  (dataset v1.0)   Modelo base (hurdle)     Capa de incertidumbre
   293.678 filas  →  p(x), mu(x), sigma  →   score PIT + conformal   →  [0, U(x)]
                     (modelo entrenado)       (procedimiento online)     intervalo
                                                                        con garantía
```

La frontera entre capas es un archivo CSV. Eso permite que cada autor trabaje
por separado y que la capa B se pueda aplicar sobre cualquier modelo base.

---

## 2. Capa A: modelo base (hurdle)

**Qué hace.** Estima la ley de probabilidad completa del curtailment diario de
una central, 7 días adelante.

**Por qué "hurdle" (dos partes).** Cerca de la mitad de los días una central no
vierte nada. Una regresión común se confunde con tanta masa en cero. El modelo
separa el problema:

- **Parte 1, ocurrencia.** Clasificador (gradient boosting) que estima
  `p(x) = P(hay curtailment | x)`.
- **Parte 2, magnitud.** Regresor (gradient boosting) sobre `log(mwh)` de los
  días positivos, que da `mu(x)`, más una dispersión `sigma`.

**Ley predictiva resultante.** Una mezcla:

```
   Y | x  ~  (1 - p(x)) · delta_0   +   p(x) · LogNormal(mu(x), sigma)
```

es decir, con probabilidad `1-p(x)` el valor es exactamente cero, y con
probabilidad `p(x)` sigue una lognormal.

**Especificación del entrenamiento.**

| Elemento | Valor |
|---|---|
| Target | mwh diario por central, horizonte 7 días (predicción directa) |
| Alcance | Solar y eólica (hidro excluida) |
| Corte de entrenamiento | Solo datos hasta 2023-12-31 |
| Período de predicción | 2024-01-01 a 2026-05-31 (104.420 filas) |
| Features | Lags 1, 7, 14 y medias móviles 7 y 30 del mwh (todos relativos al origen t = T-7, sin fuga), ocurrencia rezagada, día de la semana, día del año, log potencia_mw, región, tecnología |
| sigma | Escalar, 1,7016, estimado out-of-fold (5-fold en train) |
| Semilla | 42 |

**Variante estudiada: sigma(x) heterocedástico.** Segunda etapa que predice la
dispersión en función del contexto, en vez de usarla constante. Features de la
varianza y su importancia: p_occ 23%, volatilidad móvil 60 días 21%,
tecnología 21%, día del año 19%, log potencia 17%. Resultado: ver sección 6.

**Baselines de comparación (MAE, MWh, 2024-2026).**

| Modelo | MAE total |
|---|---|
| Naive estacional semanal | 85,1 |
| GBM cuantílico (q50) | 88,3 |
| Persistencia | 92,2 |
| XGBoost de punto | 93,0 |
| Hurdle (mediana de la mezcla) | 104,1 |

Lectura: el pronóstico de punto está agotado en este problema. Una regla de
calendario le gana a los métodos sofisticados. Esa es la motivación empírica
de todo el sistema: el valor no está en acertar el número, sino en cuantificar
la incertidumbre de forma útil.

---

## 3. Capa B: incertidumbre con garantías

**Qué hace.** Toma la ley predictiva de la capa A y devuelve un intervalo
`[0, U(x)]` que contiene el valor real con probabilidad al menos `1 - alpha`
(nominal 90%), sin asumir que la ley del modelo sea correcta.

**El score PIT.** En vez de medir el error en MWh, se mide en unidades de
probabilidad: `s = F_x(y)`, donde `F_x` es la función de distribución
acumulada de la mezcla. Como `F_x` salta en cero, cuando `y = 0` se randomiza:
`s = F_x(0) · V`, con `V ~ Uniforme(0,1)`.

Por qué importa esta elección: el score vive en `[0,1]`, es homogéneo entre
centrales chicas y grandes, y hace que un cambio de escala en la magnitud
actúe sobre la ley de los scores como una simple traslación, que es lo que
permite adaptarse a la deriva con pocos parámetros.

**Inversión.** El cuantil conformal `q` sobre los scores se invierte para
recuperar el límite en MWh:

```
   U(x) = 0                                              si q <= 1 - p(x)
   U(x) = exp( mu(x) + sigma · Phi^-1( (q - (1-p))/p ) )  en caso contrario
```

Verificada numéricamente contra cobertura oráculo en tres niveles de alpha.

**Cuantil conformal.** `q = s_(k)` con `k = ceil((n+1)(1-alpha))`, la
corrección de muestra finita estándar. Garantiza cobertura al menos `1-alpha`
**bajo intercambiabilidad**. El resto del sistema existe porque ese supuesto
se rompe.

**Métodos comparados.**

| Método | Idea | Rol en el paper |
|---|---|---|
| Split estático | Calibra una vez y no se mueve | Referencia |
| Weighted por punto (Tibshirani 2019) | Repondera la calibración por razón de densidades | **Negative result**: 76% de intervalos infinitos en la rampa |
| Recencia con pesos fijos (Barber 2023) | Decaimiento exponencial hacia el pasado | Benchmark; con pool fijo colapsa, con pool deslizante funciona |
| Ventana deslizante | Recalibra con los últimos 60 días | Resultado positivo simple |
| ACI (Gibbs y Candès 2021) | Ajusta alpha online según los errores observados | Resultado positivo principal |
| **Transporte de scores + ACI** | Mapea la ley de scores del régimen viejo al nuevo con el mapa monótono de transporte óptimo, y envuelve en ACI | **Contribución teórica** |

**Embargo de horizonte.** Como el pronóstico es a 7 días, al recalibrar en el
día t no se pueden usar observaciones de los últimos 7 días: aún no se
conocen. Implementado en los tres métodos online. Efecto sobre los resultados:
dentro del error de muestreo, sin sesgo direccional. Es requisito de validez,
no de desempeño.

---

## 4. Protocolo de evaluación

**Cortes temporales (datos reales).**

| Conjunto | Período | Rol |
|---|---|---|
| Entrenamiento | hasta 2023-12-31 | Ajuste de la capa A |
| Calibración | ene a ago 2024 | Ajuste de la capa B |
| test_pre | sep 2024 | Régimen estable |
| test_ramp | oct a dic 2024 | Inicio de la rampa BESS |
| test_post | 2025-S1 en adelante | Post quiebre, por semestre |

**Métricas.**

- **Cobertura empírica**: qué fracción de los valores reales cae dentro del
  intervalo. Debe acercarse al 90% nominal. Los errores estándar se
  **clusterizan por fecha**, porque todas las centrales comparten el estado
  del sistema el mismo día (rondan 1,0 a 1,1 puntos: diferencias de 1 a 3
  puntos entre métodos están dentro del ruido).
- **Ancho medio (sharpness)**: a igual cobertura, más angosto es mejor.
- **Porcentaje de intervalos infinitos**: cuando el método responde "no sé".
- **CRPS**: calidad global del pronóstico probabilístico.

---

## 5. Cómo se corre

Secuencia completa, de datos crudos a resultados del paper:

```
1. ETL y dataset            etl/*.py                     → release/v1.0/
2. Exploración              flagship-eda/generar_eda.py  → figuras del EDA
3. Capa A (modelo base)     flagship/entrenar_baselines.py
                                                         → flagship/predicciones/*.csv
4. Capa A variante          flagship/entrenar_hurdle_hetero.py
                                                         → pred_hurdle_hetero.csv
5. Capa B, sintético        flagship/conformal_prototype.py, conformal_v2.py
                                                         → tabla comparativa sintética
6. Capa B, datos reales     flagship/conformal_v3_real.py
                                                         → tabla y figuras del paper
7. Comparación sigma(x)     flagship/conformal_v3_hetero.py
                                                         → conformal_v3_hetero_comparacion.csv
```

Todo con semilla fija y regenerable. Requiere numpy, pandas, scipy,
scikit-learn.

**La interfaz entre capas** es `flagship/predicciones/pred_hurdle.csv`, con
columnas `fecha, central_codigo, tecnologia, y_real, p_occ, mu_log, sigma`.
Para probar la capa B sobre otro modelo base, basta generar un CSV con ese
mismo formato.

---

## 6. Estado de los resultados (datos reales)

**Comportamiento del conformal estático.** Cobertura entre 89% y 95% en todos
los períodos. La sobrecobertura severa que aparecía en el banco sintético
(99,8%) **no** se reproduce en datos reales: el modelo base, con sus lags y
medias móviles, absorbe buena parte del quiebre BESS. Consecuencia: la tensión
entre cobertura y sharpness es leve fuera de la transición.

**Dónde paga la adaptatividad.** En la rampa BESS. Transporte + ACI baja el
ancho de 1203 a 732 MWh manteniendo 90,7% de cobertura. Fuera de la
transición, las diferencias entre métodos son ambiguas y a veces caen dentro
del error estándar.

**Negative result.** Weighted conformal por punto, bien implementado, entrega
intervalos infinitos en 76% de los casos durante la rampa. Robusto a la
elección de score, lo que demuestra que el fallo viene del cambio de régimen y
no de la geometría del score.

**Variante sigma(x): mejora de sharpness con costo condicional.**

| Métrica | sigma constante | sigma(x) |
|---|---|---|
| Cobertura agregada (estático) | 92,5% | 90,9% |
| Ancho | referencia | 17 a 36% más angosto |
| Rampa | 95,3% / 1203 MWh | 91,7% / 769 MWh |
| Terciles (chicas / medias / grandes) | 93,1 / 93,3 / 91,1% | 91,9 / 92,8 / 87,8% |

Diagnóstico del porqué: los residuos en escala logarítmica son casi
homocedásticos condicionalmente, y el quiebre BESS actúa como un
desplazamiento de la ubicación (el modelo sub-predice la magnitud después del
quiebre), no de la dispersión. Modelar la varianza no corrige un sesgo de
media.

**Decisión de diseño**: se mantiene sigma constante como modelo base del
experimento central, porque la confiabilidad por central (cobertura
condicional) es el requisito operacional para un asset manager, y sigma(x)
sacrifica 3,3 puntos en las centrales grandes. La comparación se reporta como
subsección propia de resultados.

---

## 7. Qué queda

- Ratificar la reetiquetación de sigma(x) (de "resultado negativo" a "mejora
  de sharpness con costo condicional") y dejar consistentes DECISIONS.md e
  INDICE_PAPER.md.
- Migrar `draft/04_methods.md` a LaTeX en Overleaf, para que la formulación
  sea legible por terceros.
- Redactar las secciones restantes sobre el índice ya definido.
- Trabajo futuro declarado: detección de change-point para el episodio de
  mayo a julio 2025, horizontes distintos de 7 días, transporte multivariado
  entre centrales.
