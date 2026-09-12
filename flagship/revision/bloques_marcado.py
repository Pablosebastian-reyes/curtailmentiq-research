"""Convierte pasajes intercalados del marcado en reemplazo de bloque completo.

Se importa desde generar_marcado.py. No toca las fuentes: opera sobre el .tex
del marcado que produce latexdiff.
"""
import re

# Los ocho pasajes. La unidad de cada uno es la natural: el argumento de
# \title, el entorno abstract, o el parrafo completo que contiene el ancla.
BLOQUES = [
    ('titulo',   'titulo',   r'\title{'),
    ('abstract', 'abstract', r'\begin{abstract}'),
    ('4.6',      'parrafo',  'What is new is the combination'),
    ('5.3',      'parrafo',  'One qualification belongs here'),
    ('5.5',      'parrafo',  'it is reported as such'),
    ('6.3',      'parrafo',  'The distributional change documented'),
    ('7-A',      'parrafo',  'largest plants; the diagnosis is that'),
    ('7-B',      'parrafo',  'is a natural next step}'),
]

# Secciones cuyo texto se reescribio completo y donde el intercalado de
# latexdiff queda ilegible. Se identifican por su encabezado en el manuscrito
# final, no por numero: la numeracion se corre en el marcado.
SECCIONES_BARRIDAS = [
    # (trozo del encabezado en el manuscrito final, politica)
    #
    #   mixtos      el encabezado si esta mezclado, y TODO parrafo mezclado
    #   criterio    solo los parrafos que cumplen ilegible()
    #   enc+crit    el encabezado mezclado, mas los que cumplen ilegible()
    #   encabezado  solo el encabezado
    #   primero     solo el primer parrafo mezclado
    #
    # La politica sigue el encargo seccion por seccion, no un umbral unico:
    # de 4.5 se pidio solo el encabezado, de 5.5 solo el primer parrafo, de 3.3
    # solo el tercero, y de 1, 2.1, 4.1, 4.2, 4.3, 4.4, 4.8, 6.2, 6.3, 6.4, 6.5,
    # 8 y el apendice B la seccion entera. 2.1, 4.4 y 6.3 se agregaron, y 4.3
    # paso de solo encabezado a seccion entera, en la ultima ronda.
    ('Introduction',                                   'mixtos'),
    ('Curtailment: causes, measurement and forecasting', 'mixtos'),
    ('Probabilistic forecasting and conformal predic',  'mixtos'),
    ('Exploratory characterisation',                    'criterio'),
    ('Problem setup and base forecasters',              'mixtos'),
    ('Conformal calibration with a PIT score',          'mixtos'),
    ('Three guarantees, and which one applies where',   'mixtos'),
    ('Responses to the shift',                          'mixtos'),
    ('The adaptive scheme in full',                     'encabezado'),
    ('Evaluation',                                      'mixtos'),
    ('Point forecasting adds little, within the scope', 'enc+crit'),
    ('With the hurdle base model',                      'enc+crit'),
    ('Which components earn their cost',                'primero'),
    ('Where the operational value actually lies',       'mixtos'),
    ('The change in the record, and what we do not',    'mixtos'),
    ('The mid-2025 excursion',                          'mixtos'),
    ('Open directions',                                 'mixtos'),
    ('Conclusion',                                      'mixtos'),
    ('Coverage under score transport',                  'mixtos'),
]

# Firma de un borde donde una palabra queda pegada a la siguiente.
# Entornos que latexdiff vuelve atomicos. Un pasaje que contiene uno de estos
# NO se convierte: el texto viejo completo incluiria matematica en display, y
# eso dentro de \\DIFdel{} no compila. Se reportan como omitidos.
ATOMICO = re.compile(r'\\begin\{(equation|displaymath|align|eqnarray|gather|'
                     r'multline|table|figure|algorithm)\*?\}')

# No solo letra contra letra: "preferable1.334" y "1,which is why" son
# fusiones igual de ilegibles y el lado izquierdo es un digito o una coma.
FUSION = re.compile(
    r'[A-Za-z0-9,;:\)\]]\}\s*\\DIF(?:del|add)end(?:FL)?\s*'
    r'\\DIF(?:add|del)begin(?:FL)?\s*\\DIF(?:add|del)(?:FL)?\{[A-Za-z0-9\(\[]')


def _grupo(texto, i):
    """Contenido balanceado que empieza en la llave de texto[i]."""
    assert texto[i] == '{'
    j, d = i + 1, 1
    while j < len(texto) and d:
        if texto[j] == '{': d += 1
        elif texto[j] == '}': d -= 1
        j += 1
    return texto[i + 1:j - 1], j

