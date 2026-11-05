#!/usr/bin/env python3
"""
R2-08. Ablaciones por modelo base y TODAS las tablas LaTeX de la R2.

Primero calcula las contribuciones de cada componente (como la Fase 2 de la R1,
ahora para tres modelos base) y despues escribe en manuscrito/ cada tabla a
partir de los archivos de resultados. Ninguna cifra se transcribe a mano.

Las tablas de la R1 cuyo contenido no cambia (descomposicion estacional,
sensibilidad de la frontera, rejilla gamma x ventana, esquemas de panel) se
copian de las fuentes de la R1 con sus leyendas limpias de referencias a
versiones anteriores y a rutas de archivos.
"""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_lib as L                      # noqa: E402
import numpy as np                      # noqa: E402
import pandas as pd                     # noqa: E402
R = L.R

MAN = L.R2 / 'manuscrito'
BASE_R1 = L.R2 / 'base_r1' / 'fuentes'
ETQ = {'hurdle_800': 'Reference hurdle (2$\\times$400 trees)',
       'hurdle_es': 'Early-stopped hurdle (105 trees)',
       'hurdle_sigma_x': 'Hurdle with $\\sigma(x)$',
       'qgbm_54x400': 'Reference quantile GBM (54$\\times$400)'}
MET = {'static': 'Static split (PIT)', 'sw60': 'Sliding window, 60 d',
       'aci_g05': 'ACI ($\\gamma=0.05$)', 'tr_g05': 'Transport+ACI ($\\gamma=0.05$)',
       'aci_sel': 'ACI (selected $\\gamma$)', 'tr_sel': 'Transport+ACI (selected)',
       'aci_g05_amin005': 'ACI ($\\gamma=0.05$, $\\alpha_{\\min}=0.005$)',
       'tr_g05_amin005': 'Transport+ACI ($\\gamma=0.05$, $\\alpha_{\\min}=0.005$)',
       'cqr': 'One-sided CQR'}

NOMBRE = {'hurdle_800': 'reference hurdle', 'hurdle_es': 'early-stopped hurdle',
          'hurdle_sigma_x': 'hurdle with $\\sigma(x)$', 'hurdle_2000': 'hurdle 2$\\times$2000',
          'qgbm_54x15': 'quantile GBM 54$\\times$15', 'qgbm_54x50': 'quantile GBM 54$\\times$50',
          'qgbm_54x100': 'quantile GBM 54$\\times$100', 'qgbm_54x200': 'quantile GBM 54$\\times$200',
          'qgbm_54x400': 'reference quantile GBM'}


def f(v, d=1):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return '--'
    if np.isinf(v):
        return '$\\infty$'
    return f'{v:.{d}f}'


def cov(c, se):
    return f'{c:.1f}\\,({se:.2f})'


def escribir(nombre, cuerpo):
    (MAN / f'{nombre}.tex').write_text(cuerpo)
    L.log(f'tabla {nombre}', 'r2_08_tablas.log')


# ==========================================================================
# Ablaciones
# ==========================================================================
COMPONENTES = [('Online adaptation (ACI over static)', 'aci_g05', 'static'),
               ('Transport alone (over static)', 'ab_tr_fijo', 'static'),
               ('Transport added to ACI', 'ab_tr_sinshrink_g05', 'aci_g05'),
               ('Tail shrinkage added to transport', 'tr_g05', 'ab_tr_sinshrink_g05'),
               ('Full scheme (over static)', 'tr_g05', 'static')]


def ablaciones():
    ft = L.RES / 'r2_13_tiempos.csv'   # tiempos limpios si existen
    tiempos = pd.read_csv(ft if ft.exists() else L.RES / 'r2_02_tiempos.csv')
    filas = []
    for b in L.PRINCIPALES:
        S = pd.read_parquet(L.SERIES_DIR / f'{b}.parquet')
        f_t, y = S.fecha.values, S.y.values
        tb = tiempos[tiempos.brazo == b].set_index('componente').segundos
        seg = {'aci_g05': tb.get('aci_g05', np.nan), 'ab_tr_fijo': tb.get('ab_tr_fijo', np.nan),
               'ab_tr_sinshrink_g05': tb.get('ab_tr_sinshrink_g05', np.nan),
               'tr_g05': tb.get('tr_g05', np.nan), 'static': tb.get('static', 0.0)}
        for etq, a, c in COMPONENTES:
            for per, ini, fin in L.PER_TODOS:
                m = L.mascara(f_t, ini, fin)
                ia = R.interval_score_unilateral(y[m], S[a].values[m])
                ib = R.interval_score_unilateral(y[m], S[c].values[m])
                fi = np.isfinite(ia) & np.isfinite(ib)
                d, lo, hi = R.bootstrap_diferencia(f_t[m][fi], ia[fi], ib[fi])
                filas.append(dict(brazo=b, componente=etq, periodo=per, d_IS=d, lo=lo, hi=hi,
                                  significativo=bool(lo * hi > 0),
                                  d_segundos=seg[a] - seg[c] if etq != 'Tail shrinkage added to transport'
                                  else seg[a] - seg['ab_tr_sinshrink_g05']))
    A = pd.DataFrame(filas)
    A.to_csv(L.RES / 'r2_08_ablaciones.csv', index=False)
    # control contra la Tabla 8 de la R1 (hurdle de referencia, test completo)
    r1 = pd.read_csv(L.REPO / 'resultados/fase2/fase2_aporte_por_componente.csv')
    r1 = r1[r1.periodo == 'TEST_COMPLETO'].d_IS.values
    aqui = A[(A.brazo == 'hurdle_800') & (A.periodo == 'TEST_COMPLETO')].d_IS.values
    L.log(f'control ablaciones vs R1: R1 {np.round(r1, 1)} | R2 {np.round(aqui, 1)}', 'r2_08_tablas.log')
    assert np.allclose(np.round(aqui, 1), r1, atol=0.11), (aqui, r1)
    return A


# ==========================================================================
# Tablas principales
# ==========================================================================
def tab_mae():
    t = (BASE_R1 / 'tab_mae.tex').read_text()
    t = re.sub(r' Computed from \\texttt\{[^}]*\}\.', '', t)
    j = json.load(open(L.REPO / 'resultados/verificacion/obj1e_mae_hurdle_es.json'))
    e = j['mae_hurdle_es']
    fila = (f"Hurdle, early stopping (mixture median) & {e['2024']:.1f} & {e['2025']:.1f} & "
            f"{e['2026']:.1f} & {e['total']:.1f} \\\\\n")
    t = t.replace('\\bottomrule', fila + '\\bottomrule', 1)
    escribir('tab_mae', t)


