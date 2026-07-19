#!/usr/bin/env python3
"""
PROTOTIPO DE LA CAPA DE INCERTIDUMBRE - flagship CurtailmentIQ
==============================================================
ADVERTENCIA IMPORTANTE: este script corre sobre DATOS SINTETICOS calibrados
para imitar las caracteristicas del EDA del release v1.0. NO son resultados
reales y no pueden citarse. Es un banco de pruebas de la METODOLOGIA:
cuando existan predicciones reales, se reemplaza la seccion 1 y el resto
corre igual.

Historia que demuestra:
  1. Datos sinteticos: ~30% ceros, magnitud lognormal cola pesada,
     persistencia AR(1) 0.85, ciclo semanal, quiebre BESS desde fines 2024.
  2. Modelo hurdle: ocurrencia (clasificador) + magnitud (lognormal).
  3. Conformal split one-sided: intervalo [0, U] con cobertura garantizada.
  4. LA COBERTURA SE CUMPLE pre-quiebre y SOBRECUBRE post-quiebre con
     intervalos sobreanchos e inutiles: se pierde sharpness, no cobertura.
  5. Weighted conformal (Tibshirani et al. 2019) como intento de reparacion.
  6. Metricas: cobertura, ancho (sharpness), CRPS.
"""
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression

RNG = np.random.default_rng(7)
ALPHA = 0.10  # queremos cobertura nominal del 90%

# =====================================================================
# 1. DATOS SINTETICOS (reemplazable por predicciones reales)
# =====================================================================
def generar_panel():
    dates = pd.date_range('2022-01-01', '2026-05-31', freq='D')
    T, J = len(dates), 40

    cap = RNG.lognormal(np.log(90), 0.55, J)          # potencia MW por central
    plant_eff = RNG.normal(0, 0.35, J)                 # efecto fijo de central

    # Estado latente del sistema con persistencia AR(1) (EDA: ACF lag-1 ~0.85)
    rho = 0.85
    z = np.zeros(T)
    for t in range(1, T):
        z[t] = rho * z[t-1] + RNG.normal(0, np.sqrt(1 - rho**2))

    doy = dates.dayofyear.values
    seas = np.cos(2*np.pi*(doy - 15)/365)              # verano austral en enero
    dow = dates.dayofweek.values
    weekly = np.where(dow >= 5, 0.35, 0.0)             # finde: menos demanda, mas vertimiento
    yrs = (dates - dates[0]).days.values / 365.25
    trend = 0.85 * np.minimum(yrs, 2.6)                # crecimiento hasta ~mid-2024

    # BESS: rampa desde oct-2024 (EDA: quiebre visible desde ene-2025)
    bess = np.clip((dates - pd.Timestamp('2024-10-01')).days.values / 365.25, 0, None)
    bess = np.minimum(bess, 1.3)

    filas = []
    for j in range(J):
        eta = 0.9 + 1.0*seas + 0.85*z + 0.4*trend + weekly + plant_eff[j]
        p_occ = 1/(1 + np.exp(-eta))
        occ = RNG.random(T) < p_occ
        mu = 1.6 + 0.45*np.log(cap[j]) + 0.75*seas + 0.80*z + 0.55*trend - 1.25*bess
        mag = RNG.lognormal(mu, 0.85)
        y = np.where(occ, mag, 0.0)
        filas.append(pd.DataFrame({
            'fecha': dates, 'central': f'PFV-{j:02d}', 'y': y,
            'seas': seas, 'z': z, 'weekly': weekly, 'trend': trend,
            'log_cap': np.log(cap[j]), 'bess': bess,
        }))
    df = pd.concat(filas, ignore_index=True).sort_values(['central', 'fecha'])
    # lag-1 por central: la persistencia es la feature mas fuerte y el baseline a batir
    df['y_lag1'] = df.groupby('central')['y'].shift(1)
    df['occ_lag1'] = (df['y_lag1'] > 0).astype(float)
    return df.dropna().reset_index(drop=True)

# =====================================================================
# 2. MODELO HURDLE (dos partes)
# =====================================================================
FEATS = ['seas', 'z', 'weekly', 'trend', 'log_cap', 'y_lag1', 'occ_lag1']

class Hurdle:
    """P(Y>0) via clasificador; Y|Y>0 ~ LogNormal(mu(x), sigma)."""
    def fit(self, X, y):
        occ = (y > 0).astype(int)
        self.clf = GradientBoostingClassifier(max_depth=3, n_estimators=200,
                                              learning_rate=0.05, random_state=0)
        self.clf.fit(X, occ)
        pos = y > 0
        self.reg = GradientBoostingRegressor(max_depth=3, n_estimators=200,
                                             learning_rate=0.05, random_state=0)
        self.reg.fit(X[pos], np.log(y[pos]))
        resid = np.log(y[pos]) - self.reg.predict(X[pos])
        self.sigma = resid.std()
        return self

    def params(self, X):
        p = np.clip(self.clf.predict_proba(X)[:, 1], 1e-6, 1-1e-6)
        mu = self.reg.predict(X)
        return p, mu

    def upper(self, X, alpha):
        """Cuantil (1-alpha) de la mezcla: delta_0 con peso (1-p) + LogNormal con peso p.
        Si p <= alpha, el modelo dice 'casi seguro cero' y el limite es 0."""
        p, mu = self.params(X)
        u = np.zeros(len(p))
        m = p > alpha
        u[m] = np.exp(mu[m] + self.sigma * norm.ppf(1 - alpha/p[m]))
        return u

    def sample(self, X, n=200):
        p, mu = self.params(X)
        occ = RNG.random((len(p), n)) < p[:, None]
        mag = np.exp(mu[:, None] + self.sigma * RNG.standard_normal((len(p), n)))
        return np.where(occ, mag, 0.0)

