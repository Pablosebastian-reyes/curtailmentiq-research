# Flagship: modelo base + capa de incertidumbre conforme

Código y experimentos del paper metodológico (SEGAN). El pipeline completo, del dataset congelado v1.0 a las figuras del manuscrito, se regenera con los comandos de la sección "Reproducing the results" del README raíz.

## Etapas y archivos

**1. Modelo base** (insumo de la capa conformal, ver `predicciones/README.md`):

- `entrenar_baselines.py` (seed 42): persistencia, naive estacional, XGBoost punto, GBM cuantílico y hurdle, entrenados solo hasta 2023-12-31. Salidas en `predicciones/`.
- `entrenar_hurdle_hetero.py` (seed 42): variante heterocedástica sigma(x) del hurdle, especificada en `ESPECIFICACION_SIGMA_X.md`. Salida `predicciones/pred_hurdle_hetero.csv` y diagnóstico PIT (`hurdle_hetero_pit.pdf`).

**2. Capa conformal sobre datos reales** (experimento central):

- `conformal_metodos.py`: módulo compartido de métodos (score PIT, estático, ventana deslizante, ACI, transporte OT + ACI, weighted conformal). Código idéntico para sintético y real: entre ambos solo cambian los datos.
- `conformal_v3_real.py` (seed 20260720, EMBARGO_DIAS = 7): experimento oficial sobre `predicciones/pred_hurdle.csv`. Salidas: `conformal_v3_tabla.csv` (tabla oficial de cobertura y ancho del paper), `conformal_v3_cobertura_rodante.{pdf,png}`, `conformal_v3_salida.txt` y `conformal_v3_hallazgos.txt`.
- `conformal_v3_hetero.py` (seed 20260720): corre el pipeline completo dos veces (sigma constante contra sigma(x)) con protocolo idéntico. Salida `conformal_v3_hetero_comparacion.csv`, el estudio del trade-off sharpness contra cobertura condicional.
- `RESULTADOS_REALES.md`: consolidación en prosa de los hallazgos reales. Los valores vigentes son los de `conformal_v3_tabla.csv` (corrida con embargo; ver nota de vigencia y DECISIONS.md 2026-07-28).

**3. Figuras y manuscrito:**

- `generar_figuras_paper.py`: figuras 1 a 4 del manuscrito, en `segan/figuras/`. La fig. 3 recomputa las series conformal con el mismo orden de RNG que la corrida oficial y se autochequea contra `conformal_v3_tabla.csv`. Detalle en `segan/REPORTE_FIGURAS.md`.
- `segan/SEGAN_paper_FINAL.tex`: manuscrito LaTeX vigente (copia de trabajo del Overleaf).
- `draft/`: borradores en markdown de las secciones del paper; `INDICE_PAPER.md` es el índice.

**4. Banco de pruebas sintético** (etapa de prototipado, NO citable):

- `conformal_prototype.py`, `conformal_v2.py`, `conformal_v2_cierre.py` (seed 20260720): panel sintético calibrado al EDA del v1.0. Sus resultados no son evidencia empírica; documentan la metodología y el negative result del weighted conformal pooled. Salidas de referencia en los `*_salida.txt` y `*_tabla.csv` correspondientes.

## Documentación metodológica

- `AUDIT_METODOLOGICO.md`: audit de Kerven Cea (2026-07-19); define los cuatro pilares del diseño (weighted conformal por punto como negative result, la rampa BESS de 15 meses, ventana deslizante 60d con score PIT, transporte del score + ACI).
- `ESPECIFICACION_TECNICA.md`: referencia del sistema completo (capa A de datos, capa B de incertidumbre).
- `ESPECIFICACION_SIGMA_X.md`: especificación del modelo base heterocedástico.
- `HANDOFF_KERVEN.md`: traspaso sobre conformal bajo cambio de régimen vía OT.

## Decisiones de alcance vigentes

- Embargo de horizonte de 7 días activo en todos los métodos online (requisito de validez del backtest a 7 días; DECISIONS.md 2026-07-20).
- Modelo base oficial: hurdle con sigma constante (`predicciones/pred_hurdle.csv`). El sigma(x) queda como estudio del trade-off, no como modelo base (DECISIONS.md 2026-07-22).
- Errores estándar de cobertura clusterizados por fecha en toda tabla reportada.

## Ejecución

Todos los scripts corren desde la raíz del repo, con el entorno de `environment.yml` o el venv de `../curtailmentiq-model`. Versiones de referencia: python 3.12.3, pandas 3.0.3, numpy 2.4.6, scikit-learn 1.9.0, xgboost 3.2.0. Las salidas de referencia (tablas, logs y figuras) están versionadas junto a cada script.