def tab_estacional():
    t = (BASE_R1 / 'tab_estacional.tex').read_text()
    t = re.sub(r' Generated from \\texttt\{[^}]*\}\.', '', t)
    escribir('tab_estacional', t)


def tab_modelos():
    M = pd.read_csv(L.RES / 'r2_02_metricas.csv')
    B = pd.read_csv(L.RES / 'r2_02_base.csv')
    mets = ['static', 'sw60', 'aci_g05', 'tr_g05', 'aci_sel', 'tr_sel', 'cqr']
    difs = {}
    for b_ in L.PRINCIPALES:
        S_ = pd.read_parquet(L.SERIES_DIR / f'{b_}.parquet')
        ist = R.interval_score_unilateral(S_.y.values, S_['static'].values)
        for m_ in mets:
            if m_ == 'static' or m_ not in S_:
                continue
            ism = R.interval_score_unilateral(S_.y.values, S_[m_].values)
            fi = np.isfinite(ism) & np.isfinite(ist)
            difs[(b_, m_)] = R.bootstrap_diferencia(S_.fecha.values[fi], ism[fi], ist[fi])
    out = ['\\begin{table*}[tp]', '\\centering', '\\footnotesize',
           '\\caption{Calibration layers over the three main base models, nominal level 90\\%. Coverage in per cent '
           'with the date-clustered standard error, mean width over finite limits (MWh), one-sided interval score '
           'over finite limits (MWh) and fraction of infinite limits (\\%). In the whole-test interval score, an '
           'asterisk marks a method with infinite limits, whose unrestricted score is infinite. CRPS and twCRPS are '
           'those of the base predictive (MWh); the twCRPS weights the region above each plant\'s calibration-window '
           '90th percentile. $\\Delta$IS: difference in whole-test interval score from the static split on the same base '
           'model, with a 95\\% day-block bootstrap interval, on plant-days where both limits are finite. No limit is '
           'infinite in the transition window. The selected configurations come from rolling-origin validation inside '
           'the calibration window (\\ref{app:hiper}).}',
           '\\label{tab:modelos}',
           '\\setlength{\\tabcolsep}{4pt}',
           '\\begin{tabular}{l rrr rrrrl}', '\\toprule',
           ' & \\multicolumn{3}{c}{Transition window (Oct--Dec 2024)} & \\multicolumn{5}{c}{Whole test (Sep 2024--May 2026)} \\\\',
           '\\cmidrule(lr){2-4}\\cmidrule(lr){5-9}',
           'Method & Coverage & Width & IS & Coverage & Width & IS & \\% inf. & $\\Delta$IS vs. static [95\\% CI] \\\\', '\\midrule']
    for b in L.PRINCIPALES:
        bb = B[B.brazo == b].set_index('periodo')
        out.append(f'\\multicolumn{{9}}{{l}}{{\\textit{{{ETQ[b]}}}: CRPS {bb.loc["test_transition", "crps"]:.1f} / '
                   f'{bb.loc["TEST_COMPLETO", "crps"]:.1f}, twCRPS {bb.loc["test_transition", "twcrps"]:.1f} / '
                   f'{bb.loc["TEST_COMPLETO", "twcrps"]:.1f}}} \\\\')
        for m in mets:
            r = M[(M.brazo == b) & (M.metodo == m)].set_index('periodo')
            if r.empty:
                continue
            t, w = r.loc['test_transition'], r.loc['TEST_COMPLETO']
            ast = '$^\\ast$' if w.pct_infinito > 0 else ''
            assert t.pct_infinito == 0, (b, m)
            if m == 'static':
                dtxt = '--'
            else:
                d_, lo_, hi_ = difs[(b, m)]
                dtxt = f'{d_:+.1f} [{lo_:+.1f}, {hi_:+.1f}]'.replace('-', '$-$')
            out.append(f'\\quad {MET[m]} & {cov(t.cobertura, t.se_cluster)} & {f(t.ancho_medio, 0)} & '
                       f'{f(t.IS_finitos, 0)} & {cov(w.cobertura, w.se_cluster)} & '
                       f'{f(w.ancho_medio, 0)} & {f(w.IS_finitos, 0)}{ast} & {f(w.pct_infinito)} & {dtxt} \\\\')
    out += ['\\bottomrule', '\\end{tabular}', '\\end{table*}', '']
    escribir('tab_modelos', '\n'.join(out))


def tab_mecanico():
    res = json.load(open(L.RES / 'r2_03_resumen.json'))
    nom = {'tr_g05': 'Transport+ACI, $\\gamma=0.05$',
           'tr_g05_amin005': 'Transport+ACI, $\\gamma=0.05$, $\\alpha_{\\min}=0.005$',
           'aci_g05_amin005': 'ACI, $\\gamma=0.05$, $\\alpha_{\\min}=0.005$',
           'tr_sel': 'Transport+ACI, selected', 'aci_sel': 'ACI, selected'}
    out = ['\\begin{table*}[tp]', '\\centering', '\\footnotesize',
           '\\caption{How much of the adaptive width change is mechanical. For each adaptive configuration, the '
           'cross-cell regression of the width change on the static over-coverage (observed), the same regression '
           'for the constant-threshold oracle that attains the adaptive layer\'s coverage (mechanical), the share '
           'of the variance of the observed change explained by the mechanical one, and the mean residual. 40 cells: '
           'eight base models by five windows; 45 cells: the same plus the early-stopped hurdle. Intervals are 95\\% '
           'day-block bootstrap intervals, recomputing every cell on each of 2{,}000 replicates.}',
           '\\label{tab:mecanico}',
           '\\setlength{\\tabcolsep}{4pt}',
           '\\begin{tabular}{l c l l c l c}', '\\toprule',
           ' & & Observed & Mechanical & & & \\\\',
           'Configuration & Cells & slope (\\%/pp) & slope (\\%/pp) & $R^2$ & Mean residual (\\%) & $r$(res., OC) \\\\', '\\midrule']
    for conf in ('tr_g05', 'tr_g05_amin005', 'aci_g05_amin005', 'tr_sel', 'aci_sel'):
        for conj in ('r1_40', 'r2_45'):
            k = f'{conf}|{conj}'
            if k not in res:
                continue
            o = res[k]
            ic = o['ic95']
            out.append(f'{nom[conf] if conj == "r1_40" else ""} & {o["n"]} & '
                       f'{o["pendiente"]:.2f} [{ic["pendiente"][0]:.2f}, {ic["pendiente"][1]:.2f}] & '
                       f'{o["pendiente_mec"]:.2f} [{ic["pendiente_mec"][0]:.2f}, {ic["pendiente_mec"][1]:.2f}] & '
                       f'{o["R2_obs_sobre_mec"]:.2f} & '
                       f'{o["resid_media"]:+.1f} [{ic["resid_media"][0]:+.1f}, {ic["resid_media"][1]:+.1f}] & '
                       f'{o["r_resid_oc"]:+.2f} \\\\')
        out.append('\\addlinespace[2pt]')
    out[-1] = '\\bottomrule'
    out += ['\\end{tabular}', '\\end{table*}', '']
    escribir('tab_mecanico', '\n'.join(out))


