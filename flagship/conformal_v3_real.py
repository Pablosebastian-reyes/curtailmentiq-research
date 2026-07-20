#!/usr/bin/env python3
"""
EXPERIMENTO CENTRAL: capa de incertidumbre sobre PREDICCIONES REALES
====================================================================
Tarea 2 del diseno de Kerven Cea: enchufar la maquinaria conformal a las
predicciones REALES del modelo base (hurdle sobre el dataset congelado v1.0),
en vez del panel sintetico.

DATOS REALES, no sinteticos. Insumo: flagship/predicciones/pred_hurdle.csv
(104,420 filas, 2024-01 a 2026-05, columnas p_occ, mu_log, sigma, y_real),
generado por entrenar_baselines.py con el modelo base entrenado SOLO hasta
2023-12-31. Los hiperparametros del modelo base vienen fijos de esa etapa,
aqui no se tocan.

Dato clave del real: sigma del hurdle = 1.70 (out-of-fold), el doble del 0.85
sintetico. Los intervalos reales seran mas anchos y el problema de sharpness
mas severo. Es el fenomeno real, se reporta, no se suaviza.

Metodos (los que quedaron mejor en sintetico):
  conformal estatico PIT (referencia), ventana deslizante 60d con score PIT,
  ACI sobre score PIT, y transporte + ACI con banda de incertidumbre.

Usa el modulo compartido conformal_metodos (codigo identico al del cierre
sintetico): asi lo unico que cambia entre sintetico y real son los datos.

Embargo de horizonte (7 dias): los metodos online respetan el desfase de un
pronostico a 7 dias. Las ventanas de calibracion terminan 7 dias antes del
target y la retroalimentacion de alpha del ACI se retrasa 7 pasos. Ver
EMBARGO_DIAS y la entrada de DECISIONS.md del 2026-07-20.
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
# Embargo de horizonte: el modelo base pronostica a 7 dias, asi que el outcome
# del target t solo se conoce en t, pero el pronostico se emitio en t-7 con
# datos hasta t-7. Para no filtrar el futuro en el backtesting, toda ventana de
# calibracion online termina 7 dias antes del target, y la retroalimentacion de
# alpha en el ACI se retrasa 7 pasos. Decision de alcance 2026-07-20.
EMBARGO_DIAS = 7
RNG = np.random.default_rng(20260720)  # misma semilla de aleatorizacion que el cierre sintetico
CSV = FLAGSHIP / 'predicciones' / 'pred_hurdle.csv'

# Cortes sobre datos reales (documentados). Las predicciones reales existen
# desde 2024-01-01 (el modelo base predice fuera de muestra desde ahi), asi
# que la calibracion debe caer dentro de 2024-01 a 2024-08 para dejar
# test_pre como regimen estable previo a la rampa BESS.
CAL_INI, CAL_FIN = pd.Timestamp('2024-01-01'), pd.Timestamp('2024-09-01')


def cargar():
    h = pd.read_csv(CSV, parse_dates=['fecha'])
    h = h.sort_values(['fecha', 'central_codigo']).reset_index(drop=True)
    h['p'] = np.clip(h.p_occ.values, 1e-6, 1 - 1e-6)
    h['mu'] = h.mu_log.values
    return h


def main():
    print("=" * 78)
    print("EXPERIMENTO CENTRAL - PREDICCIONES REALES (dataset v1.0)")
    print("Diseno: Kerven Cea. Insumo real: pred_hurdle.csv. NO es sintetico.")
    print("=" * 78)

    h = cargar()
    sigma = float(h.sigma.iloc[0])
    assert h.sigma.nunique() == 1, "sigma deberia ser constante (out-of-fold)"
    s_all = cm.pit_score(h.p.values, h.mu.values, sigma, h.y_real.values, RNG)
    h['s'] = s_all

    es_cal = (h.fecha >= CAL_INI) & (h.fecha < CAL_FIN)
    cal = h[es_cal]
    test = h[h.fecha >= CAL_FIN].reset_index(drop=True)
    s_cal = cal.s.values

    print(f"\nsigma hurdle REAL = {sigma:.3f}  (sintetico era 0.839: el doble)")
    print(f"Cortes: calibracion [{CAL_INI.date()}, {CAL_FIN.date()})  "
          f"{len(cal):,} filas, {cal.fecha.dt.normalize().nunique()} dias")
    for nombre, ini, fin in cm.PERIODOS:
        d = test[(test.fecha >= ini) & (test.fecha < fin)]
        print(f"  {nombre:10s} [{ini.date()}, {fin.date()})  {len(d):7,} filas  "
              f"{d.fecha.dt.normalize().nunique():4d} dias")

    filas = []
    fechas_test = np.sort(test.fecha.unique())
    p_t, mu_t, y_t, f_t = test.p.values, test.mu.values, test.y_real.values, test.fecha.values

    # =================================================================
    # 1. CONFORMAL ESTATICO PIT (referencia)
    # =================================================================
    print("\n" + "-" * 78)
    print("1. Conformal estatico PIT (referencia)")
    print("-" * 78)
    qhat = cm.q_conformal(s_cal, ALPHA)
    U_est = cm.pit_upper(p_t, mu_t, sigma, qhat)
    filas += cm.filas_por_periodo('1_estatico_pit', f_t, y_t, U_est)
    print(f"qhat PIT = {qhat:.4f}")

    # =================================================================
    # 2. VENTANA DESLIZANTE 60d, refresco 7d, score PIT
    # =================================================================
    print("\n" + "-" * 78)
    print("2. Ventana deslizante 60d / refresco 7d, score PIT")
    print("-" * 78)
    U_vent = np.full(len(test), np.nan)
    refrescos = pd.date_range('2024-09-01', '2026-05-31', freq='7D')
    fechas_h = h.fecha.values
    for t0 in refrescos:
        # embargo de 7 dias: la ventana de 60 dias termina en t0-7, no en t0
        ini = np.datetime64((t0 - pd.Timedelta(days=60 + EMBARGO_DIAS)).date())
        fin = np.datetime64((t0 - pd.Timedelta(days=EMBARGO_DIAS)).date())
        win = (fechas_h >= ini) & (fechas_h < fin)
        obj = (f_t >= np.datetime64(t0.date())) & (f_t < np.datetime64((t0 + pd.Timedelta(days=7)).date()))
        if obj.sum() == 0 or win.sum() < 100:
            continue
        q_w = cm.q_conformal(h.s.values[win], ALPHA)
        U_vent[obj] = cm.pit_upper(p_t[obj], mu_t[obj], sigma, q_w)
    filas += cm.filas_por_periodo('2_ventana60d_pit', f_t, y_t, U_vent)
    print(f"  listo ({len(refrescos)} refrescos)")

    # =================================================================
    # 3. ACI (Gibbs & Candes 2021) sobre score PIT, pool estatico
    # =================================================================
    print("\n" + "-" * 78)
    print("3. ACI sobre score PIT")
    print("-" * 78)
    for gamma in (0.02, 0.05):
        U_aci, a_fin = correr_aci(np.sort(s_cal), test, p_t, mu_t, y_t, f_t,
                                  fechas_test, sigma, gamma)
        filas += cm.filas_por_periodo(f'3_aci_pit_g{gstr(gamma)}', f_t, y_t, U_aci)
        print(f"  gamma={gamma:.3f}: alpha_t final={a_fin:.4f}")
        if abs(gamma - 0.05) < 1e-9:
            serie_aci = U_aci.copy()

    # =================================================================
    # 4. TRANSPORTE + ACI con BANDA de incertidumbre
    # =================================================================
    print("\n" + "-" * 78)
    print("4. Transporte de scores + ACI, con banda de bootstrap")
    print("-" * 78)
    for gamma in (0.02, 0.05):
        U_tr, a_fin, diag = correr_transporte_aci(h, test, s_cal, p_t, mu_t, y_t, f_t,
                                                  fechas_test, sigma, gamma, RNG)
        filas += cm.filas_por_periodo(f'4_transporte_banda_g{gstr(gamma)}', f_t, y_t, U_tr)
        print(f"  gamma={gamma:.3f}: alpha_t final={a_fin:.4f}  "
              f"(banda en ramp: sd_cola={diag['sd_cola']:.3f} lam_cola={diag['lam_cola']:.2f})")
        if abs(gamma - 0.05) < 1e-9:
            serie_tr = U_tr.copy()

    # =================================================================
    # TABLA UNICA (REAL)
    # =================================================================
    tabla = cm.ordenar_tabla(filas)
    cols = ['metodo', 'periodo', 'cobertura', 'se_cluster', 'ancho_medio',
            'pct_infinito', 'n_dias', 'n']
    print("\n" + "=" * 78)
    print("TABLA UNICA (DATOS REALES): metodo x periodo")
    print("cobertura y se_cluster en %; ancho_medio en MWh sobre intervalos finitos;")
    print("se_cluster = error estandar de la cobertura diaria, CLUSTERIZADO POR FECHA")
    print("=" * 78)
    print(tabla[cols].to_string(index=False))
    tabla[cols].to_csv(FLAGSHIP / 'conformal_v3_tabla.csv', index=False)

    # =================================================================
    # CRPS del modelo base REAL por periodo (heavy tail por sigma=1.70)
    # =================================================================
    print("\n" + "-" * 78)
    print("CRPS del modelo base REAL por periodo (propiedad del hurdle, no del")
    print("metodo conformal). Con sigma=1.70 la predictiva es de cola muy pesada:")
    print("el CRPS es grande y sensible a la cola, se reporta tal cual.")
    print("-" * 78)
    rng_crps = np.random.default_rng(11)
    for nombre, ini, fin in cm.PERIODOS:
        mask = (f_t >= np.datetime64(ini.date())) & (f_t < np.datetime64(fin.date()))
        if mask.sum() == 0:
            continue
        muestras = cm.sample_hurdle(p_t[mask], mu_t[mask], sigma, rng_crps, n=300)
        c = cm.crps(muestras, y_t[mask], rng_crps)
        print(f"  {nombre:10s} CRPS = {c:8.2f} MWh  (n={int(mask.sum()):,})")

    # =================================================================
    # FIGURA: cobertura rodante 90d (REAL)
    # =================================================================
    print("\n" + "-" * 78)
    print("Figura: cobertura rodante 90d (datos reales)")
    print("-" * 78)
    graficar(f_t, y_t, {
        '1. Estatico PIT (referencia)': U_est,
        '2. Ventana 60d PIT': U_vent,
        '3. ACI PIT (gamma=0.05)': serie_aci,
        '4. Transporte + ACI banda (gamma=0.05)': serie_tr,
    })
    print("\n" + "=" * 78)


def gstr(g):
    return str(g).replace('0.', '')


def correr_aci(pool_ord, test, p_t, mu_t, y_t, f_t, fechas_test, sigma, gamma):
    alpha_t = ALPHA
    U = np.empty(len(test))
    # embargo: el error del target f solo esta disponible 7 pasos despues, asi
    # que la actualizacion de alpha se retrasa EMBARGO_DIAS pasos.
    pendientes = deque()
    for f in fechas_test:
        mask = f_t == f
        q_t = cm.q_desde_pool(pool_ord, alpha_t)
        U_t = cm.pit_upper(p_t[mask], mu_t[mask], sigma, q_t)
        U[mask] = U_t
        err_t = 1 - (y_t[mask] <= U_t).mean()
        pendientes.append(err_t)
        if len(pendientes) > EMBARGO_DIAS:
            err_fb = pendientes.popleft()
            alpha_t = np.clip(alpha_t + gamma * (ALPHA - err_fb), -1.0, 2.0)
    return U, alpha_t


def correr_transporte_aci(h, test, s_cal, p_t, mu_t, y_t, f_t, fechas_test,
                          sigma, gamma, rng, refresco_dias=7, ventana_dias=60):
    fechas_h = h.fecha.values
    alpha_t = ALPHA
    U = np.empty(len(test))
    pool = np.sort(s_cal)
    prox = pd.Timestamp('2024-09-01')
    diag_ramp = dict(sd_cola=np.nan, lam_cola=np.nan)
    # embargo: la retroalimentacion de alpha se retrasa EMBARGO_DIAS pasos.
    pendientes = deque()
    for f in fechas_test:
        f_ts = pd.Timestamp(f)
        if f_ts >= prox:
            # embargo: la ventana reciente termina en f-7, no en f
            ini = np.datetime64((f_ts - pd.Timedelta(days=ventana_dias + EMBARGO_DIAS)).date())
            fin = np.datetime64((f_ts - pd.Timedelta(days=EMBARGO_DIAS)).date())
            reciente = (fechas_h >= ini) & (fechas_h < fin)
            s_new = h.s.values[reciente]
            if len(s_new) >= 100:
                T, diag = cm.mapa_transporte_banda(s_cal, s_new, rng)
                if pd.Timestamp('2024-10-01') <= f_ts < pd.Timestamp('2025-01-01'):
                    diag_ramp = diag
                pool = np.sort(T(s_cal))
            prox = f_ts + pd.Timedelta(days=refresco_dias)
        mask = f_t == f
        q_t = cm.q_desde_pool(pool, alpha_t)
        U_t = cm.pit_upper(p_t[mask], mu_t[mask], sigma, q_t)
        U[mask] = U_t
        err_t = 1 - (y_t[mask] <= U_t).mean()
        pendientes.append(err_t)
        if len(pendientes) > EMBARGO_DIAS:
            err_fb = pendientes.popleft()
            alpha_t = np.clip(alpha_t + gamma * (ALPHA - err_fb), -1.0, 2.0)
    return U, alpha_t, diag_ramp


def graficar(fecha, y, series_dict, ventana=90):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fechas = pd.to_datetime(fecha)
    base = pd.DataFrame({'fecha': fechas, 'y': y})
    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    colores = ['#4c72b0', '#55a868', '#c44e52', '#dd8452']
    idx_full = pd.date_range(fechas.min(), fechas.max(), freq='D')
    for (nombre, U), color in zip(series_dict.items(), colores):
        d = base.copy()
        d['cubierto'] = (y <= U).astype(float)
        por_dia = d.groupby('fecha').cubierto.mean().reindex(idx_full)
        rodante = 100 * por_dia.rolling(ventana, min_periods=int(ventana * 0.6)).mean()
        ax.plot(rodante.index, rodante.values, label=nombre, color=color, linewidth=1.6)

    ax.axhline(90, color='#666666', linewidth=1, linestyle=':', zorder=0)
    ax.axvline(pd.Timestamp('2024-10-01'), color='#999999', linewidth=1, linestyle='--', zorder=0)
    ax.text(pd.Timestamp('2024-10-10'), 61, 'inicio rampa BESS', fontsize=8,
            color='#999999', va='bottom', ha='left')
    ax.set_ylim(58, 101)
    ax.set_xlabel('Fecha')
    ax.set_ylabel('Cobertura rodante 90 dias (%)')
    ax.set_title('Cobertura rodante sobre datos REALES bajo el quiebre BESS (sigma hurdle = 1.70)')
    ax.legend(loc='lower left', fontsize=8, framealpha=0.9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    fig.savefig(FLAGSHIP / 'conformal_v3_cobertura_rodante.pdf')
    fig.savefig(FLAGSHIP / 'conformal_v3_cobertura_rodante.png')
    plt.close(fig)
    print(f"  guardado conformal_v3_cobertura_rodante.pdf y .png")


if __name__ == '__main__':
    main()
