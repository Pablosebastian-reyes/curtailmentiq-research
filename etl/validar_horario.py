"""Fase 5 (v1.0): validacion mes a mes de curtailment_horario vs curtailment_diario.

Por cada (mes, central) compara la suma de las 24h del horario contra el total
diario acumulado del mes. Reporta la discrepancia PONDERADA por mes:
    disc(mes) = SUM(|mwh_horario - mwh_diario|) / SUM(mwh_diario)
(sumas sobre las centrales del mes). Umbral de alerta: 1%.

Solo lectura: no modifica la base.
"""
import os

import psycopg2
from dotenv import load_dotenv

from parsers import BASE

load_dotenv(BASE / "curtailmentiq-model" / ".env")

UMBRAL_PCT = 1.0

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.set_session(readonly=True, autocommit=True)
cur = conn.cursor()

cur.execute("""
WITH h AS (
    SELECT date_trunc('month', fecha)::date AS mes, central_codigo, SUM(mwh) AS mwh_h
    FROM curtailment_horario GROUP BY 1, 2
),
d AS (
    SELECT date_trunc('month', fecha)::date AS mes, central_codigo, SUM(mwh) AS mwh_d
    FROM curtailment_diario GROUP BY 1, 2
),
j AS (
    SELECT COALESCE(h.mes, d.mes) AS mes,
           COALESCE(h.central_codigo, d.central_codigo) AS central,
           COALESCE(h.mwh_h, 0) AS mwh_h,
           COALESCE(d.mwh_d, 0) AS mwh_d
    FROM h FULL OUTER JOIN d ON h.mes = d.mes AND h.central_codigo = d.central_codigo
)
SELECT mes,
       SUM(mwh_d) / 1000.0                                   AS gwh_diario,
       SUM(mwh_h) / 1000.0                                   AS gwh_horario,
       SUM(ABS(mwh_h - mwh_d)) / NULLIF(SUM(mwh_d), 0) * 100 AS disc_pond_pct,
       COUNT(*) FILTER (WHERE ABS(mwh_h - mwh_d) > 0.001)    AS centrales_con_dif
FROM j GROUP BY mes ORDER BY mes
""")
filas = cur.fetchall()

print(f"{'mes':10s} {'diario GWh':>12s} {'horario GWh':>12s} {'disc.pond.%':>12s} {'cent.dif':>9s}")
alertas = []
for mes, gd, gh, disc, ncent in filas:
    disc = float(disc) if disc is not None else 0.0
    marca = "  <-- ALERTA >1%" if disc > UMBRAL_PCT else ""
    if disc > UMBRAL_PCT:
        alertas.append((mes, disc))
    print(f"{str(mes)[:7]:10s} {float(gd):12.3f} {float(gh):12.3f} {disc:12.4f} {ncent:9d}{marca}")

print(f"\nMeses evaluados: {len(filas)} | con discrepancia ponderada > {UMBRAL_PCT}%: {len(alertas)}")

# Detalle de los meses en alerta: top centrales responsables
for mes, disc in alertas:
    print(f"\n--- Detalle {str(mes)[:7]} (disc. ponderada {disc:.3f}%) ---")
    cur.execute("""
        WITH h AS (
            SELECT central_codigo, tecnologia, SUM(mwh) AS mwh_h
            FROM curtailment_horario
            WHERE date_trunc('month', fecha)::date = %s GROUP BY 1, 2
        ),
        d AS (
            SELECT central_codigo, tecnologia, SUM(mwh) AS mwh_d
            FROM curtailment_diario
            WHERE date_trunc('month', fecha)::date = %s GROUP BY 1, 2
        ),
        j AS (
            SELECT COALESCE(h.central_codigo, d.central_codigo) AS central,
                   COALESCE(h.tecnologia, d.tecnologia) AS tec,
                   COALESCE(h.mwh_h, 0) AS mwh_h, COALESCE(d.mwh_d, 0) AS mwh_d
            FROM h FULL OUTER JOIN d ON h.central_codigo = d.central_codigo
        )
        SELECT central, tec, mwh_h, mwh_d, mwh_h - mwh_d AS dif
        FROM j WHERE ABS(mwh_h - mwh_d) > 0.001
        ORDER BY ABS(mwh_h - mwh_d) DESC LIMIT 10
    """, (mes, mes))
    for central, tec, mh, md, dif in cur.fetchall():
        print(f"    {central:22s} {tec:13s} horario={float(mh):11,.3f} diario={float(md):11,.3f} dif={float(dif):+10,.3f}")
    # desglose por tecnologia del mes
    cur.execute("""
        WITH h AS (SELECT tecnologia, SUM(mwh) m FROM curtailment_horario
                   WHERE date_trunc('month', fecha)::date = %s GROUP BY 1),
             d AS (SELECT tecnologia, SUM(mwh) m FROM curtailment_diario
                   WHERE date_trunc('month', fecha)::date = %s GROUP BY 1)
        SELECT COALESCE(h.tecnologia, d.tecnologia), COALESCE(h.m,0)/1000.0, COALESCE(d.m,0)/1000.0
        FROM h FULL OUTER JOIN d USING (tecnologia) ORDER BY 1
    """, (mes, mes))
    for tec, mh, md in cur.fetchall():
        print(f"    [tec] {tec:13s} horario={float(mh):9.3f} GWh  diario={float(md):9.3f} GWh")

cur.close()
conn.close()