def tab_inferencia():
    res = json.load(open(L.RES / 'r2_03_resumen.json'))
    I = pd.read_csv(L.RES / 'r2_03_inferencia.csv')
    out = ['\\begin{table}[tp]', '\\centering', '\\footnotesize',
           '\\caption{Inference on the cross-cell relationship under dependence, Transport+ACI with '
           '$\\gamma=0.05$. Slope of the width change (\\%) on the static over-coverage (pp). Rows differ in what '
           'they hold fixed and in how they treat the dependence between cells that share days, base models and '
           'windows.}',
           '\\label{tab:inferencia}',
           '\\begin{tabular}{l rr}', '\\toprule',
           'Estimator & 40 cells & 45 cells \\\\', '\\midrule']

    def g(conj, metodo, campo='pendiente', d=2):
        s = I[(I.config == 'tr_g05') & (I.conjunto == conj) & (I.metodo == metodo)]
        return np.nan if s.empty else float(s[campo].iloc[0])
    for et, mt in (('Pooled OLS', 'OLS combinado'), ('Window fixed effects', 'EF ventana'),
                   ('Base-model fixed effects', 'EF modelo'), ('Two-way fixed effects', 'EF bidireccional'),
                   ('Crossed random effects (REML)', 'Efectos aleatorios cruzados')):
        a, b = g('r1_40', mt), g('r2_45', mt)
        sa, sb = g('r1_40', mt, 'se'), g('r2_45', mt, 'se')
        out.append(f'{et} & {a:.2f} ({sa:.2f}) & {b:.2f} ({sb:.2f}) \\\\')
    ia, ib = res['tr_g05|r1_40']['ic95']['pendiente'], res['tr_g05|r2_45']['ic95']['pendiente']
    out.append(f'Day-block bootstrap, 95\\% interval & [{ia[0]:.2f}, {ia[1]:.2f}] & [{ib[0]:.2f}, {ib[1]:.2f}] \\\\')
    for et, mt in (('Wild cluster bootstrap by base model, $p$', 'Wild cluster bootstrap por modelo'),
                   ('Wild cluster bootstrap by window, $p$', 'Wild cluster bootstrap por ventana')):
        a, b = g('r1_40', mt, 'p_valor'), g('r2_45', mt, 'p_valor')
        ca, cb = g('r1_40', mt, 'clusters'), g('r2_45', mt, 'clusters')
        out.append(f'{et} & {a:.4f} ({int(ca)} cl.) & {b:.4f} ({int(cb)} cl.) \\\\')
    w = I[(I.config == 'tr_g05') & I.metodo.str.startswith('dentro de ventana')]
    for conj, col in (('r1_40', 'a'), ('r2_45', 'b')):
        ww = w[w.conjunto == conj]
        if col == 'a':
            ra = (ww.r.min(), ww.r.max())
        else:
            rb = (ww.r.min(), ww.r.max())
    out.append(f'Within-window correlation, range over 5 windows & [{ra[0]:.2f}, {ra[1]:.2f}] & [{rb[0]:.2f}, {rb[1]:.2f}] \\\\')
    fa, fb = res['tr_g05|r1_40']['familia_x_ventana'], res['tr_g05|r2_45']['familia_x_ventana']
    out.append(f'Family $\\times$ window means (10 cells), $r$ & {fa["r"]:.2f} & {fb["r"]:.2f} \\\\')
    aa, ab = res['tr_g05|r1_40']['anova_oc'], res['tr_g05|r2_45']['anova_oc']
    out.append('\\midrule')
    out.append('\\multicolumn{3}{l}{\\textit{Variance of the static over-coverage explained (two-way ANOVA)}} \\\\')
    out.append(f'\\quad base model & {100 * aa["modelo"]:.0f}\\% & {100 * ab["modelo"]:.0f}\\% \\\\')
    out.append(f'\\quad window & {100 * aa["ventana"]:.0f}\\% & {100 * ab["ventana"]:.0f}\\% \\\\')
    out += ['\\bottomrule', '\\end{tabular}', '',
            '\\smallskip\\parbox{0.95\\linewidth}{\\scriptsize Standard errors in parentheses are the usual OLS or REML '
            'ones and treat cells as independent; they are shown for comparison with the bootstrap and wild cluster '
            'results. Wild cluster bootstrap: restricted, six-point Webb weights, 9{,}999 replicates.}',
            '\\end{table}', '']
    escribir('tab_inferencia', '\n'.join(out))


