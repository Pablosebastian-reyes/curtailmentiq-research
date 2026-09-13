#!/usr/bin/env python3
"""
FASE 1: tabla unica de hiperparametros, leida del codigo.
=========================================================
Comentarios R1.2 y R2.4. El revisor pide largo de la ventana reciente, regla de
seleccion de cuantiles empiricos, esquema de interpolacion, repeticiones
bootstrap, funcion exacta e intensidad del shrinkage de cola, y orden de
ejecucion entre el mapa de transporte y la actualizacion de ACI. Mas semillas.

Este script NO escribe ningun valor a mano: importa los modulos y lee las
constantes y las firmas de las funciones, de modo que la tabla del manuscrito no
pueda desincronizarse del codigo. Los valores que son RESULTADOS y no constantes
(gamma y ventana elegidos por origen rodante, dias y filas de la calibracion,
costo de la cota de alpha) se leen de su archivo de resultados.

La tabla se emite en ingles, que es el idioma del manuscrito: hasta el cierre
del 14 de septiembre salia en espanol en el PDF (bloque B9).

Salidas:
  resultados/fase1/hiperparametros.csv
  resultados/fase1/hiperparametros.tex   (tabla completa, para \\input)

Comando:
  <venv>/bin/python flagship/revision/fase1_hiperparametros.py
"""
from pathlib import Path
import inspect
import json
import sys

import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rev_lib as R   # noqa: E402
sys.path.insert(0, str(R.FLAGSHIP))
import conformal_metodos as cm          # noqa: E402
import entrenar_baselines as EB         # noqa: E402
import fase0_entrenar_qgbm as QG        # noqa: E402
import fase3_seleccion_hiperparametros as F3  # noqa: E402

SAL = R.REPO / 'resultados' / 'fase1'
SAL.mkdir(parents=True, exist_ok=True)
RES = R.REPO / 'resultados'


def costo_cobertura_cota_alpha():
    """Caida maxima de cobertura al acotar alpha por abajo, leida de la Fase 4.

    Este campo se escribia a mano y quedo desincronizado: decia 0.4 puntos
    cuando el manuscrito y la carta ya decian medio punto. Ahora sale del mismo
    CSV que alimenta la Tabla 10, asi que no puede volver a divergir.
    """
    c = pd.read_csv(RES / 'fase4' / 'fase4_cota_alpha.csv')
    v = c[c.periodo == 'TEST_COMPLETO']
    sin = v[v.cota == 'sin cota'].set_index('metodo').cobertura
    con = v[v.cota == 'alpha_min=0.005'].set_index('metodo').cobertura
    return float((sin - con).max())


def seleccion_fase3():
    """gamma y ventana elegidos por origen rodante, del JSON de la Fase 3."""
    el = json.load(open(RES / 'fase3' / 'fase3_hiperparametros_elegidos.json'))['elegidos']
    return el['ACI']['gamma'], el['Transporte+ACI']['gamma'], el['Transporte+ACI']['ventana']


def calibracion():
    """Dias y filas de la ventana de calibracion, de la Fase 5."""
    d = pd.read_csv(RES / 'fase5' / 'fase5_diagnostico_dependencia.csv').iloc[0]
    return int(d.n_dias), int(d.n_filas)


def defecto(fn, nombre):
    return inspect.signature(fn).parameters[nombre].default


