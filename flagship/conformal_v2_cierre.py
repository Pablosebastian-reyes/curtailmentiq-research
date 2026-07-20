#!/usr/bin/env python3
"""
CIERRE DE LA TABLA COMPARATIVA (SINTETICO) - flagship CurtailmentIQ
===================================================================
Tarea 1 del diseno de Kerven Cea: resolver las tres decisiones que quedaron
abiertas en conformal_v2_hallazgos.txt, sobre el MISMO panel sintetico que v1
y v2 (importa conformal_prototype como modulo, misma semilla, sin tocarlo).

ADVERTENCIA: datos SINTETICOS. No son resultados reales, no se citan. El
experimento sobre datos reales esta en conformal_v3_real.py, con salidas
separadas y claramente rotuladas.

Decisiones que cierra:
  (a) Pesos de recencia (Barber et al. 2023) con POOL DESLIZANTE, en su mejor
      version, contra el pool fijo de v2 (cuyo colapso a 100% de intervalos
      infinitos se reporta como limitacion conocida del pool fijo).
  (b) Transporte + ACI con BANDA de incertidumbre por bootstrap sobre la
      ventana reciente, contra la version sin banda de v2, mirando el ancho
      de la transicion (test_ramp).
  (c) Weighted conformal por punto con score PIT como version definitiva del
      negative result (el fallo por las X, no por el score, ya se verifico
      tambien con score aditivo en el audit y en v2).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

FLAGSHIP = Path(__file__).resolve().parent
sys.path.insert(0, str(FLAGSHIP))
import conformal_prototype as cp   # noqa: E402  (generador sintetico, sin tocarlo)
import conformal_metodos as cm     # noqa: E402  (metodos compartidos con el real)

ALPHA = cp.ALPHA
RNG = np.random.default_rng(20260720)  # misma semilla de aleatorizacion del atomo que v2


def main():
    print("=" * 78)
    print("CIERRE TABLA COMPARATIVA - DATOS SINTETICOS (no son resultados reales)")
    print("Tarea 1 del diseno de Kerven. Panel: misma semilla que v1 y v2.")
    print("=" * 78)

    df = cp.generar_panel()
    tr = df[df.fecha < '2024-01-01']
    m = cp.Hurdle().fit(tr[cp.FEATS].values, tr.y.values)

    # Panel de evaluacion completo (calibracion + test), 2024-01 en adelante.
    ev = df[(df.fecha >= '2024-01-01') & (df.fecha < '2026-06-01')].copy().reset_index(drop=True)
    p_ev, mu_ev = m.params(ev[cp.FEATS].values)
    s_ev = cm.pit_score(p_ev, mu_ev, m.sigma, ev.y.values, RNG)  # score PIT de todo el panel
    ev['p'], ev['mu'], ev['s'] = p_ev, mu_ev, s_ev

    es_cal = ev.fecha < '2024-09-01'
    cal = ev[es_cal]
    test = ev[~es_cal].reset_index(drop=True)
    s_cal = cal.s.values
    fecha_cal = cal.fecha.values.astype('datetime64[D]').astype(float)
    print(f"\nPanel: {len(df):,} filas | sigma hurdle = {m.sigma:.3f} "
          f"| calib {len(cal):,} | test {len(test):,}")

    filas = []
    fechas_test = np.sort(test.fecha.unique())

    # =================================================================
    # (a) RECENCIA: pool fijo (v2, limitacion) vs pool deslizante (mejor)
    # =================================================================
    print("\n" + "-" * 78)
    print("(a) Pesos de recencia (Barber et al. 2023): pool fijo vs pool deslizante")
    print("-" * 78)
    dias_ev = ev.fecha.values.astype('datetime64[D]').astype(float)

    for hl in (30, 90, 180):
        decay = 0.5 ** (1.0 / hl)

        # pool FIJO: solo la calibracion (ene-ago 2024); el peso se desvanece
        # al alejarse en el futuro (colapso conocido de v2).
        q_fijo = {}
        for f in fechas_test:
            dias = f.astype('datetime64[D]').astype(float) - fecha_cal
            w = decay ** np.clip(dias, 0, None)
            q_fijo[f] = cm.q_ponderado(s_cal, w, 1.0, ALPHA)
        U_fijo = cm.pit_upper(test.p.values, test.mu.values, m.sigma,
                              np.array([q_fijo[f] for f in test.fecha.values]))
        filas += [dict(f, familia='a_recencia_fijo') for f in
                  cm.filas_por_periodo(f'a_recencia_fijo_hl{hl}', test.fecha.values,
                                       test.y.values, U_fijo)]

        # pool DESLIZANTE: en cada fecha t el pool son TODOS los scores con
        # fecha < t (calibracion mas test ya observado), decay-weighted. Nunca
        # colapsa: siempre hay scores recientes con peso ~1.
        q_desl = {}
        for f in fechas_test:
            t = f.astype('datetime64[D]').astype(float)
            pool = dias_ev < t
            w = decay ** np.clip(t - dias_ev[pool], 0, None)
            q_desl[f] = cm.q_ponderado(ev.s.values[pool], w, 1.0, ALPHA)
        U_desl = cm.pit_upper(test.p.values, test.mu.values, m.sigma,
                              np.array([q_desl[f] for f in test.fecha.values]))
        filas += [dict(f, familia='a_recencia_deslizante') for f in
                  cm.filas_por_periodo(f'a_recencia_desl_hl{hl}', test.fecha.values,
                                       test.y.values, U_desl)]
        print(f"  semivida {hl:3d}d: pool fijo y deslizante calculados")

    # =================================================================
    # (b) TRANSPORTE + ACI: sin banda (v2) vs con banda (nuevo)
    # =================================================================
    print("\n" + "-" * 78)
    print("(b) Transporte + ACI: sin banda vs con banda de bootstrap")
    print("-" * 78)
    for con_banda in (False, True):
        U_tr, diag_ramp = correr_transporte_aci(
            ev, test, s_cal, m.sigma, fechas_test, gamma=0.02,
            con_banda=con_banda, rng=RNG)
        etq = 'b_transporte_conbanda' if con_banda else 'b_transporte_sinbanda'
        filas += cm.filas_por_periodo(etq, test.fecha.values, test.y.values, U_tr)
        txt = (f"sd_cola={diag_ramp['sd_cola']:.3f} lam_cola={diag_ramp['lam_cola']:.2f}"
               if con_banda else "mapa puntual")
        print(f"  {'con banda ' if con_banda else 'sin banda '}: listo  ({txt})")

    # =================================================================
    # (c) WEIGHTED CONFORMAL POR PUNTO con score PIT (negative result final)
    # =================================================================
    print("\n" + "-" * 78)
    print("(c) Weighted conformal por punto, score PIT (negative result definitivo)")
    print("-" * 78)
    from sklearn.linear_model import LogisticRegression
    objetivos = [(nm, test[test.fecha.apply(cm.etiquetar_periodo) == nm])
                 for nm, _, _ in cm.PERIODOS]
    for nombre, d in objetivos:
        if len(d) == 0:
            continue
        Xc, Xt = cal[cp.FEATS].values, d[cp.FEATS].values
        w_cal = cp.pesos_shift(Xc, Xt)
        clf = LogisticRegression(max_iter=2000).fit(
            np.vstack([Xc, Xt]), np.r_[np.zeros(len(Xc)), np.ones(len(d))])
        ratio = len(Xc) / len(d)
        pr = np.clip(clf.predict_proba(Xt)[:, 1], 1e-4, 1 - 1e-4)
        w_test = (pr / (1 - pr)) * ratio
        q_pp = cm.q_ponderado(s_cal, w_cal, w_test, ALPHA)
        U_pp = cm.pit_upper(d.p.values, d.mu.values, m.sigma, q_pp)
        fila = cm.fila_metrica('c_weighted_pit', nombre, d.fecha.values, d.y.values, U_pp)
        ess = w_cal.sum() ** 2 / np.sum(w_cal ** 2)
        fila['ess_calib'] = round(ess, 0)
        filas.append(fila)
        print(f"  {nombre:10s} ESS={ess:6.0f}/{len(w_cal):,}  "
              f"%infinito={fila['pct_infinito']:5.1f}%  cobertura={fila['cobertura']:5.1f}%")
    print("  (el fallo por las X, no por el score, se verifico tambien con score")
    print("   aditivo en el audit y en conformal_v2; PIT queda como version definitiva)")

    # =================================================================
    # TABLA DE CIERRE
    # =================================================================
    for f in filas:
        f.pop('familia', None)
    tabla = cm.ordenar_tabla(filas)
    cols = ['metodo', 'periodo', 'cobertura', 'se_cluster', 'ancho_medio',
            'pct_infinito', 'n_dias', 'n']
    if 'ess_calib' in tabla.columns:
        cols.append('ess_calib')
    print("\n" + "=" * 78)
    print("TABLA DE CIERRE (SINTETICO): metodo x periodo")
    print("cobertura y se_cluster en %; ancho_medio en MWh sobre intervalos finitos")
    print("=" * 78)
    print(tabla[cols].to_string(index=False))
    tabla[cols].to_csv(FLAGSHIP / 'conformal_v2_cierre_tabla.csv', index=False)
    print(f"\nTabla guardada en {FLAGSHIP / 'conformal_v2_cierre_tabla.csv'}")
    print("=" * 78)


def correr_transporte_aci(ev, test, s_cal, sigma, fechas_test, gamma,
                          con_banda, rng, refresco_dias=7, ventana_dias=60):
    """Transporte de scores (calibracion vieja -> ventana reciente) mas ACI
    diario sobre el pool transportado. Devuelve (U por fila de test, diag del
    ultimo refresco dentro de test_ramp)."""
    dias_ev = ev.fecha.values.astype('datetime64[D]')
    U = np.empty(len(test))
    alpha_t = ALPHA
    pool = np.sort(s_cal)
    prox = pd.Timestamp('2024-09-01')
    diag_ramp = dict(sd_cola=np.nan, lam_cola=np.nan)

    for f in fechas_test:
        f_ts = pd.Timestamp(f)
        if f_ts >= prox:
            ini = np.datetime64((f_ts - pd.Timedelta(days=ventana_dias)).date())
            fin = np.datetime64(f_ts.date())
            reciente = (dias_ev >= ini) & (dias_ev < fin)
            s_new = ev.s.values[reciente]
            if len(s_new) >= 100:
                if con_banda:
                    T, diag = cm.mapa_transporte_banda(s_cal, s_new, rng)
                    if pd.Timestamp('2024-10-01') <= f_ts < pd.Timestamp('2025-01-01'):
                        diag_ramp = diag
                else:
                    T = cm.mapa_transporte(s_cal, s_new)
                pool = np.sort(T(s_cal))
            prox = f_ts + pd.Timedelta(days=refresco_dias)

        mask = test.fecha.values == f
        q_t = cm.q_desde_pool(pool, alpha_t)
        U_t = cm.pit_upper(test.p.values[mask], test.mu.values[mask], sigma, q_t)
        U[mask] = U_t
        err_t = 1 - (test.y.values[mask] <= U_t).mean()
        alpha_t = np.clip(alpha_t + gamma * (ALPHA - err_t), -1.0, 2.0)
    return U, diag_ramp


if __name__ == '__main__':
    main()