def tab_simulacion():
    S = json.load(open(L.RES / 'r2_05_sim_resumen.json'))
    C = pd.read_csv(L.RES / 'r2_05_sim_celdas.csv')
    post = C[C.ventana.isin(['W2 transition', 'W3', 'W4', 'W5'])]
    esc = ['S0 no shift', 'S1 level only', 'S2 level + dispersion', 'S3 dispersion only']
    nom = {'S0 no shift': 'S0, no shift', 'S1 level only': 'S1, level $\\times 3$',
           'S2 level + dispersion': 'S2, level $\\times 3$ and dispersion $\\times 0.6$',
           'S3 dispersion only': 'S3, dispersion $\\times 0.6$'}
    out = ['\\begin{table*}[tp]', '\\centering', '\\footnotesize',
           f'\\caption{{Controlled simulation, {S["disenio"]["replicas"]} replicates per scenario. Left: static '
           'over-coverage (pp) averaged over the four post-shift windows and the replicates, for four of the eight '
           'base models (\\ref{app:sim}). Right: cross-cell regression of the Transport+ACI width change on the '
           'static over-coverage within each replicate (40 cells), median and 2.5--97.5 percentiles over replicates; '
           'mechanical slope from the constant-threshold oracle; share of the variance of the observed change '
           'explained by the mechanical one; mean residual.}',
           '\\label{tab:simulacion}', '\\setlength{\\tabcolsep}{3pt}', '\\scriptsize',
           '\\begin{tabular}{l rrrr llll}', '\\toprule',
           ' & \\multicolumn{4}{c}{Static over-coverage (pp)} & \\multicolumn{4}{c}{Cross-cell regression, Transport+ACI} \\\\',
           '\\cmidrule(lr){2-5}\\cmidrule(lr){6-9}',
           'Scenario & M1 & M2 & M4 & M7 & Slope & Mech. slope & $R^2$ obs.$\\sim$mech. & Residual (\\%) \\\\',
           '\\midrule']
    mods = {m.split(' ')[0]: m for m in C.modelo.unique()}
    for e in esc:
        oc = post[post.escenario == e].groupby('modelo').oc.mean()
        t = S[e]['tr']
        fm = lambda k, d=2: f'{t[k]["mediana"]:.{d}f} [{t[k]["p2_5"]:.{d}f}, {t[k]["p97_5"]:.{d}f}]'   # noqa: E731
        out.append(f'{nom[e]} & {oc[mods["M1"]]:+.1f} & {oc[mods["M2"]]:+.1f} & {oc[mods["M4"]]:+.1f} & '
                   f'{oc[mods["M7"]]:+.1f} & {fm("pendiente")} & {fm("pendiente_mec")} & '
                   f'{fm("R2_mec")} & {fm("resid", 1)} \\\\')
    out += ['\\bottomrule', '\\end{tabular}', '',
            '\\smallskip\\parbox{0.95\\linewidth}{\\scriptsize M1: correctly specified oracle. M2: oracle with '
            'dispersion inflated by 30\\% in every period. M4: dispersion fixed at its calibration value. M7: level '
            'lagged by 30 days. In S0 there is no shift and the regression has no systematic variation to explain.}',
            '\\end{table*}', '']
    escribir('tab_simulacion', '\n'.join(out))


def tab_escalera():
    B = pd.read_csv(L.RES / 'r2_02_base.csv')
    M = pd.read_csv(L.RES / 'r2_02_metricas.csv')
    ref = B[(B.brazo == 'hurdle_800') & (B.periodo == 'TEST_COMPLETO')].crps.iloc[0]
    filas = [('hurdle_800', 'Hurdle, 2$\\times$400'), ('hurdle_es', 'Hurdle, early stopping (59+46)'),
             ('hurdle_2000', 'Hurdle, 2$\\times$2000'), ('qgbm_54x15', 'Quantile GBM, 54$\\times$15'),
             ('qgbm_54x50', 'Quantile GBM, 54$\\times$50'), ('qgbm_54x100', 'Quantile GBM, 54$\\times$100'),
             ('qgbm_54x200', 'Quantile GBM, 54$\\times$200'), ('qgbm_54x400', 'Quantile GBM, 54$\\times$400')]
    out = ['\\begin{table}[tp]', '\\centering', '\\footnotesize',
           '\\caption{Model form and fitted capacity. Every model shares features, rows, training cut-off, '
           'per-model hyperparameters and seed; only the number of trees and the model form change. CRPS of the '
           'base predictive (MWh); change over the whole test relative to the reference hurdle; static-split '
           'coverage and mean width over the whole test.}',
           '\\label{tab:escalera}',
           '\\begin{tabular}{l r rr r rr}', '\\toprule',
           ' & & \\multicolumn{2}{c}{CRPS} & & \\multicolumn{2}{c}{Static split} \\\\',
           '\\cmidrule(lr){3-4}\\cmidrule(lr){6-7}',
           'Base model & Trees & Transition & Whole test & vs. ref. & Coverage & Width \\\\', '\\midrule']
    for b, nm in filas:
        bb = B[B.brazo == b].set_index('periodo')
        st = M[(M.brazo == b) & (M.metodo == 'static') & (M.periodo == 'TEST_COMPLETO')].iloc[0]
        ct = bb.loc['TEST_COMPLETO', 'crps']
        out.append(f'{nm} & {L.BRAZOS[b][2]:,} & {bb.loc["test_transition", "crps"]:.1f} & {ct:.1f} & '
                   f'{100 * (ct / ref - 1):+.1f}\\% & {st.cobertura:.1f} & {st.ancho_medio:.0f} \\\\')
    out += ['\\bottomrule', '\\end{tabular}', '\\end{table}', '']
    escribir('tab_escalera', '\n'.join(out).replace(',', '{,}'))


def tab_ablaciones(A):
    out = ['\\begin{table*}[tp]', '\\centering', '\\footnotesize',
           '\\caption{Marginal contribution of each component of the transport-based scheme to the mean one-sided '
           'interval score (MWh; negative is an improvement), with 95\\% day-block bootstrap intervals, for the three '
           'main base models. All adaptive steps use $\\gamma=0.05$ and no bound on $\\alpha_t$, as in '
           'Algorithm~\\ref{alg:transporte}. Differences are computed on the plant-days where both limits are '
           'finite. Runtime is the additional wall-clock time of the component over the 638 test dates.}',
           '\\label{tab:ablaciones}',
           '\\begin{tabular}{l rr rr rr r}', '\\toprule']
    cab = ' & '.join(f'\\multicolumn{{2}}{{c}}{{{s}}}' for s in
                     ('Reference hurdle', 'Early-stopped hurdle', 'Reference quantile GBM'))
    out += [f' & {cab} & \\\\', '\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}\\cmidrule(lr){6-7}',
            'Component & Transition & Whole test & Transition & Whole test & Transition & Whole test & Runtime (s) \\\\',
            '\\midrule']
    for etq, _, _ in COMPONENTES:
        celdas = []
        for b in L.PRINCIPALES:
            for per in ('test_transition', 'TEST_COMPLETO'):
                r = A[(A.brazo == b) & (A.componente == etq) & (A.periodo == per)].iloc[0]
                celdas.append(f'{r.d_IS:+.1f}{"$^\\dagger$" if r.significativo else ""}')
        rt = A[(A.brazo == 'hurdle_800') & (A.componente == etq) & (A.periodo == 'TEST_COMPLETO')].d_segundos.iloc[0]
        out.append(f'{etq} & ' + ' & '.join(celdas) + f' & {rt:+.2f} \\\\')
    out += ['\\bottomrule', '\\end{tabular}', '',
            '\\smallskip\\parbox{0.95\\linewidth}{\\scriptsize $^\\dagger$ the 95\\% interval excludes zero. '
            'Intervals for every cell are in the result files of the companion repository; runtime measured on the '
            'reference hurdle.}', '\\end{table*}', '']
    escribir('tab_ablaciones', '\n'.join(out))


