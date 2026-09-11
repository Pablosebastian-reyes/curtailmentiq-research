#!/usr/bin/env python3
"""Genera la version con cambios marcados para Editorial Manager.

    python flagship/revision/generar_marcado.py [--baseline TAG] [--salida DIR]

Baseline por omision: submitted-segan-v1 (commit 4af5ea7, 28 de julio de 2026),
que es la version efectivamente enviada. NO se cambia el baseline.

Tres decisiones de configuracion, todas por la misma razon: latexdiff alinea
palabra por palabra, y cuando un bloque se reescribio completo el intercalado
resultante es ilegible y a veces no compila.

 1. PICTUREENV se extiende a los entornos de tabla, figura, algoritmo,
    ecuacion y bibliografia. latexdiff convierte cada entorno de esa lista en
    un token unico (\\PICTUREBLOCK...), asi que una tabla borrada se marca
    entera en vez de derramarse como texto corrido dentro del parrafo
    siguiente. La version enviada traia las tablas en linea; la actual las
    trae por \\input, de modo que sin esto las tablas viejas se desarman.
 2. --math-markup=whole trata cada ecuacion como bloque.
 3. --disable-citation-markup apaga el marcado de citas.

La bibliografia se sustituye por la nueva en AMBOS archivos antes de diffear,
de modo que aparezca una sola vez y sin marcas. Paso de 10 a 43 entradas y el
intercalado producia entradas vacias, entradas fundidas y DOI duplicados. La
nota de cabecera lo declara. Se comprueba antes que las claves de la version
enviada sean un subconjunto de las nuevas, para no dejar citas sin resolver.
"""
import argparse, pathlib, re, shutil, string, subprocess, sys, tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[2]
BASELINE = 'submitted-segan-v1'
PRINCIPAL = 'flagship/segan/SEGAN_paper_FINAL.tex'

ENTORNOS_ATOMICOS = [
    r'picture[\w\d*@]*', r'tikzpicture[\w\d*@]*', r'DIFnomarkup[\w\d*@]*',
    r'table[\w\d*@]*', r'tabular[\w\d*@]*', r'figure[\w\d*@]*',
    r'algorithm[\w\d*@]*', r'algorithmic[\w\d*@]*',
    r'equation[\w\d*@]*', r'thebibliography',
]

def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)

def bloque_bib(texto):
    m = re.search(r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}', texto, re.S)
    if not m: sys.exit('no se encontro thebibliography')
    return m.group(0)

def claves_bib(bloque):
    return [e.split('}', 1)[0] for e in re.split(r'\\bibitem\{', bloque)[1:]]

def palabras(t):
    t = re.sub(r'%.*', ' ', t)
    t = re.sub(r'\\[a-zA-Z@]+\*?', ' ', t)
    t = re.sub(r'[{}$&\\~^_]', ' ', t)
    return [w for w in t.split() if re.search(r'[A-Za-z]', w)]

