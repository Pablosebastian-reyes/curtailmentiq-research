import os
from datetime import date, timedelta

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

from parsers import (
    BASE, ARCHIVOS_ACUMULADO, SHEET_TECNOLOGIA, CSV_RANKING, PARCHES_DIARIO,
    parse_acumulado_anual, parse_resumen_mensual, parse_parche_diario,
)

load_dotenv(BASE / "curtailmentiq-model" / ".env")

FECHA_MIN = date(2022, 1, 1)
FECHA_MAX = date(2026, 5, 31)  # corte v1.0

# ---------------------------------------------------------------------------
# Extraer todos los datos de los archivos Excel
# ---------------------------------------------------------------------------
print("Leyendo archivos Excel...")

curtailment_rows = []
resumen_rows = []

for archivo in ARCHIVOS_ACUMULADO:
    path = archivo["path"]
    origen = archivo["origen"]
    xls = pd.ExcelFile(path)

    for sheet_name, tecnologia in SHEET_TECNOLOGIA.items():
        if sheet_name not in xls.sheet_names:
            continue
        filas = parse_acumulado_anual(path, sheet_name, tecnologia, origen)
        curtailment_rows.extend(filas)
        print(f"  {origen} / {sheet_name}: {len(filas)} filas")

    filas_resumen = parse_resumen_mensual(path, origen)
    resumen_rows.extend(filas_resumen)
    print(f"  {origen} / Resumen-Mensual: {len(filas_resumen)} filas")

# ---------------------------------------------------------------------------
# Parches de erratas: dias ausentes del desglose diario, recuperados desde
# la hoja horaria del reporte mensual del propio mes (ver ERRATA_LOG.md).
# ---------------------------------------------------------------------------
parche_rows = []
for parche in PARCHES_DIARIO:
    filas_parche = parse_parche_diario(parche)
    suma = sum(f[3] for f in filas_parche)
    print(f"  [parche] {parche['fecha']} desde {parche['origen']}: "
          f"{len(filas_parche)} filas, sum={suma:,.3f} MWh")
    parche_rows.extend(filas_parche)

print(f"\nTotal curtailment_diario: {len(curtailment_rows) + len(parche_rows)} filas "
      f"({len(parche_rows)} de parches)")
print(f"Total resumen_mensual: {len(resumen_rows)} filas")

# ---------------------------------------------------------------------------
# Catalogo de centrales (deducido de curtailment_diario)
#
# Algunas centrales hidro fueron reclasificadas durante 2024 (p.ej. de
# "Hidro Embalse" a "Hidro Pasada"); curtailment_diario conserva la
# tecnologia tal como la informo cada reporte, pero el catalogo usa la
# clasificacion mas reciente (los archivos se procesan en orden cronologico,
# asi que la ultima ocurrencia gana). Las filas de parche no pisan el
# catalogo: solo agregan centrales que no aparezcan en ningun acumulado.
# ---------------------------------------------------------------------------
central_a_tecnologia = {}
for (_, central, tecnologia, _, _) in curtailment_rows:
    central_a_tecnologia[central] = tecnologia
for (_, central, tecnologia, _, _) in parche_rows:
    central_a_tecnologia.setdefault(central, tecnologia)
curtailment_rows.extend(parche_rows)
centrales_rows = sorted(central_a_tecnologia.items())
print(f"Total centrales (catalogo): {len(centrales_rows)}")

# ---------------------------------------------------------------------------
# Sanidad ANTES de tocar la base: continuidad diaria POR TECNOLOGIA dentro
# del rango activo de cada una, rango global v1.0 y unicidad de claves.
# Este es el detector deterministico de la errata "dia final ausente"
# (ERRATA_LOG #1 y #2). Si algo falla, se aborta aqui.
# ---------------------------------------------------------------------------
fechas_por_tec = {}
for (f, _, tec, _, _) in curtailment_rows:
    fechas_por_tec.setdefault(tec, set()).add(f)
problemas = []
for tec, fechas_tec in sorted(fechas_por_tec.items()):
    d = min(fechas_tec)
    while d <= max(fechas_tec):
        if d not in fechas_tec:
            problemas.append((tec, d))
        d += timedelta(days=1)
assert not problemas, f"dias ausentes dentro del rango activo de una tecnologia: {problemas[:10]}"

fechas = set().union(*fechas_por_tec.values())
assert min(fechas) == FECHA_MIN and max(fechas) == FECHA_MAX, \
    f"rango inesperado: {min(fechas)} a {max(fechas)} (esperado {FECHA_MIN} a {FECHA_MAX})"