def tab_operacional():
    T = pd.read_csv(L.RES / 'r2_04_operacional.csv')
    allr = T[T.subconjunto == 'all']
    out = ['\\begin{table*}[tp]', '\\centering', '\\footnotesize',
           '\\caption{Operational evaluation over the whole test period. Coverage by plant-day (date-clustered '
           'standard error), weighted by installed capacity and weighted by curtailed energy; share of curtailed '
           'energy above the limit; mean width (MWh); fraction of infinite limits. Cost: expected cost per plant-day '
           'in units of the allowance cost $c_h$, for a ratio $k=c_p/c_h$ of the penalty to the allowance cost, '
           'with the limit calibrated at the decision-optimal level $1-1/k$; at $k=10$ it is the one-sided interval '
           'score at 90\\%. Costs over finite limits; an asterisk marks methods with infinite limits.}',
           '\\label{tab:operacional}', '\\setlength{\\tabcolsep}{3.5pt}',
           '\\begin{tabular}{l rrrr rr rrr}', '\\toprule',
           ' & \\multicolumn{4}{c}{Coverage and exposure (90\\% limits)} & & & \\multicolumn{3}{c}{Cost per plant-day} \\\\',
           '\\cmidrule(lr){2-5}\\cmidrule(lr){8-10}',
           'Method & Plant-day & Capacity & Energy & Uncovered & Width & \\% inf. & $k=10$ & $k=20$ & $k=100$ \\\\',
           '\\midrule']

    def fila(b, m, nombre):
        r = allr[(allr.base == b) & (allr.metodo == m) & (allr.alpha == 0.10)]
        if r.empty:
            return None
        r = r.iloc[0]
        cs = []
        for a in (0.10, 0.05, 0.01):
            s = allr[(allr.base == b) & (allr.metodo == m) & (allr.alpha == a)]
            if s.empty:
                cs.append('--')
            else:
                s = s.iloc[0]
                cs.append(f'{s.IS_finitos:.0f}{"$^\\ast$" if s.pct_infinito > 0 else ""}')
        return (f'\\quad {nombre} & {r.cobertura:.1f} & {r.cob_capacidad:.1f} & {r.cob_energia:.1f} & '
                f'{r.energia_no_cubierta:.1f}\\% & {r.ancho_medio:.0f} & {r.pct_infinito:.1f} & ' + ' & '.join(cs) + ' \\\\')
    for b in L.PRINCIPALES:
        out.append(f'\\multicolumn{{10}}{{l}}{{\\textit{{{ETQ[b]}}}}} \\\\')
        for m in ('static', 'aci_sel', 'tr_sel', 'tr_g05', 'cqr'):
            x = fila(b, m, MET[m])
            if x:
                out.append(x)
    out.append('\\multicolumn{10}{l}{\\textit{Benchmarks without a base model}} \\\\')
    for m in ('B1 empirical quantile 365 d', 'B2 rolling distribution 60 d', 'B4 zero-inflated lognormal'):
        x = fila('model-free', m, m[3:].capitalize().replace(' d', ' days').replace('365 days', 'per plant, 365 days')
                 .replace('60 days', 'per plant, 60 days').replace('lognormal', 'lognormal per plant'))
        if x:
            out.append(x)
    out += ['\\bottomrule', '\\end{tabular}', '\\end{table*}', '']
    escribir('tab_operacional', '\n'.join(out))


def tab_altos():
    T = pd.read_csv(L.RES / 'r2_04_operacional.csv')
    T = T[T.alpha == 0.10]
    D = json.load(open(L.RES / 'r2_04_dias_altos.json'))
    C = pd.read_csv(L.RES / 'r2_04_condicional.csv')
    subs = [('H1 ex post (cal. P90)', f'H1, ex post ({D["H1_dias"]} days)'),
            ('H2 ex post (test top decile)', f'H2, ex post ({D["H2_dias"]} days)'),
            ('H3 ex ante (regime known at origin)', f'H3, ex ante ({D["H3_dias"]} days)')]
    out = ['\\begin{table*}[tp]', '\\centering', '\\footnotesize',
           '\\caption{Coverage on high-curtailment days and conditional coverage, 90\\% limits. H1: system '
           'curtailment above the calibration-window 90th percentile; H2: top decile of test days; H3: trailing '
           'seven-day mean of system curtailment known at the forecast origin above the same threshold. H1 and H2 '
           'condition on the outcome, H3 only on information available when the forecast is issued. Coverage on '
           'each subset with 95\\% day-block bootstrap interval; energy-weighted coverage on the same subset. The '
           'last three columns give the worst absolute deviation from 90\\% across technologies, capacity terciles '
           'and regions (pp).}',
           '\\label{tab:altos}', '\\setlength{\\tabcolsep}{3pt}',
           '\\begin{tabular}{l ' + 'rr' * len(subs) + ' rrr}', '\\toprule',
           ' & ' + ' & '.join(f'\\multicolumn{{2}}{{c}}{{{s[1]}}}' for s in subs) +
           ' & \\multicolumn{3}{c}{Worst deviation} \\\\',
           ''.join(f'\\cmidrule(lr){{{2 + 2 * i}-{3 + 2 * i}}}' for i in range(len(subs))) +
           f'\\cmidrule(lr){{{2 + 2 * len(subs)}-{4 + 2 * len(subs)}}}',
           'Method & ' + ' & '.join(['Coverage & Energy'] * len(subs)) + ' & Techn. & Size & Region \\\\',
           '\\midrule']
    for b in L.PRINCIPALES:
        out.append(f'\\multicolumn{{{4 + 2 * len(subs)}}}{{l}}{{\\textit{{{ETQ[b]}}}}} \\\\')
        for m in ('static', 'aci_sel', 'tr_sel', 'tr_g05', 'cqr'):
            cel = []
            for sn, _ in subs:
                r = T[(T.base == b) & (T.metodo == m) & (T.subconjunto == sn)]
                if r.empty:
                    cel += ['--', '--']
                    continue
                r = r.iloc[0]
                cel += [f'{r.cobertura:.1f} [{r.cobertura_lo:.1f}, {r.cobertura_hi:.1f}]', f'{r.cob_energia:.1f}']
            c = C[(C.base == b) & (C.metodo == m)]
            if c.empty:
                continue
            c = c.iloc[0]
            out.append(f'\\quad {MET[m]} & ' + ' & '.join(cel) +
                       f' & {c.peor_tecnologia:.1f} & {c.peor_tercil:.1f} & {c.peor_region:.1f} \\\\')
    out += ['\\bottomrule', '\\end{tabular}', '\\end{table*}', '']
    escribir('tab_altos', '\n'.join(out))