# =====================================================================
# 3-5. CONFORMAL
# =====================================================================
def q_conformal(scores, alpha):
    """Cuantil conformal estandar con la correccion de muestra finita."""
    n = len(scores)
    k = int(np.ceil((n+1)*(1-alpha)))
    if k > n:
        return np.inf
    return np.sort(scores)[k-1]

def q_conformal_ponderado(scores, w, alpha):
    """Weighted conformal (Tibshirani et al. 2019). w = dP_test/dP_calib.
    El punto de test aporta masa en +inf con peso w_test=media(w)."""
    w = np.asarray(w, float)
    w_test = w.mean()
    total = w.sum() + w_test
    orden = np.argsort(scores)
    s, p = np.asarray(scores)[orden], w[orden]/total
    cum = np.cumsum(p)
    idx = np.searchsorted(cum, 1-alpha)
    return np.inf if idx >= len(s) else s[idx]

def pesos_shift(X_cal, X_test):
    """Razon de densidades via clasificador calib-vs-test (odds ratio)."""
    X = np.vstack([X_cal, X_test])
    etiq = np.r_[np.zeros(len(X_cal)), np.ones(len(X_test))]
    clf = LogisticRegression(max_iter=2000).fit(X, etiq)
    pr = np.clip(clf.predict_proba(X_cal)[:, 1], 1e-4, 1-1e-4)
    return (pr/(1-pr)) * (len(X_cal)/len(X_test))

# =====================================================================
# 6. METRICAS
# =====================================================================
def crps(muestras, y):
    """CRPS por muestreo: E|X-y| - 0.5*E|X-X'|. Premia exactitud Y confianza calibrada."""
    a = np.abs(muestras - y[:, None]).mean(1)
    idx = RNG.permutation(muestras.shape[1])
    b = 0.5*np.abs(muestras - muestras[:, idx]).mean(1)
    return (a - b).mean()

def evaluar(nombre, y, U):
    cob = (y <= U).mean()
    return dict(conjunto=nombre, cobertura=round(100*cob, 1),
                ancho_medio=round(float(np.mean(U)), 1), n=len(y))

