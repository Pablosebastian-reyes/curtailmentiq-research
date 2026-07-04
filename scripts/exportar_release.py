#!/usr/bin/env python3
"""Exporta el release v1.0 del dataset de curtailment SEN a release/v1.0/.

- 4 tablas (nombres en ingles) a CSV y Parquet, con orden deterministico y
  SIN la columna `id` (artefacto de carga; la clave real es fecha[/hora]+central).
- errata_log.csv derivado de la tabla de ERRATA_LOG.md (fuente unica).
- CHECKSUMS.sha256 unico: archivos publicables + los 53 originales del CEN
  en data-raw/ (rutas relativas a la raiz del repo).

Quedan FUERA del release: predicciones y centrales_ranking_2024_2025.
Uso: python scripts/exportar_release.py   (requiere DATABASE_URL en el
.env del pipeline o como variable de entorno; pyarrow instalado)
"""
import csv
import hashlib
import io
import os
import re
import sys
from pathlib import Path

import psycopg2
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parent.parent
RELEASE = REPO / "release" / "v1.0"
RAW = REPO / "data-raw"
ENV_PIPELINE = REPO.parent / "curtailmentiq-model" / ".env"

VERSION_CORTE = "2026-05-31"

TABLAS = {
    "curtailment_daily": {
        "sql": """SELECT fecha, central_codigo, tecnologia, mwh, archivo_origen
                  FROM curtailment_diario ORDER BY fecha, central_codigo""",
        "schema": {"fecha": pa.date32(), "central_codigo": pa.string(),
                   "tecnologia": pa.string(), "mwh": pa.float64(),
                   "archivo_origen": pa.string()},
    },
    "curtailment_hourly": {
        "sql": """SELECT fecha, hora, central_codigo, tecnologia, mwh, archivo_origen
                  FROM curtailment_horario ORDER BY fecha, hora, central_codigo""",
        "schema": {"fecha": pa.date32(), "hora": pa.int16(),
                   "central_codigo": pa.string(), "tecnologia": pa.string(),
                   "mwh": pa.float64(), "archivo_origen": pa.string()},
    },
    "plants": {
        "sql": "SELECT central_codigo, tecnologia FROM centrales ORDER BY central_codigo",
        "schema": {"central_codigo": pa.string(), "tecnologia": pa.string()},
    },
    "plants_metadata": {
        "sql": """SELECT central_codigo, cen_id, cen_nombre, match_metodo, region,
                         provincia, comuna, latitud, longitud, potencia_mw,
                         fecha_operacion, propietario, coordinado, estado,
                         tipo_tecnologia, tipo_conv_energia, punto_conexion, conv_ernc
                  FROM centrales_metadata ORDER BY central_codigo""",
        "schema": {"central_codigo": pa.string(), "cen_id": pa.int32(),
                   "cen_nombre": pa.string(), "match_metodo": pa.string(),
                   "region": pa.string(), "provincia": pa.string(),
                   "comuna": pa.string(), "latitud": pa.float64(),
                   "longitud": pa.float64(), "potencia_mw": pa.float64(),
                   "fecha_operacion": pa.date32(), "propietario": pa.string(),
                   "coordinado": pa.string(), "estado": pa.string(),
                   "tipo_tecnologia": pa.string(), "tipo_conv_energia": pa.string(),
                   "punto_conexion": pa.string(), "conv_ernc": pa.string()},
    },
}


def db_url():
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    with open(ENV_PIPELINE) as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                return line.strip().split("=", 1)[1]
    sys.exit("DATABASE_URL no encontrada")


def exportar_tablas():
    RELEASE.mkdir(parents=True, exist_ok=True)
    conn = psycopg2.connect(db_url())
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()
    for nombre, spec in TABLAS.items():
        csv_path = RELEASE / f"{nombre}.csv"
        with open(csv_path, "wb") as f:
            cur.copy_expert(
                f"COPY ({spec['sql']}) TO STDOUT WITH (FORMAT csv, HEADER true)", f)
        # Parquet desde el mismo CSV (garantiza contenido identico) con tipos explicitos
        tabla = pacsv.read_csv(
            csv_path,
            convert_options=pacsv.ConvertOptions(column_types=spec["schema"]),
        )
        pq.write_table(tabla, RELEASE / f"{nombre}.parquet", compression="zstd")
        print(f"  {nombre}: {tabla.num_rows:,} filas -> csv "
              f"{csv_path.stat().st_size/1e6:,.1f} MB | parquet "
              f"{(RELEASE / f'{nombre}.parquet').stat().st_size/1e6:,.1f} MB", flush=True)
    cur.close()
    conn.close()


def generar_errata_csv():
    """Deriva errata_log.csv de la tabla markdown de ERRATA_LOG.md (fuente unica)."""
    src = (REPO / "ERRATA_LOG.md").read_text(encoding="utf-8")
    filas = []
    for linea in src.splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|", linea)
        if not m:
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) == 6:
            filas.append(celdas)
    assert filas, "no se encontraron filas numeradas en ERRATA_LOG.md"
    out = RELEASE / "errata_log.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["numero", "archivos_fuente", "hoja_campo",
                    "regla_deteccion", "tratamiento", "evidencia_contraste"])
        w.writerows(filas)
    print(f"  errata_log.csv: {len(filas)} erratas")
    return len(filas)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def generar_checksums():
    """CHECKSUMS unico: publicables de release/v1.0 + 53 originales del CEN."""
    lineas = []
    publicables = sorted(p for p in RELEASE.iterdir()
                         if p.is_file() and p.name != "CHECKSUMS.sha256")
    for p in publicables:
        lineas.append(f"{sha256(p)}  {p.relative_to(REPO)}")
    originales = sorted(RAW.glob("*.xlsx"))
    for p in originales:
        lineas.append(f"{sha256(p)}  {p.relative_to(REPO)}")
    (RELEASE / "CHECKSUMS.sha256").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"  CHECKSUMS.sha256: {len(publicables)} publicables + {len(originales)} originales CEN")


if __name__ == "__main__":
    print(f"Exportando release v1.0 (corte {VERSION_CORTE}) a {RELEASE}")
    exportar_tablas()
    generar_errata_csv()
    generar_checksums()
    print("Listo. Recordar: data_dictionary.md se mantiene a mano junto al release.")
