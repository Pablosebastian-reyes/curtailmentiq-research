#!/usr/bin/env python3
"""
Libreria compartida de la REVISION MAYOR (SEGAN-D-26-03850).
============================================================
Generaliza la maquinaria conformal de `flagship/conformal_metodos.py` para que
no dependa de la forma parametrica del hurdle. El modulo original trabaja con
(p, mu, sigma) del hurdle lognormal; aqui se introduce una interfaz de
predictiva con solo dos operaciones:

    cdf(y)     -> el score PIT s = F_x(y), con el atomo en y=0 randomizado
    inv(q)     -> el limite superior U(x) = F_x^{-1}(q)

Cualquier modelo base que sepa hacer esas dos cosas entra a la capa conformal
sin cambiar una linea de la capa. Eso es exactamente lo que pide el comentario
R1.1: separar el aporte de la capa de calibracion del aporte del hurdle.

`conformal_metodos.py` NO se modifica en su algebra: este modulo lo importa y
reusa `q_conformal`, `q_desde_pool`, `mapa_transporte_banda`, etc. La unica
diferencia en las funciones que se reimplementan aqui es que reciben un objeto
predictiva en vez de arrays (p, mu, sigma).

NOMENCLATURA (Fase 7): las ventanas de evaluacion se nombran por su propiedad
medible, no por ningun despliegue tecnologico. `test_ramp` de la version
enviada pasa a `test_transition`.
"""
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import norm

FLAGSHIP = Path(__file__).resolve().parent.parent
REPO = FLAGSHIP.parent
sys.path.insert(0, str(FLAGSHIP))
import conformal_metodos as cm   # noqa: E402

# --------------------------------------------------------------------------
# Constantes del protocolo (identicas a la corrida oficial)
# --------------------------------------------------------------------------
ALPHA = 0.10
EMBARGO_DIAS = 7
SEED_CONFORMAL = 20260720      # aleatorizacion del atomo PIT y bootstrap
SEED_BASE = 42                 # entrenamiento de modelos base
SEED_CRPS = 11                 # muestreo del CRPS
SEED_BOOTSTRAP = 20260901      # bootstrap de diferencias entre metodos
CAL_INI = pd.Timestamp('2024-01-01')
CAL_FIN = pd.Timestamp('2024-09-01')

# Ventanas de evaluacion. Mismas fronteras que la version enviada; solo cambia
# el nombre de la segunda (Fase 7, comentario R2.2).
PERIODOS = [
    ('test_pre',        pd.Timestamp('2024-09-01'), pd.Timestamp('2024-10-01')),
    ('test_transition', pd.Timestamp('2024-10-01'), pd.Timestamp('2025-01-01')),
    ('2025-S1',         pd.Timestamp('2025-01-01'), pd.Timestamp('2025-07-01')),
    ('2025-S2',         pd.Timestamp('2025-07-01'), pd.Timestamp('2026-01-01')),
    ('2026-S1',         pd.Timestamp('2026-01-01'), pd.Timestamp('2026-06-01')),
]
NOMBRE_ANTIGUO = {'test_ramp': 'test_transition'}


# ==========================================================================
# INTERFAZ DE PREDICTIVA
# ==========================================================================
class PredictivaHurdle:
    """Mezcla (1-p) delta_0 + p LogNormal(mu, sigma). Es la predictiva del
    modelo base oficial. Reproduce exactamente cm.pit_score y cm.pit_upper."""

    nombre = 'hurdle'

    def __init__(self, p, mu, sigma):
        self.p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
        self.mu = np.asarray(mu, float)
        self.sigma = float(sigma) if np.ndim(sigma) == 0 else np.asarray(sigma, float)

    def __len__(self):
        return len(self.p)

    def sub(self, mask):
        s = self.sigma if np.ndim(self.sigma) == 0 else self.sigma[mask]
        return PredictivaHurdle(self.p[mask], self.mu[mask], s)

    def cdf(self, y, rng):
        return cm.pit_score(self.p, self.mu, self.sigma, y, rng)

    def inv(self, q):
        return cm.pit_upper(self.p, self.mu, self.sigma, q)

    def muestrear(self, rng, n=300):
        sig = self.sigma if np.ndim(self.sigma) == 0 else self.sigma[:, None]
        occ = rng.random((len(self.p), n)) < self.p[:, None]
        mag = np.exp(self.mu[:, None] + sig * rng.standard_normal((len(self.p), n)))
        return np.where(occ, mag, 0.0)


