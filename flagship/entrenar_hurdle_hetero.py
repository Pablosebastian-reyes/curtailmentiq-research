#!/usr/bin/env python3
"""
MODELO BASE HETEROCEDASTICO: sigma(x) condicional para el hurdle
================================================================
Mejora del modelo base del flagship. El hurdle actual usa una dispersion
constante (sigma = 1.70, out-of-fold) para toda prediccion positiva; el
experimento real mostro que el ancho de los intervalos esta dominado por esa
constante, no por la capa conformal. Aqui se estima sigma(x) condicional para
bajar el techo de sharpness.

Disciplina de split (identica a entrenar_baselines.py, no negociable):
  sigma(x) se estima SOLO con datos hasta 2023-12-31, out-of-fold (5-fold en
  train). Jamas ve 2024-2026. Las predicciones cubren 2024-01-01 a 2026-05-31
  con las mismas claves (fecha, central) que pred_hurdle.csv.

Modelo (dos etapas):
  Etapa 1 (SIN cambios, se reutiliza entrenar_baselines): clasificador de
  ocurrencia p_occ y regresor mu(x) sobre log-magnitud de los positivos.
  Etapa 2 (nueva): un GBM que predice la dispersion. Target = log de los
  residuos out-of-fold de la etapa 1 al cuadrado. sigma_raw(x) = exp(pred/2).
  Una escala global c calibra la dispersion media (E[(r/sigma)^2] = 1 en OOF
  de train, absorbe el sesgo de Jensen sin suponer normalidad). Se aplica un
  piso positivo a sigma(x) para evitar overconfidence.

Este script NO aplica conformal ni intervalos (eso es de Kerven). El PIT y el
cuantil superior que se calculan aca son solo DIAGNOSTICOS del modelo base.

NO toca la etapa 1 (mu) ni el clasificador; no usa datos 2024-2026 para
estimar sigma(x); no incluye hidro.
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm, kstest
from sklearn.model_selection import KFold
from xgboost import XGBClassifier, XGBRegressor

FLAGSHIP = Path(__file__).resolve().parent
sys.path.insert(0, str(FLAGSHIP))
import entrenar_baselines as eb  # noqa: E402  (reutiliza panel, features y params de la etapa 1)

SEED = eb.SEED
RNG = np.random.default_rng(SEED)
SALIDA = eb.SALIDA
GARCH_W = 60          # ventana en dias del feature de volatilidad tipo GARCH
GARCH_MINOBS = 5      # minimo de observaciones positivas para definir la volatilidad
PISO_PCT = 0.05       # el piso de sigma(x) es el percentil 5 de sigma(x) en train

# Features de la etapa 2 (dispersion). p_occ entra como feature (out-of-fold en
# train, prediccion del clasificador completo en 2024-2026).
SIG_FEATS = ['log_potencia_mw', 'tecnologia', 'doy_target', 'p_occ_feat', 'vol_garch']


def construir_largo():
    """Panel y features de la etapa 1 (via entrenar_baselines) mas el feature
    de volatilidad tipo GARCH. Todo con shift >= 7 (cero fuga)."""
    piv, estat = eb.construir_panel()
    largo = eb.construir_features(piv)

    # Volatilidad tipo GARCH: desviacion estandar de la log-magnitud de los
    # dias POSITIVOS de la misma central en una ventana trailing, con el mismo
    # desfase H que el resto (usa solo pasado respecto del origen t = T - H).
    logpos = np.log(piv.where(piv > 0))
    vol = logpos.shift(eb.H).rolling(f'{GARCH_W}D', min_periods=GARCH_MINOBS).std()
    vol_long = vol.stack(future_stack=True).rename('vol_garch').reset_index()
    vol_long.columns = ['fecha', 'central_codigo', 'vol_garch']
    largo = largo.merge(vol_long, on=['fecha', 'central_codigo'], how='left')

    largo = largo.merge(estat[['central_codigo', 'tecnologia', 'region',
                               'log_potencia_mw', 'potencia_mw']],
                        on='central_codigo')
    for c in ('region', 'tecnologia'):
        largo[c] = pd.Categorical(largo[c], categories=sorted(largo[c].unique()))
    return largo


def etapa1(df_tr, df_pr):
    """Reproduce EXACTAMENTE la etapa 1 de entrenar_baselines (clasificador y
    mu). Devuelve p_occ y mu en prediccion, los residuos OOF de mu en train y
    el p_occ OOF en train. Se verifica contra pred_hurdle.csv."""
    X_tr, y_tr = df_tr[eb.FEATS], df_tr.y_real.values
    X_pr = df_pr[eb.FEATS]

    clf = XGBClassifier(objective='binary:logistic', eval_metric='logloss', **eb.XGB_PARAMS)
    clf.fit(X_tr, (y_tr > 0).astype(int))
    p_occ_pr = clf.predict_proba(X_pr)[:, 1]

    pos = y_tr > 0
    X_pos, ylog_pos = X_tr[pos], np.log(y_tr[pos])
    reg_m = XGBRegressor(objective='reg:squarederror', **eb.XGB_PARAMS)
    reg_m.fit(X_pos, ylog_pos)
    mu_pr = reg_m.predict(X_pr)

    # OOF de mu sobre los positivos de train (mismos folds que la sigma
    # constante de entrenar_baselines): residuos honestos para la etapa 2.
    kf = KFold(5, shuffle=True, random_state=SEED)
    mu_oof = np.full(pos.sum(), np.nan)
    for itr, ite in kf.split(X_pos):
        rf = XGBRegressor(objective='reg:squarederror', **eb.XGB_PARAMS)
        rf.fit(X_pos.iloc[itr], ylog_pos[itr])
        mu_oof[ite] = rf.predict(X_pos.iloc[ite])
    resid_oof = ylog_pos - mu_oof
    sigma_const = float(np.std(resid_oof, ddof=1))

    # OOF de p_occ sobre TODO train (feature de la etapa 2 sin fuga de label).
    p_oof = np.full(len(X_tr), np.nan)
    for itr, ite in kf.split(X_tr):
        cf = XGBClassifier(objective='binary:logistic', eval_metric='logloss', **eb.XGB_PARAMS)
        cf.fit(X_tr.iloc[itr], (y_tr[itr] > 0).astype(int))
        p_oof[ite] = cf.predict_proba(X_tr.iloc[ite])[:, 1]

    return dict(p_occ_pr=p_occ_pr, mu_pr=mu_pr, pos=pos, X_pos=X_pos,
                resid_oof=resid_oof, sigma_const=sigma_const,
                p_oof_pos=p_oof[pos.values if hasattr(pos, 'values') else pos],
                clf=clf)


def etapa2(df_tr, df_pr, e1):
    """GBM de dispersion. Target = log(resid_oof^2). sigma_raw = exp(pred/2),
    escalado por c para que E[(r/sigma)^2] = 1 en OOF de train, con piso."""
    pos = e1['pos']
    # matriz de features de sigma en train (positivos) y en prediccion
    Xsig_tr = df_tr[pos].copy()
    Xsig_tr['p_occ_feat'] = e1['p_oof_pos']          # p_occ OOF en train
    Xsig_pr = df_pr.copy()
    Xsig_pr['p_occ_feat'] = e1['p_occ_pr']           # p_occ del clasificador completo
    Xtr = Xsig_tr[SIG_FEATS]
    Xpr = Xsig_pr[SIG_FEATS]

    t2 = np.log(e1['resid_oof'] ** 2 + 1e-6)         # target de dispersion

    # OOF de la etapa 2 para calibrar la escala c sin optimismo in-sample
    kf = KFold(5, shuffle=True, random_state=SEED)
    pred2_oof = np.full(len(Xtr), np.nan)
    for itr, ite in kf.split(Xtr):
        g = XGBRegressor(objective='reg:squarederror', **eb.XGB_PARAMS)
        g.fit(Xtr.iloc[itr], t2[itr])
        pred2_oof[ite] = g.predict(Xtr.iloc[ite])
    sigma_raw_oof = np.exp(pred2_oof / 2)
    c = float(np.sqrt(np.mean(e1['resid_oof'] ** 2 / sigma_raw_oof ** 2)))

    # modelo completo de la etapa 2
    g_full = XGBRegressor(objective='reg:squarederror', **eb.XGB_PARAMS)
    g_full.fit(Xtr, t2)
    sigma_x_tr = c * np.exp(g_full.predict(Xtr) / 2)
    piso = float(np.quantile(sigma_x_tr, PISO_PCT))  # piso desde train, sin fuga

    sigma_raw_pr = np.exp(g_full.predict(Xpr) / 2)
    sigma_x_pr = np.maximum(c * sigma_raw_pr, piso)
    frac_piso = float((c * sigma_raw_pr < piso).mean())

    # sigma(x) OOF sobre los positivos de train (para el PIT condicional en
    # train, sin quiebre de regimen): es la dispersion que sigma(x) predeciria
    # in-distribution.
    sigma_x_oof = np.maximum(c * sigma_raw_oof, piso)

    return dict(sigma_x_pr=sigma_x_pr, sigma_x_tr=np.maximum(sigma_x_tr, piso),
                sigma_x_oof=sigma_x_oof, c=c, piso=piso, frac_piso=frac_piso,
                g_full=g_full, Xpr=Xpr)


# ---- diagnosticos del modelo base (PIT, cuantil, CRPS, NLL); NO son conformal
def pit_crudo(p, mu, sigma, y, u):
    z = (np.log(np.maximum(y, 1.0)) - mu) / sigma
    Fpos = (1 - p) + p * norm.cdf(z)
    return np.where(y > 0, Fpos, (1 - p) * u)


def q_upper_modelo(p, mu, sigma, nivel):
    arg = np.clip((nivel - (1 - p)) / p, 0.0, 1.0)
    with np.errstate(divide='ignore'):
        return np.exp(mu + sigma * norm.ppf(arg))


def muestrear(p, mu, sigma, rng, n=300):
    sig = np.asarray(sigma, float).reshape(-1, 1)
    occ = rng.random((len(p), n)) < np.asarray(p)[:, None]
    mag = np.exp(np.asarray(mu)[:, None] + sig * rng.standard_normal((len(p), n)))
    return np.where(occ, mag, 0.0)


def crps(muestras, y, rng):
    a = np.abs(muestras - np.asarray(y)[:, None]).mean(1)
    idx = rng.permutation(muestras.shape[1])
    b = 0.5 * np.abs(muestras - muestras[:, idx]).mean(1)
    return float((a - b).mean())


def nll(p, mu, sigma, y):
    """Log-score (NLL) de la mezcla (1-p)*delta_0 + p*LogNormal(mu, sigma)."""
    out = np.where(y > 0,
                   -np.log(p) + np.log(np.maximum(y, 1e-12)) + np.log(sigma)
                   + 0.5 * np.log(2 * np.pi)
                   + (np.log(np.maximum(y, 1e-12)) - mu) ** 2 / (2 * sigma ** 2),
                   -np.log(1 - p))
    return float(np.mean(out))


def main():
    print("=" * 78)
    print("MODELO BASE HETEROCEDASTICO sigma(x) - dataset v1.0 (solar y eolica)")
    print("Disciplina de split identica a entrenar_baselines. NO aplica conformal.")
    print("=" * 78)

    largo = construir_largo()
    comun = largo.y_real.notna() & largo.mwh_t.notna()
    df_tr = largo[comun & (largo.fecha <= eb.CORTE_TRAIN)].reset_index(drop=True)
    df_pr = largo[comun & (largo.fecha >= eb.PRED_INI)
                  & (largo.fecha <= eb.PRED_FIN)].reset_index(drop=True)
    print(f"\nTrain: {len(df_tr):,} filas (target <= {eb.CORTE_TRAIN.date()}) | "
          f"prediccion: {len(df_pr):,} filas ({eb.PRED_INI.date()} a {eb.PRED_FIN.date()})")
    print(f"Cobertura del feature vol_garch en prediccion: "
          f"{100*df_pr.vol_garch.notna().mean():.1f}% de filas (NaN lo maneja XGBoost)")

    e1 = etapa1(df_tr, df_pr)
    sigma_const = e1['sigma_const']

    # --- verificacion de identidad con pred_hurdle.csv (etapa 1 intacta)
    ref = pd.read_csv(SALIDA / 'pred_hurdle.csv', parse_dates=['fecha'])
    ref = ref.sort_values(['fecha', 'central_codigo']).reset_index(drop=True)
    key = df_pr[['fecha', 'central_codigo']].copy()
    key['fecha'] = key.fecha.dt.normalize()
    cur = key.assign(p_occ=e1['p_occ_pr'], mu_log=e1['mu_pr']).sort_values(
        ['fecha', 'central_codigo']).reset_index(drop=True)
    d_p = np.abs(cur.p_occ.values - ref.p_occ.values).max()
    d_mu = np.abs(cur.mu_log.values - ref.mu_log.values).max()
    print(f"\nVerificacion etapa 1 vs pred_hurdle.csv: max|dp_occ|={d_p:.2e} "
          f"max|dmu_log|={d_mu:.2e} | sigma_const={sigma_const:.4f} (ref 1.7016)")
    assert d_p < 1e-6 and d_mu < 1e-4, "la etapa 1 no reproduce pred_hurdle.csv"

    e2 = etapa2(df_tr, df_pr, e1)
    sigma_x = e2['sigma_x_pr']
    print(f"\nEtapa 2 (sigma(x)): escala c={e2['c']:.4f}  piso={e2['piso']:.4f} "
          f"(percentil {int(100*PISO_PCT)} de train, clipa {100*e2['frac_piso']:.1f}% de prediccion)")
    print(f"sigma(x) en prediccion: min={sigma_x.min():.3f} p10={np.quantile(sigma_x,.1):.3f} "
          f"mediana={np.median(sigma_x):.3f} p90={np.quantile(sigma_x,.9):.3f} "
          f"max={sigma_x.max():.3f}  (constante = {sigma_const:.3f})")

    # =================================================================
    # SALIDA: pred_hurdle_hetero.csv (mismas claves que pred_hurdle.csv)
    # =================================================================
    out = df_pr[['fecha', 'central_codigo', 'tecnologia', 'y_real']].copy()
    out['fecha'] = out.fecha.dt.date
    out['p_occ'] = e1['p_occ_pr']
    out['mu_log'] = e1['mu_pr']
    out['sigma_x'] = sigma_x
    out.to_csv(SALIDA / 'pred_hurdle_hetero.csv', index=False, float_format='%.6f')
    print(f"\nEscrito {SALIDA / 'pred_hurdle_hetero.csv'} ({len(out):,} filas)")

    # =================================================================
    # REPORTE DESCRIPTIVO (sin conclusiones)
    # =================================================================
    p, mu, y = e1['p_occ_pr'], e1['mu_pr'], df_pr.y_real.values

    print("\n" + "-" * 78)
    print("1. Importancia de features de sigma(x) (etapa 2, ganancia normalizada)")
    print("-" * 78)
    booster = e2['g_full'].get_booster()
    gain = booster.get_score(importance_type='gain')
    tot = sum(gain.values()) or 1.0
    for f in SIG_FEATS:
        g = gain.get(f, 0.0)
        print(f"  {f:16s} {100*g/tot:5.1f}%")

    print("\n" + "-" * 78)
    print("2. Diagnostico PIT crudo (antes de conformal): distancia KS a la uniforme")
    print("-" * 78)
    u = RNG.random(len(y))  # aleatorizacion del atomo COMUN a ambos modelos
    pit_c = pit_crudo(p, mu, sigma_const, y, u)
    pit_x = pit_crudo(p, mu, sigma_x, y, u)
    ks_c = kstest(pit_c, 'uniform').statistic
    ks_x = kstest(pit_x, 'uniform').statistic
    print(f"  sigma constante : KS = {ks_c:.4f}")
    print(f"  sigma(x)        : KS = {ks_x:.4f}   (menor es mas plano, mejor calibrado)")

    print("\n" + "-" * 78)
    print("2b. PIT condicional sobre positivos, Phi((log y - mu)/sigma): aisla la")
    print("    dispersion. Compara train (OOF, SIN quiebre) vs OOS (CON quiebre).")
    print("-" * 78)
    resid_oof = e1['resid_oof']                          # log y - mu_oof en train positivos
    pit_tr_c = norm.cdf(resid_oof / sigma_const)
    pit_tr_x = norm.cdf(resid_oof / e2['sigma_x_oof'])
    pos_oos = y > 0
    resid_oos = np.log(np.maximum(y[pos_oos], 1e-12)) - mu[pos_oos]
    pit_oos_c = norm.cdf(resid_oos / sigma_const)
    pit_oos_x = norm.cdf(resid_oos / sigma_x[pos_oos])
    print(f"  {'':24s} {'KS_const':>9s} {'KS_sig(x)':>10s}")
    print(f"  train OOF (sin quiebre)  {kstest(pit_tr_c,'uniform').statistic:9.4f} "
          f"{kstest(pit_tr_x,'uniform').statistic:10.4f}")
    print(f"  OOS 2024-2026 (quiebre)  {kstest(pit_oos_c,'uniform').statistic:9.4f} "
          f"{kstest(pit_oos_x,'uniform').statistic:10.4f}")

    print("\n" + "-" * 78)
    print("3. Metricas de la predictiva base (menor es mejor), OOS 2024-2026")
    print("-" * 78)
    rng_m = np.random.default_rng(11)
    crps_c = crps(muestrear(p, mu, np.full(len(p), sigma_const), rng_m), y, rng_m)
    rng_m = np.random.default_rng(11)
    crps_x = crps(muestrear(p, mu, sigma_x, rng_m), y, rng_m)
    nll_c = nll(p, mu, sigma_const, y)
    nll_x = nll(p, mu, sigma_x, y)
    print(f"  {'':16s}   CRPS (MWh)    NLL (log-score)")
    print(f"  sigma constante   {crps_c:10.2f}    {nll_c:10.4f}")
    print(f"  sigma(x)          {crps_x:10.2f}    {nll_x:10.4f}")

    print("\n" + "-" * 78)
    print("4. Robustez por tercil de tamano de central (potencia_mw)")
    print("   KS del PIT y cobertura del cuantil 90% propio del modelo (nominal 90)")
    print("-" * 78)
    ter = pd.qcut(df_pr.potencia_mw, 3, labels=['chica', 'media', 'grande'])
    U90_c = q_upper_modelo(p, mu, sigma_const, 0.90)
    U90_x = q_upper_modelo(p, mu, sigma_x, 0.90)
    print(f"  {'tercil':8s} {'n':>7s} {'KS_const':>9s} {'KS_sig(x)':>10s} "
          f"{'cob90_const':>12s} {'cob90_sig(x)':>13s}")
    for t in ['chica', 'media', 'grande']:
        m = (ter == t).values
        ks_tc = kstest(pit_c[m], 'uniform').statistic
        ks_tx = kstest(pit_x[m], 'uniform').statistic
        cob_c = 100 * (y[m] <= U90_c[m]).mean()
        cob_x = 100 * (y[m] <= U90_x[m]).mean()
        print(f"  {t:8s} {m.sum():7,} {ks_tc:9.4f} {ks_tx:10.4f} "
              f"{cob_c:11.1f}% {cob_x:12.1f}%")

    graficar_pit(pit_c, pit_x, ks_c, ks_x)
    actualizar_readme(len(df_tr), len(df_pr), sigma_const, e2, ks_c, ks_x,
                      crps_c, crps_x, nll_c, nll_x)
    print("\n" + "=" * 78)


def graficar_pit(pit_c, pit_x, ks_c, ks_x):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), dpi=150, sharey=True)
    for ax, pit, ks, tit in [(axes[0], pit_c, ks_c, 'sigma constante'),
                             (axes[1], pit_x, ks_x, 'sigma(x) heterocedastico')]:
        ax.hist(pit, bins=20, range=(0, 1), color='#4c72b0',
                edgecolor='white', density=True)
        ax.axhline(1.0, color='#c44e52', linewidth=1, linestyle='--', zorder=3)
        ax.set_title(f'{tit}\nKS a uniforme = {ks:.4f}', fontsize=10)
        ax.set_xlabel('PIT crudo del hurdle')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    axes[0].set_ylabel('densidad')
    fig.suptitle('Histograma PIT del modelo base (datos reales 2024-2026, sin conformal)',
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(FLAGSHIP / 'hurdle_hetero_pit.pdf')
    fig.savefig(FLAGSHIP / 'hurdle_hetero_pit.png')
    plt.close(fig)
    print(f"\n  guardado hurdle_hetero_pit.pdf y .png")


def actualizar_readme(n_tr, n_pr, sigma_const, e2, ks_c, ks_x, crps_c, crps_x, nll_c, nll_x):
    readme = SALIDA / 'README.md'
    marca = '## Modelo base heterocedastico'
    texto = f"""
{marca} (`pred_hurdle_hetero.csv`)

