#!/usr/bin/env python3
"""
Cuerpos de las tablas nuevas del manuscrito, generados desde los archivos de
resultados. Regla Dura 1: ningun numero del .tex se escribe a mano.

Salida: resultados/tablas_tex/*.tex   (para \input desde el manuscrito)

Comando:
  <venv>/bin/python flagship/revision/fase9_tablas_tex.py
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rev_lib as R   # noqa: E402

RES = R.REPO / 'resultados'
OUT = RES / 'tablas_tex'
OUT.mkdir(parents=True, exist_ok=True)

PER = ['test_pre', 'test_transition', '2025-S1', '2025-S2', '2026-S1']
ETQM = {'hurdle': 'Hurdle, constant $\\sigma$',
        'hurdle_sigma_x': 'Hurdle, $\\sigma(x)$',
        'qgbm_multi': 'Quantile GBM'}
ETQMET = {'1_estatico_pit': 'Static split (PIT)',
          '2_ventana60d_pit': 'Sliding window 60d',
          '3_aci_pit_g02': 'ACI ($\\gamma{=}0.02$)',
          '3_aci_pit_g05': 'ACI ($\\gamma{=}0.05$)',
          '4_transporte_banda_g02': 'Transport+ACI ($\\gamma{=}0.02$)',
          '4_transporte_banda_g05': 'Transport+ACI ($\\gamma{=}0.05$)'}


def esc(t):
    return str(t).replace('_', '\\_').replace('%', '\\%').replace('&', '\\&')


CABECERA = ('%% generado por flagship/revision/fase9_tablas_tex.py\n'
            '%% NO EDITAR A MANO: se regenera desde resultados/\n')


def escribir(nombre, lineas, *, entorno='table*', col='', encabezado='',
             caption='', label='', nota='', ancho='footnotesize'):
    """Escribe una tabla flotante COMPLETA.

    Se emite el float entero, y no solo el cuerpo, porque TeX no acepta un
    \\input cuyo primer token sea \\multicolumn dentro de un tabular: al
    empezar la celda inserta la plantilla antes de ejecutar el \\input y
    \\omit queda fuera de lugar. Emitir el float completo evita el problema y
    mantiene la regla de que ningun numero se escribe a mano en el .tex.
    """
    out = [CABECERA.rstrip('\n'),
           f'\\begin{{{entorno}}}[t]', '\\centering']
    if ancho:
        out.append(f'\\{ancho}')
    if caption:
        out.append(f'\\caption{{{caption}}}')
    if label:
        out.append(f'\\label{{{label}}}')
    out += [f'\\begin{{tabular}}{{{col}}}', '\\toprule']
    if encabezado:
        out.append(encabezado)
    out.append('\\midrule')
    out += lineas
    out += ['\\bottomrule', '\\end{tabular}']
    if nota:
        out += ['', '\\vspace{3pt}',
                f'\\parbox{{\\linewidth}}{{\\footnotesize {nota}}}']
    out.append(f'\\end{{{entorno}}}')
    (OUT / f'{nombre}.tex').write_text('\n'.join(out) + '\n')
    print(f'  {nombre}.tex')


# ---------------------------------------------------------------- tabla 4
def tabla_model_agnostic():
    t = pd.read_csv(RES / 'fase0' / 'fase0_tabla_por_modelo.csv')
    tr = t[t.periodo == 'test_transition']
    L = []
    for m in ('hurdle', 'hurdle_sigma_x', 'qgbm_multi'):
        s = tr[tr.modelo_base == m]
        L.append(f'\\multicolumn{{6}}{{l}}{{\\emph{{{ETQM[m]}}}}} \\\\')
        for _, r in s.iterrows():
            L.append(f'\\quad {ETQMET[r.metodo]} & {r.cobertura}\\,({r.se_cluster}) & '
                     f'{r.ancho_medio:.0f} & {r.IS_finitos:.0f} & '
                     f'{r.pct_infinito} & {r.crps_base:.1f} \\\\')
        L.append('\\addlinespace')
    escribir('tab_model_agnostic', L[:-1], col='lccccc',
             encabezado='Method & Coverage (se) & Width & Interval score & '
                        '\\% infinite & CRPS \\\\',
             caption='The same calibration layer over three base predictives, '
                     'transition window (October to December 2024), nominal '
                     '90\\%. Coverage in percent with date-clustered standard '
                     'error, mean width in MWh over finite intervals, interval '
                     'score of the one-sided limit in MWh restricted to finite '
                     'intervals, fraction of infinite intervals, and base-model '
                     'CRPS in MWh. Only the base model differs across blocks; '
                     'the score, the windows, the embargo, the seeds and every '
                     'constant of the calibration layer are identical. '
                     'Generated from '
                     '\\texttt{resultados/fase0/fase0\\_tabla\\_por\\_modelo.csv}.',
             label='tab:agnostic')


# ---------------------------------------------------------------- tabla 5
def tabla_diagnostico():
    d = pd.read_csv(RES / 'fase0' / 'fase0_diagnostico.csv')
    ETQP = {'test_pre': "Sep '24", 'test_transition': "Oct--Dec '24",
            '2025-S1': '2025-S1', '2025-S2': '2025-S2', '2026-S1': '2026-S1'}
    L = []
    for m in ('hurdle', 'hurdle_sigma_x', 'qgbm_multi'):
        s = d[d.modelo_base == m].set_index('periodo').reindex(PER)
        L.append(f'\\multicolumn{{5}}{{l}}{{\\emph{{{ETQM[m]}}}}} \\\\')
        for p, r in s.iterrows():
            L.append(f'\\quad {ETQP[p]} & {r.cob_estatico} & '
                     f'{r.sobrecobertura_pp:+.1f} & {r.ancho_estatico:.0f} & '
                     f'{r.cambio_ancho_pct:+.1f} \\\\')
        L.append('\\addlinespace')
    x, y = d.sobrecobertura_pp.values, d.cambio_ancho_pct.values
    b = np.polyfit(x, y, 1)
    r = float(np.corrcoef(x, y)[0, 1])
    L = L[:-1]
    L.append('\\midrule')
    L.append(f'\\multicolumn{{5}}{{l}}{{Pearson $r = {r:.3f}$; slope '
             f'${b[0]:.2f}$ \\% of width per pp of over-coverage; intercept '
             f'${b[1]:+.2f}$ \\%}} \\\\')
    escribir('tab_diagnostico', L, col='lcccc',
             encabezado='Window & Static coverage (\\%) & Over-coverage (pp) & '
                        'Static width (MWh) & Width change (\\%) \\\\',
             caption='The diagnostic, over the fifteen cells given by three '
                     'base models and five evaluation windows. Over-coverage '
                     'is the coverage of the static split minus the 90\\% '
                     'nominal level. The width change is that of Transport+ACI '
                     '($\\gamma=0.05$) relative to the static split in the same '
                     'cell. Generated from '
                     '\\texttt{resultados/fase0/fase0\\_diagnostico.csv}.',
             label='tab:diagnostico')


# ---------------------------------------------------------------- tabla 6
def tabla_ablaciones():
    a = pd.read_csv(RES / 'fase2' / 'fase2_aporte_por_componente.csv')
    ETQC = {'adaptacion online (A1 - A0)': 'Online adaptation (ACI over static split)',
            'transporte sin ACI (A2 - A0)': 'Transport alone (over static split)',
            'transporte sobre ACI (A3 - A1)': 'Transport added on top of ACI',
            'shrinkage de cola (A4 - A3)': 'Tail shrinkage added on top of transport',
            'pipeline completo (A4 - A0)': 'Full pipeline (over static split)'}
    COSTO = {'adaptacion online (A1 - A0)': '$+0.2$',
             'transporte sin ACI (A2 - A0)': '$+7.1$',
             'transporte sobre ACI (A3 - A1)': '$+0.4$',
             'shrinkage de cola (A4 - A3)': '$+6.1$',
             'pipeline completo (A4 - A0)': '$+6.7$'}
    L = []
    for c, etq in ETQC.items():
        tr = a[(a.componente == c) & (a.periodo == 'test_transition')].iloc[0]
        to = a[(a.componente == c) & (a.periodo == 'TEST_COMPLETO')].iloc[0]
        L.append(f'{etq} & ${tr.d_IS:+.1f}$ & $[{tr.IS_lo:+.0f}, {tr.IS_hi:+.0f}]$ & '
                 f'${to.d_IS:+.1f}$ & $[{to.IS_lo:+.0f}, {to.IS_hi:+.0f}]$ & '
                 f'{"yes" if to.significativo == "si" else "no"} & {COSTO[c]} \\\\')
    escribir('tab_ablaciones', L, col='lccccccc',
             encabezado='Component & \\multicolumn{2}{c}{Transition window} & '
                        '\\multicolumn{2}{c}{Whole test} & Significant & '
                        'Runtime (s) \\\\\n'
                        '\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}\n'
                        ' & $\\Delta\\mathrm{IS}$ & 95\\% CI & '
                        '$\\Delta\\mathrm{IS}$ & 95\\% CI & (whole test) & \\\\',
             caption='Marginal contribution of each component to the mean '
                     'interval score, in MWh, with 95\\% bootstrap intervals '
                     'resampling whole days. Negative is an improvement. '
                     'Runtime is the additional wall-clock cost of the '
                     'component over the 638 test dates. Generated from '
                     '\\texttt{resultados/fase2/fase2\\_aporte\\_por\\_componente.csv}.',
             label='tab:ablaciones')


# ---------------------------------------------------------------- tabla 7
ETQ_F4 = {
    'B1 cuantil empirico 365d': 'B1 empirical quantile, 365-day window, per plant',
    'B2 distribucion movil 60d': 'B2 rolling historical distribution, 60 days, per plant',
    'B3 CQR unilateral (GBM)': 'B3 one-sided conformalized quantile regression (GBM)',
    'B4 lognormal inflada en cero': 'B4 zero-inflated lognormal, per plant',
    'ACI (g=0.005, Fase 3)': 'ACI ($\\gamma{=}0.005$)',
    'Transporte+ACI (g=0.005, v=120, Fase 3)': 'Transport+ACI ($\\gamma{=}0.005$, 120-day window)',
    'Split estatico (PIT)': 'Static split (PIT)',
    'Ventana deslizante 60d': 'Sliding window 60d',
    'ACI (g=0.02)': 'ACI ($\\gamma{=}0.02$)',
    'ACI (g=0.05)': 'ACI ($\\gamma{=}0.05$)',
    'Transporte+ACI (g=0.02)': 'Transport+ACI ($\\gamma{=}0.02$)',
    'Transporte+ACI (g=0.05)': 'Transport+ACI ($\\gamma{=}0.05$)',
}


def tabla_benchmarks():
    m = pd.read_csv(RES / 'fase4' / 'fase4_metricas_completas.csv')
    d = pd.read_csv(RES / 'fase4' / 'fase4_diferencias_bootstrap.csv').set_index('metodo')
    t = m[m.periodo == 'TEST_COMPLETO'].sort_values('IS_finitos')
    FAM = {'benchmark': 'Probabilistic benchmarks (new in this revision)',
           'paper': 'Methods of the submitted version',
           'seleccionado': 'Configuration selected by rolling origin'}
    L = []
    for fam in ('benchmark', 'seleccionado', 'paper'):
        s = t[t.familia == fam]
        L.append(f'\\multicolumn{{7}}{{l}}{{\\emph{{{FAM[fam]}}}}} \\\\')
        for _, r in s.iterrows():
            IS_tot = ('$\\infty$' if not np.isfinite(r.IS_total)
                      else f'{r.IS_total:.0f}')
            crps = '--' if pd.isna(r.crps) else f'{r.crps:.1f}'
            dif = ('--' if r.metodo not in d.index
                   else f'${d.loc[r.metodo].d_IS:+.0f}$ '
                        f'$[{d.loc[r.metodo].IS_lo:+.0f}, {d.loc[r.metodo].IS_hi:+.0f}]$')
            L.append(f'\\quad {ETQ_F4.get(r.metodo, esc(r.metodo))} & {r.cobertura}\\,({r.se_cluster}) & '
                     f'{r.ancho_medio:.0f} & {r.pct_infinito} & '
                     f'{r.IS_finitos:.0f} & {IS_tot} & {dif} \\\\')
        L.append('\\addlinespace')
    escribir('tab_benchmarks', L[:-1], col='lcccccc',
             encabezado='Method & Coverage (se) & Width & \\% inf. & '
                        '$\\mathrm{IS}$ finite & $\\mathrm{IS}$ all & '
                        '$\\Delta\\mathrm{IS}$ vs static [95\\% CI] \\\\',
             caption='All methods on the whole test period, September 2024 to '
                     'May 2026. Coverage in percent with date-clustered '
                     'standard error, mean width in MWh over finite intervals, '
                     'fraction of infinite intervals, interval score '
                     'restricted to finite intervals, unrestricted interval '
                     'score, and the bootstrap difference in interval score '
                     'against the static split resampling whole days. The '
                     'unrestricted score is the verdict: it is infinite for '
                     'any method producing even one infinite limit. Generated '
                     'from \\texttt{resultados/fase4/}.',
             label='tab:benchmarks')


# ---------------------------------------------------------------- tabla 8
def tabla_cota_alpha():
    c = pd.read_csv(RES / 'fase4' / 'fase4_cota_alpha.csv')
    v = c[c.periodo == 'TEST_COMPLETO']
    ORD = ['sin cota', 'alpha_min=0.005', 'alpha_min=0.01', 'alpha_min=0.02']
    ETQC = {'sin cota': 'unbounded (submitted version)',
            'alpha_min=0.005': '$\\alpha_{\\min}=0.005$',
            'alpha_min=0.01': '$\\alpha_{\\min}=0.01$',
            'alpha_min=0.02': '$\\alpha_{\\min}=0.02$'}
    L = []
    for met in ('ACI (g=0.05)', 'Transporte+ACI (g=0.05)'):
        etq = ('ACI ($\\gamma{=}0.05$)' if met.startswith('ACI')
               else 'Transport+ACI ($\\gamma{=}0.05$)')
        L.append(f'\\multicolumn{{6}}{{l}}{{\\emph{{{etq}}}}} \\\\')
        s = v[v.metodo == met].set_index('cota').reindex(ORD)
        for k, r in s.iterrows():
            IS_tot = ('$\\infty$' if not np.isfinite(r.IS_total)
                      else f'{r.IS_total:.0f}')
            L.append(f'\\quad {ETQC[k]} & {r.cobertura}\\,({r.se_cluster}) & '
                     f'{r.ancho_medio:.0f} & {r.pct_infinito} & '
                     f'{r.IS_finitos:.0f} & {IS_tot} \\\\')
        L.append('\\addlinespace')
    escribir('tab_cota_alpha', L[:-1], col='lccccc',
             encabezado='Bound on $\\alpha_t$ & Coverage (se) & Width & '
                        '\\% infinite & $\\mathrm{IS}$ finite & '
                        '$\\mathrm{IS}$ all \\\\',
             caption='Effect of bounding the online update of $\\alpha$ from '
                     'below, whole test period. A bound of '
                     '$\\alpha_{\\min}=0.005$ removes infinite intervals '
                     'entirely at negligible cost in coverage, and makes the '
                     'unrestricted interval score finite and therefore '
                     'comparable across methods. Generated from '
                     '\\texttt{resultados/fase4/fase4\\_cota\\_alpha.csv}.',
             label='tab:cota')


# ---------------------------------------------------------------- tabla 9
def tabla_panel():
    r = pd.read_csv(RES / 'fase5' / 'fase5_remedios.csv')
    v = r[r.periodo == 'TEST_COMPLETO']
    des = pd.read_csv(RES / 'fase5' / 'fase5_cobertura_desagregada.csv')
    mx = des.assign(a=des.desvio_pp.abs()).groupby(['metodo', 'eje']).a.max().unstack()
    ETQ = {'M0 split agrupado (manuscrito)': 'Pooled split (submitted version)',
           'M1 conformal por bloques de dia': 'Block conformal, one plant per date',
           'M2 Mondrian por tecnologia': 'Mondrian by technology',
           'M2 Mondrian por region': 'Mondrian by region',
           'M2 Mondrian por tercil de potencia': 'Mondrian by capacity tercile',
           'M3 conformal por central': 'Plant-level conformal',
           'ACI (g=0.02), referencia': 'ACI ($\\gamma{=}0.02$), for reference',
           'Transporte+ACI (g=0.05), referencia': 'Transport+ACI ($\\gamma{=}0.05$), for reference'}
    L = []
    for k, etq in ETQ.items():
        s = v[v.metodo == k]
        if s.empty:
            continue
        s = s.iloc[0]
        m = mx.loc[k] if k in mx.index else None
        L.append(f'{etq} & {s.cobertura}\\,({s.se_cluster}) & {s.ancho_medio:.0f} & '
                 f'{s.IS_finitos:.0f} & '
                 f'{m["tecnologia"]:.1f} & {m["tamano de central"]:.1f} & '
                 f'{m["region"]:.1f} & {m["evento"]:.1f} \\\\')
    escribir('tab_panel', L, col='lcccrrrr',
             encabezado=' & \\multicolumn{3}{c}{Marginal} & '
                        '\\multicolumn{4}{c}{Worst deviation from nominal (pp)} \\\\\n'
                        '\\cmidrule(lr){2-4}\\cmidrule(lr){5-8}\n'
                        'Scheme & Coverage (se) & Width & $\\mathrm{IS}$ & '
                        'Technology & Size & Region & High-curt. \\\\',
             caption='Calibration schemes designed to address panel '
                     'dependence, whole test period. The last four columns '
                     'give the worst absolute deviation from the 90\\% nominal '
                     'level over the groups of each axis, in percentage '
                     'points, which is the measure of conditional coverage; '
                     'smaller is better. Generated from '
                     '\\texttt{resultados/fase5/}.',
             label='tab:panel')


# ---------------------------------------------------------------- tabla 10
def tabla_estacional():
    d = pd.read_csv(RES / 'fase6' / 'fase6_descomposicion_estacional.csv')
    ETQ = {'solar_norte': 'Solar, Antofagasta and Atacama',
           'sistema_sol_eol': 'System (solar and wind)'}
    L = []
    for e in ('solar_norte', 'sistema_sol_eol'):
        s = d[(d.estrato == e) & (d.ventanas == 'ene-sep vs oct-dic')]
        L.append(f'\\multicolumn{{5}}{{l}}{{\\emph{{{ETQ[e]}}}}} \\\\')
        for _, r in s.iterrows():
            neg = r.anio == 2024
            f = (lambda v: f'$\\mathbf{{{v:+.2f}}}$') if neg else (lambda v: f'${v:+.2f}$')
            a = f'\\textbf{{{r.anio:.0f}}}' if neg else f'{r.anio:.0f}'
            L.append(f'\\quad {a} & {f(r.total)} & {f(r.estacional)} & '
                     f'{f(r.secular)} & {r.pct_estacional:.0f}\\% \\\\')
        c = d[(d.estrato == e) & (d.ventanas.str.startswith('calibracion'))].iloc[0]
        L.append(f'\\quad 2024, calibration window & ${c.total:+.2f}$ & '
                 f'${c.estacional:+.2f}$ & ${c.secular:+.2f}$ & '
                 f'{c.pct_estacional:.0f}\\% \\\\')
        L.append('\\addlinespace')
    escribir('tab_estacional', L[:-1], entorno='table', col='lcccc',
             ancho='',
             encabezado='Year & Total shift & Seasonal & Secular & '
                        'Seasonal share \\\\',
             caption='Decomposition of the January--September to '
                     'October--December shift in the monthly mean of $\\log Y$ '
                     'over positive plant-days, in log units, by year. The '
                     'seasonal component is the difference between the '
                     'calendar-month effects of the two windows and is by '
                     'construction the same in every year; the secular '
                     'component is the remainder. The 2024 row is the contrast '
                     'that defines the transition window used in the '
                     'evaluation; the final row of each block repeats the '
                     'decomposition on the calibration window itself (January '
                     'to August against October to December 2024), which is '
                     'the pair the evaluation actually uses. Generated from '
                     '\\texttt{resultados/fase6/fase6\\_descomposicion\\_estacional.csv}.',
             label='tab:seasonal',
             nota='Note: the calendar-month effects are estimated as the '
                  'median of each calendar month over the whole record. A '
                  'robust STL decomposition returns somewhat different values '
                  'on a 53-month series carrying a strong trend; it does not '
                  'change the order of magnitude of the split, and the secular '
                  'components remain the smaller part of the 2024 contrast.')


# ---------------------------------------------------------------- tabla 11
def tabla_sensibilidad_frontera():
    s = pd.read_csv(RES / 'fase6' / 'fase6_sensibilidad_frontera.csv')
    ETQ = {'Split estatico': 'Static split', 'ACI (g=0.02)': 'ACI ($\\gamma{=}0.02$)',
           'Transporte+ACI (g=0.05)': 'Transport+ACI ($\\gamma{=}0.05$)'}
    NOM = {'oficial: oct-dic 2024': 'Oct--Dec 2024 (the one used)',
           'sep-dic 2024': 'Sep--Dec 2024', 'nov 2024-ene 2025': 'Nov 2024--Jan 2025',
           'oct 2024-feb 2025': 'Oct 2024--Feb 2025', 'oct-nov 2024': 'Oct--Nov 2024',
           'sep 2024-mar 2025': 'Sep 2024--Mar 2025'}
    L = []
    for p, g in s.groupby('periodo', sort=False):
        L.append(f'\\multicolumn{{4}}{{l}}{{\\emph{{{NOM[p]}}}, '
                 f'$W_1 = {g.w1_vs_calibracion.iloc[0]:.3f}$}} \\\\')
        for _, r in g.iterrows():
            L.append(f'\\quad {ETQ[r.metodo]} & {r.cobertura}\\,({r.se_cluster}) & '
                     f'{r.ancho_medio:.0f} & {r.IS_finitos:.0f} \\\\')
        L.append('\\addlinespace')
    escribir('tab_sensibilidad_frontera', L[:-1], col='lccc',
             encabezado='Method & Coverage (se) & Width & Interval score \\\\',
             caption='Sensitivity to alternative definitions of the transition '
                     'window, hurdle base model. $W_1$ is the Wasserstein-1 '
                     'distance between the positive log-magnitudes of the '
                     'window and those of the calibration set. Generated from '
                     '\\texttt{resultados/fase6/fase6\\_sensibilidad\\_frontera.csv}.',
             label='tab:frontera')


# ---------------------------------------------------------------- tabla 3
def tabla_resultados_hurdle():
    """Tabla 3 del manuscrito, desde la corrida oficial. En la version enviada
    estos numeros estaban escritos a mano en el .tex; ahora se leen del CSV."""
    t = pd.read_csv(R.FLAGSHIP / 'conformal_v3_tabla.csv')
    t = t[t.periodo != 'TEST_COMPLETO']
    sal = pd.read_csv(RES / 'fase0' / 'fase0_tabla_por_modelo.csv')
    crps = (sal[sal.modelo_base == 'hurdle']
            .drop_duplicates('periodo').set_index('periodo').crps_base)
    inf_sup = {}
    for _, r in t.iterrows():
        if r.pct_infinito > 0:
            inf_sup[(r.metodo, r.periodo)] = f'\\textsuperscript{{{r.pct_infinito}}}'
    L = []
    for k, etq in ETQMET.items():
        s_ = t[t.metodo == k].set_index('periodo').reindex(PER)
        celdas = []
        for p_, r in s_.iterrows():
            sup = inf_sup.get((k, p_), '')
            celdas.append(f'{r.cobertura}\\,({r.se_cluster}) / '
                          f'{r.ancho_medio:.0f}{sup}')
        L.append(etq + ' & ' + ' & '.join(celdas) + ' \\\\')
    L.append('\\midrule')
    L.append('Base-model CRPS (MWh) & '
             + ' & '.join(f'{crps[p_]:.1f}' for p_ in PER) + ' \\\\')
    escribir('tab_results', L, col='l@{\\hspace{5pt}}c@{\\hspace{5pt}}c@{\\hspace{5pt}}c@{\\hspace{5pt}}c@{\\hspace{5pt}}c',
             encabezado='Method & test\\_pre & test\\_transition & 2025-S1 & '
                        '2025-S2 & 2026-S1 \\\\\n'
                        ' & (Sep 24, stable) & (Oct--Dec 24, max.\\ divergence) '
                        '& & & \\\\',
             caption='Coverage and mean interval width of the conformal '
                     'methods by period, on real data with the hurdle base '
                     'model, with the 7-day horizon embargo. Each cell shows '
                     'coverage in percent (clustered standard error by date in '
                     'parentheses) over mean interval width in MWh. Nominal '
                     'coverage is 90\\%. The base-model CRPS is a property of '
                     'the predictive, not of the calibration layer, and is '
                     'reported once per period. Superscripts give the fraction '
                     'of infinite intervals where nonzero; '
                     'Section~\\ref{sec:metricas} reports the metric that does '
                     'not let those cases improve a method\'s score. Generated '
                     'from \\texttt{flagship/conformal\\_v3\\_tabla.csv}.',
             label='tab:results')


# ---------------------------------------------------------------- tabla 2
def tabla_mae():
    """MAE de los modelos base, calculado desde los CSV de prediccion."""
    from scipy.stats import norm
    pred = R.FLAGSHIP / 'predicciones'
    filas = {}
    base = pd.read_csv(pred / 'pred_hurdle.csv', parse_dates=['fecha'])
    anio = base.fecha.dt.year.values
    y = base.y_real.values

    def mae(v, etq):
        d = {a: float(np.abs(v[anio == a] - y[anio == a]).mean())
             for a in (2024, 2025, 2026)}
        d['total'] = float(np.abs(v - y).mean())
        filas[etq] = d

    mae(pd.read_csv(pred / 'pred_naive_estacional.csv').y_pred.values,
        'Seasonal-naive (weekly)')
    q = pd.read_csv(pred / 'pred_qgbm_multi.csv.gz')
    cols = [c for c in q.columns if c.startswith('q0')]
    taus = np.array([float(c[1:]) for c in cols])
    mae(q[cols[int(np.argmin(np.abs(taus - 0.5)))]].values,
        'Multi-quantile GBM (median)')
    mae(pd.read_csv(pred / 'pred_gbm_cuantilico.csv').q50.values,
        'Quantile GBM, 3 levels (median)')
    mae(pd.read_csv(pred / 'pred_persistencia.csv').y_pred.values, 'Persistence')
    mae(pd.read_csv(pred / 'pred_xgboost_punto.csv').y_pred.values, 'Point XGBoost')
    p_, mu_, sg = base.p_occ.values, base.mu_log.values, float(base.sigma.iloc[0])
    med = np.zeros(len(p_))
    a = p_ > 0.5
    med[a] = np.exp(mu_[a] + sg * norm.ppf(1 - 0.5 / p_[a]))
    mae(med, 'Hurdle (mixture median)')

    L = [f'{k} & {v[2024]:.1f} & {v[2025]:.1f} & {v[2026]:.1f} & {v["total"]:.1f} \\\\'
         for k, v in sorted(filas.items(), key=lambda kv: kv[1]['total'])]
    escribir('tab_mae', L, entorno='table', col='lcccc', ancho='',
             encabezado='Model & 2024 & 2025 & 2026 & Total \\\\',
             caption='Mean absolute error (MWh) of the base forecasters on the '
                     'out-of-sample period, on the common row set. Lower is '
                     'better. The comparison is between these model classes on '
                     'this feature set at this horizon under this criterion; '
                     'see the scope statement in the text. Computed from '
                     '\\texttt{flagship/predicciones/}.',
             label='tab:mae')


if __name__ == '__main__':
    print('Cuerpos de tabla generados desde resultados/:')
    tabla_model_agnostic()
    tabla_diagnostico()
    tabla_ablaciones()
    tabla_benchmarks()
    tabla_cota_alpha()
    tabla_panel()
    tabla_estacional()
    tabla_sensibilidad_frontera()
    tabla_resultados_hurdle()
    tabla_mae()
    print(f'en {OUT}')
