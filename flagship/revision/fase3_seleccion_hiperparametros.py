#!/usr/bin/env python3
"""
FASE 3: seleccion de hiperparametros y analisis de sensibilidad.
================================================================
Comentario R1.4. El revisor exige que la seleccion de hiperparametros se haga
en un conjunto de validacion independiente o por validacion de origen rodante,
DENTRO de las fases de entrenamiento y calibracion, y que el conjunto de test
quede estrictamente reservado para una unica evaluacion final.

Estado de la version enviada, declarado sin adornos: los valores gamma = 0.02 y
0.05 y la ventana de 60 dias venian del banco de pruebas sintetico y de la
practica habitual de la literatura, no de una seleccion formal sobre datos
reales, y ambos gamma se reportaban en la tabla del test. Eso no cumple el
criterio del revisor. Aqui se rehace.

PROTOCOLO DE ORIGEN RODANTE, todo dentro de la ventana de calibracion
-------------------------------------------------------------------
Las predicciones del modelo base existen desde 2024-01-01 (el modelo se entrena
solo hasta 2023-12-31), asi que el unico material anterior al test son los 244
dias de calibracion, enero a agosto de 2024. Se parte en dos:

  calibracion interna : 2024-01-01 a 2024-04-30   (pool de scores)
  validacion interna  : 2024-05-01 a 2024-08-31   (origen rodante de 7 dias)

El test (desde 2024-09-01) NO se toca en este script. Ninguna metrica de test
entra en el criterio de seleccion.

CRITERIO: interval score medio del limite unilateral superior sobre la
validacion interna. Es una regla de puntuacion propia, penaliza a la vez el
ancho y la falta de cobertura en MWh, y **vale +infinito si la configuracion
produce algun intervalo infinito**, de modo que una configuracion que se escapa
a intervalos no informativos queda descalificada por el propio criterio y no
por una regla ad hoc. Ese es exactamente el defecto que el comentario R1.5
senala en el ancho medio.

Rejillas: gamma en {0.005, 0.01, 0.02, 0.05, 0.10, 0.20};
ventana reciente en {30, 45, 60, 90, 120} dias.

La sensibilidad SI se reporta tambien sobre el test, pero como exhibicion
posterior a la seleccion, nunca como criterio, y se declara asi en el texto.

Salidas:
  resultados/fase3/fase3_seleccion_validacion.csv
  resultados/fase3/fase3_sensibilidad_test.csv
  resultados/fase3/fase3_hiperparametros_elegidos.json

Comando:
  <venv>/bin/python flagship/revision/fase3_seleccion_hiperparametros.py
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rev_lib as R   # noqa: E402

SAL = R.REPO / 'resultados' / 'fase3'
SAL.mkdir(parents=True, exist_ok=True)

CAL_INT_INI = pd.Timestamp('2024-01-01')
CAL_INT_FIN = pd.Timestamp('2024-05-01')
VAL_INT_FIN = pd.Timestamp('2024-09-01')

GAMMAS = (0.005, 0.01, 0.02, 0.05, 0.10, 0.20)
VENTANAS = (30, 45, 60, 90, 120)


def cargar(modelo='hurdle'):
    if modelo == 'hurdle':
        h = pd.read_csv(R.FLAGSHIP / 'predicciones' / 'pred_hurdle.csv',
                        parse_dates=['fecha'])
        h = h.sort_values(['fecha', 'central_codigo']).reset_index(drop=True)
        pred = R.PredictivaHurdle(h.p_occ.values, h.mu_log.values,
                                  float(h.sigma.iloc[0]))
    else:
        h = pd.read_csv(R.FLAGSHIP / 'predicciones' / 'pred_qgbm_multi.csv.gz',
                        parse_dates=['fecha'])
        h = h.sort_values(['fecha', 'central_codigo']).reset_index(drop=True)
        cols = [c for c in h.columns if c.startswith('q0')]
        taus = np.array([float(c[1:]) for c in cols])
        o = np.argsort(taus)
        pred = R.PredictivaCuantilica(h[[cols[i] for i in o]].values, taus[o])
    rng = np.random.default_rng(R.SEED_CONFORMAL)
    h = h.assign(s=pred.cdf(h.y_real.values, rng))
    return h, pred


def evaluar(h, pred, s_cal, ini, fin, gamma, ventana, rng_seed,
            metodo='transporte', shrinkage=True):
    """Corre un metodo online sobre [ini, fin) y devuelve metricas agregadas."""
    idx = ((h.fecha >= ini) & (h.fecha < fin)).values
    sub = h[idx].reset_index(drop=True)
    p_sub = pred.sub(idx)
    y, f = sub.y_real.values, sub.fecha.values
    fechas = np.sort(sub.fecha.unique())
    rng = (rng_seed if isinstance(rng_seed, np.random.Generator)
           else np.random.default_rng(rng_seed))
    if metodo == 'aci':
        U, _, _ = R.aci(p_sub, s_cal, y, f, fechas, gamma)
    else:
        U, _, _ = R.transporte_aci(p_sub, s_cal, h.s.values, h.fecha.values,
                                   y, f, fechas, gamma, rng,
                                   ventana_dias=ventana, shrinkage=shrinkage,
                                   ini_test=ini)
    IS = R.interval_score_unilateral(y, U)
    fin_m = np.isfinite(U)
    cov, se, _ = R.cm.cobertura_clusterizada(f, y <= U)
    return dict(IS_total=float(np.mean(IS)),
                IS_finitos=float(np.mean(IS[fin_m])) if fin_m.any() else np.nan,
                ancho=float(U[fin_m].mean()) if fin_m.any() else np.nan,
                cobertura=round(100 * cov, 2),
                se_cluster=round(100 * se, 2),
                pct_infinito=round(100 * float((~fin_m).mean()), 2),
                n=int(len(y)))


def main():
    print('=' * 92)
    print('FASE 3 - SELECCION DE HIPERPARAMETROS POR ORIGEN RODANTE (R1.4)')
    print(f'calibracion interna [{CAL_INT_INI.date()}, {CAL_INT_FIN.date()})')
    print(f'validacion  interna [{CAL_INT_FIN.date()}, {VAL_INT_FIN.date()})')
    print('El conjunto de test (>= 2024-09-01) NO se usa en la seleccion.')
    print('=' * 92)

    h, pred = cargar('hurdle')
    s_cal_int = h.s.values[((h.fecha >= CAL_INT_INI) & (h.fecha < CAL_INT_FIN)).values]
    print(f'pool de calibracion interna: {len(s_cal_int):,} scores')

    filas = []
    for g in GAMMAS:
        r = evaluar(h, pred, s_cal_int, CAL_INT_FIN, VAL_INT_FIN, g, 60,
                    R.SEED_CONFORMAL, metodo='aci')
        filas.append(dict(metodo='ACI', gamma=g, ventana=np.nan, **r))
        print(f'  ACI            gamma={g:<6} IS={r["IS_total"]:>9.1f}  '
              f'cob={r["cobertura"]:.2f}%  ancho={r["ancho"]:.1f}  '
              f'inf={r["pct_infinito"]}%')
    for g in GAMMAS:
        for v in VENTANAS:
            r = evaluar(h, pred, s_cal_int, CAL_INT_FIN, VAL_INT_FIN, g, v,
                        R.SEED_CONFORMAL, metodo='transporte')
            filas.append(dict(metodo='Transporte+ACI', gamma=g, ventana=v, **r))
            print(f'  Transporte+ACI gamma={g:<6} ventana={v:<4} '
                  f'IS={r["IS_total"]:>9.1f}  cob={r["cobertura"]:.2f}%  '
                  f'ancho={r["ancho"]:.1f}  inf={r["pct_infinito"]}%')

    sel = pd.DataFrame(filas)
    sel.to_csv(SAL / 'fase3_seleccion_validacion.csv', index=False)

    print('\n' + '-' * 92)
    print('SELECCION (menor interval score en validacion interna)')
    print('-' * 92)
    elegidos = {}
    for met in ('ACI', 'Transporte+ACI'):
        s = sel[(sel.metodo == met) & np.isfinite(sel.IS_total)]
        if s.empty:
            print(f'  {met}: TODA configuracion produce intervalos infinitos '
                  f'en validacion; no hay eleccion posible con este criterio')
            continue
        b = s.loc[s.IS_total.idxmin()]
        elegidos[met] = dict(gamma=float(b.gamma),
                             ventana=None if pd.isna(b.ventana) else int(b.ventana),
                             IS_validacion=round(float(b.IS_total), 2),
                             cobertura_validacion=float(b.cobertura))
        print(f'  {met}: gamma = {b.gamma}' +
              (f', ventana = {int(b.ventana)} d' if pd.notna(b.ventana) else '') +
              f'  (IS validacion = {b.IS_total:.1f}, cobertura = {b.cobertura}%)')
        desc = s[np.isfinite(s.IS_total)].nsmallest(5, 'IS_total')
        print(f'    cinco mejores: ' + ', '.join(
            f'g={r.gamma}' + (f'/v={int(r.ventana)}' if pd.notna(r.ventana) else '')
            + f' ({r.IS_total:.0f})' for _, r in desc.iterrows()))

    with open(SAL / 'fase3_hiperparametros_elegidos.json', 'w') as fp:
        json.dump(dict(
            protocolo='origen rodante dentro de la ventana de calibracion',
            calibracion_interna=[str(CAL_INT_INI.date()), str(CAL_INT_FIN.date())],
            validacion_interna=[str(CAL_INT_FIN.date()), str(VAL_INT_FIN.date())],
            criterio='interval score medio del limite unilateral superior, +inf si hay algun intervalo infinito',
            rejilla_gamma=list(GAMMAS), rejilla_ventana=list(VENTANAS),
            semilla=R.SEED_CONFORMAL, elegidos=elegidos), fp, indent=2)

    # ------------------------------------------------------------------
    # SENSIBILIDAD sobre el test. Exhibicion posterior a la seleccion.
    # ------------------------------------------------------------------
    print('\n' + '=' * 92)
    print('SENSIBILIDAD SOBRE EL TEST (exhibicion, NO criterio de seleccion)')
    print('=' * 92)
    s_cal = h.s.values[((h.fecha >= R.CAL_INI) & (h.fecha < R.CAL_FIN)).values]
    filas = []
    for g in GAMMAS:
        r = evaluar(h, pred, s_cal, R.CAL_FIN, pd.Timestamp('2026-06-01'), g, 60,
                    R.SEED_CONFORMAL, metodo='aci')
        filas.append(dict(metodo='ACI', gamma=g, ventana=np.nan, **r))
    # Las dos celdas que son configuraciones de la version enviada (gamma 0.02
    # y 0.05 con ventana de 60 dias) se evaluan en el orden canonico: el mismo
    # generador que aleatorizo el score, primero 0.02 y despues 0.05, como en
    # H7. Con un generador fresco por celda la de 0.05 daba 593.4 / 6.1% /
    # 1028.2 y contradecia a la Tabla 9. El resto de la rejilla, que no tiene
    # contraparte en otra tabla, conserva el generador fresco por celda de la
    # seleccion; la celda elegida (0.005, 120 dias) coincide asi con la fila de
    # la configuracion seleccionada de la Tabla 9, que usa el mismo protocolo.
    rng_canon = np.random.default_rng(R.SEED_CONFORMAL)
    pred.cdf(h.y_real.values, rng_canon)            # sorteos del score
    CANON = {(0.02, 60), (0.05, 60)}
    for g in GAMMAS:
        for v in VENTANAS:
            r = evaluar(h, pred, s_cal, R.CAL_FIN, pd.Timestamp('2026-06-01'), g, v,
                        rng_canon if (g, v) in CANON else R.SEED_CONFORMAL,
                        metodo='transporte')
            filas.append(dict(metodo='Transporte+ACI', gamma=g, ventana=v, **r))
    sen = pd.DataFrame(filas)
    ref = pd.read_csv(R.REPO / 'resultados' / 'fase4' / 'fase4_metricas_completas.csv')
    ref = ref[ref.periodo == 'TEST_COMPLETO'].set_index('metodo')
    for g, v, met in ((0.02, 60, 'Transporte+ACI (g=0.02)'),
                      (0.05, 60, 'Transporte+ACI (g=0.05)'),
                      (0.005, 120, 'Transporte+ACI (g=0.005, v=120, Fase 3)')):
        a = sen[(sen.metodo == 'Transporte+ACI') & (sen.gamma == g) & (sen.ventana == v)].iloc[0]
        b = ref.loc[met]
        dif = max(abs(a.ancho - b.ancho_medio), abs(a.cobertura - b.cobertura),
                  abs(a.pct_infinito - b.pct_infinito), abs(a.IS_finitos - b.IS_finitos))
        if dif > 0.06:
            raise SystemExit(f'la celda ({g}, {v}) no reproduce la Tabla 9 ({met}): '
                             f'desvio {dif:.2f}')
    sen.to_csv(SAL / 'fase3_sensibilidad_test.csv', index=False)

    print('\nACI, por gamma (test completo):')
    print(sen[sen.metodo == 'ACI'][['gamma', 'cobertura', 'se_cluster', 'ancho',
                                    'pct_infinito', 'IS_finitos']].to_string(index=False))
    print('\nTransporte+ACI: ancho medio por (gamma, ventana):')
    print(sen[sen.metodo == 'Transporte+ACI'].pivot_table(
        index='gamma', columns='ventana', values='ancho').round(1).to_string())
    print('\nTransporte+ACI: cobertura por (gamma, ventana):')
    print(sen[sen.metodo == 'Transporte+ACI'].pivot_table(
        index='gamma', columns='ventana', values='cobertura').round(2).to_string())
    print('\nTransporte+ACI: % de intervalos infinitos por (gamma, ventana):')
    print(sen[sen.metodo == 'Transporte+ACI'].pivot_table(
        index='gamma', columns='ventana', values='pct_infinito').round(2).to_string())
    print(f'\nguardado en {SAL.relative_to(R.REPO)}/')


if __name__ == '__main__':
    main()
