#!/usr/bin/env python3
"""
R2-04. Evaluacion operacional: ponderaciones, cola, dias altos y costo.
=====================================================================
Comentario 3 del Revisor 2: Transport+ACI cubre 86.7% en dias de alto
vertimiento contra 91.9% del split estatico, y CQR domina al pipeline. Pide
cobertura ponderada por capacidad o por energia vertida, scores de cola y una
metrica simple de costo operacional, y que el Abstract y la Conclusion digan
que el pipeline de transporte no es el metodo operacional preferido.

Metricas, por modelo base x metodo, sobre el test completo:
  cobertura por central-dia (agrupada por fecha, la del paper)
  cobertura ponderada por capacidad instalada
  cobertura ponderada por energia vertida      sum y*1{y<=U} / sum y
  energia no cubierta                          sum (y-U)+ / sum y
  exceso medio dado que se excede              E[(y-U)+ | y > U]
  interval score unilateral (finito / total), ancho medio
  dias altos con TRES definiciones:
    H1 ex post (la de la R1): vertimiento sistemico del dia >= P90 de la
       ventana de calibracion (254 de 638 dias, porque la serie crece)
    H2 ex post: decil superior de los dias del TEST
    H3 ex ante: media movil de 7 dias del vertimiento sistemico conocida en el
       origen del pronostico (termina en T-7) >= el mismo umbral P90. Es un
       condicionamiento legitimo (informacion disponible al emitir); H1 y H2
       condicionan en el resultado (forecaster's dilemma, Lerch et al. 2017).
  costo operacional: un duenio reserva una holgura U a costo c_h por MWh y
    paga c_p por MWh vertido por encima de U. Con k = c_p / c_h la decision
    optima es el cuantil k/(1+k) y el costo esperado en unidades de c_h es
    EXACTAMENTE el interval score unilateral al nivel 1-1/k. Se evalua
    k = 10 (limites al 90%), k = 20 (95%) y k = 100 (99%): los dos ultimos son
    ademas los scores de cola.
Todas las diferencias clave llevan IC 95% por bootstrap de dias completos.

Salidas: resultados/r2_04_operacional.csv, r2_04_costo.csv,
         r2_04_condicional.csv, r2_04_diferencias.csv, r2_04_dias_altos.json
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_lib as L                      # noqa: E402
import numpy as np                      # noqa: E402
import pandas as pd                     # noqa: E402
R = L.R

LOG = 'r2_04_operacional.log'
B = 2000
# metodos por modelo base que entran a la evaluacion operacional
METODOS = ['static', 'aci_sel', 'tr_sel', 'tr_g05', 'aci_g05_amin005',
           'tr_g05_amin005', 'cqr']
ETIQ = {'static': 'Static split (PIT)', 'aci_sel': 'ACI (selected)',
        'tr_sel': 'Transport+ACI (selected)', 'tr_g05': 'Transport+ACI (gamma 0.05, R1)',
        'aci_g05_amin005': 'ACI (gamma 0.05, alpha_min 0.005)',
        'tr_g05_amin005': 'Transport+ACI (gamma 0.05, alpha_min 0.005)',
        'cqr': 'One-sided CQR'}


def benchmarks(h, idx):
    import fase4_metricas_benchmarks as F4
    df = h[['fecha', 'central_codigo', 'y_real']].copy()
    out = {}
    U, _ = F4.bench_cuantil_movil(df, 365); out['B1 empirical quantile 365 d'] = U[idx]
    U, _ = F4.bench_cuantil_movil(df, 60); out['B2 rolling distribution 60 d'] = U[idx]
    U, _ = F4.bench_zi_lognormal(df); out['B4 zero-inflated lognormal'] = U[idx]
    return out


def agregados(f, y, U, cap, alpha):
    """Sumas por dia de todo lo que necesitan las metricas (para el bootstrap)."""
    dias, di = np.unique(f, return_inverse=True)
    nD = len(dias)
    fi = np.isfinite(U)
    cub = (y <= U).astype(float)
    exc = np.where(fi, np.maximum(y - U, 0.0), 0.0)
    IS = np.where(fi, U + (1 / alpha) * np.maximum(y - U, 0.0), 0.0)
    bc = lambda w: np.bincount(di, w, nD)                       # noqa: E731
    return dict(dias=dias, n=bc(np.ones_like(y)), cub=bc(cub), y=bc(y), ycub=bc(y * cub),
                cap=bc(cap), capcub=bc(cap * cub), exc=bc(exc), nexc=bc((y > U).astype(float)),
                IS=bc(IS), nfin=bc(fi.astype(float)), w=bc(np.where(fi, U, 0.0)),
                covdia=bc(cub) / bc(np.ones_like(y)))


def metricas_de(Ag, w):
    """Metricas con pesos por dia w (vector) o matriz (replicas x dias)."""
    W = np.atleast_2d(w)
    s = {k: W @ v for k, v in Ag.items() if k not in ('dias',)}
    nd = W.sum(1)
    return dict(cobertura=100 * s['covdia'] / nd,            # agrupada por fecha
                cob_capacidad=100 * s['capcub'] / s['cap'],
                cob_energia=100 * s['ycub'] / s['y'],
                energia_no_cubierta=100 * s['exc'] / s['y'],
                exceso_medio=s['exc'] / np.maximum(s['nexc'], 1e-12),
                IS_finitos=s['IS'] / s['nfin'],
                ancho_medio=s['w'] / s['nfin'],
                pct_infinito=100 * (1 - s['nfin'] / s['n']))


def main():
    h = L.panel_filas()
    idx = ((h.fecha >= R.CAL_FIN) & (h.fecha < L.FIN_TEST)).values
    cal = ((h.fecha >= R.CAL_INI) & (h.fecha < R.CAL_FIN)).values
    test = h[idx].reset_index(drop=True)
    f_t, y_t = test.fecha.values, test.y_real.values
    cap = test.potencia_mw.values.astype(float)
    assert np.isfinite(cap).all()

    # ---- dias altos
    tot = h.groupby('fecha').y_real.sum()
    umbral = float(tot[(tot.index >= R.CAL_INI) & (tot.index < R.CAL_FIN)].quantile(0.90))
    tot_test = tot[(tot.index >= R.CAL_FIN) & (tot.index < L.FIN_TEST)]
    H1 = set(tot_test.index[tot_test >= umbral])
    H2 = set(tot_test.index[tot_test >= tot_test.quantile(0.90)])
    ma7_origen = tot.rolling(7).mean().shift(7)          # media de T-13..T-7, conocida en T-7
    H3 = set(tot_test.index[ma7_origen.reindex(tot_test.index) >= umbral])
    ft_s = pd.Series(pd.to_datetime(f_t))
    sub = {'all': np.ones(len(f_t), bool),
           'H1 ex post (cal. P90)': ft_s.isin(H1).values,
           'H2 ex post (test top decile)': ft_s.isin(H2).values,
           'H3 ex ante (regime known at origin)': ft_s.isin(H3).values}
    json.dump(dict(umbral_MWh_dia=umbral, H1_dias=len(H1), H2_dias=len(H2), H3_dias=len(H3),
                   dias_test=int(tot_test.size),
                   H1_y_H3_comunes=len(H1 & H3),
                   nota='sistema = suma de las centrales solares y eolicas del panel'),
              open(L.RES / 'r2_04_dias_altos.json', 'w'), indent=1)
    L.log(f'umbral {umbral:,.0f} MWh/dia | H1 {len(H1)} | H2 {len(H2)} | H3 {len(H3)} dias', LOG)

    # ---- series de todos los metodos
    series = {}
    for b in L.PRINCIPALES + ('hurdle_sigma_x',):
        S = pd.read_parquet(L.SERIES_DIR / f'{b}.parquet')
        assert np.allclose(S.y.values, y_t, atol=1e-6)
        for m in METODOS:
            if m in S:
                series[(b, m, 0.10)] = S[m].values
        for a, tag in ((0.05, 'a05'), (0.01, 'a01')):
            for m in ('static', 'cqr', 'aci_sel', 'tr_sel'):
                if f'{m}_{tag}' in S:
                    series[(b, m, a)] = S[f'{m}_{tag}'].values
    for nm, U in benchmarks(h, idx).items():
        series[('model-free', nm, 0.10)] = U
    for a, tag in ((0.05, 'a05'), (0.01, 'a01')):
        import fase4_metricas_benchmarks as F4
        df = h[['fecha', 'central_codigo', 'y_real']].copy()
        U, _ = F4.bench_cuantil_movil(df, 60, alpha=a)
        series[('model-free', 'B2 rolling distribution 60 d', a)] = U[idx]
        U, _ = F4.bench_cuantil_movil(df, 365, alpha=a)
        series[('model-free', 'B1 empirical quantile 365 d', a)] = U[idx]
        U, _ = F4.bench_zi_lognormal(df, alpha=a)
        series[('model-free', 'B4 zero-inflated lognormal', a)] = U[idx]

    # ---- metricas + bootstrap por dias
    rng = np.random.default_rng(R.SEED_BOOTSTRAP)
    dias_all = np.unique(f_t)
    Wb = np.vstack([np.bincount(rng.integers(0, len(dias_all), len(dias_all)),
                                minlength=len(dias_all)) for _ in range(B)]).astype(float)
    filas, BOOT = [], {}
    for (b, m, a), U in series.items():
        for sn, sm in sub.items():
            Ag = agregados(f_t[sm], y_t[sm], U[sm], cap[sm], a)
            pos = np.searchsorted(dias_all, Ag['dias'])
            w1 = np.ones(len(Ag['dias']))
            pt = {k: float(v[0]) for k, v in metricas_de(Ag, w1).items()}
            bt = metricas_de(Ag, Wb[:, pos])
            BOOT[(b, m, a, sn)] = bt
            fila = dict(base=b, metodo=m, etiqueta=ETIQ.get(m, m), alpha=a, subconjunto=sn,
                        n=int(sm.sum()), dias=len(Ag['dias']), **pt)
            for k in ('cobertura', 'cob_energia', 'energia_no_cubierta', 'IS_finitos'):
                fila[f'{k}_lo'] = float(np.nanpercentile(bt[k], 2.5))
                fila[f'{k}_hi'] = float(np.nanpercentile(bt[k], 97.5))
            filas.append(fila)
    T = pd.DataFrame(filas)
    T.to_csv(L.RES / 'r2_04_operacional.csv', index=False)

    # ---- costo: k = 10, 20, 100 sobre limites a 90, 95, 99%
    cos = T[(T.subconjunto == 'all')][['base', 'metodo', 'etiqueta', 'alpha', 'IS_finitos',
                                       'pct_infinito', 'cobertura', 'IS_finitos_lo', 'IS_finitos_hi']].copy()
    cos['k'] = (1 / cos.alpha).round().astype(int)
    cos = cos.rename(columns={'IS_finitos': 'costo_por_central_dia'})
    cos.to_csv(L.RES / 'r2_04_costo.csv', index=False)

    # ---- diferencias clave con IC (bootstrap pareado por dias)
    pares = [
        ('hurdle_800', 'tr_g05', 'hurdle_800', 'static'),
        ('hurdle_800', 'tr_sel', 'hurdle_800', 'static'),
        ('hurdle_es', 'tr_sel', 'hurdle_es', 'static'),
        ('hurdle_es', 'static', 'hurdle_800', 'static'),
        ('hurdle_es', 'static', 'hurdle_800', 'tr_sel'),
        ('qgbm_54x400', 'cqr', 'qgbm_54x400', 'static'),
        ('qgbm_54x400', 'tr_sel', 'qgbm_54x400', 'static'),
        ('qgbm_54x400', 'static', 'hurdle_es', 'static'),
        ('qgbm_54x400', 'cqr', 'hurdle_800', 'tr_sel'),
        ('hurdle_es', 'cqr', 'hurdle_es', 'static'),
    ]
    dif = []
    for a in (0.10, 0.05, 0.01):
        for (b1, m1, b2, m2) in pares:
            for sn in sub:
                k1, k2 = (b1, m1, a, sn), (b2, m2, a, sn)
                if k1 not in BOOT or k2 not in BOOT:
                    continue
                for met in ('cobertura', 'cob_energia', 'energia_no_cubierta', 'IS_finitos'):
                    d = BOOT[k1][met] - BOOT[k2][met]
                    p1 = T[(T.base == b1) & (T.metodo == m1) & (T.alpha == a) & (T.subconjunto == sn)][met].iloc[0]
                    p2 = T[(T.base == b2) & (T.metodo == m2) & (T.alpha == a) & (T.subconjunto == sn)][met].iloc[0]
                    lo, hi = np.nanpercentile(d, [2.5, 97.5])
                    dif.append(dict(alpha=a, subconjunto=sn, metrica=met,
                                    a=f'{b1}:{m1}', b=f'{b2}:{m2}', dif=p1 - p2, lo=lo, hi=hi,
                                    significativo=bool(lo * hi > 0)))
    pd.DataFrame(dif).to_csv(L.RES / 'r2_04_diferencias.csv', index=False)

    # ---- cobertura condicional (Tabla 11 ampliada): peor desvio por eje
    cortes = h[cal].groupby('central_codigo').potencia_mw.first().quantile([1 / 3, 2 / 3]).values
    test['tercil'] = pd.cut(test.potencia_mw, [-np.inf, *cortes, np.inf],
                            labels=['small', 'medium', 'large'])
    test['alto'] = np.where(sub['H1 ex post (cal. P90)'], 'high', 'rest')
    test['alto_exante'] = np.where(sub['H3 ex ante (regime known at origin)'], 'high', 'rest')
    cond = []
    for (b, m, a), U in series.items():
        if a != 0.10:
            continue
        cub = (y_t <= U).astype(float)
        fila = dict(base=b, metodo=m, etiqueta=ETIQ.get(m, m))
        for eje in ('tecnologia', 'tercil', 'region', 'alto', 'alto_exante'):
            peor = 0.0
            for g, gi in test.groupby(eje, observed=True).indices.items():
                if len(gi) < 200:
                    continue
                cov, _, _ = R.cm.cobertura_clusterizada(f_t[gi], cub[gi])
                peor = max(peor, abs(100 * cov - 90))
                if eje in ('alto', 'alto_exante'):
                    fila[f'cob_{eje}_{g}'] = 100 * cov
            fila[f'peor_{eje}'] = peor
        cond.append(fila)
    pd.DataFrame(cond).to_csv(L.RES / 'r2_04_condicional.csv', index=False)
    L.log('listo', LOG)
    v = T[(T.alpha == 0.10) & (T.subconjunto.isin(['all', 'H1 ex post (cal. P90)', 'H3 ex ante (regime known at origin)']))]
    print(v[['base', 'metodo', 'subconjunto', 'cobertura', 'cob_capacidad', 'cob_energia',
             'energia_no_cubierta', 'IS_finitos', 'ancho_medio']].round(1).to_string(index=False))


if __name__ == '__main__':
    main()