class PredictivaCuantilica:
    """Predictiva definida por una rejilla densa de cuantiles empiricos por fila.

    Q tiene forma (n, K): Q[i, k] = F_i^{-1}(tau_k), reordenada de forma no
    decreciente por fila (rearrangement) y recortada a >= 0. La CDF es la
    inversa generalizada interpolada linealmente entre nodos.

    El atomo en cero NO se impone: es el que produce el propio modelo,
    F_i(0) = max{tau_k : Q[i,k] = 0}, cero si ningun cuantil se anula.

    Convenios de borde, declarados porque afectan a las metricas:
      - y por encima del cuantil mas alto estimado (tau = 0.999) recibe score
        s = 1. La predictiva no expresa nada mas alla de ese nodo y extrapolar
        una cola seria inventarla.
      - q por encima de tau_max devuelve U = +infinito, y se cuenta como
        intervalo infinito con el mismo criterio que el resto del paper.
    La rejilla interna aumentada anade siempre un nodo (x=0, tau=0), de modo
    que el tramo continuo arranca en el origen tambien cuando no hay atomo.
    """

    nombre = 'qgbm'

    def __init__(self, Q, taus, tol_cero=1e-9):
        Q = np.maximum(0.0, np.sort(np.asarray(Q, float), axis=1))
        self.Q = Q
        self.taus = np.asarray(taus, float)
        self.tol_cero = tol_cero
        n = Q.shape[0]
        # rejilla aumentada: nodo en el origen + los K cuantiles
        self.Xa = np.concatenate([np.zeros((n, 1)), Q], axis=1)      # (n, K+1)
        self.Ta = np.concatenate([[0.0], self.taus])                 # (K+1,) comun
        kz = (Q <= tol_cero).sum(axis=1)
        self._F0 = np.where(kz == 0, 0.0,
                            self.taus[np.clip(kz - 1, 0, len(self.taus) - 1)])

    def __len__(self):
        return self.Q.shape[0]

    def sub(self, mask):
        return PredictivaCuantilica(self.Q[mask], self.taus, self.tol_cero)

    def F0(self):
        return self._F0

    def cdf(self, y, rng):
        y = np.asarray(y, float)
        n, K1 = self.Xa.shape
        # indice del ultimo nodo con x <= y, por fila
        idx = (self.Xa <= y[:, None]).sum(axis=1) - 1
        idx = np.clip(idx, 0, K1 - 1)
        fuera = idx >= K1 - 1                      # y por encima del cuantil top
        j = np.minimum(idx, K1 - 2)
        x0 = np.take_along_axis(self.Xa, j[:, None], 1).ravel()
        x1 = np.take_along_axis(self.Xa, (j + 1)[:, None], 1).ravel()
        t0, t1 = self.Ta[j], self.Ta[j + 1]
        dx = x1 - x0
        frac = np.where(dx > 0, (y - x0) / np.where(dx > 0, dx, 1.0), 1.0)
        s_pos = np.clip(t0 + np.clip(frac, 0.0, 1.0) * (t1 - t0), 0.0, 1.0)
        s_pos = np.where(fuera, 1.0, s_pos)
        s_cero = self._F0 * rng.random(n)          # atomo randomizado (Smith 1985)
        return np.where(y > 0, s_pos, s_cero)

    def inv(self, q):
        n, K1 = self.Xa.shape
        qa = np.broadcast_to(np.asarray(q, float), (n,)).astype(float)
        j = np.clip(np.searchsorted(self.Ta, qa, side='right') - 1, 0, K1 - 2)
        x0 = np.take_along_axis(self.Xa, j[:, None], 1).ravel()
        x1 = np.take_along_axis(self.Xa, (j + 1)[:, None], 1).ravel()
        t0, t1 = self.Ta[j], self.Ta[j + 1]
        dt = t1 - t0
        frac = np.where(dt > 0, (qa - t0) / np.where(dt > 0, dt, 1.0), 0.0)
        U = x0 + np.clip(frac, 0.0, 1.0) * (x1 - x0)
        U = np.where(qa <= self._F0, 0.0, U)
        return np.where(qa > self.taus[-1], np.inf, U)

    def muestrear(self, rng, n=300):
        """Muestreo por transformada inversa sobre la rejilla, vectorizado."""
        u = rng.random((len(self), n))
        K1 = self.Xa.shape[1]
        j = np.clip(np.searchsorted(self.Ta, u.ravel(), side='right') - 1,
                    0, K1 - 2).reshape(u.shape)
        x0 = np.take_along_axis(self.Xa, j, 1)
        x1 = np.take_along_axis(self.Xa, j + 1, 1)
        t0, t1 = self.Ta[j], self.Ta[j + 1]
        dt = t1 - t0
        frac = np.where(dt > 0, (u - t0) / np.where(dt > 0, dt, 1.0), 0.0)
        return x0 + np.clip(frac, 0.0, 1.0) * (x1 - x0)


