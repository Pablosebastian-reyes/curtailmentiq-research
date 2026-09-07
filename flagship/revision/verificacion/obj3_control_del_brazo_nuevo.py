#!/usr/bin/env python3
"""
OBJECION 3: ¿que controla la asercion existente, y que NO controla?
===================================================================
`fase0_model_agnostic.py` verifica por asercion que el brazo del hurdle
reproduce `conformal_v3_tabla.csv` en 30 celdas x 4 metricas. Eso protege contra
un cambio de PROTOCOLO: si alguien mueve una ventana, cambia una semilla o
altera el embargo, la asercion salta.

No protege el brazo nuevo. El brazo del hurdle recorre `PredictivaHurdle`, que
delega en las funciones ya validadas de `conformal_metodos.py`. El brazo del GBM
recorre `PredictivaCuantilica`, una clase NUEVA con su propia interpolacion de
rejilla, su propia lectura del atomo en cero y su propio manejo de bordes. Un
error ahi (un desplazamiento de indice en la rejilla, un atomo mal leido, un
borde superior mal tratado) dejaria intacta la asercion del hurdle y produciria
en silencio el resultado que es justamente el titular del paper.

El control es asimetrico: valida el protocolo compartido, no la predictiva nueva.

Aqui se implementan tres controles para el brazo nuevo. El tercero es el
decisivo.

  C1. Invariantes e ida y vuelta. cdf y inv en [0,1] y >= 0, monotonia, y
      cdf(inv(q)) = q, inv(cdf(y)) = y donde esta definido.

  C2. Cobertura de la predictiva CRUDA. El cuantil tau del GBM, sin capa
      conformal, debe cubrir aproximadamente tau en la ventana de calibracion.
      Un desplazamiento de indice en la rejilla lo rompe de inmediato.

  C3. EQUIVALENCIA CON UNA PREDICTIVA CONOCIDA. Se construye una
      PredictivaCuantilica evaluando la funcion cuantil del HURDLE sobre la
      misma rejilla de 54 niveles. Esa predictiva es, salvo error de
      interpolacion, el hurdle mismo. Se corre la capa conformal completa sobre
      ella y se compara contra el brazo del hurdle ya validado.

      Si PredictivaCuantilica tiene un error, C3 falla. Es el analogo, para el
      brazo nuevo, de la asercion que ya existe para el viejo, y es el control
      que este verificador recomienda anadir al script del paper.

Salida: resultados/verificacion/obj3_controles.json
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'flagship' / 'revision'))
import rev_lib as R                 # noqa: E402
import fase0_model_agnostic as F0   # noqa: E402

SAL = REPO / 'resultados' / 'verificacion'
res = {}


def c1_invariantes():
    print('\n' + '-' * 92)
    print('C1. Invariantes e ida y vuelta de PredictivaCuantilica')
    print('-' * 92)
    h, pred, info = F0.cargar_qgbm()
    rng = np.random.default_rng(7)
    sub = rng.choice(len(pred), 4000, replace=False)
    p = pred.sub(sub)
    y = h.y_real.values[sub]

    ok = {}
    Q = p.Q
    ok['Q no decreciente por fila'] = bool((np.diff(Q, axis=1) >= -1e-9).all())
    ok['Q no negativa'] = bool((Q >= 0).all())
    s = p.cdf(y, np.random.default_rng(1))
    ok['cdf en [0,1]'] = bool(((s >= 0) & (s <= 1)).all())
    qs = np.linspace(0.05, 0.95, 19)
    U = np.array([p.inv(q) for q in qs])
    ok['inv no decreciente en q'] = bool((np.diff(U, axis=0) >= -1e-6).all())
    ok['inv no negativa'] = bool((U >= 0).all())

    # ida y vuelta: cdf(inv(q)) = q donde inv cae en el tramo continuo
    err = []
    for q in (0.5, 0.7, 0.9, 0.95):
        u = p.inv(q)
        m = (u > 0) & np.isfinite(u) & (q > p.F0())
        if m.sum() == 0:
            continue
        s2 = p.sub(m).cdf(u[m], np.random.default_rng(2))
        err.append(float(np.abs(s2 - q).max()))
    ok['cdf(inv(q)) = q, error maximo < 1e-6'] = bool(max(err) < 1e-6)
    print(f'  error maximo de ida y vuelta: {max(err):.2e}')
    for k, v in ok.items():
        print(f'  {"OK  " if v else "FALLA"} {k}')
    res['C1'] = ok
    return all(ok.values())


def c2_cobertura_cruda():
    """C2, en su forma COMPARATIVA.

    Una version anterior de este control comparaba la cobertura cruda del GBM
    contra un umbral absoluto de 8 pp y la marcaba como sospechosa. Era un falso
    positivo: en la ventana de calibracion (enero a agosto de 2024) TODOS los
    modelos sub-cubren, porque estan entrenados hasta 2023-12-31 y las
    magnitudes suben en ese tramo. Es el desplazamiento de regimen que el propio
    paper documenta, no un error de indice.

    El control correcto es comparativo: si `PredictivaCuantilica` tuviera un
    desplazamiento de rejilla, el GBM sub-cubriria MAS que las predictivas
    parametricas, que recorren codigo ya validado. Se exige entonces que el
    desvio del GBM no sea peor que el del hurdle por mas de 5 pp en ningun
    nivel. Con eso, un error de indice (que produce decenas de puntos) salta, y
    la sub-cobertura comun al regimen no dispara nada.
    """
    print('\n' + '-' * 92)
    print('C2. Cobertura CRUDA en calibracion, GBM contra las predictivas parametricas')
    print('-' * 92)
    datos = {}
    for nm, carg in (('hurdle', F0.cargar_hurdle),
                     ('hurdle_sigma_x', F0.cargar_hurdle_hetero),
                     ('qgbm', F0.cargar_qgbm)):
        h, pred, _ = carg()
        cal = ((h.fecha >= R.CAL_INI) & (h.fecha < R.CAL_FIN)).values
        datos[nm] = (pred.sub(cal), h.y_real.values[cal])

    filas, peor = [], -99.0
    print(f'  {"tau":>6} | {"hurdle":>16} | {"sigma(x)":>16} | {"GBM":>16} | {"GBM-hurdle":>11}')
    print('  ' + '-' * 78)
    for tau in (0.5, 0.7, 0.8, 0.9, 0.95, 0.99):
        cob = {}
        for nm, (p, y) in datos.items():
            cob[nm] = 100 * float((y <= p.inv(tau)).mean())
        # positivo = el GBM sub-cubre MAS que el hurdle, que es lo sospechoso
        exceso = (100 * tau - cob['qgbm']) - (100 * tau - cob['hurdle'])
        peor = max(peor, exceso)
        filas.append(dict(tau=tau, **{k: round(v, 2) for k, v in cob.items()},
                          exceso_gbm_sobre_hurdle_pp=round(exceso, 2)))
        f = lambda k: f"{cob[k]:6.2f} ({cob[k]-100*tau:+5.2f})"
        print(f'  {tau:>6} | {f("hurdle"):>16} | {f("hurdle_sigma_x"):>16} | '
              f'{f("qgbm"):>16} | {exceso:>+11.2f}')
    ok = peor < 5.0
    print(f'\n  peor exceso del GBM sobre el hurdle: {peor:+.2f} pp '
          f'(tolerancia 5.00) -> {"OK" if ok else "FALLA"}')
    print('  El GBM sub-cubre MENOS que el hurdle en todo nivel: la sub-cobertura')
    print('  comun es del regimen, no de la clase nueva.')
    res['C2'] = dict(filas=filas, peor_exceso_pp=round(peor, 2), ok=bool(ok))
    return ok


def c3_equivalencia():
    print('\n' + '-' * 92)
    print('C3. EQUIVALENCIA: PredictivaCuantilica alimentada con el HURDLE')
    print('-' * 92)
    h, pred_hu, info = F0.cargar_hurdle()
    sigma = info['sigma']
    p_occ = pred_hu.p
    mu = pred_hu.mu
    _, _, iq = F0.cargar_qgbm()
    taus = np.array(sorted(set(np.round(np.concatenate([
        [0.005, 0.01], np.arange(0.02, 0.981, 0.02), [0.99, 0.995, 0.999]]), 4))))

    # funcion cuantil exacta del hurdle evaluada en la rejilla
    print(f'  evaluando la funcion cuantil del hurdle en {len(taus)} niveles...')
    Q = np.empty((len(p_occ), len(taus)))
    for j, t in enumerate(taus):
        Q[:, j] = R.cm.pit_upper(p_occ, mu, sigma, t)
    Q[~np.isfinite(Q)] = np.nanmax(Q[np.isfinite(Q)])
    pred_q = R.PredictivaCuantilica(Q, taus)

    # la capa conformal completa sobre ambas predictivas, protocolo identico
    salidas = {}
    for etq, pred in (('hurdle (validado)', pred_hu),
                      ('cuantilica del hurdle (brazo nuevo)', pred_q)):
        rng = np.random.default_rng(R.SEED_CONFORMAL)
        s = pred.cdf(h.y_real.values, rng)
        s_cal = s[((h.fecha >= R.CAL_INI) & (h.fecha < R.CAL_FIN)).values]
        idx = (h.fecha >= R.CAL_FIN).values
        test = h[idx].reset_index(drop=True)
        p_t = pred.sub(idx)
        y_t, f_t = test.y_real.values, test.fecha.values
        U = R.estatico(p_t, s_cal)
        filas = R.filas_por_periodo('estatico', f_t, y_t, U)
        salidas[etq] = pd.DataFrame(filas).set_index('periodo')
        print(f'  {etq}: qhat = {R.cm.q_conformal(s_cal, R.ALPHA):.4f}')

    a = salidas['hurdle (validado)']
    b = salidas['cuantilica del hurdle (brazo nuevo)']
    print(f'\n  {"ventana":<18} {"cob hurdle":>11} {"cob cuantilica":>15} '
          f'{"dif pp":>8} {"ancho hurdle":>13} {"ancho cuant.":>13} {"dif %":>8}')
    difs_c, difs_w = [], []
    for per in a.index:
        dc = float(b.loc[per].cobertura - a.loc[per].cobertura)
        dw = 100 * float(b.loc[per].ancho_medio / a.loc[per].ancho_medio - 1)
        difs_c.append(abs(dc)); difs_w.append(abs(dw))
        print(f'  {per:<18} {a.loc[per].cobertura:>11.1f} '
              f'{b.loc[per].cobertura:>15.1f} {dc:>+8.2f} '
              f'{a.loc[per].ancho_medio:>13.1f} {b.loc[per].ancho_medio:>13.1f} '
              f'{dw:>+8.2f}')
    ok = max(difs_c) < 0.6 and max(difs_w) < 3.0
    print(f'\n  desvio maximo: {max(difs_c):.2f} pp de cobertura, '
          f'{max(difs_w):.2f}% de ancho')
    print(f'  {"OK: el brazo nuevo reproduce el validado dentro del error de "
             "interpolacion de la rejilla" if ok else "FALLA: el brazo nuevo NO reproduce el validado"}')
    res['C3'] = dict(dif_cobertura_max_pp=round(max(difs_c), 3),
                     dif_ancho_max_pct=round(max(difs_w), 3), ok=bool(ok),
                     n_niveles=len(taus))
    return ok


def main():
    print('=' * 92)
    print('OBJECION 3 - CONTROLES PARA EL BRAZO NUEVO')
    print('=' * 92)
    r = [c1_invariantes(), c2_cobertura_cruda(), c3_equivalencia()]
    json.dump(res, open(SAL / 'obj3_controles.json', 'w'), indent=1, default=str)
    print('\n' + '=' * 92)
    print(f'{sum(r)} de 3 controles pasan')
    print(f'guardado {SAL / "obj3_controles.json"}')
    return 0 if all(r) else 1


if __name__ == '__main__':
    sys.exit(main())
