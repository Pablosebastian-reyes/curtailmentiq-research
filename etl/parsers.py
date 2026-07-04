import calendar
from datetime import date
from pathlib import Path

import pandas as pd
from dateutil.relativedelta import relativedelta

BASE = Path("/Users/pabloreyescerda/Desktop/PROYECTO-CURLTAIMENT")

MESES_ES = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6,
    "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12,
}


def periodo_de_origen(origen):
    """'Diciembre-2024' -> (2024, 12). El mes que le corresponde al archivo."""
    nombre, anio = origen.split("-")
    return int(anio), MESES_ES[nombre]

# ---------------------------------------------------------------------------
# Fuente canonica: curtailmentiq-research/data-raw/ (originales del CEN,
# inmutables, con SHA-256 en CHECKSUMS.sha256). Politica de versiones:
# cuando el CEN publico mas de una version de un mes, se usa la ULTIMA
# (v2/_2/Final sobre la original). Ver DECISIONS.md.
# ---------------------------------------------------------------------------
RAW = BASE / "curtailmentiq-research" / "data-raw"

# Un archivo por año calendario para el desglose diario acumulado: el reporte
# de diciembre de cada año cerrado, y el ultimo mes publicado del año en curso.
ARCHIVOS_ACUMULADO = [
    {"path": RAW / "Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Diciembre-2022.xlsx", "origen": "Diciembre-2022"},
    {"path": RAW / "Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Diciembre-2023_v2.xlsx", "origen": "Diciembre-2023"},
    {"path": RAW / "Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Diciembre-24-PE-PFV_Publicar.xlsx", "origen": "Diciembre-2024"},
    {"path": RAW / "Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_Diciembre-25-PE-PFV_Publicar.xlsx", "origen": "Diciembre-2025"},
    {"path": RAW / "Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_Mayo-26-PE-PFV_Publicar.xlsx", "origen": "Mayo-2026"},
]

SHEET_TECNOLOGIA = {
    "Acumulado-Anual-Eólico": "Eólica",
    "Acumulado-Anual-Solar": "Solar",
    "Acumulado-Anual-HP": "Hidro Pasada",
    "Acumulado-Anual-HE": "Hidro Embalse",
}

CSV_RANKING = BASE / "centrales_curtailment_2024_2025_full.csv"

