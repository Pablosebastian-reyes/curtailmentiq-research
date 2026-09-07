#!/usr/bin/env python3
"""
OBJECION 1: ¿la dominacion del GBM multi-cuantil es forma o capacidad?
======================================================================
El manuscrito compara un hurdle de 2 modelos boosted de 400 arboles (800 arboles
desplegados) contra un GBM multi-cuantil de 54 modelos de 400 arboles (21.600
arboles). Comparten features, filas, corte temporal, hiperparametros por modelo
y semilla, pero no capacidad. Un revisor puede decir que la comparacion confunde
forma del modelo con presupuesto del modelo.

Se ataca por las DOS direcciones, que es lo que hace concluyente el experimento:

  A. GBM multi-cuantil ENCOGIDO al presupuesto del hurdle.
     54 niveles x 15 arboles = 810 arboles, contra los 800 del hurdle.
     Si aun asi gana, la ventaja no es capacidad.

  B. Hurdle AGRANDADO.
     2 etapas x 2000 arboles = 4000 arboles, cinco veces su presupuesto.
     Si no cierra la brecha, el deficit del hurdle no es de capacidad: es la
     forma lognormal de cola fija.

  C. GBM multi-cuantil con rejilla GRUESA a capacidad plena.
     9 niveles x 400 arboles = 3.600 arboles. Aisla el efecto de la finura de la
     rejilla del efecto del presupuesto total.

Todo lo demas identico: mismas features, mismas filas, mismo corte 2023-12-31,
misma semilla 42, y despues la misma capa conformal con las mismas constantes.

Metrica de arbitraje: CRPS de la predictiva base e interval score del limite
unilateral, ambos en la ventana de transicion y sobre el test completo.

Salida: resultados/verificacion/obj1_capacidad.json y .csv
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from xgboost import XGBClassifier, XGBRegressor
from sklearn.model_selection import KFold

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'flagship'))
sys.path.insert(0, str(REPO / 'flagship' / 'revision'))
import entrenar_baselines as EB     # noqa: E402
import rev_lib as R                 # noqa: E402
import fase0_entrenar_qgbm as QG    # noqa: E402

SAL = REPO / 'resultados' / 'verificacion'
TAUS_GRUESA = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])


def panel():
    piv, estat = EB.construir_panel()
    largo = EB.construir_features(piv)
    largo = largo.merge(estat[['central_codigo', 'tecnologia', 'region',
                               'log_potencia_mw']], on='central_codigo')
    for c in ('region', 'tecnologia'):
        largo[c] = pd.Categorical(largo[c], categories=sorted(largo[c].unique()))
    comun = largo.y_real.notna() & largo.mwh_t.notna()
    tr = largo[comun & (largo.fecha <= EB.CORTE_TRAIN)].reset_index(drop=True)
    pr = largo[comun & (largo.fecha >= EB.PRED_INI)
               & (largo.fecha <= EB.PRED_FIN)].reset_index(drop=True)
    return tr, pr


def entrenar_qgbm(df_tr, df_pr, taus, n_estimators):
    par = dict(EB.XGB_PARAMS); par['n_estimators'] = n_estimators
    m = XGBRegressor(objective='reg:quantileerror', quantile_alpha=taus, **par)
    m.fit(df_tr[EB.FEATS], df_tr.y_real.values)
    Q = np.maximum(0.0, np.sort(np.asarray(m.predict(df_pr[EB.FEATS]), float), axis=1))
    return R.PredictivaCuantilica(Q, taus), len(taus) * n_estimators


def entrenar_hurdle(df_tr, df_pr, n_estimators):
    par = dict(EB.XGB_PARAMS); par['n_estimators'] = n_estimators
    X_tr, y_tr = df_tr[EB.FEATS], df_tr.y_real.values
    X_pr = df_pr[EB.FEATS]
    clf = XGBClassifier(objective='binary:logistic', eval_metric='logloss', **par)
    clf.fit(X_tr, (y_tr > 0).astype(int))
    p = clf.predict_proba(X_pr)[:, 1]
    pos = y_tr > 0
    Xp, yl = X_tr[pos], np.log(y_tr[pos])
    reg = XGBRegressor(objective='reg:squarederror', **par)
    reg.fit(Xp, yl)
    mu = reg.predict(X_pr)
    oof = np.full(pos.sum(), np.nan)
    for itr, ite in KFold(5, shuffle=True, random_state=EB.SEED).split(Xp):
        rf = XGBRegressor(objective='reg:squarederror', **par)
        rf.fit(Xp.iloc[itr], yl[itr]); oof[ite] = rf.predict(Xp.iloc[ite])
    sigma = float(np.std(yl - oof, ddof=1))
    return R.PredictivaHurdle(p, mu, sigma), 2 * n_estimators, sigma


SERIES = SAL / 'series'


def clave_archivo(nombre):
    """Nombre de archivo seguro a partir de la etiqueta del brazo."""
    return (nombre.split(' (')[0].strip()
            .replace(' ', '_').replace('/', '_').replace('.', 'p'))


def evaluar(nombre, pred, df_pr, arboles, extra='', persistir=True):
    """Capa conformal identica a la del experimento, y metricas.

    PERSISTENCIA DE SERIES (anadido para la Fase 0b). Ademas de las metricas
    agregadas, se guarda por brazo la serie POR FILA de fecha, y, U del split
    estatico y U de Transporte+ACI(0.05). El diagnostico ampliado necesita
    recomputar cobertura y ancho de cada celda sobre remuestreos de dias
    completos, y para eso las metricas agregadas no alcanzan: hacen falta las
    filas. Sin esto habria que reentrenar los ocho brazos en cada replica.
    """
    h = df_pr[['fecha', 'central_codigo', 'y_real']].copy()
    h = h.sort_values(['fecha', 'central_codigo'])
    orden = h.index.values
    pred = pred.sub(orden)
    h = h.reset_index(drop=True)
    rng = np.random.default_rng(R.SEED_CONFORMAL)
    h['s'] = pred.cdf(h.y_real.values, rng)
    s_cal = h.s.values[((h.fecha >= R.CAL_INI) & (h.fecha < R.CAL_FIN)).values]
    idx = (h.fecha >= R.CAL_FIN).values
    test = h[idx].reset_index(drop=True)
    p_t = pred.sub(idx)
    y_t, f_t = test.y_real.values, test.fecha.values
    fechas = np.sort(test.fecha.unique())

    U_est = R.estatico(p_t, s_cal)
    R.transporte_aci(p_t, s_cal, h.s.values, h.fecha.values, y_t, f_t, fechas,
                     0.02, rng, ini_test=R.CAL_FIN)
    U_tr, _, _ = R.transporte_aci(p_t, s_cal, h.s.values, h.fecha.values, y_t,
                                  f_t, fechas, 0.05, rng, ini_test=R.CAL_FIN)
    filas = []
    rng_c = np.random.default_rng(R.SEED_CRPS)
    for nm, ini, fin in R.PERIODOS + [('TEST_COMPLETO', R.CAL_FIN,
                                       pd.Timestamp('2026-06-01'))]:
        m = (f_t >= np.datetime64(pd.Timestamp(ini).date())) & \
            (f_t < np.datetime64(pd.Timestamp(fin).date()))
        if m.sum() == 0:
            continue
        crps = R.crps_pred(p_t.sub(m), y_t[m], np.random.default_rng(R.SEED_CRPS))
        for met, U in (('estatico', U_est), ('transporte_g05', U_tr)):
            f = R.resumen_metrico(met, nm, f_t[m], y_t[m], U[m])
            f.update(modelo=nombre, arboles=arboles, crps=round(crps, 2), nota=extra)
            filas.append(f)

    if persistir:
        SERIES.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(dict(fecha=f_t, y=y_t, U_est=U_est, U_tr=U_tr)).to_parquet(
            SERIES / f'{clave_archivo(nombre)}.parquet', index=False)
    return filas


def main():
    print('=' * 96)
    print('OBJECION 1 - CAPACIDAD CONTRA FORMA')
    print('=' * 96)
    df_tr, df_pr = panel()
    print(f'train {len(df_tr):,} filas, prediccion {len(df_pr):,} filas')
    filas = []

    print('\n[ref] hurdle original, 2 x 400 = 800 arboles')
    pred, arb, sg = entrenar_hurdle(df_tr, df_pr, 400)
    print(f'      sigma = {sg:.4f}')
    filas += evaluar('hurdle_400 (referencia)', pred, df_pr, arb)

    print('\n[A] GBM multi-cuantil encogido: 54 niveles x 15 arboles')
    pred, arb = entrenar_qgbm(df_tr, df_pr, QG.TAUS, 15)
    print(f'      {arb} arboles, contra 800 del hurdle')
    filas += evaluar('qgbm_54x15 (capacidad equiparada)', pred, df_pr, arb)

    print('\n[B] hurdle agrandado: 2 x 2000 arboles')
    pred, arb, sg = entrenar_hurdle(df_tr, df_pr, 2000)
    print(f'      {arb} arboles, sigma = {sg:.4f}')
    filas += evaluar('hurdle_2000 (capacidad x5)', pred, df_pr, arb)

    print('\n[C] GBM multi-cuantil de rejilla gruesa: 9 niveles x 400 arboles')
    pred, arb = entrenar_qgbm(df_tr, df_pr, TAUS_GRUESA, 400)
    print(f'      {arb} arboles')
    filas += evaluar('qgbm_9x400 (rejilla gruesa)', pred, df_pr, arb)

    T = pd.DataFrame(filas)
    T.to_csv(SAL / 'obj1_capacidad.csv', index=False)
    cols = ['modelo', 'arboles', 'metodo', 'cobertura', 'se_cluster',
            'ancho_medio', 'pct_infinito', 'IS_finitos', 'crps']
    for per in ('test_transition', 'TEST_COMPLETO'):
        print(f'\n{"=" * 96}\n{per}\n{"=" * 96}')
        print(T[T.periodo == per][cols].to_string(index=False))
    print(f'\nguardado {SAL / "obj1_capacidad.csv"}')


if __name__ == '__main__':
    main()