def _desenvolver(texto, cmd):
    """\\cmd{X} -> X, respetando llaves balanceadas."""
    fuera, i = [], 0
    pat = re.compile(r'\\' + cmd + r'(?:FL)?\s*\{')
    while (m := pat.search(texto, i)):
        fuera.append(texto[i:m.start()])
        cont, j = _grupo(texto, m.end() - 1)
        fuera.append(cont); i = j
    fuera.append(texto[i:])
    return ''.join(fuera)

def _borrar_grupo(texto, cmd):
    """Elimina cada \\cmd{X} junto con su contenido.

    Se borra por comando y no por region \\DIFxxxbegin...\\DIFxxxend, porque un
    parrafo puede empezar o terminar a mitad de una region: latexdiff abre el
    \\DIFaddbegin en el parrafo anterior cuando la adicion abarca varios.
    """
    fuera, i = [], 0
    pat = re.compile(r'\\' + cmd + r'(?:FL)?\s*\{')
    while (m := pat.search(texto, i)):
        fuera.append(texto[i:m.start()])
        # un espacio en el hueco: sin el, dos fragmentos del mismo lado
        # separados por uno del otro quedan pegados ("operatorfigures")
        fuera.append(' ')
        _, j = _grupo(texto, m.end() - 1)
        i = j
    fuera.append(texto[i:])
    return ''.join(fuera)

def proyeccion(texto, lado):
    """Texto tal como queda en la version vieja ('del') o nueva ('add')."""
    otro = 'add' if lado == 'del' else 'del'
    t = _borrar_grupo(texto, 'DIF' + otro)
    if lado == 'del':
        # los comandos borrados los preserva latexdiff como comentario
        t = re.sub(r'^%DIFDELCMD\s*<\s?(.*?)\s*%%%\s*$', r'\1', t, flags=re.M)
    t = _desenvolver(t, 'DIF' + lado)
    t = re.sub(r'\\(DIFaddbegin|DIFaddend|DIFdelbegin|DIFdelend)(FL)?\b', ' ', t)
    t = re.sub(r'%DIF.*?$', ' ', t, flags=re.M)
    return t


def colgantes(frag):
    """Cierres sin apertura dentro del fragmento, que hay que preservar."""
    c = lambda k: len(re.findall(r'\\DIF' + k + r'(?:FL)?\b', frag))
    return max(0, c('addend') - c('addbegin')), max(0, c('delend') - c('delbegin'))

def norm(t):
    """Normaliza solo el espacio en blanco, que LaTeX trata como equivalente.

    Incluye el espacio espurio que latexdiff deja antes de la puntuacion en el
    borde entre una region marcada y la siguiente ("System , where"). Sin esto
    el texto reconstruido no calza con la fuente, y ademas quedaria impreso con
    ese espacio de mas.
    """
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'\s+([,.;:!?])', r'\1', t)
    return t.strip()

def canon(t):
    """Forma canonica para cotejar, con el mapa de indices al original.

    Tres normalizaciones en una sola pasada, porque hacerlas por separado se
    pisan entre si: se descartan las llaves de agrupacion, se colapsa el
    espacio en blanco, y se descarta el espacio que precede a la puntuacion.
    Las tres son invisibles en LaTeX y las tres las introduce latexdiff en los
    bordes: parte el separador de miles "1{,}000" y deja "System , where".
    """
    fuera, idx, i = [], [], 0
    while i < len(t):
        c = t[i]
        if c in '{}':
            i += 1
            continue
        if c.isspace():
            j = i
            while j < len(t) and (t[j].isspace() or t[j] in '{}'):
                j += 1
            if j < len(t) and t[j] in ',.;:!?':
                i = j
                continue
            fuera.append(' ')
            idx.append(i)
            i = j
            continue
        fuera.append(c)
        idx.append(i)
        i += 1
    while fuera and fuera[0] == ' ':
        fuera.pop(0)
        idx.pop(0)
    while fuera and fuera[-1] == ' ':
        fuera.pop()
        idx.pop()
    return ''.join(fuera), idx


def _mas_largo(proy, fuente, sufijo=False):
    """Longitud del prefijo (o sufijo) mas largo de proy presente en fuente."""
    lo, hi = 0, len(proy)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        trozo = proy[-mid:] if sufijo else proy[:mid]
        if trozo in fuente:
            lo = mid
        else:
            hi = mid - 1
    return lo