# ==========================================================================
# Apendices
# ==========================================================================
def tab_hiper():
    sel = json.load(open(L.RES / 'r2_02_seleccion.json'))
    B = pd.read_csv(L.RES / 'r2_02_base.csv')
    filas = [
        ('\\textit{Base models}', '', ''),
        ('Forecast horizon', '7 days', 'direct; every dynamic feature lags the target by at least 7 days'),
        ('Last training target', '2023-12-31', 'no model sees the evaluation period'),
        ('Trees per model / learning rate / depth', '400 / 0.05 / 6', 'fixed a priori; reference models'),
        ('Min. child weight / subsample / colsample', '5 / 0.9 / 0.9', 'all models'),
        ('Features', '12', 'lags 7, 8, 14, 21 d; 7- and 30-d means; occurrence; day of week and year; log capacity; region; technology'),
        ('Hurdle dispersion', 'out of fold, 5 folds', '$\\hat\\sigma=1.70$ (reference), $1.83$ (early stopping)'),
        ('Early stopping of the hurdle', 'ceiling 4{,}000, patience 50', 'validation Jul--Dec 2023; refit on full training period: 59 + 46 trees'),
        ('Quantile grid', '54 levels, 0.005--0.999', '0.02--0.98 by 0.02, plus 0.005, 0.01, 0.99, 0.995, 0.999; rearranged'),
        ('Capacity ladder', '15, 50, 100, 200, 400', 'trees per quantile level'),
        ('\\textit{Calibration layers}', '', ''),
        ('Nominal level', '$1-\\alpha=0.90$', 'one-sided upper limit $[0,U]$; tail levels 0.95 and 0.99'),
        ('Score', 'PIT, $s=F_x(y)$', 'atom at zero randomised'),
        ('Calibration window', '2024-01-01 to 2024-08-31', '244 days, 26{,}552 plant-days'),
        ('Horizon embargo', '7 days', 'online windows end at $t-7$; error feedback delayed 7 steps'),
        ('Sliding window', '60 days, refreshed every 7', ''),
        ('Transport window / refresh', '60 days / 7 days', 'at least 100 recent scores per refresh'),
        ('Transport quantile grid', '$g=\\min(100,\\max(20,m/2))$', '$m$ recent scores; two linear interpolations'),
        ('Bootstrap of the map / shrinkage scale', '$B=150$ / $\\tau=0.05$', '$\\lambda(u)=[1+(\\mathrm{sd}_{\\mathrm{boot}}(u)/\\tau)^2]^{-1}$'),
        ('ACI bound', 'none, or $\\alpha_{\\min}=0.005$', 'both reported'),
        ('One-sided CQR', '$U=\\max\\{q_{0.9}(x)+\\hat Q_{0.9}(y-q_{0.9}(x)),0\\}$', 'on each base model\'s own quantile'),
        ('\\textit{Selection by rolling origin}', '', ''),
        ('Inner calibration / validation', 'Jan--Apr 2024 / May--Aug 2024', 'same refresh and embargo as the test'),
        ('Grids', 'step $\\gamma$: 0.005, 0.01, 0.02, 0.05, 0.10, 0.20', 'windows: 30, 45, 60, 90, 120 days'),
        ('Criterion', 'mean one-sided interval score', '$+\\infty$ if any limit is infinite'),
    ]
    for b in L.BRAZOS:
        s = sel.get(b, {})
        a, t = s.get('ACI'), s.get('Transport+ACI')
        if a and t:
            filas.append((f'Selected, {NOMBRE[b]}', f'ACI $\\gamma={a["gamma"]}$',
                          f'Transport+ACI $\\gamma={t["gamma"]}$, window {t["ventana"]} d'))
    filas += [
        ('\\textit{Evaluation}', '', ''),
        ('Primary metric', '$U+\\alpha^{-1}\\max(y-U,0)$', 'proper for the $1-\\alpha$ quantile; $+\\infty$ if $U$ is'),
        ('Coverage standard error', 'clustered by date', ''),
        ('Bootstrap of differences', '2{,}000 replicates of whole days', '95\\% percentile interval'),
        ('CRPS / twCRPS', '300 samples per plant-day', 'twCRPS threshold: plant\'s calibration-window 90th percentile'),
        ('\\textit{Seeds}', '', ''),
        ('Base-model training', '42', 'XGBoost hist, 4 threads'),
        ('PIT atom and map bootstrap', '20260720', 'one generator, consumed in a fixed order'),
        ('CRPS sampling', '11', ''),
        ('Day-block bootstrap and wild cluster bootstrap', '20260901', ''),
        ('Simulation', '20261103', 'seed per scenario and replicate'),
    ]
    out = ['\\begin{longtable}{p{0.25\\textwidth} p{0.27\\textwidth} p{0.36\\textwidth}}',
           '\\caption{Hyperparameters, constants, selected values and seeds.}\\label{tab:hiper}\\\\',
           '\\toprule', 'Item & Value & Detail \\\\', '\\midrule', '\\endfirsthead',
           '\\multicolumn{3}{l}{\\footnotesize Table~\\ref{tab:hiper}, continued.}\\\\', '\\toprule',
           'Item & Value & Detail \\\\', '\\midrule', '\\endhead', '\\bottomrule', '\\endlastfoot']
    for a, b, c in filas:
        out.append(f'{a} & {b} & {c} \\\\')
    out += ['\\end{longtable}', '']
    escribir('tab_hiper', '\n'.join(out).replace('\\footnotesize Table', '\\footnotesize Table'))


