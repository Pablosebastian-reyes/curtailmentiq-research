"""Fases 4 y 5: conversión UTM -> lat/lng y carga de centrales_metadata a Neon.

Combina matching_centrales.csv (Fase 3) con catalogo_cen_centrales.json
(Fase 1), convierte coordenadas y formatos chilenos, crea la tabla
centrales_metadata (sin tocar las tablas existentes) y la carga.
"""
import json
import os
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from pyproj import Transformer

CARPETA = Path(__file__).parent
load_dotenv(CARPETA / ".env")

# ---------------------------------------------------------------------------
# Insumos
# ---------------------------------------------------------------------------
matching = pd.read_csv(CARPETA / "matching_centrales.csv")
catalogo = {c["id_central"]: c for c in json.load(open(CARPETA / "catalogo_cen_centrales.json"))}

# Transformadores UTM -> lat/lng (WGS84). Chile usa husos 18 y 19, hemisferio sur.
# EPSG:32718 = UTM zona 18 sur, EPSG:32719 = UTM zona 19 sur.
TRANSFORMERS = {
    "18": Transformer.from_crs("EPSG:32718", "EPSG:4326", always_xy=True),
    "19": Transformer.from_crs("EPSG:32719", "EPSG:4326", always_xy=True),
}

# Erratas de huso en fichas del catalogo CEN (ver ERRATA_LOG.md #8):
# cen_id -> huso correcto. PE MESAMAVIDA (1758) declara '19H', pero con huso
# 18 la coordenada cae en su comuna declarada (Los Angeles, Biobio, lon -72.47,
# junto a la S/E Santa Luisa); con 19 caeria en Argentina (lon -66.46).
# Deteccion: longitud a >1.5 grados de la mediana de su region.
HUSO_MANUAL = {1758: "18"}


def num_cl(valor):
    """Número en formato mixto del catálogo CEN.

    Con coma -> decimal chileno ('6,0145' o '1.234,56').
    Sin coma -> el punto es decimal ('279542.74') o es un entero.
    """
    s = str(valor or "").strip()
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def fecha_cl(valor):
    """'01-03-2022' (DD-MM-AAAA) -> date; vacío -> None."""
    s = str(valor or "").strip()
    if not s:
        return None
    try:
        return pd.to_datetime(s, format="%d-%m-%Y").date()
    except ValueError:
        return None


def utm_a_latlng(este, norte, huso):
    """Convierte UTM (este, norte, huso tipo '19H') a (lat, lng).

    Repara erratas de escala del catálogo (dígitos de más o de menos,
    p.ej. '74712184' por '7471218.4'); el control de sanidad final
    sobre lat/lng descarta cualquier reparación incorrecta.
    """
    e, n = num_cl(este), num_cl(norte)
    zona = "".join(ch for ch in str(huso or "") if ch.isdigit())
    if e is None or n is None or zona not in TRANSFORMERS:
        return None, None
    # este válido: 6 cifras (~100.000-999.999 m); norte válido en Chile: ~5,4M-8,1M
    while e >= 1_000_000:
        e /= 10
    while n >= 10_000_000:
        n /= 10
    while 0 < n < 1_000_000:
        n *= 10
    lng, lat = TRANSFORMERS[zona].transform(e, n)
    # sanidad: Chile continental está aprox entre lat -17 y -56, lng -76 y -66
    if not (-57 < lat < -16 and -77 < lng < -65):
        return None, None
    return round(lat, 6), round(lng, 6)


# ---------------------------------------------------------------------------
# Construcción de las filas
# ---------------------------------------------------------------------------
filas = []
sin_coord = []
for _, m in matching.iterrows():
    if pd.isna(m["cen_id"]):
        continue  # las 2 sin ficha en el CEN
    c = catalogo[int(m["cen_id"])]
    huso = HUSO_MANUAL.get(int(m["cen_id"]), c["zona_huso"])
    lat, lng = utm_a_latlng(c["coordenada_este"], c["coordenada_norte"], huso)
    if lat is None:
        sin_coord.append((m["central_codigo"], c["coordenada_este"], c["coordenada_norte"], c["zona_huso"]))
    filas.append((
        m["central_codigo"],
        int(m["cen_id"]),
        c["central"],
        m["metodo"],
        c["region"] or None,
        c["provincia"] or None,
        c["comuna"] or None,
        lat, lng,
        num_cl(c["pot_max_bruta"]),
        fecha_cl(c["fecha_ent_oper"]),
        c["propietario"] or None,
        c["coordinado"] or None,
        c["estado"] or None,
        c["tipo_tecnologia"] or None,
        c["tipo_conv_energia"] or None,
        c["punto_conexion"] or None,
        c["conv_ernc"] or None,
    ))

