#!/usr/bin/env python3
"""
EXPERIMENTO 1 DEL FLAGSHIP: modelos base de pronostico sobre dataset v1.0
=========================================================================
Entrena los modelos base (persistencia, naive estacional, XGBoost punto,
GBM cuantilico, hurdle) SOLO con datos hasta 2023-12-31 y genera las
predicciones out-of-sample 2024-01-01 a 2026-05-31 que alimentan la capa
de incertidumbre (Kerven). Sin conformal, sin intervalos, sin hidro.

Diseno temporal (prediccion directa a 7 dias):
  - Con informacion disponible hasta el dia t se predice el dia T = t+7.
  - Cada fila de salida esta indexada por la fecha TARGET T.
  - Toda feature dinamica es un shift >= 7 dias respecto de T (se verifica
    con una asercion en construccion). Cero fuga de informacion.

Entrada:  release/v1.0/ (dataset congelado 2026-07-04, ver CHECKSUMS.sha256)
Salida:   flagship/predicciones/ (un CSV por modelo + README.md con reporte)
Reproducibilidad: seed fija 42, XGBoost hist deterministico con n_jobs fijo.
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.model_selection import KFold
from xgboost import XGBClassifier, XGBRegressor

SEED = 42
H = 7                                   # horizonte en dias
CORTE_TRAIN = pd.Timestamp('2023-12-31')  # ultimo target usado para entrenar
PRED_INI = pd.Timestamp('2024-01-01')
PRED_FIN = pd.Timestamp('2026-05-31')

REPO = Path(__file__).resolve().parent.parent
RELEASE = REPO / 'release' / 'v1.0'
SALIDA = REPO / 'flagship' / 'predicciones'

# Hiperparametros fijados a priori (NUNCA ajustados contra 2024-2026).
XGB_PARAMS = dict(n_estimators=400, learning_rate=0.05, max_depth=6,
                  min_child_weight=5, subsample=0.9, colsample_bytree=0.9,
                  tree_method='hist', enable_categorical=True,
                  random_state=SEED, n_jobs=4)

FEATS = ['mwh_t', 'mwh_lag1', 'mwh_lag7', 'mwh_lag14', 'ma7_t', 'ma30_t',
         'occ_t', 'dow_target', 'doy_target', 'log_potencia_mw',
         'region', 'tecnologia']


# =====================================================================
# 1. PANEL: solar + eolica, calendario continuo por central
# =====================================================================
def construir_panel():
    d = pd.read_parquet(RELEASE / 'curtailment_daily.parquet')
    d['fecha'] = pd.to_datetime(d['fecha'])
    plants = pd.read_csv(RELEASE / 'plants.csv')
    meta = pd.read_csv(RELEASE / 'plants_metadata.csv')

    # Solo solar y eolica, segun la clasificacion mas reciente (plants.csv).
    # Verificado: para estas tecnologias no hay discrepancia fila-a-fila.
    keep = plants[plants.tecnologia.isin(['Solar', 'Eólica'])]
    d = d[d.central_codigo.isin(keep.central_codigo)]

    assert not d.duplicated(['fecha', 'central_codigo']).any()

    # Matriz fechas x centrales sobre el calendario completo del release.
    # Antes de la entrada de una central (o en sus dias faltantes por
    # errata) queda NaN: ausencia de reporte, NO cero (los ceros del
    # dataset son explicitos).
    cal = pd.date_range(d.fecha.min(), PRED_FIN, freq='D')
    piv = d.pivot(index='fecha', columns='central_codigo', values='mwh').reindex(cal)

    estat = keep.merge(meta[['central_codigo', 'region', 'potencia_mw']],
                       on='central_codigo')
    estat['log_potencia_mw'] = np.log(estat.potencia_mw)
    return piv, estat


def construir_features(piv):
    """Features indexadas por fecha TARGET T; el origen es t = T - H."""
    occ = (piv > 0).astype(float).where(piv.notna())

    # shift(k) sobre el indice de fechas = valor en T-k. Todo shift >= H.
    partes = {
        'y_real':    piv,
        'mwh_t':     piv.shift(H),        # y(t)   = y(T-7)
        'mwh_lag1':  piv.shift(H + 1),    # y(t-1) = y(T-8)
        'mwh_lag7':  piv.shift(H + 7),    # y(t-7) = y(T-14)
        'mwh_lag14': piv.shift(H + 14),   # y(t-14)= y(T-21)
        'ma7_t':     piv.shift(H).rolling(7, min_periods=7).mean(),
        'ma30_t':    piv.shift(H).rolling(30, min_periods=30).mean(),
        'occ_t':     occ.shift(H),        # 1{y(t)>0}
        # naive estacional: promedio del mismo dia de semana de las 4
        # semanas previas al target (T-7, T-14, T-21, T-28), skipna.
        'naive_est': pd.concat([piv.shift(k) for k in (7, 14, 21, 28)]
                               ).groupby(level=0).mean(),
    }
    for k, v in partes.items():
        assert (v.index == piv.index).all()

    largo = pd.concat({k: v.stack(future_stack=True) for k, v in partes.items()},
                      axis=1).reset_index()
    largo.columns = ['fecha', 'central_codigo'] + list(partes)

    largo['dow_target'] = largo.fecha.dt.dayofweek.astype(np.int16)
    largo['doy_target'] = largo.fecha.dt.dayofyear.astype(np.int16)
    return largo


# =====================================================================
# 2. MODELOS
# =====================================================================
def ajustar_y_predecir(df_tr, df_pr):
    X_tr, y_tr = df_tr[FEATS], df_tr.y_real.values
    X_pr = df_pr[FEATS]
    out = {}

    # a) persistencia y b) naive estacional: no requieren ajuste
    out['persistencia'] = df_pr.mwh_t.values
    out['naive_estacional'] = df_pr.naive_est.values

    # c) XGBoost de punto (squared error), prediccion recortada a >= 0
    print('  ajustando XGBoost punto...')
    reg = XGBRegressor(objective='reg:squarederror', **XGB_PARAMS)
    reg.fit(X_tr, y_tr)
    out['xgboost_punto'] = np.maximum(0, reg.predict(X_pr))

    # d) GBM cuantilico: un modelo por cuantil + rearrangement (sort por
    #    fila) para eliminar cruces de cuantiles + recorte a >= 0
    qs = {}
    for a in (0.1, 0.5, 0.9):
        print(f'  ajustando cuantil {a}...')
        rq = XGBRegressor(objective='reg:quantileerror', quantile_alpha=a,
                          **XGB_PARAMS)
        rq.fit(X_tr, y_tr)
        qs[a] = rq.predict(X_pr)
    Q = np.sort(np.column_stack([qs[a] for a in (0.1, 0.5, 0.9)]), axis=1)
    Q = np.maximum(0, Q)
    out['q10'], out['q50'], out['q90'] = Q[:, 0], Q[:, 1], Q[:, 2]

    # e) hurdle: P(Y>0) + LogNormal(mu(x), sigma) en los positivos
    print('  ajustando hurdle (clasificador)...')
    occ_tr = (y_tr > 0).astype(int)
    clf = XGBClassifier(objective='binary:logistic', eval_metric='logloss',
                        **XGB_PARAMS)
    clf.fit(X_tr, occ_tr)
    out['p_occ'] = clf.predict_proba(X_pr)[:, 1]

    print('  ajustando hurdle (regresor log-magnitud)...')
    pos = y_tr > 0
    X_pos, ylog_pos = X_tr[pos], np.log(y_tr[pos])
    reg_m = XGBRegressor(objective='reg:squarederror', **XGB_PARAMS)
    reg_m.fit(X_pos, ylog_pos)
    out['mu_log'] = reg_m.predict(X_pr)

    # sigma out-of-fold (5-fold) sobre el train: los residuos in-sample de
    # un GBM subestiman la dispersion predictiva (AUDIT_METODOLOGICO.md).
    print('  sigma out-of-fold (5-fold)...')
    oof = np.full(pos.sum(), np.nan)
    for itr, ite in KFold(5, shuffle=True, random_state=SEED).split(X_pos):
        rf = XGBRegressor(objective='reg:squarederror', **XGB_PARAMS)
        rf.fit(X_pos.iloc[itr], ylog_pos[itr])
        oof[ite] = rf.predict(X_pos.iloc[ite])
    out['sigma'] = float(np.std(ylog_pos - oof, ddof=1))
    return out


def mediana_hurdle(p, mu, sigma):
    """Mediana de la mezcla (1-p)*delta_0 + p*LogNormal(mu, sigma)."""
    m = np.zeros(len(p))
    a = p > 0.5
    m[a] = np.exp(mu[a] + sigma * norm.ppf(1 - 0.5 / p[a]))
    return m


# =====================================================================
# 3. MAIN
# =====================================================================
def main():
    RNG_CHECK = np.random.default_rng(SEED)  # noqa: F841 (seed global fijada)
    piv, estat = construir_panel()
    largo = construir_features(piv)
    largo = largo.merge(estat[['central_codigo', 'tecnologia', 'region',
                               'log_potencia_mw']], on='central_codigo')
    for c in ('region', 'tecnologia'):
        largo[c] = pd.Categorical(largo[c], categories=sorted(largo[c].unique()))

    # Conjunto comun: target observado y persistencia definible (y(t) existe).
    # Asi los 5 modelos se evaluan sobre exactamente las mismas filas.
    comun = largo.y_real.notna() & largo.mwh_t.notna()
    df_tr = largo[comun & (largo.fecha <= CORTE_TRAIN)].reset_index(drop=True)
    df_pr = largo[comun & (largo.fecha >= PRED_INI)
                  & (largo.fecha <= PRED_FIN)].reset_index(drop=True)

    print(f'Panel largo: {len(largo):,} celdas | centrales: '
          f'{largo.central_codigo.nunique()} | train: {len(df_tr):,} filas '
          f'(target <= {CORTE_TRAIN.date()}) | prediccion: {len(df_pr):,} '
          f'filas ({PRED_INI.date()} a {PRED_FIN.date()})')

    pred = ajustar_y_predecir(df_tr, df_pr)

    # ---- archivos de salida (un CSV por modelo)
    SALIDA.mkdir(exist_ok=True)
    base = df_pr[['fecha', 'central_codigo', 'tecnologia', 'y_real']].copy()
    base['fecha'] = base.fecha.dt.date

    archivos = {
        'pred_persistencia.csv':     {'y_pred': pred['persistencia']},
        'pred_naive_estacional.csv': {'y_pred': pred['naive_estacional']},
        'pred_xgboost_punto.csv':    {'y_pred': pred['xgboost_punto']},
        'pred_gbm_cuantilico.csv':   {'q10': pred['q10'], 'q50': pred['q50'],
                                      'q90': pred['q90']},
        'pred_hurdle.csv':           {'p_occ': pred['p_occ'],
                                      'mu_log': pred['mu_log'],
                                      'sigma': pred['sigma']},
    }
    for nombre, cols in archivos.items():
        out = base.copy()
        for c, v in cols.items():
            out[c] = v
        fmt = '%.6f' if nombre == 'pred_hurdle.csv' else '%.4f'
        out.to_csv(SALIDA / nombre, index=False, float_format=fmt)
        print(f'  escrito {nombre} ({len(out):,} filas)')

    # ---- reporte descriptivo (sin conclusiones)
    puntos = {
        'persistencia': pred['persistencia'],
        'naive_estacional': pred['naive_estacional'],
        'xgboost_punto': pred['xgboost_punto'],
        'gbm_cuantilico (q50)': pred['q50'],
        'hurdle (mediana mezcla)': mediana_hurdle(pred['p_occ'],
                                                  pred['mu_log'],
                                                  pred['sigma']),
    }
    anio = df_pr.fecha.dt.year.values
    y = df_pr.y_real.values
    anios = sorted(np.unique(anio))
    mae = pd.DataFrame(
        {m: {a: np.abs(y[anio == a] - v[anio == a]).mean() for a in anios}
         | {'total': np.abs(y - v).mean()} for m, v in puntos.items()}).T
    mae = mae.round(2)

    desc = pd.DataFrame({
        'filas': {a: int((anio == a).sum()) for a in anios} | {'total': len(y)},
        'pct_y_cero': {a: round(100 * (y[anio == a] == 0).mean(), 1)
                       for a in anios} | {'total': round(100 * (y == 0).mean(), 1)},
    })

    print('\nMAE (MWh) por modelo y anio — referencia sanitaria, sin conclusiones:')
    print(mae.to_string())
    print('\nFilas y % de y_real = 0 por anio:')
    print(desc.to_string())
    print(f"\nsigma (hurdle, out-of-fold train): {pred['sigma']:.4f}")

    escribir_readme(df_tr, df_pr, mae, desc, pred['sigma'])
    print(f'\nListo. Salidas en {SALIDA}')


def escribir_readme(df_tr, df_pr, mae, desc, sigma):
    import sklearn
    import xgboost
    txt = f"""# Predicciones de los modelos base — Experimento 1 del flagship

