# etl/

Scripts de procesamiento: del archivo CEN original a las tablas curadas en la base de datos. La descarga de los originales vive en `scripts/descargar_cen.sh`.

- `parsers.py`: parseo de los xlsx del CEN y reglas de corrección de erratas (cada regla referencia su fila en ERRATA_LOG.md).
- `cargar_a_neon.py` / `cargar_horario_a_neon.py`: carga de las tablas diaria y horaria, con chequeos de continuidad pre-commit.
- `validar_horario.py`: validación de la tabla horaria contra la diaria.
- `matchear_centrales.py` / `enriquecer_centrales.py`: matching del censo de centrales contra el maestro del CEN y enriquecimiento de metadata.

Todo script corre de punta a punta sin intervención manual. Requieren credenciales de base de datos (`.env` no versionado); no son necesarios para reproducir los resultados del paper desde el dataset público.

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
