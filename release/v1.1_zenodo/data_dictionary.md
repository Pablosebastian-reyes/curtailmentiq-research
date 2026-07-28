# Data dictionary: Curtailment SEN Chile, dataset v1.0

**Corte:** 2022-01-01 a 2026-05-31 (1,612 días continuos, sin días faltantes) · **Congelado:** 2026-07-04
**Fuente:** reportes mensuales oficiales "Reducciones de Energía Eólica, Solar e Hidro en el SEN" del Coordinador Eléctrico Nacional (CEN), Chile (53 archivos originales preservados en `data-raw/` con SHA-256).
**Formatos:** cada tabla se publica en CSV (UTF-8, header, separador coma) y Parquet (compresión zstd) con contenido idéntico y orden determinístico.
**Convenciones globales:** los ceros son explícitos (un registro con `mwh = 0` significa "sin curtailment ese día/hora", no dato faltante) · la columna `id` de la base de datos (secuencial de carga) se excluye del release: la clave natural de cada tabla se indica abajo · valores de `tecnologia`: `Solar`, `Eólica`, `Hidro Pasada`, `Hidro Embalse` (las hidro se reportan desde 2024-06-01 en la serie diaria y desde 2024-07-01 en la horaria, ver errata nº 5) · separador decimal punto · fechas ISO-8601 (YYYY-MM-DD).

---

## curtailment_daily.csv / .parquet (293,678 filas)

Curtailment diario por central. Clave natural: (`fecha`, `central_codigo`). Orden: `fecha`, `central_codigo`.

| columna | tipo (parquet) | descripción |
|---|---|---|
| fecha | date32 | Día calendario del registro (2022-01-01 a 2026-05-31, continuo). |
| central_codigo | string | Código de la central/unidad según la nomenclatura del reporte de reducciones del CEN. |
| tecnologia | string | Tecnología según el reporte del año correspondiente (una central reclasificada por el CEN conserva aquí la etiqueta de cada reporte anual). |
| mwh | float64 | Energía reducida (curtailment) del día, en MWh. Cero explícito. |
| archivo_origen | string | Reporte mensual CEN del que proviene la fila (p.ej. `Diciembre-2024`); los 186 registros recuperados por errata llevan el reporte mensual usado para recuperarlos (`Mayo-2022`, `Mayo-2025`; erratas nº 1 y 2). |

Nota: serie diaria construida desde el desglose "Acumulado-Anual" del último reporte publicado de cada año (política "última versión gana"; ver DECISIONS.md). Suma total: 19,030,463.14 MWh. Cuadra exacto (±0.001 GWh) con los totales anuales oficiales del CEN 2022-2026.

## curtailment_hourly.csv / .parquet (6,906,761 filas)

Curtailment horario por central. Clave natural: (`fecha`, `hora`, `central_codigo`). Orden: `fecha`, `hora`, `central_codigo`.

| columna | tipo (parquet) | descripción |
|---|---|---|
| fecha | date32 | Día calendario (2022-01-01 a 2026-05-31, continuo). |
| hora | int16 | Hora del día en convención CEN 1–24 (la hora h cubre el intervalo que termina en h:00). |
| central_codigo | string | Código de la central/unidad (misma nomenclatura que curtailment_daily). |
| tecnologia | string | Tecnología según el reporte mensual correspondiente. |
| mwh | float64 | Energía reducida en esa hora, en MWh. Cero explícito. |
| archivo_origen | string | Reporte mensual CEN del que proviene la fila (cada reporte aporta solo su propio mes; p.ej. `Marzo-2023`). |

