# 4. Methods

Contenido previsto (ver `../INDICE_PAPER.md`, seccion 4). Las subsecciones 4.2
a 4.7 y 4.9 estan redactadas en ingles (borrador); 4.1, 4.8 y 4.10 quedan como
andamiaje con su material. Notacion compartida al inicio.

**Shared notation.** For target date $T$ and plant $j$, let $Y \ge 0$ be the
daily curtailed energy and $x$ the feature vector available at the forecast
origin $t = T - 7$ (seven day ahead direct forecast). The base hurdle model
gives an occurrence probability $p(x) = \widehat{\Pr}(Y > 0 \mid x)$ and a
magnitude law $Y \mid Y > 0, x \sim \mathrm{LogNormal}(\mu(x), \sigma)$, so the
predictive is the two part mixture
$F_x(y) = (1 - p(x)) + p(x)\,\Phi((\log y - \mu(x))/\sigma)$ for $y > 0$, with an
atom of mass $1 - p(x)$ at the origin. We report one sided intervals $[0, U(x)]$,
the operational quantity being an upper bound on curtailment. Miscoverage level
is $\alpha$ (nominal coverage $1 - \alpha = 0.9$).

## 4.1 Modelo base hurdle
Ocurrencia (clasificador de P(Y mayor que 0)) mas magnitud lognormal; predictiva de mezcla y su cuantil superior.
- Material: `../conformal_prototype.py` (clase Hurdle, derivacion del cuantil de la mezcla), `../entrenar_baselines.py`, `../AUDIT_METODOLOGICO.md` (punto 1, verificacion del cuantil).

## 4.2 The PIT nonconformity score

We use the probability integral transform (PIT) of the base predictive as the
nonconformity score, following the distributional score of Chernozhukov,
Wuthrich and Zhu (2021). For a pair $(x, y)$,

$$
s(x, y) =
\begin{cases}
(1 - p(x)) + p(x)\,\Phi\!\left(\dfrac{\log y - \mu(x)}{\sigma}\right), & y > 0,\\[2mm]
(1 - p(x))\, V, \quad V \sim \mathrm{Uniform}(0,1), & y = 0.
\end{cases}
$$

The randomization at the atom (Smith, 1985) is required because $F_x$ jumps by
$1 - p(x)$ at the origin; spreading the atom uniformly over $[0, 1 - p(x)]$ makes
$s(x, Y) \sim \mathrm{Uniform}(0,1)$ under the true predictive, despite the
discontinuity. Two properties motivate this score for a zero inflated, heavy
tailed target. First, it is bounded in $[0, 1]$ and therefore homogeneous across
small and large plants, unlike an additive residual score in MWh whose scale is
dominated by the largest plants. Second, conformalizing a PIT score corrects
miscalibration in probability units, which is where a misspecified hurdle errs,
rather than in energy units.

Given a conformal threshold $q \in [0, 1]$ on the score, the interval endpoint is
obtained by inverting the mixture at level $q$:

$$
U(x) =
\begin{cases}
0, & q \le 1 - p(x),\\[1mm]
\exp\!\left(\mu(x) + \sigma\,\Phi^{-1}\!\left(\dfrac{q - (1 - p(x))}{p(x)}\right)\right), & q > 1 - p(x),
\end{cases}
$$

and $U(x) = \infty$ when $q \ge 1$. The first branch encodes that if the mixture
places at least $q$ mass on the atom, the level $q$ upper bound is zero. The
inversion is in closed form and is verified numerically against Monte Carlo draws
from the mixture (Appendix A).

*Sources: `../conformal_metodos.py` (pit_score, pit_upper), `../AUDIT_METODOLOGICO.md` (punto 2).*

## 4.3 Split conformal and finite sample correction

Let $\{(x_i, y_i)\}_{i=1}^{n}$ be a calibration set disjoint from training, with
scores $S_i = s(x_i, y_i)$. The conformal threshold is the order statistic

$$
\hat{q} = S_{(k)}, \qquad k = \lceil (n + 1)(1 - \alpha) \rceil,
$$

with $\hat{q} = \infty$ when $k > n$, the conservative tail convention. Under
exchangeability of the calibration and test scores this yields the finite sample
guarantee $\Pr(Y_{n+1} \le U(X_{n+1})) \ge 1 - \alpha$, with upper bound
$1 - \alpha + 1/(n+1)$ when scores are almost surely distinct, which holds here
because the continuous component of $s$ has no atoms. This static split conformal
predictor is the reference throughout.

*Sources: `../conformal_metodos.py` (q_conformal, q_desde_pool), `../AUDIT_METODOLOGICO.md` (punto 3).*

## 4.4 Dependence and clustered standard errors

Exchangeability is violated in two ways, both inflating the sampling variability
of empirical coverage beyond the independent case. Serially, the system state is
persistent (an AR(1) latent factor, and lagged curtailment enters the features).
Cross sectionally, all plants share the same daily system state, so the
calibration scores arrive in correlated blocks, one per date, and the effective
sample size for coverage fluctuation is of the order of the number of days, not
rows. We therefore cluster all coverage standard errors by date: coverage is
averaged within each day and its standard error is computed across daily
coverages. Reported coverage differences of one to three points between methods
are typically within one clustered standard error and are not overinterpreted.

