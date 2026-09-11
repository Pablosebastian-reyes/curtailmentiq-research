#!/usr/bin/env python3
"""
MAE puntual del hurdle con deteccion temprana, sobre las filas de la Tabla 2.
=============================================================================
Pregunta acotada: el hurdle con deteccion temprana mejora el CRPS del modelo base
oficial en 5.7% (ver obj1d). ¿Que hace con el MAE de su mediana de mixtura, que
es lo que la Tabla 2 reporta y lo que sostiene la afirmacion de la Seccion 5.1
sobre el pronostico puntual?

Importa porque el descuento de la Seccion 7 deja fuera a proposito la Tabla 2: el
descuento ahi no corre en una sola direccion, porque un hurdle mejor acercaria su
MAE al del naive estacional en vez de alejarlo. Esto lo mide.

CONTROL, sin el cual el numero no seria comparable. El script recomputa primero
el MAE del hurdle OFICIAL con el mismo pipeline y exige que reproduzca la Tabla 2
celda a celda: 104.43, 104.82, 101.60 y 104.08. Si no lo reproduce, se aborta,
porque entonces la diferencia entre los dos numeros vendria del pipeline y no del
modelo.

Mismas filas, mismo periodo, misma mediana de mixtura (`EB.mediana_hurdle`),
misma semilla. NO modifica la Tabla 2 ni ningun texto.

Salida: resultados/verificacion/obj1e_mae_hurdle_es.json

Comando:
  <venv>/bin/python flagship/revision/verificacion/obj1e_mae_hurdle_es.py
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'flagship'))
sys.path.insert(0, str(REPO / 'flagship' / 'revision'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import entrenar_baselines as EB            # noqa: E402
import obj1_capacidad_contra_forma as O1   # noqa: E402
import obj1d_hurdle_deteccion_temprana as O1D   # noqa: E402

SAL = REPO / 'resultados' / 'verificacion'
# valores de la Tabla 2, de flagship/predicciones/README.md
REF_OFICIAL = {'2024': 104.43, '2025': 104.82, '2026': 101.60, 'total': 104.08}
REF_FILAS = {'2024': 40549, '2025': 44725, '2026': 19146}
NAIVE_TOTAL = 85.10


def mae_por_anio(pred, y, anio):
    out = {}
    for a in sorted(anio.unique()):
        m = anio == a
        out[str(a)] = float(np.abs(pred[m] - y[m]).mean())
    out['total'] = float(np.abs(pred - y).mean())
    return out


def main():
    print('=' * 88)
    print('MAE PUNTUAL DEL HURDLE CON DETECCION TEMPRANA, filas de la Tabla 2')
    print('=' * 88)
    df_tr, df_pr = O1.panel()
    y = df_pr.y_real.values
    anio = df_pr.fecha.dt.year
    print(f'filas fuera de muestra: {len(df_pr):,}')
    for a, n in REF_FILAS.items():
        obt = int((anio == int(a)).sum())
        estado = 'OK' if obt == n else f'DISTINTO, la Tabla 2 dice {n}'
        print(f'  {a}: {obt:,}  {estado}')
        if obt != n:
            sys.exit(f'las filas no coinciden con la Tabla 2 en {a}')

    # ---------------- control: el hurdle oficial ----------------
    print('\n' + '-' * 88)
    print('CONTROL: recomputar el MAE del hurdle OFICIAL con este pipeline')
    print('-' * 88)
    pred_of, arb_of, sg_of = O1.entrenar_hurdle(df_tr, df_pr, 400)
    med_of = EB.mediana_hurdle(pred_of.p, pred_of.mu, sg_of)
    mae_of = mae_por_anio(med_of, y, anio)
    print(f'  {arb_of} arboles, sigma {sg_of:.4f}')
    print(f'  {"periodo":9s} {"recomputado":>12s} {"Tabla 2":>10s} {"dif":>8s}')
    malo = False
    for k in ('2024', '2025', '2026', 'total'):
        d = mae_of[k] - REF_OFICIAL[k]
        if abs(d) > 0.006:
            malo = True
        print(f'  {k:9s} {mae_of[k]:>12.2f} {REF_OFICIAL[k]:>10.2f} {d:>+8.3f}')
    if malo:
        sys.exit('\nel pipeline NO reproduce la Tabla 2: el numero nuevo no seria '
                 'comparable, se aborta')
    print('\n  el pipeline reproduce la Tabla 2 celda a celda; la comparacion es valida')

    # ---------------- el hurdle con deteccion temprana ----------------
    print('\n' + '-' * 88)
    print('HURDLE CON DETECCION TEMPRANA')
    print('-' * 88)
    pred_es, arb_es, sg_es, etapas = O1D.entrenar_con_es(df_tr, df_pr)
    med_es = EB.mediana_hurdle(pred_es.p, pred_es.mu, sg_es)
    mae_es = mae_por_anio(med_es, y, anio)
    print(f'    {arb_es} arboles, sigma {sg_es:.4f}')

    print('\n' + '=' * 88)
    print('RESULTADO: MAE (MWh) de la mediana de la mixtura')
    print('=' * 88)
    print(f'  {"periodo":9s} {"hurdle oficial":>15s} {"hurdle con ES":>15s} {"cambio":>9s}')
    for k in ('2024', '2025', '2026', 'total'):
        print(f'  {k:9s} {mae_of[k]:>15.2f} {mae_es[k]:>15.2f} '
              f'{100*(mae_es[k]/mae_of[k]-1):>+8.1f}%')

    print('\n' + '-' * 88)
    print('ORDEN FRENTE A LOS BASELINES DE LA TABLA 2 (total, menor es mejor)')
    print('-' * 88)
    # Las filas se LEEN de la tabla generada, no se escriben a mano. Una version
    # anterior de este script las llevaba cableadas y omitio la fila del GBM
    # multi-cuantil, que si esta en la Tabla 2 con 87.6.
    import re as _re
    tex = (REPO / 'resultados' / 'tablas_tex' / 'tab_mae.tex').read_text()
    tabla = []
    for ln in tex.split('\n'):
        m = _re.match(r'^([A-Z][^&]*?) & [\d.]+ & [\d.]+ & [\d.]+ & ([\d.]+) \\\\', ln.strip())
        if m:
            tabla.append((m.group(1).strip(), float(m.group(2))))
    if len(tabla) < 5:
        sys.exit(f'no se pudieron leer las filas de tab_mae.tex (halladas {len(tabla)})')
    print(f'  ({len(tabla)} filas leidas de resultados/tablas_tex/tab_mae.tex)')
    tabla.append(('Hurdle with early stopping', mae_es['total']))
    for nm, v in sorted(tabla, key=lambda x: x[1]):
        marca = '  <-- nuevo' if nm.startswith('Hurdle with early') else ''
        print(f'  {v:7.2f}  {nm}{marca}')

    naive = [v for nm, v in tabla if 'naive' in nm.lower()]
    if not naive:
        sys.exit('no se hallo la fila del naive estacional en tab_mae.tex')
    naive_total = naive[0]
    gana_naive = mae_es['total'] > naive_total
    print('\n' + '=' * 88)
    if gana_naive:
        print(f'VEREDICTO: el naive estacional SIGUE GANANDO.')
        print(f'  {mae_es["total"]:.2f} contra {naive_total:.2f}, '
              f'{mae_es["total"]-naive_total:+.2f} MWh, '
              f'{100*(mae_es["total"]/naive_total-1):+.1f}%')
        print('  La afirmacion de la Seccion 5.1 no se ve afectada en su direccion.')
    else:
        print(f'VEREDICTO: el hurdle con deteccion temprana GANA al naive estacional.')
        print(f'  {mae_es["total"]:.2f} contra {naive_total:.2f}, '
              f'{mae_es["total"]-naive_total:+.2f} MWh, '
              f'{100*(mae_es["total"]/naive_total-1):+.1f}%')
        print('  ESTO AFECTA la Seccion 5.1, la 6.2 y la conclusion. DETENERSE.')
    print('=' * 88)

    json.dump(dict(filas=len(df_pr), mae_hurdle_oficial=mae_of,
                   mae_hurdle_es=mae_es, arboles_es=arb_es, sigma_es=sg_es,
                   etapas_es=etapas, naive_estacional_total=naive_total,
                   orden_tabla2=[(nm, v) for nm, v in sorted(tabla, key=lambda x: x[1])],
                   naive_sigue_ganando=bool(gana_naive),
                   control_reproduce_tabla2=True),
              open(SAL / 'obj1e_mae_hurdle_es.json', 'w'), indent=1)
    print(f'\nguardado {SAL / "obj1e_mae_hurdle_es.json"}')


if __name__ == '__main__':
    main()
