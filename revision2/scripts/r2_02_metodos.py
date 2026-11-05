#!/usr/bin/env python3
"""
R2-02. Todos los metodos de calibracion sobre los nueve modelos base.
====================================================================
Responde al comentario 2 del Revisor 2 (repetir static, ACI, Transport+ACI y
CQR con el hurdle con detencion temprana) y produce las series por fila que
usan el diagnostico (r2_03) y las metricas operacionales (r2_04).

Por cada modelo base:
  A. Seleccion de gamma y ventana por ORIGEN RODANTE dentro de la ventana de
     calibracion (calibracion interna ene-abr 2024, validacion interna may-ago
     2024), criterio interval score unilateral (+inf si hay algun intervalo
     infinito). Mismo protocolo que la Fase 3 de la R1; para el hurdle del
     paper se exige reproducir su resultado (ACI 0.005; T+ACI 0.005 / 120 d).
  B. Metodos sobre el test (2024-09-01 .. 2026-05-31), con el generador en el
     orden canonico de la R1 donde corresponde:
       static, sw60, aci_g02, aci_g05, tr_g02, tr_g05   (version R1)
       aci_g05_amin005, tr_g05_amin005 (+ 0.01, 0.02)   (cota de alpha)
       aci_sel, tr_sel                                  (seleccion propia)
       ab_tr_fijo, ab_tr_sinshrink_g05                  (ablaciones)
       cqr                                              (CQR sobre la propia predictiva)
       static_a05, static_a01, cqr_a05, cqr_a01,
       aci_sel_a05, aci_sel_a01                         (cola: 95% y 99%)
  C. Metricas por ventana y test completo; CRPS, CRPS ponderado por umbral
     (twCRPS) y Brier de la predictiva base.

Salidas (resultados/):
  series/<brazo>.parquet          U por fila del test, una columna por metodo
  r2_02_seleccion.csv / .json     seleccion por origen rodante, por brazo
  r2_02_metricas.csv              metricas por brazo x metodo x ventana
  r2_02_base.csv                  CRPS, twCRPS, Brier por brazo x ventana
  r2_02_tiempos.csv               segundos por componente (ablaciones)
"""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_lib as L                      # noqa: E402
import numpy as np                      # noqa: E402
import pandas as pd                     # noqa: E402
R, cm = L.R, L.cm

LOG = 'r2_02_metodos.log'
CAL_INT_INI = pd.Timestamp('2024-01-01')
CAL_INT_FIN = pd.Timestamp('2024-05-01')
VAL_INT_FIN = pd.Timestamp('2024-09-01')
GAMMAS = (0.005, 0.01, 0.02, 0.05, 0.10, 0.20)
VENTANAS = (30, 45, 60, 90, 120)


# --------------------------------------------------------------------------
# A. Seleccion por origen rodante (copia del protocolo de fase3)
# --------------------------------------------------------------------------
def evaluar_val(c, s_cal_int, gamma, ventana, metodo):
    h, pred = c['h'], c['pred']
    idx = ((h.fecha >= CAL_INT_FIN) & (h.fecha < VAL_INT_FIN)).values
    sub = h[idx].reset_index(drop=True)
    p_sub = pred.sub(idx)
    y, f = sub.y_real.values, sub.fecha.values
    fechas = np.sort(sub.fecha.unique())
    if metodo == 'aci':
        U, _, _ = R.aci(p_sub, s_cal_int, y, f, fechas, gamma)
    else:
        U, _, _ = R.transporte_aci(p_sub, s_cal_int, h.s.values, h.fecha.values, y, f,
                                   fechas, gamma, np.random.default_rng(R.SEED_CONFORMAL),
                                   ventana_dias=ventana, ini_test=CAL_INT_FIN)
    IS = R.interval_score_unilateral(y, U)
    fi = np.isfinite(U)
    cov, se, _ = cm.cobertura_clusterizada(f, y <= U)
    return dict(IS_total=float(np.mean(IS)),
                IS_finitos=float(np.mean(IS[fi])) if fi.any() else np.nan,
                ancho=float(U[fi].mean()) if fi.any() else np.nan,
                cobertura=round(100 * cov, 2), pct_infinito=round(100 * float((~fi).mean()), 2))


def seleccionar(c):
    h = c['h']
    s_cal_int = h.s.values[((h.fecha >= CAL_INT_INI) & (h.fecha < CAL_INT_FIN)).values]
    filas = []
    for g in GAMMAS:
        filas.append(dict(metodo='ACI', gamma=g, ventana=np.nan,
                          **evaluar_val(c, s_cal_int, g, 60, 'aci')))
    for g in GAMMAS:
        for v in VENTANAS:
            filas.append(dict(metodo='Transport+ACI', gamma=g, ventana=v,
                              **evaluar_val(c, s_cal_int, g, v, 'tr')))
    T = pd.DataFrame(filas)
    el = {}
    for met in ('ACI', 'Transport+ACI'):
        s = T[(T.metodo == met) & np.isfinite(T.IS_total)]
        if s.empty:
            el[met] = None
            continue
        b = s.loc[s.IS_total.idxmin()]
        el[met] = dict(gamma=float(b.gamma),
                       ventana=None if pd.isna(b.ventana) else int(b.ventana),
                       IS_validacion=round(float(b.IS_total), 2),
                       cobertura_validacion=float(b.cobertura))
    return T, el


