"""Fase 3: matching entre los códigos de central de curtailment_diario
y los nombres del catálogo oficial del CEN (catalogo_cen_centrales.json).

Etapas:
  1. exacto      : nombres normalizados idénticos
  2. sin_unidad  : idem quitando el sufijo de unidad (-1, -2...) de nuestro código
  3. fuzzy       : similitud difflib >= UMBRAL dentro de la misma tecnología

Salida: matching_centrales.csv + resumen en consola. No escribe en Neon.
"""
import json
import os
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

CARPETA = Path(__file__).parent
load_dotenv(CARPETA / ".env")

UMBRAL_FUZZY = 0.85

# Mapeos resueltos a mano (verificados con potencia, región y fechas de
# operación vs nuestra historia de curtailment). id = id_central del CEN.
MANUAL = {
    "PE-RENAICO-2": 1753,       # PE RENAICO II (el fuzzy lo confundía con RENAICO I)
    "PFV-ANDES": 374,           # PFV ANDES SOLAR
    "PFV-ANDES2A": 643,         # PFV ANDES SOLAR II
    "PFV-ANDES2B": 1850,        # PFV ANDES SOLAR II-B
    "PFV-ANDES3": 2322,         # PFV ANDES SOLAR III (familia ANDES: siempre manual)
    "PFV-ANDESIV": 2076,        # PFV ANDES SOLAR IV
    "PFV-POZOALMONTE-2": 401,   # PFV POZO ALMONTE SOLAR II (números romanos)
    "PFV-POZOALMONTE-3": 402,   # PFV POZO ALMONTE SOLAR III
    "PFV-SANPEDRO-GPG": 1672,   # PFV SAN PEDRO 104 MW Antofagasta (no el PMGD de 3 MW)
    # Codigos del reporte de reducciones que el CEN publica con otro nombre en
    # su catalogo: unidades MC1/MC2 de HIDROENERSUR en S/E Rio Bonito
    # (verificado por sufijo de unidad, tecnologia, potencia y conexion;
    # ver investigacion pre-freeze 2026-07-03).
    "CENTRALBONITO-MC1": 241,   # HP MC1 (9.0 MW, Puerto Octay, Los Lagos)
    "CENTRALFEO-MC2": 242,      # HP MC2 (3.2 MW, Puerto Octay, Los Lagos)
}
# Sin ficha en el catálogo del CEN (hoy vacío; mantener el mecanismo):
SIN_FICHA = set()

# Tecnología nuestra -> tipo_central del catálogo CEN
TIPO_CEN = {
    "Solar": "Solares",
    "Eólica": "Eólicas",
    "Hidro Pasada": "Hidroeléctricas",
    "Hidro Embalse": "Hidroeléctricas",
}

PREFIJOS = ("PMGD", "PMG", "PFV", "FV", "PE", "CENTRAL", "PAS", "EMB", "HID", "CH",
            "HP", "HE", "MINI", "MC")


def normalizar(nombre):
    """Mayúsculas, sin tildes, sin prefijos de tipo, solo letras y números."""
    s = unicodedata.normalize("NFKD", str(nombre).upper())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\[.*?\]", "", s)              # sufijos [EN_REVISION] etc.
    tokens = re.split(r"[\s\-_/]+", s.strip())
    while tokens and tokens[0] in PREFIJOS:
        tokens = tokens[1:]
    s = "".join(tokens)
    return re.sub(r"[^A-Z0-9]", "", s)


def sin_unidad(codigo_norm):
    """Quita un número final (unidad): RUCUE1 -> RUCUE."""
    return re.sub(r"\d+$", "", codigo_norm)


# --- Nuestras centrales (desde Neon) ---
conn = psycopg2.connect(os.environ["DATABASE_URL"])
nuestras = pd.read_sql("SELECT central_codigo, tecnologia FROM centrales ORDER BY 1", conn)
conn.close()
print(f"Centrales nuestras: {len(nuestras)}")