def apendice_sensibilidad():
    S = pd.read_csv(L.RES / 'r2_06_sensibilidad.csv')
    txt = []
    txt.append('All analyses vary one parameter at a time around a reference configuration, Transport+ACI with '
               '$\\gamma=0.05$, a 60-day window, weekly refresh, $B=150$, $\\tau=0.05$, a map grid of 100 levels, '
               'at least 100 recent scores and $\\alpha_{\\min}=0.005$, and report the whole test period. The '
               'embargo is fixed at seven days by the forecast horizon and is not a free parameter. '
               'Table~\\ref{tab:sens_capa} covers the calibration layer, Table~\\ref{tab:sens_nivel} the nominal '
               'level, Table~\\ref{tab:sens_cal} the calibration window, the quantile grid and the threshold '
               'defining high-curtailment days, and Table~\\ref{tab:sens_base} the seeds and the base-model '
               'hyperparameters. The full $\\gamma\\times$window grid for the reference hurdle is in '
               'Table~\\ref{tab:sens_hiper} of \\ref{app:extra}.\n')
    # tabla capa
    out = ['\\begin{table*}[tp]', '\\centering', '\\footnotesize',
           '\\caption{Sensitivity of Transport+ACI to the parameters of the calibration layer, whole test, for the '
           'early-stopped hurdle and the reference quantile GBM. Coverage (\\%), mean width (MWh), fraction of '
           'infinite limits (\\%) and one-sided interval score over finite limits (MWh).}',
           '\\label{tab:sens_capa}',
           '\\begin{tabular}{ll rrrr rrrr}', '\\toprule',
           ' & & \\multicolumn{4}{c}{Early-stopped hurdle} & \\multicolumn{4}{c}{Reference quantile GBM} \\\\',
           '\\cmidrule(lr){3-6}\\cmidrule(lr){7-10}',
           'Parameter & Value & Cov. & Width & \\% inf. & IS & Cov. & Width & \\% inf. & IS \\\\', '\\midrule']
    nombres = {'reference': 'Reference', 'tau': 'Shrinkage scale $\\tau$', 'B': 'Bootstrap size $B$',
               'n_grid': 'Map grid', 'refresh_days': 'Refresh period (days)',
               'min_recent_scores': 'Min. recent scores', 'window_days': 'Window (days)',
               'transport_without_ACI': 'Transport without ACI', 'gamma': 'Step $\\gamma$',
               'alpha_min': 'Bound $\\alpha_{\\min}$'}
    sub = S[S.bloque.isin(['ref', 'E1', 'E2']) & (S.metodo.isin(['Transport+ACI', 'Transport (fixed alpha)']))]
    for (par, val), g in sub.groupby(['parametro', 'valor'], sort=False):
        cel = []
        for b in ('hurdle_es', 'qgbm_54x400'):
            r = g[g.brazo == b]
            if r.empty:
                cel += ['--'] * 4
                continue
            r = r.iloc[0]
            cel += [f'{r.cobertura:.1f}', f'{r.ancho:.0f}', f'{r.pct_inf:.1f}', f'{r.IS_finitos:.0f}']
        v = 'none' if str(val) in ('inf', 'none') else str(val)
        out.append(f'{nombres.get(par, par)} & {v} & ' + ' & '.join(cel) + ' \\\\')
    g = S[(S.bloque == 'E2') & (S.metodo == 'ACI')]
    out.append('\\midrule')
    for val, gg in g.groupby('valor', sort=False):
        cel = []
        for b in ('hurdle_es', 'qgbm_54x400'):
            r = gg[gg.brazo == b].iloc[0]
            cel += [f'{r.cobertura:.1f}', f'{r.ancho:.0f}', f'{r.pct_inf:.1f}', f'{r.IS_finitos:.0f}']
        out.append(f'ACI, step $\\gamma$ & {val} & ' + ' & '.join(cel) + ' \\\\')
    out += ['\\bottomrule', '\\end{tabular}', '\\end{table*}', '']
    txt.append('\n'.join(out))
    # nivel nominal
    out = ['\\begin{table}[tp]', '\\centering', '\\footnotesize',
           '\\caption{Sensitivity to the nominal level, whole test. Coverage (\\%) and one-sided interval score at '
           'the same level (MWh). Adaptive layers use $\\gamma=0.05$ and $\\alpha_{\\min}=\\alpha/20$.}',
           '\\label{tab:sens_nivel}', '\\begin{tabular}{l l rr rr}', '\\toprule',
           ' & & \\multicolumn{2}{c}{Early-stopped hurdle} & \\multicolumn{2}{c}{Ref. quantile GBM} \\\\',
           '\\cmidrule(lr){3-4}\\cmidrule(lr){5-6}', 'Level & Method & Cov. & IS & Cov. & IS \\\\', '\\midrule']
    g = S[S.bloque == 'E3']
    for (val, met), gg in g.groupby(['valor', 'metodo'], sort=False):
        cel = []
        for b in ('hurdle_es', 'qgbm_54x400'):
            r = gg[gg.brazo == b].iloc[0]
            cel += [f'{r.cobertura:.1f}', f'{r.IS_finitos:.0f}{"$^\\ast$" if r.pct_inf > 0 else ""}']
        out.append(f'{float(val):.2f} & {met} & ' + ' & '.join(cel) + ' \\\\')
    out += ['\\bottomrule', '\\end{tabular}', '', '\\smallskip\\parbox{0.95\\linewidth}{\\scriptsize '
            '$^\\ast$ the method returns infinite limits; the score is over finite limits.}', '\\end{table}', '']
    txt.append('\n'.join(out))
    # calibracion, rejilla, umbral
    out = ['\\begin{table}[tp]', '\\centering', '\\footnotesize',
           '\\caption{Sensitivity to the calibration window (all windows end on 31 August 2024), to the density '
           'of the quantile grid of the reference quantile GBM, and to the threshold that defines high-curtailment '
           'days (H1). Whole test; coverage (\\%) and one-sided interval score over finite limits (MWh).}',
           '\\label{tab:sens_cal}', '\\begin{tabular}{l l l rr}', '\\toprule',
           'Analysis & Value & Method & Coverage & IS \\\\', '\\midrule']
    for blo, etq in (('E4', 'Calibration window'), ('E6', 'Quantile grid')):
        g = S[S.bloque == blo]
        for _, r in g.iterrows():
            base = 'early-stopped hurdle' if r.brazo == 'hurdle_es' else 'quantile GBM'
            out.append(f'{etq} & {r.valor} ({base}) & {r.metodo} & {r.cobertura:.1f} & {r.IS_finitos:.0f} \\\\')
        out.append('\\midrule')
    g = S[S.bloque == 'E7']
    for _, r in g.iterrows():
        out.append(f'High-day threshold & {r.valor} ({r.dias_altos:.0f} days), {NOMBRE[r.brazo]} & '
                   f'{MET.get(r.metodo, r.metodo)} & {r.cobertura:.1f} & -- \\\\')
    out += ['\\bottomrule', '\\end{tabular}', '\\end{table}', '']
    txt.append('\n'.join(out))
    # semillas y modelo base
    out = ['\\begin{table}[tp]', '\\centering', '\\footnotesize',
           '\\caption{Sensitivity to seeds and to base-model hyperparameters. Top: ten seeds of the conformal layer '
           '(PIT atom and map bootstrap), mean and standard deviation over seeds. Bottom: early-stopped hurdle '
           'refitted with other depths, learning rates and training seeds; trees selected by early stopping, CRPS '
           'over the whole test, and whole-test coverage and interval score of the static split and of '
           'Transport+ACI.}',
           '\\label{tab:sens_base}', '\\begin{tabular}{l l rrrr}', '\\toprule',
           'Analysis & Method & \\multicolumn{2}{c}{Coverage} & \\multicolumn{2}{c}{IS} \\\\',
           ' & & mean & sd & mean & sd \\\\', '\\midrule']
    g = S[S.bloque == 'E5']
    for (b, met), gg in g.groupby(['brazo', 'metodo']):
        out.append(f'Conformal seeds, {NOMBRE[b]} & {met} & {gg.cobertura.mean():.2f} & '
                   f'{gg.cobertura.std():.2f} & {gg.IS_finitos.mean():.1f} & {gg.IS_finitos.std():.1f} \\\\')
    out += ['\\midrule', ' & & Trees & CRPS & Static (cov./IS) & T+ACI (cov./IS) \\\\', '\\midrule']
    g = S[S.bloque == 'E8']
    for (par, val), gg in g.groupby(['parametro', 'valor'], sort=False):
        st = gg[gg.metodo == 'Static split'].iloc[0]
        ta = gg[gg.metodo == 'Transport+ACI'].iloc[0]
        nm = {'max_depth': 'depth', 'learning_rate': 'learning rate', 'random_state': 'training seed'}[par]
        out.append(f'Early-stopped hurdle & {nm} = {val} & {int(st.arboles)} & {st.crps_test:.1f} & '
                   f'{st.cobertura:.1f} / {st.IS_finitos:.0f} & {ta.cobertura:.1f} / {ta.IS_finitos:.0f} \\\\')
    out += ['\\bottomrule', '\\end{tabular}', '\\end{table}', '']
    txt.append('\n'.join(out))
    (MAN / 'apendice_sensibilidad.tex').write_text('\n'.join(txt))
    L.log('apendice_sensibilidad', 'r2_08_tablas.log')


