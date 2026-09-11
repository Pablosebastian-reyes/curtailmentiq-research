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

def _mas_largo(proy, fuente, sufijo=False):
    """Longitud del prefijo (o sufijo) mas largo de proy presente en fuente."""
    lo, hi = 0, len(proy)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        trozo = proy[-mid:] if sufijo else proy[:mid]
        if trozo in fuente: lo = mid
        else: hi = mid - 1
    return lo


def desde_fuente(proy, fuente, minimo=40):
    """Texto de la FUENTE correspondiente al pasaje, verbatim.

    Se ubica la proyeccion por sus dos extremos y se devuelve lo que hay en la
    fuente entre ellos. Asi el bloque emitido calza con la fuente aunque
    latexdiff haya perdido un caracter dentro del pasaje: en el abstract de la
    version enviada se come el espacio de "system operator figures" y lo emite
    como "operatorfigures", dentro de un unico \\DIFdel.

    Devuelve (texto, estado) con estado en {'exacto', 'reconstruido', 'fallo'}.
    """
    if not proy:
        return '', 'exacto'
    if proy in fuente:
        return proy, 'exacto'
    npre, nsuf = _mas_largo(proy, fuente), _mas_largo(proy, fuente, sufijo=True)
    if npre < minimo or nsuf < minimo:
        return proy, 'fallo'
    i = fuente.find(proy[:npre])
    j = fuente.find(proy[-nsuf:], i)
    if j < 0 or j + nsuf <= i:
        return proy, 'fallo'
    texto = fuente[i:j + nsuf]
    # el pasaje reconstruido no puede diferir en mas de un 2% del proyectado:
    # si difiere mas, las anclas cayeron en el lugar equivocado
    if abs(len(texto) - len(proy)) > max(8, 0.02 * len(proy)):
        return proy, 'fallo'
    return texto, 'reconstruido'


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

def convertir(marcado, fuente_vieja, fuente_nueva):
    """Devuelve (marcado nuevo, informe de verificacion)."""
    nv, nn = norm(fuente_vieja), norm(fuente_nueva)
    informe = []
    for nom, clase, ancla in BLOQUES:
        lim = limites(marcado, clase, ancla)
        if lim is None:
            informe.append((nom, 'ANCLA NO ENCONTRADA', None, None, 0, 0)); continue
        ini, fin, frag = lim
        viejo, est_v = desde_fuente(norm(proyeccion(frag, 'del')), nv)
        nuevo, est_n = desde_fuente(norm(proyeccion(frag, 'add')), nn)
        ok_v = (viejo in nv) if viejo else None
        ok_n = (nuevo in nn) if nuevo else None
        ca, cd = colgantes(frag)
        nuevo_frag = (r'\DIFaddend ' * ca) + (r'\DIFdelend ' * cd) + bloque(viejo, nuevo)
        if clase == 'parrafo':
            nuevo_frag = nuevo_frag + '\n'
        marcado = marcado[:ini] + nuevo_frag + marcado[fin:]
        informe.append((nom, f'{est_v}/{est_n}', ok_v, ok_n,
                        len(viejo), len(nuevo)))
    return marcado, informe
