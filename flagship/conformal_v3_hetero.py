#!/usr/bin/env python3
"""
PRUEBA END TO END DEL NEGATIVE RESULT sigma(x): capa conformal sobre el modelo
base heterocedastico contra el de sigma constante.
==============================================================================
Tarea de Kerven Cea: correr la capa conformal (estatico, ventana deslizante,
ACI, transporte + ACI) sobre pred_hurdle_hetero.csv con el MISMO protocolo y
los mismos cortes que conformal_v3_real.py, y comparar contra sigma constante,
para confirmar o refutar en numeros el trade-off anticipado: intervalos
marginalmente mas sharp en el bulk con subcobertura en centrales grandes.

Para que la comparacion sea limpia, este script corre el pipeline COMPLETO dos
veces con el mismo codigo y la misma semilla, cambiando solo la dispersion:
sigma constante (pred_hurdle.csv) contra sigma(x) (pred_hurdle_hetero.csv). El
embargo de horizonte de 7 dias esta implementado en los metodos online (ventana
que termina en t-7 y retroalimentacion de alpha del ACI retrasada 7 pasos),
identico a conformal_v3_real.py.

DATOS REALES. No aplica al panel sintetico. Salidas separadas y rotuladas.
"""
from collections import deque
from pathlib import Path
import sys

import numpy as np
import pandas as pd

FLAGSHIP = Path(__file__).resolve().parent
sys.path.insert(0, str(FLAGSHIP))
import conformal_metodos as cm   # noqa: E402

ALPHA = 0.10
EMBARGO_DIAS = 7
SEED = 20260720
RELEASE = FLAGSHIP.parent / 'release' / 'v1.0'
PRED = FLAGSHIP / 'predicciones'
CAL_INI, CAL_FIN = pd.Timestamp('2024-01-01'), pd.Timestamp('2024-09-01')


def cargar(csv, col_sigma):
    h = pd.read_csv(PRED / csv, parse_dates=['fecha'])
    h = h.sort_values(['fecha', 'central_codigo']).reset_index(drop=True)
    h['p'] = np.clip(h.p_occ.values, 1e-6, 1 - 1e-6)
    h['mu'] = h.mu_log.values
    h['sig'] = h[col_sigma].values
    return h


def muestrear(p, mu, sig, rng, n=300):
    occ = rng.random((len(p), n)) < np.asarray(p)[:, None]
    mag = np.exp(np.asarray(mu)[:, None] + np.asarray(sig)[:, None] * rng.standard_normal((len(p), n)))
    return np.where(occ, mag, 0.0)


def correr(h, etiqueta):
    """Corre las 4 familias de metodos sobre h (con su columna sig por fila) y
    devuelve (filas de metrica, dict metodo->U sobre test, test)."""
    rng = np.random.default_rng(SEED)  # misma semilla de atomo para ambos modelos
    s_all = cm.pit_score(h.p.values, h.mu.values, h.sig.values, h.y_real.values, rng)
    h = h.assign(s=s_all)

    es_cal = (h.fecha >= CAL_INI) & (h.fecha < CAL_FIN)
    cal = h[es_cal]
    test = h[h.fecha >= CAL_FIN].reset_index(drop=True)
    s_cal = cal.s.values
    fechas_test = np.sort(test.fecha.unique())
    p_t, mu_t, sg_t = test.p.values, test.mu.values, test.sig.values
    y_t, f_t = test.y_real.values, test.fecha.values
    fechas_h = h.fecha.values

    filas, U_series = [], {}

    # 1. estatico PIT
    qhat = cm.q_conformal(s_cal, ALPHA)
    U_est = cm.pit_upper(p_t, mu_t, sg_t, qhat)
    filas += cm.filas_por_periodo('1_estatico_pit', f_t, y_t, U_est)
    U_series['1. Estatico PIT'] = U_est

    # 2. ventana deslizante 60d, refresco 7d, embargo 7d
    U_vent = np.full(len(test), np.nan)
    for t0 in pd.date_range('2024-09-01', '2026-05-31', freq='7D'):
        ini = np.datetime64((t0 - pd.Timedelta(days=60 + EMBARGO_DIAS)).date())
        fin = np.datetime64((t0 - pd.Timedelta(days=EMBARGO_DIAS)).date())
        win = (fechas_h >= ini) & (fechas_h < fin)
        obj = (f_t >= np.datetime64(t0.date())) & (f_t < np.datetime64((t0 + pd.Timedelta(days=7)).date()))
        if obj.sum() == 0 or win.sum() < 100:
            continue
        q_w = cm.q_conformal(h.s.values[win], ALPHA)
        U_vent[obj] = cm.pit_upper(p_t[obj], mu_t[obj], sg_t[obj], q_w)
    filas += cm.filas_por_periodo('2_ventana60d_pit', f_t, y_t, U_vent)
    U_series['2. Ventana 60d PIT'] = U_vent

    # 3. ACI sobre PIT, embargo 7d
    for gamma in (0.02, 0.05):
        U_aci = correr_aci(np.sort(s_cal), p_t, mu_t, sg_t, y_t, f_t, fechas_test, gamma)
        filas += cm.filas_por_periodo(f'3_aci_pit_g{gstr(gamma)}', f_t, y_t, U_aci)
        if abs(gamma - 0.05) < 1e-9:
            U_series['3. ACI PIT (g=0.05)'] = U_aci

    # 4. transporte + ACI con banda, embargo 7d
    for gamma in (0.02, 0.05):
        U_tr = correr_transporte_aci(h, s_cal, p_t, mu_t, sg_t, y_t, f_t, fechas_test, gamma)
        filas += cm.filas_por_periodo(f'4_transporte_banda_g{gstr(gamma)}', f_t, y_t, U_tr)
        if abs(gamma - 0.05) < 1e-9:
            U_series['4. Transporte + ACI banda (g=0.05)'] = U_tr

    for fila in filas:
        fila['modelo'] = etiqueta
    return filas, U_series, test


