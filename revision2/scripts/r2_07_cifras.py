#!/usr/bin/env python3
"""
R2-07. Cifras del texto, leidas de los archivos de resultados.
=============================================================
Escribe manuscrito/cifras.tex con una macro por cifra que el texto cita como
\\cf{clave}. Ninguna cifra del texto se transcribe a mano: si un resultado
cambia, se regenera este archivo y el PDF cambia con el.

Ademas escribe resultados/r2_07_cifras.csv (clave, valor, definicion) para la
verificacion y para la carta.

Al final verifica que toda clave usada en los .tex del manuscrito y de la carta
este definida, y que no sobre ninguna.
"""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_lib as L                      # noqa: E402
import numpy as np                      # noqa: E402
import pandas as pd                     # noqa: E402

RES = L.RES
MAN = L.R2 / 'manuscrito'
CARTA = L.R2 / 'carta'
C = {}
DEF = {}


def put(k, v, d, definicion):
    if isinstance(v, str):
        s = v
    else:
        s = f'{v:.{d}f}'
        if s.startswith('-'):
            s = '\\ensuremath{-}' + s[1:]
    C[k] = s
    DEF[k] = definicion


def sgn(v, d=1):
    s = f'{v:+.{d}f}'
    return s.replace('-', '\\ensuremath{-}').replace('+', '\\ensuremath{+}')


