#!/usr/bin/env python3
"""
Verificador de referencias cruzadas entre el manuscrito y los documentos que lo
acompanan.
======================================================================
Motivo. La carta de respuesta y la documentacion interna citan secciones, tablas
y figuras del manuscrito con NUMEROS LITERALES, no con \\ref. Cuando se inserta
una subseccion o se funde una tabla, esos numeros se corren en silencio: LaTeX no
avisa porque no hay ninguna referencia rota que resolver. Una auditoria externa
encontro ocho de estos corrimientos en el paquete de la revision mayor. Este
script existe para que no vuelva a pasar.

Hace tres comprobaciones.

1. AUTOCHEQUEO DEL PARSER. Numera el manuscrito leyendo el .tex (secciones,
   subsecciones, figuras, tablas, algoritmos, ecuaciones y apendices) y contrasta
   el resultado contra build/SEGAN_paper_FINAL.aux, que es lo que LaTeX numero de
   verdad. Si el parser y LaTeX discrepan, el script se detiene: no tendria
   sentido auditar con una numeracion propia equivocada.

2. EXISTENCIA. Toda referencia literal a Section, Table, Figure, Algorithm o
   Appendix en los documentos auditados tiene que corresponder a un objeto que
   existe con ese numero en el manuscrito.

3. SEMANTICA. La existencia no basta: "Section 4.7" existe pero puede estar
   apuntando al lugar equivocado. MAPA_SEMANTICO ancla frases distintivas de la
   carta a la etiqueta que les corresponde, y el script comprueba que el numero
   escrito junto a esa frase sea el de esa etiqueta.

Documentos auditados: la carta de respuesta, REVISION_PLAN.md y
CHANGELOG_REVISION.md.

Comando:
  <venv>/bin/python flagship/revision/verificar_referencias_cruzadas.py

Devuelve 0 si todo cuadra, 1 si hay alguna referencia rota o mal dirigida.
"""
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[2]
TEX = REPO / 'flagship' / 'segan' / 'SEGAN_paper_FINAL.tex'
AUX = REPO / 'build' / 'SEGAN_paper_FINAL.aux'
DOCS = [
    ('response_to_reviewers.tex', REPO / 'flagship' / 'segan' / 'response_to_reviewers.tex'),
    ('REVISION_PLAN.md', REPO / 'REVISION_PLAN.md'),
    ('CHANGELOG_REVISION.md', REPO / 'CHANGELOG_REVISION.md'),
]


# Los cuerpos de tabla, y con ellos el float completo con su \caption y su
# \label, viven en archivos generados que el manuscrito trae con \input. La
# numeracion de las tablas la fija, por tanto, el ORDEN de esos \input, y el
# parser tiene que resolverlos para poder numerar.
RUTAS_INPUT = [
    REPO / 'resultados' / 'tablas_tex',
    REPO / 'resultados' / 'fase1',
    REPO / 'flagship' / 'segan',
    REPO / 'build',
]


def expandir_inputs(texto, profundidad=0):
    """Sustituye cada \\input{x} por el contenido de x.tex, buscandolo en
    RUTAS_INPUT. Recursivo, con tope por si hubiera un ciclo."""
    if profundidad > 5:
        return texto

    def resolver(m):
        nombre = m.group(1).strip()
        for base in RUTAS_INPUT:
            for cand in (base / nombre, base / f'{nombre}.tex'):
                if cand.is_file():
                    return expandir_inputs(cand.read_text(), profundidad + 1)
        print(f'  AVISO  no se encuentra el \\input{{{nombre}}}; '
              f'la numeracion puede quedar incompleta')
        return ''

    return re.sub(r'\\input\{([^}]*)\}', resolver, texto)


