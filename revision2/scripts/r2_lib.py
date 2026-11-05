"""
Libreria comun de la SEGUNDA revision (SEGAN-D-26-03850R1 -> R2).

Reutiliza sin modificar la maquinaria de la primera revision que vive en
`curtailmentiq-research/flagship/revision/rev_lib.py` (capa conformal,
predictivas, metricas) y `flagship/entrenar_baselines.py` (panel y features).
Nada de este modulo escribe dentro de `curtailmentiq-research/`: todas las
salidas van a `revision2-segan/`.

Convenciones
------------
* Filas: el panel de prediccion 2024-01-01 .. 2026-05-31 sobre el conjunto
  comun de filas del paper, ordenado por (fecha, central_codigo). Es el mismo
  orden que usa la Fase 0, y por eso las series se alinean fila a fila.
* Ventanas: las cinco del paper mas TEST_COMPLETO (2024-09-01 .. 2026-05-31).
* Semillas: las del paper (20260720 score PIT y bootstrap del mapa, 11 CRPS,
  20260901 bootstrap por dias). Las nuevas se declaran donde se usan.
"""
from pathlib import Path
import os
import sys
import time

sys.dont_write_bytecode = True           # no dejar __pycache__ en el repo
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')

import numpy as np
import pandas as pd

R2 = Path(__file__).resolve().parents[1]
PROY = R2.parent
# Dentro del repositorio (curtailmentiq-research/revision2/) el repo es el padre;
# como carpeta de trabajo al lado del repo, es PROY/curtailmentiq-research.
REPO = PROY if (PROY / 'flagship' / 'revision' / 'rev_lib.py').exists() else PROY / 'curtailmentiq-research'
RES = R2 / 'resultados'
FIG = R2 / 'figuras'
LOGS = R2 / 'logs'
PRED_DIR = RES / 'predictivas'
SERIES_DIR = RES / 'series'
for d in (RES, FIG, LOGS, PRED_DIR, SERIES_DIR):
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(REPO / 'flagship'))
sys.path.insert(0, str(REPO / 'flagship' / 'revision'))
sys.path.insert(0, str(REPO / 'flagship' / 'revision' / 'verificacion'))
import rev_lib as R                      # noqa: E402
import conformal_metodos as cm           # noqa: E402

ALPHA = R.ALPHA
FIN_TEST = pd.Timestamp('2026-06-01')
PERIODOS = R.PERIODOS
PER_TODOS = R.PERIODOS + [('TEST_COMPLETO', R.CAL_FIN, FIN_TEST)]

# Nombres de ventana para el paper (ingles)
VENTANA_EN = {'test_pre': 'Sep 2024', 'test_transition': 'Oct-Dec 2024',
              '2025-S1': '2025-S1', '2025-S2': '2025-S2', '2026-S1': '2026-S1',
              'TEST_COMPLETO': 'Whole test'}

# --------------------------------------------------------------------------
# Modelos base (brazos). 'diag' = entra al diagnostico de celdas.
# --------------------------------------------------------------------------
BRAZOS = {
    # nombre           etiqueta paper                    familia   arboles  diag
    'hurdle_800':     ('Hurdle, 2x400 trees (paper)',     'hurdle', 800,   True),
    'hurdle_es':      ('Hurdle, early stopping (105 trees)', 'hurdle', 105, True),
    'hurdle_sigma_x': ('Hurdle, sigma(x)',                'hurdle', 800,   True),
    'hurdle_2000':    ('Hurdle, 2x2000 trees',            'hurdle', 4000,  True),
    'qgbm_54x15':     ('Quantile GBM, 54x15',             'qgbm',   810,   True),
    'qgbm_54x50':     ('Quantile GBM, 54x50',             'qgbm',   2700,  True),
    'qgbm_54x100':    ('Quantile GBM, 54x100',            'qgbm',   5400,  True),
    'qgbm_54x200':    ('Quantile GBM, 54x200',            'qgbm',   10800, True),
    'qgbm_54x400':    ('Quantile GBM, 54x400 (paper)',    'qgbm',   21600, True),
}
# Los tres modelos base de las tablas principales de la R2
PRINCIPALES = ('hurdle_800', 'hurdle_es', 'qgbm_54x400')
# Los 40 brazos-celda del diagnostico de la R1 (sin el hurdle ES)
DIAG_R1 = tuple(b for b in BRAZOS if b != 'hurdle_es')


def log(msg, archivo=None):
    linea = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(linea, flush=True)
    if archivo is not None:
        with open(LOGS / archivo, 'a') as fp:
            fp.write(linea + '\n')


