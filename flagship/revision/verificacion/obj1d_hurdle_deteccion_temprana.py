#!/usr/bin/env python3
"""
El hurdle con DETENCION TEMPRANA.
=================================
La Seccion 5.4 concede por escrito que un hurdle con detencion temprana
"plausiblemente recuperaria su rendimiento a 800 arboles" cuando se le da un
presupuesto mayor. Es una concesion razonable pero no medida, y el manuscrito no
deberia conceder lo que puede comprobar. Esto lo mide.

PROTOCOLO. La disciplina del paper es que ningun modelo ve datos posteriores a
2023-12-31. La detencion temprana necesita un conjunto de validacion, asi que se
toma un corte TEMPORAL dentro del periodo de entrenamiento: los ultimos seis
meses (2023-07-01 a 2023-12-31) validan, el resto entrena. Con eso se selecciona
el numero de arboles de cada etapa del hurdle por separado, el clasificador de
ocurrencia y el regresor de la log-magnitud, con un techo de 4000 y paciencia de
50 rondas.

Seleccionado el numero de arboles, se REAJUSTA cada etapa sobre el periodo de
entrenamiento completo con ese numero, que es la practica habitual: la validacion
sirve para elegir el presupuesto, no para recortar los datos del modelo final.
La dispersion sigma se estima out-of-fold con el mismo procedimiento de siempre y
con el numero de arboles ya elegido.

Se comparan tres objetos, todos con el mismo panel, las mismas features, el mismo
corte temporal y la misma semilla:

  hurdle_400   2 x 400 arboles, el modelo base del paper
  hurdle_2000  2 x 2000 arboles, el brazo agrandado de la Seccion 5.4
  hurdle_es    detencion temprana, con techo 4000 y paciencia 50

La pregunta concreta: ¿la detencion temprana devuelve al hurdle agrandado al
rendimiento que tiene con 800 arboles, o lo lleva mas alla?

Salida: resultados/verificacion/obj1d_deteccion_temprana.json

Comando:
  <venv>/bin/python flagship/revision/verificacion/obj1d_hurdle_deteccion_temprana.py
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from xgboost import XGBClassifier, XGBRegressor

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'flagship'))
sys.path.insert(0, str(REPO / 'flagship' / 'revision'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import entrenar_baselines as EB            # noqa: E402
import rev_lib as R                        # noqa: E402
import obj1_capacidad_contra_forma as O1   # noqa: E402

SAL = REPO / 'resultados' / 'verificacion'
CORTE_VAL = pd.Timestamp('2023-07-01')   # ultimos seis meses del train validan
TECHO = 4000
PACIENCIA = 50


def entrenar_con_es(df_tr, df_pr):
    """Selecciona el numero de arboles por etapa con detencion temprana sobre un
    corte temporal, y reajusta cada etapa sobre el train completo."""
    ent = df_tr[df_tr.fecha < CORTE_VAL]
    val = df_tr[df_tr.fecha >= CORTE_VAL]
    print(f'    seleccion: entrena {len(ent):,} filas (< {CORTE_VAL.date()}), '
          f'valida {len(val):,}')
    par = dict(EB.XGB_PARAMS)
    par['n_estimators'] = TECHO
    par['early_stopping_rounds'] = PACIENCIA
    elegidos = {}

    # etapa 1: ocurrencia
    clf = XGBClassifier(objective='binary:logistic', eval_metric='logloss', **par)
    clf.fit(ent[EB.FEATS], (ent.y_real.values > 0).astype(int),
            eval_set=[(val[EB.FEATS], (val.y_real.values > 0).astype(int))],
            verbose=False)
    elegidos['ocurrencia'] = int(clf.best_iteration) + 1

    # etapa 2: log-magnitud sobre los positivos
    pe, pv = ent[ent.y_real > 0], val[val.y_real > 0]
    reg = XGBRegressor(objective='reg:squarederror', **par)
    reg.fit(pe[EB.FEATS], np.log(pe.y_real.values),
            eval_set=[(pv[EB.FEATS], np.log(pv.y_real.values))], verbose=False)
    elegidos['magnitud'] = int(reg.best_iteration) + 1
    print(f'    arboles elegidos: ocurrencia {elegidos["ocurrencia"]}, '
          f'magnitud {elegidos["magnitud"]}')

    # reajuste sobre el train completo con el presupuesto elegido
    fin = dict(EB.XGB_PARAMS)
    fin['n_estimators'] = elegidos['ocurrencia']
    clf2 = XGBClassifier(objective='binary:logistic', eval_metric='logloss', **fin)
    clf2.fit(df_tr[EB.FEATS], (df_tr.y_real.values > 0).astype(int))
    p = clf2.predict_proba(df_pr[EB.FEATS])[:, 1]

    fin['n_estimators'] = elegidos['magnitud']
    pos = df_tr[df_tr.y_real > 0]
    Xp, yl = pos[EB.FEATS], np.log(pos.y_real.values)
    reg2 = XGBRegressor(objective='reg:squarederror', **fin)
    reg2.fit(Xp, yl)
    mu = reg2.predict(df_pr[EB.FEATS])

    oof = np.full(len(yl), np.nan)
    for itr, ite in KFold(5, shuffle=True, random_state=EB.SEED).split(Xp):
        rf = XGBRegressor(objective='reg:squarederror', **fin)
        rf.fit(Xp.iloc[itr], yl[itr]); oof[ite] = rf.predict(Xp.iloc[ite])
    sigma = float(np.std(yl - oof, ddof=1))
    arboles = elegidos['ocurrencia'] + elegidos['magnitud']
    return R.PredictivaHurdle(p, mu, sigma), arboles, sigma, elegidos


def main():
    print('=' * 92)
    print('HURDLE CON DETENCION TEMPRANA')
    print(f'techo {TECHO} arboles, paciencia {PACIENCIA}, validacion temporal '
          f'desde {CORTE_VAL.date()}')
    print('=' * 92)
    df_tr, df_pr = O1.panel()
    filas, meta = [], {}

    for etq, n_est in (('hurdle_400', 400), ('hurdle_2000', 2000)):
        pred, arb, sg = O1.entrenar_hurdle(df_tr, df_pr, n_est)
        print(f'\n  {etq}: {arb} arboles, sigma {sg:.4f}')
        filas += O1.evaluar(etq, pred, df_pr, arb, persistir=False)
        meta[etq] = dict(arboles=arb, sigma=sg)

    print('\n  hurdle_es (detencion temprana):')
    pred, arb, sg, el = entrenar_con_es(df_tr, df_pr)
    print(f'    total {arb} arboles, sigma {sg:.4f}')
    filas += O1.evaluar('hurdle_es', pred, df_pr, arb, persistir=False)
    meta['hurdle_es'] = dict(arboles=arb, sigma=sg, por_etapa=el)

    T = pd.DataFrame(filas)
    T.to_csv(SAL / 'obj1d_deteccion_temprana.csv', index=False)
    est = T[T.metodo == 'estatico']

    print('\n' + '=' * 92)
    print('RESULTADO')
    print('=' * 92)
    print(f'  {"modelo":14s} {"arboles":>8s} {"sigma":>8s} '
          f'{"CRPS transicion":>16s} {"CRPS test":>11s} {"cobertura est.":>15s}')
    res = {}
    for etq in ('hurdle_400', 'hurdle_2000', 'hurdle_es'):
        tr = est[(est.modelo == etq) & (est.periodo == 'test_transition')].iloc[0]
        tt = est[(est.modelo == etq) & (est.periodo == 'TEST_COMPLETO')].iloc[0]
        res[etq] = dict(arboles=int(tr.arboles), sigma=meta[etq]['sigma'],
                        por_etapa=meta[etq].get('por_etapa'),
                        crps_transicion=float(tr.crps), crps_test=float(tt.crps),
                        cobertura_estatica=float(tt.cobertura),
                        ancho_estatico=float(tt.ancho_medio))
        print(f'  {etq:14s} {int(tr.arboles):>8d} {meta[etq]["sigma"]:>8.4f} '
              f'{tr.crps:>16.2f} {tt.crps:>11.2f} {tt.cobertura:>14.1f}%')

    b400, bes = res['hurdle_400']['crps_test'], res['hurdle_es']['crps_test']
    b2000 = res['hurdle_2000']['crps_test']
    print(f'\n  contra el hurdle de 800 arboles: {100*(bes/b400-1):+.1f}% de CRPS')
    print(f'  contra el hurdle de 4000 arboles: {100*(bes/b2000-1):+.1f}%')
    if bes <= b400 * 1.005:
        veredicto = ('la detencion temprana devuelve al hurdle a su rendimiento '
                     'de 800 arboles o mejor')
    else:
        veredicto = ('la detencion temprana NO devuelve al hurdle a su '
                     'rendimiento de 800 arboles')
    print(f'  veredicto: {veredicto}')

    # el GBM multi-cuantil, para situar la comparacion
    t = pd.read_csv(REPO / 'resultados' / 'fase0' / 'fase0_tabla_por_modelo.csv')
    q = t[(t.modelo_base == 'qgbm_multi') & (t.periodo == 'test_transition')].crps_base.iloc[0]
    print(f'\n  referencia: el GBM multi-cuantil da CRPS {q:.2f} en la transicion, '
          f'contra {res["hurdle_es"]["crps_transicion"]:.2f} del hurdle con detencion temprana')

    json.dump(dict(techo=TECHO, paciencia=PACIENCIA,
                   corte_validacion=str(CORTE_VAL.date()),
                   resultados=res, veredicto=veredicto,
                   crps_qgbm_transicion=float(q)),
              open(SAL / 'obj1d_deteccion_temprana.json', 'w'), indent=1)
    print(f'\nguardado {SAL / "obj1d_deteccion_temprana.json"}')


if __name__ == '__main__':
    main()
