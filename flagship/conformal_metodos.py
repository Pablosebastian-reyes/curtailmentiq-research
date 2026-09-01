#!/usr/bin/env python3
"""
Libreria compartida de metodos conformal (capa de incertidumbre).
=================================================================
Diseno metodologico: Kerven Cea. Este modulo NO contiene datos: solo las
funciones de score, inversion, cuantiles conformal, transporte de scores y
metricas. Lo importan tanto el cierre sobre datos sinteticos
(conformal_v2_cierre.py) como el experimento sobre datos reales
(conformal_v3_real.py), de modo que ambos corran con codigo identico. Esa
identidad de implementacion es lo que hace comparable el paso de sintetico a
real: cualquier diferencia en los resultados viene de los datos, no del
metodo.

Todas las funciones trabajan con arrays (p, mu, sigma) del hurdle, no con un
objeto de modelo, para ser agnosticas a la fuente (Hurdle sintetico o columnas
p_occ, mu_log, sigma del CSV real).

Convenciones:
  score PIT s = F_x(y) en [0, 1], con randomizacion del atomo en y=0.
  intervalo superior [0, U(x)] a nivel 1-alpha.
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

# Fronteras de periodo compartidas por el experimento sintetico y el real.
# Son identicas por diseno: test_pre regimen estable (septiembre 2024),
# test_transition la ventana de transicion (octubre a diciembre 2024), luego por semestre.
PERIODOS = [
    ('test_pre',  pd.Timestamp('2024-09-01'), pd.Timestamp('2024-10-01')),
    ('test_transition', pd.Timestamp('2024-10-01'), pd.Timestamp('2025-01-01')),
    ('2025-S1',   pd.Timestamp('2025-01-01'), pd.Timestamp('2025-07-01')),
    ('2025-S2',   pd.Timestamp('2025-07-01'), pd.Timestamp('2026-01-01')),
    ('2026-S1',   pd.Timestamp('2026-01-01'), pd.Timestamp('2026-06-01')),
]


# =====================================================================
# SCORE PIT Y SU INVERSION
# =====================================================================
def pit_score(p, mu, sigma, y, rng):
    """s = F_x(y): (1-p)+p*Phi((log y - mu)/sigma) si y>0; (1-p)*V si y=0,
    V~U(0,1). La randomizacion del atomo (Smith 1985) hace s ~ Uniforme(0,1)
    bajo la ley verdadera, pese al salto de F en 0."""
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    y = np.asarray(y, float)
    yy = np.maximum(y, 1.0)  # evita log(0); irrelevante donde y=0 (np.where)
    z = (np.log(yy) - mu) / sigma
    Fpos = (1 - p) + p * norm.cdf(z)
    return np.where(y > 0, Fpos, (1 - p) * rng.random(len(y)))


def pit_upper(p, mu, sigma, q):
    """Invierte F_x(U) = q. Formula unificada por clip: U = 0 si q <= 1-p
    (el clip lleva el argumento a 0 y Phi^-1(0) = -inf da exp(-inf) = 0);
    U = inf si q >= 1 (Phi^-1(1) = +inf). q escalar o array del largo de p."""
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    thresh = 1 - p
    arg = np.clip((np.asarray(q, float) - thresh) / p, 0.0, 1.0)
    with np.errstate(divide='ignore'):
        return np.exp(mu + sigma * norm.ppf(arg))


# =====================================================================
# CUANTILES CONFORMAL
# =====================================================================
def q_conformal(scores, alpha):
    """Cuantil conformal estandar con correccion de muestra finita."""
    n = len(scores)
    k = int(np.ceil((n + 1) * (1 - alpha)))
    if k > n:
        return np.inf
    return np.sort(scores)[k - 1]


def q_ponderado(scores, w, w_test, alpha):
    """Cuantil conformal ponderado. w_test escalar (pesos fijos de recencia,
    Barber et al. 2023) o array por punto de test (weighted conformal de
    Tibshirani et al. 2019). Devuelve escalar si w_test es escalar, array si
    w_test es array."""
    w = np.asarray(w, float)
    orden = np.argsort(scores)
    s_sorted = np.asarray(scores)[orden]
    cumw = np.cumsum(w[orden])
    W = w[orden].sum()
    wt = np.atleast_1d(np.asarray(w_test, dtype=float))
    umbral = (1 - alpha) * (W + wt)
    idx = np.searchsorted(cumw, umbral)
    q = np.where(idx >= len(s_sorted), np.inf,
                 s_sorted[np.minimum(idx, len(s_sorted) - 1)])
    return q if np.ndim(w_test) > 0 else float(q[0])


def q_desde_pool(pool_ordenado, alpha):
    """Cuantil conformal desde un pool ya ordenado (para el bucle ACI)."""
    if alpha <= 0:
        return np.inf
    if alpha >= 1:
        return -np.inf
    n = len(pool_ordenado)
    k = int(np.ceil((n + 1) * (1 - alpha)))
    return pool_ordenado[k - 1] if k <= n else np.inf


# =====================================================================
# TRANSPORTE DE SCORES (mapa monotono 1D = increasing rearrangement)
# =====================================================================
def mapa_transporte(s_old, s_new, n_grid=100):
    """T = F_new^{-1} o F_old, interpolacion monotona entre cuantiles
    empiricos. Version puntual (sin banda), como en v2."""
    g = min(n_grid, max(20, len(s_new) // 2))
    niveles = np.linspace(0, 1, g)
    q_old = np.quantile(s_old, niveles)
    q_new = np.quantile(s_new, niveles)

    def T(s):
        nivel = np.interp(s, q_old, niveles)
        return np.interp(nivel, niveles, q_new)
    return T


def mapa_transporte_banda(s_old, s_new, rng, B=150, n_grid=100, tau=0.05):
    """Transporte con banda de incertidumbre por bootstrap sobre la ventana
    reciente (s_new). Ataca el ruido de la cola superior durante la
    transicion: donde el bootstrap del mapa es inestable (sd alta en unidades
    PIT), el mapa se encoge (shrink) hacia la identidad, es decir hacia el
    cuantil viejo estable, en vez de extrapolar un cuantil nuevo ruidoso.

    lambda(nivel) = 1 / (1 + (sd_bootstrap / tau)^2): vale ~1 (transporte
    pleno) donde el mapa es estable, ~0 (identidad) donde es ruidoso. tau es
    una escala de regularizacion fija en unidades PIT, NO ajustada contra el
    test. Devuelve (T, diagnostico)."""
    g = min(n_grid, max(20, len(s_new) // 2))
    niveles = np.linspace(0, 1, g)
    q_old = np.quantile(s_old, niveles)

    m = len(s_new)
    Tb = np.empty((B, g))
    for b in range(B):
        muestra = s_new[rng.integers(0, m, m)]
        Tb[b] = np.quantile(muestra, niveles)
    q_new_bag = Tb.mean(0)          # bagging: reduce la varianza del mapa
    sd = Tb.std(0)                  # ancho de la banda por nivel (unidades PIT)
    lam = 1.0 / (1.0 + (sd / tau) ** 2)
    q_reg = (1 - lam) * q_old + lam * q_new_bag   # shrink hacia la identidad
    q_reg = np.clip(np.maximum.accumulate(q_reg), 0.0, 1.0)  # fuerza monotonia

    def T(s):
        nivel = np.interp(s, q_old, niveles)
        return np.interp(nivel, niveles, q_reg)

    cola = niveles >= 0.9
    diag = dict(sd_media=float(sd.mean()), sd_cola=float(sd[cola].mean()),
                lam_cola=float(lam[cola].mean()))
    return T, diag


# =====================================================================
# METRICAS
# =====================================================================
def sample_hurdle(p, mu, sigma, rng, n=300):
    """Muestras de la mezcla (1-p)*delta_0 + p*LogNormal(mu, sigma)."""
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    mu = np.asarray(mu, float)
    occ = rng.random((len(p), n)) < p[:, None]
    mag = np.exp(mu[:, None] + sigma * rng.standard_normal((len(p), n)))
    return np.where(occ, mag, 0.0)


def crps(muestras, y, rng):
    """CRPS por muestreo: E|X-y| - 0.5*E|X-X'|. rng explicito (reproducible)."""
    a = np.abs(muestras - np.asarray(y)[:, None]).mean(1)
    idx = rng.permutation(muestras.shape[1])
    b = 0.5 * np.abs(muestras - muestras[:, idx]).mean(1)
    return float((a - b).mean())