# --------------------------------------------------------------------------
# Panel de filas y metadatos
# --------------------------------------------------------------------------
def panel_filas():
    """fecha, central_codigo, y_real, tecnologia, region, potencia_mw para
    las filas de prediccion, en el orden canonico (fecha, central)."""
    f = PRED_DIR / 'panel_filas.parquet'
    if f.exists():
        return pd.read_parquet(f)
    h = pd.read_csv(REPO / 'flagship' / 'predicciones' / 'pred_hurdle.csv',
                    parse_dates=['fecha'])
    h = h.sort_values(['fecha', 'central_codigo']).reset_index(drop=True)
    meta = pd.read_csv(REPO / 'release' / 'v1.0' / 'plants_metadata.csv')
    meta = meta[['central_codigo', 'region', 'potencia_mw']].drop_duplicates('central_codigo')
    h = h[['fecha', 'central_codigo', 'tecnologia', 'y_real']].merge(
        meta, on='central_codigo', how='left')
    assert len(h) == 104420, len(h)
    h.to_parquet(f, index=False)
    return h


# --------------------------------------------------------------------------
# Persistencia de predictivas
# --------------------------------------------------------------------------
def guardar_predictiva(nombre, pred, meta=None):
    f = PRED_DIR / f'{nombre}.npz'
    if isinstance(pred, R.PredictivaHurdle):
        sig = np.asarray(pred.sigma, float)
        np.savez_compressed(f, tipo='hurdle', p=pred.p, mu=pred.mu, sigma=sig,
                            meta=str(meta or {}))
    else:
        np.savez_compressed(f, tipo='qgbm', Q=pred.Q.astype(np.float64),
                            taus=pred.taus, meta=str(meta or {}))


def cargar_predictiva(nombre):
    z = np.load(PRED_DIR / f'{nombre}.npz', allow_pickle=False)
    if str(z['tipo']) == 'hurdle':
        sig = z['sigma']
        sig = float(sig) if sig.ndim == 0 else sig
        return R.PredictivaHurdle(z['p'], z['mu'], sig)
    return R.PredictivaCuantilica(z['Q'], z['taus'])


def contexto(nombre):
    """Carga una predictiva y deja listo todo lo que la capa conformal usa,
    con el generador canonico: el MISMO objeto rng aleatoriza el atomo del
    score y despues alimenta el bootstrap del mapa (orden de la R1)."""
    h = panel_filas()
    pred = cargar_predictiva(nombre)
    rng = np.random.default_rng(R.SEED_CONFORMAL)
    s = pred.cdf(h.y_real.values, rng)
    h = h.assign(s=s)
    cal = ((h.fecha >= R.CAL_INI) & (h.fecha < R.CAL_FIN)).values
    idx = ((h.fecha >= R.CAL_FIN) & (h.fecha < FIN_TEST)).values
    test = h[idx].reset_index(drop=True)
    return dict(nombre=nombre, h=h, pred=pred, rng=rng, s_cal=h.s.values[cal],
                cal=cal, idx=idx, test=test, p_t=pred.sub(idx),
                y_t=test.y_real.values, f_t=test.fecha.values,
                fechas_test=np.sort(test.fecha.unique()))


# --------------------------------------------------------------------------
# Metodos adicionales
# --------------------------------------------------------------------------
def cqr_unilateral(pred, h, cal, idx, alpha=ALPHA):
    """CQR unilateral (Romano et al., 2019) sobre el cuantil 1-alpha de la
    PROPIA predictiva: E = y - q_{1-alpha}(x) en calibracion,
    U = max(q_{1-alpha}(x) + Q_{1-alpha}(E), 0). Para el QGBM coincide con el
    benchmark B3 de la R1 cuando 1-alpha esta en la rejilla."""
    q = pred.inv(np.full(len(pred), 1 - alpha))
    E = h.y_real.values[cal] - q[cal]
    Q = cm.q_conformal(E, alpha)
    U = np.maximum(q + Q, 0.0)
    return U[idx], float(Q)


def oraculo_constante(pred_t, y, cobertura_objetivo, lo=1e-6, hi=0.999999):
    """Umbral PIT constante elegido EX POST para que el limite F^{-1}(q)
    cubra exactamente la fraccion pedida en las filas dadas. Es el
    reajuste puramente mecanico: no adapta nada en el tiempo. Biseccion
    sobre q (la cobertura es monotona en q)."""
    def cov(q):
        return float(np.mean(y <= pred_t.inv(np.full(len(y), q))))
    a, b = lo, hi
    if cov(b) < cobertura_objetivo:
        return b
    for _ in range(40):
        m = 0.5 * (a + b)
        if cov(m) < cobertura_objetivo:
            a = m
        else:
            b = m
    return b


