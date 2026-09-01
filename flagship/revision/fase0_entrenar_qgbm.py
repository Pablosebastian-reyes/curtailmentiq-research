#!/usr/bin/env python3
"""
FASE 0, paso 1: modelo base alternativo -- GBM MULTI-CUANTIL denso.
===================================================================
Comentario R1.1. El revisor pide un modelo base probabilistico competitivo
distinto del hurdle, y sugiere un GBM multi-cuantil, para poder decidir si la
ventaja de Transport+ACI viene de la capa de calibracion o de su compatibilidad
con la forma parametrica del hurdle.

Disciplina IDENTICA a `flagship/entrenar_baselines.py`, para que la comparacion
sea del modelo y no del protocolo:
  - mismas features, mismo panel, mismo conjunto comun de filas
  - entrenamiento SOLO con target <= 2023-12-31; jamas ve 2024-2026
  - mismos hiperparametros fijados a priori (400 arboles, lr 0.05, depth 6,
    min_child_weight 5, subsample 0.9, colsample 0.9), nunca ajustados contra
    el periodo de evaluacion
  - seed 42

Lo unico que cambia es el objetivo: en vez de una mezcla parametrica
(1-p) delta_0 + p LogNormal(mu, sigma), se estima una rejilla densa de 43
cuantiles con perdida pinball, y la predictiva es la funcion cuantil empirica
interpolada. La inflacion en cero NO se impone: emerge de los cuantiles bajos
que el modelo predice iguales a cero.

Rejilla de cuantiles: 0.02 a 0.98 en pasos de 0.02, mas 0.005, 0.01, 0.99,
0.995 y 0.999 para tener resolucion en la cola donde vive el limite conformal.
Se aplica rearrangement (sort por fila) contra el cruce de cuantiles y recorte
a >= 0.

Salida: flagship/predicciones/pred_qgbm_multi.csv.gz (una columna por cuantil)

Comando:
  <venv>/bin/python flagship/revision/fase0_entrenar_qgbm.py
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

FLAGSHIP = Path(__file__).resolve().parent.parent
REPO = FLAGSHIP.parent
sys.path.insert(0, str(FLAGSHIP))
import entrenar_baselines as EB   # noqa: E402  (reusa panel y features)

SEED = EB.SEED
# Se guarda comprimido: sin comprimir la matriz de 54 cuantiles x 104.420 filas
# pesa 56 MB, por encima del limite blando de GitHub y del criterio del repo de
# no versionar binarios grandes. pandas lee y escribe .gz de forma transparente
# por la extension, asi que no cambia nada mas.
SALIDA = FLAGSHIP / 'predicciones' / 'pred_qgbm_multi.csv.gz'

TAUS = np.unique(np.concatenate([
    [0.005, 0.01],
    np.round(np.arange(0.02, 0.981, 0.02), 4),
    [0.99, 0.995, 0.999],
]))


def main():
    print('=' * 78)
    print('FASE 0 - MODELO BASE ALTERNATIVO: GBM multi-cuantil')
    print(f'{len(TAUS)} cuantiles, de {TAUS[0]} a {TAUS[-1]}')
    print('Misma disciplina de split, features y hiperparametros que el hurdle.')
    print('=' * 78)

    piv, estat = EB.construir_panel()
    largo = EB.construir_features(piv)
    largo = largo.merge(estat[['central_codigo', 'tecnologia', 'region',
                               'log_potencia_mw']], on='central_codigo')
    for c in ('region', 'tecnologia'):
        largo[c] = pd.Categorical(largo[c], categories=sorted(largo[c].unique()))

    comun = largo.y_real.notna() & largo.mwh_t.notna()
    df_tr = largo[comun & (largo.fecha <= EB.CORTE_TRAIN)].reset_index(drop=True)
    df_pr = largo[comun & (largo.fecha >= EB.PRED_INI)
                  & (largo.fecha <= EB.PRED_FIN)].reset_index(drop=True)
    print(f'train: {len(df_tr):,} filas (target <= {EB.CORTE_TRAIN.date()})')
    print(f'prediccion: {len(df_pr):,} filas')

    X_tr, y_tr = df_tr[EB.FEATS], df_tr.y_real.values
    X_pr = df_pr[EB.FEATS]

    print('\najustando GBM multi-cuantil (objetivo reg:quantileerror vectorial)...')
    m = XGBRegressor(objective='reg:quantileerror',
                     quantile_alpha=TAUS, **EB.XGB_PARAMS)
    m.fit(X_tr, y_tr)
    Q = np.asarray(m.predict(X_pr), float)
    print(f'  matriz de cuantiles: {Q.shape}')

    # rearrangement + recorte a >= 0 (mismo tratamiento que el GBM cuantilico
    # de 3 niveles de entrenar_baselines.py)
    cruces = int((np.diff(Q, axis=1) < 0).any(axis=1).sum())
    Q = np.maximum(0.0, np.sort(Q, axis=1))
    print(f'  filas con cruce de cuantiles antes del rearrangement: {cruces:,} '
          f'({100*cruces/len(Q):.1f}%)')

    out = df_pr[['fecha', 'central_codigo', 'tecnologia', 'y_real']].copy()
    for j, t in enumerate(TAUS):
        out[f'q{t:.4f}'] = np.round(Q[:, j], 6)
    out.to_csv(SALIDA, index=False, compression='gzip')
    print(f'\nguardado {SALIDA.relative_to(REPO)}  ({len(out):,} filas)')

    # ---- reporte descriptivo, sin conclusiones ----
    med = Q[:, np.argmin(np.abs(TAUS - 0.5))]
    y = out.y_real.values
    anio = out.fecha.dt.year
    print('\nMAE (MWh) de la mediana del GBM multi-cuantil, por anio:')
    for a in sorted(anio.unique()):
        m_ = anio == a
        print(f'  {a}: {np.abs(med[m_] - y[m_]).mean():8.2f}  (n={m_.sum():,})')
    print(f'  total: {np.abs(med - y).mean():8.2f}')

    F0 = TAUS[np.clip((Q <= 1e-9).sum(axis=1) - 1, 0, len(TAUS) - 1)]
    F0 = np.where((Q <= 1e-9).sum(axis=1) == 0, 0.0, F0)
    print(f'\nAtomo en cero implicito F(0): media {F0.mean():.3f}, '
          f'mediana {np.median(F0):.3f}, filas con F(0)=0: '
          f'{100*(F0 == 0).mean():.1f}%')
    print(f'Fraccion real de y=0 en el periodo: {(y == 0).mean():.3f}')
    print(f'\nCuantil {TAUS[-1]} medio: {Q[:, -1].mean():.1f} MWh; '
          f'maximo {Q[:, -1].max():.1f} MWh')


if __name__ == '__main__':
    main()
