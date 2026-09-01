#!/usr/bin/env python3
"""
PROTOTIPO CONFORMAL v2 - flagship CurtailmentIQ
================================================
Diseno de Kerven Cea (Methodology / Formal analysis), a partir del audit
metodologico sobre conformal_prototype.py (ver AUDIT_METODOLOGICO.md).
Corre sobre el MISMO panel sintetico que v1 (misma semilla, mismo generador,
sin tocarlo) para que los resultados sean comparables.

ADVERTENCIA: datos sinteticos. No son resultados reales, no se citan.

Que compara este script (todos sobre los splits corregidos: test_pre =
solo septiembre 2024, ya no incluye la ventana de transicion que arrancaba en
2024-10-01, error de v1 que el audit encontro):

  a) Conformal split estatico, score aditivo (referencia = v1).
  b) Conformal split estatico, score PIT (recomendacion central de Kerven).
  c) Weighted conformal POR-PUNTO (Tibshirani et al. 2019 correcto), el
     negative result: reporta % de intervalos infinitos.
  d) Pesos de recencia fijos (Barber, Candes, Ramdas, Tibshirani 2023),
     sin clasificador, 3 semividas.
  e) Ventana deslizante 60 dias, recalibrada cada 7, score aditivo y PIT.
  f) ACI (Gibbs & Candes 2021) sobre score PIT, 3 tasas de aprendizaje.
  g) Transporte de scores (mapa monotono 1D via cuantiles empiricos) +
     ACI, la propuesta teorica de Kerven.

Reproducibilidad: importa conformal_prototype como modulo (mismo RNG con
semilla 7, mismo orden de consumo hasta el ajuste del hurdle) + un RNG
propio (semilla fija) para la aleatorizacion del atomo en el score PIT y
para el test numerico de inversion.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conformal_prototype as cp  # noqa: E402  (mismo generador, sin tocarlo)

ALPHA = cp.ALPHA
RNG2 = np.random.default_rng(20260720)  # aleatoriedad NUEVA de v2 (atomo PIT), separada de cp.RNG

FLAGSHIP = Path(__file__).resolve().parent


# =====================================================================
# 0. TEST NUMERICO DE LA INVERSION PIT (punto 1 del encargo)
# =====================================================================
def test_inversion_pit():
    """Bajo el modelo VERDADERO (p, mu, sigma oraculo, sin ajuste), el score
    PIT aleatorizado s = F_x(0)*V si y=0, F_x(y) si y>0, es Uniforme(0,1)
    exacto (teorema estandar de PIT aleatorizado para leyes con atomos:
    Smith 1985; aqui con la mezcla hurdle). Verificamos dos cosas:
      (i) que los cuantiles empiricos de s calzan con el nivel teorico;
      (ii) que invertir el cuantil (1-alpha) de s recupera cobertura
           oraculo ~ 1-alpha, para varios alpha.
    """
    rng = np.random.default_rng(123)  # RNG local, hermetico, no toca cp.RNG ni RNG2
    n = 500_000
    p0, mu0, sigma0 = 0.65, 3.0, 0.8
    occ = rng.random(n) < p0
    mag = np.exp(mu0 + sigma0 * rng.standard_normal(n))
    y = np.where(occ, mag, 0.0)

    z = (np.log(np.maximum(y, 1e-300)) - mu0) / sigma0
    Fpos = (1 - p0) + p0 * norm.cdf(z)
    s = np.where(y > 0, Fpos, (1 - p0) * rng.random(n))
    assert s.min() >= 0 and s.max() <= 1, "score PIT fuera de [0,1]"

    print("  (i) uniformidad de s bajo el modelo oraculo:")
    for lvl in (0.1, 0.5, 0.9, 0.99):
        qe = np.quantile(s, lvl)
        print(f"      nivel {lvl:.2f}  cuantil empirico de s = {qe:.4f}")
        assert abs(qe - lvl) < 0.01, f"PIT no uniforme en nivel {lvl}"

    print("  (ii) cobertura oraculo tras invertir (formula unificada por clip):")
    for alpha in (0.10, 0.20, 0.02):
        q = np.quantile(s, 1 - alpha)
        thresh = 1 - p0
        arg = np.clip((q - thresh) / p0, 0.0, 1.0)
        U = np.exp(mu0 + sigma0 * norm.ppf(arg))
        cov = (y <= U).mean()
        print(f"      alpha={alpha:.2f}  U={U:8.2f}  cobertura oraculo={100*cov:5.2f}%  "
              f"(objetivo {100*(1-alpha):.0f}%)")
        assert abs(cov - (1 - alpha)) < 0.01, f"cobertura oraculo fuera de tolerancia en alpha={alpha}"
    print("  PASA: inversion PIT verificada numericamente.\n")


# =====================================================================
# 1. SCORE PIT Y SU INVERSION
# =====================================================================
def pit_score(m, X, y, rng):
    """s = F_x(y): (1-p)+p*Phi((log y - mu)/sigma) si y>0; (1-p)*V si y=0,
    V~U(0,1). Aleatorizacion del atomo (Smith 1985): PIT estandar para
    leyes con saltos; aqui el salto de F en 0 mide (1-p)."""
    p, mu = m.params(X)
    yy = np.maximum(y, 1.0)  # evita log(0); descartado por np.where cuando y=0
    z = (np.log(yy) - mu) / m.sigma
    Fpos = (1 - p) + p * norm.cdf(z)
    return np.where(y > 0, Fpos, (1 - p) * rng.random(len(y)))


def pit_upper(m, X, q):
    """Invierte F_x(U) = q. Formula de Kerven en dos ramas (U=0 si
    q<=1-p; si no, exp(mu+sigma*Phi^-1((q-(1-p))/p))) es equivalente a
    un solo np.clip: en el limite q->(1-p)+, Phi^-1(0)=-inf da U=0 (misma
    continuidad); si q=+inf (qhat no finito), clip lo satura a 1 y
    Phi^-1(1)=+inf da U=inf. q puede ser escalar o array del largo de X."""
    p, mu = m.params(X)
    thresh = 1 - p
    arg = np.clip((np.asarray(q, dtype=float) - thresh) / p, 0.0, 1.0)
    with np.errstate(divide='ignore'):
        return np.exp(mu + m.sigma * norm.ppf(arg))


# =====================================================================
# 2. CUANTIL CONFORMAL PONDERADO GENERICO
#    (reemplaza a cp.q_conformal_ponderado: ese pooled con w_test=mean(w)
#    fue el artefacto que el audit identifico. Aqui w_test es explicito:
#    escalar para pesos fijos/recencia (Barber et al. 2023, w_test=1),
#    o un array por punto de test (Tibshirani et al. 2019 correcto).)
# =====================================================================
def q_ponderado(scores, w, w_test, alpha):
    w = np.asarray(w, float)
    orden = np.argsort(scores)
    s_sorted = np.asarray(scores)[orden]
    w_sorted = w[orden]
    cumw = np.cumsum(w_sorted)
    W = w_sorted.sum()
    w_test_arr = np.atleast_1d(np.asarray(w_test, dtype=float))
    umbral = (1 - alpha) * (W + w_test_arr)
    idx = np.searchsorted(cumw, umbral)
    q = np.where(idx >= len(s_sorted), np.inf, s_sorted[np.minimum(idx, len(s_sorted) - 1)])
    return q if q.shape != (1,) or np.ndim(w_test) > 0 else q[0]


def mapa_transporte(s_old, s_new, n_grid=200):
    """T = F_new^{-1} o F_old, interpolacion monotona entre cuantiles
    empiricos (mapa de transporte optimo en 1D = increasing rearrangement).
    n_grid limitado por el tamano de la muestra 'nueva' (ventana corta)."""
    g = min(n_grid, max(20, len(s_new) // 2))
    niveles = np.linspace(0, 1, g)
    q_old = np.quantile(s_old, niveles)
    q_new = np.quantile(s_new, niveles)

    def T(s):
        nivel = np.interp(s, q_old, niveles)
        return np.interp(nivel, niveles, q_new)
    return T


# =====================================================================
# 3. COBERTURA CON ERROR ESTANDAR CLUSTERIZADO POR FECHA
#    (decision del audit: las centrales comparten el estado sistemico
#    diario, el n efectivo es el de dias, no de filas)
# =====================================================================
def cobertura_clusterizada(fecha, cubierto):
    por_dia = pd.Series(np.asarray(cubierto, float)).groupby(
        pd.Series(fecha).values).mean()
    cov = por_dia.mean()
    se = por_dia.std(ddof=1) / np.sqrt(len(por_dia)) if len(por_dia) > 1 else np.nan
    return cov, se, len(por_dia)


PERIODOS = [
    ('test_pre',  pd.Timestamp('2024-09-01'), pd.Timestamp('2024-10-01')),
    ('test_transition', pd.Timestamp('2024-10-01'), pd.Timestamp('2025-01-01')),
    ('2025-S1',   pd.Timestamp('2025-01-01'), pd.Timestamp('2025-07-01')),
    ('2025-S2',   pd.Timestamp('2025-07-01'), pd.Timestamp('2026-01-01')),
    ('2026-S1',   pd.Timestamp('2026-01-01'), pd.Timestamp('2026-06-01')),
]


def etiquetar_periodo(fecha):
    for nombre, ini, fin in PERIODOS:
        if ini <= fecha < fin:
            return nombre
    return None


def fila_metrica(metodo, periodo, fecha, y, U, n_score_pool=None):
    cov, se, ndias = cobertura_clusterizada(fecha, y <= U)
    finito = np.isfinite(U)
    pct_inf = 100 * (~finito).mean()
    ancho = float(U[finito].mean()) if finito.any() else np.nan
    return dict(metodo=metodo, periodo=periodo, cobertura=round(100 * cov, 1),
                se_cluster=round(100 * se, 2) if pd.notna(se) else np.nan,
                ancho_medio=round(ancho, 1) if pd.notna(ancho) else np.nan,
                pct_infinito=round(pct_inf, 1), n_dias=ndias, n=len(y))


def filas_por_periodo(metodo, fecha, y, U):
    """Parte (fecha,y,U) en los periodos de PERIODOS y arma una fila por
    cada periodo presente."""
    per = pd.Series(fecha).apply(etiquetar_periodo).values
    filas = []
    for nombre, _, _ in PERIODOS:
        m = per == nombre
        if m.sum() == 0:
            continue
        filas.append(fila_metrica(metodo, nombre, fecha[m], y[m], U[m]))
    return filas


# =====================================================================
# MAIN
# =====================================================================
def main():
    print("=" * 78)
    print("PROTOTIPO CONFORMAL v2 - DATOS SINTETICOS (no son resultados reales)")
    print("Diseno: Kerven Cea. Panel: mismo generador y semilla que v1.")
    print("=" * 78)

    print("\n" + "-" * 78)
    print("TEST NUMERICO: inversion del score PIT (verificacion previa al resto)")
    print("-" * 78)
    test_inversion_pit()

    # ---- mismo panel, mismo split de train/calib que v1 (comparabilidad)
    df = cp.generar_panel()
    tr = df[df.fecha < '2024-01-01']
    cal = df[(df.fecha >= '2024-01-01') & (df.fecha < '2024-09-01')]
    m = cp.Hurdle().fit(tr[cp.FEATS].values, tr.y.values)
    print(f"Panel: {len(df):,} filas | train {len(tr):,} | calib {len(cal):,} "
          f"| sigma hurdle = {m.sigma:.3f}")

    # splits de evaluacion CORREGIDOS (test_pre ya no incluye la ventana de transicion)
    ev = df[df.fecha >= '2024-09-01'].copy()
    ev = ev[ev.fecha < '2026-06-01']
    ev['periodo'] = ev.fecha.apply(etiquetar_periodo)
    ev = ev[ev.periodo.notna()].reset_index(drop=True)
    for nombre, ini, fin in PERIODOS:
        n = (ev.periodo == nombre).sum()
        print(f"  {nombre:10s} {n:7,} filas  [{ini.date()}, {fin.date()})")

    X_cal = cal[cp.FEATS].values
    y_cal = cal.y.values
    fecha_cal = cal.fecha.values

    filas_tabla = []

    # =================================================================
    # (a) conformal split estatico, score aditivo -- referencia (=v1)
    # =================================================================
    print("\n" + "-" * 78)
    print("(a) Conformal split estatico, score ADITIVO (referencia v1)")
    print("-" * 78)
    U_cal_add = m.upper(X_cal, ALPHA)
    s_add_cal = y_cal - U_cal_add
    qhat_add = cp.q_conformal(s_add_cal, ALPHA)
    print(f"qhat aditivo = {qhat_add:+.1f} MWh")
    U_add = np.maximum(0, m.upper(ev[cp.FEATS].values, ALPHA) + qhat_add)
    filas_tabla += filas_por_periodo('a_estatico_aditivo', ev.fecha.values, ev.y.values, U_add)
    serie_a = U_add.copy()

    # =================================================================
    # (b) conformal split estatico, score PIT
    # =================================================================
    print("\n" + "-" * 78)
    print("(b) Conformal split estatico, score PIT (recomendacion central)")
    print("-" * 78)
    s_pit_cal = pit_score(m, X_cal, y_cal, RNG2)
    qhat_pit = cp.q_conformal(s_pit_cal, ALPHA)
    print(f"qhat PIT = {qhat_pit:.4f}  (escala [0,1], vs {qhat_add:+.1f} MWh del aditivo)")
    U_pit = pit_upper(m, ev[cp.FEATS].values, qhat_pit)
    filas_tabla += filas_por_periodo('b_estatico_pit', ev.fecha.values, ev.y.values, U_pit)
    serie_b = U_pit.copy()

    # =================================================================
    # (c) weighted conformal POR-PUNTO (Tibshirani 2019 correcto)
    #     un clasificador calib-vs-objetivo por cada periodo objetivo,
    #     score PIT (ver nota en el resumen de hallazgos sobre la
    #     eleccion de score aqui vs. el aditivo del audit original).
    # =================================================================
    print("\n" + "-" * 78)
    print("(c) Weighted conformal POR-PUNTO (negative result)")
    print("-" * 78)
    objetivos_c = [(nombre, ev[ev.periodo == nombre]) for nombre, _, _ in PERIODOS]
    objetivos_c.append(('post_total', ev[ev.fecha >= '2025-01-01']))
    for nombre, d in objetivos_c:
        if len(d) == 0:
            continue
        w_cal = cp.pesos_shift(X_cal, d[cp.FEATS].values)
        clf = LogisticRegression(max_iter=2000).fit(
            np.vstack([X_cal, d[cp.FEATS].values]),
            np.r_[np.zeros(len(X_cal)), np.ones(len(d))])
        ratio = len(X_cal) / len(d)
        pr_t = np.clip(clf.predict_proba(d[cp.FEATS].values)[:, 1], 1e-4, 1 - 1e-4)
        w_test = (pr_t / (1 - pr_t)) * ratio
        q_pp = q_ponderado(s_pit_cal, w_cal, w_test, ALPHA)
        U_pp = pit_upper(m, d[cp.FEATS].values, q_pp)
        ess = (w_cal.sum() ** 2 / np.sum(w_cal ** 2))
        fila = fila_metrica('c_weighted_por_punto', nombre, d.fecha.values, d.y.values, U_pp)
        fila['ess_calib'] = round(ess, 0)
        filas_tabla.append(fila)
        print(f"  {nombre:10s} ESS={ess:6.0f}/{len(w_cal):,}  "
              f"%infinito={fila['pct_infinito']:5.1f}%  cobertura={fila['cobertura']:5.1f}%")

    # =================================================================
    # (d) pesos de recencia fijos (Barber et al. 2023), sin clasificador
    #     w_i = decay ** (fecha_ref - fecha_calib_i).dias ; w_test = 1
    #     (fijo, no depende de x: no hay covariate shift, solo tiempo)
    #     calculado por CADA fecha de evaluacion (continuo, sin ventanas)
    # =================================================================
    print("\n" + "-" * 78)
    print("(d) Pesos de recencia fijos (Barber, Candes, Ramdas, Tibshirani 2023)")
    print("-" * 78)
    dias_cal = (fecha_cal.astype('datetime64[D]')).astype(float)
    fechas_unicas = np.sort(ev.fecha.unique())
    for hl in (30, 90, 180):
        decay = 0.5 ** (1.0 / hl)
        # un cuantil ponderado por fecha unica de evaluacion (no por fila:
        # el peso solo depende de (fecha_ref - fecha_calib), no de x)
        q_por_fecha = {}
        for f in fechas_unicas:
            dias = (f.astype('datetime64[D]').astype(float)) - dias_cal
            w = decay ** np.clip(dias, 0, None)
            q_por_fecha[f] = q_ponderado(s_pit_cal, w, 1.0, ALPHA)
        q_vec = np.array([q_por_fecha[f] for f in ev.fecha.values])
        U_rec = pit_upper(m, ev[cp.FEATS].values, q_vec)
        filas_tabla += filas_por_periodo(f'd_recencia_hl{hl}', ev.fecha.values, ev.y.values, U_rec)
        if hl == 90:
            serie_d90 = U_rec.copy()
        print(f"  semivida {hl:3d} dias: listo ({len(fechas_unicas)} fechas evaluadas)")

    # =================================================================
    # (e) ventana deslizante 60 dias, recalibrada cada 7, aditivo y PIT
    # =================================================================
    print("\n" + "-" * 78)
    print("(e) Ventana deslizante 60 dias / refresco 7 dias (resultado positivo del audit)")
    print("-" * 78)
    refrescos = pd.date_range('2024-09-01', '2026-05-31', freq='7D')
    for score_tipo in ('aditivo', 'pit'):
        U_vent = np.full(len(ev), np.nan)
        for t0 in refrescos:
            t1 = t0 + pd.Timedelta(days=7)
            win = df[(df.fecha >= t0 - pd.Timedelta(days=60)) & (df.fecha < t0)]
            obj = (ev.fecha >= t0) & (ev.fecha < t1)
            if obj.sum() == 0 or len(win) == 0:
                continue
            Xw = win[cp.FEATS].values
            if score_tipo == 'aditivo':
                s_w = win.y.values - m.upper(Xw, ALPHA)
                q_w = cp.q_conformal(s_w, ALPHA)
                U_vent[obj.values] = np.maximum(
                    0, m.upper(ev.loc[obj, cp.FEATS].values, ALPHA) + q_w)
            else:
                s_w = pit_score(m, Xw, win.y.values, RNG2)
                q_w = cp.q_conformal(s_w, ALPHA)
                U_vent[obj.values] = pit_upper(m, ev.loc[obj, cp.FEATS].values, q_w)
        filas_tabla += filas_por_periodo(f'e_ventana60d_{score_tipo}', ev.fecha.values,
                                         ev.y.values, U_vent)
        if score_tipo == 'pit':
            serie_e_pit = U_vent.copy()
        print(f"  score {score_tipo}: listo ({len(refrescos)} refrescos)")

    # =================================================================
    # (f) ACI (Gibbs & Candes 2021) sobre score PIT, pool estatico de
    #     calibracion, alpha_t se actualiza cada dia con la cobertura
    #     observada ese dia (agregada entre centrales)
    # =================================================================
    print("\n" + "-" * 78)
    print("(f) ACI (Gibbs & Candes 2021), score PIT, pool estatico")
    print("-" * 78)
    s_pool_sorted = np.sort(s_pit_cal)
    n_pool = len(s_pool_sorted)

    def q_aci(alpha_t):
        if alpha_t <= 0:
            return np.inf
        if alpha_t >= 1:
            return -np.inf
        k = int(np.ceil((n_pool + 1) * (1 - alpha_t)))
        return s_pool_sorted[k - 1] if k <= n_pool else np.inf

    for gamma in (0.005, 0.02, 0.05):
        alpha_t = ALPHA
        U_aci = np.empty(len(ev))
        alphas_hist = []
        for f in fechas_unicas:
            mask = (ev.fecha.values == f)
            q_t = q_aci(alpha_t)
            U_t = pit_upper(m, ev.loc[mask, cp.FEATS].values, q_t)
            U_aci[mask] = U_t
            err_t = 1 - (ev.loc[mask, 'y'].values <= U_t).mean()
            alphas_hist.append(alpha_t)
            alpha_t = np.clip(alpha_t + gamma * (ALPHA - err_t), -1.0, 2.0)
        filas_tabla += filas_por_periodo(f'f_aci_pit_g{str(gamma).replace("0.", "")}',
                                         ev.fecha.values, ev.y.values, U_aci)
        print(f"  gamma={gamma:.3f}: alpha_t final={alpha_t:.4f}  "
              f"(rango observado [{min(alphas_hist):.3f}, {max(alphas_hist):.3f}])")
        if abs(gamma - 0.02) < 1e-9:
            serie_f_g02 = U_aci.copy()

    # =================================================================
    # (g) transporte de scores + ACI (propuesta teorica de Kerven)
    #     mapa T semanal (ventana nueva = 60 dias trailing), scores
    #     viejos = pool de calibracion completo; ACI diario sobre el
    #     pool TRANSPORTADO vigente esa semana.
    # =================================================================
    print("\n" + "-" * 78)
    print("(g) Transporte de scores (mapa monotono 1D) + ACI")
    print("-" * 78)
    for gamma in (0.02, 0.05):
        alpha_t = ALPHA
        U_tr = np.empty(len(ev))
        pool_actual = s_pit_cal
        prox_refresco = pd.Timestamp('2024-09-01')
        for f in fechas_unicas:
            f_ts = pd.Timestamp(f)
            if f_ts >= prox_refresco:
                nueva = df[(df.fecha >= f_ts - pd.Timedelta(days=60)) & (df.fecha < f_ts)]
                if len(nueva) >= 100:
                    s_nueva = pit_score(m, nueva[cp.FEATS].values, nueva.y.values, RNG2)
                    T = mapa_transporte(s_pit_cal, s_nueva)
                    pool_actual = np.sort(T(s_pit_cal))
                prox_refresco = f_ts + pd.Timedelta(days=7)
            mask = (ev.fecha.values == f)
            n_p = len(pool_actual)
            if alpha_t <= 0:
                q_t = np.inf
            elif alpha_t >= 1:
                q_t = -np.inf
            else:
                k = int(np.ceil((n_p + 1) * (1 - alpha_t)))
                q_t = pool_actual[k - 1] if k <= n_p else np.inf
            U_t = pit_upper(m, ev.loc[mask, cp.FEATS].values, q_t)
            U_tr[mask] = U_t
            err_t = 1 - (ev.loc[mask, 'y'].values <= U_t).mean()
            alpha_t = np.clip(alpha_t + gamma * (ALPHA - err_t), -1.0, 2.0)
        filas_tabla += filas_por_periodo(f'g_transporte_aci_g{str(gamma).replace("0.", "")}',
                                         ev.fecha.values, ev.y.values, U_tr)
        print(f"  gamma={gamma:.3f}: alpha_t final={alpha_t:.4f}")
        if abs(gamma - 0.02) < 1e-9:
            serie_g_g02 = U_tr.copy()

    # =================================================================
    # TABLA UNICA
    # =================================================================
    tabla = pd.DataFrame(filas_tabla)
    orden_periodo = {n: i for i, (n, _, _) in enumerate(PERIODOS)}
    orden_periodo['post_total'] = len(PERIODOS)
    tabla['orden'] = tabla.periodo.map(orden_periodo)
    tabla = tabla.sort_values(['metodo', 'orden']).drop(columns='orden')
    cols = ['metodo', 'periodo', 'cobertura', 'se_cluster', 'ancho_medio',
            'pct_infinito', 'n_dias', 'n']
    if 'ess_calib' in tabla.columns:
        cols.append('ess_calib')
    print("\n" + "=" * 78)
    print("TABLA UNICA: metodo x periodo")
    print("(cobertura y se_cluster en %; ancho_medio en MWh sobre intervalos finitos;")
    print(" se_cluster = error estandar de la cobertura diaria promediada por fecha)")
    print("=" * 78)
    print(tabla[cols].to_string(index=False))

    # =================================================================
    # CRPS del modelo base (propiedad del hurdle, NO varia por metodo
    # conformal: el conformal solo recorta la cola superior)
    # =================================================================
    print("\n" + "-" * 78)
    print("CRPS del modelo base por periodo (no varia por metodo conformal)")
    print("-" * 78)
    for nombre, _, _ in PERIODOS:
        d = ev[ev.periodo == nombre]
        if len(d) == 0:
            continue
        c = cp.crps(m.sample(d[cp.FEATS].values), d.y.values)
        print(f"  {nombre:10s} CRPS = {c:7.2f} MWh  (n={len(d):,})")

    # =================================================================
    # FIGURA: cobertura rodante (90 dias) de los metodos clave
    # =================================================================
    print("\n" + "-" * 78)
    print("Figura: cobertura rodante 90 dias")
    print("-" * 78)
    graficar_cobertura_rodante(ev, {
        'a. Estatico aditivo (v1)': serie_a,
        'b. Estatico PIT': serie_b,
        'e. Ventana 60d PIT': serie_e_pit,
        'f. ACI PIT (gamma=0.02)': serie_f_g02,
        'g. Transporte + ACI (gamma=0.02)': serie_g_g02,
    })

    tabla[cols].to_csv(FLAGSHIP / 'conformal_v2_tabla.csv', index=False)
    print(f"\nTabla tambien guardada en {FLAGSHIP / 'conformal_v2_tabla.csv'}")
    print("\n" + "=" * 78)


def graficar_cobertura_rodante(ev, series_dict, ventana=90):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fechas = pd.to_datetime(ev.fecha.values)
    y = ev.y.values
    base = pd.DataFrame({'fecha': fechas, 'y': y})

    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    colores = ['#4c72b0', '#8172b2', '#55a868', '#c44e52', '#dd8452']
    for (nombre, U), color in zip(series_dict.items(), colores):
        d = base.copy()
        d['cubierto'] = (y <= U).astype(float)
        por_dia = d.groupby('fecha').cubierto.mean().reindex(
            pd.date_range(fechas.min(), fechas.max(), freq='D'))
        rodante = 100 * por_dia.rolling(ventana, min_periods=int(ventana * 0.6)).mean()
        ax.plot(rodante.index, rodante.values, label=nombre, color=color, linewidth=1.6)

    ax.axhline(90, color='#666666', linewidth=1, linestyle=':', zorder=0)
    ax.axvline(pd.Timestamp('2024-10-01'), color='#999999', linewidth=1, linestyle='--', zorder=0)
    ax.text(pd.Timestamp('2024-10-10'), 98, 'inicio ventana de transicion', fontsize=8,
            color='#999999', va='top', ha='left')

    ax.set_ylim(55, 101)
    ax.set_xlabel('Fecha')
    ax.set_ylabel('Cobertura rodante 90 dias (%)')
    ax.set_title('Cobertura rodante bajo el quiebre de regimen (datos sinteticos, no reales)')
    ax.legend(loc='lower left', fontsize=8, framealpha=0.9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()

    fig.savefig(FLAGSHIP / 'conformal_v2_cobertura_rodante.pdf')
    fig.savefig(FLAGSHIP / 'conformal_v2_cobertura_rodante.png')
    plt.close(fig)
    print(f"  guardado {FLAGSHIP / 'conformal_v2_cobertura_rodante.pdf'} y .png")


if __name__ == '__main__':
    main()
