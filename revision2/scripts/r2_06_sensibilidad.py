#!/usr/bin/env python3
"""
R2-06. Analisis de sensibilidad completo (Apendice E).
=====================================================
Pregunta 2 del Revisor 2: "provide more details and appendix for sensitivity
analysis for the parameters used in details".

Configuracion de referencia (la del paper con la cota recomendada):
  Transport+ACI gamma 0.05, ventana 60 d, refresco 7 d, B 150, tau 0.05,
  rejilla del mapa 100, minimo de scores recientes 100, alpha_min 0.005,
  embargo 7 d (fijado por el horizonte, no es un parametro libre).
Se varia UN parametro a la vez y se reporta el test completo. Modelos base:
hurdle con detencion temprana y GBM multi-cuantil (los dos de referencia de
la R2); el hurdle del paper se agrega donde la R1 ya tenia una tabla.

Bloques
  E1 capa de transporte: tau, B, rejilla, refresco, minimo de scores, ventana
  E2 capa adaptativa: gamma, alpha_min
  E3 nivel nominal: 1-alpha en {0.80, 0.90, 0.95, 0.99}
  E4 ventana de calibracion: 8, 6 y 4 meses (todas terminan el 2024-08-31)
  E5 semillas de la capa conformal: 10 semillas (atomo PIT y bootstrap del mapa)
  E6 densidad de la rejilla del GBM: 54, 27 y 14 niveles (submuestreo)
  E7 umbral de dia alto: P75, P90 y P95 de la ventana de calibracion
  E8 modelo base: hiperparametros del hurdle con detencion temprana
     (profundidad 4/6/8, tasa 0.03/0.05/0.10) y 10 semillas de entrenamiento

Salida: resultados/r2_06_sensibilidad.csv (formato largo)
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_lib as L                      # noqa: E402
import numpy as np                      # noqa: E402
import pandas as pd                     # noqa: E402
R, cm = L.R, L.cm

LOG = 'r2_06_sensibilidad.log'
REF = dict(gamma=0.05, ventana_dias=60, refresco_dias=7, B=150, tau=0.05, n_grid=100,
           min_recientes=100, alpha_min=0.005)
BRAZOS = ('hurdle_es', 'qgbm_54x400')
filas = []


def registrar(bloque, brazo, parametro, valor, metodo, c, U, alpha=L.ALPHA, extra=None):
    r = R.resumen_metrico(metodo, 'TEST_COMPLETO', c['f_t'], c['y_t'], U, alpha)
    tr = L.mascara(c['f_t'], '2024-10-01', '2025-01-01')
    rt = R.resumen_metrico(metodo, 'test_transition', c['f_t'][tr], c['y_t'][tr], U[tr], alpha)
    fila = dict(bloque=bloque, brazo=brazo, parametro=parametro, valor=str(valor), metodo=metodo,
                alpha=alpha, cobertura=r['cobertura'], se=r['se_cluster'], ancho=r['ancho_medio'],
                pct_inf=r['pct_infinito'], IS_finitos=r['IS_finitos'], IS_total=r['IS_total'],
                cob_transicion=rt['cobertura'], ancho_transicion=rt['ancho_medio'],
                IS_transicion=rt['IS_finitos'])
    if extra:
        fila.update(extra)
    filas.append(fila)


def tr(c, rng=None, **kw):
    p = dict(REF)
    p.update(kw)
    rng = np.random.default_rng(R.SEED_CONFORMAL) if rng is None else rng
    return L.transporte_aci_ext(c['p_t'], c['s_cal'], c['h'].s.values, c['h'].fecha.values,
                                c['y_t'], c['f_t'], c['fechas_test'], p.pop('gamma'), rng,
                                ini_test=R.CAL_FIN, **p)


def main():
    t00 = time.perf_counter()
    # ---- control: la version extendida reproduce rev_lib a los valores por defecto
    c = L.contexto('hurdle_800')
    a = R.transporte_aci(c['p_t'], c['s_cal'], c['h'].s.values, c['h'].fecha.values, c['y_t'],
                         c['f_t'], c['fechas_test'], 0.05, np.random.default_rng(R.SEED_CONFORMAL),
                         alpha_min=0.005, ini_test=R.CAL_FIN)[0]
    b = tr(c)
    assert np.allclose(a, b, equal_nan=True), 'transporte_aci_ext no reproduce rev_lib'
    L.log('[OK] transporte_aci_ext == rev_lib.transporte_aci en la configuracion de referencia', LOG)

    for brazo in BRAZOS:
        c = L.contexto(brazo)
        # referencia
        registrar('ref', brazo, 'reference', 'ref', 'Transport+ACI', c, tr(c))
        # E1
        for v in (0.01, 0.025, 0.10, 0.25, np.inf):
            registrar('E1', brazo, 'tau', v, 'Transport+ACI', c, tr(c, tau=v))
        for v in (25, 50, 300):
            registrar('E1', brazo, 'B', v, 'Transport+ACI', c, tr(c, B=v))
        for v in (25, 50, 200):
            registrar('E1', brazo, 'n_grid', v, 'Transport+ACI', c, tr(c, n_grid=v))
        for v in (1, 14, 28):
            registrar('E1', brazo, 'refresh_days', v, 'Transport+ACI', c, tr(c, refresco_dias=v))
        for v in (50, 500, 2000):
            registrar('E1', brazo, 'min_recent_scores', v, 'Transport+ACI', c, tr(c, min_recientes=v))
        for v in (30, 45, 90, 120):
            registrar('E1', brazo, 'window_days', v, 'Transport+ACI', c, tr(c, ventana_dias=v))
        registrar('E1', brazo, 'transport_without_ACI', 'gamma=0', 'Transport (fixed alpha)', c,
                  tr(c, adaptar=False))
        L.log(f'{brazo}: E1 listo', LOG)
        # E2
        for v in (0.005, 0.01, 0.02, 0.10, 0.20):
            registrar('E2', brazo, 'gamma', v, 'Transport+ACI', c, tr(c, gamma=v))
            registrar('E2', brazo, 'gamma', v, 'ACI', c,
                      R.aci(c['p_t'], c['s_cal'], c['y_t'], c['f_t'], c['fechas_test'], v,
                            alpha_min=0.005)[0])
        registrar('E2', brazo, 'gamma', 0.05, 'ACI', c,
                  R.aci(c['p_t'], c['s_cal'], c['y_t'], c['f_t'], c['fechas_test'], 0.05,
                        alpha_min=0.005)[0])
        for v in (None, 0.001, 0.01, 0.02):
            registrar('E2', brazo, 'alpha_min', 'none' if v is None else v, 'Transport+ACI', c,
                      tr(c, alpha_min=v))
        L.log(f'{brazo}: E2 listo', LOG)
        # E3 nivel nominal
        for a in (0.20, 0.10, 0.05, 0.01):
            amin = a / 20
            registrar('E3', brazo, 'nominal_level', 1 - a, 'Static split', c,
                      R.estatico(c['p_t'], c['s_cal'], a), alpha=a)
            registrar('E3', brazo, 'nominal_level', 1 - a, 'ACI', c,
                      R.aci(c['p_t'], c['s_cal'], c['y_t'], c['f_t'], c['fechas_test'], 0.05,
                            alpha=a, alpha_min=amin)[0], alpha=a)
            registrar('E3', brazo, 'nominal_level', 1 - a, 'Transport+ACI', c,
                      tr(c, alpha=a, alpha_min=amin), alpha=a)
            registrar('E3', brazo, 'nominal_level', 1 - a, 'One-sided CQR', c,
                      L.cqr_unilateral(c['pred'], c['h'], c['cal'], c['idx'], a)[0], alpha=a)
        L.log(f'{brazo}: E3 listo', LOG)
        # E4 ventana de calibracion
        h = c['h']
        for ini, etq in ((pd.Timestamp('2024-01-01'), '8 months (Jan-Aug)'),
                         (pd.Timestamp('2024-03-01'), '6 months (Mar-Aug)'),
                         (pd.Timestamp('2024-05-01'), '4 months (May-Aug)')):
            calm = ((h.fecha >= ini) & (h.fecha < R.CAL_FIN)).values
            s_cal = h.s.values[calm]
            c2 = dict(c, s_cal=s_cal, cal=calm)
            registrar('E4', brazo, 'calibration_window', etq, 'Static split', c2,
                      R.estatico(c['p_t'], s_cal), extra=dict(n_cal=int(calm.sum())))
            registrar('E4', brazo, 'calibration_window', etq, 'Transport+ACI', c2, tr(c2),
                      extra=dict(n_cal=int(calm.sum())))
            registrar('E4', brazo, 'calibration_window', etq, 'One-sided CQR', c2,
                      L.cqr_unilateral(c['pred'], h, calm, c['idx'])[0],
                      extra=dict(n_cal=int(calm.sum())))
        L.log(f'{brazo}: E4 listo', LOG)
        # E5 semillas de la capa conformal
        for sd in range(10):
            seed = 1000 + sd
            rng = np.random.default_rng(seed)
            s = c['pred'].cdf(h.y_real.values, rng)
            calm = c['cal']
            c3 = dict(c, s_cal=s[calm], h=h.assign(s=s))
            registrar('E5', brazo, 'conformal_seed', seed, 'Static split', c3, R.estatico(c['p_t'], s[calm]))
            registrar('E5', brazo, 'conformal_seed', seed, 'Transport+ACI', c3, tr(c3, rng=rng))
        L.log(f'{brazo}: E5 listo', LOG)

    # E6 densidad de la rejilla del GBM (submuestreo de los 54 niveles)
    c = L.contexto('qgbm_54x400')
    pred = c['pred']
    taus = pred.taus
    sub27 = np.unique(np.concatenate([taus[::2], [0.9, 0.95, 0.99, 0.999]]))
    sub14 = np.unique(np.concatenate([taus[::4], [0.9, 0.95, 0.99, 0.999]]))
    for etq, tt in (('54 levels', taus), ('27 levels', sub27), ('14 levels', sub14)):
        k = np.isin(taus, tt)
        pq = R.PredictivaCuantilica(pred.Q[:, k], taus[k])
        rng = np.random.default_rng(R.SEED_CONFORMAL)
        s = pq.cdf(c['h'].y_real.values, rng)
        c4 = dict(c, pred=pq, p_t=pq.sub(c['idx']), s_cal=s[c['cal']], h=c['h'].assign(s=s))
        registrar('E6', 'qgbm_54x400', 'quantile_grid', etq, 'Static split', c4, R.estatico(c4['p_t'], c4['s_cal']))
        registrar('E6', 'qgbm_54x400', 'quantile_grid', etq, 'Transport+ACI', c4, tr(c4, rng=rng))
        registrar('E6', 'qgbm_54x400', 'quantile_grid', etq, 'One-sided CQR', c4,
                  L.cqr_unilateral(pq, c['h'], c['cal'], c['idx'])[0])
    L.log('E6 listo', LOG)

    # E8 modelo base: hiperparametros y semillas del hurdle con detencion temprana
    import obj1_capacidad_contra_forma as O1
    import obj1d_hurdle_deteccion_temprana as O1D
    import entrenar_baselines as EB
    df_tr, df_pr = O1.panel()
    orden = df_pr[['fecha', 'central_codigo']].sort_values(['fecha', 'central_codigo']).index.values
    base = dict(EB.XGB_PARAMS)
    variantes = [('max_depth', v) for v in (4, 8)] + [('learning_rate', v) for v in (0.03, 0.10)] + \
                [('random_state', v) for v in range(1, 11)]
    for par, v in variantes:
        EB.XGB_PARAMS = dict(base, **{par: v})
        try:
            pred, arb, sg, el = O1D.entrenar_con_es(df_tr, df_pr)
        finally:
            EB.XGB_PARAMS = base
        pred = pred.sub(orden)
        hh = L.panel_filas()
        rng = np.random.default_rng(R.SEED_CONFORMAL)
        s = pred.cdf(hh.y_real.values, rng)
        cal = ((hh.fecha >= R.CAL_INI) & (hh.fecha < R.CAL_FIN)).values
        idx = ((hh.fecha >= R.CAL_FIN) & (hh.fecha < L.FIN_TEST)).values
        test = hh[idx].reset_index(drop=True)
        c5 = dict(h=hh.assign(s=s), pred=pred, s_cal=s[cal], cal=cal, idx=idx, p_t=pred.sub(idx),
                  y_t=test.y_real.values, f_t=test.fecha.values,
                  fechas_test=np.sort(test.fecha.unique()))
        crps = R.crps_pred(c5['p_t'], c5['y_t'], np.random.default_rng(R.SEED_CRPS))
        ex = dict(arboles=arb, sigma=sg, crps_test=crps)
        registrar('E8', 'hurdle_es', par, v, 'Static split', c5, R.estatico(c5['p_t'], c5['s_cal']), extra=ex)
        registrar('E8', 'hurdle_es', par, v, 'Transport+ACI', c5, tr(c5, rng=rng), extra=ex)
        registrar('E8', 'hurdle_es', par, v, 'One-sided CQR', c5,
                  L.cqr_unilateral(pred, c5['h'], cal, idx)[0], extra=ex)
        L.log(f'E8 {par}={v}: {arb} arboles, CRPS {crps:.2f}', LOG)

    # E7 umbral de dia alto (cobertura en dias altos de los metodos principales)
    h = L.panel_filas()
    tot = h.groupby('fecha').y_real.sum()
    tot_cal = tot[(tot.index >= R.CAL_INI) & (tot.index < R.CAL_FIN)]
    for brazo in ('hurdle_800', 'hurdle_es', 'qgbm_54x400'):
        fpq = L.SERIES_DIR / f'{brazo}.parquet'
        while not (L.RES / 'r2_02_metricas.csv').exists():
            time.sleep(30)          # espera a que r2_02 termine de escribir todas las series
        S = pd.read_parquet(L.SERIES_DIR / f'{brazo}.parquet')
        for qq in (0.75, 0.90, 0.95):
            u = float(tot_cal.quantile(qq))
            altos = set(tot.index[tot >= u])
            m = S.fecha.isin(altos).values
            for met in ('static', 'tr_sel', 'tr_g05', 'cqr'):
                if met not in S:
                    continue
                cov, se, nd = cm.cobertura_clusterizada(S.fecha.values[m], S.y.values[m] <= S[met].values[m])
                filas.append(dict(bloque='E7', brazo=brazo, parametro='high_day_threshold',
                                  valor=f'P{int(qq * 100)}', metodo=met, alpha=0.1,
                                  cobertura=round(100 * cov, 1), se=round(100 * se, 2),
                                  dias_altos=int(nd)))
    L.log('E7 listo', LOG)

    T = pd.DataFrame(filas)
    T.to_csv(L.RES / 'r2_06_sensibilidad.csv', index=False)
    L.log(f'sensibilidad lista ({time.perf_counter() - t00:.0f} s)', LOG)


if __name__ == '__main__':
    main()
