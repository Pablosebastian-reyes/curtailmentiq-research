# Fase 0 — ¿la ventaja de Transport+ACI viene de la capa o del modelo base?

**Comentario que responde:** R1.1.  
**Estado:** ejecutado. **El resultado es una condicion de parada tipo (a)**: 
ver `HALLAZGOS_CRITICOS.md`, hallazgo H1.

> **Nota del 14 de septiembre.** Las cifras de interval score de esta nota (tabla principal, diferencia +13.9 [−10.7, +37.8] y tabla de la mejor combinación) son anteriores a C1 y usan 2/α. Con 1/α la diferencia del GBM en la transición es +14.5 [+4.9, +24.0] y excluye el cero, y el GBM con split estático es el mejor en cuatro de las cinco ventanas. El ajuste de quince celdas de esta nota (−0.757, −4.39, +5.49) se calculó sobre las entradas de `fase0_diagnostico.csv` redondeadas a un decimal; sobre las series sin redondear, como se hace desde la corrección D1 (`CHANGELOG_REVISION.md`, sección 10.4), es −0.755, −4.36, +5.45. Coberturas, anchos y CRPS no cambian; los valores vigentes están en los CSV listados al final.

## Pregunta

El revisor pide implementar un modelo base probabilistico competitivo alternativo
al hurdle, siguiendo su sugerencia de un GBM multi-cuantil, y repetir con el
**todos** los experimentos de Transport+ACI, para determinar si la ventaja del
metodo viene de la capa de calibracion o de su compatibilidad con el hurdle
especifico.

## Diseno

Se corre el protocolo conformal completo, sin cambiar una sola constante, sobre
tres predictivas base distintas.

| Modelo base | Forma de la predictiva | Origen |
|---|---|---|
| `hurdle` | (1-p) delta_0 + p LogNormal(mu(x), sigma), sigma = 1.7016 constante | modelo base oficial, `entrenar_baselines.py` |
| `hurdle_sigma_x` | idem con dispersion condicional sigma(x) | `entrenar_hurdle_hetero.py`, hasta ahora solo estudio de trade-off |
| `qgbm_multi` | funcion cuantil empirica sobre 54 cuantiles (0.005 a 0.999), interpolada, con atomo en cero leido de los cuantiles nulos | **nuevo**, `fase0_entrenar_qgbm.py` |

El GBM multi-cuantil se entrena con **disciplina identica** al hurdle: mismas 12
features, mismo panel, mismo conjunto comun de filas, entrenamiento solo con
target <= 2023-12-31, mismos hiperparametros fijados a priori (400 arboles,
lr 0.05, depth 6, min_child_weight 5, subsample 0.9, colsample 0.9), seed 42.
Nunca ve el periodo de evaluacion. Se aplica rearrangement por fila contra el
cruce de cuantiles y recorte a >= 0.

La capa conformal es literalmente el mismo codigo: `flagship/revision/rev_lib.py`
generaliza `conformal_metodos.py` a una interfaz de predictiva con solo dos
operaciones, `cdf(y)` y `inv(q)`, y reusa sin tocar el algebra de los cuantiles
conformal, del ACI y del mapa de transporte con shrinkage.

**Control de validez.** La rama del hurdle reproduce `conformal_v3_tabla.csv` de
la version enviada en las 30 celdas x 4 metricas, verificado por asercion dentro
del script. Cualquier diferencia entre ramas es del modelo base, no del protocolo.

Semillas: 20260720 (aleatorizacion del atomo PIT y bootstrap del mapa),
42 (entrenamiento), 11 (muestreo del CRPS), 20260901 (bootstrap de diferencias).

## Resultado principal

Ventana de transicion, octubre a diciembre de 2024, nominal 90%. Cobertura en
por ciento con error estandar clusterizado por fecha, ancho medio en MWh sobre
intervalos finitos, interval score del limite unilateral superior en MWh.

