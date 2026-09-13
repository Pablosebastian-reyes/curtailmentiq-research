#!/usr/bin/env python3
"""
FASE 8: busqueda y VERIFICACION de referencias contra Crossref.
===============================================================
Comentario R2.1 y restriccion textual del editor (prohibidas las citas
agrupadas). La Regla Dura 3 del encargo: ninguna referencia entra sin DOI
verificable, autores reales y titulo real.

Este script no propone referencias de memoria. Consulta la API de Crossref por
tema, se queda con articulos de revista o de conferencia con DOI, y escribe los
metadatos EXACTOS que devuelve Crossref. Lo que no aparezca en la salida de este
script no entra a la bibliografia.

Uso:
  <venv>/bin/python flagship/revision/fase8_buscar_referencias.py buscar
  <venv>/bin/python flagship/revision/fase8_buscar_referencias.py verificar DOI [DOI ...]
"""
from pathlib import Path
import json
import subprocess
import sys
import time
import urllib.parse

MAIL = 'pablo.reyes.ce@usach.cl'
SAL = Path(__file__).resolve().parents[2] / 'resultados' / 'fase8'
SAL.mkdir(parents=True, exist_ok=True)

TEMAS = {
    'pronostico_de_vertimiento': [
        'renewable energy curtailment forecasting',
        'wind power curtailment prediction machine learning',
        'solar curtailment prediction power system',
    ],
    'operacion_de_almacenamiento': [
        'battery energy storage operation renewable curtailment',
        'grid scale battery storage dispatch optimisation',
        'energy storage sizing renewable integration',
    ],
    'congestion_de_transmision': [
        'transmission congestion management renewable curtailment',
        'locational marginal price congestion renewable',
    ],
    'capacidad_de_red_y_ampacidad': [
        'dynamic line rating transmission capacity',
        'dynamic thermal rating overhead line ampacity',
        'cable ampacity thermal rating underground power cable',
    ],
    'restricciones_termicas': [
        'thermal constraints power system operation dynamic rating',
        'conductor temperature thermal limit transmission line',
    ],
    'modelado_hibrido_fisico_datos': [
        'physics informed machine learning power systems',
        'hybrid physics data driven model energy forecasting',
    ],
    'pronostico_probabilistico': [
        'probabilistic forecasting wind power prediction intervals',
        'quantile regression forecasting electricity',
    ],
    'prediccion_conforme': [
        'conformal prediction time series distribution shift',
        'conformalized quantile regression',
        'adaptive conformal inference',
    ],
}


def crossref(q, rows=12, filtro='type:journal-article'):
    url = ('https://api.crossref.org/works?query.bibliographic='
           + urllib.parse.quote(q)
           + f'&rows={rows}&filter={filtro}&select=DOI,title,author,'
             'container-title,issued,is-referenced-by-count,type,publisher'
             f'&mailto={MAIL}')
    out = subprocess.run(['curl', '-s', '--max-time', '45', url],
                         capture_output=True, text=True)
    if out.returncode != 0 or not out.stdout.strip():
        return []
    try:
        return json.loads(out.stdout)['message']['items']
    except Exception:
        return []


def limpiar(it):
    au = it.get('author', []) or []
    def nom(a):
        return (a.get('family', '') + (', ' + a.get('given', '') if a.get('given') else '')
                ) or a.get('name', '')
    anio = None
    if it.get('issued', {}).get('date-parts', [[None]])[0]:
        anio = it['issued']['date-parts'][0][0]
    return dict(doi=it.get('DOI'),
                titulo=(it.get('title') or [''])[0],
                autores='; '.join(nom(a) for a in au[:8]),
                n_autores=len(au),
                revista=(it.get('container-title') or [''])[0],
                anio=anio, citas=it.get('is-referenced-by-count', 0),
                tipo=it.get('type'), editorial=it.get('publisher', ''))


