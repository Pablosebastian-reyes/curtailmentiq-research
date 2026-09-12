#!/usr/bin/env python3
"""Convierte el suplementario a PDF y verifica que lleguen el titulo y las tablas.

    python flagship/revision/suplementario_pdf.py

Entrada: flagship/segan/SUPPLEMENTARY_storage_registry.md
Salida:  entrega_revision/13_suplementario_registro_almacenamiento.pdf

Usa pandoc con pdflatex. Falla con estado distinto de cero si el PDF no trae el
titulo actual del manuscrito, si todavia trae el viejo, o si alguna tabla del
Markdown no llega al PDF. Cada tabla se coteja por la primera celda de su
primera fila de datos, leida del propio Markdown, contra el texto extraido del
PDF; y el .tex intermedio tiene que traer una longtable por cada tabla.
"""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[2]
MD = RAIZ / 'flagship' / 'segan' / 'SUPPLEMENTARY_storage_registry.md'
SAL = RAIZ / 'entrega_revision' / '13_suplementario_registro_almacenamiento.pdf'
PANDOC = shutil.which('pandoc') or str(pathlib.Path.home() / '.local' / 'bin' / 'pandoc')
TITULO_VIEJO = 'Probabilistic forecasting of renewable curtailment under regime change'

# caracteres fuera de Latin-1 que pdflatex no conoce, con su equivalente
UNICODE = {'\u2265': r'\ensuremath{\geq}', '\u2264': r'\ensuremath{\leq}',
           '\u2192': r'\ensuremath{\rightarrow}', '\u2248': r'\ensuremath{\approx}',
           '\u2212': r'\ensuremath{-}', '\u2009': r'\,', '\u202f': r'\,',
           '\u2011': '-', '\u2032': "'"}

OPCIONES = ['--pdf-engine=pdflatex', '-V', 'geometry:margin=2cm', '-V', 'fontsize=10pt',
            '-V', 'colorlinks=true', '-V', 'linkcolor=black', '-V', 'urlcolor=blue']


def norm(t):
    return re.sub(r'\s+', ' ', t).strip()


def tablas_md(texto):
    """Primera celda de la primera fila de datos de cada tabla del Markdown."""
    celdas, lineas, i = [], texto.split('\n'), 0
    while i < len(lineas):
        if lineas[i].startswith('|') and i + 1 < len(lineas) \
                and re.match(r'^\|[-| :]+\|\s*$', lineas[i + 1]):
            fila = lineas[i + 2] if i + 2 < len(lineas) else ''
            # la primera celda con texto, no la primera a secas: en el registro
            # la primera columna es el numero de fila, y "1" esta en cualquier
            # texto, asi que no prueba que la tabla haya llegado
            cand = [norm(re.sub(r'[*_`]', '', c)) for c in fila.split('|')[1:-1]]
            # y si ninguna tiene letras, la primera no vacia: unir la fila entera
            # no sirve, porque las celdas nunca salen contiguas en el texto extraido
            celda = next((c for c in cand if re.search(r'[A-Za-z]', c)),
                         next((c for c in cand if c), ''))
            celdas.append(celda)
            i += 2
            while i < len(lineas) and lineas[i].startswith('|'):
                i += 1
        else:
            i += 1
    return celdas