| Modelo base | Metodo | Cobertura | Ancho | Interval score | % infinitos |
|---|---|---|---|---|---|
| Hurdle, sigma constante (base oficial) | Split estatico (PIT) | 95.3 (0.45) | 1203 | 1588 | 0.0 |
|  | Ventana deslizante 60d | 92.0 (0.73) | 834 | 1391 | 0.0 |
|  | ACI (g=0.02) | 93.5 (0.55) | 915 | 1401 | 0.0 |
|  | ACI (g=0.05) | 92.1 (0.67) | 822 | 1370 | 0.0 |
|  | Transporte+ACI (g=0.02) | 91.1 (0.8) | 787 | 1390 | 0.0 |
|  | Transporte+ACI (g=0.05) | 90.9 (0.81) | 806 | 1408 | 0.0 |
| Hurdle, sigma(x) condicional | Split estatico (PIT) | 91.7 (0.63) | 770 | 1214 | 0.0 |
|  | Ventana deslizante 60d | 88.7 (0.88) | 627 | 1237 | 0.0 |
|  | ACI (g=0.02) | 89.9 (0.77) | 657 | 1198 | 0.0 |
|  | ACI (g=0.05) | 89.5 (0.82) | 649 | 1205 | 0.0 |
|  | Transporte+ACI (g=0.02) | 88.9 (0.94) | 669 | 1269 | 0.0 |
|  | Transporte+ACI (g=0.05) | 89.5 (0.96) | 733 | 1267 | 0.0 |
| GBM multi-cuantil, 54 cuantiles (R1.1) | Split estatico (PIT) | 90.6 (0.85) | 410 | 765 | 0.0 |
|  | Ventana deslizante 60d | 90.1 (0.94) | 409 | 786 | 0.0 |
|  | ACI (g=0.02) | 90.6 (0.86) | 412 | 765 | 0.0 |
|  | ACI (g=0.05) | 90.6 (0.87) | 412 | 764 | 0.0 |
|  | Transporte+ACI (g=0.02) | 90.4 (0.98) | 420 | 782 | 0.0 |
|  | Transporte+ACI (g=0.05) | 90.5 (0.99) | 425 | 779 | 0.0 |

**El recorte de ancho de Transport+ACI frente al split estatico, por modelo base:**

| Modelo base | Cobertura del split estatico | Cambio de ancho de Transport+ACI |
|---|---|---|
| Hurdle, sigma constante (base oficial) | 95.3% | -33.1% |
| Hurdle, sigma(x) condicional | 91.7% | -4.8% |
| GBM multi-cuantil, 54 cuantiles (R1.1) | 90.6% | +3.6% |

Con incertidumbre, bootstrap de 2000 remuestreos de **dias completos** (la unidad
de dependencia del panel), intervalo de percentil al 95% de la diferencia de
ancho medio Transport+ACI menos split estatico:

- Hurdle, sigma constante (base oficial): -396.1 MWh, IC 95% [-462.8, -333.1]
- Hurdle, sigma(x) condicional: -36.8 MWh, IC 95% [-96.7, +25.9]
- GBM multi-cuantil, 54 cuantiles (R1.1): +15.1 MWh, IC 95% [+0.0, +30.3]

**La ganancia no se replica.** Con el GBM multi-cuantil el punto estimado de la
diferencia de ancho tiene el signo contrario al reportado en el manuscrito, y su
intervalo apenas excluye el cero por el lado equivocado. La diferencia de
interval score en la misma celda, +13.9 con intervalo [-10.7, +37.8], si
contiene el cero. En cualquiera de las dos lecturas la reduccion no esta.

## Diagnostico: la ganancia mide la mala calibracion del modelo base

Sobre las 15 celdas (3 modelos base x 5 ventanas):

- correlacion de Pearson entre sobre-cobertura del split estatico y cambio de ancho: **r = -0.757**
- pendiente: **-4.39%** de ancho por punto porcentual de sobre-cobertura
- intercepto: **+5.49%**, el cambio esperado cuando el split ya esta en nominal

| Modelo base | Ventana | Sobre-cobertura del estatico (pp) | Cambio de ancho (%) |
|---|---|---|---|
| hurdle | test_transition | +5.3 | -33.1 |
| hurdle_sigma_x | test_pre | +4.5 | -16.9 |
| hurdle | 2025-S2 | +4.0 | -4.3 |
| hurdle | test_pre | +3.5 | -14.8 |
| hurdle_sigma_x | 2025-S2 | +2.9 | +7.6 |
| hurdle | 2026-S1 | +2.5 | -8.6 |
| hurdle_sigma_x | test_transition | +1.7 | -4.8 |
| qgbm_multi | 2025-S2 | +1.7 | +4.3 |
| qgbm_multi | test_pre | +1.2 | +1.2 |
| hurdle_sigma_x | 2026-S1 | +0.7 | +16.9 |
| qgbm_multi | 2026-S1 | +0.6 | +6.1 |
| qgbm_multi | test_transition | +0.6 | +3.6 |
| hurdle | 2025-S1 | -0.6 | -2.0 |
| hurdle_sigma_x | 2025-S1 | -2.0 | +9.2 |
| qgbm_multi | 2025-S1 | -2.0 | +10.0 |

