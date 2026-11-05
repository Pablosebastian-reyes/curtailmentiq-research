# Second revision (SEGAN-D-26-03850R1)

This folder holds everything produced for the second revision of the article *An open curtailment dataset and an evaluation of adaptive conformal calibration under regime change*: the analysis scripts, their outputs, the LaTeX sources of the revised manuscript and of the response to the reviewers, and the compiled PDFs. It reuses, without modifying them, the calibration code of the first revision (`flagship/revision/rev_lib.py`), the training code (`flagship/entrenar_baselines.py`, `flagship/revision/verificacion/`) and the frozen dataset (`release/v1.0/`).

## Contents

| Folder | Contents |
|---|---|
| [scripts/](scripts/) | The analysis, numbered in execution order (`r2_01` to `r2_13`), and [r2_00_correr_todo.sh](scripts/r2_00_correr_todo.sh), which runs them all. |
| [resultados/](resultados/) | Every output table (CSV/JSON). The base-model predictives and the per-row series (`predictivas/`, `series/`, about 230 MB) are not versioned; `r2_01` and `r2_02` regenerate them. |
| [figuras/](figuras/) | The new figures of the manuscript (vector PDF, with PNG previews). |
| [manuscrito/](manuscrito/) | LaTeX sources of the revised manuscript. Tables are written by `r2_08`, and every number quoted in the text is read from the result files by `r2_07` into `cifras.tex`. |
| [carta/](carta/) | LaTeX source of the response to the reviewers; its cross-references are read from the compiled manuscript. |
| [entrega/](entrega/) | Compiled PDFs: response letter, revised manuscript, marked-up version against the first revision, and highlights. |
| [base_r1/fuentes/](base_r1/fuentes/) | LaTeX source package of the first revision as submitted (tag `submission-2026-09-14`), used to build the marked-up version. |
| [logs/](logs/) | One log per script run. |

## Reproducing

Prerequisites: the environment of [environment.yml](../environment.yml) and the dataset files from Zenodo in `release/v1.0/` (step 1 of the [root README](../README.md#reproducing-the-results)). Then, from this folder:

```bash
PY=python bash scripts/r2_00_correr_todo.sh
```

| Script | Regenerates | Seeds |
|---|---|---|
| `r2_01_predictivas.py` | The nine base predictives (four hurdle variants, including the early-stopped hurdle, and five capacity variants of the multi-quantile model). Checks each against the stored predictions or series of the first revision; the relative difference is below 1e-5, the rounding of the stored files. | 42 |
| `r2_02_metodos.py` | Every calibration layer on every base model (static split, sliding window, ACI, Transport+ACI with and without a bound on alpha, configurations selected by rolling origin per base model, ablation components, one-sided CQR, 95% and 99% levels), and CRPS, threshold-weighted CRPS and Brier score of each base model. Asserts that the reference hurdle reproduces the tables of the first revision. | 20260720, 11 |
| `r2_03_diagnostico.py` | The cross-model relationship and its decomposition with the constant-threshold oracle; day-block bootstrap common to all cells, fixed and crossed random effects, wild cluster bootstrap; out-of-sample test on the early-stopped hurdle. Asserts that the 40 cells of the first revision are reproduced. | 20260901 |
| `r2_04_operacional.py` | Capacity- and energy-weighted coverage, uncovered energy, the three definitions of high-curtailment days, the cost at k = 10, 20 and 100, conditional coverage, and bootstrap intervals for the key differences. | 20260901 |
| `r2_05_simulacion.py` | The controlled simulation (four scenarios, eight base models, fifty replicates; about 40 minutes on eight cores). | 20261103 |
| `r2_06_sensibilidad.py` | Appendix E: every parameter of the calibration layer, the nominal level, the calibration window, the quantile grid, the high-day threshold, conformal seeds and base-model hyperparameters. | 20260720; 1000-1009 (conformal); 1-10 (training) |
| `r2_13_tiempos.py` | Runtime of each component, measured on an idle machine. | 20260720 |
| `r2_08_tablas.py` | Ablations per base model and every LaTeX table. | 20260901 |
| `r2_09_figuras.py` | The new figures. | 20260720 |
| `r2_07_cifras.py` | `manuscrito/cifras.tex`, with every number quoted in the text, and fails if the text uses a number it does not define. | none |
| `r2_12_verificar.py` | Checks each qualitative statement of the text (rankings, "every", "only", "at every cost ratio") against the result files. | none |
| `r2_10_ensamblar.py --empaquetar` | Orders the bibliography by first citation, compiles the manuscript and the letter, checks the logs, counts the words of the abstract, and writes the single-file source package. | none |
| `r2_11_marcado.py` | The marked-up version against the first revision (latexdiff). | none |