# --------------------------------------------------------------------------
# B. Metodos sobre el test
# --------------------------------------------------------------------------
def transporte_sin_aci(c, rng, ventana_dias=60, refresco_dias=7, alpha=L.ALPHA):
    """Ablacion A2 de la R1: transporte con alpha FIJO, sin ACI."""
    h, p_t, s_cal = c['h'], c['p_t'], c['s_cal']
    f_t, fechas_test = c['f_t'], c['fechas_test']
    s_todo, fechas_todo = h.s.values, h.fecha.values
    U = np.empty(len(p_t))
    pool = np.sort(s_cal)
    prox = R.CAL_FIN
    for f in fechas_test:
        f_ts = pd.Timestamp(f)
        if f_ts >= prox:
            ini = np.datetime64((f_ts - pd.Timedelta(days=ventana_dias + R.EMBARGO_DIAS)).date())
            fin = np.datetime64((f_ts - pd.Timedelta(days=R.EMBARGO_DIAS)).date())
            s_new = s_todo[(fechas_todo >= ini) & (fechas_todo < fin)]
            if len(s_new) >= 100:
                T, _ = cm.mapa_transporte_banda(s_cal, s_new, rng)
                pool = np.sort(T(s_cal))
            prox = f_ts + pd.Timedelta(days=refresco_dias)
        m = f_t == f
        U[m] = p_t.sub(m).inv(cm.q_desde_pool(pool, alpha))
    return U


def correr_brazo(nombre, sel, principal):
    c = L.contexto(nombre)
    h, p_t, s_cal = c['h'], c['p_t'], c['s_cal']
    y_t, f_t, fechas_test = c['y_t'], c['f_t'], c['fechas_test']
    s_todo, fechas_todo = h.s.values, h.fecha.values
    U, seg = {}, {}

    def cron(k, fn):
        t0 = time.perf_counter()
        out = fn()
        seg[k] = time.perf_counter() - t0
        return out

    U['static'] = cron('static', lambda: R.estatico(p_t, s_cal))
    U['sw60'] = cron('sw60', lambda: R.ventana_deslizante(
        p_t, s_todo, fechas_todo, f_t, '2024-09-01', '2026-05-31'))
    for g in (0.02, 0.05):
        k = f'aci_g{str(g)[2:]}'
        U[k] = cron(k, lambda g=g: R.aci(p_t, s_cal, y_t, f_t, fechas_test, g)[0])
    rng = c['rng']                                   # canonico: continua el del score
    for g in (0.02, 0.05):
        k = f'tr_g{str(g)[2:]}'
        U[k] = cron(k, lambda g=g: R.transporte_aci(
            p_t, s_cal, s_todo, fechas_todo, y_t, f_t, fechas_test, g, rng,
            ini_test=R.CAL_FIN)[0])

    # cota de alpha (orden de la R1, Fase 4: generador fresco que consume el score)
    cotas = (0.005, 0.01, 0.02) if principal else (0.005,)
    for amin in cotas:
        rng_t = np.random.default_rng(R.SEED_CONFORMAL)
        c['pred'].cdf(h.y_real.values, rng_t)
        for g in (0.02, 0.05):
            a = R.aci(p_t, s_cal, y_t, f_t, fechas_test, g, alpha_min=amin)[0]
            t = R.transporte_aci(p_t, s_cal, s_todo, fechas_todo, y_t, f_t, fechas_test,
                                 g, rng_t, alpha_min=amin, ini_test=R.CAL_FIN)[0]
            if g == 0.05 or principal:
                tag = str(amin).replace('0.', '')
                U[f'aci_g{str(g)[2:]}_amin{tag}'] = a
                U[f'tr_g{str(g)[2:]}_amin{tag}'] = t

    # configuracion seleccionada por el propio brazo
    if sel.get('ACI'):
        U['aci_sel'] = R.aci(p_t, s_cal, y_t, f_t, fechas_test, sel['ACI']['gamma'])[0]
    if sel.get('Transport+ACI'):
        U['tr_sel'] = R.transporte_aci(
            p_t, s_cal, s_todo, fechas_todo, y_t, f_t, fechas_test,
            sel['Transport+ACI']['gamma'], np.random.default_rng(R.SEED_CONFORMAL),
            ventana_dias=sel['Transport+ACI']['ventana'], ini_test=R.CAL_FIN)[0]

    # ablaciones (R1, Fase 2), solo brazos principales
    if principal:
        U['ab_tr_fijo'] = cron('ab_tr_fijo', lambda: transporte_sin_aci(
            c, np.random.default_rng(R.SEED_CONFORMAL)))
        U['ab_tr_sinshrink_g05'] = cron('ab_tr_sinshrink_g05', lambda: R.transporte_aci(
            p_t, s_cal, s_todo, fechas_todo, y_t, f_t, fechas_test, 0.05,
            np.random.default_rng(R.SEED_CONFORMAL), shrinkage=False,
            ini_test=R.CAL_FIN)[0])

    # CQR sobre la predictiva propia, y niveles de cola
    U['cqr'], q_cqr = L.cqr_unilateral(c['pred'], h, c['cal'], c['idx'], 0.10)
    extra = dict(Q_cqr=q_cqr)
    if principal:
        for a in (0.05, 0.01):
            tag = f'a{str(a)[2:]}'
            U[f'static_{tag}'] = R.estatico(p_t, s_cal, a)
            U[f'cqr_{tag}'], _ = L.cqr_unilateral(c['pred'], h, c['cal'], c['idx'], a)
            if sel.get('ACI'):
                U[f'aci_sel_{tag}'] = R.aci(p_t, s_cal, y_t, f_t, fechas_test,
                                           sel['ACI']['gamma'], alpha=a,
                                           alpha_min=a / 20)[0]
            if sel.get('Transport+ACI'):
                U[f'tr_sel_{tag}'] = R.transporte_aci(
                    p_t, s_cal, s_todo, fechas_todo, y_t, f_t, fechas_test,
                    sel['Transport+ACI']['gamma'], np.random.default_rng(R.SEED_CONFORMAL),
                    alpha=a, alpha_min=a / 20,
                    ventana_dias=sel['Transport+ACI']['ventana'], ini_test=R.CAL_FIN)[0]
    return c, U, seg, extra