# ---------------------------------------------------------------------------
# Datos HORARIOS: las hojas "Resumen-DiarioHorario-*" solo traen UN mes por
# archivo (el mes del reporte), asi que la serie horaria completa requiere
# TODOS los reportes mensuales: 53 meses de enero-2022 a mayo-2026.
# ---------------------------------------------------------------------------
_E22 = "Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_"       # 2022-2024
_E25 = "Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_"   # 2025-2026
_MESES_HORARIO = [
    # 2022
    ("Enero-2022", _E22 + "Enero-2022.xlsx"),
    ("Febrero-2022", _E22 + "Febrero-2022.xlsx"),
    ("Marzo-2022", _E22 + "Marzo-2022.xlsx"),
    ("Abril-2022", _E22 + "Abril-2022.xlsx"),
    ("Mayo-2022", _E22 + "Mayo-2022.xlsx"),
    ("Junio-2022", _E22 + "Junio-2022.xlsx"),
    ("Julio-2022", _E22 + "Julio-2022.xlsx"),
    ("Agosto-2022", _E22 + "Agosto-2022.xlsx"),
    ("Septiembre-2022", _E22 + "Septiembre-2022.xlsx"),
    ("Octubre-2022", _E22 + "Octubre-2022.xlsx"),
    ("Noviembre-2022", _E22 + "Noviembre-2022.xlsx"),
    ("Diciembre-2022", _E22 + "Diciembre-2022.xlsx"),
    # 2023
    ("Enero-2023", _E22 + "Enero-2023.xlsx"),
    ("Febrero-2023", _E22 + "Febrero-2023.xlsx"),
    ("Marzo-2023", _E22 + "Marzo-2023.xlsx"),
    ("Abril-2023", _E22 + "Abril-2023.xlsx"),
    ("Mayo-2023", _E22 + "Mayo-2023.xlsx"),
    ("Junio-2023", _E22 + "Junio-2023.xlsx"),
    ("Julio-2023", _E22 + "Julio-2023.xlsx"),
    ("Agosto-2023", _E22 + "Agosto-2023.xlsx"),
    ("Septiembre-2023", _E22 + "Septiembre-2023.xlsx"),
    ("Octubre-2023", _E22 + "Octubre-2023.xlsx"),
    ("Noviembre-2023", _E22 + "Noviembre-2023.xlsx"),
    ("Diciembre-2023", _E22 + "Diciembre-2023_v2.xlsx"),
    # 2024
    ("Enero-2024", _E22 + "Enero-24_v2.xlsx"),
    ("Febrero-2024", _E22 + "Febrero-24_publicar.xlsx"),
    ("Marzo-2024", _E22 + "Marzo-24_publicar_2.xlsx"),
    ("Abril-2024", _E22 + "Abril-24_publicar.xlsx"),
    ("Mayo-2024", _E22 + "Mayo-24_publicar.xlsx"),
    ("Junio-2024", _E22 + "Junio-24_publicar_v2.xlsx"),
    ("Julio-2024", _E22 + "Julio-24-PE-PFV-HE_publicar-1.xlsx"),
    ("Agosto-2024", _E22 + "Agosto-24-PE-PFV-HE_publicar_v2.xlsx"),
    ("Septiembre-2024", _E22 + "Septiembre-24-PE-PFV-HE_publicar_v2.xlsx"),
    ("Octubre-2024", _E22 + "Octubre-24-PE-PFV-HE_publicar_v2.xlsx"),
    ("Noviembre-2024", _E22 + "Noviembre-24-PE-PFV_publicar.xlsx"),
    ("Diciembre-2024", _E22 + "Diciembre-24-PE-PFV_Publicar.xlsx"),
    # 2025
    ("Enero-2025", _E25 + "Enero-25-PE-PFV_Publicar.xlsx"),
    ("Febrero-2025", _E25 + "Febrero-25-PE-PFV_Publicar.xlsx"),
    ("Marzo-2025", _E25 + "Marzo-25-PE-PFV_Publicar.xlsx"),
    ("Abril-2025", _E25 + "Abril-25-PE-PFV_Final.xlsx"),
    ("Mayo-2025", _E25 + "Mayo-25-PE-PFV_Publicar.xlsx"),
    ("Junio-2025", _E25 + "Junio-25-PE-PFV_Publicar.xlsx"),
    ("Julio-2025", _E25 + "Julio-25-PE-PFV_Publicar.xlsx"),
    ("Agosto-2025", _E25 + "Agosto-25-PE-PFV_Publicar.xlsx"),
    ("Septiembre-2025", _E25 + "Septiembre-25-PE-PFV_Publicar.xlsx"),
    ("Octubre-2025", _E25 + "Octubre-25-PE-PFV_Publicar.xlsx"),
    ("Noviembre-2025", _E25 + "Noviembre-25-PE-PFV_Publicar.xlsx"),
    ("Diciembre-2025", _E25 + "Diciembre-25-PE-PFV_Publicar.xlsx"),
    # 2026
    ("Enero-2026", _E25 + "Enero-26-PE-PFV_Publicar.xlsx"),
    ("Febrero-2026", _E25 + "Febrero-26-PE-PFV_Publicar.xlsx"),
    ("Marzo-2026", _E25 + "Marzo-26-PE-PFV_Publicar.xlsx"),
    ("Abril-2026", _E25 + "Abril-26-PE-PFV_Publicar.xlsx"),
    ("Mayo-2026", _E25 + "Mayo-26-PE-PFV_Publicar.xlsx"),
]
ARCHIVOS_HORARIO = [{"path": RAW / fn, "origen": o} for o, fn in _MESES_HORARIO]

