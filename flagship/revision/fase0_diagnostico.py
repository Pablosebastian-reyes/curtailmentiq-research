#!/usr/bin/env python3
"""
FASE 0, paso 3: diagnostico del hallazgo.
=========================================
Lee `resultados/fase0/fase0_tabla_por_modelo.csv` y cuantifica la relacion
entre (i) cuanto sobre-cubre el split estatico en una ventana bajo un modelo
base dado y (ii) cuanto ancho le recorta ahi Transporte+ACI.

Si la ganancia de la capa adaptativa fuese una propiedad de la capa, seria
aproximadamente constante entre modelos base. Si es una reparacion de la
mala calibracion del modelo base, debe ser proporcional a la sobre-cobertura
del split estatico. Este script decide entre las dos lecturas.

Salida: resultados/fase0/fase0_diagnostico.csv y numeros citables en el .md

Comando:
  <venv>/bin/python flagship/revision/fase0_diagnostico.py
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rev_lib as R   # noqa: E402

SAL = R.REPO / 'resultados' / 'fase0'
NOMINAL = 100 * (1 - R.ALPHA)


def main():
    t = pd.read_csv(SAL / 'fase0_tabla_por_modelo.csv')
    est = t[t.metodo == '1_estatico_pit'].set_index(['modelo_base', 'periodo'])
    tra = t[t.metodo == '4_transporte_banda_g05'].set_index(['modelo_base', 'periodo'])

    d = pd.DataFrame({
        'cob_estatico': est.cobertura,
        'sobrecobertura_pp': (est.cobertura - NOMINAL).round(2),
        'ancho_estatico': est.ancho_medio,
        'ancho_transporte': tra.ancho_medio,
        'cob_transporte': tra.cobertura,
        'IS_estatico': est.IS_finitos,
        'IS_transporte': tra.IS_finitos,
        'crps_base': est.crps_base,
    })
    d['cambio_ancho_pct'] = (100 * (d.ancho_transporte / d.ancho_estatico - 1)).round(1)
    d['cambio_IS_pct'] = (100 * (d.IS_transporte / d.IS_estatico - 1)).round(1)
    d = d.reset_index()

    print('=' * 96)
    print('FASE 0 - DIAGNOSTICO')
    print('=' * 96)
    print(d.to_string(index=False))

    # El ajuste se hace sobre los valores EXACTOS, leidos de las series por
    # fila, no sobre las columnas de la tabla, que van redondeadas a un decimal
    # para mostrarse. Ajustar sobre las redondeadas desplaza r en 0.002 y la
    # pendiente en 0.02: inmaterial, pero no hay razon para publicar el valor
    # peor cuando el exacto esta disponible.
    ser = SAL / 'series'
    if ser.exists() and len(list(ser.glob('*.parquet'))) >= 3:
        ex = []
        for _, r_ in d.iterrows():
            f = pd.read_parquet(ser / f'{r_.modelo_base}.parquet')
            ini, fin = [(a, b) for nm, a, b in R.PERIODOS if nm == r_.periodo][0]
            m = ((pd.to_datetime(f.fecha) >= ini)
                 & (pd.to_datetime(f.fecha) < fin)).values
            yv, Ue, Ut = f.y.values[m], f.U_est.values[m], f.U_tr.values[m]
            fe, ft = np.isfinite(Ue), np.isfinite(Ut)
            ex.append((100 * float((yv <= Ue).mean()) - NOMINAL,
                       100 * (float(Ut[ft].mean()) / float(Ue[fe].mean()) - 1)))
        d['sobrecobertura_pp_exacta'] = [e[0] for e in ex]
        d['cambio_ancho_pct_exacto'] = [e[1] for e in ex]
        x = d.sobrecobertura_pp_exacta.values
        y = d.cambio_ancho_pct_exacto.values
        print('  ajuste sobre valores exactos (series por fila)')
    else:
        x = d.sobrecobertura_pp.values
        y = d.cambio_ancho_pct.values
        print('  AVISO: sin series por fila, se ajusta sobre valores redondeados')
    r = float(np.corrcoef(x, y)[0, 1])
    b = np.polyfit(x, y, 1)
    d['r_ajuste'] = round(r, 6)
    d['pendiente_ajuste'] = round(float(b[0]), 6)
    d['intercepto_ajuste'] = round(float(b[1]), 6)
    d.to_csv(SAL / 'fase0_diagnostico.csv', index=False)
    print('\n' + '-' * 96)
    print('Relacion entre sobre-cobertura del split estatico y recorte de ancho')
    print(f'de Transporte+ACI, sobre las {len(d)} celdas (modelo base x ventana):')
    print(f'  correlacion de Pearson r = {r:.3f}')
    print(f'  pendiente: {b[0]:.2f} % de ancho por punto porcentual de sobre-cobertura')
    print(f'  intercepto: {b[1]:.2f} % (recorte esperado con el split ya en nominal)')

    print('\n' + '-' * 96)
    print('Ranking por interval score (metrica propia, penaliza ancho y no cobertura):')
    for per in [p for p, _, _ in R.PERIODOS]:
        s = t[t.periodo == per].nsmallest(3, 'IS_finitos')
        best = s.iloc[0]
        print(f'  {per:16s} mejor = {best.modelo_base} / {best.metodo} '
              f'(IS {best.IS_finitos:.1f}, cob {best.cobertura}%, '
              f'ancho {best.ancho_medio:.0f} MWh)')

    print('\n' + '-' * 96)
    print('CRPS del modelo base por ventana (propiedad de la predictiva):')
    c = t.pivot_table(index='periodo', columns='modelo_base', values='crps_base')
    c = c.reindex([p for p, _, _ in R.PERIODOS])
    c['mejora_qgbm_vs_hurdle_pct'] = (100 * (c.qgbm_multi / c.hurdle - 1)).round(1)
    print(c.to_string())

    print('\n' + '-' * 96)
    print('Brier del evento {Y>0} por ventana. AVISO: para el qgbm la')
    print('probabilidad de ocurrencia es 1 - F(0) leida de la rejilla de')
    print('cuantiles, con resolucion 0.02, y no un clasificador dedicado como')
    print('el del hurdle. La comparacion no es equivalente y se reporta como')
    print('descriptiva, no como veredicto.')
    bq = t.pivot_table(index='periodo', columns='modelo_base', values='brier_base')
    print(bq.reindex([p for p, _, _ in R.PERIODOS]).to_string())
    print('\nguardado', (SAL / 'fase0_diagnostico.csv').relative_to(R.REPO))


if __name__ == '__main__':
    main()