# ==========================================================================
# METODOS CONFORMAL, AGNOSTICOS AL MODELO BASE
# ==========================================================================
def estatico(pred_test, s_cal, alpha=ALPHA):
    return pred_test.inv(cm.q_conformal(s_cal, alpha))


def ventana_deslizante(pred_test, s_todo, fechas_todo, f_t, ini_test, fin_test,
                       alpha=ALPHA, ventana_dias=60, refresco_dias=7,
                       embargo=EMBARGO_DIAS):
    U = np.full(len(pred_test), np.nan)
    refrescos = pd.date_range(ini_test, fin_test, freq=f'{refresco_dias}D')
    for t0 in refrescos:
        ini = np.datetime64((t0 - pd.Timedelta(days=ventana_dias + embargo)).date())
        fin = np.datetime64((t0 - pd.Timedelta(days=embargo)).date())
        win = (fechas_todo >= ini) & (fechas_todo < fin)
        obj = ((f_t >= np.datetime64(t0.date()))
               & (f_t < np.datetime64((t0 + pd.Timedelta(days=refresco_dias)).date())))
        if obj.sum() == 0 or win.sum() < 100:
            continue
        q_w = cm.q_conformal(s_todo[win], alpha)
        U[obj] = pred_test.sub(obj).inv(q_w)
    return U


def aci(pred_test, s_cal, y_t, f_t, fechas_test, gamma, alpha=ALPHA,
        embargo=EMBARGO_DIAS, alpha_min=None, alpha_max=None):
    """ACI de Gibbs y Candes sobre el pool estatico de scores.

    alpha_min / alpha_max acotan la actualizacion. En la version enviada el
    recorte es [-1, 2], que permite alpha_t <= 0 y por tanto q = +infinito, que
    es el origen de los intervalos infinitos (comentario R1.5). Pasando
    alpha_min > 0 se evita por construccion.
    """
    from collections import deque
    lo = -1.0 if alpha_min is None else float(alpha_min)
    hi = 2.0 if alpha_max is None else float(alpha_max)
    pool = np.sort(s_cal)
    alpha_t = alpha
    U = np.empty(len(pred_test))
    pendientes = deque()
    traza = []
    for f in fechas_test:
        mask = f_t == f
        q_t = cm.q_desde_pool(pool, alpha_t)
        U_t = pred_test.sub(mask).inv(q_t)
        U[mask] = U_t
        traza.append((f, alpha_t, q_t))
        err_t = 1 - (y_t[mask] <= U_t).mean()
        pendientes.append(err_t)
        if len(pendientes) > embargo:
            alpha_t = np.clip(alpha_t + gamma * (alpha - pendientes.popleft()), lo, hi)
    return U, alpha_t, traza


