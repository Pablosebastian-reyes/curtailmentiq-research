# 5. Results

Contenido previsto (ver `../INDICE_PAPER.md`, seccion 5).

## 5.1 Benchmark sintetico
Cierre de la tabla comparativa sobre el panel sintetico (no citable como evidencia): el pool deslizante resuelve el colapso del pool fijo; la ventana y el ACI recuperan sharpness bajo la rampa; la banda del transporte es inerte porque el ancho de la transicion no es ruido de muestreo.
- Material: `../conformal_v2_cierre_salida.txt`, `../conformal_v2_cierre_tabla.csv`, `../conformal_v3_hallazgos.txt` (parte A), `../conformal_v2_cobertura_rodante.png`.

## 5.2 Datos reales
La maquinaria PIT funciona de extremo a extremo; la sobrecobertura severa del sintetico no aparece porque el modelo base absorbe el quiebre; la adaptatividad paga sobre todo en la rampa (transporte mas ACI baja el ancho de 1203 a 732 MWh con 90.7% de cobertura) y es ambigua fuera de ella; el techo de sharpness lo fija sigma = 1.70; las diferencias de 1 a 3 puntos estan dentro del error estandar clusterizado. Sensibilidad al embargo dentro del error estandar y sin sesgo direccional.
- Material: `../RESULTADOS_REALES.md` (secciones 1 a 5), `../conformal_v3_tabla.csv`, `../conformal_v3_salida.txt`, `../conformal_v3_cobertura_rodante.png`, `../conformal_v3_hallazgos.txt` (partes B a F).

## 5.3 Resultado negativo: weighted conformal por punto
El weighted conformal por punto con score PIT entrega intervalos infinitos en una fraccion alta de los casos (ESS de calibracion colapsado); el fallo es por falta de solapamiento en las X y es robusto entre score aditivo y PIT.
- Material: `../conformal_v2_cierre_salida.txt` (parte A.c), `../conformal_v3_hallazgos.txt` (parte A.c y B.1), `../AUDIT_METODOLOGICO.md` (punto 4).

## 5.4 Heteroscedastic base model $\sigma(x)$: marginal sharpness versus conditional coverage

This is not a negative result but a trade-off study (label fixed by the authors,
see `../../DECISIONS.md`, 2026-07-22). The base model metrics suggest a marginal
gain, but the conformal layer amplifies it into substantially sharper intervals
at preserved marginal coverage, at the cost of a conditional coverage deficit
concentrated on the largest plants and in the ramp.

### Motivation

The real data results locate the sharpness bottleneck in the base model rather
than in the conformal layer: with a constant dispersion $\sigma = 1.70$ (out of
fold), the level $0.9$ upper tail of the lognormal magnitude is inflated
uniformly, and the conformal layer can calibrate but not reduce that dispersion.
We test whether a conditional dispersion $\sigma(x)$ lowers the ceiling. The
model is a two stage extension that leaves the occurrence and mean stages
unchanged: a second gradient boosting model predicts the log of the squared out
of fold residuals of the mean stage, giving $\sigma_{\mathrm{raw}}(x) =
\exp(\hat{g}(x)/2)$; a single scale $c$ calibrates the average dispersion to unit
standardized variance out of fold, and a positive floor prevents overconfidence.
Candidate features are log capacity, technology, day of year, the occurrence
probability, and a GARCH style feature, the standard deviation of the plant's
recent positive log magnitude. Estimation obeys the same split discipline as the
rest of the study: $\sigma(x)$ is fit only on data up to 2023-12-31, out of fold,
and never sees 2024 to 2026. Feature importances are spread across all five
candidates (23% occurrence probability, 21% technology, 21% GARCH volatility,
19% day of year, 17% log capacity), with no single dominant driver.

### Base model diagnostics: little to gain from dispersion