# ---------------------------------------------------------------------------
# Parches de erratas del CEN (ver ERRATA_LOG.md en curtailmentiq-research):
# bloques mensuales del Acumulado-Anual publicados con la plantilla del mes
# anterior (30 columnas-dia), dejando el dia 31 fuera del desglose diario.
# El dia ausente se recupera agregando la hoja horaria del reporte mensual
# del propio mes, y se valida contra la columna "Total" por central del
# bloque errado (Total - suma(dias) = dia faltante).
# ---------------------------------------------------------------------------
PARCHES_DIARIO = [
    {
        # Errata 1: dia 2022-05-31 ausente en TODAS las tecnologias
        # (bloque de mayo con encabezados de abril repetidos).
        "fecha": date(2022, 5, 31),
        "tecnologias": None,  # todas las hojas del archivo
        "path": RAW / (_E22 + "Mayo-2022.xlsx"),
        "origen": "Mayo-2022",
    },
    {
        # Errata 2: dia 2025-05-31 ausente en las hojas Solar e Hidro
        # Embalse del reporte Diciembre-2025 (bloques de mayo con 30
        # columnas-dia; Eolica e HP si tienen las 31). El dia recuperado
        # de HE es 0.000 MWh: se incluye igual para mantener la
        # convencion de ceros explicitos y la continuidad por tecnologia.
        "fecha": date(2025, 5, 31),
        "tecnologias": {"Solar", "Hidro Embalse"},
        "path": RAW / (_E25 + "Mayo-25-PE-PFV_Publicar.xlsx"),
        "origen": "Mayo-2025",
    },
]


def parse_parche_diario(parche):
    """Recupera un dia ausente del desglose diario desde la hoja horaria.

    Devuelve filas (fecha, central, tecnologia, mwh, archivo_origen) con la
    suma de las 24 horas del dia del parche, incluyendo ceros explicitos
    (misma convencion que el resto de curtailment_diario).
    """
    filas = {}
    for sheet_name, tecnologia in SHEET_TECNOLOGIA_HORARIO.items():
        if parche["tecnologias"] is not None and tecnologia not in parche["tecnologias"]:
            continue
        xls = pd.ExcelFile(parche["path"])
        if sheet_name not in xls.sheet_names:
            continue
        regs = parse_diario_horario(parche["path"], sheet_name, tecnologia, parche["origen"])
        for (fecha, _hora, central, tec, mwh, _origen) in regs:
            if fecha == parche["fecha"]:
                clave = (fecha, central, tec)
                filas[clave] = filas.get(clave, 0.0) + mwh
    return [(f, c, t, mwh, parche["origen"]) for (f, c, t), mwh in sorted(filas.items())]

SHEET_TECNOLOGIA_HORARIO = {
    "Resumen-DiarioHorario-Eólico": "Eólica",
    "Resumen-DiarioHorario-Solar": "Solar",
    "Resumen-DiarioHorario-HP": "Hidro Pasada",
    "Resumen-DiarioHorario-HE": "Hidro Embalse",
}


