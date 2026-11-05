#!/usr/bin/env python3
"""
R2-03. El diagnostico: cuanto es mecanico, cuanto es modelo base, con
inferencia que respeta la dependencia.
=====================================================================
Comentario 1 del Revisor 2: las 40 celdas (8 modelos x 5 ventanas) no son
independientes, son dos familias, y la asociacion entre sobre-cobertura del
split estatico y reduccion de ancho adaptativa "puede venir en parte del propio
procedimiento de calibracion".

1. Descomposicion mecanica en espacio PIT. Para cada celda (modelo, ventana)
   se busca EX POST el umbral PIT constante q* tal que el limite F^{-1}(q*)
   cubre en esa ventana exactamente lo mismo que el metodo adaptativo. Ese
   limite no adapta nada en el tiempo: solo reajusta el nivel del split
   estatico. Su cambio de ancho es la parte MECANICA; el resto, el residuo, es
   lo que la adaptacion temporal agrega (o cuesta).
2. Inferencia:
   a. bootstrap por bloques de DIA comun a todas las celdas (2000 replicas,
      semilla 20260901): preserva la dependencia cruzada entre celdas que
      comparten dias; se recalcula todo, incluido el oraculo;
   b. efectos fijos de ventana, de modelo y bidireccionales;
   c. efectos aleatorios cruzados (modelo, ventana);
   d. wild cluster bootstrap restringido por modelo y por ventana (pesos de
      Webb, pocos clusters);
   e. correlaciones dentro de ventana (mismo shift, distinto modelo);
   f. ANOVA de la sobre-cobertura: cuanto explica el modelo y cuanto la ventana;
   g. agregacion a familia x ventana (10 celdas).
3. Prueba fuera de muestra: la recta ajustada en las 40 celdas de la R1 predice
   las 5 celdas del hurdle con detencion temprana, que no entro en el ajuste.

Configuraciones adaptativas evaluadas:
  tr_g05          Transport+ACI gamma 0.05 sin cota (la del paper, R1)
  tr_g05_amin005  la misma con alpha_min = 0.005 (sin intervalos infinitos)
  aci_g05_amin005 ACI puro gamma 0.05 con alpha_min = 0.005
  tr_sel, aci_sel la configuracion elegida por origen rodante de cada modelo

Salidas: resultados/r2_03_celdas.csv, r2_03_resumen.json, r2_03_inferencia.csv,
         r2_03_bootstrap_lineas.npz
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_lib as L                      # noqa: E402
import numpy as np                      # noqa: E402
import pandas as pd                     # noqa: E402
from scipy.stats import norm            # noqa: E402
import statsmodels.formula.api as smf   # noqa: E402
import statsmodels.api as sm            # noqa: E402
R = L.R

LOG = 'r2_03_diagnostico.log'
CONFIGS = ('tr_g05', 'tr_g05_amin005', 'aci_g05_amin005', 'tr_sel', 'aci_sel')
QGRID = np.linspace(0.60, 0.999, 1597)            # paso 0.00025
B = 2000
VENT = [p for p, _, _ in L.PERIODOS]


def inv_multi(pred, q):
    """F^{-1}(q_k) para todas las filas de `pred` y todos los q de la rejilla."""
    q = np.asarray(q, float)
    if isinstance(pred, R.PredictivaHurdle):
        p = pred.p[:, None]
        sig = pred.sigma if np.ndim(pred.sigma) == 0 else pred.sigma[:, None]
        arg = np.clip((q[None, :] - (1 - p)) / p, 0.0, 1.0)
        with np.errstate(divide='ignore', over='ignore'):
            return np.exp(pred.mu[:, None] + sig * norm.ppf(arg))
    Ta, Xa = pred.Ta, pred.Xa
    K1 = Xa.shape[1]
    j = np.clip(np.searchsorted(Ta, q, side='right') - 1, 0, K1 - 2)
    t0, t1 = Ta[j], Ta[j + 1]
    frac = np.where(t1 - t0 > 0, (q - t0) / np.where(t1 - t0 > 0, t1 - t0, 1.0), 0.0)
    x0, x1 = Xa[:, j], Xa[:, j + 1]
    U = x0 + np.clip(frac, 0, 1)[None, :] * (x1 - x0)
    U = np.where(q[None, :] <= pred.F0()[:, None], 0.0, U)
    return np.where(q[None, :] > pred.taus[-1], np.inf, U)


def agregados_diarios(nombre):
    """Por dia del test: filas, cubiertos y suma de anchos finitos del split
    estatico, de cada configuracion adaptativa y de F^{-1}(q) sobre QGRID."""
    S = pd.read_parquet(L.SERIES_DIR / f'{nombre}.parquet')
    pred = L.cargar_predictiva(nombre)
    h = L.panel_filas()
    idx = ((h.fecha >= R.CAL_FIN) & (h.fecha < L.FIN_TEST)).values
    p_t = pred.sub(idx)
    assert len(p_t) == len(S)
    dias = np.sort(S.fecha.unique())
    pos = {d: i for i, d in enumerate(dias)}
    di = S.fecha.map(pos).values
    nD, K = len(dias), len(QGRID)
    out = dict(dias=dias, n=np.bincount(di, minlength=nD).astype(float))
    y = S.y.values
    for k in ('static',) + CONFIGS:
        if k not in S:
            continue
        U = S[k].values
        fi = np.isfinite(U)
        out[f'{k}_cov'] = np.bincount(di, (y <= U).astype(float), nD)
        out[f'{k}_w'] = np.bincount(di, np.where(fi, U, 0.0), nD)
        out[f'{k}_nf'] = np.bincount(di, fi.astype(float), nD)
    Cq = np.zeros((nD, K)); Wq = np.zeros((nD, K)); Nq = np.zeros((nD, K))
    orden = np.argsort(di, kind='stable')
    cortes = np.searchsorted(di[orden], np.arange(nD + 1))
    for d in range(nD):
        filas = orden[cortes[d]:cortes[d + 1]]
        Ud = inv_multi(p_t.sub(filas), QGRID)
        fi = np.isfinite(Ud)
        Cq[d] = (y[filas][:, None] <= Ud).sum(0)
        Wq[d] = np.where(fi, Ud, 0.0).sum(0)
        Nq[d] = fi.sum(0)
    out.update(Cq=Cq, Wq=Wq, Nq=Nq)
    # control: el split estatico es F^{-1}(qhat) con qhat constante
    return out


def celdas(A, Wm, dmask, confs):
    """Estadisticos de una celda (modelo, ventana) para una MATRIZ de pesos por
    dia Wm (nrep x ndias); la fila de unos es la estimacion puntual. Devuelve
    un dict por configuracion con vectores de largo nrep."""
    WW = Wm * dmask[None, :]
    n = WW @ A['n']
    cov_s = WW @ A['static_cov'] / n
    W_s = (WW @ A['static_w']) / (WW @ A['static_nf'])
    CC = np.maximum.accumulate((WW @ A['Cq']) / n[:, None], axis=1)
    CW = (WW @ A['Wq']) / np.maximum(WW @ A['Nq'], 1e-12)
    def q_para(cc, c):
        if c <= cc[0]:
            return QGRID[0]
        if c >= cc[-1]:
            return QGRID[-1]
        return float(np.interp(c, cc, QGRID))
    q90 = np.array([q_para(CC[i], 0.90) for i in range(len(n))])
    W90 = np.array([np.interp(q90[i], QGRID, CW[i]) for i in range(len(n))])
    out = {}
    for conf in confs:
        if f'{conf}_cov' not in A:
            continue
        cov_a = WW @ A[f'{conf}_cov'] / n
        nf_a = WW @ A[f'{conf}_nf']
        W_a = (WW @ A[f'{conf}_w']) / nf_a
        qm = np.array([q_para(CC[i], cov_a[i]) for i in range(len(n))])
        Wmc = np.array([np.interp(qm[i], QGRID, CW[i]) for i in range(len(n))])
        dW = 100 * (W_a / W_s - 1)
        dWm = 100 * (Wmc / W_s - 1)
        out[conf] = dict(oc=100 * (cov_s - 0.90), dW=dW, dW_mec=dWm,
                         dW_mec90=100 * (W90 / W_s - 1), resid=dW - dWm,
                         cov_adapt=100 * cov_a, W_static=W_s, W_adapt=W_a,
                         q_oraculo=qm, pct_inf=100 * (1 - nf_a / n))
    return out


def ajuste_vec(X, Y):
    """r, pendiente e intercepto por fila (replicas en filas, celdas en columnas)."""
    xm, ym = X.mean(1, keepdims=True), Y.mean(1, keepdims=True)
    sxy = ((X - xm) * (Y - ym)).sum(1)
    sxx = ((X - xm) ** 2).sum(1)
    syy = ((Y - ym) ** 2).sum(1)
    b1 = sxy / sxx
    return sxy / np.sqrt(sxx * syy), b1, ym[:, 0] - b1 * xm[:, 0]


def ajuste(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    b1, b0 = np.polyfit(x, y, 1)
    return float(np.corrcoef(x, y)[0, 1]), float(b1), float(b0)


def _t_cluster(X, y, g, G):
    """t de la pendiente con varianza robusta por cluster (CR1)."""
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ (X.T @ y)
    e = y - X @ b
    S = np.zeros((2, 2))
    for k in range(G):
        s = X[g == k].T @ e[g == k]
        S += np.outer(s, s)
    n, kx = X.shape
    V = XtXi @ S @ XtXi * (G / (G - 1)) * ((n - 1) / (n - kx))
    return b[1] / np.sqrt(V[1, 1])


def wild_cluster_restringido(df, cluster, nrep=9999, seed=20260901):
    """Wild cluster bootstrap RESTRINGIDO (H0: pendiente = 0) con pesos de
    Webb (6 puntos), recomendado con pocos clusters (MacKinnon y Webb, 2017).
    Devuelve el t observado con SE por cluster (CR1), el p-valor bootstrap
    bilateral y el numero de clusters."""
    rng = np.random.default_rng(seed)
    X = np.column_stack([np.ones(len(df)), df.oc.values])
    y = df.dW.values.astype(float)
    g = pd.factorize(df[cluster])[0]
    G = int(g.max() + 1)
    t0 = _t_cluster(X, y, g, G)
    r0 = y - y.mean()
    webb = np.array([-np.sqrt(1.5), -1, -np.sqrt(0.5), np.sqrt(0.5), 1, np.sqrt(1.5)])
    ts = np.empty(nrep)
    for b in range(nrep):
        v = webb[rng.integers(0, 6, G)][g]
        ts[b] = _t_cluster(X, y.mean() + r0 * v, g, G)
    return float(t0), float(np.mean(np.abs(ts) >= abs(t0))), G


def main():
    brazos = list(L.BRAZOS)
    A = {}
    for nm in brazos:
        A[nm] = agregados_diarios(nm)
        L.log(f'agregados diarios {nm}', LOG)
    dias = A[brazos[0]]['dias']
    for nm in brazos:
        assert (A[nm]['dias'] == dias).all()
    vmask = {}
    for per, ini, fin in L.PERIODOS:
        vmask[per] = ((dias >= np.datetime64(ini.date())) & (dias < np.datetime64(fin.date()))).astype(float)
    uno = np.ones(len(dias))

    # --------------------------- estimacion puntual y bootstrap, todo de una vez
    rng = np.random.default_rng(R.SEED_BOOTSTRAP)
    Wm = np.vstack([np.ones(len(dias))] +
                   [np.bincount(rng.integers(0, len(dias), len(dias)), minlength=len(dias))
                    for _ in range(B)]).astype(float)
    CEL = {}                       # (conf, brazo, ventana) -> dict de vectores (B+1)
    for nm in brazos:
        for per in VENT:
            for conf, d in celdas(A[nm], Wm, vmask[per], CONFIGS).items():
                CEL[(conf, nm, per)] = d
        L.log(f'celdas {nm}: listo', LOG)
    filas = []
    for (conf, nm, per), d in CEL.items():
        r = {k: float(v[0]) for k, v in d.items()}
        r.update(config=conf, brazo=nm, ventana=per, familia=L.BRAZOS[nm][1],
                 en_r1=nm in L.DIAG_R1)
        filas.append(r)
    TC = pd.DataFrame(filas)
    TC.to_csv(L.RES / 'r2_03_celdas.csv', index=False)

    # control: reproduce las 40 celdas de la R1 (tr_g05)
    r1 = pd.read_csv(L.REPO / 'resultados/fase0b/fase0b_celdas.csv')
    r1['brazo'] = r1.modelo_base.replace({'hurdle_400': 'hurdle_800'})
    m = TC[TC.config == 'tr_g05'].merge(r1, on=['brazo', 'ventana'])
    d_oc = float((m.oc - m.sobrecobertura_pp).abs().max())
    d_dw = float((m.dW - m.cambio_ancho_pct).abs().max())
    L.log(f'control 40 celdas R1: {len(m)} celdas, max|dif| OC {d_oc:.4f} pp, dW {d_dw:.4f} %', LOG)
    assert len(m) == 40 and d_oc < 0.02 and d_dw < 0.05, (d_oc, d_dw)

    res = dict(control_r1=dict(celdas=len(m), max_dif_oc_pp=d_oc, max_dif_dw_pct=d_dw))
    inf_rows = []
    for conf in CONFIGS:
        for conjunto, brz in (('r1_40', list(L.DIAG_R1)), ('r2_45', brazos)):
            keys = [(conf, nm, per) for nm in brz for per in VENT if (conf, nm, per) in CEL]
            if not keys:
                continue
            Cc = TC[(TC.config == conf) & (TC.brazo.isin(brz))].copy()
            clave = f'{conf}|{conjunto}'
            M = {k: np.column_stack([CEL[kk][k] for kk in keys]) for k in ('oc', 'dW', 'dW_mec', 'resid')}
            r_o, s_o, i_o = ajuste_vec(M['oc'], M['dW'])
            r_m, s_m, i_m = ajuste_vec(M['oc'], M['dW_mec'])
            r_res, s_res, _ = ajuste_vec(M['oc'], M['resid'])
            r_om, _, _ = ajuste_vec(M['dW_mec'], M['dW'])
            Bt = pd.DataFrame(dict(r=r_o, pendiente=s_o, intercepto=i_o, r_mec=r_m,
                                   pendiente_mec=s_m, intercepto_mec=i_m,
                                   resid_media=M['resid'].mean(1), r_resid_oc=r_res,
                                   pendiente_resid=s_res, R2_obs_sobre_mec=r_om ** 2))
            out = {k: float(Bt[k].iloc[0]) for k in Bt.columns}
            out.update(n=len(keys), resid_sd=float(Cc.resid.std(ddof=1)),
                       rango_oc=[float(Cc.oc.min()), float(Cc.oc.max())])
            out['ic95'] = {k: [float(np.percentile(Bt[k].iloc[1:], 2.5)),
                               float(np.percentile(Bt[k].iloc[1:], 97.5))] for k in Bt.columns}
            if conf == 'tr_g05' and conjunto == 'r1_40':
                np.savez_compressed(L.RES / 'r2_03_bootstrap_lineas.npz',
                                    pendiente=s_o[1:], intercepto=i_o[1:])
            # inferencia con dependencia sobre la estimacion puntual
            D = Cc.rename(columns={'brazo': 'arm', 'ventana': 'win'})
            for etq, f in (('OLS combinado', 'dW ~ oc'), ('EF ventana', 'dW ~ oc + C(win)'),
                           ('EF modelo', 'dW ~ oc + C(arm)'),
                           ('EF bidireccional', 'dW ~ oc + C(arm) + C(win)')):
                fit = smf.ols(f, D).fit()
                inf_rows.append(dict(config=conf, conjunto=conjunto, metodo=etq,
                                     pendiente=fit.params['oc'], se=fit.bse['oc'],
                                     nota='SE OLS ingenuo'))
            try:
                vc = {'arm': '0 + C(arm)', 'win': '0 + C(win)'}
                mm = smf.mixedlm('dW ~ oc', D, groups=np.ones(len(D)), vc_formula=vc).fit(reml=True)
                inf_rows.append(dict(config=conf, conjunto=conjunto,
                                     metodo='Efectos aleatorios cruzados',
                                     pendiente=mm.params['oc'], se=mm.bse['oc'],
                                     nota='REML, (1|modelo)+(1|ventana)'))
            except Exception as e:                      # noqa: BLE001
                L.log(f'mixedlm fallo ({clave}): {e}', LOG)
            for cl in ('arm', 'win'):
                t0, p, G = wild_cluster_restringido(D, cl)
                inf_rows.append(dict(config=conf, conjunto=conjunto,
                                     metodo=f'Wild cluster bootstrap por {"modelo" if cl == "arm" else "ventana"}',
                                     pendiente=out['pendiente'], t=t0, p_valor=p, clusters=G,
                                     nota='restringido, pesos de Webb, 9999 replicas'))
            for per in VENT:
                g = D[D.win == per]
                inf_rows.append(dict(config=conf, conjunto=conjunto,
                                     metodo=f'dentro de ventana {per}',
                                     pendiente=np.polyfit(g.oc, g.dW, 1)[0],
                                     r=np.corrcoef(g.oc, g.dW)[0, 1], n=len(g)))
            an = sm.stats.anova_lm(smf.ols('oc ~ C(arm) + C(win)', D).fit(), typ=2)
            tot = an.sum_sq.sum()
            out['anova_oc'] = {'modelo': float(an.sum_sq['C(arm)'] / tot),
                               'ventana': float(an.sum_sq['C(win)'] / tot),
                               'residuo': float(an.sum_sq['Residual'] / tot)}
            fam = D.groupby(['familia', 'win'])[['oc', 'dW']].mean()
            out['familia_x_ventana'] = dict(zip(('r', 'pendiente', 'intercepto'),
                                                ajuste(fam.oc, fam.dW)), n=len(fam))
            res[clave] = out
            L.log(f'{clave}: r {out["r"]:.3f} pend {out["pendiente"]:.2f} | mec r {out["r_mec"]:.3f} '
                  f'pend {out["pendiente_mec"]:.2f} | R2 {out["R2_obs_sobre_mec"]:.2f} | '
                  f'resid {out["resid_media"]:.2f} IC {out["ic95"]["resid_media"]}', LOG)

    # --------------------------------------------- prueba fuera de muestra (ES)
    lin = res['tr_g05|r1_40']
    es = TC[(TC.config == 'tr_g05') & (TC.brazo == 'hurdle_es')].copy()
    es['pred'] = lin['intercepto'] + lin['pendiente'] * es.oc
    bl = np.load(L.RES / 'r2_03_bootstrap_lineas.npz')
    pi = np.array([[np.percentile(bl['intercepto'] + bl['pendiente'] * o, q) for q in (2.5, 97.5)]
                   for o in es.oc])
    es['pred_lo'], es['pred_hi'] = pi[:, 0], pi[:, 1]
    err = es.dW - es.pred
    res['fuera_de_muestra_hurdle_es'] = dict(
        celdas=es[['ventana', 'oc', 'dW', 'pred', 'pred_lo', 'pred_hi']].round(3).to_dict('records'),
        r_obs_pred=float(np.corrcoef(es.dW, es.pred)[0, 1]),
        rmse=float(np.sqrt(np.mean(err ** 2))), sesgo_medio=float(err.mean()))
    L.log(f'fuera de muestra (hurdle ES): r {res["fuera_de_muestra_hurdle_es"]["r_obs_pred"]:.3f} '
          f'RMSE {res["fuera_de_muestra_hurdle_es"]["rmse"]:.2f}', LOG)

    pd.DataFrame(inf_rows).to_csv(L.RES / 'r2_03_inferencia.csv', index=False)
    json.dump(res, open(L.RES / 'r2_03_resumen.json', 'w'), indent=1, default=float)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ('r', 'pendiente', 'r_mec', 'pendiente_mec', 'R2_obs_sobre_mec', 'resid_media')}
                      for k, v in res.items() if '|' in k}, indent=1, default=float))


if __name__ == '__main__':
    main()
