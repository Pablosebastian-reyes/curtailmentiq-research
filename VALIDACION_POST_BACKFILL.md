# Reporte de verificación post-backfill: dataset v1.0 (corte 2026-05-31)

Generado: 2026-07-04 · Base: neondb (Neon PostgreSQL) · Consultas de solo lectura (scripts en `etl/`, validación en `etl/validar_horario.py`).
Actualizado tras las compuertas G-A (metadata 300/300) y G-B (ERRATA_LOG consolidado, 7 erratas).

## 1. Filas y rango de fechas por tabla

| tabla | filas | rango | nota |
|---|---|---|---|
| curtailment_horario | 6,906,761 | 2022-01-01 a 2026-05-31 | 1,612 días continuos; 53 reportes mensuales CEN |
| curtailment_diario | 293,678 | 2022-01-01 a 2026-05-31 | 1,612 días continuos; incluye 186 filas recuperadas por erratas 1-2 |
| centrales | 300 | — | 5 nuevas de 2026 |
| centrales_metadata | 300 | — | cobertura 300/300 (compuerta G-A) |
| resumen_mensual | 214 | 2022-01 a 2026-05 | meses jun-dic 2026 = placeholders oficiales gwh=0 |

Claves únicas OK en ambas tablas de hechos. Ceros explícitos: 49.8% (diario) y 83.6% (horario) de las filas.

## 2. Centrales

300 en total: Solar 75, Eólica 56, Hidro Pasada 140, Hidro Embalse 29. Presentes 300/300 en ambas series. Metadata 300/300 (match: exacto 129, sin_unidad 146, contenido 10, fuzzy 4, manual 11).

## 3. Consistencia horario vs diario

- Muestra de 30 días (setseed 0.42 sobre 1,612 días): discrepancia promedio/mediana/máxima = 0.0000%; energía emparejada idéntica (305,980.34 MWh); 100% de pares ≤ 1%.
- Validación censal mes a mes (53 meses, disc. ponderada = Σ|horario−diario|/Σdiario por central-mes): 50/53 meses ≤ 1%, 42/53 en 0.0000%. Meses en alerta, todos por inconsistencias del propio CEN (erratas 5-7 del ERRATA_LOG): 2023-10 (8.96%, restatement con 3 cifras oficiales), 2024-06 (17.97%, sin hojas horarias hidro), 2024-07 (1.11%, déficit sistemático eólico de las hojas horarias 2024).

## 4. Curtailment total por año (GWh)

| año | diario | horario | resumen CEN (Total) | diario vs CEN |
|---|---|---|---|---|
| 2022 | 1,471.02 | 1,471.02 | 1,471.02 | ±0.000 |
| 2023 | 2,666.97 | 2,668.76 | 2,666.97 | ±0.000 |
| 2024 | 6,223.73 | 6,173.69 | 6,223.73 | ±0.000 |
| 2025 | 6,205.49 | 6,205.49 | 6,205.49 | ±0.000 |
| 2026 (ene-may) | 2,463.26 | 2,463.26 | 2,463.26 | ±0.000 |

Total diario: 19,030.46 GWh. El diario cuadra exacto con los totales oficiales del CEN en los 5 años (los desvíos del horario en 2023/2024 corresponden a las erratas 5-7).

Desglose diario por tecnología (GWh): 2022 S 829.90, E 641.12 · 2023 S 1,862.71, E 804.26 · 2024 S 4,189.47, E 1,453.00, HE 356.06, HP 225.20 · 2025 S 4,424.25, E 1,619.81, HE 18.40, HP 143.02 · 2026 S 1,787.00, E 641.92, HE 4.18, HP 30.16.

## 5. Erratas del CEN

7 erratas/límites de fuente, consolidadas en `ERRATA_LOG.md` (tabla formal) y `release/v1.0/errata_log.csv`: 3 corregidas por regla de parseo, 1 con día recuperado desde hoja horaria (2 días: 2022-05-31 y 2025-05-31), 3 documentadas como límite de fuente. Ver detalle y evidencia de contraste en el log.

## 6. Trazabilidad

- `data-raw/`: 53 archivos CEN originales, inmutables, SHA-256 + fecha de descarga en `data-raw/CHECKSUMS.sha256`.
- `release/v1.0/`: 4 tablas en CSV+Parquet (orden determinístico, sin columna id), `data_dictionary.md`, `errata_log.csv`, `CHECKSUMS.sha256` único (publicables + 53 originales).
- Pipeline en `etl/` y `scripts/`: descarga (descargar_cen.sh), parseo y erratas (parsers.py), cargas con sanidad pre-commit (cargar_a_neon.py, cargar_horario_a_neon.py), validación censal (validar_horario.py), export (exportar_release.py).
- Decisiones metodológicas fechadas en `DECISIONS.md`.