# ==========================================================================
# 1. NUMERACION CANONICA, LEIDA DEL MANUSCRITO
# ==========================================================================
def numerar_manuscrito(texto):
    """Recorre el .tex en orden y asigna a cada objeto el numero que LaTeX le
    dara. Antes de \\appendix las secciones son 1, 2, 3...; despues son A, B,
    C... y los contadores de tabla y figura pasan a llevar el prefijo de la
    letra del apendice sin reiniciarse, que es como los numera elsarticle."""
    numeros, etiquetas = {}, {}
    sec = sub = 0
    fig = tab = alg = ecu = 0
    en_apendice = False
    letra = ''
    ultimo = None   # ultimo objeto abierto, para asociarle su \label

    patron = re.compile(
        r'\\(appendix|section\*?|subsection\*?|label|caption)\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\})?'
        r'|\\begin\{(figure\*?|table\*?|algorithm|equation)\}')

    for m in patron.finditer(texto):
        cmd, arg, entorno = m.group(1), m.group(2), m.group(3)

        if entorno:
            base = entorno.rstrip('*')
            if base == 'figure':
                fig += 1
                ultimo = ('figure', f'{letra}.{fig}' if en_apendice else str(fig))
            elif base == 'table':
                tab += 1
                ultimo = ('table', f'{letra}.{tab}' if en_apendice else str(tab))
            elif base == 'algorithm':
                alg += 1
                ultimo = ('algorithm', f'{letra}.{alg}' if en_apendice else str(alg))
            elif base == 'equation':
                ecu += 1
                ultimo = ('equation', f'{letra}.{ecu}' if en_apendice else str(ecu))
            continue

        if cmd == 'appendix':
            en_apendice, sec, sub = True, 0, 0
            continue

        if cmd == 'section' or cmd == 'section*':
            if cmd.endswith('*'):
                ultimo = None
                continue
            sec += 1
            sub = 0
            if en_apendice:
                letra = chr(ord('A') + sec - 1)
                ultimo = ('appendix', letra)
            else:
                ultimo = ('section', str(sec))
            numeros.setdefault('secciones', []).append(ultimo[1])
            continue

        if cmd == 'subsection' or cmd == 'subsection*':
            if cmd.endswith('*'):
                ultimo = None
                continue
            sub += 1
            base = letra if en_apendice else str(sec)
            ultimo = ('subsection', f'{base}.{sub}')
            numeros.setdefault('secciones', []).append(ultimo[1])
            continue

        if cmd == 'label' and arg and ultimo:
            etiquetas[arg] = ultimo[1]

    inventario = {
        'Section': set(numeros.get('secciones', [])),
        'Table': {v for k, v in etiquetas.items() if k.startswith('tab:')},
        'Figure': {v for k, v in etiquetas.items() if k.startswith('fig:')},
        'Algorithm': {v for k, v in etiquetas.items() if k.startswith('alg:')},
        'Appendix': {v for k, v in etiquetas.items() if k.startswith('app:')},
    }
    return inventario, etiquetas, dict(figuras=fig, tablas=tab, algoritmos=alg,
                                       ecuaciones=ecu)


def leer_aux(ruta):
    if not ruta.exists():
        return None
    out = {}
    for m in re.finditer(r'\\newlabel\{([^}]*)\}\{\{([^}]*)\}', ruta.read_text()):
        clave, valor = m.group(1), m.group(2)
        if clave.endswith('@cref'):
            continue
        out[clave] = valor.replace('Appendix~', '')
    return out