def main():
    M = pd.read_csv(RES / 'r2_02_metricas.csv')
    B = pd.read_csv(RES / 'r2_02_base.csv')
    D = json.load(open(RES / 'r2_03_resumen.json'))
    CE = pd.read_csv(RES / 'r2_03_celdas.csv')
    INF = pd.read_csv(RES / 'r2_03_inferencia.csv')
    OP = pd.read_csv(RES / 'r2_04_operacional.csv')
    ALT = json.load(open(RES / 'r2_04_dias_altos.json'))
    PRELIM = '--preliminar' in sys.argv
    hay_sim = (RES / 'r2_05_sim_resumen.json').exists()
    hay_se = (RES / 'r2_06_sensibilidad.csv').exists()
    if not PRELIM and not (hay_sim and hay_se):
        raise SystemExit('faltan resultados de simulacion o sensibilidad (usar --preliminar para un borrador)')
    SIM = pd.read_csv(RES / 'r2_05_sim_celdas.csv') if hay_sim else None
    SR = json.load(open(RES / 'r2_05_sim_resumen.json')) if hay_sim else None
    AB = pd.read_csv(RES / 'r2_08_ablaciones.csv')
    SE = pd.read_csv(RES / 'r2_06_sensibilidad.csv') if hay_se else None

    def m(b, met, per='TEST_COMPLETO', campo='IS_finitos', a=0.10):
        r = M[(M.brazo == b) & (M.metodo == met) & (M.periodo == per) & (np.isclose(M.alpha, a))]
        assert len(r) == 1, (b, met, per, a)
        return float(r[campo].iloc[0])

    def op(b, met, sub='all', campo='cobertura', a=0.10):
        r = OP[(OP.base == b) & (OP.metodo == met) & (OP.subconjunto == sub) & np.isclose(OP.alpha, a)]
        assert len(r) == 1, (b, met, sub, a)
        return float(r[campo].iloc[0])

    # ---------------------------------------------------------- referencia
    put('ref_st_tr_cov', m('hurdle_800', 'static', 'test_transition', 'cobertura'), 1, 'cobertura estatica transicion, hurdle ref')
    put('ref_st_tr_w', m('hurdle_800', 'static', 'test_transition', 'ancho_medio'), 0, 'ancho estatico transicion, hurdle ref')
    put('ref_tr_tr_w', m('hurdle_800', 'tr_g05', 'test_transition', 'ancho_medio'), 0, 'ancho T+ACI 0.05 transicion, ref')
    put('ref_tr_tr_cov', m('hurdle_800', 'tr_g05', 'test_transition', 'cobertura'), 1, 'cobertura T+ACI 0.05 transicion, ref')
    put('ref_tr_tr_dw', abs(100 * (m('hurdle_800', 'tr_g05', 'test_transition', 'ancho_medio') /
                                   m('hurdle_800', 'static', 'test_transition', 'ancho_medio') - 1)), 0,
        'reduccion de ancho T+ACI transicion, ref (valor absoluto)')
    put('ref_tr_tot_inf', m('hurdle_800', 'tr_g05', campo='pct_infinito'), 1, '% infinitos T+ACI 0.05 test, ref')
    put('ref_tr_tot_IS', m('hurdle_800', 'tr_g05'), 0, 'IS finito T+ACI 0.05 test, ref')
    put('ref_st_tot_IS', m('hurdle_800', 'static'), 0, 'IS estatico test, ref')
    put('ref_st_tot_cov', m('hurdle_800', 'static', campo='cobertura'), 1, 'cobertura estatica test, ref')
    for b in ('hurdle_800', 'hurdle_es', 'hurdle_sigma_x', 'qgbm_54x400'):
        w_s = m(b, 'static', 'test_transition', 'ancho_medio')
        w_t = m(b, 'tr_g05', 'test_transition', 'ancho_medio')
        C[f'dw_tr_{b}'] = sgn(100 * (w_t / w_s - 1)); DEF[f'dw_tr_{b}'] = f'cambio de ancho T+ACI transicion, {b}'
        oc = m(b, 'static', 'test_transition', 'cobertura') - 90
        oc_exact = CE[(CE.config == 'tr_g05') & (CE.brazo == b) & (CE.ventana == 'test_transition')].oc.iloc[0]
        C[f'oc_tr_{b}'] = sgn(oc_exact); DEF[f'oc_tr_{b}'] = f'sobre-cobertura estatica transicion (filas), {b}'
    put('qg_st_tr_cov', m('qgbm_54x400', 'static', 'test_transition', 'cobertura'), 1, 'cobertura estatica transicion, QGBM')
    # ---------------------------------------------------------- modelo base vs capa
    ref_st = m('hurdle_800', 'static')
    es_st, qg_st = m('hurdle_es', 'static'), m('qgbm_54x400', 'static')
    put('es_st_tot_IS', es_st, 0, 'IS estatico test, hurdle ES')
    put('es_st_tot_cov', m('hurdle_es', 'static', campo='cobertura'), 1, 'cobertura estatica test, ES')
    put('es_vs_ref_static_IS_pct', 100 * (1 - es_st / ref_st), 0, 'reduccion % de IS estatico ES vs ref')
    put('qg_vs_ref_static_IS_pct', 100 * (1 - qg_st / ref_st), 0, 'reduccion % de IS estatico QGBM vs ref')
    put('es_vs_ref_static_W_pct', 100 * (1 - m('hurdle_es', 'static', campo='ancho_medio') /
                                         m('hurdle_800', 'static', campo='ancho_medio')), 0, 'reduccion % de ancho estatico ES vs ref')
    capas = ['sw60', 'aci_g05', 'tr_g05', 'aci_sel', 'tr_sel', 'cqr', 'aci_g05_amin005', 'tr_g05_amin005']
    nombres = {'sw60': 'the 60-day sliding window', 'aci_g05': 'ACI', 'tr_g05': 'Transport+ACI',
               'aci_sel': 'ACI with the selected step', 'tr_sel': 'the selected Transport+ACI',
               'cqr': 'one-sided CQR', 'aci_g05_amin005': 'bounded ACI', 'tr_g05_amin005': 'bounded Transport+ACI'}
    fin = [(c, m('hurdle_800', c)) for c in capas if m('hurdle_800', c, campo='pct_infinito') == 0]
    best = min(fin, key=lambda x: x[1])
    put('ref_best_layer_name', nombres[best[0]], 0, 'mejor capa (sin infinitos) sobre el hurdle ref')
    put('ref_best_layer_IS', best[1], 0, 'IS de la mejor capa sobre el hurdle ref')
    put('ref_best_layer_IS_pct', 100 * (1 - best[1] / ref_st), 0, 'reduccion % de IS de la mejor capa sobre ref')
    online = ['sw60', 'aci_sel', 'tr_sel', 'aci_g05_amin005', 'tr_g05_amin005']
    be = min(m('hurdle_es', c) for c in online)
    put('es_best_online_gain_pct', 100 * (1 - be / es_st), 0, 'mejora % de la mejor capa online sobre ES')
    put('es_tr_g05_vs_st_pct', 100 * (m('hurdle_es', 'tr_g05') / es_st - 1), 0, 'empeoramiento % T+ACI 0.05 vs estatico, ES')
    put('es_tr_sel_vs_st_pct', abs(100 * (m('hurdle_es', 'tr_sel') / es_st - 1)), 0, '|diferencia %| T+ACI sel vs estatico, ES')
    put('qg_st_tot_IS', qg_st, 0, 'IS estatico test, QGBM')
    put('qg_st_tot_cov', m('qgbm_54x400', 'static', campo='cobertura'), 1, 'cobertura estatica test, QGBM')
    put('ref_cqr_tot_IS', m('hurdle_800', 'cqr'), 0, 'IS CQR test, ref')
    put('qg_cqr_tot_IS', m('qgbm_54x400', 'cqr'), 0, 'IS CQR test, QGBM')
    put('qg_cqr_tot_cov', m('qgbm_54x400', 'cqr', campo='cobertura'), 1, 'cobertura CQR test, QGBM')
    put('es_cqr_tot_cov', m('hurdle_es', 'cqr', campo='cobertura'), 1, 'cobertura CQR test, ES')
    put('es_cqr_tot_IS', m('hurdle_es', 'cqr'), 0, 'IS CQR test, ES')
    # cobertura del cuantil 0.9 propio del hurdle ES en calibracion, y qhat PIT
    h = L.panel_filas()
    calm = ((h.fecha >= L.R.CAL_INI) & (h.fecha < L.R.CAL_FIN)).values
    pes = L.cargar_predictiva('hurdle_es')
    q90 = pes.inv(np.full(len(h), 0.9))
    put('es_q90_cal_cov', 100 * np.mean(h.y_real.values[calm] <= q90[calm]), 1, 'cobertura del q0.9 propio del hurdle ES en calibracion')
    s_es = pes.cdf(h.y_real.values, np.random.default_rng(L.R.SEED_CONFORMAL))
    put('es_qhat', L.cm.q_conformal(s_es[calm], 0.10), 3, 'qhat PIT estatico, hurdle ES')
    q = B[(B.brazo == 'hurdle_es')].Q_cqr.iloc[0]
    C['es_cqr_Q'] = sgn(q); DEF['es_cqr_Q'] = 'correccion conformal de CQR (MWh), ES'
    # ---------------------------------------------------------- diagnostico
    o40 = D['tr_g05|r1_40']
    put('r_40', o40['r'], 2, 'r 40 celdas (T+ACI 0.05)')
    put('slope_40', o40['pendiente'], 2, 'pendiente 40 celdas')
    put('slope_40_lo', o40['ic95']['pendiente'][0], 2, 'IC pendiente 40 celdas, inf')
    put('slope_40_hi', o40['ic95']['pendiente'][1], 2, 'IC pendiente 40 celdas, sup')
    o45 = D['tr_g05|r2_45']
    put('slope_45_lo', o45['ic95']['pendiente'][0], 2, 'IC pendiente 45 celdas, inf')
    put('slope_45_hi', o45['ic95']['pendiente'][1], 2, 'IC pendiente 45 celdas, sup')
    oos = D['fuera_de_muestra_hurdle_es']
    put('oos_r', oos['r_obs_pred'], 2, 'r observado-predicho, hurdle ES fuera de muestra')
    put('oos_rmse', oos['rmse'], 1, 'RMSE fuera de muestra (pp)')
    a45 = D['tr_g05|r2_45']
    put('mec_r2_pct', 100 * a45['R2_obs_sobre_mec'], 0, 'R2 observado sobre mecanico (%), T+ACI 0.05, 45 celdas')
    put('mec_slope_45', a45['pendiente_mec'], 2, 'pendiente mecanica, 45 celdas')
    put('obs_slope_45', a45['pendiente'], 2, 'pendiente observada, T+ACI 0.05, 45 celdas')
    C['resid_45'] = sgn(a45['resid_media']); DEF['resid_45'] = 'residuo medio (%)'
    C['resid_45_lo'] = sgn(a45['ic95']['resid_media'][0]); DEF['resid_45_lo'] = 'IC residuo, inf'
    C['resid_45_hi'] = sgn(a45['ic95']['resid_media'][1]); DEF['resid_45_hi'] = 'IC residuo, sup'
    put('resid_r_45', a45['r_resid_oc'], 2, 'r(residuo, sobre-cobertura)')
    C['resid_aci_45'] = sgn(D['aci_g05_amin005|r2_45']['resid_media']); DEF['resid_aci_45'] = 'residuo medio ACI acotado'
    am = D['tr_g05_amin005|r2_45']
    put('amin_mec_slope', am['pendiente_mec'], 2, 'pendiente mecanica, T+ACI acotado')
    C['amin_resid'] = sgn(am['resid_media']); DEF['amin_resid'] = 'residuo medio, T+ACI acotado'
    put('amin_r2', am['R2_obs_sobre_mec'], 2, 'R2 mecanico, T+ACI acotado')
    r2s = [D['tr_sel|r2_45']['R2_obs_sobre_mec'], D['aci_sel|r2_45']['R2_obs_sobre_mec']]
    put('sel_r2_min', min(r2s), 2, 'R2 mecanico configuraciones seleccionadas, min')
    put('sel_r2_max', max(r2s), 2, 'R2 mecanico configuraciones seleccionadas, max')
    C['resid_trsel'] = sgn(D['tr_sel|r2_45']['resid_media']); DEF['resid_trsel'] = 'residuo T+ACI seleccionado'
    C['resid_acisel'] = sgn(D['aci_sel|r2_45']['resid_media']); DEF['resid_acisel'] = 'residuo ACI seleccionado'
    an = D['tr_g05|r2_45']['anova_oc']
    put('anova_modelo_pct', 100 * an['modelo'], 0, 'ANOVA: % varianza de OC por modelo base')
    put('anova_ventana_pct', 100 * an['ventana'], 0, 'ANOVA: % varianza de OC por ventana')
    ct = CE[(CE.config == 'tr_g05') & (CE.ventana == 'test_transition')]
    C['oc_min_transicion'] = sgn(ct.oc.min()); DEF['oc_min_transicion'] = 'OC minima en transicion (9 modelos)'
    C['oc_max_transicion'] = sgn(ct.oc.max()); DEF['oc_max_transicion'] = 'OC maxima en transicion (9 modelos)'
    put('oc_rango_transicion', ct.oc.max() - ct.oc.min(), 1, 'rango de OC en transicion (pp)')
    w = INF[(INF.config == 'tr_g05') & (INF.conjunto == 'r2_45') & INF.metodo.str.startswith('dentro de ventana')]
    w4 = w[~w.metodo.str.endswith('2025-S1')]
    put('within_r_4_min', w4.r.min(), 2, 'r dentro de ventana (4 ventanas sin 2025-S1), minimo')
    put('within_r_4_max', w4.r.max(), 2, 'r dentro de ventana (4 ventanas sin 2025-S1), maximo')
    put('within_r_2025s1', float(w[w.metodo.str.endswith('2025-S1')].r.iloc[0]), 2, 'r dentro de 2025-S1')
    c25 = CE[(CE.config == 'tr_g05') & (CE.ventana == '2025-S1')]
    put('oc_rango_2025s1', c25.oc.max() - c25.oc.min(), 1, 'rango de OC en 2025-S1 (pp)')
    fe = INF[(INF.config == 'tr_g05') & (INF.conjunto == 'r2_45') &
             INF.metodo.isin(['EF ventana', 'EF modelo', 'EF bidireccional', 'Efectos aleatorios cruzados'])]
    put('slope_fe_min', fe.pendiente.min(), 2, 'pendiente minima (EF/EA)')
    put('slope_fe_max', fe.pendiente.max(), 2, 'pendiente maxima (EF/EA)')
    for k, mt in (('wcb_modelo_p', 'Wild cluster bootstrap por modelo'), ('wcb_ventana_p', 'Wild cluster bootstrap por ventana')):
        p = float(INF[(INF.config == 'tr_g05') & (INF.conjunto == 'r2_45') & (INF.metodo == mt)].p_valor.iloc[0])
        C[k] = f'{p:.3f}' if p >= 0.01 else (f'{p:.4f}' if p > 0 else '<0.0001')
        DEF[k] = f'p-valor {mt}, 45 celdas'
    # ---------------------------------------------------------- simulacion
    if SIM is not None:
        post = SIM[SIM.ventana.isin(['W2 transition', 'W3', 'W4', 'W5'])]
        mod = {x.split(' ')[0]: x for x in SIM.modelo.unique()}

        def oc_sim(mm, esc):
            return post[(post.modelo == mod[mm]) & (post.escenario == esc)].oc.mean()
        C['sim_m1_s1'] = sgn(oc_sim('M1', 'S1 level only')); DEF['sim_m1_s1'] = 'OC media M1 en S1'
        C['sim_m1_s2'] = sgn(oc_sim('M1', 'S2 level + dispersion')); DEF['sim_m1_s2'] = 'OC media M1 en S2'
        C['sim_m2_s0'] = sgn(oc_sim('M2', 'S0 no shift')); DEF['sim_m2_s0'] = 'OC media M2 en S0'
        C['sim_m4_s2'] = sgn(oc_sim('M4', 'S2 level + dispersion')); DEF['sim_m4_s2'] = 'OC media M4 en S2'
        s2 = SR['S2 level + dispersion']['tr']
        put('sim_r2_s2', s2['R2_mec']['mediana'], 2, 'mediana R2 mecanico, S2')
        C['sim_resid_s2'] = sgn(s2['resid']['mediana']); DEF['sim_resid_s2'] = 'mediana residuo, S2 (%)'
        m1 = post[(post.modelo == mod['M1']) & (post.escenario == 'S2 level + dispersion')].oc
        C['sim_m1_lo'] = sgn(np.percentile(m1, 2.5)); DEF['sim_m1_lo'] = 'OC M1 por ventana, p2.5 (S2)'
        C['sim_m1_hi'] = sgn(np.percentile(m1, 97.5)); DEF['sim_m1_hi'] = 'OC M1 por ventana, p97.5 (S2)'

    # ---------------------------------------------------------- escalera
    bt = B[B.periodo == 'TEST_COMPLETO'].set_index('brazo').crps
    put('qg15_vs_ref_crps_pct', 100 * (1 - bt['qgbm_54x15'] / bt['hurdle_800']), 1, 'mejora % CRPS 54x15 vs ref')
    put('qg100_vs_ref_crps_pct', 100 * (1 - bt['qgbm_54x100'] / bt['hurdle_800']), 1, 'mejora % CRPS 54x100 vs ref')
    put('h2000_vs_ref_crps_pct', 100 * (bt['hurdle_2000'] / bt['hurdle_800'] - 1), 1, 'empeoramiento % CRPS hurdle 2000')
    put('es_vs_ref_crps_pct', 100 * (1 - bt['hurdle_es'] / bt['hurdle_800']), 1, 'mejora % CRPS ES vs ref')
    put('es_vs_qg_crps_pct', 100 * (bt['hurdle_es'] / bt['qgbm_54x400'] - 1), 0, '% CRPS ES por encima del QGBM')
    # ---------------------------------------------------------- ablaciones
    def ab(b, comp):
        return float(AB[(AB.brazo == b) & (AB.componente == comp) & (AB.periodo == 'TEST_COMPLETO')].d_IS.iloc[0])
    put('abl_aci_ref', abs(ab('hurdle_800', 'Online adaptation (ACI over static)')), 1, 'mejora IS por ACI, ref')
    put('abl_aci_es', abs(ab('hurdle_es', 'Online adaptation (ACI over static)')), 1, 'mejora IS por ACI, ES')
    C['abl_aci_qg'] = f"{ab('qgbm_54x400', 'Online adaptation (ACI over static)'):.1f}"; DEF['abl_aci_qg'] = 'costo IS por ACI, QGBM'
    fq = AB[(AB.brazo == 'qgbm_54x400') & (AB.componente == 'Full scheme (over static)') & (AB.periodo == 'TEST_COMPLETO')].iloc[0]
    put('abl_full_qg', fq.d_IS, 1, 'esquema completo vs estatico, QGBM')
    C['abl_full_qg_lo'] = sgn(fq.lo); DEF['abl_full_qg_lo'] = 'IC inf'
    C['abl_full_qg_hi'] = sgn(fq.hi); DEF['abl_full_qg_hi'] = 'IC sup'
    TT = pd.read_csv(RES / 'r2_13_tiempos.csv' if (RES / 'r2_13_tiempos.csv').exists() else RES / 'r2_02_tiempos.csv'); tt = TT[TT.brazo == 'hurdle_800'].set_index('componente').segundos
    put('abl_shrink_runtime_pct', 100 * (tt['tr_g05'] - tt['ab_tr_sinshrink_g05']) / tt['tr_g05'], 0, '% del tiempo de T+ACI que es shrinkage (ref)')
    for k, b in (('abl_tr_ref', 'hurdle_800'), ('abl_tr_es', 'hurdle_es'), ('abl_tr_qg', 'qgbm_54x400')):
        C[k] = sgn(ab(b, 'Transport added to ACI')); DEF[k] = f'Delta IS transporte sobre ACI, {b}'
    # ---------------------------------------------------------- operacional
    tab = OP[(OP.subconjunto == 'all') & np.isclose(OP.alpha, 0.10) & OP.base.isin(L.PRINCIPALES) &
             OP.metodo.isin(['static', 'aci_sel', 'tr_sel', 'tr_g05', 'cqr'])]
    put('cob_energia_min', tab.cob_energia.min(), 0, 'cobertura ponderada por energia, minima')
    put('cob_energia_max', tab.cob_energia.max(), 0, 'cobertura ponderada por energia, maxima')
    put('nc_tr_ref', op('hurdle_800', 'tr_g05', campo='energia_no_cubierta'), 1, 'energia no cubierta T+ACI 0.05 ref')
    vtr = [op('hurdle_800', m_, campo='energia_no_cubierta') for m_ in ('tr_sel', 'tr_g05', 'tr_g05_amin005')]
    put('nc_tr_ref_min', min(vtr), 1, 'energia no cubierta, variantes de transporte ref, min')
    put('nc_tr_ref_max', max(vtr), 1, 'energia no cubierta, variantes de transporte ref, max')
    spread = 0.0
    for a_ in (0.10, 0.05, 0.01):
        v = [op('qgbm_54x400', m_, campo='IS_finitos', a=a_) for m_ in ('static', 'aci_sel', 'tr_sel', 'cqr')]
        spread = max(spread, 100 * (max(v) - min(v)) / min(v))
    put('qg_cost_spread_pct', spread, 0, 'dispersion % del costo entre capas sobre QGBM, max sobre k')
    put('qg_tr_k100', op('qgbm_54x400', 'tr_sel', campo='IS_finitos', a=0.01), 0, 'costo k=100 T+ACI sel QGBM')
    put('qg_tr_vs_st_k100_pct', 100 * (1 - op('qgbm_54x400', 'tr_sel', campo='IS_finitos', a=0.01) /
                                       op('qgbm_54x400', 'static', campo='IS_finitos', a=0.01)), 1, 'T+ACI sel vs estatico, k=100, QGBM (%)')
    for a_, k_ in ((0.10, 'b2_cov_90'), (0.05, 'b2_cov_95'), (0.01, 'b2_cov_99')):
        put(k_, op('model-free', 'B2 rolling distribution 60 d', a=a_), 1, f'cobertura B2 a alpha {a_}')
    for a_, k_ in ((0.10, 'b1_cov_90'), (0.05, 'b1_cov_95'), (0.01, 'b1_cov_99')):
        put(k_, op('model-free', 'B1 empirical quantile 365 d', a=a_), 1, f'cobertura B1 a alpha {a_}')
    b1k = op('model-free', 'B1 empirical quantile 365 d', campo='IS_finitos', a=0.01)
    put('b1_k100', b1k, 0, 'costo k=100 de B1')
    k100 = OP[(OP.subconjunto == 'all') & np.isclose(OP.alpha, 0.01)].IS_finitos
    assert np.isclose(b1k, k100.min()), 'B1 ya no es el mas barato a k=100'
    put('nc_st_ref', op('hurdle_800', 'static', campo='energia_no_cubierta'), 1, 'energia no cubierta estatico ref')
    put('nc_st_qg', op('qgbm_54x400', 'static', campo='energia_no_cubierta'), 1, 'energia no cubierta estatico QGBM')
    put('h1_dias', float(ALT['H1_dias']), 0, 'dias H1')
    CO = pd.read_csv(RES / 'r2_04_condicional.csv')
    co = CO[CO.base.isin(L.PRINCIPALES) & CO.metodo.isin(['static', 'aci_sel', 'tr_sel', 'tr_g05', 'cqr'])]
    peor = co[['peor_tecnologia', 'peor_tercil', 'peor_region']].max(axis=1)
    put('cond_peor_min', float(peor.min()), 1, 'peor desvio condicional, minimo entre metodos principales')
    put('cond_peor_max', float(peor.max()), 1, 'peor desvio condicional, maximo')
    assert (co.peor_region >= co[['peor_tecnologia', 'peor_tercil']].max(axis=1)).all(), 'region no es siempre el eje mas dificil'
    H1, H3 = 'H1 ex post (cal. P90)', 'H3 ex ante (regime known at origin)'
    put('st_alto_h1', op('hurdle_800', 'static', H1), 1, 'cobertura H1 estatico ref')
    put('tr_alto_h1', op('hurdle_800', 'tr_g05', H1), 1, 'cobertura H1 T+ACI 0.05 ref')
    put('qg_st_h1', op('qgbm_54x400', 'static', H1), 1, 'cobertura H1 estatico QGBM')
    put('qg_cqr_h1', op('qgbm_54x400', 'cqr', H1), 1, 'cobertura H1 CQR QGBM')
    put('qg_st_h3', op('qgbm_54x400', 'static', H3), 1, 'cobertura H3 estatico QGBM')
    put('qg_cqr_h3', op('qgbm_54x400', 'cqr', H3), 1, 'cobertura H3 CQR QGBM')
    put('tr_ref_h3', op('hurdle_800', 'tr_g05', H3), 1, 'cobertura H3 T+ACI 0.05 ref')
    put('qg_st_k20', op('qgbm_54x400', 'static', campo='IS_finitos', a=0.05), 0, 'costo k=20 estatico QGBM')
    put('qg_st_k100', op('qgbm_54x400', 'static', campo='IS_finitos', a=0.01), 0, 'costo k=100 estatico QGBM')
    put('ref_tr_k20', op('hurdle_800', 'tr_sel', campo='IS_finitos', a=0.05), 0, 'costo k=20 T+ACI sel ref')
    put('ref_tr_k100', op('hurdle_800', 'tr_sel', campo='IS_finitos', a=0.01), 0, 'costo k=100 T+ACI sel ref')
    if SE is not None:
        # ---------------------------------------------------------- sensibilidad
        ref = SE[(SE.bloque == 'ref')].set_index('brazo').IS_finitos
        e1 = SE[(SE.bloque == 'E1') & SE.parametro.isin(['tau', 'B', 'n_grid', 'refresh_days', 'min_recent_scores'])]
        dev = max(abs(100 * (r.IS_finitos / ref[r.brazo] - 1)) for _, r in e1.iterrows())
        put('sens_max_capa_pct', dev, 1, 'max cambio % de IS en E1 (tau, B, rejilla, refresco, minimo)')
        w30 = SE[(SE.bloque == 'E1') & (SE.parametro == 'window_days') & (SE.valor == '30') & (SE.brazo == 'hurdle_es')].IS_finitos.iloc[0]
        put('sens_win30_pct', 100 * (w30 / ref['hurdle_es'] - 1), 0, 'aumento % de IS con ventana de 30 dias, ES')
        e5 = SE[SE.bloque == 'E5'].groupby(['brazo', 'metodo']).cobertura.std()
        put('sens_seed_sd_max', float(e5.max()), 2, 'max DE de cobertura entre 10 semillas conformales')
        e8 = SE[(SE.bloque == 'E8') & (SE.metodo == 'Static split')].IS_finitos
        put('sens_es_st_min', float(e8.min()), 0, 'IS estatico ES, minimo entre variantes E8')
        put('sens_es_st_max', float(e8.max()), 0, 'IS estatico ES, maximo entre variantes E8')
        e8b = SE[SE.bloque == 'E8'].pivot_table(index=['parametro', 'valor'], columns='metodo', values='IS_finitos')
        assert (e8b['Static split'] < e8b['Transport+ACI']).all(), 'E8: estatico no siempre bajo T+ACI'


    # ---------------------------------------------------------- escritura
    lineas = ['% Generado por scripts/r2_07_cifras.py. No editar a mano.']
    for k in sorted(C):
        lineas.append(f'\\expandafter\\def\\csname cf@{k}\\endcsname{{{C[k]}}}')
    (MAN / 'cifras.tex').write_text('\n'.join(lineas) + '\n')
    pd.DataFrame([dict(clave=k, valor=C[k], definicion=DEF[k]) for k in sorted(C)]).to_csv(
        RES / 'r2_07_cifras.csv', index=False)
    usadas = set()
    for f in list(MAN.glob('*.tex')) + list(CARTA.glob('*.tex')):
        usadas |= set(re.findall(r'\\cf\{([^}]*)\}', f.read_text()))
    faltan = sorted(usadas - set(C))
    sobran = sorted(set(C) - usadas)
    print(f'{len(C)} cifras escritas; usadas {len(usadas)}')
    if sobran:
        print('definidas y no usadas:', sobran)
    if faltan:
        if PRELIM:
            print(f'(borrador) faltan {len(faltan)} cifras: {faltan}')
        else:
            raise SystemExit(f'FALTAN cifras usadas en el texto: {faltan}')


if __name__ == '__main__':
    main()