# =====================================================================
# MAIN
# =====================================================================
if __name__ == '__main__':
    df = generar_panel()
    print("="*74)
    print("PROTOTIPO CONFORMAL - DATOS SINTETICOS (no son resultados reales)")
    print("="*74)
    print(f"\nPanel: {len(df):,} filas | {df.central.nunique()} centrales | "
          f"{df.fecha.min().date()} a {df.fecha.max().date()}")
    print(f"Ceros: {100*(df.y==0).mean():.1f}%  (EDA solar real: 27.1%)")
    pos = df.y[df.y > 0]
    print(f"Magnitud>0 p50={pos.quantile(.5):.0f} p90={pos.quantile(.9):.0f} "
          f"p99={pos.quantile(.99):.0f} MWh | razon p99/p50={pos.quantile(.99)/pos.quantile(.5):.1f}x "
          f"(EDA real: 15x)")

    # ---- Splits temporales (el diseno que discutiremos con Kerven)
    # Audit Kerven (pto 3): la rampa BESS parte el 1-oct-2024, asi que el test
    # de mismo regimen termina el 2024-09-30; oct-dic 2024 es rampa temprana.
    tr    = df[df.fecha <  '2024-01-01']                                  # entrena
    cal   = df[(df.fecha >= '2024-01-01') & (df.fecha < '2024-09-01')]    # calibra
    tpre  = df[(df.fecha >= '2024-09-01') & (df.fecha < '2024-10-01')]    # test MISMO regimen
    tramp = df[(df.fecha >= '2024-10-01') & (df.fecha < '2025-01-01')]    # rampa BESS temprana
    tpos  = df[df.fecha >= '2025-01-01']                                  # test POST-quiebre
    for n, d in [('train', tr), ('calib', cal), ('test_pre', tpre),
                 ('test_ramp', tramp), ('test_post', tpos)]:
        print(f"  {n:10s} {len(d):7,} filas  {d.fecha.min().date()} .. {d.fecha.max().date()}")

    # ---- Ajuste del hurdle
    m = Hurdle().fit(tr[FEATS].values, tr.y.values)
    print(f"\nHurdle ajustado. sigma (dispersion log-magnitud) = {m.sigma:.3f}")

    # ---- PASO 1: sin conformal, solo el modelo (cobertura nominal 90%)
    print("\n" + "-"*74)
    print("PASO 1 - Modelo solo, sin garantia (cuantil 90% del hurdle)")
    print("-"*74)
    filas = [evaluar('test_pre  (mismo regimen)', tpre.y.values, m.upper(tpre[FEATS].values, ALPHA)),
             evaluar('test_ramp (rampa temprana)', tramp.y.values, m.upper(tramp[FEATS].values, ALPHA)),
             evaluar('test_post (post-quiebre)', tpos.y.values, m.upper(tpos[FEATS].values, ALPHA))]
    print(pd.DataFrame(filas).to_string(index=False))

    # ---- PASO 2: conformal split -> garantia bajo intercambiabilidad
    print("\n" + "-"*74)
    print("PASO 2 - Conformal split (garantia >=90% SI hay intercambiabilidad)")
    print("-"*74)
    U_cal = m.upper(cal[FEATS].values, ALPHA)
    s_cal = cal.y.values - U_cal                 # score: cuanto EXCEDIO el limite
    qhat = q_conformal(s_cal, ALPHA)
    print(f"Correccion conformal qhat = {qhat:+.1f} MWh  (n_calib={len(cal):,})")
    filas = []
    for nombre, d in [('test_pre  (mismo regimen)', tpre), ('test_ramp (rampa temprana)', tramp),
                      ('test_post (post-quiebre)', tpos)]:
        U = np.maximum(0, m.upper(d[FEATS].values, ALPHA) + qhat)
        filas.append(evaluar(nombre, d.y.values, U))
    print(pd.DataFrame(filas).to_string(index=False))

    # ---- PASO 3: el quiebre ano por ano
    print("\n" + "-"*74)
    print("PASO 3 - Cobertura conformal por semestre (el quiebre en camara lenta)")
    print("-"*74)
    tmp = df[df.fecha >= '2024-01-01'].copy()
    tmp['U'] = np.maximum(0, m.upper(tmp[FEATS].values, ALPHA) + qhat)
    tmp['cubierto'] = tmp.y <= tmp.U
    tmp['periodo'] = tmp.fecha.dt.year.astype(str) + '-S' + ((tmp.fecha.dt.month > 6).astype(int)+1).astype(str)
    r = tmp.groupby('periodo').agg(cobertura=('cubierto', lambda x: round(100*x.mean(), 1)),
                                   ancho=('U', lambda x: round(x.mean(), 1)),
                                   n=('y', 'size'))
    # Audit Kerven (pto 3): 2024-S1 es el propio set de calibracion evaluado
    # in-sample; se marca para que no se lea como cobertura out-of-sample.
    r = r.rename(index={'2024-S1': '2024-S1 (calib, in-sample)'})
    print(r.to_string())

    # ---- PASO 4: weighted conformal
    print("\n" + "-"*74)
    print("PASO 4 - Weighted conformal (reponderar la calibracion hacia el test)")
    print("-"*74)
    w = pesos_shift(cal[FEATS].values, tpos[FEATS].values)
    print(f"Pesos: min={w.min():.3f} mediana={np.median(w):.3f} max={w.max():.3f} "
          f"| ESS={(w.sum()**2/np.sum(w**2)):.0f} de {len(w):,}")
    qw = q_conformal_ponderado(s_cal, w, ALPHA)
    print(f"qhat ponderado = {qw:+.1f} MWh (vs {qhat:+.1f} sin ponderar)")
    U = np.maximum(0, m.upper(tpos[FEATS].values, ALPHA) + qw)
    print(pd.DataFrame([evaluar('test_post con weighted conformal', tpos.y.values, U)]).to_string(index=False))

    # ---- PASO 5: recalibrar con datos post-quiebre (el arreglo practico)
    print("\n" + "-"*74)
    print("PASO 5 - Recalibrar con los primeros 60 dias post-quiebre")
    print("-"*74)
    cal2 = df[(df.fecha >= '2025-01-01') & (df.fecha < '2025-03-02')]
    resto = df[df.fecha >= '2025-03-02']
    q2 = q_conformal(cal2.y.values - m.upper(cal2[FEATS].values, ALPHA), ALPHA)
    U = np.maximum(0, m.upper(resto[FEATS].values, ALPHA) + q2)
    print(f"qhat recalibrado = {q2:+.1f} MWh (n={len(cal2):,})")
    print(pd.DataFrame([evaluar('resto post-quiebre, recalibrado', resto.y.values, U)]).to_string(index=False))

    # ---- CRPS
    print("\n" + "-"*74)
    print("CRPS (menor es mejor) - grado global del pronostico probabilistico")
    print("-"*74)
    for nombre, d in [('test_pre ', tpre), ('test_post', tpos)]:
        print(f"  {nombre}: CRPS = {crps(m.sample(d[FEATS].values), d.y.values):7.2f} MWh")
    print("\nBaseline persistencia (y_lag1 como pronostico puntual, MAE):")
    for nombre, d in [('test_pre ', tpre), ('test_post', tpos)]:
        print(f"  {nombre}: MAE = {np.abs(d.y.values - d.y_lag1.values).mean():7.2f} MWh")
    print("\n" + "="*74)
