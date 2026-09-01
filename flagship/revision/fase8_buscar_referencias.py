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


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'verificar':
        verificar(sys.argv[2:])
    else:
        buscar()