def gstr(g):
    return str(g).replace('0.', '')


def correr_aci(pool_ord, p_t, mu_t, sg_t, y_t, f_t, fechas_test, gamma):
    alpha_t = ALPHA
    U = np.empty(len(f_t))
    pendientes = deque()
    for f in fechas_test:
        mask = f_t == f
        q_t = cm.q_desde_pool(pool_ord, alpha_t)
        U_t = cm.pit_upper(p_t[mask], mu_t[mask], sg_t[mask], q_t)
        U[mask] = U_t
        pendientes.append(1 - (y_t[mask] <= U_t).mean())
        if len(pendientes) > EMBARGO_DIAS:
            alpha_t = np.clip(alpha_t + gamma * (ALPHA - pendientes.popleft()), -1.0, 2.0)
    return U


def correr_transporte_aci(h, s_cal, p_t, mu_t, sg_t, y_t, f_t, fechas_test, gamma,
                          refresco_dias=7, ventana_dias=60):
    rng = np.random.default_rng(SEED + 1)
    fechas_h = h.fecha.values
    alpha_t = ALPHA
    U = np.empty(len(f_t))
    pool = np.sort(s_cal)
    prox = pd.Timestamp('2024-09-01')
    pendientes = deque()
    for f in fechas_test:
        f_ts = pd.Timestamp(f)
        if f_ts >= prox:
            ini = np.datetime64((f_ts - pd.Timedelta(days=ventana_dias + EMBARGO_DIAS)).date())
            fin = np.datetime64((f_ts - pd.Timedelta(days=EMBARGO_DIAS)).date())
            reciente = (fechas_h >= ini) & (fechas_h < fin)
            s_new = h.s.values[reciente]
            if len(s_new) >= 100:
                T, _ = cm.mapa_transporte_banda(s_cal, s_new, rng)
                pool = np.sort(T(s_cal))
            prox = f_ts + pd.Timedelta(days=refresco_dias)
        mask = f_t == f
        q_t = cm.q_desde_pool(pool, alpha_t)
        U_t = cm.pit_upper(p_t[mask], mu_t[mask], sg_t[mask], q_t)
        U[mask] = U_t
        pendientes.append(1 - (y_t[mask] <= U_t).mean())
        if len(pendientes) > EMBARGO_DIAS:
            alpha_t = np.clip(alpha_t + gamma * (ALPHA - pendientes.popleft()), -1.0, 2.0)
    return U