# ---------------------------------------------------------------------------
# Parsers de los reportes del Coordinador Eléctrico Nacional
# ---------------------------------------------------------------------------
def parse_acumulado_anual(path, sheet_name, tecnologia, archivo_origen):
    df = pd.read_excel(path, sheet_name=sheet_name, header=None)
    n_rows, n_cols = df.shape
    registros = []
    i = 0
    prev_fechas_set = None
    while i < n_rows:
        col1 = df.iat[i, 1]
        # La fila de encabezado de cada bloque mensual dice "Central  /  Día"
        if isinstance(col1, str) and "central" in col1.lower() and "día" in col1.lower() and "/" in col1:
            fechas_col = {}
            for c in range(4, n_cols):
                val = df.iat[i, c]
                if pd.notna(val):
                    try:
                        fechas_col[c] = pd.to_datetime(val).date()
                    except Exception:
                        pass

            fechas_set = set(fechas_col.values())
            if fechas_set and fechas_set == prev_fechas_set:
                # Bloque con las mismas fechas que el bloque anterior: error de
                # armado del reporte (encabezados de fecha no actualizados).
                # Se corrige sumando 1 mes, asumiendo que representa el mes
                # siguiente al del bloque previo.
                print(f"    [aviso] {archivo_origen}/{sheet_name}: bloque en fila {i} repite fechas "
                      f"{min(fechas_set)}..{max(fechas_set)}; se corrige sumando 1 mes")
                fechas_col = {c: d + relativedelta(months=1) for c, d in fechas_col.items()}
                fechas_set = set(fechas_col.values())

            prev_fechas_set = fechas_set

            j = i + 1
            if j < n_rows and isinstance(df.iat[j, 1], str) and df.iat[j, 1].strip().lower() == "total":
                j += 1

            centrales_en_bloque = set()
            while j < n_rows and pd.notna(df.iat[j, 1]):
                # El sufijo "*" marca centrales en periodo de pruebas en los
                # reportes del CEN; es la misma planta fisica, asi que se
                # normaliza el nombre para no partir su serie en dos.
                central = str(df.iat[j, 1]).strip().rstrip("*").strip()
                valores = {}
                for c, fecha in fechas_col.items():
                    val = df.iat[j, c]
                    if pd.notna(val):
                        try:
                            valores[fecha] = float(val)
                        except (TypeError, ValueError):
                            continue

                if central in centrales_en_bloque:
                    # Fila duplicada de una central dentro del mismo bloque
                    # mensual; si son todos ceros, es una fila sobrante del
                    # armado del reporte y se ignora.
                    if all(v == 0 for v in valores.values()):
                        print(f"    [aviso] {archivo_origen}/{sheet_name}: fila {j} repite la central "
                              f"'{central}' dentro del bloque de la fila {i} con valores en 0; se ignora")
                        j += 1
                        continue
                centrales_en_bloque.add(central)

                for fecha, mwh in valores.items():
                    registros.append((fecha, central, tecnologia, mwh, archivo_origen))
                j += 1
            i = j
        else:
            i += 1
    return registros


def parse_resumen_mensual(path, archivo_origen):
    df = pd.read_excel(path, sheet_name="Resumen-Mensual", header=None)
    n_rows, n_cols = df.shape
    registros = []

    for i in range(n_rows):
        col1 = df.iat[i, 1]
        col2 = df.iat[i, 2]
        if pd.isna(col1) and pd.notna(col2):
            try:
                d0 = pd.to_datetime(col2)
            except Exception:
                continue
            if not (isinstance(d0, pd.Timestamp) and d0.day == 1):
                continue

            # Fila de meses encontrada: cada mes ocupa 3 columnas (GWh, ?, %)
            meses_col = {}
            for c in range(2, n_cols, 3):
                val = df.iat[i, c]
                if pd.notna(val):
                    try:
                        d = pd.to_datetime(val)
                        meses_col[c] = (d.year, d.month)
                    except Exception:
                        pass

            j = i + 1
            while j < n_rows and pd.notna(df.iat[j, 1]):
                tecnologia = str(df.iat[j, 1]).strip()
                for c, (anio, mes) in meses_col.items():
                    gwh = df.iat[j, c]
                    if pd.notna(gwh):
                        # Los reportes de meses intermedios rellenan los meses
                        # aun no publicados con "-": esa celda no es dato.
                        try:
                            gwh = float(gwh)
                        except (TypeError, ValueError):
                            continue
                        pct_val = df.iat[j, c + 2] if c + 2 < n_cols else None
                        try:
                            porcentaje = float(pct_val) if pd.notna(pct_val) else None
                        except (TypeError, ValueError):
                            porcentaje = None
                        registros.append((anio, mes, tecnologia, gwh, porcentaje, archivo_origen))
                j += 1
            break  # un solo bloque "Acumulado <año>" por archivo

    return registros


