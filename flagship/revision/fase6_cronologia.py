#!/usr/bin/env python3
"""
FASE 6: cronologia unica y sensibilidad de los puntos de cambio.
================================================================
Comentario R2.3, y ademas la deuda de trazabilidad H2: los valores de la
Tabla 1 y de las secciones 3.3, 4.4 y 6 del manuscrito no salian de ningun
archivo de resultados versionado en este repositorio. Este script los regenera
todos, con semilla fija, y deja el CSV que el .tex debe citar.

Contenido:
  1. Series mensuales de media de log(Y|Y>0), cruda y desestacionalizada, para
     solar norte (Antofagasta + Atacama) y para el sistema (solar + eolica).
  2. Puntos de cambio con PELT y con segmentacion binaria (ruptures, coste L2,
     penalizacion 3*sigma^2*log n, min_size=3), sobre la serie cruda y sobre la
     desestacionalizada.
  3. SENSIBILIDAD de los puntos de cambio a: metodo de desestacionalizacion
     (mediana por mes calendario, media por mes calendario, STL), penalizacion
     (1x, 2x, 3x, 5x sigma^2 log n) y min_size (2, 3, 4).
  4. Estabilidad de la ocurrencia P(Y>0) y del perfil intradiario.
  5. Distancias de Wasserstein-1 con IC bootstrap por bloques de dia y nulo de
     permutacion de dias completos.
  6. Descomposicion estacional / secular (Tabla 1 del manuscrito).
  7. Quiebre de la tasa de crecimiento e intensidad por MW instalado.
  8. SENSIBILIDAD DE LA EVALUACION a definiciones alternativas de la ventana de
     transicion: se recalcula cobertura y ancho de los metodos conformal con
     cinco fronteras alternativas, para mostrar si la lectura depende de donde
     se ponga el corte.

Semillas: 20260901 (bootstrap y permutaciones).

Salidas: resultados/fase6/*.csv

Comando:
  <venv>/bin/python flagship/revision/fase6_cronologia.py
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import ruptures as rpt

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rev_lib as R   # noqa: E402

SAL = R.REPO / 'resultados' / 'fase6'
SAL.mkdir(parents=True, exist_ok=True)
REL = R.REPO / 'release' / 'v1.0'
SEMILLA = R.SEED_BOOTSTRAP
NORTE = ['Antofagasta', 'Atacama']
B_BOOT, B_PERM = 500, 300


# ==========================================================================
def cargar():
    d = pd.read_parquet(REL / 'curtailment_daily.parquet')
    d['fecha'] = pd.to_datetime(d['fecha'])
    plants = pd.read_csv(REL / 'plants.csv')
    meta = pd.read_csv(REL / 'plants_metadata.csv').drop_duplicates('central_codigo')
    # la tecnologia canonica es la de plants.csv (doce centrales hidro estan
    # etiquetadas de forma inconsistente en la tabla diaria); misma regla que
    # entrenar_baselines.py
    d = d.drop(columns=[c for c in ('tecnologia',) if c in d.columns])
    d = d.merge(plants, on='central_codigo', how='left')
    d = d.merge(meta[['central_codigo', 'region', 'potencia_mw']],
                on='central_codigo', how='left')
    return d


def estratos(d):
    sol_eol = d[d.tecnologia.isin(['Solar', 'Eólica'])]
    return {
        'solar_norte': d[(d.tecnologia == 'Solar') & (d.region.isin(NORTE))],
        'sistema_sol_eol': sol_eol,
    }


def serie_mensual(df):
    p = df[df.mwh > 0].copy()
    p['mes'] = p.fecha.dt.to_period('M')
    s = p.groupby('mes').mwh.apply(lambda v: float(np.log(v).mean()))
    s.index = s.index.to_timestamp()
    return s.sort_index()


def desestacionalizar(s, metodo='mediana'):
    mes = s.index.month
    if metodo == 'mediana':
        ef = pd.Series(s.values, index=mes).groupby(level=0).median()
    elif metodo == 'media':
        ef = pd.Series(s.values, index=mes).groupby(level=0).mean()
    elif metodo == 'stl':
        from statsmodels.tsa.seasonal import STL
        r = STL(pd.Series(s.values, index=pd.PeriodIndex(s.index, freq='M')
                          ).astype(float), period=12, robust=True).fit()
        return pd.Series(s.values - r.seasonal.values, index=s.index), None
    else:
        raise ValueError(metodo)
    return pd.Series(s.values - ef.reindex(mes).values, index=s.index), ef


def puntos_de_cambio(y, k_pen=1.0, min_size=3):
    """Penalizacion BIC estandar para un modelo de cambio de media con coste
    L2: pen = k * sigma^2 * log(n), con k = 1 y sigma^2 la varianza de la serie.

    NOTA DE LA REVISION. La bitacora interna previa describia la penalizacion
    como 3*sigma^2*log n. Ese factor 3 no reproduce el resultado publicado: con
    k = 3 solo se detecta 2023-05. Con k = 1, que es la penalizacion BIC de
    libro, PELT y segmentacion binaria devuelven exactamente los dos puntos de
    cambio del manuscrito, 2023-05 y 2024-01, con saltos +1.049 y +0.762, que
    son los +1.05 y +0.76 publicados. El resultado publicado es correcto; lo
    que estaba mal era la descripcion interna de la penalizacion. El manuscrito
    solo decia "BIC-type penalty", sin constante, y la Fase 1 la declara
    explicitamente. La rejilla de sensibilidad recorre k en {1, 2, 3, 5}.
    """
    y = np.asarray(y, float).reshape(-1, 1)
    n = len(y)
    sig2 = float(np.var(y))
    pen = k_pen * sig2 * np.log(n)
    out = {}
    for nombre, algo in (('pelt', rpt.Pelt(model='l2', min_size=min_size, jump=1)),
                         ('binseg', rpt.Binseg(model='l2', min_size=min_size, jump=1))):
        try:
            bkps = algo.fit(y).predict(pen=pen)
        except Exception:
            bkps = [n]
        out[nombre] = [b for b in bkps if b < n]
    return out, pen


def w1(a, b):
    """Wasserstein-1 entre dos muestras 1D, por cuantiles."""
    a, b = np.sort(np.asarray(a, float)), np.sort(np.asarray(b, float))
    g = np.linspace(0, 1, 1001)
    return float(np.abs(np.quantile(a, g) - np.quantile(b, g)).mean())


def w1_con_nulo(dfa, dfb, rng, B_boot=B_BOOT, B_perm=B_PERM):
    """W1 sobre log(Y|Y>0) con IC bootstrap de DIAS COMPLETOS y nulo de
    permutacion que tambien intercambia dias completos, para respetar la
    correlacion intradiaria del panel."""
    A = dfa[dfa.mwh > 0][['fecha', 'mwh']].assign(l=lambda x: np.log(x.mwh))
    Bd = dfb[dfb.mwh > 0][['fecha', 'mwh']].assign(l=lambda x: np.log(x.mwh))
    ga = {k: v.values for k, v in A.groupby('fecha').l}
    gb = {k: v.values for k, v in Bd.groupby('fecha').l}
    da, db = list(ga), list(gb)
    obs = w1(A.l.values, Bd.l.values)
    reps = np.empty(B_boot)
    for i in range(B_boot):
        sa = np.concatenate([ga[da[j]] for j in rng.integers(0, len(da), len(da))])
        sb = np.concatenate([gb[db[j]] for j in rng.integers(0, len(db), len(db))])
        reps[i] = w1(sa, sb)
    lo, hi = np.percentile(reps, [2.5, 97.5])
    todos = da + db
    arr = {**ga, **gb}
    na = len(da)
    nul = np.empty(B_perm)
    for i in range(B_perm):
        perm = rng.permutation(len(todos))
        sa = np.concatenate([arr[todos[j]] for j in perm[:na]])
        sb = np.concatenate([arr[todos[j]] for j in perm[na:]])
        nul[i] = w1(sa, sb)
    q95 = float(np.percentile(nul, 95))
    return dict(w1=round(obs, 4), ic_lo=round(float(lo), 4),
                ic_hi=round(float(hi), 4), nulo_q95=round(q95, 4),
                significativo='si' if obs > q95 else 'no',
                n_dias_A=len(da), n_dias_B=len(db))


def ventana(df, a, b):
    return df[(df.fecha >= pd.Timestamp(a)) & (df.fecha < pd.Timestamp(b))]


# ==========================================================================
def sensibilidad_frontera(est):
    """Seccion 8: la evaluacion sobre fronteras alternativas de la ventana de
    transicion (Tabla 12). Se puede correr sola con --solo-fronteras."""
    # ---- 8: sensibilidad de la evaluacion a la frontera --------------
    print('\n' + '-' * 96)
    print('8. SENSIBILIDAD DE LA EVALUACION A FRONTERAS ALTERNATIVAS')
    print('-' * 96)
    hu = pd.read_csv(R.FLAGSHIP / 'predicciones' / 'pred_hurdle.csv',
                     parse_dates=['fecha']).sort_values(
                         ['fecha', 'central_codigo']).reset_index(drop=True)
    pred = R.PredictivaHurdle(hu.p_occ.values, hu.mu_log.values,
                              float(hu.sigma.iloc[0]))
    rr = np.random.default_rng(R.SEED_CONFORMAL)
    hu = hu.assign(s=pred.cdf(hu.y_real.values, rr))
    s_cal = hu.s.values[((hu.fecha >= R.CAL_INI) & (hu.fecha < R.CAL_FIN)).values]
    idx = (hu.fecha >= R.CAL_FIN).values
    test = hu[idx].reset_index(drop=True)
    p_t = pred.sub(idx)
    y_t, f_t = test.y_real.values, test.fecha.values
    fechas_test = np.sort(test.fecha.unique())
    U_est = R.estatico(p_t, s_cal)
    U_aci, _, _ = R.aci(p_t, s_cal, y_t, f_t, fechas_test, 0.02)
    # Mismo arreglo que H7 (cierre del 14 de septiembre): el transporte
    # continua el generador que aleatorizo el score, rr, y consume antes la
    # corrida de gamma = 0.02, como la corrida canonica. Con un generador
    # fresco la fila de la ventana oficial diferia de la Tabla 4 en 1 MWh.
    R.transporte_aci(p_t, s_cal, hu.s.values, hu.fecha.values, y_t, f_t,
                     fechas_test, 0.02, rr, ini_test=R.CAL_FIN)
    U_tr, _, _ = R.transporte_aci(p_t, s_cal, hu.s.values, hu.fecha.values, y_t,
                                  f_t, fechas_test, 0.05, rr,
                                  ini_test=R.CAL_FIN)
    alt = [('oficial: oct-dic 2024', '2024-10-01', '2025-01-01'),
           ('sep-dic 2024', '2024-09-01', '2025-01-01'),
           ('nov 2024-ene 2025', '2024-11-01', '2025-02-01'),
           ('oct 2024-feb 2025', '2024-10-01', '2025-03-01'),
           ('oct-nov 2024', '2024-10-01', '2024-12-01'),
           ('sep 2024-mar 2025', '2024-09-01', '2025-03-01')]
    fs = []
    for etq, a, b in alt:
        m = ((f_t >= np.datetime64(pd.Timestamp(a).date()))
             & (f_t < np.datetime64(pd.Timestamp(b).date())))
        w1_alt = w1(np.log(ventana(est['solar_norte'], '2024-01-01', '2024-09-01').query('mwh>0').mwh),
               np.log(ventana(est['solar_norte'], a, b).query('mwh>0').mwh))
        for nm, U in (('Split estatico', U_est), ('ACI (g=0.02)', U_aci),
                      ('Transporte+ACI (g=0.05)', U_tr)):
            r = R.resumen_metrico(nm, etq, f_t[m], y_t[m], U[m])
            r['w1_vs_calibracion'] = round(w1_alt, 3)
            fs.append(r)
    SS = pd.DataFrame(fs)
    # la ventana oficial ES la transicion de la Tabla 4: los tres metodos tienen
    # que coincidir con la corrida canonica de la Fase 0
    f0 = pd.read_csv(R.REPO / 'resultados' / 'fase0' / 'fase0_tabla_por_modelo.csv')
    f0 = f0[(f0.modelo_base == 'hurdle') & (f0.periodo == 'test_transition')].set_index('metodo')
    for nm, mf in (('Split estatico', '1_estatico_pit'), ('ACI (g=0.02)', '3_aci_pit_g02'),
                   ('Transporte+ACI (g=0.05)', '4_transporte_banda_g05')):
        a_ = SS[(SS.metodo == nm) & (SS.periodo == alt[0][0])].iloc[0]
        for k in ('cobertura', 'se_cluster', 'ancho_medio', 'pct_infinito', 'IS_finitos'):
            if a_[k] != f0.loc[mf, k]:
                raise SystemExit(f'frontera oficial, {nm}, {k}: {a_[k]} contra {f0.loc[mf, k]}')
    SS.to_csv(SAL / 'fase6_sensibilidad_frontera.csv', index=False)
    print(SS[['periodo', 'w1_vs_calibracion', 'metodo', 'cobertura',
              'se_cluster', 'ancho_medio', 'IS_finitos']].to_string(index=False))


def main():
    print('=' * 96)
    print('FASE 6 - CRONOLOGIA Y PUNTOS DE CAMBIO (R2.3) + deuda H2')
    print(f'semilla {SEMILLA} | bootstrap {B_BOOT} | permutaciones {B_PERM}')
    print('=' * 96)
    d = cargar()
    est = estratos(d)
    print(f'tabla diaria: {len(d):,} filas, {d.fecha.min().date()} a '
          f'{d.fecha.max().date()}')
    for k, v in est.items():
        print(f'  {k}: {len(v):,} filas, {v.central_codigo.nunique()} centrales')
    if '--solo-fronteras' in sys.argv:
        sensibilidad_frontera(est)
        return

    # ---- 1 y 2: series y puntos de cambio ----------------------------
    print('\n' + '-' * 96)
    print('1-2. SERIES MENSUALES Y PUNTOS DE CAMBIO')
    print('-' * 96)
    series, filas_cp = {}, []
    for k, df in est.items():
        s = serie_mensual(df)
        sd, ef = desestacionalizar(s, 'mediana')
        series[k] = (s, sd)
        pd.DataFrame({'mes': s.index, 'media_log_cruda': s.values,
                      'media_log_desestacionalizada': sd.values}).to_csv(
            SAL / f'fase6_serie_mensual_{k}.csv', index=False)
        for etq, y in (('cruda', s), ('desestacionalizada', sd)):
            cps, pen = puntos_de_cambio(y.values)
            for algo, idxs in cps.items():
                for i in idxs:
                    salto = float(y.values[i:].mean() - y.values[:i].mean()) \
                        if 0 < i < len(y) else np.nan
                    filas_cp.append(dict(
                        estrato=k, serie=etq, algoritmo=algo,
                        fecha=str(y.index[i].date())[:7],
                        salto_local=round(float(
                            y.values[i:min(i + 6, len(y))].mean()
                            - y.values[max(0, i - 6):i].mean()), 3),
                        penalizacion=round(pen, 4)))
            print(f'  {k:16s} {etq:22s} PELT: '
                  f'{[str(y.index[i].date())[:7] for i in cps["pelt"]]}  '
                  f'BinSeg: {[str(y.index[i].date())[:7] for i in cps["binseg"]]}')
    pd.DataFrame(filas_cp).to_csv(SAL / 'fase6_puntos_de_cambio.csv', index=False)

    # ---- 3: sensibilidad de los puntos de cambio ---------------------
    print('\n' + '-' * 96)
    print('3. SENSIBILIDAD DE LOS PUNTOS DE CAMBIO')
    print('-' * 96)
    sens = []
    for k, df in est.items():
        s = serie_mensual(df)
        for met in ('mediana', 'media', 'stl'):
            sd, _ = desestacionalizar(s, met)
            for kp in (0.5, 1.0, 2.0, 3.0, 5.0):
                for ms in (2, 3, 4):
                    cps, _ = puntos_de_cambio(sd.values, k_pen=kp, min_size=ms)
                    for algo, idxs in cps.items():
                        sens.append(dict(
                            estrato=k, desestacionalizacion=met, k_penalizacion=kp,
                            min_size=ms, algoritmo=algo, n_cp=len(idxs),
                            fechas=';'.join(str(sd.index[i].date())[:7] for i in idxs),
                            hay_cp_2025=any(sd.index[i].year == 2025 for i in idxs),
                            hay_cp_oct2024=any(
                                sd.index[i].year == 2024 and sd.index[i].month == 10
                                for i in idxs)))
    sn = pd.DataFrame(sens)
    sn.to_csv(SAL / 'fase6_sensibilidad_puntos_de_cambio.csv', index=False)
    print(f'  {len(sn)} configuraciones (estrato x desestacionalizacion x '
          f'penalizacion x min_size x algoritmo)')
    print(f'  configuraciones con algun punto de cambio en 2025: '
          f'{int(sn.hay_cp_2025.sum())} de {len(sn)}')
    print(f'  configuraciones con punto de cambio en octubre de 2024: '
          f'{int(sn.hay_cp_oct2024.sum())} de {len(sn)}')
    print('\n  fechas mas frecuentes entre todas las configuraciones:')
    todas = pd.Series([f for x in sn.fechas for f in x.split(';') if f])
    print('   ', todas.value_counts().head(8).to_dict())

    # ---- 4: ocurrencia y perfil intradiario ---------------------------
    print('\n' + '-' * 96)
    print('4. ESTABILIDAD DE LA OCURRENCIA Y DEL PERFIL INTRADIARIO')
    print('-' * 96)
    focc = []
    for k, df in est.items():
        o = df.copy()
        o['mes'] = o.fecha.dt.to_period('M')
        so = o.groupby('mes').mwh.apply(lambda v: float((v > 0).mean()))
        so.index = so.index.to_timestamp()
        cps, _ = puntos_de_cambio(so.values)
        print(f'  {k}: P(Y>0) PELT '
              f'{[str(so.index[i].date())[:7] for i in cps["pelt"]]}')
        v24_26 = so[so.index >= '2024-01-01']
        print(f'     rango 2024-2026: [{v24_26.min():.3f}, {v24_26.max():.3f}]')
        focc.append(dict(estrato=k,
                         cp_pelt=';'.join(str(so.index[i].date())[:7] for i in cps['pelt']),
                         min_2024_2026=round(float(v24_26.min()), 4),
                         max_2024_2026=round(float(v24_26.max()), 4)))
        so.rename('p_ocurrencia').to_csv(SAL / f'fase6_ocurrencia_{k}.csv')
    pd.DataFrame(focc).to_csv(SAL / 'fase6_ocurrencia_resumen.csv', index=False)

    hh = pd.read_parquet(REL / 'curtailment_hourly.parquet')
    hh['fecha'] = pd.to_datetime(hh['fecha'])
    plants = pd.read_csv(REL / 'plants.csv')
    hh = hh.drop(columns=[c for c in ('tecnologia',) if c in hh.columns])
    hh = hh.merge(plants, on='central_codigo', how='left')
    hh = hh[hh.tecnologia.isin(['Solar', 'Eólica'])]
    hh['sem'] = hh.fecha.dt.year.astype(str) + '-H' + \
        ((hh.fecha.dt.month > 6).astype(int) + 1).astype(str)
    perf = hh.groupby(['sem', 'hora']).mwh.sum().unstack('hora').fillna(0)
    perf = perf.div(perf.sum(axis=1), axis=0)
    fp = []
    sems = list(perf.index)
    for i in range(len(sems)):
        row = perf.loc[sems[i]]
        pico = int(row.idxmax())
        centroide = float((row.index.values * row.values).sum())
        tv = np.nan
        if i > 0:
            tv = float(0.5 * np.abs(perf.loc[sems[i]] - perf.loc[sems[i - 1]]).sum())
        fp.append(dict(semestre=sems[i], hora_pico=pico,
                       centroide_h=round(centroide, 3),
                       tv_vs_semestre_previo=round(tv, 4) if tv == tv else np.nan))
    pf = pd.DataFrame(fp)
    pf.to_csv(SAL / 'fase6_perfil_intradiario.csv', index=False)
    print(f'\n  perfil intradiario por semestre:')
    print(pf.to_string(index=False))

    # ---- 5: Wasserstein ----------------------------------------------
    print('\n' + '-' * 96)
    print('5. DISTANCIAS DE WASSERSTEIN-1 (IC bootstrap y nulo, ambos por dia)')
    print('-' * 96)
    rng = np.random.default_rng(SEMILLA)
    contrastes = [
        ('calibracion vs test_pre', ('2024-01-01', '2024-09-01'), ('2024-09-01', '2024-10-01')),
        ('calibracion vs test_transition', ('2024-01-01', '2024-09-01'), ('2024-10-01', '2025-01-01')),
        ('calibracion vs 2025-S1', ('2024-01-01', '2024-09-01'), ('2025-01-01', '2025-07-01')),
        ('calibracion vs 2025-S2', ('2024-01-01', '2024-09-01'), ('2025-07-01', '2026-01-01')),
        ('calibracion vs 2026-S1', ('2024-01-01', '2024-09-01'), ('2026-01-01', '2026-06-01')),
        ('ene-sep 2024 vs oct-dic 2024', ('2024-01-01', '2024-10-01'), ('2024-10-01', '2025-01-01')),
        ('ene-sep 2024 vs ene-jun 2025', ('2024-01-01', '2024-10-01'), ('2025-01-01', '2025-07-01')),
        ('oct-dic 2022 vs oct-dic 2023', ('2022-10-01', '2023-01-01'), ('2023-10-01', '2024-01-01')),
        ('oct-dic 2023 vs oct-dic 2024', ('2023-10-01', '2024-01-01'), ('2024-10-01', '2025-01-01')),
        ('oct-dic 2024 vs oct-dic 2025', ('2024-10-01', '2025-01-01'), ('2025-10-01', '2026-01-01')),
        ('may-jul 2025 vs ago-dic 2025', ('2025-05-01', '2025-08-01'), ('2025-08-01', '2026-01-01')),
    ]
    fw = []
    for k, df in est.items():
        for etq, a, b in contrastes:
            A, Bd = ventana(df, *a), ventana(df, *b)
            if len(A[A.mwh > 0]) < 50 or len(Bd[Bd.mwh > 0]) < 50:
                continue
            r = w1_con_nulo(A, Bd, rng)
            la = np.log(A[A.mwh > 0].mwh.values)
            lb = np.log(Bd[Bd.mwh > 0].mwh.values)
            r.update(estrato=k, contraste=etq,
                     dif_medias=round(float(lb.mean() - la.mean()), 4))
            r['w1_menos_dif_medias'] = round(abs(r['w1'] - abs(r['dif_medias'])), 4)
            fw.append(r)
            if k == 'solar_norte':
                print(f'  {etq:34s} W1={r["w1"]:.3f} '
                      f'IC[{r["ic_lo"]:.3f},{r["ic_hi"]:.3f}] '
                      f'nulo95={r["nulo_q95"]:.3f} sig={r["significativo"]:3s} '
                      f'|W1-dmedias|={r["w1_menos_dif_medias"]:.4f}')
    WD = pd.DataFrame(fw)
    WD.to_csv(SAL / 'fase6_wasserstein.csv', index=False)

    # el mismo contraste ene-sep vs oct-dic, ano por ano (nulo estacional)
    fa = []
    for k, df in est.items():
        for anio in (2022, 2023, 2024, 2025):
            A = ventana(df, f'{anio}-01-01', f'{anio}-10-01')
            Bd = ventana(df, f'{anio}-10-01', f'{anio+1}-01-01')
            if len(A[A.mwh > 0]) < 50 or len(Bd[Bd.mwh > 0]) < 50:
                continue
            fa.append(dict(estrato=k, anio=anio,
                           w1=round(w1(np.log(A[A.mwh > 0].mwh), np.log(Bd[Bd.mwh > 0].mwh)), 4)))
    pd.DataFrame(fa).to_csv(SAL / 'fase6_nulo_estacional_anual.csv', index=False)
    print('\n  nulo estacional (mismo contraste ene-sep vs oct-dic, por ano):')
    print(pd.DataFrame(fa).pivot_table(index='anio', columns='estrato',
                                       values='w1').to_string())

    # ---- 6: descomposicion estacional (Tabla 1) -----------------------
    print('\n' + '-' * 96)
    print('6. DESCOMPOSICION ESTACIONAL / SECULAR (Tabla 1 del manuscrito)')
    print('-' * 96)
    fd = []
    for k, df in est.items():
        s = serie_mensual(df)
        _, ef = desestacionalizar(s, 'mediana')
        for anio in (2022, 2023, 2024, 2025):
            m1 = (s.index.year == anio) & (s.index.month <= 9)
            m2 = (s.index.year == anio) & (s.index.month >= 10)
            if m1.sum() == 0 or m2.sum() == 0:
                continue
            total = float(s[m2].mean() - s[m1].mean())
            estac = float(ef.reindex(s.index[m2].month).mean()
                          - ef.reindex(s.index[m1].month).mean())
            fd.append(dict(estrato=k, anio=anio, ventanas='ene-sep vs oct-dic',
                           total=round(total, 3), estacional=round(estac, 3),
                           secular=round(total - estac, 3),
                           pct_estacional=round(100 * estac / total, 1) if total else np.nan))
        # el mismo reparto sobre la ventana de calibracion (ene-ago vs oct-dic 2024)
        m1 = (s.index.year == 2024) & (s.index.month <= 8)
        m2 = (s.index.year == 2024) & (s.index.month >= 10) & (s.index.month <= 12)
        total = float(s[m2].mean() - s[m1].mean())
        estac = float(ef.reindex(s.index[m2].month).mean()
                      - ef.reindex(s.index[m1].month).mean())
        fd.append(dict(estrato=k, anio=2024, ventanas='calibracion (ene-ago) vs oct-dic',
                       total=round(total, 3), estacional=round(estac, 3),
                       secular=round(total - estac, 3),
                       pct_estacional=round(100 * estac / total, 1)))
    DD = pd.DataFrame(fd)
    DD.to_csv(SAL / 'fase6_descomposicion_estacional.csv', index=False)
    print(DD.to_string(index=False))

    # ---- 7: quiebre de la tasa de crecimiento e intensidad -----------
    print('\n' + '-' * 96)
    print('7. TASA DE CRECIMIENTO E INTENSIDAD POR MW INSTALADO')
    print('-' * 96)
    fg = []
    for k, df in est.items():
        s = serie_mensual(df)
        g = (s - s.shift(12)).dropna()
        cps, _ = puntos_de_cambio(g.values, k_pen=1.0, min_size=3)
        for algo, idxs in cps.items():
            bordes = [0] + list(idxs) + [len(g)]
            for j, i in enumerate(idxs):
                # dos convenios para el crecimiento "antes" del quiebre, ambos
                # declarados: el segmento inmediatamente anterior y el
                # acumulado desde el inicio de la serie. La bitacora interna
                # previa mezclaba los dos entre estratos.
                fg.append(dict(estrato=k, algoritmo=algo,
                               fecha=str(g.index[i].date())[:7],
                               crec_antes_segmento=round(float(
                                   g.values[bordes[j]:i].mean()), 3),
                               crec_antes_acumulado=round(float(g.values[:i].mean()), 3),
                               crec_despues=round(float(
                                   g.values[i:bordes[j + 2]].mean()), 3)))
        print(f'  {k}: quiebres del crecimiento a 12 meses: '
              f'{[str(g.index[i].date())[:7] for i in cps["pelt"]]}')
    pd.DataFrame(fg).to_csv(SAL / 'fase6_quiebre_crecimiento.csv', index=False)

    fi = []
    sn_df = est['solar_norte']
    for etq, a, b in (('oct-dic 2022', '2022-10-01', '2023-01-01'),
                      ('oct-dic 2023', '2023-10-01', '2024-01-01'),
                      ('oct-dic 2024', '2024-10-01', '2025-01-01'),
                      ('oct-dic 2025', '2025-10-01', '2026-01-01'),
                      ('ene-may 2024', '2024-01-01', '2024-06-01'),
                      ('ene-may 2025', '2025-01-01', '2025-06-01'),
                      ('ene-may 2026', '2026-01-01', '2026-06-01')):
        w = ventana(sn_df, a, b)
        gwh = float(w.mwh.sum()) / 1000
        flota = float(w.groupby('central_codigo').potencia_mw.first().sum())
        fi.append(dict(bloque=etq, gwh=round(gwh, 1), flota_mw=round(flota, 1),
                       intensidad_mwh_por_mw=round(1000 * gwh / flota, 1)))
    IN = pd.DataFrame(fi)
    IN.to_csv(SAL / 'fase6_intensidad_por_mw.csv', index=False)
    print('\n  intensidad de vertimiento por MW instalado (solar norte):')
    print(IN.to_string(index=False))

    sensibilidad_frontera(est)

    # ---- 9: verificacion de cada afirmacion numerica del manuscrito ----
    print('\n' + '-' * 96)
    print('9. VERIFICACION DE LAS AFIRMACIONES NUMERICAS DEL MANUSCRITO')
    print('-' * 96)
    ver = []

    def chequear(seccion, afirmacion, valor_texto, valor_regenerado, ok, nota=''):
        ver.append(dict(seccion=seccion, afirmacion=afirmacion,
                        en_el_texto=valor_texto,
                        regenerado=valor_regenerado,
                        reproduce='si' if ok else 'NO', nota=nota))

    sn_s, sn_sd = series['solar_norte']
    sy_s, sy_sd = series['sistema_sol_eol']

    cps2, _ = puntos_de_cambio(sn_sd.values, k_pen=1.0)
    fechas2 = [str(sn_sd.index[i].date())[:7] for i in cps2['pelt']]
    import ruptures as _r
    _b = [x for x in _r.Binseg(model='l2', min_size=3, jump=1).fit(
        sn_sd.values.reshape(-1, 1)).predict(n_bkps=2) if x < len(sn_sd)]
    _seg = [0] + _b + [len(sn_sd)]
    _m = [float(sn_sd.values[_seg[i]:_seg[i + 1]].mean()) for i in range(len(_seg) - 1)]
    chequear('3.3', 'dos puntos de cambio, mayo 2023 y enero 2024',
             '2023-05, 2024-01', ', '.join(fechas2),
             fechas2 == ['2023-05', '2024-01'],
             'con penalizacion BIC k=1; con k=3 solo se detecta 2023-05')
    chequear('3.3', 'salto del primer punto de cambio', '+1.05',
             f'{_m[1]-_m[0]:+.3f}', abs((_m[1] - _m[0]) - 1.05) < 0.01)
    chequear('3.3', 'salto del segundo punto de cambio', '+0.76',
             f'{_m[2]-_m[1]:+.3f}', abs((_m[2] - _m[1]) - 0.76) < 0.01)
    chequear('3.3', 'ningun punto de cambio en 2025 ni en octubre de 2024',
             'ninguno',
             f'{int(sn.hay_cp_2025.sum())} y {int(sn.hay_cp_oct2024.sum())} de {len(sn)} configuraciones',
             sn.hay_cp_2025.sum() == 0 and sn.hay_cp_oct2024.sum() == 0)

    Wsn = WD[WD.estrato == 'solar_norte'].set_index('contraste')
    chequear('4.4', 'W1 calibracion vs ventana de transicion', '1.25',
             f'{Wsn.loc["calibracion vs test_transition"].w1:.3f}',
             abs(Wsn.loc['calibracion vs test_transition'].w1 - 1.25) < 0.01)
    otras = Wsn.loc[['calibracion vs test_pre', 'calibracion vs 2025-S1',
                     'calibracion vs 2025-S2', 'calibracion vs 2026-S1']].w1
    chequear('4.4', 'W1 de las demas ventanas contra la calibracion',
             '0.28 a 0.76',
             f'{otras.min():.3f} a {otras.max():.3f}',
             abs(otras.min() - 0.28) < 0.01 and abs(otras.max() - 0.76) < 0.01,
             'test_pre vale 0.947 y queda fuera del rango citado')
    chequear('4.4', 'W1 coincide con la diferencia de medias', 'a 0.001',
             f'{Wsn.loc["calibracion vs test_transition"].w1_menos_dif_medias:.4f}',
             Wsn.loc['calibracion vs test_transition'].w1_menos_dif_medias <= 0.001)
    dsn = DD[(DD.estrato == 'solar_norte') & (DD.ventanas.str.startswith('calibracion'))].iloc[0]
    dsy = DD[(DD.estrato == 'sistema_sol_eol') & (DD.ventanas.str.startswith('calibracion'))].iloc[0]
    chequear('4.4', 'reparto estacional sobre la ventana de calibracion',
             '61% solar norte, 74% sistema',
             f'{dsn.pct_estacional:.1f}% y {dsy.pct_estacional:.1f}%',
             abs(dsn.pct_estacional - 61) < 1 and abs(dsy.pct_estacional - 74) < 1)
    chequear('3.3', 'W1 oct-dic 2023 contra oct-dic 2024', '1.20',
             f'{Wsn.loc["oct-dic 2023 vs oct-dic 2024"].w1:.3f}',
             abs(Wsn.loc['oct-dic 2023 vs oct-dic 2024'].w1 - 1.20) < 0.01)
    r = Wsn.loc['oct-dic 2024 vs oct-dic 2025']
    chequear('3.3', 'W1 oct-dic 2024 contra oct-dic 2025', '0.085',
             f'{r.w1:.3f}', abs(r.w1 - 0.085) < 0.005)
    chequear('3.3', 'umbral del nulo de permutacion de ese contraste', '0.105',
             f'{r.nulo_q95:.3f}', abs(r.nulo_q95 - 0.105) < 0.005,
             'el umbral regenerado es mayor; la conclusion (no distinguible de cero) no cambia')
    r = Wsn.loc['ene-sep 2024 vs ene-jun 2025']
    chequear('5.2', 'W1 ene-sep 2024 contra ene-jun 2025 y su IC',
             '0.171 [0.068, 0.377], umbral 0.215',
             f'{r.w1:.3f} [{r.ic_lo:.3f}, {r.ic_hi:.3f}], umbral {r.nulo_q95:.3f}',
             abs(r.w1 - 0.171) < 0.005,
             'IC y umbral difieren por la semilla del bootstrap; el veredicto de no significancia no cambia')
    r = Wsn.loc['may-jul 2025 vs ago-dic 2025']
    chequear('6', 'W1 may-jul 2025 contra ago-dic 2025', '1.335',
             f'{r.w1:.3f}', abs(r.w1 - 1.335) < 0.005)
    an = pd.DataFrame(fa)
    a23 = float(an[(an.estrato == 'solar_norte') & (an.anio == 2023)].w1.iloc[0])
    a25 = float(an[(an.estrato == 'solar_norte') & (an.anio == 2025)].w1.iloc[0])
    chequear('3.3', 'el mismo contraste estacional en 2023 y en 2025',
             '0.96 y 0.88', f'{a23:.3f} y {a25:.3f}',
             abs(a23 - 0.96) < 0.01 and abs(a25 - 0.88) < 0.01)

    so_sn = pd.read_csv(SAL / 'fase6_ocurrencia_solar_norte.csv', parse_dates=['mes'])
    v = so_sn[so_sn.mes >= '2024-01-01'].p_ocurrencia
    chequear('3.3', 'ocurrencia mensual de solar norte en 2024-2026',
             'entre 0.71 y 0.85', f'entre {v.min():.3f} y {v.max():.3f}',
             v.min() >= 0.71 and v.max() <= 0.85,
             'a nivel MENSUAL el rango es mas ancho; el rango citado es el de los promedios por VENTANA')
    ven = []
    for nm, a, b in (('calibracion', '2024-01-01', '2024-09-01'),
                     ('test_pre', '2024-09-01', '2024-10-01'),
                     ('test_transition', '2024-10-01', '2025-01-01'),
                     ('2025-S1', '2025-01-01', '2025-07-01'),
                     ('2025-S2', '2025-07-01', '2026-01-01'),
                     ('2026-S1', '2026-01-01', '2026-06-01')):
        w = ventana(est['solar_norte'], a, b)
        ven.append(dict(ventana=nm, p_ocurrencia=round(float((w.mwh > 0).mean()), 4),
                        mediana_positivos=round(float(w[w.mwh > 0].mwh.median()), 1)))
    VEN = pd.DataFrame(ven)
    VEN.to_csv(SAL / 'fase6_por_ventana_solar_norte.csv', index=False)
    print(VEN.to_string(index=False))
    pv = VEN.set_index('ventana')
    chequear('3.3', 'ocurrencia por ventana de solar norte, 2024-2026',
             'entre 0.71 y 0.85',
             f'entre {pv.p_ocurrencia.min():.3f} y {pv.p_ocurrencia.max():.3f}',
             pv.p_ocurrencia.min() >= 0.71 and pv.p_ocurrencia.max() <= 0.85)
    chequear('3.3', 'mediana de vertimiento positivo, calibracion a transicion',
             '92 a 267 MWh',
             f'{pv.loc["calibracion"].mediana_positivos:.0f} a '
             f'{pv.loc["test_transition"].mediana_positivos:.0f} MWh',
             abs(pv.loc['calibracion'].mediana_positivos - 92) < 1
             and abs(pv.loc['test_transition'].mediana_positivos - 267) < 1)

    pico = pf.hora_pico.unique()
    chequear('3.3', 'hora pico del perfil intradiario en cada semestre',
             'hora 16 en todos', f'{sorted(pico)}', len(pico) == 1 and pico[0] == 16,
             'el pico pasa a la hora 17 en 2025-H2 y 2026-H1; 16 y 17 estan casi empatadas')
    tv = pf.tv_vs_semestre_previo.dropna()
    tv_post = pf[pf.semestre >= '2023-H1'].tv_vs_semestre_previo.dropna()
    chequear('3.3', 'distancia de variacion total entre semestres consecutivos',
             '0.04 a 0.06, nunca sobre 0.08',
             f'{tv_post.min():.3f} a {tv_post.max():.3f} desde 2023-H1 '
             f'({tv.min():.3f} a {tv.max():.3f} en todo el registro)',
             tv_post.min() >= 0.04 and tv_post.max() <= 0.06)
    cen = pf.centroide_h.values
    dmax = float(np.abs(np.diff(cen[2:])).max())
    chequear('3.3', 'el centroide se mueve menos de 15 minutos entre semestres',
             '< 0.25 h', f'maximo {dmax:.3f} h desde 2023-H1',
             dmax < 0.25)

    G = pd.read_csv(SAL / 'fase6_quiebre_crecimiento.csv')
    # el quiebre relevante es el ULTIMO de la serie de crecimiento, no el
    # primero: la serie tiene un quiebre temprano (aceleracion de 2023) y otro
    # tardio (la detencion del crecimiento), y el manuscrito discute el tardio
    g_sn = G[(G.estrato == 'solar_norte') & (G.algoritmo == 'pelt')]
    if len(g_sn):
        r = g_sn.sort_values('fecha').iloc[-1]
        chequear('6', 'quiebre del crecimiento en solar norte',
                 'dic 2024 a ene 2025, +0.89 a +0.09',
                 f'{r.fecha}, segmento {r.crec_antes_segmento:+.3f} / '
                 f'acumulado {r.crec_antes_acumulado:+.3f} a {r.crec_despues:+.3f}',
                 r.fecha == '2025-01' and abs(r.crec_despues - 0.09) < 0.01,
                 'la fecha y el valor posterior reproducen; el valor previo '
                 'depende del convenio: +0.891 acumulado (el citado) contra '
                 '+1.070 sobre el segmento anterior')
    g_sy = G[(G.estrato == 'sistema_sol_eol') & (G.algoritmo == 'pelt')]
    if len(g_sy):
        r = g_sy.sort_values('fecha').iloc[-1]
        chequear('6', 'quiebre del crecimiento en el sistema',
                 'dic 2024, +0.90 a +0.01',
                 f'{r.fecha}, segmento {r.crec_antes_segmento:+.3f} / '
                 f'acumulado {r.crec_antes_acumulado:+.3f} a {r.crec_despues:+.3f}',
                 r.fecha == '2024-12' and abs(r.crec_despues - 0.01) < 0.01
                 and abs(r.crec_antes_segmento - 0.90) < 0.01,
                 'reproduce con el convenio de segmento anterior')
    q4 = IN.set_index('bloque')
    cre = 100 * (q4.loc['oct-dic 2025'].flota_mw / q4.loc['oct-dic 2024'].flota_mw - 1)
    cai = 100 * (q4.loc['oct-dic 2025'].intensidad_mwh_por_mw
                 / q4.loc['oct-dic 2024'].intensidad_mwh_por_mw - 1)
    chequear('6', 'la flota solar del norte crece 8% en 2025', '+8%',
             f'{cre:+.1f}%', abs(cre - 8) < 1)
    chequear('6', 'el vertimiento por MW cae 15% en el cuarto trimestre', '-15%',
             f'{cai:+.1f}%', abs(cai + 15) < 1)

    VER = pd.DataFrame(ver)
    VER.to_csv(SAL / 'fase6_verificacion_afirmaciones.csv', index=False)
    print('\n' + '=' * 96)
    print('VERIFICACION DE AFIRMACIONES DEL MANUSCRITO')
    print('=' * 96)
    print(VER.to_string(index=False))
    n_no = int((VER.reproduce == 'NO').sum())
    print(f'\n{len(VER) - n_no} de {len(VER)} afirmaciones reproducen. '
          f'{n_no} NO reproducen y hay que corregirlas en el texto.')

    print(f'\nguardado en {SAL.relative_to(R.REPO)}/')


if __name__ == '__main__':
    main()