def contenido_de(cmd, texto):
    """Contenido balanceado de cada \\cmd{...} y \\cmdFL{...}."""
    fuera, i = [], 0
    pat = re.compile(r'\\' + cmd + r'(?:FL)?\{')
    while (m := pat.search(texto, i)):
        j, d = m.end(), 1
        while j < len(texto) and d:
            if texto[j] == '{': d += 1
            elif texto[j] == '}': d -= 1
            j += 1
        fuera.append(texto[m.end():j - 1]); i = j
    return fuera

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', default=BASELINE)
    ap.add_argument('--salida', default=str(RAIZ / 'resultados' / 'latexdiff'))
    a = ap.parse_args()
    salida = pathlib.Path(a.salida); salida.mkdir(parents=True, exist_ok=True)

    trabajo = pathlib.Path(tempfile.mkdtemp())
    commit = sh(f'git -C {RAIZ} rev-parse "{a.baseline}^{{commit}}"').stdout.strip()[:7]
    fecha = sh(f'git -C {RAIZ} log --format=%ad --date=short -1 {a.baseline}').stdout.strip()
    print(f'baseline: {a.baseline} = commit {commit} del {fecha}')

    vieja = sh(f'git -C {RAIZ} show "{a.baseline}:{PRINCIPAL}"').stdout
    nueva = (RAIZ / PRINCIPAL).read_text()

    # --- bibliografia: una sola, la nueva, sin marcas ---
    bib_v, bib_n = bloque_bib(vieja), bloque_bib(nueva)
    cv, cn = claves_bib(bib_v), claves_bib(bib_n)
    huerfanas = [k for k in cv if k not in cn]
    if huerfanas:
        sys.exit(f'ERROR: claves de la enviada ausentes de la bib nueva: {huerfanas}')
    print(f'  bibliografia: {len(cv)} -> {len(cn)} entradas, '
          f'sustituida por la nueva en ambos archivos (sin marcas)')
    vieja_pp = vieja.replace(bib_v, bib_n)

    # El conteo de la nota es prosa del CUERPO, sin bibliografia, para que
    # cuadre con el porcentaje de la misma frase. No se usa wc -w del .tex:
    # cuenta comandos y comentarios de LaTeX y se mueve al editar un
    # comentario del preambulo, que no es un cambio del manuscrito.
    sin_bib = lambda t: t.replace(bloque_bib(t), ' ')
    pv, pn = len(palabras(sin_bib(vieja))), len(palabras(sin_bib(nueva)))
    (trabajo / 'vieja.tex').write_text(vieja_pp)
    (trabajo / 'nueva.tex').write_text(nueva)

    cfg = 'PICTUREENV=' + ';'.join(ENTORNOS_ATOMICOS)
    cmd = (f'latexdiff -t CCHANGEBAR --math-markup=whole --disable-citation-markup '
           f'--config "{cfg}" vieja.tex nueva.tex')
    print(f'  latexdiff -t CCHANGEBAR --math-markup=whole --disable-citation-markup')
    print(f'  --config PICTUREENV={",".join(e.split("[")[0] for e in ENTORNOS_ATOMICOS)}')
    r = sh(cmd, cwd=trabajo)
    if r.returncode or not r.stdout:
        sys.exit(f'latexdiff fallo: {r.stderr[:500]}')
    for w in (l for l in r.stderr.splitlines() if l.strip()):
        print(f'    aviso: {w}')
    marcado = r.stdout

    # --- cuanto queda marcado, medido sobre el cuerpo sin bibliografia ---
    cuerpo = marcado.split(r'\begin{document}', 1)[1].split(r'\begin{thebibliography}', 1)[0]
    tot = len(palabras(cuerpo))
    add = sum(len(palabras(x)) for x in contenido_de('DIFadd', cuerpo))
    pct = 100 * add / tot

    # --- nota de cabecera, sin marcado de diff ---
    nota = string.Template(NOTA).substitute(
        fecha_envio='28 July 2026', version_enviada='5.0',
        pct=round(pct), pv=f'{pv:,}', pn=f'{pn:,}', bv=len(cv), bn=len(cn))
    if r'\end{frontmatter}' not in marcado:
        sys.exit('no se encontro \\end{frontmatter} donde insertar la nota')
    marcado = marcado.replace(r'\end{frontmatter}', r'\end{frontmatter}' + nota, 1)

    destino = salida / 'marcado_CCHANGEBAR.tex'
    destino.write_text(marcado)
    print(f'  marcado: {destino.relative_to(RAIZ)}')
    print(f'  cuerpo sin bibliografia: {tot} palabras, {pct:.1f}% marcado como añadido')
    print(f'  fuente: {pv} -> {pn} palabras')

    # --- compilar en el directorio de trabajo, que ya tiene lo necesario ---
    for f in (RAIZ / 'build').glob('fig*.pdf'): shutil.copy(f, trabajo)
    for f in (RAIZ / 'build').glob('tab_*.tex'): shutil.copy(f, trabajo)
    shutil.copy(RAIZ / 'build' / 'hiperparametros.tex', trabajo)
    shutil.copy(sh('kpsewhich elsarticle.cls').stdout.strip(), trabajo)
    shutil.copy(destino, trabajo / 'marcado.tex')
    for i in (1, 2, 3):
        sh(f'pdflatex -interaction=nonstopmode marcado.tex > c{i}.log 2>&1', cwd=trabajo)
    log = (trabajo / 'c3.log').read_text(errors='replace')
    err = log.count('\n! ') + (1 if log.startswith('! ') else 0)
    pdf = trabajo / 'marcado.pdf'
    if not pdf.exists():
        print('  RESULTADO: no se produjo PDF'); print(log[-3000:]); sys.exit(1)
    pag = sh(f'pdfinfo {pdf}').stdout
    pag = re.search(r'^Pages:\s+(\d+)', pag, re.M).group(1)
    und = len(re.findall(r'(?i)undefined', log))
    print(f'  compilacion: {pag} paginas, {err} errores, {und} refs/citas sin resolver')
    shutil.copy(pdf, salida / 'marcado_CCHANGEBAR.pdf')
    shutil.copy(trabajo / 'c3.log', salida / 'marcado_CCHANGEBAR.log')
    print(f'  PDF: {(salida / "marcado_CCHANGEBAR.pdf").relative_to(RAIZ)}')
    if err or und: sys.exit(1)

NOTA = r"""

\vspace{6pt}
\noindent\rule{\linewidth}{0.4pt}
\vspace{2pt}

\noindent\textbf{\small Note on this marked-up version}

{\small
\noindent This revision is a substantial reframing of the manuscript, not an
incremental correction. The marked-up text is therefore dense with change, and
we set out here what a reader should expect before reading it.

\noindent The comparison is against the version submitted on $fecha_envio
(version $version_enviada), and about $pct\% of the body text is new: excluding
the bibliography, it grew from $pv to $pn words. Whole sections are new rather than edited,
and the sections that were retained were in most cases rewritten rather than
amended. The methodological contribution is now stated as a diagnostic, and the
attribution of the 2025 regime change to storage deployment has been removed
throughout; both changes touch most of the manuscript.

\noindent The bibliography grew from $bv to $bn entries. It is shown here
unmarked, because word-level markup of a reference list that more than
quadrupled produces merged and truncated entries rather than a readable record
of what changed. Tables, figures and displayed equations are marked as whole
blocks for the same reason.

\noindent This note is a reading aid and not the record of changes. The
change-by-change account, with the exact location of each change and its
relation to each referee comment, is in the accompanying response to reviewers.
}

\vspace{2pt}
\noindent\rule{\linewidth}{0.4pt}
\vspace{6pt}

"""

if __name__ == '__main__':
    main()
