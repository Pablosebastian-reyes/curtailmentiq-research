#!/usr/bin/env python3
"""
PASO 4: registro ciego de los numeros obtenidos en ESTA corrida.
================================================================
Se escribe ANTES de abrir el manuscrito o los resultados versionados. Lee
unicamente lo que acaban de producir fase0_model_agnostic.py y
fase0_diagnostico.py en este clon.

Salida: resultados/verificacion/paso4_mis_numeros.md
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
SAL = REPO / 'resultados' / 'verificacion'
F0 = REPO / 'resultados' / 'fase0'

t = pd.read_csv(F0 / 'fase0_tabla_por_modelo.csv')
d = pd.read_csv(F0 / 'fase0_diagnostico.csv')
b = pd.read_csv(F0 / 'fase0_diferencias_bootstrap.csv')

L = []
P = L.append
P('# Paso 4: mis numeros, antes de comparar con nada\n')
P('Producidos por esta corrida en el clon limpio, entorno recien construido.\n')

P('## Tabla de 3 modelos base x 6 metodos, ventana de transicion\n')
P('| modelo base | metodo | cobertura | se | ancho | % inf | IS finitos | CRPS |')
P('|---|---|---|---|---|---|---|---|')
tr = t[t.periodo == 'test_transition']
for _, r in tr.iterrows():
    P(f'| {r.modelo_base} | {r.metodo} | {r.cobertura} | {r.se_cluster} | '
      f'{r.ancho_medio} | {r.pct_infinito} | {r.IS_finitos} | {r.crps_base} |')

P('\n## Diferencias de ancho Transporte+ACI(0.05) menos estatico, transicion\n')
P('| modelo base | diferencia | IC 95% bootstrap por dia |')
P('|---|---|---|')
bt = b[(b.metodo == '4_transporte_banda_g05') & (b.periodo == 'test_transition')]
for _, r in bt.iterrows():
    P(f'| {r.modelo_base} | {r.d_ancho:+.1f} MWh | [{r.ancho_lo:+.1f}, {r.ancho_hi:+.1f}] |')

P('\n## Diagnostico: ajuste sobre las 15 celdas\n')
x, y = d.sobrecobertura_pp.values, d.cambio_ancho_pct.values
r = float(np.corrcoef(x, y)[0, 1])
m, c = np.polyfit(x, y, 1)
P(f'- r de Pearson: **{r:.6f}**')
P(f'- pendiente: **{m:.6f}** % de ancho por punto porcentual')
P(f'- intercepto: **{c:.6f}** %')
P(f'- celdas: {len(d)}')

P('\n## Las 15 celdas\n')
P('| modelo base | ventana | sobre-cobertura pp | cambio de ancho % |')
P('|---|---|---|---|')
for _, rr in d.iterrows():
    P(f'| {rr.modelo_base} | {rr.periodo} | {rr.sobrecobertura_pp:+.2f} | '
      f'{rr.cambio_ancho_pct:+.2f} |')

(SAL / 'paso4_mis_numeros.md').write_text('\n'.join(L) + '\n')
print('\n'.join(L))
print(f'\nguardado {SAL / "paso4_mis_numeros.md"}')