# ==========================================================================
# 3. MAPA SEMANTICO: frase distintiva -> etiqueta que le corresponde
# ==========================================================================
# Cada entrada es (etiqueta, regex). El regex tiene que capturar el numero en el
# grupo 1 y estar anclado en una frase que solo pueda referirse a ese objeto.
MAPA_SEMANTICO = [
    ('sec:seleccion',  r'Section~([\d.]+) is a new subsection giving the protocol and the outcome'),
    ('sec:evaluacion', r'Section~([\d.]+) defines the metric and the convention for infinite bounds'),
    ('sec:evaluacion', r'Section~([\d.]+), the metric set'),
    ('sec:novedad',    r'Section~([\d.]+) now states which parts of the construction are new'),
    ('sec:novedad',    r'Section~([\d.]+) closes by noting that neither survives its ablation'),
    ('sec:novedad',    r'Section~([\d.]+) now attributes each ingredient explicitly'),
    ('sec:novedad',    r'Section~([\d.]+), attribution and novelty'),
    ('sec:algoritmo',  r'Section~([\d.]+) gives the three items above that belong in the body'),
    ('fig:flow',       r'Figure~([\d.]+) is the flowchart'),
    ('fig:flow',       r'Algorithm~1 and Figure~([\d.]+), the complete procedure'),
    ('tab:hiper',      r'Appendix~C, Table~([\dA-D.]+), is the complete hyperparameter specification'),
    ('tab:hiper',      r'Appendix~C, Table~([\dA-D.]+), every parameter and all four seeds'),
    ('tab:frontera',   r'and Table~([\d]+), the boundary sensitivity'),
    ('tab:panel',      r'and Table~([\d]+)\s*,?\s*conditional coverage'),
    ('sec:ablaciones', r'Section~([\d.]+) is a new subsection\. Table~8 gives the marginal'),
    ('sec:agnostic',   r'Section~([\d.]+) is a new subsection reporting the result'),
    ('sec:panel',      r'Section~([\d.]+) reports the remedies and the disaggregated coverage'),
    ('sec:base',       r'Section~([\d.]+) describes the base models'),
    ('sec:guarantees', r'Section~([\d.]+) is a new subsection separating the three guarantee regimes'),
    ('fig:regime',     r'Figure~([\d.]+), regenerated under the stated penalty'),
    ('fig:rolling',    r'Figures~([\d.]+) and 6, labels regenerated'),
    ('fig:flow',       r'Figure~([\d.]+), the algorithm flowchart'),
    ('tab:agnostic',   r'Table~([\d.]+) \(the three arms in the transition window\)'),
    ('tab:diagnostico',r'Table~([\d.]+) \(the fifteen cells and the fitted relationship\)'),
    ('tab:results',    r'Table~([\d.]+), footnote removed and column renamed'),
    ('tab:ablaciones', r'Table~([\d.]+) gives the marginal contributions'),
    ('tab:cota',       r'Table~([\d.]+) reports the effect of the \$\\alpha\$ bound'),
    ('sec:frontera',   r'Section~([\d.]+) reports the boundary and chronology sensitivity'),
    ('sec:escalera',   r'Section~([\d.]+) is a further new subsection with the capacity ladder'),
    ('tab:diag_ampliado', r'Table~([\d.]+) \(the forty cells with their bootstrap intervals\)'),
    ('tab:escalera',   r'the capacity ladder, Table~([\d]+) and Figure~\d+'),
    ('fig:escalera',   r'the capacity ladder, Table~\d+ and Figure~([\d]+)'),
]


