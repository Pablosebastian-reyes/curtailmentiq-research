#!/usr/bin/env python3
"""
OBJECION 2: incertidumbre del diagnostico (r, pendiente, intercepto).
=====================================================================
El paper reporta r = -0.757, pendiente -4.39 e intercepto +5.49 sobre 15 celdas,
SIN intervalo, mientras que reporta intervalo bootstrap por bloques de dia en
cada diferencia de ancho. Es una inconsistencia visible.

ESTRUCTURA DE DEPENDENCIA. Las 15 celdas son 3 modelos base x 5 ventanas. No son
independientes por dos vias cruzadas: las cinco celdas de un mismo modelo base
comparten la predictiva ajustada, y las tres celdas de una misma ventana
comparten los mismos dias y los mismos desenlaces. Es un diseno CRUZADO, no
anidado, asi que remuestrear celdas (o modelos, o ventanas) seria incorrecto:
con 3 y 5 niveles no hay material para remuestrear ninguno de los dos factores.

ESQUEMA CORRECTO. La aleatoriedad comun a las 15 celdas esta en los DIAS: tanto
la sobre-cobertura del split estatico como el cambio de ancho de Transport+ACI
se calculan, en toda celda, sobre el mismo panel de dias-central. Entonces se
remuestrean DIAS COMPLETOS una sola vez por replica, se recomputan LAS 15 CELDAS
sobre ese mismo remuestreo, y se reajusta la recta. Eso preserva exactamente la
dependencia cruzada, porque toda celda ve el mismo conjunto de dias.

QUE CONDICIONA. El intervalo es de la incertidumbre de EVALUACION: se mantienen
fijos los modelos ajustados y la trayectoria secuencial de los metodos online (no
se puede re-correr un ACI sobre dias barajados sin destruir su orden temporal).
Es el mismo condicionamiento que ya usa el paper para las diferencias de ancho.
No cubre la incertidumbre de entrenamiento del modelo base.

Ademas se reporta:
  - dejar-uno-fuera por celda (15 reajustes)
  - dejar-un-modelo-base-fuera (3 reajustes), que es la pregunta dura: si se
    quita el hurdle, que aporta el punto extremo, ¿queda relacion?

Salida: resultados/verificacion/obj2_incertidumbre.json y .md
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'flagship' / 'revision'))
import rev_lib as R                      # noqa: E402
sys.path.insert(0, str(REPO / 'flagship' / 'revision'))
import fase0_model_agnostic as F0        # noqa: E402

SAL = REPO / 'resultados' / 'verificacion'
SERIES = SAL / 'series'
B = 2000
SEMILLA = 20260901
NOMINAL = 100 * (1 - R.ALPHA)


def series_por_modelo():
    """Recalcula U del split estatico y de Transport+ACI(0.05) para los tres
    modelos base, con el mismo orden de consumo del RNG que el experimento."""
    out = {}
    for nombre, cargador in (('hurdle', F0.cargar_hurdle),
                             ('hurdle_sigma_x', F0.cargar_hurdle_hetero),
                             ('qgbm_multi', F0.cargar_qgbm)):
        h, pred, _ = cargador()
        rng = np.random.default_rng(R.SEED_CONFORMAL)
        h = h.assign(s=pred.cdf(h.y_real.values, rng))
        s_cal = h.s.values[((h.fecha >= R.CAL_INI) & (h.fecha < R.CAL_FIN)).values]
        idx = (h.fecha >= R.CAL_FIN).values
        test = h[idx].reset_index(drop=True)
        p_t = pred.sub(idx)
        y_t, f_t = test.y_real.values, test.fecha.values
        fechas = np.sort(test.fecha.unique())

        U_est = R.estatico(p_t, s_cal)
        # el mismo rng sigue consumiendose: primero g=0.02, luego g=0.05
        R.transporte_aci(p_t, s_cal, h.s.values, h.fecha.values, y_t, f_t,
                         fechas, 0.02, rng, ini_test=R.CAL_FIN)
        U_tr, _, _ = R.transporte_aci(p_t, s_cal, h.s.values, h.fecha.values,
                                      y_t, f_t, fechas, 0.05, rng,
                                      ini_test=R.CAL_FIN)
        out[nombre] = dict(y=y_t, f=pd.to_datetime(f_t), U_est=U_est, U_tr=U_tr)
        # se persisten en el mismo formato que las de obj1, para que el
        # diagnostico ampliado de la Fase 0b pueda leer los ocho brazos de un
        # solo sitio. hurdle_400 de obj1 y hurdle de aqui son el mismo modelo,
        # lo que sirve ademas de chequeo cruzado.
        SERIES.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(dict(fecha=f_t, y=y_t, U_est=U_est, U_tr=U_tr)).to_parquet(
            SERIES / f'{nombre}.parquet', index=False)
        print(f'  {nombre}: {len(y_t):,} filas, {len(fechas)} dias')
    return out


def celdas(series, dias_sel=None):
    """Las 15 celdas (x = sobre-cobertura del estatico, y = cambio de ancho %).
    Si dias_sel se pasa, se restringe a esos dias (con repeticion)."""
    xs, ys, etq = [], [], []
    for modelo, d in series.items():
        for nombre, ini, fin in R.PERIODOS:
            m = np.asarray((d['f'] >= ini) & (d['f'] < fin))
            if dias_sel is not None:
                idx = dias_sel[modelo][nombre]
                if len(idx) == 0:
                    return None
                y, Ue, Ut = d['y'][idx], d['U_est'][idx], d['U_tr'][idx]
            else:
                y, Ue, Ut = d['y'][m], d['U_est'][m], d['U_tr'][m]
            fe, ft = np.isfinite(Ue), np.isfinite(Ut)
            if not fe.any() or not ft.any():
                return None
            cob = 100 * float((y <= Ue).mean())
            we, wt = float(Ue[fe].mean()), float(Ut[ft].mean())
            xs.append(cob - NOMINAL)
            ys.append(100 * (wt / we - 1))
            etq.append((modelo, nombre))
    return np.array(xs), np.array(ys), etq


def ajuste(x, y):
    b = np.polyfit(x, y, 1)
    r = float(np.corrcoef(x, y)[0, 1])
    return r, float(b[0]), float(b[1])


def main():
    print('=' * 92)
    print('OBJECION 2 - INCERTIDUMBRE DEL DIAGNOSTICO')
    print(f'bootstrap de {B} remuestreos de DIAS COMPLETOS, comunes a las 15 celdas')
    print('=' * 92)
    series = series_por_modelo()

    x0, y0, etq = celdas(series)
    r0, m0, b0 = ajuste(x0, y0)
    print(f'\npunto estimado sobre las 15 celdas:')
    print(f'  r = {r0:.4f}   pendiente = {m0:.4f}   intercepto = {b0:.4f}')

    # ---- bootstrap por bloques de dia, comun a todas las celdas ----
    rng = np.random.default_rng(SEMILLA)
    # indices de fila agrupados por dia, por modelo y ventana
    por_dia = {}
    dias_por_ventana = {}
    for modelo, d in series.items():
        por_dia[modelo] = {}
        for nombre, ini, fin in R.PERIODOS:
            m = np.asarray((d['f'] >= ini) & (d['f'] < fin))
            sub = pd.Series(np.flatnonzero(m)).groupby(d['f'][m].values).apply(np.array)
            por_dia[modelo][nombre] = sub
            dias_por_ventana.setdefault(nombre, sub.index.values)

    reps = []
    for _ in range(B):
        sel = {}
        # UN solo remuestreo de dias por ventana, compartido por los 3 modelos:
        # asi la dependencia cruzada entre modelos queda preservada
        elegidos = {nm: rng.integers(0, len(d), len(d))
                    for nm, d in dias_por_ventana.items()}
        for modelo in series:
            sel[modelo] = {}
            for nm in dias_por_ventana:
                grupos = por_dia[modelo][nm]
                k = elegidos[nm]
                k = k[k < len(grupos)]
                sel[modelo][nm] = (np.concatenate(grupos.values[k])
                                   if len(k) else np.array([], dtype=int))
        c = celdas(series, sel)
        if c is None:
            continue
        reps.append(ajuste(c[0], c[1]))
    reps = np.array(reps)
    nombres = ('r', 'pendiente', 'intercepto')
    ic = {}
    print(f'\nbootstrap ({len(reps)} replicas validas de {B}):')
    for j, nm in enumerate(nombres):
        lo, hi = np.percentile(reps[:, j], [2.5, 97.5])
        ic[nm] = dict(punto=[r0, m0, b0][j], lo=float(lo), hi=float(hi),
                      cruza_cero=bool(lo * hi < 0))
        print(f'  {nm:11s} {[r0, m0, b0][j]:+8.4f}   IC 95% [{lo:+.4f}, {hi:+.4f}]'
              f'   {"CRUZA CERO" if lo * hi < 0 else "excluye el cero"}')

    # ---- dejar uno fuera ----
    print('\ndejar-una-celda-fuera (15 reajustes):')
    loo = []
    for i in range(len(x0)):
        k = np.arange(len(x0)) != i
        loo.append((etq[i], *ajuste(x0[k], y0[k])))
    rr = np.array([l[1] for l in loo])
    print(f'  r va de {rr.min():.4f} a {rr.max():.4f}')
    peor = min(loo, key=lambda l: abs(l[1]))
    print(f'  celda mas influyente: {peor[0]} -> al quitarla r = {peor[1]:.4f}')

    print('\ndejar-un-modelo-base-fuera (la pregunta dura):')
    fuera = {}
    for modelo in series:
        k = np.array([e[0] != modelo for e in etq])
        r, m, b = ajuste(x0[k], y0[k])
        fuera[modelo] = dict(r=r, pendiente=m, intercepto=b, n=int(k.sum()))
        print(f'  sin {modelo:16s} n={int(k.sum()):2d}  r = {r:+.4f}  '
              f'pendiente = {m:+.3f}  intercepto = {b:+.3f}')

    json.dump(dict(punto=dict(r=r0, pendiente=m0, intercepto=b0),
                   ic_bootstrap=ic, n_replicas=len(reps), B=B, semilla=SEMILLA,
                   loo_r=[float(l[1]) for l in loo],
                   sin_modelo=fuera,
                   celdas=[dict(modelo=e[0], ventana=e[1], x=float(a), y=float(c))
                           for e, a, c in zip(etq, x0, y0)]),
              open(SAL / 'obj2_incertidumbre.json', 'w'), indent=1)
    print(f'\nguardado {SAL / "obj2_incertidumbre.json"}')


if __name__ == '__main__':
    main()
