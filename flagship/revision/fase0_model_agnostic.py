#!/usr/bin/env python3
"""
FASE 0, paso 2: ¿la ventaja de Transport+ACI es de la capa o del hurdle?
========================================================================
Comentario R1.1. Se repite el protocolo conformal COMPLETO, sin cambiar una
sola constante, sobre dos modelos base probabilisticos distintos:

  A. hurdle lognormal con sigma constante  (modelo base oficial del paper)
  B. GBM multi-cuantil denso, 54 cuantiles (modelo base alternativo, R1.1)

Todo lo demas es identico: mismo score PIT, mismas fronteras de ventana, mismo
embargo de 7 dias, misma semilla 20260720, mismos gamma, misma ventana de 60
dias, mismo shrinkage de cola (tau = 0.05, B = 150).

La pregunta que decide la Fase 0: la reduccion de ancho de Transport+ACI frente
al split estatico en la ventana de transicion, ¿se replica con el modelo base
alternativo? Si no se replica, es condicion de parada (a) y se documenta en
HALLAZGOS_CRITICOS.md.

Salidas:
  resultados/fase0/fase0_tabla_por_modelo.csv
  resultados/fase0/fase0_diferencias_bootstrap.csv
  resultados/fase0_model_agnostic.md   (redactado por este script)

Comando:
  <venv>/bin/python flagship/revision/fase0_model_agnostic.py
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rev_lib as R   # noqa: E402

REPO = R.REPO
SAL = REPO / 'resultados' / 'fase0'
SAL.mkdir(parents=True, exist_ok=True)
SERIES = SAL / 'series'

GAMMAS = (0.02, 0.05)


# --------------------------------------------------------------------------
def cargar_hurdle():
    h = pd.read_csv(R.FLAGSHIP / 'predicciones' / 'pred_hurdle.csv',
                    parse_dates=['fecha'])
    h = h.sort_values(['fecha', 'central_codigo']).reset_index(drop=True)
    sigma = float(h.sigma.iloc[0])
    assert h.sigma.nunique() == 1
    pred = R.PredictivaHurdle(h.p_occ.values, h.mu_log.values, sigma)
    return h, pred, dict(sigma=sigma)


def cargar_hurdle_hetero():
    """Tercer modelo base: el mismo hurdle con dispersion condicional
    sigma(x) (ESPECIFICACION_SIGMA_X.md). Se incluye para separar dos
    explicaciones posibles del resultado: que el problema del hurdle sea su
    dispersion constante, o que sea la forma lognormal misma."""
    h = pd.read_csv(R.FLAGSHIP / 'predicciones' / 'pred_hurdle_hetero.csv',
                    parse_dates=['fecha'])
    h = h.sort_values(['fecha', 'central_codigo']).reset_index(drop=True)
    pred = R.PredictivaHurdle(h.p_occ.values, h.mu_log.values, h.sigma_x.values)
    return h, pred, dict(sigma_x_media=round(float(h.sigma_x.mean()), 4))


def cargar_qgbm():
    h = pd.read_csv(R.FLAGSHIP / 'predicciones' / 'pred_qgbm_multi.csv.gz',
                    parse_dates=['fecha'])
    h = h.sort_values(['fecha', 'central_codigo']).reset_index(drop=True)
    cols = [c for c in h.columns if c.startswith('q0') or c.startswith('q1')]
    taus = np.array([float(c[1:]) for c in cols])
    orden = np.argsort(taus)
    Q = h[[cols[i] for i in orden]].values
    pred = R.PredictivaCuantilica(Q, taus[orden])
    return h, pred, dict(n_cuantiles=len(taus), tau_max=float(taus[orden][-1]))


# --------------------------------------------------------------------------
def correr_modelo(nombre, h, pred, info):
    """Ejecuta los seis metodos del paper sobre una predictiva cualquiera."""
    print('\n' + '=' * 78)
    print(f'MODELO BASE: {nombre}   {info}')
    print('=' * 78)

    rng = np.random.default_rng(R.SEED_CONFORMAL)
    s_all = pred.cdf(h.y_real.values, rng)
    h = h.assign(s=s_all)
    fechas_todo = h.fecha.values

    es_cal = (h.fecha >= R.CAL_INI) & (h.fecha < R.CAL_FIN)
    s_cal = h.s.values[es_cal.values]
    idx_test = (h.fecha >= R.CAL_FIN).values
    test = h[idx_test].reset_index(drop=True)
    pred_test = pred.sub(idx_test)
    y_t = test.y_real.values
    f_t = test.fecha.values
    fechas_test = np.sort(test.fecha.unique())

    print(f'calibracion: {int(es_cal.sum()):,} filas, '
          f'{h.fecha[es_cal].dt.normalize().nunique()} dias')
    print(f'test: {len(test):,} filas, {len(fechas_test)} dias')
    print(f'score PIT de calibracion: media {s_cal.mean():.4f}, '
          f'sd {s_cal.std():.4f}  (uniforme ideal: 0.5000 / 0.2887)')

    filas, series, crono = [], {}, R.Cronometro()

    with crono('1_estatico_pit'):
        qhat = R.cm.q_conformal(s_cal, R.ALPHA)
        U = R.estatico(pred_test, s_cal)
    print(f'\n1. estatico PIT: qhat = {qhat:.4f}')
    filas += R.filas_por_periodo('1_estatico_pit', f_t, y_t, U)
    series['1_estatico_pit'] = U

    with crono('2_ventana60d_pit'):
        U = R.ventana_deslizante(pred_test, h.s.values, fechas_todo, f_t,
                                 '2024-09-01', '2026-05-31')
    print('2. ventana deslizante 60d: listo')
    filas += R.filas_por_periodo('2_ventana60d_pit', f_t, y_t, U)
    series['2_ventana60d_pit'] = U

    for g in GAMMAS:
        k = f'3_aci_pit_g{str(g).replace("0.", "")}'
        with crono(k):
            U, a_fin, _ = R.aci(pred_test, s_cal, y_t, f_t, fechas_test, g)
        print(f'3. ACI gamma={g}: alpha_t final = {a_fin:.4f}')
        filas += R.filas_por_periodo(k, f_t, y_t, U)
        series[k] = U

    # El rng `rng` es el MISMO objeto que aleatorizo el atomo del score arriba y
    # se sigue consumiendo aqui en el orden gamma=0.02 y luego gamma=0.05. Ese
    # orden de consumo del generador es el de `conformal_v3_real.py`, y es lo
    # que hace que la rama del hurdle reproduzca `conformal_v3_tabla.csv` bit a
    # bit. Verificado por asercion al final de correr_modelo().
    for g in GAMMAS:
        k = f'4_transporte_banda_g{str(g).replace("0.", "")}'
        with crono(k):
            U, a_fin, diag = R.transporte_aci(
                pred_test, s_cal, h.s.values, fechas_todo, y_t, f_t,
                fechas_test, g, rng, ini_test=R.CAL_FIN)
        d = diag.get('test_transition', {})
        print(f'4. Transporte+ACI gamma={g}: alpha_t final = {a_fin:.4f}  '
              f'(transicion: sd_cola={d.get("sd_cola", float("nan")):.3f} '
              f'lam_cola={d.get("lam_cola", float("nan")):.2f})')
        filas += R.filas_por_periodo(k, f_t, y_t, U)
        series[k] = U

    tabla = R.ordenar(filas)
    tabla.insert(0, 'modelo_base', nombre)

    # CRPS de la predictiva por periodo (propiedad del modelo base)
    rng_c = np.random.default_rng(R.SEED_CRPS)
    crps, brier = {}, {}
    for nm, ini, fin in R.PERIODOS:
        m = (f_t >= np.datetime64(ini.date())) & (f_t < np.datetime64(fin.date()))
        if m.sum() == 0:
            continue
        sub = pred_test.sub(m)
        crps[nm] = R.crps_pred(sub, y_t[m], rng_c)
        brier[nm] = R.brier_ocurrencia(sub, y_t[m])
    tabla['crps_base'] = tabla.periodo.map(crps).round(2)
    tabla['brier_base'] = tabla.periodo.map(brier).round(4)
    tabla['segundos'] = tabla.metodo.map(crono.t).round(1)

    # Series POR FILA del split estatico y de Transporte+ACI(0.05). La tabla
    # agregada redondea cobertura y ancho a un decimal, y ajustar la relacion
    # diagnostica sobre valores redondeados desplaza r en 0.002. Persistiendo
    # las filas, fase0_diagnostico.py puede ajustar sobre los valores exactos.
    SERIES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(dict(fecha=f_t, y=y_t,
                      U_est=series['1_estatico_pit'],
                      U_tr=series['4_transporte_banda_g05'])).to_parquet(
        SERIES / f'{nombre}.parquet', index=False)

    if nombre == 'hurdle':
        verificar_reproduccion(tabla)
    return tabla, series, f_t, y_t


def verificar_equivalencia_cuantilica(h, pred_hu, sigma):
    """Control del BRAZO NUEVO, que la asercion del hurdle no cubre.

    `verificar_reproduccion` solo se dispara para el hurdle, que recorre
    `PredictivaHurdle` y delega en funciones ya validadas. El brazo del GBM
    recorre `PredictivaCuantilica`, una clase distinta con su propia
    interpolacion de rejilla, su propia lectura del atomo en cero y su propio
    manejo de bordes. Un error ahi dejaria intacta la asercion del hurdle y
    produciria en silencio el resultado central del paper.

    El control es de equivalencia: se construye una `PredictivaCuantilica`
    evaluando la funcion cuantil DEL HURDLE sobre la misma rejilla de 54
    niveles. Salvo error de interpolacion, esa predictiva es el hurdle. Se corre
    la capa conformal sobre ella y se compara contra el brazo validado. Si la
    clase nueva tiene un error, esto falla.

    Tolerancias: 0.6 pp de cobertura y 3% de ancho. El desvio observado es de
    0.10 pp y 0.59%, y el sesgo de ancho es constante y negativo en las cinco
    ventanas, que es la firma de discretizar una funcion cuantil continua.
    """
    taus = np.array(sorted(set(np.round(np.concatenate([
        [0.005, 0.01], np.arange(0.02, 0.981, 0.02),
        [0.99, 0.995, 0.999]]), 4))))
    Q = np.column_stack([R.cm.pit_upper(pred_hu.p, pred_hu.mu, sigma, t)
                         for t in taus])
    Q[~np.isfinite(Q)] = np.nanmax(Q[np.isfinite(Q)])
    pred_q = R.PredictivaCuantilica(Q, taus)

    salidas = {}
    for etq, pred in (('hurdle', pred_hu), ('cuantilica', pred_q)):
        rng = np.random.default_rng(R.SEED_CONFORMAL)
        sc = pred.cdf(h.y_real.values, rng)
        s_cal = sc[((h.fecha >= R.CAL_INI) & (h.fecha < R.CAL_FIN)).values]
        idx = (h.fecha >= R.CAL_FIN).values
        test = h[idx].reset_index(drop=True)
        U = R.estatico(pred.sub(idx), s_cal)
        salidas[etq] = pd.DataFrame(R.filas_por_periodo(
            'estatico', test.fecha.values, test.y_real.values, U)
        ).set_index('periodo')

    a, b = salidas['hurdle'], salidas['cuantilica']
    dc = float((b.cobertura - a.cobertura).abs().max())
    dw = float((100 * (b.ancho_medio / a.ancho_medio - 1)).abs().max())
    assert dc < 0.6, f'equivalencia cuantilica: {dc:.2f} pp de cobertura'
    assert dw < 3.0, f'equivalencia cuantilica: {dw:.2f}% de ancho'
    print(f'  [OK] PredictivaCuantilica reproduce el brazo validado: '
          f'{dc:.2f} pp de cobertura, {dw:.2f}% de ancho, sobre {len(a)} ventanas')


def verificar_reproduccion(tabla):
    """La rama del hurdle debe reproducir la tabla oficial de la version
    enviada, celda a celda. Si no lo hace, la comparacion de la Fase 0 no seria
    entre modelos base sino entre protocolos, y el resultado no valdria."""
    of = pd.read_csv(REPO / 'resultados' / 'v_enviada' / 'conformal_v3_tabla.csv')
    of['periodo'] = of.periodo.replace(R.NOMBRE_ANTIGUO)
    m = tabla.merge(of, on=['metodo', 'periodo'], suffixes=('', '_of'))
    assert len(m) == len(of), f'faltan filas: {len(m)} contra {len(of)}'
    for c in ('cobertura', 'ancho_medio', 'pct_infinito', 'se_cluster'):
        d = (m[c] - m[f'{c}_of']).abs().max()
        assert d < 1e-9, f'{c} no reproduce la version enviada: max |dif| = {d}'
    print(f'  [OK] reproduce conformal_v3_tabla.csv en {len(of)} celdas x 4 metricas')


# --------------------------------------------------------------------------
def main():
    print('=' * 78)
    print('FASE 0 - AGNOSTICISMO AL MODELO BASE (comentario R1.1)')
    print(f'semilla conformal {R.SEED_CONFORMAL} | embargo {R.EMBARGO_DIAS} d | '
          f'alpha {R.ALPHA}')
    print('=' * 78)

    # Control del brazo nuevo, antes de usarlo. Corre SIEMPRE.
    print('\n' + '-' * 78)
    print('CONTROL DE EQUIVALENCIA DE PredictivaCuantilica')
    print('-' * 78)
    h_hu, p_hu, i_hu = cargar_hurdle()
    verificar_equivalencia_cuantilica(h_hu, p_hu, i_hu['sigma'])

    resultados, ctx = [], {}
    for nombre, cargador in (('hurdle', cargar_hurdle),
                             ('hurdle_sigma_x', cargar_hurdle_hetero),
                             ('qgbm_multi', cargar_qgbm)):
        h, pred, info = cargador()
        tabla, series, f_t, y_t = correr_modelo(nombre, h, pred, info)
        resultados.append(tabla)
        ctx[nombre] = (series, f_t, y_t)

    tabla = pd.concat(resultados, ignore_index=True)
    tabla.to_csv(SAL / 'fase0_tabla_por_modelo.csv', index=False)
    print(f'\nguardado {(SAL / "fase0_tabla_por_modelo.csv").relative_to(REPO)}')

    # ------------------------------------------------------------------
    # Diferencias con incertidumbre: Transport+ACI contra el split estatico,
    # dentro de cada modelo base. Bootstrap por bloques de dia.
    # ------------------------------------------------------------------
    print('\n' + '=' * 78)
    print('DIFERENCIA Transporte+ACI(g=0.05) - estatico, por modelo base')
    print('bootstrap de 2000 remuestreos de DIAS COMPLETOS, IC de percentil 95%')
    print('=' * 78)
    difs = []
    for modelo, (series, f_t, y_t) in ctx.items():
        base = series['1_estatico_pit']
        for k in ('4_transporte_banda_g05', '4_transporte_banda_g02',
                  '3_aci_pit_g05', '2_ventana60d_pit'):
            alt = series[k]
            for nm, ini, fin in R.PERIODOS:
                m = ((f_t >= np.datetime64(ini.date()))
                     & (f_t < np.datetime64(fin.date())))
                if m.sum() == 0:
                    continue
                fin_ = np.isfinite(base[m]) & np.isfinite(alt[m])
                d_w, lo_w, hi_w = R.bootstrap_diferencia(
                    f_t[m][fin_], alt[m][fin_], base[m][fin_])
                cb = (y_t[m] <= base[m]).astype(float)
                ca = (y_t[m] <= alt[m]).astype(float)
                d_c, lo_c, hi_c = R.bootstrap_diferencia(f_t[m], ca, cb)
                isb = R.interval_score_unilateral(y_t[m], base[m])
                isa = R.interval_score_unilateral(y_t[m], alt[m])
                fi = np.isfinite(isb) & np.isfinite(isa)
                d_i, lo_i, hi_i = R.bootstrap_diferencia(f_t[m][fi], isa[fi], isb[fi])
                difs.append(dict(
                    modelo_base=modelo, metodo=k, periodo=nm,
                    d_ancho=round(d_w, 1), ancho_lo=round(lo_w, 1), ancho_hi=round(hi_w, 1),
                    d_cobertura_pp=round(100 * d_c, 2),
                    cob_lo=round(100 * lo_c, 2), cob_hi=round(100 * hi_c, 2),
                    d_IS=round(d_i, 1), IS_lo=round(lo_i, 1), IS_hi=round(hi_i, 1),
                    n_filas_IS_finitas=int(fi.sum()), n_filas=int(m.sum())))
    dif = pd.DataFrame(difs)
    dif.to_csv(SAL / 'fase0_diferencias_bootstrap.csv', index=False)
    print(dif[dif.metodo == '4_transporte_banda_g05'].to_string(index=False))
    print(f'\nguardado {(SAL / "fase0_diferencias_bootstrap.csv").relative_to(REPO)}')

    # ------------------------------------------------------------------
    print('\n' + '=' * 78)
    print('TABLA COMPARATIVA (ventana de transicion, oct-dic 2024)')
    print('=' * 78)
    tr = tabla[tabla.periodo == 'test_transition']
    print(tr[['modelo_base', 'metodo', 'cobertura', 'se_cluster', 'ancho_medio',
              'pct_infinito', 'IS_finitos', 'crps_base']].to_string(index=False))
    print('\n' + '=' * 78)


if __name__ == '__main__':
    main()