def buscar():
    vistos, filas = set(), []
    for tema, consultas in TEMAS.items():
        print(f'\n{"=" * 92}\n{tema}\n{"=" * 92}')
        for q in consultas:
            for it in crossref(q):
                r = limpiar(it)
                if not r['doi'] or r['doi'] in vistos or not r['titulo']:
                    continue
                if not r['autores'] or not r['revista'] or not r['anio']:
                    continue
                vistos.add(r['doi'])
                r['tema'] = tema
                r['consulta'] = q
                filas.append(r)
            time.sleep(0.4)
        de = [f for f in filas if f['tema'] == tema]
        for r in sorted(de, key=lambda x: -x['citas'])[:12]:
            print(f'  [{r["citas"]:>5}] {r["anio"]}  {r["doi"]}')
            print(f'          {r["titulo"][:96]}')
            print(f'          {r["autores"][:96]} | {r["revista"][:60]}')
    import pandas as pd
    df = pd.DataFrame(filas).sort_values(['tema', 'citas'], ascending=[True, False])
    df.to_csv(SAL / 'candidatas_crossref.csv', index=False)
    print(f'\n{len(df)} candidatas verificadas guardadas en '
          f'{(SAL / "candidatas_crossref.csv")}')


def verificar(dois):
    """Resuelve cada DOI contra Crossref y devuelve los metadatos exactos."""
    filas = []
    for d in dois:
        url = f'https://api.crossref.org/works/{urllib.parse.quote(d)}?mailto={MAIL}'
        out = subprocess.run(['curl', '-s', '--max-time', '45', url],
                             capture_output=True, text=True)
        try:
            it = json.loads(out.stdout)['message']
            r = limpiar(it)
            r['resuelve'] = 'si'
        except Exception:
            r = dict(doi=d, resuelve='NO', titulo='', autores='', revista='',
                     anio=None, citas=0, tipo='', editorial='', n_autores=0)
        filas.append(r)
        print(f'{"OK " if r["resuelve"] == "si" else "FALLA"} {d}')
        if r['resuelve'] == 'si':
            print(f'      {r["titulo"]}')
            print(f'      {r["autores"]} ({r["anio"]}) {r["revista"]}')
        time.sleep(0.3)
    import pandas as pd
    pd.DataFrame(filas).to_csv(SAL / 'referencias_verificadas.csv', index=False)
    print(f'\nguardado {(SAL / "referencias_verificadas.csv")}')


def _norm(s):
    """Minusculas, sin acentos ni comandos LaTeX, solo letras y digitos."""
    import re
    import unicodedata
    s = re.sub(r"\\[`'^\"~=.uvHcdbtr]\s*\{?\\?([a-zA-Z])\}?", r'\1', s)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'\\[a-zA-Z]+', ' ', s).replace('--', ' ').lower()
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', s).split())


def _json(url):
    out = subprocess.run(['curl', '-s', '--max-time', '45', '-w', '\n%{http_code}', url],
                         capture_output=True, text=True)
    cuerpo, _, st = out.stdout.rpartition('\n')
    return (json.loads(cuerpo) if st == '200' else None), st