assert len(fechas) == (FECHA_MAX - FECHA_MIN).days + 1, "dias vacios en el rango global v1.0"
claves = [(r[0], r[1]) for r in curtailment_rows]
assert len(claves) == len(set(claves)), "duplicados de (fecha, central) en las filas a cargar"
print(f"Sanidad OK: {FECHA_MIN} a {FECHA_MAX} continuo, por tecnologia y global; claves unicas.")
for tec, fechas_tec in sorted(fechas_por_tec.items()):
    print(f"  {tec:14s}: {min(fechas_tec)} a {max(fechas_tec)} ({len(fechas_tec)} dias)")

# ---------------------------------------------------------------------------
# Ranking 2024-2025 (CSV)
# ---------------------------------------------------------------------------
ranking_df = pd.read_csv(CSV_RANKING)
ranking_rows = list(
    ranking_df[["ranking", "central_codigo", "tecnologia", "mwh_2024", "mwh_2025", "mwh_total", "gwh_total"]]
    .itertuples(index=False, name=None)
)
print(f"Total centrales_ranking_2024_2025: {len(ranking_rows)} filas")

# ---------------------------------------------------------------------------
# Conexion a Neon y creacion de tablas
# ---------------------------------------------------------------------------
print("\nConectando a Neon...")
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS centrales (
    central_codigo TEXT PRIMARY KEY,
    tecnologia TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS curtailment_diario (
    id BIGSERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    central_codigo TEXT NOT NULL REFERENCES centrales(central_codigo),
    tecnologia TEXT NOT NULL,
    mwh NUMERIC NOT NULL,
    archivo_origen TEXT NOT NULL,
    UNIQUE (fecha, central_codigo)
);

CREATE TABLE IF NOT EXISTS resumen_mensual (
    id BIGSERIAL PRIMARY KEY,
    anio INT NOT NULL,
    mes INT NOT NULL,
    tecnologia TEXT NOT NULL,
    gwh NUMERIC,
    porcentaje NUMERIC,
    archivo_origen TEXT NOT NULL,
    UNIQUE (anio, mes, tecnologia)
);

CREATE TABLE IF NOT EXISTS centrales_ranking_2024_2025 (
    ranking INT,
    central_codigo TEXT PRIMARY KEY,
    tecnologia TEXT,
    mwh_2024 NUMERIC,
    mwh_2025 NUMERIC,
    mwh_total NUMERIC,
    gwh_total NUMERIC
);
""")
conn.commit()
print("Tablas verificadas/creadas.")

# ---------------------------------------------------------------------------
# Carga de datos (se vacian las tablas antes para permitir re-ejecutar el script)
# ---------------------------------------------------------------------------
print("\nCargando datos...")

cur.execute("TRUNCATE curtailment_diario, resumen_mensual, centrales_ranking_2024_2025, centrales RESTART IDENTITY CASCADE;")

execute_values(cur, "INSERT INTO centrales (central_codigo, tecnologia) VALUES %s", centrales_rows)
print(f"  centrales: {len(centrales_rows)} filas insertadas")

execute_values(
    cur,
    "INSERT INTO curtailment_diario (fecha, central_codigo, tecnologia, mwh, archivo_origen) VALUES %s",
    curtailment_rows,
    page_size=5000,
)
print(f"  curtailment_diario: {len(curtailment_rows)} filas insertadas")

execute_values(
    cur,
    "INSERT INTO resumen_mensual (anio, mes, tecnologia, gwh, porcentaje, archivo_origen) VALUES %s",
    resumen_rows,
    page_size=5000,
)
print(f"  resumen_mensual: {len(resumen_rows)} filas insertadas")

execute_values(
    cur,
    "INSERT INTO centrales_ranking_2024_2025 (ranking, central_codigo, tecnologia, mwh_2024, mwh_2025, mwh_total, gwh_total) VALUES %s",
    ranking_rows,
)
print(f"  centrales_ranking_2024_2025: {len(ranking_rows)} filas insertadas")

conn.commit()

# ---------------------------------------------------------------------------
# Resumen final
# ---------------------------------------------------------------------------
print("\nResumen final en Neon:")
for tabla in ["centrales", "curtailment_diario", "resumen_mensual", "centrales_ranking_2024_2025"]:
    cur.execute(f"SELECT COUNT(*) FROM {tabla}")
    print(f"  {tabla}: {cur.fetchone()[0]} filas")

cur.execute("SELECT MIN(fecha), MAX(fecha), SUM(mwh) FROM curtailment_diario")
fmin, fmax, total_mwh = cur.fetchone()
print(f"\n  curtailment_diario: rango de fechas {fmin} a {fmax}, suma total = {total_mwh:,.2f} MWh")

cur.close()
conn.close()
print("\nListo.")