NIVEL = {'static_a05': 0.05, 'cqr_a05': 0.05, 'aci_sel_a05': 0.05, 'tr_sel_a05': 0.05,
         'static_a01': 0.01, 'cqr_a01': 0.01, 'aci_sel_a01': 0.01, 'tr_sel_a01': 0.01}


def umbrales_tw(h, cal):
    """Umbral del twCRPS: percentil 90 del vertimiento diario de cada central
    en la ventana de calibracion (con ceros). Centrales con menos de 30 dias de
    calibracion reciben el percentil 90 global de la calibracion."""
    c = h[cal]
    g = c.groupby('central_codigo', observed=True).y_real
    p90 = g.quantile(0.90)
    n = g.size()
    glob = float(c.y_real.quantile(0.90))
    p90 = p90.where(n >= 30, glob)
    return h.central_codigo.map(p90).fillna(glob).values, glob


def main():
    principales = set(L.PRINCIPALES)
    filas_sel, elegidos, filas_m, filas_b, filas_t = [], {}, [], [], []
    for nombre in L.BRAZOS:
        t0 = time.perf_counter()
        c0 = L.contexto(nombre)
        T, el = seleccionar(c0)
        T.insert(0, 'brazo', nombre)
        filas_sel.append(T)
        elegidos[nombre] = el
        L.log(f'{nombre}: seleccion {el}', LOG)
        if nombre == 'hurdle_800':
            assert el['ACI']['gamma'] == 0.005, el
            assert el['Transport+ACI']['gamma'] == 0.005 and el['Transport+ACI']['ventana'] == 120, el
            L.log('  [OK] reproduce la seleccion de la R1 (ACI 0.005; T+ACI 0.005/120)', LOG)

        c, U, seg, extra = correr_brazo(nombre, el, nombre in principales)
        test = c['test']
        df = pd.DataFrame(dict(fecha=c['f_t'], central_codigo=test.central_codigo.values,
                               y=c['y_t']))
        for k, v in U.items():
            df[k] = v
        df.to_parquet(L.SERIES_DIR / f'{nombre}.parquet', index=False)
        for k, s in seg.items():
            filas_t.append(dict(brazo=nombre, componente=k, segundos=round(s, 3)))

        for k, v in U.items():
            a = NIVEL.get(k, L.ALPHA)
            for per, ini, fin in L.PER_TODOS:
                m = L.mascara(c['f_t'], ini, fin)
                r = R.resumen_metrico(k, per, c['f_t'][m], c['y_t'][m], v[m], a)
                r.update(brazo=nombre, alpha=a)
                filas_m.append(r)

        # metricas de la predictiva base
        umb, glob = umbrales_tw(c['h'], c['cal'])
        umb_t = umb[c['idx']]
        rng_seq = np.random.default_rng(R.SEED_CRPS)      # como la Fase 0 (por ventana, secuencial)
        for per, ini, fin in L.PER_TODOS:
            m = L.mascara(c['f_t'], ini, fin)
            sub = c['p_t'].sub(m)
            if per != 'TEST_COMPLETO':
                crps_seq = R.crps_pred(sub, c['y_t'][m], rng_seq)
            else:
                crps_seq = np.nan
            rng_f = np.random.default_rng(R.SEED_CRPS)    # como obj1 (fresco por ventana)
            mu = sub.muestrear(rng_f, n=300)
            crps_f = cm.crps(mu, c['y_t'][m], rng_f)
            tw = L.twcrps_muestras(mu, c['y_t'][m], umb_t[m], np.random.default_rng(R.SEED_CRPS))
            filas_b.append(dict(brazo=nombre, periodo=per, crps_fase0=crps_seq,
                                crps=crps_f, twcrps=tw,
                                brier=R.brier_ocurrencia(sub, c['y_t'][m]),
                                Q_cqr=extra['Q_cqr'], umbral_tw_global=glob))
        L.log(f'{nombre}: {len(U)} metodos, {time.perf_counter() - t0:.0f} s', LOG)

    pd.concat(filas_sel).to_csv(L.RES / 'r2_02_seleccion.csv', index=False)
    json.dump(elegidos, open(L.RES / 'r2_02_seleccion.json', 'w'), indent=1)
    M = pd.DataFrame(filas_m)
    M.to_csv(L.RES / 'r2_02_metricas.csv', index=False)
    B = pd.DataFrame(filas_b)
    B.to_csv(L.RES / 'r2_02_base.csv', index=False)
    pd.DataFrame(filas_t).to_csv(L.RES / 'r2_02_tiempos.csv', index=False)

    # -------------------------------------------------------------- controles
    # 1) el hurdle del paper reproduce la Tabla 3 y la Tabla 9 de la R1
    v3 = pd.read_csv(L.REPO / 'resultados/v_enviada/conformal_v3_tabla.csv')
    v3['periodo'] = v3.periodo.replace(R.NOMBRE_ANTIGUO)
    mapa = {'1_estatico_pit': 'static', '2_ventana60d_pit': 'sw60', '3_aci_pit_g02': 'aci_g02',
            '3_aci_pit_g05': 'aci_g05', '4_transporte_banda_g02': 'tr_g02',
            '4_transporte_banda_g05': 'tr_g05'}
    hu = M[M.brazo == 'hurdle_800']
    dmax = 0.0
    for _, o in v3.iterrows():
        r = hu[(hu.metodo == mapa[o.metodo]) & (hu.periodo == o.periodo)].iloc[0]
        for k in ('cobertura', 'ancho_medio', 'pct_infinito', 'se_cluster'):
            dmax = max(dmax, abs(r[k] - o[k]))
    L.log(f'control Tabla 3 de la R1 (hurdle_800): max |dif| = {dmax}', LOG)
    assert dmax < 1e-9, dmax
    f4 = pd.read_csv(L.REPO / 'resultados/fase4/fase4_metricas_completas.csv')
    f4 = f4[f4.periodo == 'TEST_COMPLETO'].set_index('metodo')
    pares = {'Split estatico (PIT)': 'static', 'ACI (g=0.005, Fase 3)': 'aci_sel',
             'Transporte+ACI (g=0.005, v=120, Fase 3)': 'tr_sel',
             'B3 CQR unilateral (GBM)': None}
    hut = hu[hu.periodo == 'TEST_COMPLETO'].set_index('metodo')
    for k_r1, k_r2 in pares.items():
        if k_r2 is None:
            r = M[(M.brazo == 'qgbm_54x400') & (M.metodo == 'cqr') & (M.periodo == 'TEST_COMPLETO')].iloc[0]
        else:
            r = hut.loc[k_r2]
        o = f4.loc[k_r1]
        d = max(abs(r.cobertura - o.cobertura), abs(r.ancho_medio - o.ancho_medio),
                abs(r.IS_finitos - o.IS_finitos))
        L.log(f'control Tabla 9 R1 {k_r1}: max |dif| = {d:.3f}', LOG)
        # el B3 de la R1 tomaba la columna q0.90 cruda; aqui se toma de la
        # predictiva reordenada (rearrangement), que puede diferir en filas con
        # cruce de cuantiles: tolerancia mayor y declarada
        assert d < (1.0 if k_r2 is None else 0.051), (k_r1, d)
    b = B[(B.brazo == 'hurdle_800')].set_index('periodo')
    L.log(f'CRPS hurdle_800: {b.crps_fase0.round(2).to_dict()} | test {b.crps.round(2).to_dict()}', LOG)
    print('listo')


if __name__ == '__main__':
    main()
