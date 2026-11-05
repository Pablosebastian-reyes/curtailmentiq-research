#!/usr/bin/env python3
"""
R2-11. Version marcada R1 -> R2 con latexdiff.

Compara el .tex enviado en la R1 (aplanado, con sus tablas) con la version
aplanada de la R2. Tablas, figuras, algoritmos, ecuaciones y bibliografia se
tratan como bloques enteros (viejo tachado, nuevo marcado), que es lo que
compila y se lee. Antepone una nota breve, sin marcas, que explica el alcance
de los cambios.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_lib as L                      # noqa: E402

LATEXDIFF = str(Path.home() / 'Library/TinyTeX/bin/universal-darwin/latexdiff')
BASE = L.R2 / 'base_r1' / 'fuentes'
NUEVO = L.R2 / 'entrega' / 'fuentes'
OUT = L.R2 / 'entrega' / 'marcado_build'

NOTA = r"""
\noindent\fbox{\parbox{0.97\textwidth}{\small\textbf{Marked-up version (revision 2).} Deleted text is struck through in red and new text is underlined in blue. Tables, figures, the algorithm, displayed equations and the bibliography are marked as whole blocks. The main text was re-read and edited throughout, so many paragraphs appear as replaced; the response letter lists every substantive change.}}
\bigskip
"""


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for f in BASE.iterdir():
        if f.suffix in ('.pdf', '.cls', '.tex'):
            shutil.copy(f, OUT / f.name)
    for f in NUEVO.iterdir():
        if f.suffix in ('.pdf', '.cls'):
            shutil.copy(f, OUT / f.name)
    shutil.copy(NUEVO / 'SEGAN_R2.tex', OUT / 'nuevo.tex')
    cfg = ('PICTUREENV=(?:picture|DIFnomarkup|table|table\\*|figure|figure\\*|algorithm|longtable|'
           'thebibliography|algorithmic)[\\w\\d*@]*')
    cmd = [LATEXDIFF, '--flatten', '--math-markup=whole', '--disable-citation-markup',
           '--type=UNDERLINE', f'--config={cfg}', 'SEGAN_paper_FINAL.tex', 'nuevo.tex']
    r = subprocess.run(cmd, cwd=OUT, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:])
        raise SystemExit('latexdiff fallo')
    d = r.stdout
    d = d.replace('\\end{frontmatter}', '\\end{frontmatter}\n' + NOTA, 1)
    d = d.replace('\\begin{document}', '\\AtBeginDocument{\\let\\origref\\ref\\renewcommand{\\ref}[1]{\\mbox{\\origref{#1}}}}\n\\begin{document}', 1)
    # Etiquetas de la R1 que ya no existen en la R2: en el texto tachado se
    # escriben con el numero que tenian en la R1, en vez de mostrar '??'.
    for _ in range(2):
        subprocess.run('pdflatex -interaction=nonstopmode SEGAN_paper_FINAL.tex', cwd=OUT, shell=True,
                       capture_output=True, text=True)
    pat = re.compile(r'\\newlabel\{([^}]*)\}\{\{(.*?)\}\{')
    r1 = dict(pat.findall((OUT / 'SEGAN_paper_FINAL.aux').read_text(errors='ignore')))
    r2 = dict(pat.findall((NUEVO / 'SEGAN_R2.aux').read_text(errors='ignore')))
    viejas = 0
    for k, v in r1.items():
        if k not in r2 and f'\\ref{{{k}}}' in d:
            viejas += d.count(f'\\ref{{{k}}}')
            d = d.replace(f'\\ref{{{k}}}', v)
    print(f'referencias de la R1 resueltas con su numero original: {viejas}')
    (OUT / 'marcado.tex').write_text(d)
    for _ in range(3):
        rc = subprocess.run('pdflatex -interaction=nonstopmode marcado.tex', cwd=OUT, shell=True,
                            capture_output=True, text=True)
    log = (OUT / 'marcado.log').read_text(errors='ignore')
    pags = re.search(r'Output written on .*\((\d+) pages', log)
    errores = re.findall(r'^! .*$', log, flags=re.M)
    print(f'marcado: {pags.group(1) if pags else "SIN PDF"} paginas; {len(errores)} errores')
    for e in errores[:15]:
        print('  ', e)
    if pags:
        shutil.copy(OUT / 'marcado.pdf', L.R2 / 'entrega' / '4_manuscrito_marcado_R1_R2.pdf')


if __name__ == '__main__':
    main()