def main():
    print("=" * 80)
    print("PRUEBA END TO END sigma(x): capa conformal, sigma constante vs sigma(x)")
    print("DATOS REALES. Mismo protocolo, misma semilla, con embargo de 7 dias.")
    print("=" * 80)

    h_const = cargar('pred_hurdle.csv', 'sigma')
    h_het = cargar('pred_hurdle_hetero.csv', 'sigma_x')
    assert h_const[['fecha', 'central_codigo']].equals(h_het[['fecha', 'central_codigo']])
    print(f"\nsigma constante = {h_const.sig.iloc[0]:.4f} | "
          f"sigma(x): mediana={np.median(h_het.sig):.3f} "
          f"p10={np.quantile(h_het.sig,.1):.3f} p90={np.quantile(h_het.sig,.9):.3f}")

    filas_c, U_c, test = correr(h_const, 'const')
    filas_h, U_h, _ = correr(h_het, 'sigma(x)')

    # -------- tabla comparativa metodo x periodo --------
    tc = pd.DataFrame(filas_c)[['metodo', 'periodo', 'cobertura', 'se_cluster', 'ancho_medio', 'pct_infinito']]
    th = pd.DataFrame(filas_h)[['metodo', 'periodo', 'cobertura', 'se_cluster', 'ancho_medio', 'pct_infinito']]
    comp = tc.merge(th, on=['metodo', 'periodo'], suffixes=('_const', '_hetero'))
    comp['d_cobertura'] = (comp.cobertura_hetero - comp.cobertura_const).round(1)
    comp['d_ancho_pct'] = (100 * (comp.ancho_medio_hetero - comp.ancho_medio_const)
                           / comp.ancho_medio_const).round(1)
    orden = {n: i for i, (n, _, _) in enumerate(cm.PERIODOS)}
    comp = comp.sort_values(['metodo', 'periodo'], key=lambda s: s.map(orden) if s.name == 'periodo' else s)
    cols = ['metodo', 'periodo', 'cobertura_const', 'cobertura_hetero', 'd_cobertura',
            'ancho_medio_const', 'ancho_medio_hetero', 'd_ancho_pct',
            'se_cluster_const', 'se_cluster_hetero', 'pct_infinito_hetero']
    print("\n" + "=" * 80)
    print("TABLA COMPARATIVA: sigma constante vs sigma(x), por metodo y periodo")
    print("cobertura y se en %; ancho en MWh; d_ancho_pct<0 = sigma(x) mas sharp")
    print("=" * 80)
    print(comp[cols].to_string(index=False))
    comp[cols].to_csv(FLAGSHIP / 'conformal_v3_hetero_comparacion.csv', index=False)

    # -------- CRPS por periodo (nivel modelo), const vs sigma(x) --------
    print("\n" + "-" * 80)
    print("CRPS del modelo base por periodo (MWh, menor es mejor): const vs sigma(x)")
    print("-" * 80)
    p_t, mu_t, y_t, f_t = test.p.values, test.mu.values, test.y_real.values, test.fecha.values
    sc, sh = h_const[h_const.fecha >= CAL_FIN].sig.values, h_het[h_het.fecha >= CAL_FIN].sig.values
    print(f"  {'periodo':10s} {'CRPS_const':>11s} {'CRPS_sigma(x)':>14s}")
    for nombre, ini, fin in cm.PERIODOS:
        m = (f_t >= np.datetime64(ini.date())) & (f_t < np.datetime64(fin.date()))
        if m.sum() == 0:
            continue
        rng = np.random.default_rng(11)
        cc = cm.crps(muestrear(p_t[m], mu_t[m], sc[m], rng), y_t[m], rng)
        rng = np.random.default_rng(11)
        ch = cm.crps(muestrear(p_t[m], mu_t[m], sh[m], rng), y_t[m], rng)
        print(f"  {nombre:10s} {cc:11.2f} {ch:14.2f}")

    # -------- trade-off por tercil de tamano (metodo estatico) --------
    print("\n" + "-" * 80)
    print("Trade-off por tercil de tamano de central (metodo ESTATICO PIT):")
    print("cobertura y ancho, sigma constante vs sigma(x). nominal 90%")
    print("-" * 80)
    meta = pd.read_csv(RELEASE / 'plants_metadata.csv')[['central_codigo', 'potencia_mw']]
    test = test.merge(meta, on='central_codigo', how='left')
    ter = pd.qcut(test.potencia_mw, 3, labels=['chica', 'media', 'grande'])
    Ue_c, Ue_h = U_c['1. Estatico PIT'], U_h['1. Estatico PIT']
    print(f"  {'tercil':8s} {'n':>7s} {'cob_const':>10s} {'cob_sig(x)':>11s} "
          f"{'anch_const':>11s} {'anch_sig(x)':>12s}")
    for t in ['chica', 'media', 'grande']:
        mm = (ter == t).values
        cob_c = 100 * (test.y_real.values[mm] <= Ue_c[mm]).mean()
        cob_h = 100 * (test.y_real.values[mm] <= Ue_h[mm]).mean()
        an_c = Ue_c[mm][np.isfinite(Ue_c[mm])].mean()
        an_h = Ue_h[mm][np.isfinite(Ue_h[mm])].mean()
        print(f"  {t:8s} {mm.sum():7,} {cob_c:9.1f}% {cob_h:10.1f}% {an_c:11.1f} {an_h:12.1f}")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
