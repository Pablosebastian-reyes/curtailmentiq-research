#!/usr/bin/env python3
"""
FASE 2: ablaciones de los componentes de Transporte+ACI.
========================================================
Comentario R1.3. Grupos minimos pedidos: ACI puro, Transporte+ACI sin
shrinkage de cola, Transporte+ACI completo. Se anaden dos grupos para cerrar el
factorial y poder atribuir el aporte de cada pieza sin ambiguedad:

  A0  Split estatico PIT                       (sin adaptacion, referencia)
  A1  ACI puro                                 (adaptacion sin transporte)
  A2  Transporte solo, sin ACI                 (transporte sin control de
                                                cobertura; el manuscrito afirma
                                                que el mapa rompe la
                                                intercambiabilidad y que por eso
                                                hace falta el ACI: A2 mide eso)
  A3  Transporte+ACI SIN shrinkage de cola     (mapa puntual)
  A4  Transporte+ACI completo                  (metodo del paper)

Cada grupo se corre para gamma en {0.02, 0.05} donde aplica, con todo lo demas
identico: ventana reciente de 60 dias, refresco de 7 dias, embargo de 7 dias,
tau = 0.05, B = 150, semilla 20260720.

Se reporta ademas el COSTO COMPUTACIONAL de cada grupo, que es la segunda mitad
del encargo del revisor: si una pieza aporta poco y cuesta mucho, hay que
decirlo.

Salidas:
  resultados/fase2/fase2_ablaciones.csv
  resultados/fase2/fase2_aporte_por_componente.csv

Comando:
  <venv>/bin/python flagship/revision/fase2_ablaciones.py
"""
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rev_lib as R   # noqa: E402

SAL = R.REPO / 'resultados' / 'fase2'
SAL.mkdir(parents=True, exist_ok=True)
FIN_TEST = pd.Timestamp('2026-06-01')


def transporte_sin_aci(pred_test, s_cal, s_todo, fechas_todo, f_t, fechas_test,
                       rng, ventana_dias=60, refresco_dias=7,
                       embargo=R.EMBARGO_DIAS, alpha=R.ALPHA, ini_test=None):
    """A2: transporta el pool y conformaliza al alpha FIJO, sin actualizacion
    online. Aisla el aporte del mapa de transporte."""
    ini_test = pd.Timestamp(fechas_test[0]) if ini_test is None else pd.Timestamp(ini_test)
    U = np.empty(len(pred_test))
    pool = np.sort(s_cal)
    prox = ini_test
    for f in fechas_test:
        f_ts = pd.Timestamp(f)
        if f_ts >= prox:
            ini = np.datetime64((f_ts - pd.Timedelta(days=ventana_dias + embargo)).date())
            fin = np.datetime64((f_ts - pd.Timedelta(days=embargo)).date())
            s_new = s_todo[(fechas_todo >= ini) & (fechas_todo < fin)]
            if len(s_new) >= 100:
                T, _ = R.cm.mapa_transporte_banda(s_cal, s_new, rng)
                pool = np.sort(T(s_cal))
            prox = f_ts + pd.Timedelta(days=refresco_dias)
        m = f_t == f
        U[m] = pred_test.sub(m).inv(R.cm.q_desde_pool(pool, alpha))
    return U


