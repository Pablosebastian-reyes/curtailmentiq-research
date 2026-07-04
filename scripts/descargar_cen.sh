#!/bin/bash
# Descarga los archivos mensuales "Reducciones de Energia" del CEN hacia data-raw/.
# URLs levantadas del inventario Wayback CDX (2026-07-03) + verificacion HEAD directa.
# Politica: se descarga la ULTIMA version publicada de cada mes (v2/_2 sobre v1).
# Uso: bash scripts/descargar_cen.sh
set -u
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
B="https://www.coordinador.cl/wp-content/uploads"
RAW="$(cd "$(dirname "$0")/../data-raw" && pwd)"

URLS=(
  # --- 2022 (Eolica-y-Solar, nombre <Mes>-2022) ---
  "$B/2022/07/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Enero-2022.xlsx"
  "$B/2022/07/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Febrero-2022.xlsx"
  "$B/2022/07/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Marzo-2022.xlsx"
  "$B/2022/07/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Abril-2022.xlsx"
  "$B/2022/07/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Mayo-2022.xlsx"
  "$B/2022/07/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Junio-2022.xlsx"
  "$B/2022/08/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Julio-2022.xlsx"
  "$B/2022/09/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Agosto-2022.xlsx"
  "$B/2022/10/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Septiembre-2022.xlsx"
  "$B/2022/11/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Octubre-2022.xlsx"
  "$B/2022/12/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Noviembre-2022.xlsx"
  # --- 2023 ---
  "$B/2023/02/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Enero-2023.xlsx"
  "$B/2023/03/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Febrero-2023.xlsx"
  "$B/2023/04/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Marzo-2023.xlsx"
  "$B/2023/05/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Abril-2023.xlsx"
  "$B/2023/06/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Mayo-2023.xlsx"
  "$B/2023/07/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Junio-2023.xlsx"
  "$B/2023/08/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Julio-2023.xlsx"
  "$B/2023/09/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Agosto-2023.xlsx"
  "$B/2023/10/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Septiembre-2023.xlsx"
  "$B/2023/12/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Octubre-2023.xlsx"
  "$B/2023/12/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Noviembre-2023.xlsx"
  # --- 2024 (ultima version por mes; Junio-24_v2 ya esta local) ---
  "$B/2024/02/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Enero-24_v2.xlsx"
  "$B/2024/03/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Febrero-24_publicar.xlsx"
  "$B/2024/04/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Marzo-24_publicar_2.xlsx"
  "$B/2024/05/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Abril-24_publicar.xlsx"
  "$B/2024/06/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Mayo-24_publicar.xlsx"
  "$B/2024/08/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Julio-24-PE-PFV-HE_publicar-1.xlsx"
  "$B/2025/01/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Agosto-24-PE-PFV-HE_publicar_v2.xlsx"
  "$B/2025/01/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Septiembre-24-PE-PFV-HE_publicar_v2.xlsx"
  "$B/2025/01/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Octubre-24-PE-PFV-HE_publicar_v2.xlsx"
  "$B/2025/01/Reducciones-de-Energia-Eolica-y-Solar-en-el-SEN_Noviembre-24-PE-PFV_publicar.xlsx"
  # --- 2025 (Eolica-Solar-Hidro; Abril-25_Final y Octubre-25 ya estan locales) ---
  "$B/2025/02/Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_Enero-25-PE-PFV_Publicar.xlsx"
  "$B/2025/03/Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_Febrero-25-PE-PFV_Publicar.xlsx"
  "$B/2025/05/Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_Marzo-25-PE-PFV_Publicar.xlsx"
  "$B/2025/07/Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_Mayo-25-PE-PFV_Publicar.xlsx"
  "$B/2025/08/Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_Junio-25-PE-PFV_Publicar.xlsx"
  "$B/2025/09/Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_Julio-25-PE-PFV_Publicar.xlsx"
  "$B/2025/11/Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_Agosto-25-PE-PFV_Publicar.xlsx"
  "$B/2025/11/Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_Septiembre-25-PE-PFV_Publicar.xlsx"
  "$B/2026/01/Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_Noviembre-25-PE-PFV_Publicar.xlsx"
  # --- 2026 ---
  "$B/2026/07/Reducciones-de-Energia-Eolica-Solar-Hidro-en-el-SEN_Mayo-26-PE-PFV_Publicar.xlsx"
)

ok=0; fail=0
for url in "${URLS[@]}"; do
  name="${url##*/}"
  dest="$RAW/$name"
  if [ -s "$dest" ]; then
    echo "[ya existe] $name"; ok=$((ok+1)); continue
  fi
  code=$(curl -s -o "$dest" -w "%{http_code}" --max-time 180 --retry 2 --retry-delay 3 -A "$UA" "$url")
  # verificar codigo HTTP y firma zip de xlsx (PK\x03\x04)
  if [ "$code" = "200" ] && [ "$(head -c 2 "$dest" 2>/dev/null)" = "PK" ]; then
    echo "[ok] $name ($(du -k "$dest" | cut -f1) KB)"
    ok=$((ok+1))
  else
    echo "[FALLO http=$code] $name"
    rm -f "$dest"
    fail=$((fail+1))
  fi
  sleep 1
done
echo
echo "Descargados/presentes: $ok | Fallidos: $fail (de ${#URLS[@]})"
[ "$fail" -eq 0 ] || exit 1
