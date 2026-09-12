#!/usr/bin/env python3
"""Auditoria de legibilidad de la version marcada.

    python flagship/revision/auditar_marcado.py [--antes COMMIT]

Mide sobre resultados/latexdiff/marcado_CCHANGEBAR.{tex,pdf}:

 1. Palabras fundidas impresas. latexdiff a veces deja el borde de un cambio
    sin espacio y dos palabras salen pegadas ("attentionthan"). Hay tres firmas
    de borde: entre dos regiones marcadas, texto sin marcar contra una region
    marcada, y una region marcada contra texto sin marcar. Cada candidata se
    CONFIRMA contra el texto extraido del PDF: si no sale pegada, no cuenta.
    Un conteo anterior miraba solo la primera firma y sin confirmar, y
    subcontaba (seccion 22 del changelog).
 2. Parrafos con texto viejo y nuevo mezclado, y cuantos quedaron en forma de
    bloque: un borrado y despues un agregado, sin intercalar.

Con --antes COMMIT repite el conteo de fusiones sobre el marcado de ese commit.
"""
import argparse
import pathlib
import re
import subprocess
import sys
import tempfile

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(AQUI))
import bloques_marcado as B  # noqa: E402

TEX = 'resultados/latexdiff/marcado_CCHANGEBAR.tex'
PDF = 'resultados/latexdiff/marcado_CCHANGEBAR.pdf'
IZQ, DER = r'[A-Za-z0-9,;:\)\]]', r'[A-Za-z0-9\(\[]'
FIRMAS = {
    'marcado|marcado': re.compile(
        IZQ + r'\}\s*\\DIF(?:del|add)end(?:FL)?\s*\\DIF(?:add|del)begin(?:FL)?\s*'
        r'\\DIF(?:add|del)(?:FL)?\{' + DER),
    'sin marca|marcado': re.compile(
        IZQ + r'\\DIF(?:add|del)begin(?:FL)?\s*\\DIF(?:add|del)(?:FL)?\{' + DER),
    'marcado|sin marca': re.compile(
        IZQ + r'\}\s*\\DIF(?:add|del)end(?:FL)?[ \t]*' + DER),
}


def cuerpo(tex):
    return tex.split(r'\end{frontmatter}', 1)[1].split(r'\begin{thebibliography}', 1)[0]


def visible(t):
    t = re.sub(r'\\DIF(?:add|del)(?:begin|end)(?:FL)?', '', t)
    t = re.sub(r'\\DIF(?:add|del)(?:FL)?\s*\{', '', t)
    t = re.sub(r'\\[a-zA-Z]+\*?(\{[^{}]*\})?', ' ', t)
    return re.sub(r'[{}~]', '', t)


def secciones(c):
    enc = []
    for m in re.finditer(r'\\(?:sub)?section\{', c):
        g, _ = B._grupo(c, m.end() - 1)
        enc.append((m.start(), B.norm(B.proyeccion(g, 'add'))
                    or B.norm(B.proyeccion(g, 'del'))))
    return lambda p: ([t for q, t in enc if q <= p] or ['antes de la seccion 1'])[-1]


def fusiones(tex, pdf):
    c = cuerpo(tex)
    txt = re.sub(r'\s+', ' ', subprocess.run(['pdftotext', str(pdf), '-'],
                                             capture_output=True, text=True).stdout)
    sec = secciones(c)
    halladas = {}
    for tipo, pat in FIRMAS.items():
        for m in pat.finditer(c):
            ctx = c[max(0, m.start() - 80):m.start() + 1]
            if re.search(r'\\(label|ref|cite|eqref|end|begin)\{[^{}]*\}?\s*$', ctx):
                continue
            iz = re.findall(r'[A-Za-z0-9]+[,;:\)\]]?$', visible(ctx).rstrip())
            de = re.findall(r'^[\(\[]?[A-Za-z0-9]+',
                            visible(c[m.end() - 1:m.end() + 60]).lstrip())
            if not iz or not de:
                continue
            pegado = iz[0] + de[0]
            # solo cuenta si de verdad sale pegado en el PDF
            if re.search(r'(?<![A-Za-z0-9])' + re.escape(pegado) + r'(?![A-Za-z0-9])', txt):
                halladas[(m.start(), pegado)] = (tipo, sec(m.start()))
    return halladas


def en_bloque(p):
    orden = [m.group(1) for m in re.finditer(r'\\DIF(add|del)(?:FL)?\{', p)]
    return orden in ([], ['del'], ['add'], ['del', 'add'])


def resumen(f):
    por = {}
    for tipo, _ in f.values():
        por[tipo] = por.get(tipo, 0) + 1
    return f'{len(f)}  ' + '  '.join(f'({k}: {n})' for k, n in sorted(por.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--antes', help='commit cuyo marcado se cuenta para comparar')
    a = ap.parse_args()
    tex = (RAIZ / TEX).read_text()

    f = fusiones(tex, RAIZ / PDF)
    print(f'fusiones impresas, confirmadas en el PDF: {resumen(f)}')
    for (_, peg), (tipo, sc) in sorted(f.items()):
        print(f'  {peg:<24} {sc[:46]:<46} {tipo}')

    if a.antes:
        with tempfile.TemporaryDirectory() as d:
            ptex = subprocess.run(['git', '-C', str(RAIZ), 'show', f'{a.antes}:{TEX}'],
                                  capture_output=True, text=True, check=True).stdout
            pp = pathlib.Path(d) / 'antes.pdf'
            pp.write_bytes(subprocess.run(['git', '-C', str(RAIZ), 'show', f'{a.antes}:{PDF}'],
                                          capture_output=True, check=True).stdout)
            print(f'\nantes ({a.antes}): {resumen(fusiones(ptex, pp))}')

    c = cuerpo(tex)
    sec = secciones(c)
    mez = [(m.start(), m.group(0))
           for m in re.finditer(r'(?s)(?:(?<=\n\n)|\A).*?(?=\n\n|\Z)', c)
           if len(m.group(0).split()) >= 12 and B.mezclado(m.group(0))]
    nob = [(pos, p) for pos, p in mez if not en_bloque(p)]
    print(f'\nparrafos mezclados: {len(mez)}, en forma de bloque: {len(mez) - len(nob)}, '
          f'fuera de bloque: {len(nob)}')
    for pos, p in nob:
        marca = 'display math' if B.ATOMICO.search(p) else ''
        print(f'  {sec(pos)[:46]:<46} {marca:<13} {B.norm(B.proyeccion(p, "add"))[:36]}')


if __name__ == '__main__':
    main()