The raw predictive is not better calibrated under $\sigma(x)$. The PIT histogram
over 2024 to 2026 is far from uniform under both dispersions, with a Kolmogorov
Smirnov (KS) distance to the uniform of $0.167$ for the constant and $0.172$ for
$\sigma(x)$, that is, marginally worse. The PIT is sloped, with excess mass in its
upper range, the signature of a location bias: the model underforecasts magnitude
on the shifted period, and a dispersion model cannot correct a location shift.
The conditional PIT on positive outcomes, $\Phi((\log y - \mu(x))/\sigma)$, is
nearly identical for the two dispersions and roughly doubles from the training
regime to the shifted period for both: from $0.097$ (train, out of fold, no break)
to $0.183$ (2024 to 2026) for the constant, and from $0.094$ to $0.182$ for
$\sigma(x)$. The degradation is the regime shift, common to both dispersions. The
log magnitude residuals are close to homoscedastic conditional on $\mu(x)$, so the
base model CRPS improves by only about 3% (81.8 to 79.1 MWh).

### End to end conformal: a real sharpness gain at a conditional cost

The base model metrics understate what happens once the conformal layer
propagates $\sigma(x)$. Running the full pipeline (static, sliding window, ACI,
transport plus ACI) under identical protocol, seed, and seven day embargo, and
changing only the dispersion input, the static reference produces intervals that
are 17 to 36% narrower under $\sigma(x)$ across the five periods, with marginal
coverage preserved. Aggregated over the test period, static coverage moves from
$92.5\%$ under the constant to $90.9\%$ under $\sigma(x)$, closer to the nominal
$90\%$ and with tighter intervals. In the ramp the improvement is clearest: static
coverage moves from $95.3\%$ (overcovering) at $1203$ MWh to $91.7\%$ (still above
nominal) at $769$ MWh, a 36% reduction. The conformal layer thus converts the
conditional dispersion into genuinely sharper intervals that the 3% CRPS gain of
the base model did not reveal.

The cost is conditional, not marginal. Coverage of the static intervals by tercile
of plant capacity over the full test period is as follows.

| tercile | n | coverage const | coverage $\sigma(x)$ | width const | width $\sigma(x)$ |
|---|---|---|---|---|---|
| small  | 25,986 | 93.1% | 91.9% | 248.0 | 188.5 |
| medium | 26,549 | 93.3% | 92.8% | 678.0 | 470.2 |
| large  | 25,333 | 91.1% | 87.8% | 1120.3 | 881.5 |

Small and medium plants keep their coverage and become 24% and 31% sharper. Large
plants become 21% sharper but fall to $87.8\%$, about two points below nominal,
opening a conditional coverage spread of $4.1$ points between the smallest and
largest terciles. This is consistent with the base model diagnostic, in which the
raw level $0.9$ quantile of large plants undercovered at $83.0\%$; the conformal
recalibration lifts that to $87.8\%$ but does not close it, because the pre 2024
conditional dispersion of the most curtailed plants does not transfer through the
ramp. A second, period localized cost appears in the same place: the per period
CRPS improves under $\sigma(x)$ in four of five periods but regresses in the ramp
(133.5 to 146.5 MWh), and aggressive ACI ($\gamma = 0.05$) yields a higher
fraction of unbounded intervals under $\sigma(x)$ in two post ramp periods (up to
about 10%).

### Reading

Conditional variance modeling does lower the sharpness ceiling end to end, by
roughly one fifth to one third in interval width at preserved marginal coverage,
a larger effect than the base model log score or CRPS suggest. It does not address
the binding problem: the residual miscalibration is a location shift induced by
the BESS ramp that doubles the conditional PIT distance for any dispersion, and
$\sigma(x)$, fit before the ramp, transfers worst exactly where the paper's regime
shift bites, on the largest plants and during the transition. The result
reinforces the central thesis, that the shift is the operative difficulty and
marginal conformal recalibration is the right instrument, while quantifying a real
but conditional sharpness benefit from modeling the base model variance. Whether
to deploy $\sigma(x)$ then depends on whether a four point conditional coverage
spread on large plants is acceptable in exchange for one fifth narrower intervals
overall.

- Material: `../conformal_v3_hetero.py`, `../conformal_v3_hetero_salida.txt`, `../conformal_v3_hetero_comparacion.csv`, `../entrenar_hurdle_hetero_salida.txt`, `../hurdle_hetero_pit.png`, `../predicciones/pred_hurdle_hetero.csv`, `../../DECISIONS.md` (2026-07-22, reetiquetación de sigma(x)).