def limpiar_r1(nombre, nuevo, reemplazos):
    t = (BASE_R1 / f'{nombre}.tex').read_text()
    t = re.sub(r' Generated from \\texttt\{[^}]*\}(\s*and\s*\\texttt\{[^}]*\})?\.', '', t)
    for a, b in reemplazos:
        assert a in t, (nombre, a)
        t = t.replace(a, b)
    (MAN / f'{nuevo}.tex').write_text(t)
    return t


def apendice_tablas():
    partes = ['Tables~\\ref{tab:results}--\\ref{tab:panel} complete the main text. Table~\\ref{tab:results} gives '
              'the reference hurdle by window; Table~\\ref{tab:cota} the effect of bounding $\\alpha_t$; '
              'Table~\\ref{tab:frontera} the sensitivity of the transition-window results to its boundaries; '
              'Table~\\ref{tab:sens_hiper} the full $\\gamma\\times$window grid on the test period, a display '
              'produced after the selection was closed; and Table~\\ref{tab:panel} the calibration schemes designed '
              'for panel dependence.\n']
    t = limpiar_r1('tab_results', 'tab_results', [])
    t = t.replace('Section~\\ref{sec:metricas} reports the metric that does not let those cases improve a method\'s score.',
                  'Table~\\ref{tab:modelos} reports the interval score, which does not let those cases improve a method\'s score.')
    t = t.replace('test\\_pre', 'Sep 2024').replace('test\\_transition', 'Oct--Dec 2024')
    t = t.replace('(Sep 24, stable)', '').replace('(Oct--Dec 24, max.\\ divergence)', '(transition)')
    assert 'test\\_' not in t
    (MAN / 'tab_results.tex').write_text(t)
    partes.append('\\input{tab_results}')
    t = limpiar_r1('tab_cota_alpha', 'tab_cota_alpha', [('unbounded (submitted version)', 'unbounded')])
    partes.append('\\input{tab_cota_alpha}')
    limpiar_r1('tab_sensibilidad_frontera', 'tab_sensibilidad_frontera', [])
    partes.append('\\input{tab_sensibilidad_frontera}')
    t = limpiar_r1('tab_sensibilidad_hiper', 'tab_sensibilidad_hiper', [])
    t = re.sub(r'the 60-day cells at \$\\gamma=0\.02\$ and \$0\.05\$ are the configurations of the submitted version and coincide with Table~\\ref\{tab:benchmarks\}\.',
               'the 60-day cells at $\\\\gamma=0.02$ and $0.05$ are the configurations of Algorithm~\\\\ref{alg:transporte} reported in the main text.', t)
    (MAN / 'tab_sensibilidad_hiper.tex').write_text(t)
    partes.append('\\input{tab_sensibilidad_hiper}')
    t = limpiar_r1('tab_panel', 'tab_panel', [('Pooled split (submitted version)', 'Pooled split')])
    partes.append('\\input{tab_panel}')
    (MAN / 'apendice_tablas.tex').write_text('\n'.join(partes) + '\n')
    for n in ('tab_results', 'tab_cota_alpha', 'tab_sensibilidad_frontera', 'tab_sensibilidad_hiper', 'tab_panel'):
        x = (MAN / f'{n}.tex').read_text()
        assert 'submitted' not in x.lower() and 'generated from' not in x.lower(), n
    L.log('apendice_tablas', 'r2_08_tablas.log')


if __name__ == '__main__':
    pedidas = sys.argv[1:]
    A = None
    if not pedidas or 'ablaciones' in pedidas:
        A = ablaciones()
    if A is None and (L.RES / 'r2_08_ablaciones.csv').exists():
        A = pd.read_csv(L.RES / 'r2_08_ablaciones.csv')
    tareas = {'mae': tab_mae, 'estacional': tab_estacional, 'modelos': tab_modelos,
              'mecanico': tab_mecanico, 'inferencia': tab_inferencia, 'simulacion': tab_simulacion,
              'escalera': tab_escalera, 'ablaciones_tex': lambda: tab_ablaciones(A),
              'operacional': tab_operacional, 'altos': tab_altos, 'hiper': tab_hiper,
              'sensibilidad': apendice_sensibilidad, 'apendice': apendice_tablas}
    for k, fn in tareas.items():
        if not pedidas or k in pedidas:
            fn()