def transporte_aci(pred_test, s_cal, s_todo, fechas_todo, y_t, f_t, fechas_test,
                   gamma, rng, alpha=ALPHA, embargo=EMBARGO_DIAS,
                   ventana_dias=60, refresco_dias=7, shrinkage=True, tau=0.05,
                   B=150, alpha_min=None, alpha_max=None, ini_test=None):
    """Transporte de los scores de calibracion + ACI.

    ORDEN DE EJECUCION (comentario R1.2): en cada fecha t, (i) si toca refresco,
    se recalcula el mapa de transporte con la ventana reciente que termina en
    t - embargo y se transporta TODO el pool de calibracion; (ii) se toma el
    cuantil del pool transportado al alpha_t VIGENTE, que todavia no incorpora
    el error de t; (iii) se emite el intervalo; (iv) el error de t entra a la
    cola de embargo y actualiza alpha_{t+1} solo `embargo` pasos despues.
    El mapa nunca usa el alpha del ACI y el ACI nunca usa el mapa: el
    acoplamiento es solo a traves del pool.

    shrinkage=False usa el mapa puntual sin encogimiento de cola (ablacion de
    la Fase 2).
    """
    from collections import deque
    lo = -1.0 if alpha_min is None else float(alpha_min)
    hi = 2.0 if alpha_max is None else float(alpha_max)
    ini_test = pd.Timestamp(fechas_test[0]) if ini_test is None else pd.Timestamp(ini_test)
    alpha_t = alpha
    U = np.empty(len(pred_test))
    pool = np.sort(s_cal)
    prox = ini_test
    pendientes = deque()
    diag_por_periodo = {}
    for f in fechas_test:
        f_ts = pd.Timestamp(f)
        if f_ts >= prox:
            ini = np.datetime64((f_ts - pd.Timedelta(days=ventana_dias + embargo)).date())
            fin = np.datetime64((f_ts - pd.Timedelta(days=embargo)).date())
            reciente = (fechas_todo >= ini) & (fechas_todo < fin)
            s_new = s_todo[reciente]
            if len(s_new) >= 100:
                if shrinkage:
                    T, diag = cm.mapa_transporte_banda(s_cal, s_new, rng, B=B, tau=tau)
                else:
                    T = cm.mapa_transporte(s_cal, s_new)
                    diag = dict(sd_media=np.nan, sd_cola=np.nan, lam_cola=1.0)
                nm = etiquetar(f_ts)
                if nm is not None:
                    diag_por_periodo[nm] = diag
                pool = np.sort(T(s_cal))
            prox = f_ts + pd.Timedelta(days=refresco_dias)
        mask = f_t == f
        q_t = cm.q_desde_pool(pool, alpha_t)
        U_t = pred_test.sub(mask).inv(q_t)
        U[mask] = U_t
        err_t = 1 - (y_t[mask] <= U_t).mean()
        pendientes.append(err_t)
        if len(pendientes) > embargo:
            alpha_t = np.clip(alpha_t + gamma * (alpha - pendientes.popleft()), lo, hi)
    return U, alpha_t, diag_por_periodo


# ==========================================================================
# METRICAS
# ==========================================================================
def etiquetar(fecha):
    fecha = pd.Timestamp(fecha)
    for nombre, ini, fin in PERIODOS:
        if ini <= fecha < fin:
            return nombre
    return None


def interval_score_unilateral(y, U, alpha=ALPHA):
    """Interval score para un limite de prediccion UNILATERAL superior
    (comentario R1.5). Para el intervalo [0, U] a nivel 1-alpha el score de
    Gneiting y Raftery se reduce a

        IS = U + (2/alpha) * max(y - U, 0),

    que es el pinball loss del cuantil 1-alpha multiplicado por 2/alpha. Es
    propio, penaliza el ancho y la no cobertura en las mismas unidades (MWh) y,
    a diferencia del ancho medio, **no se puede calcular ignorando los
    intervalos infinitos**: si U = inf el score es +inf. Esa es exactamente la
    propiedad que faltaba en la version enviada.
    """
    y = np.asarray(y, float)
    U = np.asarray(U, float)
    return U + (2.0 / alpha) * np.maximum(y - U, 0.0)


def pinball(y, U, alpha=ALPHA):
    """Pinball loss del cuantil 1-alpha. Igual al interval score dividido por
    2/alpha; se reporta por ser la escala mas usual."""
    return interval_score_unilateral(y, U, alpha) * (alpha / 2.0)


