# Predicciones de los modelos base — Experimento 1 del flagship

**Generado por:** `flagship/entrenar_baselines.py` (seed 42, determinístico) ·
**Insumo:** dataset congelado `release/v1.0/` (corte 2026-05-31, congelado 2026-07-04, ver `CHECKSUMS.sha256`) ·
**Alcance:** solo Solar y Eólica (131 centrales según `plants.csv`); hidro fuera de este experimento.

Estos archivos alimentan la capa de incertidumbre (Kerven). Aquí **no** hay
conformal ni intervalos con garantía: los cuantiles del GBM cuantílico y los
parámetros del hurdle son insumos crudos del modelo base.

## Diseño

- **Target:** `mwh` diario por central. **Horizonte:** 7 días, predicción
  directa: con información disponible hasta el día t se predice T = t+7.
  Cada fila está indexada por la fecha target T.
- **Entrenamiento:** solo filas con target T ≤ 2023-12-31
  (67,032 filas). Con ese modelo fijo se predice todo
  2024-01-01 a 2026-05-31 (104,420 filas). Los cortes de
  calibración/test los decidirá la capa de incertidumbre; por eso el archivo
  cubre el período completo sin cortes.
- **Conjunto común:** las filas de salida son idénticas en los 5 archivos:
  target observado y persistencia definible (existe y(t) = y(T−7)). Una
  central entra a las predicciones 7 días después de su primera aparición
  en los reportes.
- **Hiperparámetros:** fijados a priori (400 árboles, lr 0.05, depth 6,
  subsample 0.9); **nunca** ajustados contra 2024-2026.

## Features (idénticas para los 3 GBM; t = T − 7 es el origen del pronóstico)

| feature | definición |
|---|---|
| `mwh_t` | y(t) = y(T−7), el dato más fresco disponible |
| `mwh_lag1` | y(t−1) |
| `mwh_lag7` | y(t−7) |
| `mwh_lag14` | y(t−14) |
| `ma7_t` | media móvil 7 días terminando en t (ventana completa, si no NaN) |
| `ma30_t` | media móvil 30 días terminando en t (ídem) |
| `occ_t` | 1{y(t) > 0} |
| `dow_target` | día de la semana del target T (0-6; determinístico) |
| `doy_target` | día del año del target T (1-366; elegido sobre "mes" por granularidad) |
| `log_potencia_mw` | log de la potencia máxima bruta (plants_metadata) |
| `region` | región de Chile (categórica) |
| `tecnologia` | Solar / Eólica (categórica) |

Toda feature dinámica es un `shift ≥ 7` sobre el índice de fechas del panel
reindexado a calendario continuo por central (asegura alineación por fecha
aunque haya días faltantes) — cero fuga por construcción.

## Modelos y archivos

| archivo | modelo | columnas de predicción |
|---|---|---|
| `pred_persistencia.csv` | pred(T) = y(T−7) | `y_pred` |
| `pred_naive_estacional.csv` | promedio del mismo día de semana de las 4 semanas previas (T−7, T−14, T−21, T−28; skipna) | `y_pred` |
| `pred_xgboost_punto.csv` | XGBoost squared error, recortado a ≥ 0 | `y_pred` |
| `pred_gbm_cuantilico.csv` | XGBoost quantile loss, un modelo por cuantil; rearrangement (sort por fila) contra cruce de cuantiles; recorte a ≥ 0 | `q10`, `q50`, `q90` |
| `pred_hurdle.csv` | XGBoost clasificador de ocurrencia + XGBoost sobre log(mwh) de los positivos; Y\|Y>0 ~ LogNormal(mu_log, sigma) | `p_occ`, `mu_log`, `sigma` |

Decisiones puntuales: `sigma` del hurdle es constante y se estima con
residuos **out-of-fold** (5-fold en train; los residuos in-sample de un GBM
la subestiman, ver `flagship/AUDIT_METODOLOGICO.md`) = 1.7016.
Ausencia de reporte (central aún no listada, o los 11 días de errata de
PFV-VALLEESCONDIDO) se trata como NaN, nunca como cero; XGBoost maneja los
NaN de features nativamente y los baselines a)/b) definen su propio manejo.

## Reporte descriptivo (sin conclusiones)

MAE (MWh) por modelo y año sobre el conjunto común — referencia sanitaria;
para el hurdle se usa la mediana de la mezcla como pronóstico puntual:

```
                           2024    2025    2026   total
persistencia              88.44   96.32   90.68   92.23
naive_estacional          84.25   86.25   84.18   85.10
xgboost_punto             92.68   94.65   89.69   92.97
gbm_cuantilico (q50)      88.52   89.89   84.30   88.33
hurdle (mediana mezcla)  104.43  104.82  101.60  104.08
```

Filas y % de y_real = 0 por año:

```
        filas  pct_y_cero
2024    40549        19.9
2025    44725        25.4
2026    19146        23.7
total  104420        22.9
```

## Reproducibilidad

`python flagship/entrenar_baselines.py` desde la raíz del repo regenera
todo (CSVs y este README). Versiones usadas: python 3.12.3,
pandas 3.0.3, numpy 2.4.6, scikit-learn 1.9.0,
xgboost 3.2.0. Seed 42 en todos los componentes con azar
(XGBoost `hist`, KFold); `n_jobs=4` fijo.

## Modelo base heterocedastico (`pred_hurdle_hetero.csv`)

Generado por `flagship/entrenar_hurdle_hetero.py` (seed 42). Reemplaza la
dispersion constante del hurdle (`sigma` = 1.7016) por una
`sigma_x` condicional, para bajar el techo de sharpness. Misma disciplina de
split que el resto: `sigma(x)` se estima solo con datos hasta 2023-12-31,
out-of-fold, y jamas ve 2024-2026. Mismas claves que `pred_hurdle.csv`; el
co-autor enchufa su capa conformal cambiando solo el archivo de entrada
(usa `sigma_x` en vez de `sigma`).

Etapas: la 1 (clasificador `p_occ` y regresor `mu_log`) es identica a
`pred_hurdle.csv` (verificado por asercion). La 2 es un GBM que predice la
dispersion: target = log de los residuos out-of-fold de la etapa 1 al
cuadrado; `sigma_raw(x) = exp(pred/2)`, escala global c = 2.0908 para
que `E[(r/sigma)^2] = 1` en OOF de train, y piso 0.9345 (percentil
5 de `sigma(x)` en train; clipa 9.1%
de las filas de prediccion). Features de `sigma(x)`: `log_potencia_mw`,
`tecnologia`, `doy_target`, `p_occ` (out-of-fold en train), y `vol_garch`
(desviacion estandar de la log-magnitud positiva de la central en 60
dias trailing, con shift >= 7).

Columnas: `fecha`, `central_codigo`, `tecnologia`, `y_real`, `p_occ`,
`mu_log`, `sigma_x`.

Reporte descriptivo (sin conclusiones): KS del PIT crudo a la uniforme
0.1667 (constante) contra 0.1724 (`sigma(x)`); CRPS 81.77
contra 79.06 MWh; NLL 4.9924 contra 4.9819. Detalle de
importancia de features y tabla por tercil en
`flagship/entrenar_hurdle_hetero_salida.txt`; histograma PIT en
`flagship/hurdle_hetero_pit.{pdf,png}`.