print(f"Filas a cargar: {len(filas)} (cobertura completa 300/300, v1.0)")
if sin_coord:
    print(f"⚠ Sin coordenadas válidas ({len(sin_coord)}):")
    for s in sin_coord:
        print("  ", s)

# ---------------------------------------------------------------------------
# Carga a Neon
# ---------------------------------------------------------------------------
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS centrales_metadata (
    central_codigo    TEXT PRIMARY KEY,
    cen_id            INT NOT NULL,
    cen_nombre        TEXT NOT NULL,
    match_metodo      TEXT NOT NULL,
    region            TEXT,
    provincia         TEXT,
    comuna            TEXT,
    latitud           NUMERIC,
    longitud          NUMERIC,
    potencia_mw       NUMERIC,
    fecha_operacion   DATE,
    propietario       TEXT,
    coordinado        TEXT,
    estado            TEXT,
    tipo_tecnologia   TEXT,
    tipo_conv_energia TEXT,
    punto_conexion    TEXT,
    conv_ernc         TEXT
);
""")
cur.execute("TRUNCATE centrales_metadata;")  # permite re-ejecutar el script
execute_values(cur, """
    INSERT INTO centrales_metadata (
        central_codigo, cen_id, cen_nombre, match_metodo, region, provincia,
        comuna, latitud, longitud, potencia_mw, fecha_operacion, propietario,
        coordinado, estado, tipo_tecnologia, tipo_conv_energia, punto_conexion, conv_ernc
    ) VALUES %s
""", filas)
conn.commit()

# ---------------------------------------------------------------------------
# Validación: la tabla nueva quedó bien y las existentes están intactas
# ---------------------------------------------------------------------------
print("\n--- Validación ---")
cur.execute("SELECT COUNT(*), COUNT(latitud), COUNT(potencia_mw), COUNT(region) FROM centrales_metadata")
n, n_lat, n_pot, n_reg = cur.fetchone()
print(f"centrales_metadata: {n} filas | con lat/lng: {n_lat} | con potencia: {n_pot} | con región: {n_reg}")

cur.execute("""
    SELECT central_codigo FROM centrales c
    LEFT JOIN centrales_metadata m USING (central_codigo)
    WHERE m.central_codigo IS NULL ORDER BY 1
""")
sin_meta = [r[0] for r in cur.fetchall()]
print(f"centrales SIN metadata (esperado 0, cobertura 300/300): {len(sin_meta)} -> {sin_meta}")

# Las tablas previas no deben haber cambiado (estado v1.0, corte 2026-05-31)
esperado = {"centrales": 300, "curtailment_diario": 293678,
            "resumen_mensual": 214, "centrales_ranking_2024_2025": 126}
for tabla, n_esp in esperado.items():
    cur.execute(f"SELECT COUNT(*) FROM {tabla}")
    n_real = cur.fetchone()[0]
    estado = "OK" if n_real == n_esp else f"¡DIFERENCIA! esperado {n_esp}"
    print(f"{tabla}: {n_real} filas [{estado}]")

cur.execute("SELECT ROUND(SUM(mwh)::numeric,2) FROM curtailment_diario")
print(f"suma mwh curtailment_diario: {cur.fetchone()[0]} (esperado 19030463.14)")

print("\nMuestra (5 centrales con más curtailment 2024-2025):")
cur.execute("""
    SELECT m.central_codigo, m.region, m.comuna, m.latitud, m.longitud,
           m.potencia_mw, m.fecha_operacion, m.propietario
    FROM centrales_metadata m
    JOIN centrales_ranking_2024_2025 r USING (central_codigo)
    ORDER BY r.ranking LIMIT 5
""")
for fila in cur.fetchall():
    print("  ", fila)

cur.close()
conn.close()
print("\nListo.")
