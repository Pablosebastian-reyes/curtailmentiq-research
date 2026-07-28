# CurtailmentIQ Research

Companion repository for a research article on probabilistic forecasting of renewable energy curtailment in Chile's National Electricity System (Sistema Eléctrico Nacional, SEN): *Probabilistic forecasting of renewable curtailment under regime change: an open dataset and a conformal method with distribution-shift-aware coverage control for Chile's National Electricity System* (under review). It also hosts the pipeline behind the associated data descriptor.

The repository contains the full data pipeline (from the raw CEN monthly reports to the curated dataset), the baseline forecasting models, the conformal uncertainty layer, and the scripts that regenerate every table and figure in the manuscripts.

**Authors:** Pablo Reyes Cerda (Universidad de Santiago de Chile / Synapta SpA) and Kerven Cea Morales (Universidad del Bío-Bío).

## Dataset

The curated dataset is published on Zenodo under a **CC BY 4.0** license:

- Concept DOI, the one cited in the article (always resolves to the latest version): [10.5281/zenodo.21198816](https://doi.org/10.5281/zenodo.21198816)
- Current version: v1.1 ([10.5281/zenodo.21652187](https://doi.org/10.5281/zenodo.21652187)), a documentation-only correction; its data files are byte-identical to v1.0 ([10.5281/zenodo.21198817](https://doi.org/10.5281/zenodo.21198817), frozen 2026-07-04)

It covers plant-level curtailment of solar, wind and hydropower in the SEN from 2022-01-01 to 2026-05-31 (1,612 continuous days): a daily table (293,678 rows), an hourly table (6,906,761 rows), the plant census and metadata, a documented errata log, and SHA-256 checksums. The [data dictionary](release/v1.0/data_dictionary.md) and the [errata log](release/v1.0/errata_log.csv) are also versioned in this repository.

## What this repository contains

- **Data pipeline** ([etl/](etl/), [scripts/](scripts/)): download of the official CEN monthly reports, parsing, errata detection and correction (eight documented errata classes, see [ERRATA_LOG.md](ERRATA_LOG.md)), loaders with continuity checks, and the deterministic export of the frozen release.
- **Baseline models** ([flagship/entrenar_baselines.py](flagship/entrenar_baselines.py)): persistence, seasonal naive, point XGBoost, quantile GBM, and a hurdle model (occurrence classifier plus lognormal magnitude), all trained only on data up to 2023-12-31; plus a heteroscedastic variant ([flagship/entrenar_hurdle_hetero.py](flagship/entrenar_hurdle_hetero.py)).
- **Conformal uncertainty layer** ([flagship/](flagship/)): static split conformal, 60-day sliding window, adaptive conformal inference (ACI), score transport via optimal transport plus ACI, and the per-point weighted conformal negative result, evaluated with a 7-day horizon embargo.
- **Reproduction scripts** for every table and figure of both manuscripts (see below).

## Repository structure

| Folder | Contents |
|---|---|
| [data-raw/](data-raw/) | Original CEN monthly reports ("Reducciones de Energía"), immutable, erratas included: they are the evidence base of the errata log. The 53 `.xlsx` binaries are not versioned for size; their SHA-256 checksums are in [data-raw/CHECKSUMS.sha256](data-raw/CHECKSUMS.sha256). |
| [etl/](etl/) | Parsers for the CEN spreadsheets, errata-aware cleaning, database loaders with pre-commit continuity checks, plant matching and metadata enrichment. |
| [scripts/](scripts/) | [descargar_cen.sh](scripts/descargar_cen.sh) (re-download of the original CEN files), [make_checksums.py](scripts/make_checksums.py), [exportar_release.py](scripts/exportar_release.py) (deterministic release export), [generar_figuras_data_paper.py](scripts/generar_figuras_data_paper.py) (data descriptor figures). |
| [release/](release/) | Frozen dataset releases, matching the deposit versions published on Zenodo: `v1.0/` and `v1.1_zenodo/` (data files byte-identical between the two; v1.1 corrects the documentation). Data files live on Zenodo; the data dictionary, errata log and checksums are versioned here. |
| [flagship/](flagship/) | Code and experiments of the methods article: baseline training, the conformal experiments (synthetic testbed and the real-data experiment), figure generation, methodological documentation, the LaTeX manuscript ([flagship/segan/](flagship/segan/)) and section drafts ([flagship/draft/](flagship/draft/)). |
| [flagship/predicciones/](flagship/predicciones/) | Frozen baseline predictions (2024-01 to 2026-05), the input of the conformal layer. Fully regenerable, see its [README](flagship/predicciones/README.md). |
| [flagship-eda/](flagship-eda/) | Exploratory data analysis: script and six figures (zero structure, magnitudes, seasonality, Wasserstein drift, spatial correlation, persistence). |
| [figures/](figures/) | Figures of the data descriptor (script output only, nothing hand-made). |
| [paper-data/](paper-data/) | Data descriptor manuscript (Data in Brief format). |
| [paper-flagship/](paper-flagship/) | Periodic backups of the Overleaf project. |
| notebooks/, experiments/, legal/ | Scaffolding kept for project structure, currently empty. |

Root documents: [DECISIONS.md](DECISIONS.md) (dated log of every methodological decision), [ERRATA_LOG.md](ERRATA_LOG.md) (errata registry, the source of `errata_log.csv`), [MANUAL_OPERATIVO.md](MANUAL_OPERATIVO.md) (working plan) and [VALIDACION_POST_BACKFILL.md](VALIDACION_POST_BACKFILL.md) (post-backfill validation). Internal working documents and code comments are written in Spanish; the manuscripts, the dataset documentation and all figure text are in English.

## Reproducing the results

All scripts run from the repository root, are deterministic under fixed seeds, and read only the frozen release plus files versioned here. The reference runs used Python 3.12.3 with pandas 3.0.3, numpy 2.4.6, scikit-learn 1.9.0 and xgboost 3.2.0; small numerical differences may appear with other library versions.

**1. Get the data.** Download the data files from Zenodo ([10.5281/zenodo.21198816](https://doi.org/10.5281/zenodo.21198816); byte-identical in v1.0 and v1.1) into `release/v1.0/`, the path the scripts read, and verify their integrity:

```bash
grep 'release/v1.0' release/v1.0/CHECKSUMS.sha256 | shasum -a 256 -c
```

The same checksum file also lists the 53 original CEN files of `data-raw/`; those are only needed to rebuild the dataset from scratch, not to reproduce the paper results.

**2. Run the pipeline.** Each step regenerates a specific output of the article:

| Step | Command | Regenerates | Seed |
|---|---|---|---|
| 1 | `python flagship/entrenar_baselines.py` | The five baseline prediction files in `flagship/predicciones/` and the point-forecast MAE comparison (baselines table of the article). | 42 |
| 2 | `python flagship/entrenar_hurdle_hetero.py` | `pred_hurdle_hetero.csv` (heteroscedastic base model) and its PIT diagnostics ([hurdle_hetero_pit.pdf](flagship/hurdle_hetero_pit.pdf)). | 42 |
| 3 | `python flagship/conformal_v3_real.py` | [conformal_v3_tabla.csv](flagship/conformal_v3_tabla.csv), the official coverage and width results table of the main experiment (7-day embargo, nominal 90%, coverage standard errors clustered by date), plus the rolling-coverage figure and the run logs. | 20260720 |
| 4 | `python flagship/conformal_v3_hetero.py` | [conformal_v3_hetero_comparacion.csv](flagship/conformal_v3_hetero_comparacion.csv), the end-to-end sharpness versus conditional-coverage comparison (constant sigma versus sigma(x)). | 20260720 |
| 5 | `python flagship/generar_figuras_paper.py` | Figures 1 to 4 of the article in `flagship/segan/figuras/`. Figure 3 recomputes the conformal series with the same RNG order as step 3 and aborts if it does not match the official table (see [REPORTE_FIGURAS.md](flagship/segan/REPORTE_FIGURAS.md)). | 20260720 |
| 6 | `python scripts/generar_figuras_data_paper.py` | Figures 1 and 2 of the data descriptor in `figures/`. | deterministic |
| 7 | `python flagship-eda/generar_eda.py` | The six EDA figures in `flagship-eda/`. | deterministic |

Reference outputs of every run (tables, logs, figures) are versioned next to each script, so results can be checked without re-running. The synthetic testbed (`flagship/conformal_prototype.py`, `flagship/conformal_v2*.py`, seed 20260720) reproduces the methodology prototyping stage; its numbers are not citable and are not used in the article.

The narrative consolidation of the real-data findings is in [flagship/RESULTADOS_REALES.md](flagship/RESULTADOS_REALES.md).

## Requirements

Python 3.12 (reference runs: 3.12.3). Main libraries: pandas, numpy, scikit-learn, xgboost, scipy, matplotlib, pyarrow; plus POT, MAPIE and properscoring for the drift and conformal tooling. A ready-made environment is provided:

```bash
conda env create -f environment.yml
conda activate curtailmentiq
```

The ETL loaders additionally require PostgreSQL access (psycopg2, sqlalchemy); this is not needed to reproduce the article results.

## What is NOT in this repository

- **The original CEN `.xlsx` files** (53 monthly reports in `data-raw/`): excluded for size. Their SHA-256 checksums are versioned in [data-raw/CHECKSUMS.sha256](data-raw/CHECKSUMS.sha256), so any copy can be verified, and [scripts/descargar_cen.sh](scripts/descargar_cen.sh) re-downloads them from the CEN portal.
- **The curated data files** (CSV/Parquet of `release/`): distributed through Zenodo, not duplicated in git. Their checksums are versioned in [release/v1.0/CHECKSUMS.sha256](release/v1.0/CHECKSUMS.sha256).
- **Database credentials**: the ETL loads into a PostgreSQL instance whose credentials live in an untracked `.env`. They are only needed to rebuild the curated tables from the raw files; reproduction from the public dataset does not touch the database.

## How to cite

If you use the dataset, please cite:

> Reyes Cerda, P., & Cea Morales, K. (2026). *An errata-corrected, plant-level dataset of solar, wind and hydropower curtailment in Chile's National Electricity System (2022-2026)* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.21198816

This concept DOI covers all versions of the deposit and resolves to the current one (v1.1). The research article is currently under peer review; its citation will be added here upon acceptance.

## License and attribution

- **Code**: [MIT License](LICENSE).
- **Dataset**: CC BY 4.0, via [Zenodo](https://doi.org/10.5281/zenodo.21198816).
- **Original data**: the raw curtailment records are published by the **Coordinador Eléctrico Nacional (CEN), Chile**, which must be credited as the source of the original data. The CEN confirmed in writing (transparency request, 2026) that its public data may be used and redistributed for academic research with attribution; see the entry of 2026-07-18 in [DECISIONS.md](DECISIONS.md).
