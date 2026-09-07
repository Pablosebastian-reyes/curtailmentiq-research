#!/usr/bin/env python3
"""
FASE 0c: robustez del quiebre de ordenada del diagnostico.
==========================================================
La Fase 0b detecto que ajustar por separado los dos lados del nivel nominal
mejora el ajuste mas de lo que explicaria el azar, y que la mejora es de ORDENADA
y no de pendiente. Esa deteccion es lo que impide enunciar el diagnostico de
forma simetrica. Antes de escribirla en el manuscrito hay que saber de que
depende.

La sospecha concreta es que el quiebre lo sostenga un solo brazo. Las celdas por
debajo del nivel nominal vienen casi todas del GBM de capacidad mas baja
(qgbm_54x15), que es tambien el unico que llega a $-8$ puntos porcentuales. Si al
quitarlo el quiebre desaparece, no es un rasgo del mecanismo sino de un brazo.

Se computan seis cosas:

  1. Composicion por modelo base de las celdas bajo 0, -2 y -3 pp.
  2. El test de quiebre de ordenada, con las cuarenta celdas y sin qgbm_54x15.
  3. Dejar-un-brazo-fuera sobre el tamano del salto.
  4. El mismo test con efecto fijo por modelo base, que absorbe cualquier
     desplazamiento constante propio de cada predictiva y deja el quiebre
     identificado solo por la variacion dentro de brazo.
  5. El ajuste sobre las 35 celdas sin qgbm_54x15, evaluado FUERA DE MUESTRA
     sobre las cinco celdas de ese brazo. Es la prueba dura: si la
     especificacion con quiebre, estimada sin ver el brazo extremo, predice ese
     brazo mejor que la recta unica, el quiebre es una propiedad de la relacion
     y no un artefacto de esas cinco celdas.
  6. La comparacion contra una especificacion cuadratica, por si lo que hay no
     es un quiebre sino curvatura.

ADVERTENCIA ESTADISTICA, que el manuscrito repite. Los test F de aqui tratan las
cuarenta celdas como observaciones independientes, y no lo son: se agrupan de a
cinco por modelo base y de a ocho por ventana, y comparten el panel subyacente.
Los p que salen son por tanto optimistas. Se reportan como RAZON PARA NO AMPLIAR
la afirmacion, que es una direccion conservadora, y no como evidencia de que el
quiebre exista. Los intervalos que sí gobiernan las afirmaciones del paper son
los bootstrap por bloques de dia de la Fase 0b.

Entrada:  resultados/fase0b/fase0b_celdas.csv
Salidas:  resultados/fase0c/

Comando:
  <venv>/bin/python flagship/revision/fase0c_robustez_quiebre.py
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import f as fdist

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rev_lib as R   # noqa: E402

ENT = R.REPO / 'resultados' / 'fase0b' / 'fase0b_celdas.csv'
SAL = R.REPO / 'resultados' / 'fase0c'
SAL.mkdir(parents=True, exist_ok=True)
BRAZO_EXTREMO = 'qgbm_54x15'


def sse(M, v):
    b, *_ = np.linalg.lstsq(M, v, rcond=None)
    return float(((v - M @ b) ** 2).sum()), b


def test_F(M0, M1, y):
    """F del modelo anidado M0 dentro de M1."""
    s0, _ = sse(M0, y)
    s1, b1 = sse(M1, y)
    k0, k1 = M0.shape[1], M1.shape[1]
    gl = len(y) - k1
    F = ((s0 - s1) / (k1 - k0)) / (s1 / gl)
    return float(F), float(1 - fdist.cdf(F, k1 - k0, gl)), gl, b1


def diseno(x, con_salto=True, dummies=None):
    cols = [np.ones_like(x), x]
    if con_salto:
        cols.append((x < 0).astype(float))
    if dummies is not None:
        # se omite la primera columna para evitar colinealidad con el intercepto
        cols += [dummies[:, j] for j in range(1, dummies.shape[1])]
    return np.column_stack(cols)


def main():
    d = pd.read_csv(ENT)
    x, y = d.sobrecobertura_pp.values, d.cambio_ancho_pct.values
    mod = d.modelo_base.values
    print('=' * 96)
    print('FASE 0c - ROBUSTEZ DEL QUIEBRE DE ORDENADA')
    print(f'{len(d)} celdas, {d.modelo_base.nunique()} modelos base')
    print('=' * 96)
    out = {}

    # ---- 1. composicion de la region negativa ------------------------
    print('\n' + '-' * 96)
    print('1. QUIEN APORTA LAS CELDAS POR DEBAJO DEL NIVEL NOMINAL')
    print('-' * 96)
    comp = []
    for umbral in (0.0, -2.0, -3.0):
        sub = d[d.sobrecobertura_pp < umbral]
        cuenta = sub.modelo_base.value_counts().to_dict()
        comp.append(dict(umbral=umbral, n=len(sub), por_modelo=cuenta))
        print(f'  x < {umbral:+.0f} pp: {len(sub):2d} celdas  '
              + (', '.join(f'{k} {v}' for k, v in sorted(cuenta.items()))
                 if cuenta else '(ninguna)'))
    out['composicion'] = comp
    n_ext = int((d[d.sobrecobertura_pp < 0].modelo_base == BRAZO_EXTREMO).sum())
    n_neg = int((x < 0).sum())
    print(f'\n  de las {n_neg} celdas bajo el nominal, {n_ext} son de '
          f'{BRAZO_EXTREMO} ({100*n_ext/n_neg:.0f}%)')

    # ---- 2. quiebre de ordenada, con y sin el brazo extremo ----------
    print('\n' + '-' * 96)
    print('2. QUIEBRE DE ORDENADA')
    print('-' * 96)
    res2 = {}
    for etq, m in (('las 40 celdas', np.ones(len(x), bool)),
                   (f'sin {BRAZO_EXTREMO}', mod != BRAZO_EXTREMO)):
        F, p, gl, b = test_F(diseno(x[m], False), diseno(x[m], True), y[m])
        res2[etq] = dict(n=int(m.sum()), F=F, p=p, gl=gl,
                         pendiente=float(b[1]), salto=float(b[2]))
        print(f'  {etq:22s} n={int(m.sum()):2d}  F(1,{gl}) = {F:6.3f}  '
              f'p = {p:.4f}   pendiente {b[1]:+.3f}  salto {b[2]:+.3f}')
    out['quiebre'] = res2

    # ---- 3. dejar-un-brazo-fuera sobre el salto ----------------------
    print('\n' + '-' * 96)
    print('3. DEJAR-UN-BRAZO-FUERA sobre el tamano del salto')
    print('-' * 96)
    loo = {}
    for br in sorted(d.modelo_base.unique()):
        m = mod != br
        if (x[m] < 0).sum() < 3:
            print(f'  sin {br:16s} (quedan menos de 3 celdas negativas, se omite)')
            continue
        F, p, gl, b = test_F(diseno(x[m], False), diseno(x[m], True), y[m])
        loo[br] = dict(n=int(m.sum()), F=F, p=p, salto=float(b[2]),
                       pendiente=float(b[1]))
        print(f'  sin {br:16s} n={int(m.sum()):2d}  salto {b[2]:+7.3f}  '
              f'F(1,{gl}) = {F:6.3f}  p = {p:.4f}')
    out['dejar_un_brazo_fuera'] = loo
    saltos = [v['salto'] for v in loo.values()]
    print(f'\n  el salto se mueve entre {min(saltos):+.3f} y {max(saltos):+.3f}')

    # ---- 4. con efecto fijo por modelo base --------------------------
    print('\n' + '-' * 96)
    print('4. EL MISMO TEST CON EFECTO FIJO POR MODELO BASE')
    print('-' * 96)
    print('  El efecto fijo absorbe cualquier desplazamiento constante propio de')
    print('  cada predictiva, asi que el quiebre queda identificado solo por la')
    print('  variacion DENTRO de cada brazo.')
    D = pd.get_dummies(pd.Series(mod)).values.astype(float)
    F, p, gl, b = test_F(diseno(x, False, D), diseno(x, True, D), y)
    out['efecto_fijo'] = dict(F=F, p=p, gl=gl, salto=float(b[2]),
                              pendiente=float(b[1]))
    print(f'\n  F(1,{gl}) = {F:.3f}  p = {p:.4f}   pendiente {b[1]:+.3f}  '
          f'salto {b[2]:+.3f}')

    # ---- 5. prediccion fuera de muestra del brazo extremo ------------
    print('\n' + '-' * 96)
    print(f'5. AJUSTE SIN {BRAZO_EXTREMO}, EVALUADO SOBRE SUS CINCO CELDAS')
    print('-' * 96)
    ins, fue = mod != BRAZO_EXTREMO, mod == BRAZO_EXTREMO
    _, b_q = sse(diseno(x[ins], True), y[ins])     # con quiebre
    _, b_r = sse(diseno(x[ins], False), y[ins])    # recta unica
    filas = []
    for i in np.flatnonzero(fue):
        xi, yi = x[i], y[i]
        pq = b_q[0] + b_q[1] * xi + b_q[2] * (xi < 0)
        pr = b_r[0] + b_r[1] * xi
        filas.append(dict(ventana=d.ventana.values[i], x=float(xi),
                          observado=float(yi), pred_con_quiebre=float(pq),
                          pred_recta_unica=float(pr),
                          error_quiebre=float(yi - pq),
                          error_recta=float(yi - pr)))
    F5 = pd.DataFrame(filas).sort_values('x')
    print(f'  {"ventana":18s} {"x":>7} {"observado":>10} {"con quiebre":>12} '
          f'{"recta unica":>12} {"|err| quiebre":>14} {"|err| recta":>12}')
    for _, r_ in F5.iterrows():
        print(f'  {r_.ventana:18s} {r_.x:>+7.2f} {r_.observado:>+10.1f} '
              f'{r_.pred_con_quiebre:>+12.1f} {r_.pred_recta_unica:>+12.1f} '
              f'{abs(r_.error_quiebre):>14.1f} {abs(r_.error_recta):>12.1f}')
    eq = float(np.sqrt((F5.error_quiebre ** 2).mean()))
    er = float(np.sqrt((F5.error_recta ** 2).mean()))
    print(f'\n  RMSE fuera de muestra: con quiebre {eq:.2f}, recta unica {er:.2f}')
    out['fuera_de_muestra'] = dict(celdas=filas, rmse_quiebre=eq, rmse_recta=er,
                                   coef_quiebre=[float(v) for v in b_q],
                                   coef_recta=[float(v) for v in b_r])
    F5.to_csv(SAL / 'fase0c_fuera_de_muestra.csv', index=False)

    # ---- 6. contra una especificacion cuadratica ---------------------
    print('\n' + '-' * 96)
    print('6. CONTRA UNA ESPECIFICACION CUADRATICA')
    print('-' * 96)
    print('  Si lo que hay es curvatura y no un quiebre, un termino cuadratico')
    print('  deberia recogerlo.')
    cua = {}
    for etq, m in (('las 40 celdas', np.ones(len(x), bool)),
                   (f'sin {BRAZO_EXTREMO}', mod != BRAZO_EXTREMO)):
        M0 = diseno(x[m], False)
        M1 = np.column_stack([M0, x[m] ** 2])
        F, p, gl, b = test_F(M0, M1, y[m])
        cua[etq] = dict(n=int(m.sum()), F=F, p=p, gl=gl, coef=float(b[2]))
        print(f'  {etq:22s} n={int(m.sum()):2d}  F(1,{gl}) = {F:6.3f}  '
              f'p = {p:.4f}   coeficiente {b[2]:+.4f}')
    out['cuadratica'] = cua

    json.dump(out, open(SAL / 'fase0c_robustez.json', 'w'), indent=1)
    pd.DataFrame([dict(umbral=c['umbral'], n=c['n'], **c['por_modelo'])
                  for c in comp]).to_csv(SAL / 'fase0c_composicion.csv', index=False)
    print(f'\nguardado en {SAL.relative_to(R.REPO)}/')


if __name__ == '__main__':
    main()