La capa adaptativa no corrige el cambio de regimen: recupera el ancho que el
modelo base regala por sobre-dispersion. Donde el modelo base ya esta calibrado,
la capa cuesta ancho en vez de ahorrarlo.

## El modelo base alternativo domina en toda metrica propia

CRPS de la predictiva base, en MWh, por ventana:

| Ventana | hurdle | hurdle sigma(x) | GBM multi-cuantil | Mejora del GBM |
|---|---|---|---|---|
| test_pre | 96.07 | 92.30 | 71.85 | -25.2% |
| test_transition | 133.47 | 125.03 | 92.92 | -30.4% |
| 2025-S1 | 70.46 | 69.53 | 57.60 | -18.3% |
| 2025-S2 | 94.49 | 94.95 | 71.51 | -24.3% |
| 2026-S1 | 78.98 | 77.71 | 60.66 | -23.2% |

Mejor combinacion (modelo base x metodo) por interval score, entre las 18:

| Ventana | Mejor | Interval score | Cobertura | Ancho |
|---|---|---|---|---|
| test_pre | qgbm_multi / Ventana deslizante 60d | 511 | 91.9% | 331 |
| test_transition | qgbm_multi / ACI (g=0.05) | 764 | 90.6% | 412 |
| 2025-S1 | qgbm_multi / Split estatico (PIT) | 530 | 88.0% | 221 |
| 2025-S2 | qgbm_multi / Split estatico (PIT) | 586 | 91.7% | 319 |
| 2026-S1 | qgbm_multi / Split estatico (PIT) | 527 | 90.6% | 253 |

En tres de las cinco ventanas el optimo es el GBM multi-cuantil **con el split
estatico**, es decir sin ninguna capa adaptativa.

Contrapeso, para no sobreleer: el hurdle mantiene mejor Brier del evento {Y>0}
(0.0721 contra 0.1027 en la transicion).
La comparacion no es equivalente: la probabilidad de ocurrencia del GBM se lee de
la rejilla de cuantiles con resolucion 0.02, no de un clasificador dedicado. Se
reporta como descriptivo.

## Costo computacional

Segundos de la pasada completa sobre las 638 fechas de test, por metodo:

| Metodo | hurdle | hurdle sigma(x) | GBM multi-cuantil |
|---|---|---|---|
| Split estatico (PIT) | 0.0 | 0.0 | 0.0 |
| Ventana deslizante 60d | 0.1 | 0.1 | 0.1 |
| ACI (g=0.02) | 0.2 | 0.2 | 0.3 |
| ACI (g=0.05) | 0.2 | 0.2 | 0.3 |
| Transporte+ACI (g=0.02) | 6.8 | 6.8 | 6.9 |
| Transporte+ACI (g=0.05) | 6.8 | 6.8 | 6.8 |

El transporte con shrinkage cuesta unas 30 veces mas que el ACI puro y unas 70
veces mas que la ventana deslizante, por el bootstrap de 150 remuestreos del mapa
en cada refresco. Bajo el modelo base alternativo ese costo no compra nada.

## Tabla completa

`resultados/fase0/fase0_tabla_por_modelo.csv` (90 filas: 3 modelos x 6 metodos x 5 ventanas).
`resultados/fase0/fase0_diferencias_bootstrap.csv` (diferencias con IC bootstrap por bloques de dia).
`resultados/fase0/fase0_diagnostico.csv` (las 15 celdas del diagnostico).

## Reproduccion

```
<venv>/bin/python flagship/revision/fase0_entrenar_qgbm.py     # ~8 min
<venv>/bin/python flagship/revision/fase0_model_agnostic.py    # ~1 min
<venv>/bin/python flagship/revision/fase0_diagnostico.py       # <1 s
```
