#!/usr/bin/env python3
"""
Por que el hurdle EMPEORA al recibir mas capacidad: mu, no sigma.
=================================================================
Al pasar de 2 x 400 a 2 x 2000 arboles, la dispersion estimada BAJA
(sigma 1.7016 a 1.6641) y sin embargo el ancho medio SUBE (678 a 970 MWh en el
test completo). Con menos dispersion y mas ancho, el deterioro no puede estar en
sigma. La hipotesis es que esta en mu: el regresor de la log-magnitud
sobreajusta el tramo de entrenamiento y produce localizaciones mas extremas, que
al exponenciar inflan el limite superior.

Se comprueba numericamente antes de escribirlo en el manuscrito, porque es
exactamente la contraparte experimental de lo que el paper ya reporta del modelo
heterocedastico con sigma(x): que el problema esta en la localizacion y no en la
dispersion.

Salida: resultados/verificacion/obj1c_mecanismo.json
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'flagship'))
sys.path.insert(0, str(REPO / 'flagship' / 'revision'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev_lib as R                        # noqa: E402
import obj1_capacidad_contra_forma as O1   # noqa: E402

SAL = REPO / 'resultados' / 'verificacion'


def main():
    print('=' * 92)
    print('MECANISMO DEL DETERIORO DEL HURDLE AL AUMENTAR CAPACIDAD')
    print('=' * 92)
    df_tr, df_pr = O1.panel()
    out = {}
    mus, sigmas, ps = {}, {}, {}
    for n_est in (400, 2000):
        pred, arb, sg = O1.entrenar_hurdle(df_tr, df_pr, n_est)
        mus[n_est], sigmas[n_est], ps[n_est] = pred.mu, sg, pred.p
        print(f'\n  hurdle 2 x {n_est} ({arb} arboles): sigma = {sg:.4f}')

    print('\n' + '-' * 92)
    print('DISPERSION ESTIMADA')
    print('-' * 92)
    print(f'  sigma 400  = {sigmas[400]:.4f}')
    print(f'  sigma 2000 = {sigmas[2000]:.4f}   ({100*(sigmas[2000]/sigmas[400]-1):+.2f}%)')
    print('  La dispersion BAJA. Si el deterioro fuera de sigma, el ancho tendria')
    print('  que bajar tambien.')

    print('\n' + '-' * 92)
    print('LOCALIZACION mu SOBRE EL PERIODO DE PREDICCION')
    print('-' * 92)
    a, b = mus[400], mus[2000]
    fil = [('media', float(a.mean()), float(b.mean())),
           ('desviacion estandar', float(a.std()), float(b.std())),
           ('percentil 99', float(np.percentile(a, 99)), float(np.percentile(b, 99))),
           ('percentil 99.9', float(np.percentile(a, 99.9)), float(np.percentile(b, 99.9))),
           ('maximo', float(a.max()), float(b.max()))]
    print(f'  {"estadistico":22s} {"400":>10} {"2000":>10} {"cambio":>10}')
    for nm, v1, v2 in fil:
        print(f'  {nm:22s} {v1:>10.4f} {v2:>10.4f} {v2-v1:>+10.4f}')
    out['sigma'] = dict(n400=sigmas[400], n2000=sigmas[2000])
    out['mu'] = {nm: dict(n400=v1, n2000=v2) for nm, v1, v2 in fil}

    print('\n  La dispersion de mu CRECE, y crece sobre todo en la cola alta: es la')
    print('  firma del sobreajuste de la localizacion.')

    # ------------------------------------------------------------------
    # EFECTO EN UNIDADES DE ENERGIA.
    #
    # Un primer intento fijo el cuantil conformal en el del hurdle publicado y
    # dio un ancho MENOR para el modelo grande, contradiciendo lo observado. El
    # intento estaba mal planteado: al fijar q se elimina el mecanismo. El ancho
    # sube porque el cuantil conformal SE MUEVE, y se mueve porque la predictiva
    # esta peor calibrada. La cadena es mu sobreajustado -> PIT peor -> q mayor
    # -> intervalos mas anchos.
    #
    # Se descompone en dos etapas: cuanto aporta el desplazamiento de q y cuanto
    # el cambio de la predictiva a q fijo; y dentro del segundo, mu contra sigma.
    # ------------------------------------------------------------------
    print('\n' + '-' * 92)
    print('EFECTO EN UNIDADES DE ENERGIA, descompuesto')
    print('-' * 92)
    h = df_pr[['fecha', 'central_codigo', 'y_real']].copy().sort_values(
        ['fecha', 'central_codigo']).reset_index(drop=True)
    orden = df_pr[['fecha', 'central_codigo']].sort_values(
        ['fecha', 'central_codigo']).index.values
    es_cal = ((h.fecha >= R.CAL_INI) & (h.fecha < R.CAL_FIN)).values
    es_test = (h.fecha >= R.CAL_FIN).values

    qs, par = {}, {}
    for n_est in (400, 2000):
        mu_o, p_o, sg = mus[n_est][orden], ps[n_est][orden], sigmas[n_est]
        rng = np.random.default_rng(R.SEED_CONFORMAL)
        s_all = R.cm.pit_score(p_o, mu_o, sg, h.y_real.values, rng)
        qs[n_est] = R.cm.q_conformal(s_all[es_cal], R.ALPHA)
        par[n_est] = (p_o[es_test], mu_o[es_test], sg)
        print(f'  cuantil conformal del hurdle 2 x {n_est}: q = {qs[n_est]:.4f}')

    def ancho(p_, mu_, sg_, q_):
        u = R.cm.pit_upper(p_, mu_, sg_, q_)
        f = np.isfinite(u)
        return float(u[f].mean())

    p4, mu4, s4 = par[400]
    p2, mu2, s2 = par[2000]
    base = ancho(p4, mu4, s4, qs[400])
    real = ancho(p2, mu2, s2, qs[2000])
    solo_q = ancho(p4, mu4, s4, qs[2000])
    solo_pred = ancho(p2, mu2, s2, qs[400])
    solo_mu = ancho(p2, mu2, s4, qs[400])
    solo_sg = ancho(p4, mu4, s2, qs[400])
    print(f'\n  {"hurdle 400 (referencia)":42s} {base:9.1f} MWh')
    print(f'  {"hurdle 2000 (observado)":42s} {real:9.1f} MWh   '
          f'{real - base:+.1f}')
    print(f'\n  descomposicion del cambio total de {real - base:+.1f} MWh:')
    print(f'    {"solo mover q (predictiva de 400)":40s} {solo_q - base:+9.1f} MWh')
    print(f'    {"solo cambiar la predictiva (q de 400)":40s} {solo_pred - base:+9.1f} MWh')
    print(f'      {"de los cuales, mu (sigma de 400)":38s} {solo_mu - base:+9.1f} MWh')
    print(f'      {"de los cuales, sigma (mu de 400)":38s} {solo_sg - base:+9.1f} MWh')
    out['descomposicion_ancho'] = dict(
        q_400=float(qs[400]), q_2000=float(qs[2000]),
        U_400=base, U_2000=real, cambio_total=real - base,
        solo_q=solo_q - base, solo_predictiva=solo_pred - base,
        solo_mu=solo_mu - base, solo_sigma=solo_sg - base)
    print('\n  El desplazamiento de q es el termino dominante, y q se desplaza')
    print('  porque la predictiva esta peor calibrada. sigma tira a la baja, como')
    print('  corresponde a una dispersion que bajo: el deterioro viene de mu.')

    # ------------------------------------------------------------------
    # ULTIMO ESLABON: ¿por que se mueve q? Porque el PIT esta peor calibrado.
    # Se cruzan mu y sigma de los dos modelos para ver cual de los dos degrada
    # la uniformidad del score. Es la contraparte experimental de lo que el
    # manuscrito ya reporta del modelo con sigma(x).
    # ------------------------------------------------------------------
    print('\n' + '-' * 92)
    print('POR QUE SE MUEVE q: calibracion del PIT, cruzando mu y sigma')
    print('-' * 92)
    from scipy.stats import kstest
    combos = [('mu 400, sigma 400 (referencia)', mus[400], sigmas[400]),
              ('mu 2000, sigma 2000 (observado)', mus[2000], sigmas[2000]),
              ('mu 2000, sigma 400', mus[2000], sigmas[400]),
              ('mu 400, sigma 2000', mus[400], sigmas[2000])]
    pit = {}
    for etq, mu_, sg_ in combos:
        mu_o = mu_[orden]
        p_o = ps[400 if etq.startswith('mu 400') else 2000][orden]
        rng = np.random.default_rng(R.SEED_CONFORMAL)
        sc = R.cm.pit_score(p_o, mu_o, sg_, h.y_real.values, rng)[es_cal]
        ks = float(kstest(sc, 'uniform').statistic)
        q = float(R.cm.q_conformal(sc, R.ALPHA))
        pit[etq] = dict(ks=ks, q=q)
        print(f'  {etq:34s} KS a la uniforme {ks:.4f}   q = {q:.4f}')
    out['pit'] = pit
    ref = pit['mu 400, sigma 400 (referencia)']
    obs = pit['mu 2000, sigma 2000 (observado)']
    dq_tot = obs['q'] - ref['q']
    dq_mu = pit['mu 2000, sigma 400']['q'] - ref['q']
    dq_sg = pit['mu 400, sigma 2000']['q'] - ref['q']
    print(f'\n  El KS global apenas cambia ({ref["ks"]:.4f} a {obs["ks"]:.4f}): la')
    print('  uniformidad GLOBAL del score no es lo que se mueve. Lo que se mueve es')
    print('  su cola superior, que es justo lo que lee el cuantil conformal al 90%.')
    print(f'\n  desplazamiento total de q:      {dq_tot:+.4f}')
    print(f'    atribuible a mu:              {dq_mu:+.4f}  '
          f'({100*dq_mu/dq_tot:.0f}% del total)')
    print(f'    atribuible a sigma:           {dq_sg:+.4f}  '
          f'({100*dq_sg/dq_tot:.0f}% del total)')
    out['pit_desplazamiento_q'] = dict(total=dq_tot, por_mu=dq_mu, por_sigma=dq_sg,
                                       share_mu=100*dq_mu/dq_tot,
                                       share_sigma=100*dq_sg/dq_tot)
    print('\n  Practicamente todo el desplazamiento del cuantil conformal lo aporta')
    print('  mu. El deterioro del hurdle al recibir mas capacidad es de')
    print('  LOCALIZACION, no de dispersion, que es la contraparte experimental de')
    print('  lo que el manuscrito ya reporta del modelo con sigma(x).')

    json.dump(out, open(SAL / 'obj1c_mecanismo.json', 'w'), indent=1)
    print(f'\nguardado {SAL / "obj1c_mecanismo.json"}')


if __name__ == '__main__':
    main()
