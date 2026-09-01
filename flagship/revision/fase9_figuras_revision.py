#!/usr/bin/env python3
"""
Figuras nuevas de la revision mayor (SEGAN-D-26-03850).
=======================================================
Responden a la pregunta estructurada 4 de ambos revisores ("¿se beneficiaria de
tablas o figuras adicionales?") y al encargo explicito de R1.2 de un diagrama de
flujo del algoritmo.

  fig6_algorithm_flow   ancho doble. Diagrama de flujo de Transport+ACI, del
                        procesamiento de la entrada al intervalo final, con el
                        ORDEN DE EJECUCION entre el mapa de transporte y la
                        actualizacion de ACI marcado explicitamente (R1.2).
  fig7_model_agnostic   ancho doble, dos paneles. Izquierda: ancho y cobertura
                        del split estatico y de Transport+ACI en la ventana de
                        transicion, por modelo base. Derecha: el diagnostico,
                        cambio de ancho contra sobre-cobertura del split
                        estatico sobre las 15 celdas (R1.1).
  fig8_ablations        ancho doble. Aporte marginal de cada componente sobre
                        el interval score, con IC bootstrap por bloques de dia,
                        y costo computacional (R1.3).

Estilo identico al de generar_figuras_paper.py (serif, paleta sobria, sin
titulo dentro de la figura, textos en ingles).

Comando:
  <venv>/bin/python flagship/revision/fase9_figuras_revision.py
"""
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rev_lib as R   # noqa: E402

OUT = R.FLAGSHIP / 'segan' / 'figuras'
OUT.mkdir(parents=True, exist_ok=True)
RES = R.REPO / 'resultados'

COL_DOBLE = 7.2
plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'mathtext.fontset': 'stix', 'font.size': 8.5, 'axes.labelsize': 8.5,
    'axes.labelcolor': '#52514e', 'axes.titlesize': 8.5,
    'xtick.labelsize': 7.5, 'ytick.labelsize': 7.5, 'legend.fontsize': 7.5,
    'xtick.color': '#898781', 'ytick.color': '#898781',
    'axes.edgecolor': '#c3c2b7', 'axes.linewidth': 0.6, 'lines.linewidth': 1.4,
    'savefig.facecolor': 'white', 'figure.facecolor': 'white',
    'pdf.fonttype': 42, 'ps.fonttype': 42,
})
TINTA_1, TINTA_2, MUTED = '#0b0b0b', '#52514e', '#898781'
HAIR = '#e1e0d9'
AZUL, NARANJA, MORADO, VERDE = '#2a78d6', '#eb6834', '#4a3aa7', '#1baf7a'


def guardar(fig, nombre):
    for ext in ('pdf', 'png'):
        fig.savefig(OUT / f'{nombre}.{ext}', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'  {nombre}.pdf y .png')