Generado por `flagship/entrenar_hurdle_hetero.py` (seed {SEED}). Reemplaza la
dispersion constante del hurdle (`sigma` = {sigma_const:.4f}) por una
`sigma_x` condicional, para bajar el techo de sharpness. Misma disciplina de
split que el resto: `sigma(x)` se estima solo con datos hasta 2023-12-31,
out-of-fold, y jamas ve 2024-2026. Mismas claves que `pred_hurdle.csv`; el
co-autor enchufa su capa conformal cambiando solo el archivo de entrada
(usa `sigma_x` en vez de `sigma`).

Etapas: la 1 (clasificador `p_occ` y regresor `mu_log`) es identica a
`pred_hurdle.csv` (verificado por asercion). La 2 es un GBM que predice la
dispersion: target = log de los residuos out-of-fold de la etapa 1 al
cuadrado; `sigma_raw(x) = exp(pred/2)`, escala global c = {e2['c']:.4f} para
que `E[(r/sigma)^2] = 1` en OOF de train, y piso {e2['piso']:.4f} (percentil
{int(100*PISO_PCT)} de `sigma(x)` en train; clipa {100*e2['frac_piso']:.1f}%
de las filas de prediccion). Features de `sigma(x)`: `log_potencia_mw`,
`tecnologia`, `doy_target`, `p_occ` (out-of-fold en train), y `vol_garch`
(desviacion estandar de la log-magnitud positiva de la central en {GARCH_W}
dias trailing, con shift >= 7).

Columnas: `fecha`, `central_codigo`, `tecnologia`, `y_real`, `p_occ`,
`mu_log`, `sigma_x`.

Reporte descriptivo (sin conclusiones): KS del PIT crudo a la uniforme
{ks_c:.4f} (constante) contra {ks_x:.4f} (`sigma(x)`); CRPS {crps_c:.2f}
contra {crps_x:.2f} MWh; NLL {nll_c:.4f} contra {nll_x:.4f}. Detalle de
importancia de features y tabla por tercil en
`flagship/entrenar_hurdle_hetero_salida.txt`; histograma PIT en
`flagship/hurdle_hetero_pit.{{pdf,png}}`.
"""
    contenido = readme.read_text() if readme.exists() else ''
    if marca in contenido:
        contenido = contenido.split('\n' + marca)[0].rstrip() + '\n'
    readme.write_text(contenido.rstrip() + '\n' + texto)
    print(f"  seccion agregada a {readme}")


if __name__ == '__main__':
    main()
