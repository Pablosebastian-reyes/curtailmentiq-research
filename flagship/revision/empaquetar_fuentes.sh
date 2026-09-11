#!/bin/bash
# Arma el paquete de fuentes LaTeX para Editorial Manager y PRUEBA que compile
# en un directorio que contiene solo el contenido del zip, sin acceso al repo.
#
#   bash flagship/revision/empaquetar_fuentes.sh [commit]
#
# Falla con estado distinto de cero si el PDF aislado no da PAGINAS_ESPERADAS
# paginas, si hay errores de LaTeX, o si queda alguna referencia sin resolver.
# Si falta un archivo en el zip, la compilacion aislada es donde se descubre:
# TEXINPUTS se restringe al directorio actual y al arbol del sistema.
set -euo pipefail

C="${1:-HEAD}"
PAGINAS_ESPERADAS=36
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SALIDA="$REPO/entrega_revision"
TRABAJO="$(mktemp -d)"
trap 'rm -rf "$TRABAJO"' EXIT

PAQ="$TRABAJO/paquete"; mkdir -p "$PAQ"
cd "$REPO"

TABLAS=(tab_ablaciones tab_benchmarks tab_cota_alpha tab_diag_ampliado
        tab_diagnostico tab_escalera tab_estacional tab_mae tab_model_agnostic
        tab_panel tab_results tab_sensibilidad_frontera)
FIGURAS=(fig1_plants_map fig2_distribution fig3_rolling_coverage
         fig4_coverage_width fig5_regime_changepoints fig6_algorithm_flow
         fig7_model_agnostic fig8_ablations fig9_escalera_diagnostico)

# Todo sale del commit, no del arbol de trabajo, para que el zip corresponda
# demostrablemente a un estado versionado.
git show "${C}:flagship/segan/SEGAN_paper_FINAL.tex" > "$PAQ/SEGAN_paper_FINAL.tex"
for t in "${TABLAS[@]}"; do
  git show "${C}:resultados/tablas_tex/${t}.tex" > "$PAQ/${t}.tex"
done
git show "${C}:resultados/fase1/hiperparametros.tex" > "$PAQ/hiperparametros.tex"
for f in "${FIGURAS[@]}"; do
  git show "${C}:flagship/segan/figuras/${f}.pdf" > "$PAQ/${f}.pdf"
done
cp "$(kpsewhich elsarticle.cls)" "$PAQ/"
cp "$REPO/flagship/revision/README_paquete_fuentes.txt" "$PAQ/00_README_COMPILATION.txt"

# No hay .bbl ni .bib: la bibliografia es un thebibliography en linea. Se
# comprueba, porque si algun dia se pasa a BibTeX el zip deja de ser completo.
if grep -q '\\bibliography{' "$PAQ/SEGAN_paper_FINAL.tex"; then
  echo "ERROR: el .tex ahora usa \\bibliography{}; hay que incluir el .bbl" >&2
  exit 1
fi
grep -q '\\begin{thebibliography}' "$PAQ/SEGAN_paper_FINAL.tex" \
  || { echo "ERROR: no se encontro thebibliography en linea" >&2; exit 1; }

mkdir -p "$SALIDA"
ZIP="$SALIDA/11_fuentes_latex.zip"
rm -f "$ZIP"
( cd "$PAQ" && zip -q -X -r "$ZIP" . -x '.*' )

# ---- la prueba: compilar con SOLO el contenido del zip ----
AIS="$TRABAJO/aislado"; mkdir -p "$AIS"
( cd "$AIS" && unzip -q "$ZIP" )
cd "$AIS"
export TEXINPUTS=".:"
for i in 1 2 3; do
  pdflatex -interaction=nonstopmode SEGAN_paper_FINAL.tex > "pass$i.log" 2>&1 || true
done

fallas=0
[ -f SEGAN_paper_FINAL.pdf ] || { echo "FALLA: no se produjo PDF" >&2; exit 1; }
pag=$(pdfinfo SEGAN_paper_FINAL.pdf | awk '/^Pages/{print $2}')
err=$(grep -c '^!' pass3.log || true)
und=$(grep -ci 'undefined' pass3.log || true)
nof=$(grep -ci "not found" pass3.log || true)
# Un flotante mas alto que la pagina PIERDE filas en silencio: el PDF sale sin
# error y sin PDF truncado visible, solo con este aviso en el log. Paso asi la
# Tabla C.13, que se corta y se lleva las cuatro filas de semillas.
flo=$(grep -c "Float too large for page" pass3.log || true)

# Y la consecuencia, comprobada sobre el PDF y no sobre el .tex: las semillas
# de la Tabla C.13 tienen que estar impresas. Es el contenido que se perdia.
sem=0
for v in 42 20260720 11 20260901; do
  pdftotext -layout SEGAN_paper_FINAL.pdf - 2>/dev/null \
    | tr -s " " | grep -q "$v" || sem=$((sem+1))
done

[ "$pag" = "$PAGINAS_ESPERADAS" ] || { echo "FALLA: $pag paginas, se esperaban $PAGINAS_ESPERADAS" >&2; fallas=1; }
[ "$err" -eq 0 ] || { echo "FALLA: $err errores de LaTeX" >&2; fallas=1; }
[ "$und" -eq 0 ] || { echo "FALLA: $und referencias o citas sin resolver" >&2; fallas=1; }
[ "$nof" -eq 0 ] || { echo "FALLA: $nof archivos no encontrados (falta algo en el zip)" >&2; fallas=1; }
[ "$sem" -eq 0 ] || { echo "FALLA: $sem semillas de la Tabla C.13 no se imprimen" >&2; fallas=1; }
if [ "$flo" -ne 0 ]; then
  echo "FALLA: $flo flotante(s) mas altos que la pagina; se pierden filas" >&2
  grep "Float too large for page" pass3.log | sed 's/^/       /' >&2
  fallas=1
fi

echo "paquete:  $ZIP"
echo "  archivos:  $(unzip -l "$ZIP" | tail -1 | awk '{print $2}')"
echo "  tamano:    $(ls -l "$ZIP" | awk '{print $5}') bytes"
echo "  commit:    $(git -C "$REPO" rev-parse --short "$C")"
echo "prueba en aislamiento (TEXINPUTS restringido, sin acceso al repo):"
echo "  paginas:               $pag"
echo "  errores de LaTeX:      $err"
echo "  refs/citas sin resolver: $und"
echo "  archivos no hallados:  $nof"
echo "  flotantes sobredimensionados: $flo"
echo "  semillas C.13 sin imprimir:   $sem"
[ "$fallas" -eq 0 ] && echo "RESULTADO: el zip compila limpio en aislamiento" \
                    || { echo "RESULTADO: el zip NO esta completo o no compila" >&2; exit 1; }
