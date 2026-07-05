# CurtailmentIQ Research

Repositorio de investigación para los papers académicos sobre curtailment de energía renovable en el Sistema Eléctrico Nacional de Chile (SEN).

**Autores:** Pablo Reyes Cerda (USACH / Synapta SpA) · Kerven Cea Morales (UBB)

## Papers en curso

1. **Data paper** (Data in Brief): dataset validado de curtailment del SEN 2022-2026 + metodología de detección y corrección de erratas del CEN.
2. **Flagship** (SEGAN): pronóstico probabilístico de curtailment bajo cambio de régimen: modelo hurdle + predicción conforme + análisis de drift vía transporte óptimo (Wasserstein), con el quiebre BESS 2025 como caso de estudio.

## Estructura

```
data-raw/          Archivos CEN ORIGINALES, inmutables (con erratas). NO editar jamás.
etl/               Scripts de descarga, limpieza y corrección de erratas.
notebooks/         Exploración, validación Fraunhofer, generación de figuras.
experiments/       Configs y resultados por corrida de modelo.
figures/           Solo salida de scripts (PDF vectorial). Nada hecho a mano.
scripts/           Utilidades (checksums, etc.).
paper-data/        Manuscrito Data in Brief (template Word oficial) + anexos.
paper-flagship/    Respaldo semanal del proyecto Overleaf.
legal/             Respuesta SAIP del CEN sobre redistribución de datos.
```

## Reglas de oro

1. **Todo número que aparezca en un paper debe regenerarse con un comando.** Cada resultado queda amarrado a un commit + config + seed en `experiments.csv`.
2. `data-raw/` es inmutable. Archivo que entra, se le calcula checksum con `python scripts/make_checksums.py` y no se toca nunca más.
3. Toda decisión metodológica se registra en `DECISIONS.md` con fecha y justificación.
4. Ninguna referencia bibliográfica generada por IA entra a un manuscrito sin verificarse contra la fuente (DOI / Google Scholar).
5. Splits temporales (train / calibración / test) se definen una vez, se documentan en `DECISIONS.md` y no se cambian sin registrar el porqué.

## Setup

```bash
conda env create -f environment.yml
conda activate curtailmentiq
```

Ver `MANUAL_OPERATIVO.md` para el plan completo de trabajo, roles y cronograma.