*Sources: `../conformal_metodos.py` (filas_por_periodo, se_cluster), `../conformal_v3_tabla.csv`.*

## 4.5 Recency adaptation: sliding window and weights

Static calibration becomes stale under a regime change. We consider two recency
mechanisms on the PIT score. The sliding window recalibrates on the scores of a
trailing 60 day window, refreshed every 7 days. The recency weighted variant
follows the beyond exchangeability framework of Barber, Candes, Ramdas and
Tibshirani (2023): each past score receives a fixed weight $w_i = \rho^{\,t - t_i}$
that decays with age, with half life set by $\rho$. We use a sliding pool, in
which the weighted quantile at date $t$ is taken over all scores observed before
$t$. A fixed pool restricted to the original calibration block collapses to
unbounded intervals once the decay has drained its weight, whereas the sliding
pool always retains recent, near unit weight scores and does not collapse. The
fixed pool collapse is reported as a known limitation of the fixed pool rather
than discarded.

*Sources: `../conformal_v3_real.py` (metodo 2), `../conformal_v2_cierre.py` (parte A.a, pool deslizante).*

## 4.6 Online adaptive conformal inference (ACI)

ACI (Gibbs and Candes, 2021) treats the effective miscoverage level as a state
updated online,

$$
\alpha_{t+1} = \alpha_t + \gamma\,(\alpha - \mathrm{err}_t),
$$

where $\mathrm{err}_t$ is the empirical miscoverage on date $t$ and $\gamma > 0$
is a step size; the interval on date $t$ uses the threshold $\hat{q}(\alpha_t)$
read from the score pool. ACI guarantees long run coverage without any
exchangeability assumption, at the cost of transient deviations whose size grows
with $\gamma$. We report $\gamma \in \{0.02, 0.05\}$: larger $\gamma$ tracks
abrupt changes faster but produces more frequent unbounded intervals when
$\alpha_t$ is driven below zero.

*Sources: `../conformal_v3_real.py` (correr_aci).*

## 4.7 Transport of scores between regimes

Reweighting can only recombine calibration scores; it cannot express a score
value the old regime never produced. When the score distribution itself shifts,
we transport it. Let $\widehat{F}_{\mathrm{old}}$ be the empirical distribution of
the calibration scores and $\widehat{F}_{\mathrm{new}}$ that of a short recent
window. The monotone one dimensional optimal transport map is the increasing
rearrangement

$$
T = \widehat{F}_{\mathrm{new}}^{-1} \circ \widehat{F}_{\mathrm{old}},
$$

implemented by monotone interpolation between empirical quantiles. Each
calibration score $s_i$ is mapped to $T(s_i)$, the transported scores are
conformalized, and the procedure is wrapped in ACI, so validity follows from
online control rather than from exchangeability of the transported scores, which
is lost because $T$ is data dependent. An alternative route bounds the coverage
gap by the total variation distance between $T_\# \widehat{F}_{\mathrm{old}}$ and
the new law (Appendix C).

To temper the upper tail of the map during a transition we estimate a bootstrap
band of $T$ by resampling the recent window, shrinking the map toward the
identity at each quantile level in proportion to its bootstrap standard
deviation, so noisy tail quantiles fall back to the stable old quantile. In our
data the band is inert: with a recent window of thousands of scores the bootstrap
standard deviation of the map in the tail is about $0.003$ in PIT units, far below
the regularization scale, so the shrinkage is negligible and the transition width
is not driven by sampling noise. This is reported as a diagnostic: the transition
width is the legitimate cost of restoring coverage, not an artifact to remove.

*Sources: `../conformal_metodos.py` (mapa_transporte_banda), `../conformal_v3_real.py` (correr_transporte_aci), `../HANDOFF_KERVEN.md`, `../AUDIT_METODOLOGICO.md` (punto 5).*

## 4.8 Weighted conformal por punto (comparador)
Formulacion correcta por punto de test (Tibshirani et al. 2019), sostiene el resultado negativo.
- Material: `../conformal_v2_cierre.py` (parte A.c), `../conformal_v2_cierre_salida.txt`, `../AUDIT_METODOLOGICO.md` (punto 4).

## 4.9 Horizon embargo

Because the base model forecasts seven days ahead, the outcome of target date $t$
is only observed at $t$, whereas the forecast was issued at $t - 7$ using
information available then. To avoid look ahead leakage in the backtest, every
online calibration window ends seven days before the target, and the ACI feedback
$\mathrm{err}_t$ is delayed by seven steps before it updates $\alpha$. This is a
validity requirement for the online methods; its numerical effect on the reported
results is within the clustered standard error and without directional bias.

*Sources: `../conformal_v3_real.py` (EMBARGO_DIAS), `../conformal_v3_hallazgos.txt` (parte E), `../../DECISIONS.md` (2026-07-20).*

## 4.10 Metricas
Cobertura con error estandar clusterizado, ancho medio (sharpness), CRPS y log-score, diagnostico PIT con distancia KS a la uniforme.
- Material: `../conformal_metodos.py` (crps), `../conformal_v3_salida.txt` (CRPS por periodo), `../entrenar_hurdle_hetero_salida.txt` (KS del PIT, CRPS y log-score).
