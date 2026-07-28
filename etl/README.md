# etl/

Scripts de descarga y procesamiento. Convenciones:
- `01_download_*.py`: descarga desde el CEN (registrar URL y fecha en el log del script).
- `02_clean_*.py`: limpieza y corrección de erratas (cada regla referencia su fila en ERRATA_LOG.md).
- `03_build_*.py`: construcción de tablas analíticas / carga a Neon.
Todo script debe correr de punta a punta sin intervención manual.

## Rutas

`parsers.py` no contiene rutas absolutas: deduce la raíz del repo desde
`__file__`, así que los scripts corren desde cualquier directorio de trabajo.

| Variable | Por defecto | Para qué |
|---|---|---|
| `CURTAILMENTIQ_BASE` | directorio padre del repo | Recursos hermanos no versionados aquí: `curtailmentiq-model/.env` (credenciales) y el CSV de ranking. |
| `CURTAILMENTIQ_DATA_RAW` | `<repo>/data-raw` | Originales del CEN, si se guardan fuera del repo (son pesados y están en `.gitignore`). |
| `CURTAILMENTIQ_CSV_RANKING` | `<CURTAILMENTIQ_BASE>/centrales_curtailment_2024_2025_full.csv` | Ruta directa al CSV de ranking. |

Sin variables definidas, el layout esperado es el original:

```
PROYECTO-CURLTAIMENT/          <- CURTAILMENTIQ_BASE
├── curtailmentiq-research/    <- este repo (data-raw/ adentro)
├── curtailmentiq-model/.env
└── centrales_curtailment_2024_2025_full.csv
```