def main():
    texto = expandir_inputs(TEX.read_text())
    inventario, etiquetas, cont = numerar_manuscrito(texto)
    aux = leer_aux(AUX)

    print('=' * 92)
    print('VERIFICADOR DE REFERENCIAS CRUZADAS')
    print(f'manuscrito: {TEX.relative_to(REPO)}')
    print('=' * 92)
    print(f"objetos numerados: {cont['figuras']} figuras, {cont['tablas']} tablas, "
          f"{cont['algoritmos']} algoritmos, {cont['ecuaciones']} ecuaciones, "
          f"{len(inventario['Section'])} secciones y subsecciones")

    fallos = []

    # ---- 1. autochequeo contra el .aux ------------------------------
    print('\n' + '-' * 92)
    print('1. AUTOCHEQUEO DEL PARSER contra build/SEGAN_paper_FINAL.aux')
    print('-' * 92)
    if aux is None:
        print('  .aux ausente: compila el manuscrito antes de verificar. Se aborta.')
        return 2
    discrepancias = [(k, etiquetas[k], aux[k]) for k in sorted(etiquetas)
                     if k in aux and etiquetas[k] != aux[k]]
    faltan = [k for k in sorted(aux) if k not in etiquetas]
    if discrepancias:
        for k, mio, suyo in discrepancias:
            print(f'  DISCREPA  {k}: el parser dice {mio}, LaTeX dice {suyo}')
        print('\n  El parser no coincide con LaTeX. Se aborta para no auditar con')
        print('  una numeracion equivocada.')
        return 2
    print(f'  {len(etiquetas)} etiquetas coinciden con LaTeX'
          + (f'; {len(faltan)} en el .aux sin \\label rastreable: {faltan}' if faltan else ''))

    # ---- 2. existencia ----------------------------------------------
    print('\n' + '-' * 92)
    print('2. EXISTENCIA de cada referencia literal')
    print('-' * 92)
    # Se reconocen las cuatro formas en que estos documentos citan: la larga en
    # ingles, las abreviadas de LaTeX (\S, Fig.~, App.~, Alg.~), los rangos y
    # pares (Tables 9--10, Tables 6 and 7) y la forma en espanol de los .md.
    # Varias de las referencias corridas de la auditoria estaban precisamente en
    # las formas abreviadas y en espanol, que una version anterior no miraba.
    NUM = r'[0-9A-D]+(?:\.[0-9]+)*'
    ALIAS = {
        'Section': 'Section', 'Sections': 'Section', r'\\S': 'Section',
        'Seccion': 'Section', 'Secciones': 'Section',
        'Table': 'Table', 'Tables': 'Table', 'Tabla': 'Table', 'Tablas': 'Table',
        'Figure': 'Figure', 'Figures': 'Figure', 'Fig.': 'Figure',
        'Figs.': 'Figure', 'Figura': 'Figure', 'Figuras': 'Figure',
        'Algorithm': 'Algorithm', 'Algorithms': 'Algorithm', 'Alg.': 'Algorithm',
        'Algoritmo': 'Algorithm', 'Algoritmos': 'Algorithm',
        'Appendix': 'Appendix', 'Appendices': 'Appendix', 'App.': 'Appendix',
        'Apendice': 'Appendix', 'Apendices': 'Appendix',
    }
    encabezado = (r'\\S|Sections?|Secciones|Seccion|Tables?|Tablas|Tabla|'
                  r'Figures?|Figs?\.|Figuras|Figura|Algorithms?|Alg\.|'
                  r'Algoritmos?|Appendix|Appendices|App\.|Apendices|Apendice')
    # el encabezado, el primer numero, y opcionalmente un segundo numero unido
    # por un rango (--), una coma o una conjuncion (and / y)
    patron = re.compile(
        rf'\b({encabezado})~? ?({NUM})'
        rf'(?:\s*(?:--|,| and | y )\s*({NUM}))?')
    total = 0
    for nombre, ruta in DOCS:
        if not ruta.exists():
            print(f'  {nombre}: ausente, se omite')
            continue
        malos = []
        for i, linea in enumerate(ruta.read_text().splitlines(), 1):
            # Convenio: una referencia entre comillas de codigo es una CITA
            # literal, no una referencia viva. El changelog documenta la
            # numeracion vieja que se corrigio, y esas menciones tienen que
            # quedar tal cual sin que el verificador las tome por rotas.
            linea = re.sub(r'`[^`]*`', ' ', linea)
            for m in patron.finditer(linea):
                tipo = ALIAS.get(m.group(1).replace('\\S', r'\S'))
                if tipo is None:
                    continue
                # un rango o par solo cuenta como plural si el encabezado lo era
                plural = m.group(1).endswith(('s', 's.')) or m.group(1) in (
                    'Tablas', 'Figuras', 'Secciones', 'Apendices', 'Algoritmos')
                nums = [m.group(2)] + ([m.group(3)] if m.group(3) and plural else [])
                for num in nums:
                    total += 1
                    if num not in inventario.get(tipo, set()):
                        malos.append((i, m.group(0), tipo, num))
        if malos:
            for i, txt, tipo, num in malos:
                validos = sorted(inventario.get(tipo, set()))[:14]
                print(f'  ROTA  {nombre}:{i}  "{txt}"  -> no existe {tipo} {num}')
                print(f'        {tipo} validos: {", ".join(validos)}'
                      + (' ...' if len(inventario.get(tipo, set())) > 14 else ''))
                fallos.append(f'{nombre}:{i} {txt}')
        else:
            print(f'  OK    {nombre}: todas las referencias apuntan a objetos existentes')
    print(f'\n  {total} referencias literales examinadas')

    # ---- 3. semantica -------------------------------------------------
    print('\n' + '-' * 92)
    print('3. SEMANTICA: la referencia apunta al objeto correcto')
    print('-' * 92)
    carta = DOCS[0][1].read_text() if DOCS[0][1].exists() else ''
    for etq, rx in MAPA_SEMANTICO:
        esperado = etiquetas.get(etq)
        if esperado is None:
            print(f'  AVISO  la etiqueta {etq} no existe en el manuscrito')
            fallos.append(f'etiqueta ausente {etq}')
            continue
        encontrados = re.findall(rx, carta)
        if not encontrados:
            print(f'  AVISO  no se halla en la carta la frase de {etq}')
            print(f'         patron: {rx}')
            fallos.append(f'frase ausente {etq}')
            continue
        for hallado in encontrados:
            if hallado != esperado:
                print(f'  MAL    {etq}: la carta dice {hallado}, el manuscrito '
                      f'lo numera {esperado}')
                fallos.append(f'{etq}: {hallado} != {esperado}')
            else:
                print(f'  OK     {etq} -> {esperado}')

    # ---- veredicto ----------------------------------------------------
    print('\n' + '=' * 92)
    if fallos:
        print(f'{len(fallos)} PROBLEMAS. Corrige antes de enviar.')
        for f in fallos:
            print(f'  - {f}')
        return 1
    print('Todas las referencias cruzadas cuadran con la numeracion del manuscrito.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