# ==========================================================================
def fig6_diagrama():
    fig, ax = plt.subplots(figsize=(COL_DOBLE, 3.9))
    ax.set_xlim(0, 100); ax.set_ylim(-2, 62); ax.axis('off')

    def caja(x, y, w, h, txt, fc='white', ec=TINTA_2, fs=7.3, lw=0.9, bold=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle='round,pad=0.6,rounding_size=1.4',
                                    fc=fc, ec=ec, lw=lw, zorder=2))
        ax.text(x + w / 2, y + h / 2, txt, ha='center', va='center',
                fontsize=fs, color=TINTA_1, zorder=3,
                fontweight='bold' if bold else 'normal')

    def flecha(x1, y1, x2, y2, ec=TINTA_2, ls='-', lw=0.9):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>',
                                     mutation_scale=8, color=ec, lw=lw,
                                     linestyle=ls, zorder=1,
                                     shrinkA=0, shrinkB=0))

    # ---- fila de entrada
    caja(1, 50, 20, 8, 'Base predictive $F_x$\n(hurdle or quantile GBM)', fc='#f7f6f3')
    caja(25, 50, 20, 8, 'Calibration set\nJan–Aug 2024', fc='#f7f6f3')
    caja(49, 50, 22, 8, 'Recent window\n$[t-67,\\ t-7)$, 60 days', fc='#f7f6f3')
    caja(75, 50, 24, 8, 'Realised $Y_t$\n(known only at $t$)', fc='#f7f6f3')

    # ---- score PIT
    caja(13, 38, 44, 8,
         'PIT score  $s=F_x(y)$,  atom at $y=0$ randomised:\n'
         '$s=(1-p)U$,  $U\\sim\\mathrm{Unif}(0,1)$')
    flecha(11, 50, 20, 46.5)
    flecha(35, 50, 35, 46.5)
    flecha(60, 50, 48, 46.5)

    # ---- transporte
    caja(4, 25, 46, 9,
         'Transport map, refreshed every 7 days\n'
         '$T=\\hat F_{\\mathrm{new}}^{-1}\\circ\\hat F_{\\mathrm{old}}$,  '
         '$B=150$ bootstrap replicates', ec=MORADO)
    flecha(30, 38, 27, 34.5, ec=MORADO)
    caja(4, 13, 46, 9,
         'Tail shrinkage towards the identity\n'
         '$\\lambda(u)=[1+(\\mathrm{sd}_{\\mathrm{boot}}(u)/\\tau)^2]^{-1}$,  '
         '$\\tau=0.05$', ec=MORADO)
    flecha(27, 25, 27, 22.5, ec=MORADO)
    caja(4, 3, 46, 7, 'Transported calibration pool  $T(s_{\\mathrm{cal}})$',
         ec=MORADO)
    flecha(27, 13, 27, 10.5, ec=MORADO)

    # ---- ACI
    caja(56, 25, 42, 9,
         'ACI update, delayed by the 7-day embargo\n'
         '$\\alpha_{t+1}=\\alpha_t+\\gamma(\\alpha-\\mathrm{err}_{t-7})$',
         ec=NARANJA)
    flecha(85, 50, 90, 34.5, ec=NARANJA)
    caja(56, 13, 42, 9,
         'Conformal quantile at the CURRENT $\\alpha_t$\n'
         '$\\hat q=$ order statistic $\\lceil (n{+}1)(1-\\alpha_t)\\rceil$',
         ec=NARANJA)
    flecha(77, 25, 77, 22.5, ec=NARANJA)
    flecha(50, 6.5, 55.4, 16.5, ec=MORADO, ls=(0, (3, 2)))

    caja(56, 3, 42, 7, 'Upper prediction limit  $U_t=F_x^{-1}(\\hat q)$',
         ec=TINTA_1, lw=1.3, bold=True)
    flecha(77, 13, 77, 10.5, ec=NARANJA)

    # ---- orden de ejecucion
    ax.text(50, 60.4, 'Execution order within date $t$:  '
            '(i) refresh map  $\\rightarrow$  (ii) quantile at the current '
            '$\\alpha_t$  $\\rightarrow$  (iii) emit interval  $\\rightarrow$  '
            '(iv) error enters the embargo queue',
            ha='center', va='center', fontsize=7.6, color=TINTA_1)
    ax.text(6, 35.6, 'transport branch', ha='left', fontsize=7,
            color=MORADO, style='italic')
    ax.text(98, 35.6, 'adaptive branch', ha='right', fontsize=7,
            color=NARANJA, style='italic')
    ax.text(53, 1.0, 'the only coupling between the two branches is the pool',
            ha='center', va='center', fontsize=6.6, color=MUTED, style='italic')
    guardar(fig, 'fig6_algorithm_flow')