Nota: construida desde las hojas "Resumen-DiarioHorario-\*" de los 53 reportes mensuales. Las fechas se asignan por posición del bloque dentro del mes (las etiquetas del CEN vienen dañadas; errata nº 4), validado censalmente contra la serie diaria: 50 de 53 meses con discrepancia ponderada ≤ 1% y 35 en 0.0000%; los 3 meses sobre el 1% corresponden a inconsistencias del propio CEN (erratas nº 5, 6 y 7). Los demás meses no exactos (2025-07 a 2026-02, discrepancias de 0.008% a 0.11%) se deben a que el operador reasigna la misma energía mensual de forma distinta entre unidades hidro de pasada hermanas entre su hoja horaria mensual y su cierre anual, con efecto neto cero a nivel de sistema: el mismo mecanismo de las erratas nº 6 y 7.

## plants.csv / .parquet (300 filas)

Catálogo mínimo de centrales presentes en las series. Clave: `central_codigo`. Orden: `central_codigo`.

| columna | tipo (parquet) | descripción |
|---|---|---|
| central_codigo | string | Código de la central/unidad (75 Solar, 56 Eólica, 140 Hidro Pasada, 29 Hidro Embalse). |
| tecnologia | string | Clasificación tecnológica más reciente informada por el CEN (si una central fue reclasificada, aquí gana la última). |

## plants_metadata.csv / .parquet (300 filas)

Atributos de cada central según el catálogo de instalaciones del CEN (Infotécnica), emparejado por nombre. Clave: `central_codigo`. Orden: `central_codigo`. Cobertura 300/300.

| columna | tipo (parquet) | descripción |
|---|---|---|
| central_codigo | string | Código de la central (FK a plants y a las series). |
| cen_id | int32 | id_central en el catálogo CEN. |
| cen_nombre | string | Nombre oficial de la central en el catálogo CEN. |
| match_metodo | string | Método de emparejamiento reporte↔catálogo: `exacto` (129), `sin_unidad` (146), `contenido` (10), `fuzzy` (4, score ≥ 0.85), `manual` (11, verificados a mano). |
| region | string | Región de Chile. |
| provincia | string | Provincia. |
| comuna | string | Comuna. |
| latitud | float64 | Latitud WGS84 (convertida desde UTM husos 18/19 sur del catálogo). |
| longitud | float64 | Longitud WGS84. |
| potencia_mw | float64 | Potencia máxima bruta declarada, MW. |
| fecha_operacion | date32 | Fecha de entrada en operación (nulo en 8 centrales). |
| propietario | string | Empresa propietaria. |
| coordinado | string | Coordinado responsable ante el CEN. |
| estado | string | Estado en el catálogo (Operativa, En Construcción, Autodespacho DS88, etc.). |
| tipo_tecnologia | string | Subtipo del catálogo (Parque fotovoltaico, Parque eólico, Hidroeléctrica de pasada, Minihidro de pasada, Hidroeléctrica de embalse). |
| tipo_conv_energia | string | Tipo de conversión de energía. |
| punto_conexion | string | Punto de conexión al sistema. |
| conv_ernc | string | Clasificación Convencional / ERNC. |

## errata_log.csv (8 filas)

Las 7 erratas/límites de fuente del CEN detectados, con regla determinística, tratamiento y evidencia. Derivado automáticamente de `ERRATA_LOG.md` (fuente única, con el detalle narrativo completo).

| columna | descripción |
|---|---|
| numero | Número de errata (1–7). |
| archivos_fuente | Archivo(s) CEN afectados (en data-raw/). |
| hoja_campo | Hoja y campo afectados. |
| regla_deteccion | Regla determinística verificable por código. |
| tratamiento | corregida / recuperada / límite de fuente. |
| evidencia_contraste | Fuente independiente que valida el tratamiento. |

## CHECKSUMS.sha256

SHA-256 de todos los archivos publicables del release y de los 53 archivos originales del CEN. Rutas relativas a la raíz del repositorio; verificar con `shasum -a 256 -c release/v1.0/CHECKSUMS.sha256` desde la raíz. Las fechas de descarga de cada original están en `data-raw/CHECKSUMS.sha256`.

## Exclusiones del release

Las tablas `centrales_ranking_2024_2025` (derivable de curtailment_daily) y las predicciones del modelo (producto separado) NO forman parte del dataset v1.0.
