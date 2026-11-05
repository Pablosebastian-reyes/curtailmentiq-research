#!/usr/bin/env python3
"""
R2-09. Figuras nuevas de la R2 (PDF vectorial, fondo claro, apto para gris).

Paleta categorica validada con un verificador de separacion para daltonismo (modo
claro, todos los pares): azul #2a78d6, naranja #eb6834, aqua #1baf7a. El aqua
queda bajo 3:1 de contraste: por eso toda serie lleva ademas forma de marcador
y leyenda (codificacion secundaria, tambien para impresion en gris).

  fig_modelos.pdf      misma capa sobre distintos modelos base + 45 celdas
  fig_mecanico.pdf     cambio de ancho observado contra el oraculo mecanico
  fig_simulacion.pdf   simulacion controlada
  fig_escalera.pdf     CRPS contra arboles ajustados (escalera + hurdle ES)
  fig_ablaciones.pdf   aporte de cada componente, tres modelos base
  fig_operacional.pdf  cobertura ponderada por energia y dias altos
  fig_pit.pdf          histogramas PIT en calibracion y en la transicion
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_lib as L                      # noqa: E402
import numpy as np                      # noqa: E402
import pandas as pd                     # noqa: E402
import matplotlib                       # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt         # noqa: E402
from matplotlib.colors import LinearSegmentedColormap   # noqa: E402
R = L.R

AZUL, NARANJA, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
TXT, TXT2, GRIS, GRILLA = '#0b0b0b', '#52514e', '#8a8984', '#e4e3df'
DIVERG = LinearSegmentedColormap.from_list('div', ['#256abf', '#f0efec', '#e34948'])
plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
    'font.size': 8.5, 'axes.titlesize': 9, 'axes.labelsize': 8.5, 'legend.fontsize': 7.5,
    'xtick.labelsize': 7.5, 'ytick.labelsize': 7.5, 'axes.edgecolor': TXT2,
    'axes.labelcolor': TXT, 'xtick.color': TXT2, 'ytick.color': TXT2, 'text.color': TXT,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True,
    'grid.color': GRILLA, 'grid.linewidth': 0.6, 'lines.linewidth': 1.4,
    'pdf.fonttype': 42, 'savefig.bbox': 'tight', 'savefig.pad_inches': 0.02})
ETQ = {'hurdle_800': 'Hurdle (reference)', 'hurdle_es': 'Hurdle (early stopping)',
       'hurdle_sigma_x': r'Hurdle ($\sigma(x)$)', 'hurdle_2000': 'Hurdle (2x2000)',
       'qgbm_54x15': 'Quantile 54x15', 'qgbm_54x50': 'Quantile 54x50',
       'qgbm_54x100': 'Quantile 54x100', 'qgbm_54x200': 'Quantile 54x200',
       'qgbm_54x400': 'Quantile (reference)'}
VENT = ['test_pre', 'test_transition', '2025-S1', '2025-S2', '2026-S1']


def guardar(fig, nombre):
    fig.savefig(L.FIG / nombre)
    fig.savefig(L.FIG / nombre.replace('.pdf', '.png'), dpi=200)
    plt.close(fig)


# --------------------------------------------------------------------------
def fig_modelos():
    M = pd.read_csv(L.RES / 'r2_02_metricas.csv')
    C = pd.read_csv(L.RES / 'r2_03_celdas.csv')
    res = json.load(open(L.RES / 'r2_03_resumen.json'))
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw=dict(width_ratios=[1.05, 1]))
    brz = ['hurdle_800', 'hurdle_es', 'hurdle_sigma_x', 'qgbm_54x400']
    x = np.arange(len(brz))
    for j, (met, col, nm) in enumerate((('static', AZUL, 'Static split'),
                                        ('tr_g05', NARANJA, r'Transport+ACI ($\gamma$=0.05)'))):
        vals, covs = [], []
        for b in brz:
            r = M[(M.brazo == b) & (M.metodo == met) & (M.periodo == 'test_transition')].iloc[0]
            vals.append(r.ancho_medio); covs.append(r.cobertura)
        bars = ax[0].bar(x + (j - 0.5) * 0.36, vals, 0.34, color=col, label=nm,
                         edgecolor='white', linewidth=0.8, hatch=None if j == 0 else '////')
        for xi, v, cv in zip(x + (j - 0.5) * 0.36, vals, covs):
            ax[0].text(xi, v / 2, f'{cv:.1f}%', ha='center', va='center', fontsize=6.3, color=TXT,
                       rotation=90, bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.9))
    for i, b in enumerate(brz):
        s = M[(M.brazo == b) & (M.metodo == 'static') & (M.periodo == 'test_transition')].ancho_medio.iloc[0]
        t = M[(M.brazo == b) & (M.metodo == 'tr_g05') & (M.periodo == 'test_transition')].ancho_medio.iloc[0]
        ax[0].text(i, max(s, t) + 30, f'{100 * (t / s - 1):+.1f}%'.replace('-', '\u2212'), ha='center',
                   fontsize=7.5, color=TXT, fontweight='bold')
    ax[0].set_xticks(x, [ETQ[b].replace(' (', '\n(') for b in brz])
    ax[0].set_ylabel('Mean width, Oct-Dec 2024 (MWh)')
    ax[0].set_ylim(0, 1500)
    ax[0].legend(loc='upper right', frameon=False)
    ax[0].set_title('(a) Same layer, four base models', loc='left')
    ax[0].grid(axis='x', visible=False)

    a = ax[1]
    c = C[C.config == 'tr_g05']
    r1 = c[c.en_r1]
    for fam, mk in (('hurdle', 'o'), ('qgbm', '^')):
        s = r1[r1.familia == fam]
        a.scatter(s.oc, s.dW, s=22, marker=mk, color=AZUL, edgecolor='white', linewidth=0.6,
                  label=f'{"Hurdle" if fam == "hurdle" else "Quantile"} variants (fit)', zorder=3)
    es = c[c.brazo == 'hurdle_es']
    a.scatter(es.oc, es.dW, s=40, marker='D', color=NARANJA, edgecolor='white', linewidth=0.6,
              label='Early-stopped hurdle (held out)', zorder=4)
    lin = res['tr_g05|r1_40']
    bl = np.load(L.RES / 'r2_03_bootstrap_lineas.npz')
    xx = np.linspace(-9, 6.5, 100)
    band = np.percentile(bl['intercepto'][:, None] + bl['pendiente'][:, None] * xx[None, :], [2.5, 97.5], axis=0)
    a.fill_between(xx, band[0], band[1], color=GRIS, alpha=0.25, linewidth=0)
    a.plot(xx, lin['intercepto'] + lin['pendiente'] * xx, color=TXT, linewidth=1.2)
    a.axhline(0, color=TXT2, linewidth=0.7); a.axvline(0, color=TXT2, linewidth=0.7)
    a.set_xlabel('Static over-coverage (pp above nominal)')
    a.set_ylabel(r'Width change of Transport+ACI (%)')
    oos = res['fuera_de_muestra_hurdle_es']
    a.text(0.98, 0.97, (f"fit on 40 cells: r = {lin['r']:.2f}, slope {lin['pendiente']:.2f}\n"
                        f"held-out cells: r(obs, pred) = {oos['r_obs_pred']:.2f}, RMSE {oos['rmse']:.1f} pp"
                        ).replace('-', '\u2212'),
           transform=a.transAxes, ha='right', va='top', fontsize=6.8, color=TXT2)
    a.legend(loc='lower left', frameon=False, fontsize=6.5)
    a.set_title('(b) Width change against static over-coverage', loc='left')
    guardar(fig, 'fig_modelos.pdf')


def fig_mecanico():
    C = pd.read_csv(L.RES / 'r2_03_celdas.csv')
    res = json.load(open(L.RES / 'r2_03_resumen.json'))
    conf = 'tr_g05'
    c = C[C.config == conf]
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.0))
    a = ax[0]
    for fam, mk, col in (('hurdle', 'o', AZUL), ('qgbm', '^', NARANJA)):
        s = c[c.familia == fam]
        a.scatter(s.dW_mec, s.dW, s=22, marker=mk, color=col, edgecolor='white', linewidth=0.6,
                  label='Hurdle variants' if fam == 'hurdle' else 'Quantile variants', zorder=3)
    lim = [min(c.dW_mec.min(), c.dW.min()) - 5, max(c.dW_mec.max(), c.dW.max()) + 5]
    a.plot(lim, lim, color=TXT2, linewidth=0.9, linestyle='--', label='Equality')
    a.set_xlabel('Mechanical width change: constant-threshold oracle (%)')
    a.set_ylabel('Observed width change (%)')
    o = res[f'{conf}|r2_45']
    a.text(0.03, 0.97, f"$R^2$ = {o['R2_obs_sobre_mec']:.2f}  (45 cells)", transform=a.transAxes,
           va='top', fontsize=7, color=TXT2)
    a.legend(loc='lower right', frameon=False)
    a.set_title('(a) Observed against mechanical', loc='left')
    a = ax[1]
    for fam, mk, col in (('hurdle', 'o', AZUL), ('qgbm', '^', NARANJA)):
        s = c[c.familia == fam]
        a.scatter(s.oc, s.resid, s=22, marker=mk, color=col, edgecolor='white', linewidth=0.6, zorder=3)
    lo, hi = o['ic95']['resid_media']
    a.axhspan(lo, hi, color=GRIS, alpha=0.25, linewidth=0)
    a.axhline(o['resid_media'], color=TXT, linewidth=1.1)
    a.axhline(0, color=TXT2, linewidth=0.7)
    a.set_xlabel('Static over-coverage (pp above nominal)')
    a.set_ylabel('Residual: observed minus mechanical (%)')
    a.text(0.02, 0.03, (f"mean residual {o['resid_media']:+.1f}% [{lo:+.1f}, {hi:+.1f}]\n"
                        f"r(residual, over-coverage) = {o['r_resid_oc']:+.2f}").replace('-', '\u2212'),
           transform=a.transAxes, ha='left', va='bottom', fontsize=7, color=TXT2)
    a.set_title('(b) What adaptation adds beyond re-levelling', loc='left')
    guardar(fig, 'fig_mecanico.pdf')


def fig_simulacion():
    C = pd.read_csv(L.RES / 'r2_05_sim_celdas.csv')
    esc = ['S0 no shift', 'S1 level only', 'S2 level + dispersion', 'S3 dispersion only']
    mods = list(dict.fromkeys(C.modelo))
    post = C[C.ventana.isin(['W2 transition', 'W3', 'W4', 'W5'])]
    M = post.groupby(['modelo', 'escenario']).oc.mean().unstack()[esc].loc[mods]
    G = post.groupby(['modelo', 'escenario']).dW_tr.mean().unstack()[esc].loc[mods]
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.3), gridspec_kw=dict(width_ratios=[1.15, 1]))
    a = ax[0]
    vmax = np.nanmax(np.abs(M.values))
    a.imshow(M.values, cmap=DIVERG, vmin=-vmax, vmax=vmax, aspect='auto')
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            a.text(j, i, f'{M.values[i, j]:+.1f}\n({G.values[i, j]:+.0f}%)', ha='center', va='center',
                   fontsize=6.2, color=TXT)
    a.set_xticks(range(len(esc)), ['No shift', 'Level', 'Level +\ndispersion', 'Dispersion'])
    a.set_yticks(range(len(mods)), [m.split(' ', 1)[1] if ' ' in m else m for m in mods], fontsize=6.6)
    a.grid(False)
    a.set_title('(a) Static over-coverage, pp (width change of T+ACI)', loc='left', fontsize=8.3)
    a = ax[1]
    s2 = C[C.escenario == 'S2 level + dispersion']
    a.scatter(s2.oc, s2.dW_tr, s=4, color=AZUL, alpha=0.25, linewidth=0, label='Observed', zorder=2)
    a.scatter(s2.oc, s2.dWmec_tr, s=4, color=NARANJA, alpha=0.25, linewidth=0, label='Mechanical (oracle)', zorder=2)
    for col, k in ((AZUL, 'dW_tr'), (NARANJA, 'dWmec_tr')):
        b1, b0 = np.polyfit(s2.oc, s2[k], 1)
        xx = np.linspace(s2.oc.min(), s2.oc.max(), 50)
        a.plot(xx, b0 + b1 * xx, color=col, linewidth=1.4)
    a.axhline(0, color=TXT2, linewidth=0.7); a.axvline(0, color=TXT2, linewidth=0.7)
    a.set_xlabel('Static over-coverage (pp)')
    a.set_ylabel('Width change of Transport+ACI (%)')
    lg = a.legend(loc='upper right', frameon=False, markerscale=3)
    for h in lg.legend_handles:
        h.set_alpha(1)
    a.set_title('(b) Level + dispersion: all replicates', loc='left')
    guardar(fig, 'fig_simulacion.pdf')


def fig_escalera():
    B = pd.read_csv(L.RES / 'r2_02_base.csv')
    B = B[B.periodo == 'TEST_COMPLETO'].set_index('brazo')
    fig, a = plt.subplots(figsize=(3.5, 2.7))
    q = ['qgbm_54x15', 'qgbm_54x50', 'qgbm_54x100', 'qgbm_54x200', 'qgbm_54x400']
    arb = [L.BRAZOS[b][2] for b in q]
    a.plot(arb, B.loc[q, 'crps'], marker='^', color=AZUL, label='Quantile GBM, 54 levels')
    for b, mk in (('hurdle_800', 'o'), ('hurdle_2000', 's'), ('hurdle_es', 'D')):
        a.scatter(L.BRAZOS[b][2], B.loc[b, 'crps'], marker=mk, s=34, color=NARANJA,
                  edgecolor='white', linewidth=0.6, zorder=3)
        a.annotate(ETQ[b].replace('Hurdle ', 'Hurdle\n'), (L.BRAZOS[b][2], B.loc[b, 'crps']),
                   textcoords='offset points', xytext=(6, -2), fontsize=6.4, color=TXT2)
    a.set_xscale('log')
    a.set_xlabel('Fitted trees (log scale)')
    a.set_ylabel('CRPS, whole test (MWh)')
    a.legend(loc='lower left', frameon=False)
    guardar(fig, 'fig_escalera.pdf')


def fig_ablaciones():
    A = pd.read_csv(L.RES / 'r2_08_ablaciones.csv')
    comp = list(dict.fromkeys(A.componente))
    brz = ['hurdle_800', 'hurdle_es', 'qgbm_54x400']
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.5), sharey=True)
    for k, b in enumerate(brz):
        a = ax[k]
        s = A[(A.brazo == b) & (A.periodo == 'TEST_COMPLETO')].set_index('componente').loc[comp]
        y = np.arange(len(comp))[::-1]
        sig = (s.lo * s.hi > 0).values
        a.errorbar(s.d_IS, y, xerr=[s.d_IS - s.lo, s.hi - s.d_IS], fmt='none', ecolor=TXT2,
                   elinewidth=1.0, capsize=2)
        a.scatter(s.d_IS[sig], y[sig], color=AZUL, s=26, zorder=3, label='Interval excludes 0')
        a.scatter(s.d_IS[~sig], y[~sig], facecolor='white', edgecolor=AZUL, s=26, zorder=3,
                  label='Interval contains 0')
        a.axvline(0, color=TXT2, linewidth=0.8)
        a.set_title(ETQ[b], loc='left', fontsize=8.2)
        a.set_xlabel(r'$\Delta$ interval score, whole test (MWh)')
        if k == 0:
            a.set_yticks(y, comp, fontsize=7)
            a.legend(loc='lower left', frameon=False, fontsize=6.3)
    guardar(fig, 'fig_ablaciones.pdf')


def fig_operacional():
    T = pd.read_csv(L.RES / 'r2_04_operacional.csv')
    T = T[T.alpha == 0.10]
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.0))
    a = ax[0]
    tot = T[T.subconjunto == 'all']
    estilo = {'static': (AZUL, 'Static split'), 'aci_sel': (NARANJA, 'ACI (selected)'),
              'tr_sel': (NARANJA, 'Transport+ACI (selected)'), 'cqr': (AQUA, 'One-sided CQR')}
    marc = {'hurdle_800': 'o', 'hurdle_es': 's', 'qgbm_54x400': '^'}
    for _, r in tot.iterrows():
        if r.base in marc and r.metodo in estilo:
            col, _ = estilo[r.metodo]
            face = col if r.metodo != 'tr_sel' else 'white'
            a.scatter(r.IS_finitos, r.cob_energia, marker=marc[r.base], s=34, facecolor=face,
                      edgecolor=col, linewidth=1.1, zorder=3)
        elif r.base == 'model-free':
            a.scatter(r.IS_finitos, r.cob_energia, marker='x', s=26, color=GRIS, zorder=3)
            a.annotate(r.metodo.split(' ')[0], (r.IS_finitos, r.cob_energia), textcoords='offset points',
                       xytext=(4, -6), fontsize=6.2, color=TXT2)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker=marc[b], color=TXT2, linestyle='none', label=ETQ[b]) for b in marc]
    h += [Line2D([], [], marker='o', color=AZUL, linestyle='none', label='Static split'),
          Line2D([], [], marker='o', color=NARANJA, linestyle='none', label='ACI (selected)'),
          Line2D([], [], marker='o', markerfacecolor='white', markeredgecolor=NARANJA, linestyle='none',
                 label='Transport+ACI (selected)'),
          Line2D([], [], marker='o', color=AQUA, linestyle='none', label='One-sided CQR')]
    a.set_xlim(400, 870)
    a.legend(handles=h, loc='lower right', frameon=False, fontsize=6.0)
    a.set_xlabel('Interval score = cost at k = 10 (MWh per plant-day)')
    a.set_ylabel('Energy-weighted coverage (%)')
    a.set_title('(a) Whole test', loc='left')
    a = ax[1]
    subs = ['all', 'H3 ex ante (regime known at origin)', 'H1 ex post (cal. P90)', 'H2 ex post (test top decile)']
    nomb = ['All days', 'High,\nex ante (H3)', 'High,\nex post (H1)', 'Top decile,\nex post (H2)']
    estilo['tr_g05'] = (NARANJA, r'Transport+ACI ($\gamma$=0.05)')
    sel = [('hurdle_800', 'static'), ('hurdle_800', 'tr_g05'), ('hurdle_es', 'static'),
           ('qgbm_54x400', 'static'), ('qgbm_54x400', 'cqr')]
    off = np.linspace(-0.3, 0.3, len(sel))
    for k, (b, m) in enumerate(sel):
        col = estilo[m][0]
        for j, sn in enumerate(subs):
            r = T[(T.base == b) & (T.metodo == m) & (T.subconjunto == sn)].iloc[0]
            a.errorbar(j + off[k], r.cobertura, yerr=[[r.cobertura - r.cobertura_lo], [r.cobertura_hi - r.cobertura]],
                       fmt=marc[b], color=col, markersize=4.5, elinewidth=0.9, capsize=1.5,
                       markerfacecolor=col if m not in ('tr_sel', 'tr_g05') else 'white',
                       label=f'{ETQ[b]}: {estilo[m][1]}' if j == 0 else None)
    a.axhline(90, color=TXT2, linewidth=0.8, linestyle='--')
    a.set_xticks(range(len(subs)), nomb, fontsize=6.6)
    a.set_ylabel('Coverage (%)')
    a.legend(loc='lower left', frameon=False, fontsize=5.6)
    a.set_title('(b) Coverage on high-curtailment days', loc='left')
    a.grid(axis='x', visible=False)
    guardar(fig, 'fig_operacional.pdf')


def fig_pit():
    h = L.panel_filas()
    cal = ((h.fecha >= R.CAL_INI) & (h.fecha < R.CAL_FIN)).values
    tr = ((h.fecha >= '2024-10-01') & (h.fecha < '2025-01-01')).values
    brz = ['hurdle_800', 'hurdle_es', 'qgbm_54x400']
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.3), sharey=True)
    bins = np.linspace(0, 1, 21)
    for k, b in enumerate(brz):
        pred = L.cargar_predictiva(b)
        s = pred.cdf(h.y_real.values, np.random.default_rng(R.SEED_CONFORMAL))
        a = ax[k]
        for m, col, nm, ls in ((cal, AZUL, 'Calibration (Jan-Aug 2024)', '-'),
                               (tr, NARANJA, 'Transition (Oct-Dec 2024)', '--')):
            dens, _ = np.histogram(s[m], bins=bins, density=True)
            a.step(bins[:-1], dens, where='post', color=col, linestyle=ls, label=nm)
        a.axhline(1, color=TXT2, linewidth=0.7, linestyle=':')
        q = R.cm.q_conformal(s[cal], 0.10)
        a.axvline(q, color=TXT2, linewidth=0.7)
        a.set_title(ETQ[b], loc='left', fontsize=8.2)
        a.set_xlabel('PIT score')
        a.text(q - 0.015, 2.45, r'$\hat q$', ha='right', fontsize=7.5, color=TXT2)
        if k == 0:
            a.set_ylabel('Density')
            a.legend(loc='upper left', frameon=False, fontsize=6.2)
        a.set_ylim(0, 2.6)
    guardar(fig, 'fig_pit.pdf')


if __name__ == '__main__':
    pedidas = sys.argv[1:] or ['modelos', 'mecanico', 'simulacion', 'escalera', 'ablaciones',
                               'operacional', 'pit']
    for p in pedidas:
        globals()[f'fig_{p}']()
        L.log(f'figura {p} lista', 'r2_09_figuras.log')
