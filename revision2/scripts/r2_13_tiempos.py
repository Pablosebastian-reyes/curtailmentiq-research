#!/usr/bin/env python3
"""
R2-13. Tiempos de computo limpios de cada componente (Tabla de ablaciones).

r2_02 mide tiempos mientras corren en paralelo la simulacion y la
sensibilidad, asi que sus segundos estan inflados por la contencion de CPU.
Este script, corrido con la maquina en reposo, repite cada componente tres
veces sobre el hurdle de referencia y guarda la mediana. Los resultados de las
capas no cambian (son deterministas); solo los segundos.

Salida: resultados/r2_13_tiempos.csv (mismo formato que r2_02_tiempos.csv)
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_lib as L                      # noqa: E402
import numpy as np                      # noqa: E402
import pandas as pd                     # noqa: E402
import r2_02_metodos as M2              # noqa: E402
R = L.R


def main():
    filas = []
    for b in L.PRINCIPALES:
        c = L.contexto(b)
        h, p_t, s_cal = c['h'], c['p_t'], c['s_cal']
        y_t, f_t, ft = c['y_t'], c['f_t'], c['fechas_test']
        comp = {
            'static': lambda: R.estatico(p_t, s_cal),
            'aci_g05': lambda: R.aci(p_t, s_cal, y_t, f_t, ft, 0.05),
            'ab_tr_fijo': lambda: M2.transporte_sin_aci(c, np.random.default_rng(R.SEED_CONFORMAL)),
            'ab_tr_sinshrink_g05': lambda: R.transporte_aci(p_t, s_cal, h.s.values, h.fecha.values, y_t, f_t, ft,
                                                            0.05, np.random.default_rng(R.SEED_CONFORMAL),
                                                            shrinkage=False, ini_test=R.CAL_FIN),
            'tr_g05': lambda: R.transporte_aci(p_t, s_cal, h.s.values, h.fecha.values, y_t, f_t, ft, 0.05,
                                               np.random.default_rng(R.SEED_CONFORMAL), ini_test=R.CAL_FIN),
        }
        for k, fn in comp.items():
            ts = []
            for _ in range(3):
                t0 = time.perf_counter(); fn(); ts.append(time.perf_counter() - t0)
            filas.append(dict(brazo=b, componente=k, segundos=round(float(np.median(ts)), 3)))
            L.log(f'{b} {k}: {np.median(ts):.2f} s', 'r2_13_tiempos.log')
    pd.DataFrame(filas).to_csv(L.RES / 'r2_13_tiempos.csv', index=False)


if __name__ == '__main__':
    main()