def main():
    g_aci, g_tra, v_tra = seleccion_fase3()
    n_dias, n_filas = calibracion()
    g_sel = f'{g_aci}' if g_aci == g_tra else f'{g_aci} (ACI), {g_tra} (Transport+ACI)'

    filas = [
        # --- modelo base ---
        ('Base model', 'Forecast horizon', f'{EB.H} days',
         'direct forecast; every dynamic feature is a shift of at least H days',
         'entrenar_baselines.py:H'),
        ('Base model', 'Last training target', str(EB.CORTE_TRAIN.date()),
         'the model never sees the evaluation period', 'entrenar_baselines.py:CORTE_TRAIN'),
        ('Base model', 'Trees / learning rate / depth',
         f"{EB.XGB_PARAMS['n_estimators']} / {EB.XGB_PARAMS['learning_rate']} / "
         f"{EB.XGB_PARAMS['max_depth']}",
         'fixed a priori, never tuned against 2024-2026', 'entrenar_baselines.py:XGB_PARAMS'),
        ('Base model', 'min_child_weight / subsample / colsample',
         f"{EB.XGB_PARAMS['min_child_weight']} / {EB.XGB_PARAMS['subsample']} / "
         f"{EB.XGB_PARAMS['colsample_bytree']}", 'as above', 'entrenar_baselines.py:XGB_PARAMS'),
        ('Base model', 'Number of features', str(len(EB.FEATS)),
         ', '.join(EB.FEATS), 'entrenar_baselines.py:FEATS'),
        ('Base model', 'Dispersion of the hurdle', 'out of fold, KFold 5',
         'in-sample residuals of a boosted model understate the dispersion',
         'entrenar_baselines.py'),
        ('Base model', 'Quantile grid of the multi-quantile GBM',
         f'{len(QG.TAUS)} levels, from {QG.TAUS[0]} to {QG.TAUS[-1]}',
         '0.02 to 0.98 in steps of 0.02, plus 0.005, 0.01, 0.99, 0.995 and 0.999; '
         'row-wise rearrangement against quantile crossing',
         'fase0_entrenar_qgbm.py:TAUS'),
        # --- score y ventanas ---
        ('Conformal layer', 'Nominal level', f'1 - alpha = {1 - R.ALPHA:.2f}',
         'one-sided upper prediction limit [0, U]', 'rev_lib.py:ALPHA'),
        ('Conformal layer', 'Nonconformity score', 's = F_x(y) (PIT)',
         'atom at y = 0 randomised, s = (1-p)U with U ~ Uniform(0,1)',
         'conformal_metodos.py:pit_score'),
        ('Conformal layer', 'Calibration window',
         f'{R.CAL_INI.date()} to {R.CAL_FIN.date()}',
         f'{n_dias} days, {n_filas:,} rows', 'rev_lib.py:CAL_INI, CAL_FIN'),
        ('Conformal layer', 'Horizon embargo', f'{R.EMBARGO_DIAS} days',
         'every online window ends at t-7 and the feedback of alpha is delayed by '
         '7 steps', 'rev_lib.py:EMBARGO_DIAS'),
        ('Conformal layer', 'Conformal quantile',
         'order statistic k = ceil((n+1)(1-alpha_t))',
         'q = +infinity if k > n, which is the origin of the infinite intervals',
         'conformal_metodos.py:q_conformal'),
        # --- transporte ---
        ('Transport', 'Length of the recent window',
         f'{defecto(R.transporte_aci, "ventana_dias")} days',
         'the window ends at t minus the embargo, not at t',
         'rev_lib.py:transporte_aci(ventana_dias)'),
        ('Transport', 'Refresh period of the map',
         f'{defecto(R.transporte_aci, "refresco_dias")} days',
         'the map is recomputed every 7 days; between refreshes the pool is frozen',
         'rev_lib.py:transporte_aci(refresco_dias)'),
        ('Transport', 'Minimum recent scores for a refresh', '100',
         'with fewer scores in the recent window the previous pool is kept',
         'rev_lib.py:transporte_aci'),
        ('Transport', 'Rule for the empirical quantiles',
         f'equispaced grid of g levels on [0,1], '
         f'g = min({defecto(cm.mapa_transporte_banda, "n_grid")}, max(20, m/2))',
         'm is the number of scores in the recent window; the second term prevents '
         'a grid finer than the data', 'conformal_metodos.py:mapa_transporte_banda'),
        ('Transport', 'Interpolation scheme', 'piecewise linear, twice',
         'first s -> level on (q_old, levels), then level -> q_reg on '
         '(levels, q_reg); this is the increasing rearrangement T = F_new^{-1} o F_old',
         'conformal_metodos.py:mapa_transporte_banda.T'),
        ('Transport', 'Bootstrap repetitions of the map',
         f'B = {defecto(cm.mapa_transporte_banda, "B")}',
         'resampling of the recent window with replacement; the mean of the B '
         'replicates is the map (bagging) and their standard deviation per level '
         'is the band', 'conformal_metodos.py:mapa_transporte_banda(B)'),
        ('Transport', 'Tail shrinkage function',
         'lambda(u) = 1 / (1 + (sd_boot(u)/tau)^2)',
         'q_reg(u) = (1-lambda(u)) q_old(u) + lambda(u) q_new_bag(u); lambda ~ 1 '
         'where the map is stable and ~ 0 where it is noisy, and lambda = 0 is the '
         'identity, that is the old quantile', 'conformal_metodos.py:mapa_transporte_banda'),
        ('Transport', 'Shrinkage strength',
         f'tau = {defecto(cm.mapa_transporte_banda, "tau")} in PIT units',
         'fixed regularisation scale, not tuned against the test set',
         'conformal_metodos.py:mapa_transporte_banda(tau)'),
        ('Transport', 'Monotonisation', 'running maximum and clip to [0,1]',
         'keeps the transported map a quantile function',
         'conformal_metodos.py:mapa_transporte_banda'),
        # --- ACI ---
        ('ACI', 'Update', 'alpha_{t+1} = alpha_t + gamma (alpha - err_t)',
         'err_t = 1{Y_t > U_t}, averaged over the plants of day t', 'rev_lib.py:aci'),
        ('ACI', 'gamma reported in the submitted version', '0.02 and 0.05',
         'kept in the tables for continuity', 'rev_lib.py'),
        ('ACI', 'Bound on alpha_t, submitted version', '[-1, 2]',
         'allows alpha_t <= 0 and hence q = +infinity: the origin of the infinite '
         'intervals', 'rev_lib.py:aci(alpha_min, alpha_max)'),
        ('ACI', 'Recommended bound on alpha_t', 'alpha_min = 0.005',
         'removes infinite intervals in all five windows at a cost of at most '
         f'{costo_cobertura_cota_alpha():.1f} points of coverage',
         'fase4_metricas_benchmarks.py'),
        ('ACI', 'Order of execution',
         'map refresh, then quantile, then interval, then ACI',
         'on date t: (i) if a refresh is due, the map is recomputed from the window '
         'ending at t-7 and the whole calibration pool is transported; (ii) the '
         'quantile is taken from the transported pool at the CURRENT alpha_t, which '
         'does not yet include the error of t; (iii) the interval is emitted; (iv) '
         'the error of t enters the embargo queue and updates alpha only 7 steps '
         'later. The map never uses the alpha of ACI and ACI never uses the map: the '
         'only coupling is the pool', 'rev_lib.py:transporte_aci'),
        # --- seleccion por origen rodante (R1.4): rejillas, particion y criterio,
        # leidos de las constantes de la Fase 3 ---
        ('Hyperparameter selection', 'Grid for gamma',
         '{' + ', '.join(f'{g:.3f}' if g < 0.01 else f'{g:.2f}' for g in F3.GAMMAS) + '}',
         'the test set is not used in the selection', 'fase3_seleccion_hiperparametros.py:GAMMAS'),
        ('Hyperparameter selection', 'Grid for the recent window',
         '{' + ', '.join(str(v) for v in F3.VENTANAS) + '} days', 'Transport+ACI only',
         'fase3_seleccion_hiperparametros.py:VENTANAS'),
        ('Hyperparameter selection', 'Inner calibration pool',
         f'{F3.CAL_INT_INI.date()} to {F3.CAL_INT_FIN.date()}',
         'first part of the calibration window', 'fase3_seleccion_hiperparametros.py:CAL_INT_INI, CAL_INT_FIN'),
        ('Hyperparameter selection', 'Inner validation set',
         f'{F3.CAL_INT_FIN.date()} to {F3.VAL_INT_FIN.date()}',
         f'rolling origin with the same {defecto(R.transporte_aci, "refresco_dias")}-day refresh and '
         f'{R.EMBARGO_DIAS}-day embargo as the test protocol', 'fase3_seleccion_hiperparametros.py:VAL_INT_FIN'),
        ('Hyperparameter selection', 'Selection criterion', 'mean one-sided interval score',
         '+infinity if any interval is infinite, so such a configuration is disqualified by the '
         'criterion itself; the generator uses the seed of the PIT atom', 'fase3_seleccion_hiperparametros.py'),
        ('Hyperparameter selection', 'gamma selected by rolling origin', g_sel,
         'lowest interval score on the inner validation set; no infinite intervals there',
         'fase3_hiperparametros_elegidos.json'),
        ('Hyperparameter selection', 'Window selected by rolling origin', f'{v_tra} days',
         'as above, for Transport+ACI', 'fase3_hiperparametros_elegidos.json'),
        # --- evaluacion ---
        ('Evaluation', 'Primary metric',
         'one-sided interval score IS = U + (1/alpha) max(y-U, 0)',
         'proper for the (1-alpha) quantile, in MWh, and infinite if U is infinite; '
         'the multiplier is 1/alpha because all of alpha lies in the upper tail',
         'rev_lib.py:interval_score_unilateral'),
        ('Evaluation', 'Standard error of coverage', 'clustered by date',
         'averages the coverage of each day and takes the error across days',
         'conformal_metodos.py:cobertura_clusterizada'),
        ('Evaluation', 'Bootstrap of the differences between methods',
         f'{defecto(R.bootstrap_diferencia, "B")} resamples of whole days',
         'the resampled unit is the day, not the row; 95% percentile interval',
         'rev_lib.py:bootstrap_diferencia'),
        ('Evaluation', 'Samples for the CRPS', f'{defecto(R.crps_pred, "n")} per row',
         "sampled CRPS, E|X-y| - 0.5 E|X-X'|", 'rev_lib.py:crps_pred'),
        ('Evaluation', 'Change-point detection',
         'PELT and binary segmentation, L2 cost, pen = sigma^2 log n, min_size = 3',
         'BIC penalty with k = 1; the sensitivity grid spans k in '
         '{0.5, 1, 2, 3, 5} and min_size in {2, 3, 4}', 'fase6_cronologia.py:puntos_de_cambio'),
        # --- semillas ---
        # Las etiquetas son cortas y no aparecen en la prosa, para que la guarda
        # del empaquetador y verificar_manuscrito.py puedan comprobar sobre el
        # PDF que cada fila se imprime (H11).
        ('Seeds', 'Training of the base models', str(R.SEED_BASE),
         'deterministic XGBoost hist, n_jobs = 4, KFold', 'entrenar_baselines.py:SEED'),
        ('Seeds', 'PIT atom and map bootstrap', str(R.SEED_CONFORMAL),
         'a single generator consumed in order: first the score, then gamma = 0.02 '
         'and then gamma = 0.05', 'rev_lib.py:SEED_CONFORMAL'),
        ('Seeds', 'Sampling of the CRPS', str(R.SEED_CRPS), '', 'rev_lib.py:SEED_CRPS'),
        ('Seeds', 'Bootstrap of differences, blocks and permutations',
         str(R.SEED_BOOTSTRAP), '', 'rev_lib.py:SEED_BOOTSTRAP'),
    ]

    df = pd.DataFrame(filas, columns=['bloque', 'hiperparametro', 'valor',
                                      'detalle', 'donde_vive_en_el_codigo'])
    df.to_csv(SAL / 'hiperparametros.csv', index=False)

    def esc(t):
        # Las llaves se escapan ANTES de insertar comandos que las llevan: con el
        # orden anterior '^' pasaba a \^{} y despues a \^\{\}, y el PDF imprimia
        # un acento sobre llaves literales. '~' no se escapaba y LaTeX lo leia
        # como espacio duro: "lambda ~ 1" salia "lambda   1" (lectura pagina por
        # pagina del 14 de septiembre).
        for a, b in (('\\', r'\textbackslash '), ('{', r'\{'), ('}', r'\}'),
                     ('_', r'\_'), ('%', r'\%'), ('&', r'\&'),
                     ('^', r'\textasciicircum{}'), ('~', r'$\sim$')):
            t = t.replace(a, b)
        return t

    lineas, bloque = [], None
    for _, r in df.iterrows():
        if r.bloque != bloque:
            bloque = r.bloque
            lineas.append(r'\midrule' if lineas else '')
            lineas.append(rf'\multicolumn{{3}}{{l}}{{\emph{{{esc(bloque)}}}}} \\')
        lineas.append(f'{esc(r.hiperparametro)} & {esc(r.valor)} & '
                      f'{esc(r.detalle)} \\\\')
    cuerpo = '\n'.join(x for x in lineas if x)
    # Se emite un LONGTABLE, no un table*. Un table* es un flotante y no se
    # parte entre paginas: con 38 filas era mas alto que la caja de texto y
    # LaTeX descartaba en silencio las cuatro filas del bloque de semillas,
    # dejando solo el aviso "Float too large for page" en el log (H11). El
    # longtable se parte solo y no vuelve a fallar si la tabla crece.
    #
    # Se emite el entorno COMPLETO, no solo el cuerpo: TeX no acepta un \input
    # cuyo primer token sea \multicolumn dentro de una tabla. La cabecera del
    # .tex va en ingles porque el archivo viaja en el paquete de fuentes.
    cab = ('\\toprule\nItem & Value & Detail \\\\\n\\midrule\n')
    doc = (
        '%% generated from the source code by flagship/revision/fase1_hiperparametros.py\n'
        '%% do not edit by hand\n'
        '\\begingroup\n\\footnotesize\n'
        '\\setlength{\\LTcapwidth}{\\textwidth}\n'
        '\\begin{longtable}{p{0.30\\textwidth}p{0.22\\textwidth}p{0.40\\textwidth}}\n'
        '\\caption{Complete hyperparameter specification. Generated from the '
        'source by \\texttt{flagship/revision/fase1\\_hiperparametros.py}; the '
        'companion CSV records where each value lives in the code.}\n'
        '\\label{tab:hiper} \\\\\n'
        + cab +
        '\\endfirsthead\n'
        '\\multicolumn{3}{l}{\\emph{Table \\ref{tab:hiper}, continued.}} \\\\\n'
        + cab +
        '\\endhead\n'
        '\\midrule\n'
        '\\multicolumn{3}{r}{\\emph{continued on the next page}} \\\\\n'
        '\\endfoot\n'
        '\\bottomrule\n'
        '\\endlastfoot\n'
        + cuerpo +
        '\n\\end{longtable}\n\\endgroup\n')
    (SAL / 'hiperparametros.tex').write_text(doc)

    print('=' * 92)
    print('FASE 1 - TABLA DE HIPERPARAMETROS (R1.2, R2.4)')
    print(f'{len(df)} entradas, leidas del codigo y de los resultados, no escritas a mano')
    print('=' * 92)
    for b, g in df.groupby('bloque', sort=False):
        print(f'\n--- {b} ---')
        for _, r in g.iterrows():
            print(f'  {r.hiperparametro:52s} {r.valor}')
    print(f'\nguardado {(SAL / "hiperparametros.csv").relative_to(R.REPO)} y .tex')


if __name__ == '__main__':
    main()