**Generado por:** `flagship/entrenar_baselines.py` (seed {SEED}, determinístico) ·
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
  ({len(df_tr):,} filas). Con ese modelo fijo se predice todo
  2024-01-01 a 2026-05-31 ({len(df_pr):,} filas). Los cortes de
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
| `occ_t` | 1{{y(t) > 0}} |
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
| `pred_hurdle.csv` | XGBoost clasificador de ocurrencia + XGBoost sobre log(mwh) de los positivos; Y\\|Y>0 ~ LogNormal(mu_log, sigma) | `p_occ`, `mu_log`, `sigma` |

Decisiones puntuales: `sigma` del hurdle es constante y se estima con
residuos **out-of-fold** (5-fold en train; los residuos in-sample de un GBM
la subestiman, ver `flagship/AUDIT_METODOLOGICO.md`) = {sigma:.4f}.
Ausencia de reporte (central aún no listada, o los 11 días de errata de
PFV-VALLEESCONDIDO) se trata como NaN, nunca como cero; XGBoost maneja los
NaN de features nativamente y los baselines a)/b) definen su propio manejo.

## Reporte descriptivo (sin conclusiones)

MAE (MWh) por modelo y año sobre el conjunto común — referencia sanitaria;
para el hurdle se usa la mediana de la mezcla como pronóstico puntual:

```
{mae.to_string()}
```

Filas y % de y_real = 0 por año:

```
{desc.to_string()}
```

## Reproducibilidad

`python flagship/entrenar_baselines.py` desde la raíz del repo regenera
todo (CSVs y este README). Versiones usadas: python {sys.version.split()[0]},
pandas {pd.__version__}, numpy {np.__version__}, scikit-learn {sklearn.__version__},
xgboost {xgboost.__version__}. Seed {SEED} en todos los componentes con azar
(XGBoost `hist`, KFold); `n_jobs=4` fijo.
"""
    (SALIDA / 'README.md').write_text(txt)


if __name__ == '__main__':
    main()
