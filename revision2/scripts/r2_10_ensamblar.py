#!/usr/bin/env python3
"""
R2-10. Ensambla, compila y verifica el manuscrito y la carta.
============================================================
1. Copia al directorio del manuscrito las figuras (las que se conservan de la
   R1 y las nuevas de figuras/).
2. Ordena la bibliografia por orden de primera cita (estilo numerico de
   Elsevier) y avisa de entradas no citadas o citas sin entrada.
3. Compila el manuscrito (pdflatex x3) y la carta, y revisa los logs:
   referencias indefinidas, citas indefinidas, cifras faltantes, cajas
   desbordadas graves.
4. Cuenta palabras del abstract (limite 250) y largo de los highlights.
5. Genera la version APLANADA para Editorial Manager: un solo .tex con las
   tablas y las cifras sustituidas como texto, sin \\cf ni \\input de partes,
   en entrega/fuentes/, y compila esa version en aislamiento.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_lib as L                      # noqa: E402

MAN = L.R2 / 'manuscrito'
CARTA = L.R2 / 'carta'
ENT = L.R2 / 'entrega'
BASE = L.R2 / 'base_r1' / 'fuentes'
FIG_R1 = ['fig1_plants_map.pdf', 'fig2_distribution.pdf', 'fig5_regime_changepoints.pdf',
          'fig6_algorithm_flow.pdf', 'fig3_rolling_coverage.pdf']
FIG_R2 = ['fig_modelos.pdf', 'fig_mecanico.pdf', 'fig_pit.pdf', 'fig_simulacion.pdf',
          'fig_operacional.pdf']
PDFLATEX = 'pdflatex'


def sh(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def expandir(texto, base):
    """Resuelve \\input{x} recursivamente (como lo haria LaTeX)."""
    def rep(m):
        n = m.group(1)
        f = base / (n if n.endswith('.tex') else n + '.tex')
        if not f.exists():
            return m.group(0)
        return expandir(f.read_text(), base)
    return re.sub(r'\\input\{([^}]*)\}', rep, texto)


def ordenar_bibliografia():
    bib = (MAN / 'bibliografia.tex').read_text()
    cuerpo = expandir((MAN / 'SEGAN_R2.tex').read_text().replace('\\input{bibliografia}', ''), MAN)
    cuerpo = re.sub(r'(?m)^%.*$', '', cuerpo)
    orden = []
    for grupo in re.findall(r'\\cite\{([^}]*)\}', cuerpo):
        for k in grupo.split(','):
            k = k.strip()
            if k and k not in orden:
                orden.append(k)
    ini, fin = bib.index('\\bibitem'), bib.index('\\end{thebibliography}')
    cab, items, pie = bib[:ini], bib[ini:fin], bib[fin:]
    entradas = {}
    for bloque in re.split(r'(?=\\bibitem\{)', items):
        if bloque.strip():
            k = re.match(r'\\bibitem\{([^}]*)\}', bloque).group(1)
            entradas[k] = bloque.strip() + '\n\n'
    sin_entrada = [k for k in orden if k not in entradas]
    no_citadas = [k for k in entradas if k not in orden]
    if sin_entrada:
        raise SystemExit(f'citas sin entrada: {sin_entrada}')
    if no_citadas:
        print('AVISO entradas no citadas (se eliminan):', no_citadas)
    nuevo = cab + ''.join(entradas[k] for k in orden) + pie
    (MAN / 'bibliografia.tex').write_text(nuevo)
    return len(orden), no_citadas


def compilar(dirx, nombre, pasadas=3):
    for _ in range(pasadas):
        rc, out = sh(f'{PDFLATEX} -interaction=nonstopmode -halt-on-error {nombre}.tex', dirx)
        if rc != 0:
            print(out[-3000:])
            raise SystemExit(f'pdflatex fallo en {nombre}')
    log = (dirx / f'{nombre}.log').read_text(errors='ignore')
    problemas = []
    for pat, etq in ((r'Reference `[^\']*\' on page \d+ undefined', 'referencia indefinida'),
                     (r'Citation `[^\']*\' on page \d+ undefined', 'cita indefinida'),
                     (r'CIFRA FALTANTE: \S+', 'cifra faltante'),
                     (r'There were undefined references', 'referencias indefinidas'),
                     (r'Overfull \\hbox \((\d+\.\d+)pt too wide\)', 'overfull')):
        for mm in re.finditer(pat, log):
            if etq == 'overfull' and float(mm.group(1)) < 10:
                continue
            problemas.append(f'{etq}: {mm.group(0)}')
    pags = re.search(r'Output written on .*\((\d+) pages', log)
    return problemas, int(pags.group(1)) if pags else None


def contar_abstract():
    t = (MAN / 'abstract.tex').read_text()
    cif = dict(re.findall(r'\\csname cf@([^\\]*)\\endcsname\{(.*)\}', (MAN / 'cifras.tex').read_text()))
    t = re.sub(r'\\cf\{([^}]*)\}', lambda m: cif.get(m.group(1), 'X'), t)
    t = re.sub(r'\\(begin|end)\{abstract\}', '', t)
    t = t.replace('{,}', ',').replace('~', ' ').replace('\\%', '%')
    t = re.sub(r'\\ensuremath\{([^}]*)\}', r'\1', t)
    palabras = len(re.findall(r'\S+', t))
    return palabras


def aplanar():
    """Version de un solo archivo para Editorial Manager: sin \\cf y sin
    \\input de partes; las tablas tambien quedan dentro."""
    cif = dict(re.findall(r'\\csname cf@([^\\]*)\\endcsname\{(.*)\}', (MAN / 'cifras.tex').read_text()))
    t = expandir((MAN / 'SEGAN_R2.tex').read_text(), MAN)
    t = re.sub(r'\\cf\{([^}]*)\}', lambda m: cif[m.group(1)], t)
    t = re.sub(r'% Numbers quoted in the text.*?\\makeatother\n', '', t, flags=re.S)
    t = re.sub(r'(?m)^% Generado por scripts/r2_07_cifras\.py.*\n', '', t)
    t = re.sub(r'(?m)^\\expandafter\\def\\csname cf@.*\n', '', t)
    assert '\\cf{' not in t and 'cf@' not in t
    dest = ENT / 'fuentes'
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    (dest / 'SEGAN_R2.tex').write_text(t)
    for f in FIG_R1 + FIG_R2:
        shutil.copy(MAN / f, dest / f)
    shutil.copy(BASE / 'elsarticle.cls', dest / 'elsarticle.cls')
    return dest


def main():
    for f in FIG_R1:
        shutil.copy(BASE / f, MAN / f)
    for f in FIG_R2:
        shutil.copy(L.FIG / f, MAN / f)
    shutil.copy(BASE / 'elsarticle.cls', MAN / 'elsarticle.cls')
    n, noc = ordenar_bibliografia()
    print(f'bibliografia: {n} entradas citadas en orden de aparicion')
    prob, pags = compilar(MAN, 'SEGAN_R2')
    print(f'manuscrito: {pags} paginas')
    for p in prob:
        print('  ', p)
    prob_c, pags_c = compilar(CARTA, 'response_R2', 3)
    print(f'carta: {pags_c} paginas')
    for p in prob_c:
        print('  ', p)
    print(f'abstract: {contar_abstract()} palabras (limite 250)')
    for linea in (MAN / 'highlights.txt').read_text().splitlines():
        print(f'  highlight {len(linea):>3} car. {"OK" if len(linea) <= 85 else "LARGO"}: {linea}')
    dest = aplanar()
    prob_f, pags_f = compilar(dest, 'SEGAN_R2')
    print(f'version aplanada (entrega/fuentes): {pags_f} paginas')
    for p in prob_f:
        print('  ', p)


if __name__ == '__main__':
    main()


def empaquetar():
    """Copia los entregables numerados a entrega/ y arma el zip de fuentes."""
    import zipfile
    shutil.copy(CARTA / 'response_R2.pdf', ENT / '1_carta_respuesta_R2.pdf')
    shutil.copy(ENT / 'fuentes' / 'SEGAN_R2.pdf', ENT / '2_manuscrito_R2.pdf')
    zp = ENT / '3_fuentes_latex_R2.zip'
    if zp.exists():
        zp.unlink()
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted((ENT / 'fuentes').iterdir()):
            if f.suffix in ('.tex', '.pdf', '.cls') and f.name != 'SEGAN_R2.pdf':
                z.write(f, f.name)
        z.writestr('00_README_COMPILATION.txt',
                   'SEGAN-D-26-03850 (revision 2) -- LaTeX source package.\n'
                   'Place all files in one directory and run pdflatex SEGAN_R2.tex three times.\n'
                   'The bibliography is written inline (thebibliography); no BibTeX run is needed.\n'
                   'elsarticle.cls is included so that the build does not depend on the server TeX tree.\n')
    shutil.copy(MAN / 'highlights.txt', ENT / '5_highlights.txt')
    print('entregables copiados a entrega/')


if __name__ == '__main__' and '--empaquetar' in sys.argv:
    empaquetar()