def cobertura_clusterizada(fecha, cubierto):
    """Cobertura con error estandar CLUSTERIZADO POR FECHA: las centrales
    comparten el estado sistemico diario, asi que el n efectivo es el de dias,
    no el de filas. Promedia la cobertura de cada dia y calcula el se entre
    dias."""
    por_dia = pd.Series(np.asarray(cubierto, float)).groupby(
        pd.Series(np.asarray(fecha)).values).mean()
    cov = por_dia.mean()
    se = por_dia.std(ddof=1) / np.sqrt(len(por_dia)) if len(por_dia) > 1 else np.nan
    return cov, se, len(por_dia)


def etiquetar_periodo(fecha):
    for nombre, ini, fin in PERIODOS:
        if ini <= fecha < fin:
            return nombre
    return None


def fila_metrica(metodo, periodo, fecha, y, U):
    cov, se, ndias = cobertura_clusterizada(fecha, np.asarray(y) <= U)
    finito = np.isfinite(U)
    return dict(metodo=metodo, periodo=periodo, cobertura=round(100 * cov, 1),
                se_cluster=round(100 * se, 2) if pd.notna(se) else np.nan,
                ancho_medio=round(float(U[finito].mean()), 1) if finito.any() else np.nan,
                pct_infinito=round(100 * (~finito).mean(), 1),
                n_dias=ndias, n=len(y))


def filas_por_periodo(metodo, fecha, y, U):
    fecha = pd.to_datetime(np.asarray(fecha))
    per = pd.Series(fecha).apply(etiquetar_periodo).values
    filas = []
    for nombre, _, _ in PERIODOS:
        m = per == nombre
        if m.sum() > 0:
            filas.append(fila_metrica(metodo, nombre, np.asarray(fecha)[m],
                                      np.asarray(y)[m], U[m]))
    return filas


def ordenar_tabla(filas, extra_periodos=()):
    tabla = pd.DataFrame(filas)
    orden = {n: i for i, (n, _, _) in enumerate(PERIODOS)}
    for j, nm in enumerate(extra_periodos):
        orden[nm] = len(PERIODOS) + j
    tabla['_o'] = tabla.periodo.map(orden)
    return tabla.sort_values(['metodo', '_o']).drop(columns='_o')
