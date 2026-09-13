#!/usr/bin/env python3
"""
FASE 0b: el diagnostico sobre TODAS las celdas disponibles.
===========================================================
Comentario R1.1, que pidio verificar la propiedad de agnosticismo al modelo base
y la estabilidad del metodo A TRAVES DE DISTINTOS MODELOS BASE. La version
anterior respondio con tres. La escalera de capacidad de la verificacion
independiente dejo ocho ya evaluados con la capa conformal completa en las cinco
ventanas, asi que la pregunta se puede responder sobre cuarenta celdas.

BRAZOS (ocho modelos base, cinco ventanas cada uno):
  hurdle_400        hurdle, 2 x 400 arboles (el modelo base oficial)
  hurdle_2000       hurdle, 2 x 2000 arboles
  hurdle_sigma_x    hurdle con dispersion condicional
  qgbm_54x15        GBM multi-cuantil, 54 niveles x 15 arboles
  qgbm_54x50        idem x 50
  qgbm_54x100       idem x 100
  qgbm_54x200       idem x 200
  qgbm_54x400       idem x 400 (el del manuscrito)

Se EXCLUYE qgbm_9x400: su split estatico devuelve 100% de intervalos infinitos,
el ancho es NaN y no produce una celda valida. Se documenta como nota al pie de
la limitacion de la Seccion 7, no se usa en el ajuste.

POR QUE IMPORTA. Las quince celdas del manuscrito cubren sobre-cobertura solo en
[-2.0, +5.3] pp. Los brazos de baja capacidad caen muy por debajo de cero, que es
la region donde el manuscrito no tiene un solo punto y de la que depende el
intercepto, que con quince celdas apenas excluye el cero.

ESQUEMA DE REMUESTREO. El mismo de obj2_incertidumbre_diagnostico.py: las celdas
forman un diseno cruzado (modelo base x ventana) y la aleatoriedad comun esta en
los dias, asi que se remuestrean DIAS COMPLETOS una sola vez por replica,
comunes a todas las celdas, y se recomputa el ajuste entero sobre ese
remuestreo. Condiciona sobre los modelos ajustados y sobre la trayectoria
secuencial de los metodos online: es incertidumbre de evaluacion, no de
entrenamiento.

Semilla 20260901. B = 2000.

Salidas: resultados/fase0b/

Comando:
  <venv>/bin/python flagship/revision/fase0b_diagnostico_ampliado.py
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rev_lib as R   # noqa: E402

SERIES = R.REPO / 'resultados' / 'verificacion' / 'series'
SAL = R.REPO / 'resultados' / 'fase0b'
SAL.mkdir(parents=True, exist_ok=True)
B = 2000
SEMILLA = R.SEED_BOOTSTRAP
NOMINAL = 100 * (1 - R.ALPHA)

# archivo de series -> etiqueta -> pertenece a las quince celdas originales.
#
# Los tres brazos originales se toman de los artefactos PUBLICADOS (los que
# escribe obj2 leyendo pred_hurdle.csv, pred_hurdle_hetero.csv y
# pred_qgbm_multi.csv.gz), no de los reentrenados por la escalera. Los CSV
# congelados guardan p_occ y mu_log con seis decimales, asi que un
# reentrenamiento difiere de ellos en torno a 1e-4 relativo en el limite
# superior. Es inmaterial, pero usando los publicados la restriccion a quince
# celdas reproduce exactamente la Tabla 5 del manuscrito, que es lo que se
# quiere poder afirmar.
BRAZOS = [
    ('hurdle',         'hurdle_400',     True),    # publicado: pred_hurdle.csv
    ('hurdle_2000',    'hurdle_2000',    False),   # nuevo, reentrenado
    ('hurdle_sigma_x', 'hurdle_sigma_x', True),    # publicado
    ('qgbm_54x15',     'qgbm_54x15',     False),   # nuevo
    ('qgbm_54x50',     'qgbm_54x50',     False),   # nuevo
    ('qgbm_54x100',    'qgbm_54x100',    False),   # nuevo
    ('qgbm_54x200',    'qgbm_54x200',    False),   # nuevo
    ('qgbm_multi',     'qgbm_54x400',    True),    # publicado: pred_qgbm_multi
]
EXCLUIDO = 'qgbm_9x400'


def cargar_series():
    out = {}
    for archivo, etq, _ in BRAZOS:
        f = SERIES / f'{archivo}.parquet'
        if not f.exists():
            raise SystemExit(
                f'falta {f}.\nCorre antes:\n'
                f'  flagship/revision/verificacion/obj1_capacidad_contra_forma.py\n'
                f'  flagship/revision/verificacion/obj1b_escalera_capacidad.py\n'
                f'  flagship/revision/verificacion/obj2_incertidumbre_diagnostico.py')
        d = pd.read_parquet(f)
        out[etq] = dict(f=pd.to_datetime(d.fecha.values), y=d.y.values,
                        U_est=d.U_est.values, U_tr=d.U_tr.values)
    return out


def celdas(series, sel=None):
    """(x, y, etiquetas). x = sobre-cobertura del split estatico en pp,
    y = cambio de ancho de Transporte+ACI frente al estatico, en %."""
    xs, ys, etq = [], [], []
    for modelo, d in series.items():
        for nombre, ini, fin in R.PERIODOS:
            if sel is not None:
                idx = sel[modelo][nombre]
                if len(idx) == 0:
                    return None
                y, Ue, Ut = d['y'][idx], d['U_est'][idx], d['U_tr'][idx]
            else:
                m = np.asarray((d['f'] >= ini) & (d['f'] < fin))
                y, Ue, Ut = d['y'][m], d['U_est'][m], d['U_tr'][m]
            fe, ft = np.isfinite(Ue), np.isfinite(Ut)
            if not fe.any() or not ft.any():
                return None
            xs.append(100 * float((y <= Ue).mean()) - NOMINAL)
            ys.append(100 * (float(Ut[ft].mean()) / float(Ue[fe].mean()) - 1))
            etq.append((modelo, nombre))
    return np.array(xs), np.array(ys), etq


def ajuste(x, y):
    b = np.polyfit(x, y, 1)
    return float(np.corrcoef(x, y)[0, 1]), float(b[0]), float(b[1])


def main():
    print('=' * 96)
    print('FASE 0b - DIAGNOSTICO AMPLIADO')
    print(f'ocho modelos base x cinco ventanas | bootstrap {B} | semilla {SEMILLA}')
    print(f'excluido del ajuste: {EXCLUIDO} (split estatico 100% infinito, ancho NaN)')
    print('=' * 96)
    series = cargar_series()
    for k, d in series.items():
        print(f'  {k:16s} {len(d["y"]):,} filas, '
              f'{len(np.unique(d["f"])):,} dias')

    x0, y0, etq = celdas(series)
    r0, m0, b0 = ajuste(x0, y0)
    print(f'\nCUARENTA CELDAS: r = {r0:.4f}   pendiente = {m0:.4f}   '
          f'intercepto = {b0:.4f}')
    print(f'  rango de sobre-cobertura cubierto: '
          f'[{x0.min():+.2f}, {x0.max():+.2f}] pp')

    orig = np.array([e[0] in [b[1] for b in BRAZOS if b[2]] for e in etq])
    r15, m15, b15 = ajuste(x0[orig], y0[orig])
    print(f'\nrestringido a los tres brazos originales ({int(orig.sum())} celdas): '
          f'r = {r15:.4f}  pendiente = {m15:.4f}  intercepto = {b15:.4f}')
    print(f'  rango cubierto: [{x0[orig].min():+.2f}, {x0[orig].max():+.2f}] pp')

    # El enunciado se acota a la sobre-cobertura, asi que se reporta tambien el
    # ajuste sobre las celdas en que el split estatico sobre-cubre (x >= 0). El
    # conjunto se fija en la muestra completa y en cada replica se recomputan x
    # e y de esas mismas celdas; no consume numeros aleatorios, de modo que los
    # intervalos de las cuarenta celdas no cambian.
    sob = x0 >= 0
    rs, ms, bs = ajuste(x0[sob], y0[sob])
    print(f'\nrestringido a las celdas que sobre-cubren ({int(sob.sum())} celdas): '
          f'r = {rs:.4f}  pendiente = {ms:.4f}  intercepto = {bs:.4f}')

    # ---------- bootstrap por bloques de dia, comun a todas las celdas -------
    rng = np.random.default_rng(SEMILLA)
    por_dia, dias_ventana = {}, {}
    for modelo, d in series.items():
        por_dia[modelo] = {}
        for nombre, ini, fin in R.PERIODOS:
            m = np.asarray((d['f'] >= ini) & (d['f'] < fin))
            g = pd.Series(np.flatnonzero(m)).groupby(d['f'][m]).apply(np.array)
            por_dia[modelo][nombre] = g
            dias_ventana.setdefault(nombre, len(g))

    reps, reps_sob = [], []
    for _ in range(B):
        elegidos = {nm: rng.integers(0, n, n) for nm, n in dias_ventana.items()}
        sel = {}
        for modelo in series:
            sel[modelo] = {}
            for nm, k in elegidos.items():
                g = por_dia[modelo][nm]
                kk = k[k < len(g)]
                sel[modelo][nm] = (np.concatenate(g.values[kk]) if len(kk)
                                   else np.array([], dtype=int))
        c = celdas(series, sel)
        if c is not None:
            reps.append(ajuste(c[0], c[1]))
            reps_sob.append(ajuste(c[0][sob], c[1][sob]))
    reps, reps_sob = np.array(reps), np.array(reps_sob)

    ic = {}
    print(f'\nbootstrap ({len(reps)} replicas validas de {B}):')
    for j, nm in enumerate(('r', 'pendiente', 'intercepto')):
        lo, hi = np.percentile(reps[:, j], [2.5, 97.5])
        ic[nm] = dict(punto=[r0, m0, b0][j], lo=float(lo), hi=float(hi),
                      excluye_cero=bool(lo * hi > 0))
        print(f'  {nm:11s} {[r0, m0, b0][j]:+9.4f}   IC 95% [{lo:+.4f}, {hi:+.4f}]'
              f'   {"excluye el cero" if lo * hi > 0 else "CRUZA CERO"}')
    ic_sob = {}
    print(f'  celdas que sobre-cubren ({int(sob.sum())}):')
    for j, nm in enumerate(('r', 'pendiente', 'intercepto')):
        lo, hi = np.percentile(reps_sob[:, j], [2.5, 97.5])
        ic_sob[nm] = dict(punto=[rs, ms, bs][j], lo=float(lo), hi=float(hi),
                          excluye_cero=bool(lo * hi > 0))
        print(f'  {nm:11s} {[rs, ms, bs][j]:+9.4f}   IC 95% [{lo:+.4f}, {hi:+.4f}]')

    # ---------- robustez ------------------------------------------------
    loo = [(etq[i], *ajuste(np.delete(x0, i), np.delete(y0, i)))
           for i in range(len(x0))]
    rr = np.array([l[1] for l in loo])
    print(f'\ndejar-una-celda-fuera ({len(loo)} reajustes): r de {rr.min():.4f} '
          f'a {rr.max():.4f}')
    peor = min(loo, key=lambda l: abs(l[1]))
    print(f'  celda mas influyente: {peor[0]} -> r = {peor[1]:.4f}')

    print('\ndejar-un-modelo-base-fuera:')
    fuera = {}
    for _, modelo, _ in BRAZOS:
        k = np.array([e[0] != modelo for e in etq])
        r, m, b = ajuste(x0[k], y0[k])
        fuera[modelo] = dict(r=r, pendiente=m, intercepto=b, n=int(k.sum()))
        print(f'  sin {modelo:16s} n={int(k.sum()):2d}  r = {r:+.4f}  '
              f'pendiente = {m:+.3f}  intercepto = {b:+.3f}')

    # ---------- enunciado simetrico: las dos condiciones -----------------
    print('\n' + '=' * 96)
    print('ENUNCIADO SIMETRICO: condiciones (i) y (ii)')
    print('=' * 96)
    n_neg = int((x0 < -2).sum())
    cond_i = n_neg >= 5
    print(f'(i) celdas con sobre-cobertura por debajo de -2 pp: {n_neg} '
          f'(se exigen 5) -> {"SE CUMPLE" if cond_i else "NO SE CUMPLE"}')

    # ajuste por tramos contra ajuste unico, con corte en x = 0
    neg, pos = x0 < 0, x0 >= 0
    sse_unico = float(((y0 - np.polyval(np.polyfit(x0, y0, 1), x0)) ** 2).sum())
    sse_tramos = 0.0
    for m_ in (neg, pos):
        if m_.sum() >= 3:
            sse_tramos += float(((y0[m_] - np.polyval(
                np.polyfit(x0[m_], y0[m_], 1), x0[m_])) ** 2).sum())
        else:
            sse_tramos = np.nan
    gl1, gl2 = len(x0) - 2, len(x0) - 4
    Fst = ((sse_unico - sse_tramos) / (gl1 - gl2)) / (sse_tramos / gl2)
    from scipy.stats import f as fdist
    p_chow = float(1 - fdist.cdf(Fst, gl1 - gl2, gl2))
    cond_ii = p_chow > 0.05
    print(f'(ii) ajuste por tramos con corte en x = 0 contra ajuste unico:')
    print(f'     SSE unico {sse_unico:.1f}, SSE por tramos {sse_tramos:.1f}')
    print(f'     F({gl1 - gl2}, {gl2}) = {Fst:.3f}, p = {p_chow:.4f}')
    print(f'     -> {"no hay quiebre detectable, SE CUMPLE" if cond_ii else "HAY QUIEBRE, NO SE CUMPLE"}')
    adoptar = cond_i and cond_ii
    print(f'\nADOPTAR EL ENUNCIADO SIMETRICO: {"SI" if adoptar else "NO"}')
    if not adoptar:
        print('  Se conserva el enunciado actual, acotado a la sobre-cobertura.')

    # El quiebre, ¿es de nivel o de pendiente? Se separa en dos contrastes
    # anidados: primero se deja variar solo la ordenada por tramo, con pendiente
    # comun; luego se deja variar tambien la pendiente. Importa para la
    # redaccion: un quiebre de nivel con pendiente comun dice que la TASA a la
    # que la capa convierte desviacion de cobertura en ancho es la misma a ambos
    # lados, y que lo que cambia es la ordenada.
    def sse(M, v):
        b, *_ = np.linalg.lstsq(M, v, rcond=None)
        return float(((v - M @ b) ** 2).sum())

    uno = np.ones_like(x0)
    M0 = np.column_stack([uno, x0])
    M1 = np.column_stack([uno, x0, neg.astype(float)])
    M2 = np.column_stack([uno, x0, neg.astype(float), neg * x0])
    s0, s1, s2 = sse(M0, y0), sse(M1, y0), sse(M2, y0)
    n = len(x0)
    F_niv = ((s0 - s1) / 1) / (s1 / (n - 3))
    F_pen = ((s1 - s2) / 1) / (s2 / (n - 4))
    p_niv = float(1 - fdist.cdf(F_niv, 1, n - 3))
    p_pen = float(1 - fdist.cdf(F_pen, 1, n - 4))
    bcom, *_ = np.linalg.lstsq(M1, y0, rcond=None)
    print(f'\n  descomposicion del quiebre:')
    print(f'    solo el nivel difiere (pendiente comun): F(1,{n-3}) = {F_niv:.3f}, p = {p_niv:.4f}')
    print(f'    ademas difiere la pendiente:             F(1,{n-4}) = {F_pen:.3f}, p = {p_pen:.4f}')
    print(f'    con pendiente comun: pendiente {bcom[1]:+.3f}, '
          f'salto de nivel en el tramo negativo {bcom[2]:+.3f} %')
    quiebre = dict(F_nivel=float(F_niv), p_nivel=p_niv, F_pendiente=float(F_pen),
                   p_pendiente=p_pen, pendiente_comun=float(bcom[1]),
                   salto_nivel_pct=float(bcom[2]))

    # pendientes por tramo, informativas
    for etqt, m_ in (('sobre-cobertura negativa', neg), ('positiva', pos)):
        if m_.sum() >= 3:
            rt, mt, bt = ajuste(x0[m_], y0[m_])
            print(f'  tramo de {etqt:26s} n={int(m_.sum()):2d}  '
                  f'r = {rt:+.4f}  pendiente = {mt:+.3f}')

    # ---------- salidas -------------------------------------------------
    pd.DataFrame([dict(modelo_base=e[0], ventana=e[1], sobrecobertura_pp=round(a, 4),
                       cambio_ancho_pct=round(c, 4),
                       en_las_quince_originales=bool(o))
                  for e, a, c, o in zip(etq, x0, y0, orig)]).to_csv(
        SAL / 'fase0b_celdas.csv', index=False)
    json.dump(dict(
        n_celdas=len(x0), n_modelos=len(series), B=B, semilla=SEMILLA,
        excluido=EXCLUIDO,
        cuarenta=dict(r=r0, pendiente=m0, intercepto=b0),
        quince_originales=dict(r=r15, pendiente=m15, intercepto=b15,
                               n=int(orig.sum())),
        ic_bootstrap=ic,
        rango_x=[float(x0.min()), float(x0.max())],
        loo_r=[float(l[1]) for l in loo],
        sin_modelo=fuera,
        simetrico=dict(n_celdas_bajo_menos2=n_neg, condicion_i=bool(cond_i),
                       F=float(Fst), p=p_chow, condicion_ii=bool(cond_ii),
                       adoptar=bool(adoptar), quiebre=quiebre),
        sobrecubren=dict(n=int(sob.sum()), r=rs, pendiente=ms, intercepto=bs,
                         rango=[float(x0[sob].min()), float(x0[sob].max())],
                         ic_bootstrap=ic_sob),
    ), open(SAL / 'fase0b_diagnostico.json', 'w'), indent=1)
    print(f'\nguardado en {SAL.relative_to(R.REPO)}/')


if __name__ == '__main__':
    main()