def desde_fuente(proy, fuente, minimo=40):
    """Texto de la FUENTE correspondiente al pasaje, verbatim.

    Se ubica la proyeccion en la fuente en forma canonica y se devuelve el
    tramo de la fuente entre sus extremos. Asi el bloque emitido calza con la
    fuente aunque latexdiff haya perdido o movido caracteres dentro del pasaje.

    Devuelve (texto, estado) con estado en {'exacto', 'reconstruido', 'fallo'}.
    """
    if not norm(proy):
        return '', 'exacto'
    fs, fidx = canon(fuente)
    ps, _ = canon(proy)

    def tramo(i, largo):
        return norm(fuente[fidx[i]:fidx[i + largo - 1] + 1])

    if ps in fs:
        t = tramo(fs.index(ps), len(ps))
        return t, ('exacto' if t == norm(proy) else 'reconstruido')
    npre, nsuf = _mas_largo(ps, fs), _mas_largo(ps, fs, sufijo=True)
    if npre < minimo or nsuf < minimo:
        return norm(proy), 'fallo'
    i = fs.index(ps[:npre])
    j = fs.find(ps[-nsuf:], i)
    if j < 0 or j + nsuf <= i:
        return norm(proy), 'fallo'
    t = tramo(i, j + nsuf - i)
    # el pasaje reconstruido no puede diferir en mas de un 2% del proyectado:
    # si difiere mas, las anclas cayeron en el lugar equivocado
    ct, _ = canon(t)
    if abs(len(ct) - len(ps)) > max(8, 0.02 * len(ps)):
        return norm(proy), 'fallo'
    return t, 'reconstruido'


def limites(marcado, clase, ancla):
    i = marcado.find(ancla)
    if i < 0: return None
    if clase == 'titulo':
        j = marcado.index('{', i)
        cont, fin = _grupo(marcado, j)
        return j + 1, fin - 1, cont
    if clase == 'abstract':
        ini = marcado.index(r'\begin{abstract}', i) + len(r'\begin{abstract}')
        fin = marcado.index(r'\end{abstract}', ini)
        return ini, fin, marcado[ini:fin]
    ini = marcado.rfind('\n\n', 0, i) + 2
    fin = marcado.find('\n\n', i)
    if fin < 0: fin = len(marcado)
    return ini, fin, marcado[ini:fin]

def bloque(viejo, nuevo):
    """El pasaje viejo entero borrado, despues el nuevo entero agregado.

    El espacio separador va DENTRO del grupo de \\DIFdel. Puesto entre
    \\DIFdelend y \\DIFaddbegin, TeX lo descarta por venir despues de una
    palabra de control, y el ultimo caracter del pasaje viejo queda pegado al
    primero del nuevo ("...Electricity SystemAn open curtailment dataset").
    """
    partes = []
    v, n = norm(viejo), norm(nuevo)
    if v:
        partes.append(r'\DIFdelbegin \DIFdel{' + v + ' }' + r'\DIFdelend')
    if n:
        partes.append(r'\DIFaddbegin \DIFadd{' + n + r'}\DIFaddend')
    return ' '.join(partes)

def _cotejan(emitido, proyectado, tol=0.02):
    """El texto emitido es el pasaje que el diff habia emparejado."""
    a, _ = canon(emitido)
    b, _ = canon(proyectado)
    if a == b:
        return True
    return (_mas_largo(b, a) >= 40 and
            abs(len(a) - len(b)) <= max(8, tol * len(b)))


def ilegible(frag):
    """Criterio objetivo: el pasaje no se puede leer como texto corrido.

    Tres firmas, cualquiera basta. (i) una palabra pegada a la siguiente en el
    borde de un cambio; (ii) dos o mas fragmentos borrados cortos inyectados en
    medio de texto agregado; (iii) tres o mas alternancias entre borrado y
    agregado. Un cambio de una palabra sola no cumple ninguna y se deja como
    esta, porque se lee bien y dice mas que un bloque entero.
    """
    if '\\DIFadd' not in frag or '\\DIFdel' not in frag:
        return False
    if FUSION.search(frag):
        return True
    cortos = 0
    for m in re.finditer(r'\\DIFdel(?:FL)?\s*\{', frag):
        cont, _ = _grupo(frag, m.end() - 1)
        if 0 < len(norm(cont)) < 90:
            cortos += 1
    if cortos >= 2:
        return True
    # un solo fragmento viejo corto, pero incrustado en un pasaje nuevo largo,
    # se lee como una intrusion en medio de la frase
    largo_add = 0
    for m in re.finditer(r'\\DIFadd(?:FL)?\s*\{', frag):
        cont, _ = _grupo(frag, m.end() - 1)
        largo_add += len(norm(cont))
    if cortos >= 1 and largo_add >= 300:
        return True
    marcas = [m.group(1) for m in re.finditer(r'\\DIF(add|del)begin', frag)]
    return sum(1 for a, b in zip(marcas, marcas[1:]) if a != b) >= 3