def main():
    md = MD.read_text()
    tex_man = (RAIZ / 'flagship' / 'segan' / 'SEGAN_paper_FINAL.tex').read_text()
    titulo = re.search(r'\\title\{([^}]*)\}', tex_man).group(1).strip()
    celdas = tablas_md(md)
    presentes = sorted({c for c in md if c in UNICODE})

    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        cab = d / 'cabecera.tex'
        cab.write_text('\\usepackage{etoolbox}\n'
                       '\\AtBeginEnvironment{longtable}{\\footnotesize}\n' +
                       ''.join(f'\\DeclareUnicodeCharacter{{{ord(c):04X}}}{{{UNICODE[c]}}}\n'
                               for c in presentes))
        base = [PANDOC, str(MD), '-H', str(cab)] + OPCIONES
        r = subprocess.run(base + ['-s', '-o', str(d / 'sup.tex')], capture_output=True, text=True)
        if r.returncode:
            sys.exit(f'pandoc a .tex fallo:\n{r.stderr}')
        n_lt = (d / 'sup.tex').read_text().count('\\begin{longtable}')
        # El PDF sale de compilar ese mismo .tex con pdflatex, y no de pandoc
        # directo, para poder leer el log: un desborde (una URL que se sale del
        # margen) no deja rastro en el texto extraido, solo un Overfull \hbox.
        for _ in (1, 2):
            subprocess.run(['pdflatex', '-interaction=nonstopmode', 'sup.tex'],
                           cwd=d, capture_output=True, text=True)
        log = (d / 'sup.log').read_text(errors='replace')
        if not (d / 'sup.pdf').exists():
            sys.exit(f'pdflatex no produjo PDF:\n{log[-2000:]}')
        errores = len(re.findall(r'^! ', log, re.M))
        desbordes = [float(x) for x in re.findall(r'Overfull \\hbox \(([\d.]+)pt too wide\)', log)]
        txt = norm(subprocess.run(['pdftotext', str(d / 'sup.pdf'), '-'],
                                  capture_output=True, text=True).stdout)
        pag = re.search(r'Pages:\s+(\d+)', subprocess.run(
            ['pdfinfo', str(d / 'sup.pdf')], capture_output=True, text=True).stdout).group(1)
        SAL.parent.mkdir(exist_ok=True)
        shutil.copy(d / 'sup.pdf', SAL)

    fallas = []
    print(f'pandoc: {subprocess.run([PANDOC, "--version"], capture_output=True, text=True).stdout.split(chr(10))[0]}')
    print(f'PDF: {SAL.relative_to(RAIZ)}, {pag} paginas')
    print(f'titulo actual del manuscrito en el PDF: {"si" if titulo in txt else "NO"}')
    if titulo not in txt:
        fallas.append('titulo actual ausente')
    print(f'titulo viejo en el PDF: {"SI" if TITULO_VIEJO in txt else "no"}')
    if TITULO_VIEJO in txt:
        fallas.append('titulo viejo presente')
    print(f'tablas en el Markdown: {len(celdas)}; longtable en el .tex intermedio: {n_lt}')
    if n_lt != len(celdas):
        fallas.append('distinto numero de tablas')
    for k, c in enumerate(celdas, 1):
        clave = ' '.join(c.split()[:4])
        ok = clave in txt
        print(f'  tabla {k}: primera celda "{c[:48]}" -> {"en el PDF" if ok else "NO LLEGA"}')
        if not ok:
            fallas.append(f'tabla {k}')
    # cada URL del Markdown, entera, en el texto del PDF: un enlace mal formado
    # sale percent-encoded o cortado ('%3Cmonth') y el cotejo de celdas no lo ve
    urls = [x for g in re.findall(r'`(https?://[^`]+)`|<(https?://[^>\s]+)>|\\url\{([^}]+)\}', md)
            for x in g if x]
    # se coteja sin espacios y sin guiones: pdftotext, al unir una linea que
    # termina en guion, quita el guion, y una URL partida en 'CEN-' sale como
    # 'CENReporte'. Quitarlos de los dos lados sigue atrapando lo que importa:
    # la codificacion '%3C', un corte o un '<>' cambiado.
    def llano(x):
        return re.sub(r'[\s\-\u2010]+', '', x)
    plano = llano(txt)
    rotas = [u for u in urls if llano(u) not in plano]
    print(f'URLs en el Markdown: {len(urls)}; intactas en el PDF: {len(urls) - len(rotas)}')
    for u in rotas:
        print(f'  NO LLEGA INTACTA: {u}')
        fallas.append('URL ' + u[:40])
    grandes = [x for x in desbordes if x > 2.0]
    print(f'errores de LaTeX: {errores}; desbordes de mas de 2pt: {len(grandes)}'
          + (f' (el mayor, {max(grandes):.1f}pt)' if grandes else ''))
    if errores:
        fallas.append(f'{errores} errores de LaTeX')
    if grandes:
        fallas.append(f'{len(grandes)} desbordes de linea')
    if presentes:
        print('caracteres declarados para pdflatex: ' + ', '.join(f'U+{ord(c):04X}' for c in presentes))
    if fallas:
        sys.exit('FALLA: ' + '; '.join(fallas))
    print('RESULTADO: titulo y tablas verificados')


if __name__ == '__main__':
    main()