# ==========================================================================
def fig7_model_agnostic():
    d = pd.read_csv(RES / 'fase0' / 'fase0_diagnostico.csv')
    t = pd.read_csv(RES / 'fase0' / 'fase0_tabla_por_modelo.csv')
    ETQ = {'hurdle': 'Hurdle\n(constant $\\sigma$)',
           'hurdle_sigma_x': 'Hurdle\n($\\sigma(x)$)',
           'qgbm_multi': 'Quantile GBM\n(54 quantiles)'}
    orden = ['hurdle', 'hurdle_sigma_x', 'qgbm_multi']

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(COL_DOBLE, 3.0),
                                 gridspec_kw={'width_ratios': [1, 1.12]})

    tr = t[t.periodo == 'test_transition'].set_index(['modelo_base', 'metodo'])
    x = np.arange(3); w = 0.36
    est = [tr.loc[(m, '1_estatico_pit')].ancho_medio for m in orden]
    ada = [tr.loc[(m, '4_transporte_banda_g05')].ancho_medio for m in orden]
    ce = [tr.loc[(m, '1_estatico_pit')].cobertura for m in orden]
    ca = [tr.loc[(m, '4_transporte_banda_g05')].cobertura for m in orden]
    a1.bar(x - w / 2, est, w, color=TINTA_2, label='Static split', zorder=3)
    a1.bar(x + w / 2, ada, w, color=MORADO, hatch='xxxx', edgecolor='white',
           linewidth=0.4, label='Transport + ACI ($\\gamma=0.05$)', zorder=3)
    for i in range(3):
        a1.text(x[i] - w / 2, est[i] + 22, f'{ce[i]:.1f}%', ha='center',
                fontsize=6.8, color=TINTA_2)
        a1.text(x[i] + w / 2, ada[i] + 22, f'{ca[i]:.1f}%', ha='center',
                fontsize=6.8, color=MORADO)
        pc = 100 * (ada[i] / est[i] - 1)
        alto = max(est[i], ada[i]) + 120
        a1.annotate('', xy=(x[i] + w / 2, alto), xytext=(x[i] - w / 2, alto),
                    arrowprops=dict(arrowstyle='-|>', lw=0.7, color=MUTED,
                                    shrinkA=0, shrinkB=0))
        a1.text(x[i], alto + 30, f'{pc:+.1f}%', ha='center', fontsize=7.6,
                color=NARANJA if pc > 0 else VERDE, fontweight='bold')
    a1.set_xticks(x); a1.set_xticklabels([ETQ[m] for m in orden], fontsize=7.2)
    a1.set_ylabel('Mean interval width, MWh')
    a1.set_ylim(0, 1620)
    a1.legend(loc='upper right', frameon=False, fontsize=6.9)
    a1.spines[['top', 'right']].set_visible(False)
    a1.set_axisbelow(True)
    a1.yaxis.grid(True, color=HAIR, linewidth=0.6)

    MK = {'hurdle': 'o', 'hurdle_sigma_x': 's', 'qgbm_multi': 'D'}
    CO = {'hurdle': TINTA_1, 'hurdle_sigma_x': AZUL, 'qgbm_multi': VERDE}
    for m in orden:
        s = d[d.modelo_base == m]
        a2.scatter(s.sobrecobertura_pp, s.cambio_ancho_pct, s=34,
                   marker=MK[m], facecolor=CO[m], edgecolor='white',
                   linewidth=0.6, zorder=3,
                   label=ETQ[m].replace('\n', ' '))
    xs = np.linspace(d.sobrecobertura_pp.min() - 0.4,
                     d.sobrecobertura_pp.max() + 0.4, 50)
    b = np.polyfit(d.sobrecobertura_pp, d.cambio_ancho_pct, 1)
    r = float(np.corrcoef(d.sobrecobertura_pp, d.cambio_ancho_pct)[0, 1])
    a2.plot(xs, np.polyval(b, xs), color=NARANJA, lw=1.1, zorder=2)
    a2.axhline(0, color=MUTED, lw=0.7, ls=':', zorder=1)
    a2.text(0.97, 0.05,
            f'$r={r:.3f}$\nslope ${b[0]:.2f}$ %/pp\nintercept ${b[1]:+.2f}$ %',
            transform=a2.transAxes, ha='right', va='bottom', fontsize=7,
            color=NARANJA)
    a2.set_xlabel('Over-coverage of the static split, pp above nominal')
    a2.set_ylabel('Width change of Transport + ACI, %')
    a2.legend(loc='upper right', frameon=False, fontsize=6.9)
    a2.spines[['top', 'right']].set_visible(False)
    a2.set_axisbelow(True)
    a2.grid(True, color=HAIR, linewidth=0.6)
    fig.tight_layout(w_pad=1.8)
    guardar(fig, 'fig7_model_agnostic')