def mezclado(frag):
    """Tiene texto borrado y texto agregado a la vez."""
    return '\\DIFadd' in frag and '\\DIFdel' in frag


def _tramos_en_ambito(marcado):
    """Spans de las secciones de SECCIONES_BARRIDAS, por su encabezado nuevo."""
    enc = [(m.start(), m.end()) for m in
           re.finditer(r'\\(?:sub)?section\{', marcado)]
    tramos = []
    for k, (a, b) in enumerate(enc):
        cont, fin_grupo = _grupo(marcado, b - 1)
        titulo = norm(proyeccion(cont, 'add')) or norm(proyeccion(cont, 'del'))
        pol = next((p for t, p in SECCIONES_BARRIDAS if t in titulo), None)
        if pol:
            fin = enc[k + 1][0] if k + 1 < len(enc) else len(marcado)
            tramos.append((a, b - 1, fin_grupo, fin, titulo, pol))
    return tramos


def _objetivos(marcado):
    """Todos los pasajes a convertir, como (ini, fin, nombre, clase)."""
    obj = []
    for nom, clase, ancla in BLOQUES:
        lim = limites(marcado, clase, ancla)
        if lim is None:
            obj.append((None, None, nom, clase)); continue
        obj.append((lim[0], lim[1], nom, clase))
    for a, ini_g, fin_g, fin, titulo, pol in _tramos_en_ambito(marcado):
        corto = titulo[:34]
        grupo = marcado[ini_g + 1:fin_g - 1]
        if pol in ('mixtos', 'enc+crit', 'encabezado') and mezclado(grupo):
            obj.append((ini_g + 1, fin_g - 1, f'enc: {corto}', 'encabezado'))
        if pol == 'encabezado':
            continue
        vistos = 0
        for m in re.finditer(r'(?s)(?:(?<=\n\n)|\A).*?(?=\n\n|\Z)',
                             marcado[fin_g:fin]):
            p = m.group(0)
            if len(p.split()) < 12:
                continue
            if pol == 'mixtos':
                tomar = mezclado(p)
            elif pol == 'primero':
                tomar = mezclado(p) and vistos == 0
            else:
                tomar = ilegible(p)
            if mezclado(p):
                vistos += 1
            if not tomar:
                continue
            if ATOMICO.search(p):
                obj.append((None, None, f'par: {corto}', 'OMITIDO: display math'))
                continue
            obj.append((fin_g + m.start(), fin_g + m.end(),
                        f'par: {corto}', 'parrafo'))
    return obj


def convertir(marcado, fuente_vieja, fuente_nueva):
    """Devuelve (marcado nuevo, informe de verificacion)."""
    nv, nn = norm(fuente_vieja), norm(fuente_nueva)
    obj = _objetivos(marcado)

    # de atras hacia adelante, para que los offsets no se muevan; y sin
    # solaparse, porque un pasaje de BLOQUES puede caer dentro de un tramo
    obj = [o for o in obj if o[0] is not None] + \
          [o for o in obj if o[0] is None]
    hechos, informe = [], []
    for ini, fin, nom, clase in sorted(
            [o for o in obj if o[0] is not None], key=lambda o: -o[0]):
        if any(not (fin <= a or ini >= b) for a, b in hechos):
            continue
        frag = marcado[ini:fin]
        pv, pn = proyeccion(frag, 'del'), proyeccion(frag, 'add')
        viejo, est_v = desde_fuente(pv, fuente_vieja)
        nuevo, est_n = desde_fuente(pn, fuente_nueva)
        # dos comprobaciones, no una: que el texto emitido este literal en su
        # fuente, y que sea EL pasaje, cotejado contra la proyeccion del diff
        ok_v = (viejo in nv and _cotejan(viejo, pv)) if viejo else None
        ok_n = (nuevo in nn and _cotejan(nuevo, pn)) if nuevo else None
        if est_v == 'fallo' or est_n == 'fallo':
            ok_v = False if viejo else ok_v
            ok_n = False if nuevo else ok_n
        ca, cd = colgantes(frag)
        rep = (r'\DIFaddend ' * ca) + (r'\DIFdelend ' * cd) + bloque(viejo, nuevo)
        if clase == 'parrafo':
            rep += '\n'
        marcado = marcado[:ini] + rep + marcado[fin:]
        hechos.append((ini, fin))
        informe.append((nom, f'{est_v}/{est_n}', ok_v, ok_n,
                        len(viejo), len(nuevo)))
    for ini, fin, nom, clase in [o for o in obj if o[0] is None]:
        informe.append((nom, clase if clase.startswith('OMITIDO')
                        else 'ANCLA NO ENCONTRADA', None, None, 0, 0))
    informe.reverse()
    return marcado, informe
