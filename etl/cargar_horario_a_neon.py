"""Fase 4: carga de los datos HORARIOS a Neon (tabla curtailment_horario).

Lee las hojas "Resumen-DiarioHorario-*" de los 53 reportes mensuales del CEN
(enero-2022 a mayo-2026, ver ARCHIVOS_HORARIO en parsers.py) y las carga.
Es idempotente: vacia y recarga la tabla en cada corrida, en UNA transaccion
(si algo falla, la tabla queda como estaba).

Las fechas se asignan por la posicion del bloque dentro del mes del archivo
(ver parse_diario_horario en parsers.py), porque las etiquetas de fecha del
CEN vienen con errores (perdidas, repetidas o casilleros vacios). Antes del
commit se verifica que el rango completo 2022-01-01..2026-05-31 quedo sin
dias vacios; la validacion energetica mes a mes contra curtailment_diario
se hace por separado (validar_horario.py).
"""
import os
from datetime import date

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

from parsers import BASE, ARCHIVOS_HORARIO, SHEET_TECNOLOGIA_HORARIO, parse_diario_horario

load_dotenv(BASE / "curtailmentiq-model" / ".env")

FECHA_MIN = date(2022, 1, 1)
FECHA_MAX = date(2026, 5, 31)  # corte v1.0
DIAS_ESPERADOS = (FECHA_MAX - FECHA_MIN).days + 1

# Verificar que esten todos los archivos antes de abrir la transaccion
faltan = [a["path"].name for a in ARCHIVOS_HORARIO if not a["path"].exists()]
assert not faltan, f"archivos faltantes en data-raw: {faltan}"

print(f"Conectando a Neon... ({len(ARCHIVOS_HORARIO)} archivos por cargar)")
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS curtailment_horario (
    id BIGSERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    hora SMALLINT NOT NULL,
    central_codigo TEXT NOT NULL,
    tecnologia TEXT NOT NULL,
    mwh NUMERIC NOT NULL,
    archivo_origen TEXT NOT NULL,
    UNIQUE (fecha, hora, central_codigo)
);
CREATE INDEX IF NOT EXISTS idx_horario_tec_fecha ON curtailment_horario (tecnologia, fecha);
""")
conn.commit()

# ---------------------------------------------------------------------------
# Carga idempotente: TRUNCATE + insercion archivo por archivo, un solo commit
# ---------------------------------------------------------------------------
print("Cargando datos (TRUNCATE + 53 archivos, una transaccion)...")
cur.execute("TRUNCATE curtailment_horario RESTART IDENTITY;")
total = 0
for archivo in ARCHIVOS_HORARIO:
    path, origen = archivo["path"], archivo["origen"]
    xls = pd.ExcelFile(path)
    filas = []
    for sheet_name, tecnologia in SHEET_TECNOLOGIA_HORARIO.items():
        if sheet_name not in xls.sheet_names:
            continue
        filas.extend(parse_diario_horario(path, sheet_name, tecnologia, origen))
    execute_values(
        cur,
        "INSERT INTO curtailment_horario (fecha, hora, central_codigo, tecnologia, mwh, archivo_origen) VALUES %s",
        filas,
        page_size=10000,
    )
    total += len(filas)
    print(f"  {origen:16s}: {len(filas):>9,} filas (acumulado {total:,})", flush=True)

# Sanidad ANTES del commit: rango y continuidad diaria completos
cur.execute("SELECT COUNT(DISTINCT fecha), MIN(fecha), MAX(fecha) FROM curtailment_horario")
n_dias, fmin, fmax = cur.fetchone()
if (n_dias, fmin, fmax) != (DIAS_ESPERADOS, FECHA_MIN, FECHA_MAX):
    cur.execute("""
        SELECT d::date FROM generate_series(%s::date, %s::date, '1 day') d
        WHERE d::date NOT IN (SELECT DISTINCT fecha FROM curtailment_horario)
        LIMIT 15""", (FECHA_MIN, FECHA_MAX))
    print(f"  !! dias vacios: {[str(r[0]) for r in cur.fetchall()]}")
    conn.rollback()
    raise SystemExit(f"ABORTADO (rollback): {n_dias} dias, rango {fmin}..{fmax}; "
                     f"esperado {DIAS_ESPERADOS} dias, {FECHA_MIN}..{FECHA_MAX}")
conn.commit()
print(f"  COMMIT: {total:,} filas | {n_dias} dias continuos {fmin}..{fmax}")

# ---------------------------------------------------------------------------
# Resumen final
# ---------------------------------------------------------------------------
print("\nResumen en Neon:")
cur.execute("SELECT COUNT(*), MIN(fecha), MAX(fecha), COUNT(DISTINCT central_codigo) FROM curtailment_horario")
n, fmin, fmax, ncent = cur.fetchone()
print(f"  filas: {n:,} | fechas: {fmin} a {fmax} | centrales: {ncent}")

cur.execute("SELECT tecnologia, COUNT(*), ROUND(SUM(mwh)::numeric,0) FROM curtailment_horario GROUP BY tecnologia ORDER BY tecnologia")
print("  por tecnologia (filas | MWh):")
for tec, c, s in cur.fetchall():
    print(f"    {tec:15s}: {c:>9,} | {s:>12,.0f}")

cur.close()
conn.close()
print("\nListo.")