# ==========================================================================
def fig8_ablations():
    ap = pd.read_csv(RES / 'fase2' / 'fase2_aporte_por_componente.csv')
    ab = pd.read_csv(RES / 'fase2' / 'fase2_ablaciones.csv')
    comp = ['adaptacion online (A1 - A0)', 'transporte sin ACI (A2 - A0)',
            'transporte sobre ACI (A3 - A1)', 'shrinkage de cola (A4 - A3)',
            'pipeline completo (A4 - A0)']
    ETQ = {comp[0]: 'Online adaptation\n(ACI over static)',
           comp[1]: 'Transport alone\n(over static)',
           comp[2]: 'Transport added\nto ACI',
           comp[3]: 'Tail shrinkage\nadded to transport',
           comp[4]: 'Full pipeline\n(over static)'}
    PER = ['test_pre', 'test_transition', '2025-S1', '2025-S2', '2026-S1',
           'TEST_COMPLETO']
    ETQP = {'test_pre': "Sep '24", 'test_transition': "Oct–Dec '24",
            '2025-S1': '2025-S1', '2025-S2': '2025-S2', '2026-S1': '2026-S1',
            'TEST_COMPLETO': 'Whole test'}

    fig, axes = plt.subplots(1, 5, figsize=(COL_DOBLE, 2.55), sharey=True)
    for ax, c in zip(axes, comp):
        s = ap[ap.componente == c].set_index('periodo').reindex(PER)
        y = np.arange(len(PER))[::-1]
        for i, (p, r) in zip(y, s.iterrows()):
            sig = r.significativo == 'si'
            col = (VERDE if r.d_IS < 0 else NARANJA) if sig else MUTED
            ax.plot([r.IS_lo, r.IS_hi], [i, i], color=col,
                    lw=2.2 if p == 'TEST_COMPLETO' else 1.4,
                    solid_capstyle='round', zorder=2, alpha=0.85)
            ax.scatter([r.d_IS], [i], s=22 if p == 'TEST_COMPLETO' else 14,
                       facecolor=col, edgecolor='white', linewidth=0.5, zorder=3)
        ax.axvline(0, color=TINTA_2, lw=0.7, ls=':', zorder=1)
        ax.set_yticks(y)
        ax.set_yticklabels([ETQP[p] for p in PER], fontsize=6.9)
        ax.set_title(ETQ[c], fontsize=7.1, color=TINTA_1, pad=6)
        ax.set_xlim(-300, 250)
        ax.set_xticks([-250, 0, 250])
        ax.tick_params(axis='x', labelsize=6.6)
        ax.spines[['top', 'right', 'left']].set_visible(False)
        ax.set_axisbelow(True)
        ax.xaxis.grid(True, color=HAIR, linewidth=0.5)
    costo = {comp[0]: '+0.2 s', comp[1]: '+7.1 s', comp[2]: '+0.4 s',
             comp[3]: '+6.1 s', comp[4]: '+6.7 s'}
    for ax, c in zip(axes, comp):
        ax.text(0.5, -0.19, f'runtime {costo[c]}', transform=ax.transAxes,
                ha='center', fontsize=6.6, color=MUTED, style='italic')
    axes[2].set_xlabel('Change in mean interval score, MWh '
                       '(negative is better)', fontsize=7.4, labelpad=16)
    fig.tight_layout(w_pad=0.7)
    guardar(fig, 'fig8_ablations')


if __name__ == '__main__':
    print('Figuras nuevas de la revision:')
    fig6_diagrama()
    fig7_model_agnostic()
    fig8_ablations()
    print(f'guardadas en {OUT}')
