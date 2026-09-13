#!/usr/bin/env python3
"""
FASE 4: metricas apropiadas y benchmarks probabilisticos.
=========================================================
Comentarios R1.5 y R2.6. Tres encargos distintos:

(1) EL PROBLEMA REAL DE LA VERSION ENVIADA. El ancho medio se calcula solo
    sobre intervalos finitos, y hay configuraciones con cerca del 10% de
    intervalos infinitos en 2025-S1 y 2025-S2. Promediar el ancho de los
    finitos y reportar aparte la fraccion de infinitos da una lectura
    optimista de la nitidez: la configuracion que mas se escapa a intervalos
    no informativos aparece como la mas nitida.

    Solucion adoptada: el **interval score del limite unilateral superior**,
        IS = U + (1/alpha) * max(y - U, 0),
    con 1/alpha porque en un limite unilateral toda la masa alpha va en la cola
    superior (el 2/alpha de Gneiting y Raftery es del intervalo central, alpha/2
    por cola). Es propio para el cuantil 1-alpha, en MWh, e **infinito cuando U
    es infinito**.
    Una configuracion no puede mejorarlo escapando al infinito. Se reporta:
      - IS_total, que vale +inf si hay algun intervalo infinito (el veredicto),
      - IS_finitos, restringido a los finitos (comparable pero incompleto),
      - la fraccion de infinitos, siempre,
      - y el ancho medio de los finitos, que se conserva por continuidad con la
        version enviada y se declara como insuficiente por si solo.

(2) ACOTAR LA ACTUALIZACION DE ALPHA. El origen de los intervalos infinitos es
    que el ACI permite alpha_t <= 0, con lo que el cuantil conformal pide un
    orden estadistico que no existe. Se evalua alpha_min en {sin cota, 0.005,
    0.01, 0.02} y se reporta el efecto sobre cobertura, ancho, IS e infinitos.

(3) BENCHMARKS PROBABILISTICOS. Cuatro, ademas de los del paper:
      B1 cuantil empirico por central, ventana movil de 365 dias
      B2 distribucion historica movil por central, ventana de 60 dias
      B3 regresion cuantilica conformalizada (CQR unilateral) sobre el GBM
      B4 lognormal inflada en cero, ajustada por central, sin covariables
    Todos con el mismo embargo de 7 dias y el mismo nivel nominal.

Salidas:
  resultados/fase4/fase4_metricas_completas.csv
  resultados/fase4/fase4_cota_alpha.csv
  resultados/fase4/fase4_benchmarks.csv
  resultados/fase4/fase4_diferencias_bootstrap.csv

Comando:
  <venv>/bin/python flagship/revision/fase4_metricas_benchmarks.py
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rev_lib as R   # noqa: E402

SAL = R.REPO / 'resultados' / 'fase4'
SAL.mkdir(parents=True, exist_ok=True)
FIN_TEST = pd.Timestamp('2026-06-01')


# ==========================================================================
# CARGA
# ==========================================================================
def cargar_todo():
    hu = pd.read_csv(R.FLAGSHIP / 'predicciones' / 'pred_hurdle.csv',
                     parse_dates=['fecha']).sort_values(
                         ['fecha', 'central_codigo']).reset_index(drop=True)
    qg = pd.read_csv(R.FLAGSHIP / 'predicciones' / 'pred_qgbm_multi.csv.gz',
                     parse_dates=['fecha']).sort_values(
                         ['fecha', 'central_codigo']).reset_index(drop=True)
    assert (hu.fecha.values == qg.fecha.values).all()
    assert (hu.central_codigo.values == qg.central_codigo.values).all()
    p_hu = R.PredictivaHurdle(hu.p_occ.values, hu.mu_log.values,
                              float(hu.sigma.iloc[0]))
    cols = [c for c in qg.columns if c.startswith('q0')]
    taus = np.array([float(c[1:]) for c in cols])
    o = np.argsort(taus)
    p_qg = R.PredictivaCuantilica(qg[[cols[i] for i in o]].values, taus[o])
    return hu, p_hu, qg, p_qg, taus[o], [cols[i] for i in o]


# ==========================================================================
# BENCHMARKS
# ==========================================================================
def bench_cuantil_movil(df, ventana_dias, alpha=R.ALPHA, refresco=7,
                        embargo=R.EMBARGO_DIAS, ini=R.CAL_FIN, fin=FIN_TEST):
    """B1 y B2: cuantil empirico (1-alpha) del historial reciente de CADA
    central, con embargo de horizonte y refresco semanal. Es el benchmark no
    condicional obvio: no usa modelo, solo la propia historia de la central."""
    piv = df.pivot_table(index='fecha', columns='central_codigo',
                         values='y_real', aggfunc='first')
    piv = piv.reindex(pd.date_range(df.fecha.min(), df.fecha.max(), freq='D'))
    mask_test = (df.fecha >= ini) & (df.fecha < fin)
    U = np.full(len(df), np.nan)
    fechas = df.fecha.values
    centrales = df.central_codigo.values
    col_idx = {c: i for i, c in enumerate(piv.columns)}
    M = piv.values
    idx_fecha = {d: i for i, d in enumerate(piv.index)}
    for t0 in pd.date_range(ini, fin, freq=f'{refresco}D'):
        a = idx_fecha.get(t0 - pd.Timedelta(days=ventana_dias + embargo))
        b = idx_fecha.get(t0 - pd.Timedelta(days=embargo))
        if a is None or b is None:
            a = max(0, idx_fecha[piv.index[0]])
            b = idx_fecha.get(t0 - pd.Timedelta(days=embargo), 0)
        W = M[a:b]
        with np.errstate(invalid='ignore'):
            q = np.nanquantile(np.where(np.isnan(W), np.nan, W), 1 - alpha, axis=0)
        obj = ((fechas >= np.datetime64(t0.date()))
               & (fechas < np.datetime64((t0 + pd.Timedelta(days=refresco)).date())))
        if obj.sum() == 0:
            continue
        ci = np.array([col_idx.get(c, -1) for c in centrales[obj]])
        v = np.where(ci >= 0, q[np.clip(ci, 0, len(q) - 1)], np.nan)
        U[obj] = v
    U = np.where(np.isnan(U), 0.0, U)   # central sin historia: limite 0
    return U, mask_test.values


def bench_cqr(qg, cols, taus, alpha=R.ALPHA, ini=R.CAL_FIN, fin=FIN_TEST):
    """B3: regresion cuantilica conformalizada unilateral (Romano et al. 2019).
    Score de no conformidad E = y - q_{1-alpha}(x) sobre la calibracion;
    U(x) = q_{1-alpha}(x) + Q_{1-alpha}(E). A diferencia del score PIT, mide la
    no conformidad en MWh y no en escala de probabilidad."""
    j = int(np.argmin(np.abs(taus - (1 - alpha))))
    q1a = qg[cols[j]].values
    cal = ((qg.fecha >= R.CAL_INI) & (qg.fecha < R.CAL_FIN)).values
    E = qg.y_real.values[cal] - q1a[cal]
    n = int(cal.sum())
    k = int(np.ceil((n + 1) * (1 - alpha)))
    Q = np.sort(E)[k - 1] if k <= n else np.inf
    U = q1a + Q
    mask_test = ((qg.fecha >= ini) & (qg.fecha < fin)).values
    return np.maximum(U, 0.0), mask_test, float(Q), float(taus[j])


def bench_zi_lognormal(df, alpha=R.ALPHA, ini=R.CAL_FIN, fin=FIN_TEST):
    """B4: lognormal inflada en cero ajustada POR CENTRAL sobre la ventana de
    calibracion, sin covariables. Es el modelo parametrico inflado en cero mas
    simple que respeta la estructura del dato. U = cuantil (1-alpha) de la
    mezcla. Centrales sin positivos en calibracion reciben U = 0."""
    cal = df[(df.fecha >= R.CAL_INI) & (df.fecha < R.CAL_FIN)]
    par = {}
    for c, g in cal.groupby('central_codigo', observed=True):
        y = g.y_real.values
        pos = y[y > 0]
        if len(pos) < 5:
            par[c] = (0.0, 0.0, 1.0)
            continue
        par[c] = (float((y > 0).mean()), float(np.log(pos).mean()),
                  float(np.log(pos).std(ddof=1)) or 1.0)
    from scipy.stats import norm
    U = np.zeros(len(df))
    cc = df.central_codigo.values
    for i, c in enumerate(cc):
        p, mu, sg = par.get(c, (0.0, 0.0, 1.0))
        if p <= 0:
            continue
        q = 1 - alpha
        if q <= 1 - p:
            U[i] = 0.0
        else:
            U[i] = np.exp(mu + sg * norm.ppf(min((q - (1 - p)) / p, 1 - 1e-12)))
    mask_test = ((df.fecha >= ini) & (df.fecha < fin)).values
    return U, mask_test


# ==========================================================================
def metricas(nombre, f, y, U, familia, crps=np.nan):
    filas = R.filas_por_periodo(nombre, f, y, U)
    for fila in filas:
        fila['familia'] = familia
        fila['crps'] = crps
    fila_tot = R.resumen_metrico(nombre, 'TEST_COMPLETO', f, y, U)
    fila_tot['familia'] = familia
    fila_tot['crps'] = crps
    return filas + [fila_tot]


def main():
    print('=' * 96)
    print('FASE 4 - METRICAS APROPIADAS Y BENCHMARKS PROBABILISTICOS (R1.5, R2.6)')
    print('=' * 96)
    hu, p_hu, qg, p_qg, taus, cols = cargar_todo()
    rng = np.random.default_rng(R.SEED_CONFORMAL)
    hu = hu.assign(s=p_hu.cdf(hu.y_real.values, rng))
    s_cal = hu.s.values[((hu.fecha >= R.CAL_INI) & (hu.fecha < R.CAL_FIN)).values]

    idx_test = ((hu.fecha >= R.CAL_FIN) & (hu.fecha < FIN_TEST)).values
    test = hu[idx_test].reset_index(drop=True)
    p_test = p_hu.sub(idx_test)
    y_t, f_t = test.y_real.values, test.fecha.values
    fechas_test = np.sort(test.fecha.unique())
    print(f'test: {len(test):,} filas, {len(fechas_test)} dias, '
          f'{test.central_codigo.nunique()} centrales')

    rng_c = np.random.default_rng(R.SEED_CRPS)
    crps_hu = R.crps_pred(p_test, y_t, rng_c)
    crps_qg = R.crps_pred(p_qg.sub(idx_test), y_t, np.random.default_rng(R.SEED_CRPS))
    print(f'CRPS sobre el test completo: hurdle {crps_hu:.2f} MWh, '
          f'GBM multi-cuantil {crps_qg:.2f} MWh')

    filas, series = [], {}

    # ---- metodos del paper -------------------------------------------
    print('\n' + '-' * 96)
    print('1. Metodos del manuscrito, con la bateria de metricas completa')
    print('-' * 96)
    U = R.estatico(p_test, s_cal)
    series['Split estatico (PIT)'] = U
    filas += metricas('Split estatico (PIT)', f_t, y_t, U, 'paper', crps_hu)

    U = R.ventana_deslizante(p_test, hu.s.values, hu.fecha.values, f_t,
                             '2024-09-01', '2026-05-31')
    series['Ventana deslizante 60d'] = U
    filas += metricas('Ventana deslizante 60d', f_t, y_t, U, 'paper', crps_hu)

    for g in (0.02, 0.05):
        U, _, _ = R.aci(p_test, s_cal, y_t, f_t, fechas_test, g)
        nm = f'ACI (g={g})'
        series[nm] = U
        filas += metricas(nm, f_t, y_t, U, 'paper', crps_hu)
    # se CONTINUA el generador que aleatorizo el score, que es el orden de la
    # corrida oficial; con uno fresco el ancho del test completo daba 591.4 en
    # vez de los 595.9 canonicos
    rng_t = rng
    for g in (0.02, 0.05):
        U, _, _ = R.transporte_aci(p_test, s_cal, hu.s.values, hu.fecha.values,
                                   y_t, f_t, fechas_test, g, rng_t,
                                   ini_test=R.CAL_FIN)
        nm = f'Transporte+ACI (g={g})'
        series[nm] = U
        filas += metricas(nm, f_t, y_t, U, 'paper', crps_hu)

    # ---- configuracion seleccionada en la Fase 3 ---------------------
    print('2. Configuracion seleccionada por origen rodante en la Fase 3')
    U, _, _ = R.aci(p_test, s_cal, y_t, f_t, fechas_test, 0.005)
    series['ACI (g=0.005, Fase 3)'] = U
    filas += metricas('ACI (g=0.005, Fase 3)', f_t, y_t, U, 'seleccionado', crps_hu)
    U, _, _ = R.transporte_aci(p_test, s_cal, hu.s.values, hu.fecha.values,
                               y_t, f_t, fechas_test, 0.005,
                               np.random.default_rng(R.SEED_CONFORMAL),
                               ventana_dias=120, ini_test=R.CAL_FIN)
    series['Transporte+ACI (g=0.005, v=120, Fase 3)'] = U
    filas += metricas('Transporte+ACI (g=0.005, v=120, Fase 3)', f_t, y_t, U,
                      'seleccionado', crps_hu)

    # ---- benchmarks ---------------------------------------------------
    print('3. Benchmarks probabilisticos')
    Ub, _ = bench_cuantil_movil(hu, 365)
    series['B1 cuantil empirico 365d'] = Ub[idx_test]
    filas += metricas('B1 cuantil empirico 365d', f_t, y_t, Ub[idx_test],
                      'benchmark')
    Ub, _ = bench_cuantil_movil(hu, 60)
    series['B2 distribucion movil 60d'] = Ub[idx_test]
    filas += metricas('B2 distribucion movil 60d', f_t, y_t, Ub[idx_test],
                      'benchmark')
    Ub, mt, Qcqr, tau_cqr = bench_cqr(qg, cols, taus)
    print(f'   B3 CQR: cuantil base tau={tau_cqr}, ajuste conformal '
          f'Q = {Qcqr:+.1f} MWh')
    series['B3 CQR unilateral (GBM)'] = Ub[idx_test]
    filas += metricas('B3 CQR unilateral (GBM)', f_t, y_t, Ub[idx_test],
                      'benchmark', crps_qg)
    Ub, _ = bench_zi_lognormal(hu)
    series['B4 lognormal inflada en cero'] = Ub[idx_test]
    filas += metricas('B4 lognormal inflada en cero', f_t, y_t, Ub[idx_test],
                      'benchmark')

    tab = pd.DataFrame(filas)
    tab.to_csv(SAL / 'fase4_metricas_completas.csv', index=False)

    print('\n' + '=' * 96)
    print('TEST COMPLETO (sep 2024 a may 2026). IS_total = +inf si hay algun')
    print('intervalo infinito: ese es el veredicto, el ancho medio no lo es.')
    print('=' * 96)
    tt = tab[tab.periodo == 'TEST_COMPLETO'].sort_values('IS_finitos')
    print(tt[['familia', 'metodo', 'cobertura', 'se_cluster', 'ancho_medio',
              'pct_infinito', 'IS_finitos', 'IS_total', 'crps']].to_string(index=False))

    # ---- cota de alpha -------------------------------------------------
    print('\n' + '=' * 96)
    print('EFECTO DE ACOTAR LA ACTUALIZACION DE ALPHA (encargo explicito de R1.5)')
    print('=' * 96)
    filas = []
    for amin in (None, 0.005, 0.01, 0.02):
        et = 'sin cota' if amin is None else f'alpha_min={amin}'
        # Mismo arreglo que H7: el transporte CONTINUA el generador que
        # aleatorizo el score y consume gamma = 0.02 antes que 0.05, que es el
        # orden de la corrida canonica. Con un generador fresco por corrida la
        # fila sin cota de Transporte+ACI (g=0.05) daba 593.4 / 6.1% / 1028.2
        # en vez de los 595.9 / 5.9% / 1029.9 de la Tabla 9. El mapa no depende
        # de alpha, asi que cada cota ve los mismos sorteos que la corrida sin
        # cota y difiere de ella solo por la cota.
        rng_t = np.random.default_rng(R.SEED_CONFORMAL)
        p_hu.cdf(hu.y_real.values, rng_t)   # consume los sorteos del score
        for g in (0.02, 0.05):
            U, _, _ = R.aci(p_test, s_cal, y_t, f_t, fechas_test, g,
                            alpha_min=amin)
            for fila in metricas(f'ACI (g={g})', f_t, y_t, U, 'cota_alpha'):
                fila['cota'] = et
                fila['gamma'] = g
                filas.append(fila)
            U, _, _ = R.transporte_aci(
                p_test, s_cal, hu.s.values, hu.fecha.values, y_t, f_t,
                fechas_test, g, rng_t,
                alpha_min=amin, ini_test=R.CAL_FIN)
            for fila in metricas(f'Transporte+ACI (g={g})', f_t, y_t, U,
                                 'cota_alpha'):
                fila['cota'] = et
                fila['gamma'] = g
                filas.append(fila)
    ca = pd.DataFrame(filas)
    # la fila sin cota ES la corrida del manuscrito: tiene que coincidir celda a
    # celda con la de metricas completas, o la Tabla 10 no describe el mismo
    # objeto que la Tabla 9
    col = ['cobertura', 'ancho_medio', 'pct_infinito', 'IS_finitos']
    for met in ('ACI (g=0.02)', 'ACI (g=0.05)',
                'Transporte+ACI (g=0.02)', 'Transporte+ACI (g=0.05)'):
        a = ca[(ca.cota == 'sin cota') & (ca.metodo == met)].set_index('periodo')[col]
        b = tab[(tab.familia == 'paper') & (tab.metodo == met)].set_index('periodo')[col]
        if not a.equals(b.loc[a.index]):
            raise SystemExit(f'la fila sin cota de {met} no reproduce la corrida '
                             f'canonica de metricas completas:\n{a}\n{b}')
    ca.to_csv(SAL / 'fase4_cota_alpha.csv', index=False)
    v = ca[ca.periodo == 'TEST_COMPLETO']
    print(v[['metodo', 'cota', 'cobertura', 'se_cluster', 'ancho_medio',
             'pct_infinito', 'IS_finitos', 'IS_total']].to_string(index=False))
    print('\nFraccion de intervalos infinitos por ventana y cota:')
    pv = ca[ca.periodo != 'TEST_COMPLETO'].pivot_table(
        index=['metodo', 'cota'], columns='periodo', values='pct_infinito')
    print(pv.reindex(columns=[p for p, _, _ in R.PERIODOS]).to_string())

    # ---- incertidumbre de las diferencias ------------------------------
    print('\n' + '=' * 96)
    print('INCERTIDUMBRE DE LAS DIFERENCIAS entre metodos (R1.5)')
    print('bootstrap de 2000 remuestreos de dias completos, IC de percentil 95%')
    print('sobre el interval score. Referencia: Split estatico (PIT).')
    print('=' * 96)
    ref = series['Split estatico (PIT)']
    isr = R.interval_score_unilateral(y_t, ref)
    difs = []
    for nm, U in series.items():
        if nm == 'Split estatico (PIT)':
            continue
        isa = R.interval_score_unilateral(y_t, U)
        fi = np.isfinite(isa) & np.isfinite(isr)
        d, lo, hi = R.bootstrap_diferencia(f_t[fi], isa[fi], isr[fi])
        cov_a = (y_t <= U).astype(float)
        cov_r = (y_t <= ref).astype(float)
        dc, lc, hc = R.bootstrap_diferencia(f_t, cov_a, cov_r)
        difs.append(dict(metodo=nm, d_IS=round(d, 1), IS_lo=round(lo, 1),
                         IS_hi=round(hi, 1),
                         significativo='si' if lo * hi > 0 else 'no',
                         d_cob_pp=round(100 * dc, 2), cob_lo=round(100 * lc, 2),
                         cob_hi=round(100 * hc, 2),
                         pct_descartado=round(100 * (1 - fi.mean()), 2)))
    dd = pd.DataFrame(difs).sort_values('d_IS')
    dd.to_csv(SAL / 'fase4_diferencias_bootstrap.csv', index=False)
    print(dd.to_string(index=False))
    print(f'\nguardado en {SAL.relative_to(R.REPO)}/')


if __name__ == '__main__':
    main()