# --- Catálogo CEN (limpio, solo tecnologías relevantes) ---
catalogo = json.load(open(CARPETA / "catalogo_cen_centrales.json"))
catalogo = [c for c in catalogo
            if "[" not in (c["central"] or "")
            and c["tipo_central"] in ("Solares", "Eólicas", "Hidroeléctricas")]
print(f"Catálogo CEN (limpio, solar/eólica/hidro): {len(catalogo)}")

for c in catalogo:
    c["_norm"] = normalizar(c["central"])

por_tipo = {}
for c in catalogo:
    por_tipo.setdefault(c["tipo_central"], []).append(c)

# --- Matching por etapas ---
resultados = []
for _, fila in nuestras.iterrows():
    codigo, tecnologia = fila["central_codigo"], fila["tecnologia"]
    norm = normalizar(codigo)
    candidatos = por_tipo[TIPO_CEN[tecnologia]]

    match, metodo, score = None, None, None

    # 0) mapeo manual verificado
    if codigo in MANUAL:
        match = next(c for c in catalogo if c["id_central"] == MANUAL[codigo])
        metodo, score = "manual", 1.0
    elif codigo in SIN_FICHA:
        resultados.append({"central_codigo": codigo, "tecnologia": tecnologia,
                           "metodo": "SIN_FICHA_CEN", "score": None,
                           "cen_nombre": None, "cen_id": None})
        continue

    # 1) exacto
    if match is None:
        exactos = [c for c in candidatos if c["_norm"] == norm]
        if len(exactos) == 1:
            match, metodo, score = exactos[0], "exacto", 1.0
        else:
            # 2) sin número de unidad
            base = sin_unidad(norm)
            if base != norm:
                exactos = [c for c in candidatos if c["_norm"] == base]
                if len(exactos) == 1:
                    match, metodo, score = exactos[0], "sin_unidad", 1.0

    # 3) contención: nuestro nombre dentro del nombre del catálogo (o al revés),
    #    aceptado solo si hay UN único candidato posible
    if match is None:
        base = sin_unidad(norm)
        contenidos = [c for c in candidatos
                      if len(c["_norm"]) >= 4
                      and (norm in c["_norm"] or base in c["_norm"]
                           or c["_norm"] in norm)]
        if len(contenidos) == 1:
            match, metodo, score = contenidos[0], "contenido", 1.0

    # 4) fuzzy (sobre el código con y sin unidad)
    if match is None:
        mejor, mejor_score = None, 0.0
        for c in candidatos:
            s = max(SequenceMatcher(None, norm, c["_norm"]).ratio(),
                    SequenceMatcher(None, sin_unidad(norm), c["_norm"]).ratio())
            if s > mejor_score:
                mejor, mejor_score = c, s
        if mejor_score >= UMBRAL_FUZZY:
            match, metodo, score = mejor, "fuzzy", round(mejor_score, 3)

    resultados.append({
        "central_codigo": codigo,
        "tecnologia": tecnologia,
        "metodo": metodo or "SIN_MATCH",
        "score": score,
        "cen_nombre": match["central"] if match else None,
        "cen_id": match["id_central"] if match else None,
    })

df = pd.DataFrame(resultados)
df.to_csv(CARPETA / "matching_centrales.csv", index=False)

print("\nResumen del matching:")
print(df["metodo"].value_counts().to_string())

print("\n--- Matches FUZZY (revisar que sean razonables) ---")
fz = df[df["metodo"] == "fuzzy"][["central_codigo", "cen_nombre", "score"]]
print(fz.to_string(index=False) if len(fz) else "(ninguno)")

print("\n--- SIN MATCH (requieren revisión manual) ---")
sm = df[df["metodo"] == "SIN_MATCH"][["central_codigo", "tecnologia"]]
print(sm.to_string(index=False) if len(sm) else "(ninguno)")
