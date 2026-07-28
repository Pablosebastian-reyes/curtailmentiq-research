# Reporte de verificación post-backfill: dataset v1.0 (corte 2026-05-31)

Generado: 2026-07-04 · Base: neondb (Neon PostgreSQL) · Consultas de solo lectura (scripts en `etl/`, validación en `etl/validar_horario.py`).
Actualizado tras las compuertas G-A (metadata 300/300) y G-B (ERRATA_LOG consolidado; con la errata nº 8 agregada el mismo día son 8 erratas).

> **Actualización 2026-07-28 (auditoría pre-envío):** el censo mes a mes se reejecutó con `etl/validar_horario.py` contra Neon y contra el release congelado v1.0 (checksums verificados; Zenodo es byte a byte idéntico). El resultado vigente es 50/53 meses ≤ 1% y **35/53 en 0.0000%**, no 42. El 42 provenía de una corrida de la mañana del 2026-07-04 (aparece en el borrador v03 del data paper, 13:22) anterior a las cargas finales de esa tarde; ningún artefacto commiteado lo reproduce. La diferencia son 8 meses (2025-07 a 2026-02, discrepancia ponderada 0.008% a 0.11%) explicados por una reasignación de atribución entre 12 unidades hidro (LAHIGUERA-1/2, LIRCAY-1/2, LICAN-1/2, LOSCONDORES-1/2, LAJA1-1/2, LOMAALTA, LAMINA) entre las hojas horarias mensuales y el cierre anual del CEN, con neto exactamente 0.000 MWh por mes; se verificó contra los xlsx originales que ambas tablas reproducen fielmente su fuente declarada (fidelidad 0.000000 MWh). Mismo mecanismo de las erratas 6-7, ahora en hidro 2025-H2.

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
- Validación censal mes a mes (53 meses, disc. ponderada = Σ|horario−diario|/Σdiario por central-mes): 50/53 meses ≤ 1%, 35/53 en 0.0000% (valor vigente del recuento 2026-07-28; ver nota al inicio). Meses en alerta, todos por inconsistencias del propio CEN (erratas 5-7 del ERRATA_LOG): 2023-10 (8.96%, restatement con 3 cifras oficiales), 2024-06 (17.97%, sin hojas horarias hidro), 2024-07 (1.11%, déficit sistemático eólico de las hojas horarias 2024). Los 8 meses restantes con discrepancia no nula (2025-07 a 2026-02, 0.008% a 0.11%) corresponden a la reasignación hidro de neto cero descrita en la nota.

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

8 erratas/límites de fuente, consolidadas en `ERRATA_LOG.md` (tabla formal) y `release/v1.0/errata_log.csv`: 5 corregidas o recuperadas de forma determinística (erratas 1 a 4 y 8; incluyen los 2 días recuperados desde hojas horarias, 2022-05-31 y 2025-05-31, y la corrección de coordenada de la ficha CEN 1758) y 3 documentadas como límite de fuente (erratas 5 a 7). Ver detalle y evidencia de contraste en el log.

## 6. Trazabilidad

- `data-raw/`: 53 archivos CEN originales, inmutables, SHA-256 + fecha de descarga en `data-raw/CHECKSUMS.sha256`.
- `release/v1.0/`: 4 tablas en CSV+Parquet (orden determinístico, sin columna id), `data_dictionary.md`, `errata_log.csv`, `CHECKSUMS.sha256` único (publicables + 53 originales).
- Pipeline en `etl/` y `scripts/`: descarga (descargar_cen.sh), parseo y erratas (parsers.py), cargas con sanidad pre-commit (cargar_a_neon.py, cargar_horario_a_neon.py), validación censal (validar_horario.py), export (exportar_release.py).
- Decisiones metodológicas fechadas en `DECISIONS.md`.
