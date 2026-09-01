#!/usr/bin/env python3
"""
FASE 5: dependencia de panel y cobertura condicional.
=====================================================
Comentario R2.5. El revisor tiene razon: los errores estandar agrupados por
fecha CUANTIFICAN la incertidumbre inducida por la dependencia diaria, pero no
RESTAURAN la intercambiabilidad, que es la hipotesis de la que cuelga la
garantia de muestra finita del split conformal. Un error estandar mas ancho no
convierte en valido un procedimiento cuya validez supone independencia.

Se prueban tres remedios y se reporta la cobertura desagregada.

REMEDIOS
  M0  split conformal agrupado (referencia, el del manuscrito)
  M1  conformal por bloques de dia: la unidad intercambiable pasa a ser el DIA.
      Se submuestrea una central por fecha en el conjunto de calibracion, con
      lo que los scores de calibracion son aproximadamente independientes, y se
      promedia sobre 200 replicas con semilla fija. Cuesta tamano muestral y
      lo compra en validez.
  M2  conformal por grupos (Mondrian): un cuantil conformal por grupo, con el
      grupo definido por tecnologia, por region y por tercil de potencia
      instalada. Restaura cobertura condicional al grupo por construccion.
  M3  conformal a nivel de central: un cuantil por central, con repliegue al
      pool agrupado cuando la central tiene menos de 60 scores de calibracion.

COBERTURA DESAGREGADA por tecnologia, tamano de central, region y eventos de
alto vertimiento (dias en el decil superior de vertimiento sistemico).

Salidas:
  resultados/fase5/fase5_remedios.csv
  resultados/fase5/fase5_cobertura_desagregada.csv
  resultados/fase5/fase5_diagnostico_dependencia.csv

Comando:
  <venv>/bin/python flagship/revision/fase5_dependencia_panel.py
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rev_lib as R   # noqa: E402

SAL = R.REPO / 'resultados' / 'fase5'
SAL.mkdir(parents=True, exist_ok=True)
FIN_TEST = pd.Timestamp('2026-06-01')
N_REPLICAS_BLOQUE = 200
MIN_SCORES_CENTRAL = 60


def cobertura(fecha, cubierto):
    cov, se, nd = R.cm.cobertura_clusterizada(fecha, cubierto)
    return round(100 * cov, 2), round(100 * se, 2), nd


def main():
    print('=' * 96)
    print('FASE 5 - DEPENDENCIA DE PANEL Y COBERTURA CONDICIONAL (R2.5)')
    print('=' * 96)

    hu = pd.read_csv(R.FLAGSHIP / 'predicciones' / 'pred_hurdle.csv',
                     parse_dates=['fecha']).sort_values(
                         ['fecha', 'central_codigo']).reset_index(drop=True)
    meta = pd.read_csv(R.REPO / 'release' / 'v1.0' / 'plants_metadata.csv')
    hu = hu.merge(meta[['central_codigo', 'region', 'potencia_mw']].drop_duplicates(
        'central_codigo'), on='central_codigo', how='left')
    pred = R.PredictivaHurdle(hu.p_occ.values, hu.mu_log.values,
                              float(hu.sigma.iloc[0]))
    rng = np.random.default_rng(R.SEED_CONFORMAL)
    hu = hu.assign(s=pred.cdf(hu.y_real.values, rng))

    # terciles de potencia definidos SOLO con la ventana de calibracion
    cal_mask = ((hu.fecha >= R.CAL_INI) & (hu.fecha < R.CAL_FIN)).values
    pot = hu.loc[cal_mask].groupby('central_codigo', observed=True).potencia_mw.first()
    cortes = pot.quantile([1 / 3, 2 / 3]).values
    hu['tercil_potencia'] = pd.cut(hu.potencia_mw, [-np.inf, *cortes, np.inf],
                                   labels=['pequena', 'mediana', 'grande'])
    print(f'terciles de potencia instalada (MW): <= {cortes[0]:.1f}, '
          f'<= {cortes[1]:.1f}, >')

    idx = ((hu.fecha >= R.CAL_FIN) & (hu.fecha < FIN_TEST)).values
    test = hu[idx].reset_index(drop=True)
    p_t = pred.sub(idx)
    y_t, f_t = test.y_real.values, test.fecha.values
    s_cal = hu.s.values[cal_mask]
    cal = hu[cal_mask]

    # eventos de alto vertimiento: decil superior del vertimiento sistemico
    # diario, con el umbral fijado en la ventana de CALIBRACION
    tot_cal = cal.groupby('fecha', observed=True).y_real.sum()
    umbral = float(tot_cal.quantile(0.90))
    tot_test = test.groupby('fecha', observed=True).y_real.sum()
    dias_alto = set(tot_test.index[tot_test >= umbral])
    test['alto_vertimiento'] = np.where(
        test.fecha.isin(dias_alto), 'alto (decil sup.)', 'resto')
    print(f'umbral de alto vertimiento (calibracion, p90): {umbral:,.0f} MWh/dia')
    print(f'dias de test por encima del umbral: {len(dias_alto)} de '
          f'{test.fecha.nunique()}')

    # ------------------------------------------------------------------
    # DIAGNOSTICO: cuanto se aparta el panel de la intercambiabilidad
    # ------------------------------------------------------------------
    print('\n' + '-' * 96)
    print('DIAGNOSTICO DE DEPENDENCIA en los scores de calibracion')
    print('-' * 96)
    d = cal.groupby('fecha', observed=True).s.mean()
    n_dias, n_filas = len(d), len(cal)
    var_entre = float(d.var(ddof=1))
    var_total = float(cal.s.var(ddof=1))
    m_medio = n_filas / n_dias
    # correlacion intraclase por fecha (ANOVA de un factor)
    g = cal.groupby('fecha', observed=True).s
    ms_entre = float(g.mean().sub(cal.s.mean()).pow(2).mul(g.size()).sum() / (n_dias - 1))
    ms_dentro = float(((cal.s - g.transform('mean')) ** 2).sum() / (n_filas - n_dias))
    icc = (ms_entre - ms_dentro) / (ms_entre + (m_medio - 1) * ms_dentro)
    deff = 1 + (m_medio - 1) * icc
    print(f'  filas de calibracion: {n_filas:,} en {n_dias} dias '
          f'({m_medio:.1f} centrales/dia)')
    print(f'  correlacion intraclase por fecha (ICC) = {icc:.4f}')
    print(f'  efecto de diseno = 1 + (m-1)*ICC = {deff:.2f}')
    print(f'  tamano muestral efectivo = {n_filas / deff:,.0f} filas, '
          f'no {n_filas:,}')
    print(f'  varianza entre dias {var_entre:.5f} contra varianza total '
          f'{var_total:.5f}')
    pd.DataFrame([dict(n_filas=n_filas, n_dias=n_dias, centrales_por_dia=round(m_medio, 2),
                       icc_fecha=round(icc, 5), efecto_diseno=round(deff, 3),
                       n_efectivo=round(n_filas / deff, 1),
                       var_entre_dias=round(var_entre, 6),
                       var_total=round(var_total, 6))]).to_csv(
        SAL / 'fase5_diagnostico_dependencia.csv', index=False)

    # ------------------------------------------------------------------
    # REMEDIOS
    # ------------------------------------------------------------------
    series = {}
    print('\n' + '-' * 96)
    print('REMEDIOS')
    print('-' * 96)

    qhat = R.cm.q_conformal(s_cal, R.ALPHA)
    series['M0 split agrupado (manuscrito)'] = p_t.inv(qhat)
    print(f'M0 split agrupado: qhat = {qhat:.4f} sobre {len(s_cal):,} scores')

    # M1: conformal por bloques de dia
    rb = np.random.default_rng(R.SEED_BOOTSTRAP)
    fechas_cal = cal.fecha.values
    idx_por_dia = pd.Series(np.arange(len(cal))).groupby(fechas_cal).apply(
        lambda x: x.values)
    qs = []
    for _ in range(N_REPLICAS_BLOQUE):
        sel = np.array([v[rb.integers(0, len(v))] for v in idx_por_dia])
        qs.append(R.cm.q_conformal(s_cal[sel], R.ALPHA))
    q_bloque = float(np.mean(qs))
    series['M1 conformal por bloques de dia'] = p_t.inv(q_bloque)
    print(f'M1 bloques de dia: qhat = {q_bloque:.4f} (media de '
          f'{N_REPLICAS_BLOQUE} replicas de 1 central por fecha, '
          f'{len(idx_por_dia)} scores por replica; sd entre replicas '
          f'{np.std(qs):.4f})')

    # M2: Mondrian por grupos
    for var, etq in (('tecnologia', 'tecnologia'), ('region', 'region'),
                     ('tercil_potencia', 'tercil de potencia')):
        U = np.empty(len(test))
        qg = {}
        for gval, gc in cal.groupby(var, observed=True):
            if len(gc) < 200:
                qg[gval] = qhat
                continue
            qg[gval] = R.cm.q_conformal(gc.s.values, R.ALPHA)
        for gval in test[var].unique():
            m = (test[var] == gval).values
            U[m] = p_t.sub(m).inv(qg.get(gval, qhat))
        series[f'M2 Mondrian por {etq}'] = U
        print(f'M2 Mondrian por {etq}: {len(qg)} grupos, qhat de '
              f'{min(qg.values()):.4f} a {max(qg.values()):.4f}')

    # M3: conformal por central
    U = np.empty(len(test))
    qc, repliegues = {}, 0
    for c, gc in cal.groupby('central_codigo', observed=True):
        qc[c] = (R.cm.q_conformal(gc.s.values, R.ALPHA)
                 if len(gc) >= MIN_SCORES_CENTRAL else qhat)
    for c in test.central_codigo.unique():
        m = (test.central_codigo == c).values
        if c not in qc:
            repliegues += 1
        U[m] = p_t.sub(m).inv(qc.get(c, qhat))
    series['M3 conformal por central'] = U
    fin_q = [v for v in qc.values() if np.isfinite(v)]
    print(f'M3 por central: {len(qc)} centrales calibradas, {repliegues} '
          f'repliegues al pool; qhat de {min(fin_q):.4f} a {max(fin_q):.4f}')

    # metodos adaptativos del manuscrito, para contrastar
    fechas_test = np.sort(test.fecha.unique())
    U, _, _ = R.aci(p_t, s_cal, y_t, f_t, fechas_test, 0.02)
    series['ACI (g=0.02), referencia'] = U
    U, _, _ = R.transporte_aci(p_t, s_cal, hu.s.values, hu.fecha.values, y_t,
                               f_t, fechas_test, 0.05,
                               np.random.default_rng(R.SEED_CONFORMAL),
                               ini_test=R.CAL_FIN)
    series['Transporte+ACI (g=0.05), referencia'] = U

    filas = []
    for nm, U in series.items():
        for fila in (R.filas_por_periodo(nm, f_t, y_t, U)
                     + [R.resumen_metrico(nm, 'TEST_COMPLETO', f_t, y_t, U)]):
            filas.append(fila)
    tab = pd.DataFrame(filas)
    tab.to_csv(SAL / 'fase5_remedios.csv', index=False)
    print('\n' + '=' * 96)
    print('REMEDIOS - TEST COMPLETO')
    print('=' * 96)
    print(tab[tab.periodo == 'TEST_COMPLETO'][
        ['metodo', 'cobertura', 'se_cluster', 'ancho_medio', 'pct_infinito',
         'IS_finitos']].to_string(index=False))

    # ------------------------------------------------------------------
    # COBERTURA DESAGREGADA
    # ------------------------------------------------------------------
    print('\n' + '=' * 96)
    print('COBERTURA DESAGREGADA (nominal 90%). Error estandar clusterizado por fecha.')
    print('=' * 96)
    des = []
    ejes = [('tecnologia', 'tecnologia'), ('tercil_potencia', 'tamano de central'),
            ('region', 'region'), ('alto_vertimiento', 'evento')]
    for nm, U in series.items():
        cub = (y_t <= U).astype(float)
        for var, etq in ejes:
            for gval, gi in test.groupby(var, observed=True).indices.items():
                if len(gi) < 200:
                    continue
                cov, se, nd = cobertura(f_t[gi], cub[gi])
                fi = np.isfinite(U[gi])
                des.append(dict(metodo=nm, eje=etq, grupo=str(gval),
                                cobertura=cov, se_cluster=se,
                                desvio_pp=round(cov - 100 * (1 - R.ALPHA), 2),
                                ancho_medio=round(float(U[gi][fi].mean()), 1) if fi.any() else np.nan,
                                pct_infinito=round(100 * float((~fi).mean()), 2),
                                n=len(gi), n_dias=nd))
    dd = pd.DataFrame(des)
    dd.to_csv(SAL / 'fase5_cobertura_desagregada.csv', index=False)

    for var, etq in ejes:
        print(f'\n--- {etq} ---')
        p = dd[dd.eje == etq].pivot_table(index='metodo', columns='grupo',
                                          values='cobertura')
        print(p.to_string())

    print('\n' + '-' * 96)
    print('MAXIMO DESVIO ABSOLUTO respecto del nominal, por metodo y eje')
    print('(es la medida de cobertura condicional: un metodo marginalmente')
    print('valido puede tener desvios grandes en algun grupo)')
    print('-' * 96)
    mx = dd.assign(a=dd.desvio_pp.abs()).pivot_table(
        index='metodo', columns='eje', values='a', aggfunc='max').round(2)
    mx['peor_global'] = mx.max(axis=1)
    print(mx.sort_values('peor_global').to_string())
    print(f'\nguardado en {SAL.relative_to(R.REPO)}/')


if __name__ == '__main__':
    main()
