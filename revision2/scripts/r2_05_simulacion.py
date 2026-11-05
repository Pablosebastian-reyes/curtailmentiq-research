#!/usr/bin/env python3
"""
R2-05. Simulacion controlada del diagnostico.
============================================
Comentario 1 del Revisor 2: "support the diagnostic through controlled
simulation and dependence-aware inference or moderate the claim".

Panel sintetico cero-inflado con verdad conocida y la misma capa conformal del
paper (rev_lib: split estatico PIT, ACI y Transport+ACI, embargo de 7 dias).

DGP (por central i y dia t)
  ocurrencia   Z ~ Bernoulli(logit^-1(a_i + eta_t))
  magnitud     log Y = m_i + l_t + xi_t + eps_it,  eps ~ N(0, s_t^2)
  eta_t, xi_t  shocks diarios COMUNES a todas las centrales, AR(1) phi = 0.7:
               son la fuente de la dependencia de panel (ICC del PIT ~ 0.2-0.3)
  calibracion  240 dias; test 638 dias en cinco ventanas de 30, 92, 181, 184 y
               151 dias, como el paper; la "transicion" es la segunda.
Escenarios de shift en el test (rampa durante la ventana 2, constante despues)
  S0 sin shift
  S1 solo nivel:       l sube log(3) (las magnitudes se triplican, como en el SEN)
  S2 nivel+dispersion: S1 y ademas s_t baja de 1.0 a 0.6 (saturacion)
  S3 solo dispersion:  s_t baja de 1.0 a 0.6
Ocho modelos base (predictiva hurdle lognormal), escalera de mala especificacion
  M1 oraculo                 sigue nivel y dispersion
  M2 sobre-disperso k=1.3    sigue nivel y dispersion, sigma inflada 30% SIEMPRE
  M3 dispersion a medias     sigue nivel; sigma = media geometrica cal/real
  M4 sigma constante         sigue nivel; sigma fija en la de calibracion (el hurdle)
  M5 sigma constante, k=1.3
  M6 sigma constante, k=0.8
  M7 nivel rezagado 30 d     sigue dispersion; nivel con 30 dias de retraso
  M8 rezagado y sigma const.
Para cada replica y escenario: 8 modelos x 5 ventanas = 40 celdas, como el
diagnostico real. Se mide sobre-cobertura del split estatico, cambio de ancho
de ACI y de Transport+ACI (gamma 0.05, alpha_min 0.005) y el cambio de ancho
del oraculo constante (umbral PIT constante elegido ex post con la misma
cobertura). Replicas: 100 por escenario.

Salidas: resultados/r2_05_sim_celdas.csv, r2_05_sim_resumen.json
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_lib as L                      # noqa: E402
import numpy as np                      # noqa: E402
import pandas as pd                     # noqa: E402
from scipy.stats import norm            # noqa: E402
R = L.R

N_CENTRALES = 100
DIAS_CAL = 240
VENTANAS = [30, 92, 181, 184, 151]
NOMBRES_V = ['W1 pre', 'W2 transition', 'W3', 'W4', 'W5']
REPLICAS = 50
GAMMA, AMIN, ALPHA = 0.05, 0.005, 0.10
SD_ETA, SD_XI, PHI = 0.8, 0.5, 0.7
S_CAL = 1.0
ESCENARIOS = {'S0 no shift': (0.0, 1.0), 'S1 level only': (np.log(3), 1.0),
              'S2 level + dispersion': (np.log(3), 0.6), 'S3 dispersion only': (0.0, 0.6)}
MODELOS = {   # (phi de seguimiento de la dispersion, kappa, rezago del nivel en dias)
    'M1 oracle': (1.0, 1.0, 0), 'M2 over-dispersed (k=1.3)': (1.0, 1.3, 0),
    'M3 half dispersion tracking': (0.5, 1.0, 0), 'M4 constant sigma': (0.0, 1.0, 0),
    'M5 constant sigma, k=1.3': (0.0, 1.3, 0), 'M6 constant sigma, k=0.8': (0.0, 0.8, 0),
    'M7 lagged level (30 d)': (1.0, 1.0, 30), 'M8 lagged level, constant sigma': (0.0, 1.0, 30)}
T0 = pd.Timestamp('2030-01-01')


def ar1(rng, n, sd, phi=PHI):
    e = rng.normal(0, sd * np.sqrt(1 - phi ** 2), n)
    x = np.empty(n)
    x[0] = rng.normal(0, sd)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return x


def trayectorias(delta, rho):
    nT = DIAS_CAL + sum(VENTANAS)
    l, s = np.zeros(nT), np.full(nT, S_CAL)
    a = DIAS_CAL + VENTANAS[0]                     # inicio de la ventana de transicion
    b = a + VENTANAS[1]
    rampa = np.clip((np.arange(nT) - a) / (b - a), 0, 1)
    l += delta * rampa
    s = S_CAL * (1 + (rho - 1) * rampa)
    return l, s


def p_marginal(a):
    """E[logistic(a + eta)] con eta ~ N(0, SD_ETA^2), cuadratura de Gauss-Hermite."""
    x, w = np.polynomial.hermite_e.hermegauss(40)
    return (w[None, :] / np.sqrt(2 * np.pi) / (1 + np.exp(-(a[:, None] + SD_ETA * x[None, :])))).sum(1)


def una_replica(args):
    esc, rep = args
    delta, rho = ESCENARIOS[esc]
    rng = np.random.default_rng([20261103, list(ESCENARIOS).index(esc), rep])
    nT = DIAS_CAL + sum(VENTANAS)
    l, s = trayectorias(delta, rho)
    a_i = rng.normal(1.0, 0.8, N_CENTRALES)
    m_i = rng.normal(4.0, 0.8, N_CENTRALES)
    eta, xi = ar1(rng, nT, SD_ETA), ar1(rng, nT, SD_XI)
    occ = rng.random((nT, N_CENTRALES)) < 1 / (1 + np.exp(-(a_i[None, :] + eta[:, None])))
    logy = m_i[None, :] + l[:, None] + xi[:, None] + s[:, None] * rng.standard_normal((nT, N_CENTRALES))
    Y = np.where(occ, np.exp(logy), 0.0)
    fechas = T0 + pd.to_timedelta(np.arange(nT), 'D')
    f = np.repeat(fechas.values, N_CENTRALES)
    y = Y.ravel()
    p_bar = np.tile(p_marginal(a_i), nT)
    sig_true = np.sqrt(s ** 2 + SD_XI ** 2)             # marginaliza el shock comun
    sig_cal = np.sqrt(S_CAL ** 2 + SD_XI ** 2)
    cal = np.arange(nT * N_CENTRALES) < DIAS_CAL * N_CENTRALES
    test = ~cal
    f_t, y_t = f[test], y[test]
    fechas_test = np.sort(np.unique(f_t))
    ini_test = fechas[DIAS_CAL]
    v_lim = np.cumsum([0] + VENTANAS) + DIAS_CAL
    filas = []
    icc = None
    for mod, (phi, kappa, lag) in MODELOS.items():
        sig_mod = kappa * sig_cal ** (1 - phi) * sig_true ** phi
        l_mod = np.concatenate([np.zeros(lag), l[:nT - lag]]) if lag else l
        mu = (m_i[None, :] + l_mod[:, None]).ravel()
        sg = np.repeat(sig_mod, N_CENTRALES)
        pred = R.PredictivaHurdle(p_bar, mu, sg)
        r_s = np.random.default_rng([7, rep, list(MODELOS).index(mod)])
        sc = pred.cdf(y, r_s)
        s_cal = sc[cal]
        if mod == 'M1 oracle':
            d = pd.DataFrame(dict(f=f[cal], s=s_cal))
            g = d.groupby('f').s
            k = g.size().mean()
            msb = (g.mean() - d.s.mean()).pow(2).mul(g.size()).sum() / (g.ngroups - 1)
            msw = ((d.s - g.transform('mean')) ** 2).sum() / (len(d) - g.ngroups)
            icc = float((msb - msw) / (msb + (k - 1) * msw))
        p_t = pred.sub(test)
        U_est = R.estatico(p_t, s_cal)
        U_aci = R.aci(p_t, s_cal, y_t, f_t, fechas_test, GAMMA, alpha_min=AMIN)[0]
        U_tr = R.transporte_aci(p_t, s_cal, sc, f, y_t, f_t, fechas_test, GAMMA,
                                np.random.default_rng([11, rep]), alpha_min=AMIN,
                                ini_test=ini_test)[0]
        # PIT EXACTO de y>0 (sin el piso log(max(y,1)) de pit_score): para la
        # lognormal, y <= F^-1(q) <=> F(y) <= q, asi que la cobertura de un
        # umbral constante q es (#ceros + #{F(y) <= q}) / n y el oraculo es un
        # estadistico de orden: exacto y sin biseccion.
        p_tt, mu_tt = p_t.p, p_t.mu
        sg_tt = p_t.sigma if np.ndim(p_t.sigma) else np.full(len(p_t.p), p_t.sigma)
        with np.errstate(divide='ignore'):
            Fy = np.where(y_t > 0, (1 - p_tt) + p_tt * norm.cdf((np.log(np.maximum(y_t, 1e-300)) - mu_tt) / sg_tt), -1.0)
        for w in range(5):
            dm = (f_t >= (T0 + pd.Timedelta(days=int(v_lim[w]))).to_datetime64()) & (f_t < (T0 + pd.Timedelta(days=int(v_lim[w + 1]))).to_datetime64())
            yy = y_t[dm]
            pw = p_t.sub(dm)
            cov_s = float(np.mean(yy <= U_est[dm]))
            W_s = float(U_est[dm].mean())
            fila = dict(escenario=esc, replica=rep, modelo=mod, ventana=NOMBRES_V[w],
                        oc=100 * (cov_s - 0.9), W_static=W_s)
            Fw = Fy[dm]
            n0 = int((yy == 0).sum())
            Fpos = np.sort(Fw[yy > 0])
            for nm, U in (('aci', U_aci), ('tr', U_tr)):
                cov_a = float(np.mean(yy <= U[dm]))
                W_a = float(U[dm][np.isfinite(U[dm])].mean())
                k = int(np.ceil(cov_a * len(yy) - 1e-9)) - n0
                q_star = Fpos[min(max(k, 1), len(Fpos)) - 1] if k >= 1 else 1e-9
                W_m = float(pw.inv(np.full(len(yy), q_star)).mean())
                fila[f'dW_{nm}'] = 100 * (W_a / W_s - 1)
                fila[f'dWmec_{nm}'] = 100 * (W_m / W_s - 1)
                fila[f'cov_{nm}'] = 100 * cov_a
            filas.append(fila)
    return filas, icc


def resumir(C):
    out = {}
    for esc, g in C.groupby('escenario'):
        regs = []
        for rep, gr in g.groupby('replica'):
            for nm in ('aci', 'tr'):
                x, yv, ym = gr.oc.values, gr[f'dW_{nm}'].values, gr[f'dWmec_{nm}'].values
                if np.std(x) < 1e-9:
                    continue
                b1, b0 = np.polyfit(x, yv, 1)
                bm, _ = np.polyfit(x, ym, 1)
                regs.append(dict(metodo=nm, r=np.corrcoef(x, yv)[0, 1], pendiente=b1, intercepto=b0,
                                 pendiente_mec=bm, R2_mec=np.corrcoef(yv, ym)[0, 1] ** 2,
                                 resid=np.mean(yv - ym)))
        Rg = pd.DataFrame(regs)
        out[esc] = {}
        for nm, gg in Rg.groupby('metodo'):
            out[esc][nm] = {k: dict(mediana=float(gg[k].median()),
                                    p2_5=float(gg[k].quantile(0.025)),
                                    p97_5=float(gg[k].quantile(0.975)))
                            for k in ('r', 'pendiente', 'intercepto', 'pendiente_mec', 'R2_mec', 'resid')}
        mm = g.groupby(['modelo', 'ventana'])[['oc', 'dW_aci', 'dW_tr', 'dWmec_tr']].mean().reset_index()
        out[esc]['celdas_medias'] = mm.round(3).to_dict('records')
        an = pd.DataFrame([_anova(d) for _, d in g.groupby('replica')])
        out[esc]['anova_oc_medio'] = an.mean().round(3).to_dict()
    return out


def _anova(d):
    import statsmodels.formula.api as smf
    import statsmodels.api as sm
    a = sm.stats.anova_lm(smf.ols('oc ~ C(modelo) + C(ventana)', d).fit(), typ=2)
    t = a.sum_sq.sum()
    return dict(modelo=a.sum_sq['C(modelo)'] / t, ventana=a.sum_sq['C(ventana)'] / t,
                residuo=a.sum_sq['Residual'] / t)


def main():
    tareas = [(e, r) for e in ESCENARIOS for r in range(REPLICAS)]
    filas, iccs = [], []
    with ProcessPoolExecutor(max_workers=5) as ex:
        for i, (f, icc) in enumerate(ex.map(una_replica, tareas, chunksize=4)):
            filas += f
            iccs.append(icc)
            if i % 40 == 0:
                L.log(f'simulacion: {i + 1}/{len(tareas)}', 'r2_05_simulacion.log')
    C = pd.DataFrame(filas)
    C.to_csv(L.RES / 'r2_05_sim_celdas.csv', index=False)
    res = resumir(C)
    res['icc_pit_oraculo_calibracion'] = dict(media=float(np.mean(iccs)),
                                              p2_5=float(np.percentile(iccs, 2.5)),
                                              p97_5=float(np.percentile(iccs, 97.5)))
    res['disenio'] = dict(centrales=N_CENTRALES, dias_calibracion=DIAS_CAL, ventanas=VENTANAS,
                          replicas=REPLICAS, gamma=GAMMA, alpha_min=AMIN, sd_eta=SD_ETA,
                          sd_xi=SD_XI, phi_ar1=PHI, escenarios={k: list(v) for k, v in ESCENARIOS.items()},
                          modelos={k: list(v) for k, v in MODELOS.items()})
    json.dump(res, open(L.RES / 'r2_05_sim_resumen.json', 'w'), indent=1, default=float)
    L.log('simulacion lista', 'r2_05_simulacion.log')


if __name__ == '__main__':
    main()