def brier_ocurrencia(pred, y):
    """Brier score del evento {Y > 0} bajo la predictiva. Mide la parte de
    ocurrencia, que el score PIT trata via el atomo."""
    if isinstance(pred, PredictivaHurdle):
        p1 = pred.p
    else:
        p1 = 1.0 - pred.F0()
    return float(np.mean((p1 - (np.asarray(y) > 0).astype(float)) ** 2))


def crps_pred(pred, y, rng, n=300):
    return cm.crps(pred.muestrear(rng, n=n), y, rng)


def resumen_metrico(metodo, periodo, fecha, y, U, alpha=ALPHA):
    """Fila de metricas. Anade a la version enviada el interval score (que
    trata el infinito sin ignorarlo), la mediana del ancho finito y la
    cobertura desagregable."""
    cov, se, ndias = cm.cobertura_clusterizada(fecha, np.asarray(y) <= U)
    finito = np.isfinite(U)
    IS = interval_score_unilateral(y, U, alpha)
    # interval score agregado con y sin los infinitos, ambos declarados
    IS_fin = float(IS[finito].mean()) if finito.any() else np.nan
    IS_tot = float(np.mean(IS))          # +inf si hay algun intervalo infinito
    return dict(
        metodo=metodo, periodo=periodo,
        cobertura=round(100 * cov, 1),
        se_cluster=round(100 * se, 2) if pd.notna(se) else np.nan,
        ancho_medio=round(float(U[finito].mean()), 1) if finito.any() else np.nan,
        ancho_mediano=round(float(np.median(U[finito])), 1) if finito.any() else np.nan,
        pct_infinito=round(100 * float((~finito).mean()), 1),
        IS_finitos=round(IS_fin, 1) if np.isfinite(IS_fin) else np.nan,
        IS_total=IS_tot,
        n_dias=ndias, n=len(y))


def filas_por_periodo(metodo, fecha, y, U, alpha=ALPHA, extra=None):
    fecha = pd.to_datetime(np.asarray(fecha))
    per = np.array([etiquetar(f) for f in fecha], dtype=object)
    filas = []
    for nombre, _, _ in PERIODOS:
        m = per == nombre
        if m.sum() == 0:
            continue
        fila = resumen_metrico(metodo, nombre, np.asarray(fecha)[m],
                               np.asarray(y)[m], np.asarray(U)[m], alpha)
        if extra:
            fila.update(extra)
        filas.append(fila)
    return filas


def ordenar(filas):
    tabla = pd.DataFrame(filas)
    orden = {n: i for i, (n, _, _) in enumerate(PERIODOS)}
    tabla['_o'] = tabla.periodo.map(orden)
    cols = [c for c in tabla.columns if c not in ('metodo', '_o')]
    return tabla.sort_values(['metodo', '_o']).drop(columns='_o')[['metodo'] + cols]


# ==========================================================================
# INCERTIDUMBRE DE LAS DIFERENCIAS ENTRE METODOS (comentario R1.5)
# ==========================================================================
def bootstrap_diferencia(fecha, a, b, B=2000, seed=SEED_BOOTSTRAP):
    """Bootstrap por BLOQUES DE DIA sobre la diferencia de medias a - b.

    Remuestrea dias completos, no filas, que es la unidad de dependencia del
    panel (comentario R2.5). Devuelve la diferencia puntual y el intervalo de
    percentil al 95%.
    """
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({'f': pd.to_datetime(np.asarray(fecha)),
                       'a': np.asarray(a, float), 'b': np.asarray(b, float)})
    por_dia = df.groupby('f')[['a', 'b']].mean()
    dias = por_dia.index.values
    A, Bv = por_dia.a.values, por_dia.b.values
    d0 = float(np.mean(A) - np.mean(Bv))
    n = len(dias)
    reps = np.empty(B)
    for i in range(B):
        idx = rng.integers(0, n, n)
        reps[i] = np.mean(A[idx]) - np.mean(Bv[idx])
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return d0, float(lo), float(hi)


class Cronometro:
    """Costo computacional por metodo (comentario R1.3)."""

    def __init__(self):
        self.t = {}

    def __call__(self, nombre):
        self._n = nombre
        return self

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *a):
        self.t[self._n] = self.t.get(self._n, 0.0) + time.perf_counter() - self._t0
        return False