# --------------------------------------------------------------------------
# Metricas
# --------------------------------------------------------------------------
def metricas_basicas(f, y, U, alpha=ALPHA):
    return R.resumen_metrico('', '', f, y, U, alpha)


def twcrps_muestras(muestras, y, umbral, rng):
    """CRPS ponderado por umbral (Gneiting y Ranjan, 2011) con peso
    w(z) = 1{z >= r}: es el CRPS de las variables encadenadas max(X, r) contra
    max(y, r). `umbral` puede ser un vector por fila."""
    r = np.asarray(umbral, float)[:, None]
    X = np.maximum(muestras, r)
    yy = np.maximum(np.asarray(y, float), r[:, 0])
    return cm.crps(X, yy, rng)


def ancho_finito(U):
    fi = np.isfinite(U)
    return float(U[fi].mean()) if fi.any() else np.nan


def mascara(f_t, ini, fin):
    return ((f_t >= np.datetime64(pd.Timestamp(ini).date()))
            & (f_t < np.datetime64(pd.Timestamp(fin).date())))


# --------------------------------------------------------------------------
# Transport+ACI con TODOS los parametros expuestos (para el Apendice E).
# Copia literal de rev_lib.transporte_aci + n_grid y min_recientes, que alli
# estan fijos (100 y 100). Con los valores por defecto reproduce rev_lib
# exactamente (verificado en r2_06).
# --------------------------------------------------------------------------
def mapa_banda_ext(s_old, s_new, rng, B=150, n_grid=100, tau=0.05):
    g = min(n_grid, max(20, len(s_new) // 2))
    niveles = np.linspace(0, 1, g)
    q_old = np.quantile(s_old, niveles)
    m = len(s_new)
    Tb = np.empty((B, g))
    for b in range(B):
        Tb[b] = np.quantile(s_new[rng.integers(0, m, m)], niveles)
    q_bag, sd = Tb.mean(0), Tb.std(0)
    lam = 1.0 / (1.0 + (sd / tau) ** 2) if np.isfinite(tau) else np.ones_like(sd)
    q_reg = np.clip(np.maximum.accumulate((1 - lam) * q_old + lam * q_bag), 0.0, 1.0)

    def T(s):
        return np.interp(np.interp(s, q_old, niveles), niveles, q_reg)
    return T


def transporte_aci_ext(pred_test, s_cal, s_todo, fechas_todo, y_t, f_t, fechas_test,
                       gamma, rng, alpha=ALPHA, embargo=R.EMBARGO_DIAS, ventana_dias=60,
                       refresco_dias=7, shrinkage=True, tau=0.05, B=150, n_grid=100,
                       min_recientes=100, alpha_min=None, alpha_max=None, ini_test=None,
                       adaptar=True):
    from collections import deque
    lo = -1.0 if alpha_min is None else float(alpha_min)
    hi = 2.0 if alpha_max is None else float(alpha_max)
    ini_test = pd.Timestamp(fechas_test[0]) if ini_test is None else pd.Timestamp(ini_test)
    alpha_t = alpha
    U = np.empty(len(pred_test))
    pool = np.sort(s_cal)
    prox = ini_test
    pend = deque()
    for f in fechas_test:
        f_ts = pd.Timestamp(f)
        if f_ts >= prox:
            ini = np.datetime64((f_ts - pd.Timedelta(days=ventana_dias + embargo)).date())
            fin = np.datetime64((f_ts - pd.Timedelta(days=embargo)).date())
            s_new = s_todo[(fechas_todo >= ini) & (fechas_todo < fin)]
            if len(s_new) >= min_recientes:
                if shrinkage:
                    T = mapa_banda_ext(s_cal, s_new, rng, B=B, n_grid=n_grid, tau=tau)
                else:
                    T = cm.mapa_transporte(s_cal, s_new, n_grid=n_grid)
                pool = np.sort(T(s_cal))
            prox = f_ts + pd.Timedelta(days=refresco_dias)
        mask = f_t == f
        q_t = cm.q_desde_pool(pool, alpha_t)
        U_t = pred_test.sub(mask).inv(q_t)
        U[mask] = U_t
        if adaptar:
            pend.append(1 - (y_t[mask] <= U_t).mean())
            if len(pend) > embargo:
                alpha_t = np.clip(alpha_t + gamma * (alpha - pend.popleft()), lo, hi)
    return U