def cotejar():
    """Resuelve cada DOI de la bibliografia del manuscrito y coteja el registro
    contra la entrada: titulo, primer autor, anio y revista.

    Crossref para los DOI de editorial; DataCite para el del dataset, porque
    Zenodo registra sus DOI ahi y Crossref devuelve 404. Si Crossref no trae
    autores (le pasa a Econometrica 78(3)), el primer autor se coteja contra
    OpenAlex. Las entradas sin DOI quedan listadas y sin cotejo. El titulo
    coteja si al menos el 90 % de sus palabras de mas de dos letras estan en la
    entrada; la columna titulo_exacto dice ademas si aparece completo.

    Salida: resultados/fase8/bibliografia_cotejada.csv. Sale con codigo 1 si
    algun DOI no resuelve o no coteja.
    """
    import re
    import pandas as pd
    tex = (Path(__file__).resolve().parents[1] / 'segan' / 'SEGAN_paper_FINAL.tex').read_text()
    bib = tex[tex.find('\\begin{thebibliography}'):tex.find('\\end{thebibliography}')]
    filas = []
    for it in re.split(r'\\bibitem', bib)[1:]:
        clave = re.match(r'\s*(?:\[[^\]]*\])?\{([^}]*)\}', it).group(1)
        d = re.findall(r'doi:\s*(10\.\d{4,9}/[^\s},]+)', it, flags=re.I)
        if not d:
            filas.append(dict(clave=clave, doi='', fuente='sin DOI', http='', coteja=''))
            continue
        doi = d[0].rstrip('.')
        titulo = autor1 = revista = ''
        anios, cortas = [], []
        if doi.lower().startswith('10.5281/'):
            fuente = 'DataCite'
            j, st = _json(f'https://api.datacite.org/dois/{doi}')
            if j:
                a = j['data']['attributes']
                titulo = a['titles'][0]['title']
                c0 = a['creators'][0]
                autor1 = c0.get('familyName', c0.get('name', ''))
                anios = [a.get('publicationYear')]
                revista = a.get('publisher', '')
                revista = revista.get('name', '') if isinstance(revista, dict) else revista
        else:
            fuente = 'Crossref'
            j, st = _json(f'https://api.crossref.org/works/{urllib.parse.quote(doi)}?mailto={MAIL}')
            if j:
                m = j['message']
                titulo = (m.get('title') or [''])[0]
                au = m.get('author') or []
                autor1 = au[0].get('family', au[0].get('name', '')) if au else ''
                anios = sorted({(m.get(k) or {}).get('date-parts', [[None]])[0][0]
                                for k in ('issued', 'published-print', 'published-online')} - {None})
                revista = (m.get('container-title') or [''])[0]
                cortas = m.get('short-container-title') or []
                if not autor1:
                    o, _ = _json(f'https://api.openalex.org/works/doi:{doi}')
                    if o and o.get('authorships'):
                        autor1 = o['authorships'][0]['author']['display_name'].split()[-1]
                        fuente = 'Crossref (autores de OpenAlex)'
        ni = _norm(it)
        tok = [w for w in _norm(titulo).split() if len(w) > 2]
        cob = sum(w in set(ni.split()) for w in tok) / max(len(tok), 1)
        f = dict(clave=clave, doi=doi, fuente=fuente, http=st, titulo_registro=titulo,
                 titulo_exacto=bool(titulo) and _norm(titulo) in ni, titulo_cobertura=round(cob, 2),
                 titulo_ok=bool(titulo) and cob >= 0.9,
                 autor1_registro=autor1, autor1_ok=bool(autor1) and _norm(autor1) in ni,
                 anios_registro=' '.join(map(str, anios)),
                 anio_ok=bool({str(a) for a in anios} & set(re.findall(r'\b(19\d\d|20\d\d)\b', it))),
                 revista_registro=revista,
                 revista_ok=any(c and _norm(c) in ni for c in [revista] + cortas))
        f['coteja'] = 'si' if st == '200' and all(f[k] for k in ('titulo_ok', 'autor1_ok', 'anio_ok', 'revista_ok')) else 'NO'
        filas.append(f)
        print(f"{'OK ' if f['coteja'] == 'si' else 'FALLA'} {clave:18s} {doi}  [{fuente}]")
        time.sleep(0.3)
    df = pd.DataFrame(filas)
    df.to_csv(SAL / 'bibliografia_cotejada.csv', index=False)
    con = df[df.doi != '']
    print(f'\n{len(df)} entradas: {len(con)} con DOI ({(con.fuente.str.startswith("Crossref")).sum()} Crossref, '
          f'{(con.fuente == "DataCite").sum()} DataCite), {len(df) - len(con)} sin DOI '
          f'({", ".join(df[df.doi == ""].clave)}). Cotejan: {(con.coteja == "si").sum()} de {len(con)}.')
    print(f'guardado {(SAL / "bibliografia_cotejada.csv")}')
    sys.exit(0 if (con.coteja == 'si').all() else 1)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'verificar':
        verificar(sys.argv[2:])
    elif len(sys.argv) > 1 and sys.argv[1] == 'cotejar':
        cotejar()
    else:
        buscar()
