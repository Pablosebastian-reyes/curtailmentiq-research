#!/usr/bin/env python3
"""
OBJECION 1b: escalera de capacidad a rejilla FIJA de 54 niveles.
================================================================
El brazo de rejilla gruesa del experimento anterior no sirve para comparar CRPS:
al muestrear de una rejilla truncada en tau = 0.9, toda la masa por encima de ese
nivel colapsa al cuantil 0.9 y el CRPS sale sesgado a la baja. Se descarta.

Aqui se fija la rejilla en los 54 niveles (cola hasta 0.999, truncamiento
despreciable) y se varia SOLO el numero de arboles por nivel, para situar donde
aparece la ventaja de CRPS del GBM sobre el hurdle.
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'flagship'))
sys.path.insert(0, str(REPO / 'flagship' / 'revision'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev_lib as R                                  # noqa: E402
import fase0_entrenar_qgbm as QG                     # noqa: E402
import obj1_capacidad_contra_forma as O1             # noqa: E402

df_tr, df_pr = O1.panel()
filas = []
for n_est in (15, 50, 100, 200, 400):
    pred, arb = O1.entrenar_qgbm(df_tr, df_pr, QG.TAUS, n_est)
    f = O1.evaluar(f'qgbm_54x{n_est}', pred, df_pr, arb)
    filas += f
    tr = [x for x in f if x['periodo'] == 'test_transition' and x['metodo'] == 'estatico'][0]
    tt = [x for x in f if x['periodo'] == 'TEST_COMPLETO' and x['metodo'] == 'estatico'][0]
    print(f'  54 x {n_est:>3} = {arb:>5} arboles   CRPS transicion {tr["crps"]:7.2f}   '
          f'CRPS test {tt["crps"]:6.2f}   cobertura estatica {tt["cobertura"]:5.1f}%')
pd.DataFrame(filas).to_csv(REPO / 'resultados' / 'verificacion' / 'obj1b_escalera.csv', index=False)
print('\nreferencia del hurdle de 800 arboles: CRPS transicion 133.52, test 89.52')