def parse_diario_horario(path, sheet_name, tecnologia, archivo_origen):
    """Lee una hoja "Resumen-DiarioHorario-*".

    Cada dia es un bloque: encabezado "Central/Hora" (las 24 horas en las
    columnas 4+), una fila por central, y al final una fila "Total" (suma de
    centrales) que se ignora para no contar dos veces.

    La FECHA NO se toma de la etiqueta del Excel: los reportes del CEN la
    pierden, la repiten o dejan casilleros vacios. En cambio se asigna por la
    POSICION del bloque dentro del mes del archivo: el primer bloque es el dia
    1, el segundo el dia 2, etc. Los bloques cuya posicion excede los dias del
    mes (casilleros de plantilla del mes siguiente) se descartan. La Fase 5
    valida cada dia contra el total diario.

    Devuelve tuplas (fecha, hora, central, tecnologia, mwh, archivo_origen).
    """
    anio, mes = periodo_de_origen(archivo_origen)
    dias_mes = calendar.monthrange(anio, mes)[1]

    df = pd.read_excel(path, sheet_name=sheet_name, header=None)
    n_rows, n_cols = df.shape
    registros = []
    pos = 0  # numero de orden del bloque de datos dentro de la hoja
    i = 0
    while i < n_rows:
        col1 = df.iat[i, 1]
        if not isinstance(col1, str) or not ("central" in col1.lower() and "hora" in col1.lower()):
            i += 1
            continue

        # Encabezado "Central/Hora": mapear que columna es cada hora.
        horas_col = {}
        for c in range(4, n_cols):
            val = df.iat[i, c]
            if pd.notna(val):
                try:
                    h = int(round(float(val)))
                    if 1 <= h <= 24:
                        horas_col[c] = h
                except (TypeError, ValueError):
                    pass

        if not horas_col:
            # No es un encabezado de datos real (p.ej. el titulo de la hoja,
            # que tambien contiene las palabras "central" y "horaria").
            i += 1
            continue

        pos += 1
        dia = pos

        # Leer las centrales del bloque hasta la fila "Total".
        j = i + 1
        centrales_en_bloque = set()
        filas_bloque = []
        while j < n_rows:
            cj = df.iat[j, 1]
            if pd.isna(cj):
                j += 1
                continue
            if not isinstance(cj, str):
                break  # llego la fila de fecha del siguiente bloque
            etiqueta = cj.strip()
            if etiqueta.lower() == "total":
                j += 1
                break  # fin del bloque; la fila Total no se carga
            if "central" in etiqueta.lower() and "hora" in etiqueta.lower():
                break  # encabezado del siguiente bloque (sin Total de por medio)
            central = etiqueta.rstrip("*").strip()

            valores = {}
            for c, hora in horas_col.items():
                val = df.iat[j, c]
                if pd.notna(val):
                    try:
                        valores[hora] = float(val)
                    except (TypeError, ValueError):
                        continue

            if central in centrales_en_bloque and all(v == 0 for v in valores.values()):
                # Fila duplicada de una central con todo en 0: sobrante; se ignora.
                j += 1
                continue
            centrales_en_bloque.add(central)
            filas_bloque.append((central, valores))
            j += 1
        i = j

        # Asignar fecha por posicion. Descartar bloques que se pasan del mes
        # (casilleros del mes siguiente) o que estan completamente vacios.
        if dia > dias_mes:
            continue
        if not any(vals for _, vals in filas_bloque):
            continue
        fecha = date(anio, mes, dia)
        for central, valores in filas_bloque:
            for hora, mwh in valores.items():
                registros.append((fecha, hora, central, tecnologia, mwh, archivo_origen))

    return registros