def main():
    print('=' * 96)
    print('FASE 2 - ABLACIONES (comentario R1.3)')
    print('=' * 96)
    hu = pd.read_csv(R.FLAGSHIP / 'predicciones' / 'pred_hurdle.csv',
                     parse_dates=['fecha']).sort_values(
                         ['fecha', 'central_codigo']).reset_index(drop=True)
    pred = R.PredictivaHurdle(hu.p_occ.values, hu.mu_log.values,
                              float(hu.sigma.iloc[0]))
    rng = np.random.default_rng(R.SEED_CONFORMAL)
    hu = hu.assign(s=pred.cdf(hu.y_real.values, rng))
    s_cal = hu.s.values[((hu.fecha >= R.CAL_INI) & (hu.fecha < R.CAL_FIN)).values]
    idx = ((hu.fecha >= R.CAL_FIN) & (hu.fecha < FIN_TEST)).values
    test = hu[idx].reset_index(drop=True)
    p_t = pred.sub(idx)
    y_t, f_t = test.y_real.values, test.fecha.values
    fechas_test = np.sort(test.fecha.unique())

    filas, series, costo = [], {}, {}

    def registrar(nombre, grupo, U, seg, gamma=np.nan):
        series[nombre] = U
        costo[nombre] = seg
        for fila in (R.filas_por_periodo(nombre, f_t, y_t, U)
                     + [R.resumen_metrico(nombre, 'TEST_COMPLETO', f_t, y_t, U)]):
            fila.update(grupo=grupo, gamma=gamma, segundos=round(seg, 2))
            filas.append(fila)

    t0 = time.perf_counter()
    U = R.estatico(p_t, s_cal)
    registrar('A0 split estatico', 'A0', U, time.perf_counter() - t0)
    print('A0 split estatico: listo')

    for g in (0.02, 0.05):
        t0 = time.perf_counter()
        U, _, _ = R.aci(p_t, s_cal, y_t, f_t, fechas_test, g)
        registrar(f'A1 ACI puro (g={g})', 'A1', U, time.perf_counter() - t0, g)
        print(f'A1 ACI puro g={g}: listo')

    t0 = time.perf_counter()
    U = transporte_sin_aci(p_t, s_cal, hu.s.values, hu.fecha.values, f_t,
                           fechas_test, np.random.default_rng(R.SEED_CONFORMAL),
                           ini_test=R.CAL_FIN)
    registrar('A2 transporte sin ACI', 'A2', U, time.perf_counter() - t0)
    print('A2 transporte sin ACI: listo')

    for g in (0.02, 0.05):
        t0 = time.perf_counter()
        U, _, _ = R.transporte_aci(p_t, s_cal, hu.s.values, hu.fecha.values,
                                   y_t, f_t, fechas_test, g,
                                   np.random.default_rng(R.SEED_CONFORMAL),
                                   shrinkage=False, ini_test=R.CAL_FIN)
        registrar(f'A3 Transporte+ACI sin shrinkage (g={g})', 'A3', U,
                  time.perf_counter() - t0, g)
        print(f'A3 sin shrinkage g={g}: listo')

    # A4 es el metodo del manuscrito, asi que tiene que ser EL MISMO objeto que
    # producen conformal_v3_real.py y fase0_model_agnostic.py, no una corrida
    # parecida. Eso exige consumir el generador en el orden canonico: primero la
    # aleatorizacion del atomo sobre todas las filas, luego g=0.02 y luego
    # g=0.05 sobre el mismo generador. Creando uno fresco por gamma, como hacia
    # antes, el mapa de transporte salia de un bootstrap distinto y el ancho del
    # test completo daba 593.4 en vez de los 595.9 de la corrida oficial.
    rng_canon = np.random.default_rng(R.SEED_CONFORMAL)
    pred.cdf(hu.y_real.values, rng_canon)   # consume los mismos sorteos del score
    for g in (0.02, 0.05):
        t0 = time.perf_counter()
        U, _, _ = R.transporte_aci(p_t, s_cal, hu.s.values, hu.fecha.values,
                                   y_t, f_t, fechas_test, g, rng_canon,
                                   shrinkage=True, ini_test=R.CAL_FIN)
        registrar(f'A4 Transporte+ACI completo (g={g})', 'A4', U,
                  time.perf_counter() - t0, g)
        print(f'A4 completo g={g}: listo')

    tab = pd.DataFrame(filas)
    tab.to_csv(SAL / 'fase2_ablaciones.csv', index=False)

    for per in ('test_transition', 'TEST_COMPLETO'):
        print('\n' + '=' * 96)
        print(f'ABLACIONES - {per}')
        print('=' * 96)
        s = tab[tab.periodo == per]
        print(s[['grupo', 'metodo', 'cobertura', 'se_cluster', 'ancho_medio',
                 'pct_infinito', 'IS_finitos', 'IS_total',
                 'segundos']].to_string(index=False))

    # ------------------------------------------------------------------
    # Aporte marginal de cada componente, con incertidumbre
    # ------------------------------------------------------------------
    print('\n' + '=' * 96)
    print('APORTE MARGINAL DE CADA COMPONENTE, sobre el interval score')
    print('bootstrap de 2000 remuestreos de dias completos, IC de percentil 95%')
    print('negativo = el componente mejora; positivo = el componente empeora')
    print('=' * 96)
    contrastes = [
        ('adaptacion online (A1 - A0)', 'A1 ACI puro (g=0.05)', 'A0 split estatico'),
        ('transporte sin ACI (A2 - A0)', 'A2 transporte sin ACI', 'A0 split estatico'),
        ('transporte sobre ACI (A3 - A1)', 'A3 Transporte+ACI sin shrinkage (g=0.05)',
         'A1 ACI puro (g=0.05)'),
        ('shrinkage de cola (A4 - A3)', 'A4 Transporte+ACI completo (g=0.05)',
         'A3 Transporte+ACI sin shrinkage (g=0.05)'),
        ('pipeline completo (A4 - A0)', 'A4 Transporte+ACI completo (g=0.05)',
         'A0 split estatico'),
    ]
    out = []
    for etq, a, b in contrastes:
        for per, ini, fin in R.PERIODOS + [('TEST_COMPLETO', R.CAL_FIN, FIN_TEST)]:
            m = ((f_t >= np.datetime64(pd.Timestamp(ini).date()))
                 & (f_t < np.datetime64(pd.Timestamp(fin).date())))
            if m.sum() == 0:
                continue
            ia = R.interval_score_unilateral(y_t[m], series[a][m])
            ib = R.interval_score_unilateral(y_t[m], series[b][m])
            fi = np.isfinite(ia) & np.isfinite(ib)
            d, lo, hi = R.bootstrap_diferencia(f_t[m][fi], ia[fi], ib[fi])
            ca = (y_t[m] <= series[a][m]).astype(float)
            cb = (y_t[m] <= series[b][m]).astype(float)
            dc, lc, hc = R.bootstrap_diferencia(f_t[m], ca, cb)
            out.append(dict(componente=etq, periodo=per, d_IS=round(d, 1),
                            IS_lo=round(lo, 1), IS_hi=round(hi, 1),
                            significativo='si' if lo * hi > 0 else 'no',
                            d_cob_pp=round(100 * dc, 2),
                            d_segundos=round(costo[a] - costo[b], 1)))
    ap = pd.DataFrame(out)
    ap.to_csv(SAL / 'fase2_aporte_por_componente.csv', index=False)
    for etq, _, _ in contrastes:
        print('\n' + etq)
        print(ap[ap.componente == etq][
            ['periodo', 'd_IS', 'IS_lo', 'IS_hi', 'significativo', 'd_cob_pp',
             'd_segundos']].to_string(index=False))
    print(f'\nguardado en {SAL.relative_to(R.REPO)}/')


if __name__ == '__main__':
    main()
