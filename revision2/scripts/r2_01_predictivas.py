#!/usr/bin/env python3
"""
R2-01. Predictivas de los nueve modelos base, persistidas y verificadas.
=======================================================================
La R1 guardo las predicciones de tres modelos base (hurdle 2x400, hurdle
sigma(x) y GBM multi-cuantil 54x400) pero de los brazos de la escalera de
capacidad solo guardo dos series por fila (U del split estatico y de
Transport+ACI 0.05). El diagnostico de la R2 necesita la predictiva completa de
cada brazo (para el oraculo en espacio PIT y para re-correr la capa con alpha
acotado), y el comentario 2 del Revisor 2 pide el hurdle con detencion
temprana como modelo base completo. Este script:

  1. Carga las tres predictivas guardadas por la R1.
  2. Reentrena, con el MISMO codigo de la R1 (obj1, obj1d), el hurdle con
     detencion temprana, el hurdle 2x2000 y los GBM 54x15, 54x50, 54x100 y
     54x200. Semilla 42, mismas features, mismas filas, corte 2023-12-31.
  3. Verifica cada brazo contra lo que la R1 ya publico o registro:
       - brazos guardados: U estatico y U Transport+ACI(0.05) de
         resultados/fase0/series, fila a fila;
       - brazos reentrenados: las series de resultados/verificacion/series;
       - hurdle con detencion temprana: cobertura y ancho por ventana de
         resultados/verificacion/obj1d_deteccion_temprana.csv.

Salidas: resultados/predictivas/*.npz, resultados/r2_01_verificacion.csv
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_lib as L                      # noqa: E402
import numpy as np                      # noqa: E402
import pandas as pd                     # noqa: E402
R = L.R

LOG = 'r2_01_predictivas.log'


def cargar_guardadas(h):
    out = {}
    hu = pd.read_csv(L.REPO / 'flagship/predicciones/pred_hurdle.csv', parse_dates=['fecha'])
    hu = hu.sort_values(['fecha', 'central_codigo']).reset_index(drop=True)
    assert (hu.central_codigo.values == h.central_codigo.values).all()
    out['hurdle_800'] = R.PredictivaHurdle(hu.p_occ.values, hu.mu_log.values,
                                           float(hu.sigma.iloc[0]))
    hx = pd.read_csv(L.REPO / 'flagship/predicciones/pred_hurdle_hetero.csv', parse_dates=['fecha'])
    hx = hx.sort_values(['fecha', 'central_codigo']).reset_index(drop=True)
    assert (hx.central_codigo.values == h.central_codigo.values).all()
    out['hurdle_sigma_x'] = R.PredictivaHurdle(hx.p_occ.values, hx.mu_log.values,
                                               hx.sigma_x.values)
    q = pd.read_csv(L.REPO / 'flagship/predicciones/pred_qgbm_multi.csv.gz', parse_dates=['fecha'])
    q = q.sort_values(['fecha', 'central_codigo']).reset_index(drop=True)
    assert (q.central_codigo.values == h.central_codigo.values).all()
    cols = [c for c in q.columns if c.startswith('q0') or c.startswith('q1')]
    taus = np.array([float(c[1:]) for c in cols])
    o = np.argsort(taus)
    out['qgbm_54x400'] = R.PredictivaCuantilica(q[[cols[i] for i in o]].values, taus[o])
    return out


def reentrenar(h):
    import obj1_capacidad_contra_forma as O1
    import obj1d_hurdle_deteccion_temprana as O1D
    import fase0_entrenar_qgbm as QG
    df_tr, df_pr = O1.panel()
    L.log(f'panel: train {len(df_tr):,} filas, prediccion {len(df_pr):,}', LOG)
    s = df_pr[['fecha', 'central_codigo', 'y_real']].sort_values(['fecha', 'central_codigo'])
    orden = s.index.values
    assert (s.central_codigo.values == h.central_codigo.values).all()
    assert np.allclose(s.y_real.values, h.y_real.values, rtol=0, atol=1e-6)   # CSV de la R1 redondea a 6 decimales
    out, meta = {}, {}
    pred, arb, sg, el = O1D.entrenar_con_es(df_tr, df_pr)
    out['hurdle_es'] = pred.sub(orden)
    meta['hurdle_es'] = dict(arboles=arb, sigma=sg, por_etapa=el)
    L.log(f'hurdle_es: {arb} arboles {el}, sigma {sg:.4f}', LOG)
    pred, arb, sg = O1.entrenar_hurdle(df_tr, df_pr, 2000)
    out['hurdle_2000'] = pred.sub(orden)
    meta['hurdle_2000'] = dict(arboles=arb, sigma=sg)
    L.log(f'hurdle_2000: {arb} arboles, sigma {sg:.4f}', LOG)
    for n in (15, 50, 100, 200):
        t0 = L.time.perf_counter()
        pred, arb = O1.entrenar_qgbm(df_tr, df_pr, QG.TAUS, n)
        out[f'qgbm_54x{n}'] = pred.sub(orden)
        meta[f'qgbm_54x{n}'] = dict(arboles=arb)
        L.log(f'qgbm_54x{n}: {arb} arboles ({L.time.perf_counter() - t0:.0f} s)', LOG)
    return out, meta


def series_canonicas(nombre):
    """U estatico y U Transport+ACI(0.05) con el orden canonico del
    generador (score, luego T+ACI 0.02, luego T+ACI 0.05)."""
    c = L.contexto(nombre)
    U_est = R.estatico(c['p_t'], c['s_cal'])
    R.transporte_aci(c['p_t'], c['s_cal'], c['h'].s.values, c['h'].fecha.values,
                     c['y_t'], c['f_t'], c['fechas_test'], 0.02, c['rng'],
                     ini_test=R.CAL_FIN)
    U_tr, _, _ = R.transporte_aci(c['p_t'], c['s_cal'], c['h'].s.values,
                                  c['h'].fecha.values, c['y_t'], c['f_t'],
                                  c['fechas_test'], 0.05, c['rng'], ini_test=R.CAL_FIN)
    return c, U_est, U_tr


def main():
    h = L.panel_filas()
    L.log(f'panel de filas: {len(h):,}', LOG)
    preds = cargar_guardadas(h)
    nuevas, meta = reentrenar(h)
    preds.update(nuevas)
    for nm, p in preds.items():
        L.guardar_predictiva(nm, p, meta.get(nm))
    L.log('predictivas guardadas', LOG)

    # ---------------------------------------------------------------- control
    ref_series = {
        'hurdle_800': L.REPO / 'resultados/fase0/series/hurdle.parquet',
        'hurdle_sigma_x': L.REPO / 'resultados/fase0/series/hurdle_sigma_x.parquet',
        'qgbm_54x400': L.REPO / 'resultados/fase0/series/qgbm_multi.parquet',
        'hurdle_2000': L.REPO / 'resultados/verificacion/series/hurdle_2000.parquet',
        'qgbm_54x15': L.REPO / 'resultados/verificacion/series/qgbm_54x15.parquet',
        'qgbm_54x50': L.REPO / 'resultados/verificacion/series/qgbm_54x50.parquet',
        'qgbm_54x100': L.REPO / 'resultados/verificacion/series/qgbm_54x100.parquet',
        'qgbm_54x200': L.REPO / 'resultados/verificacion/series/qgbm_54x200.parquet',
    }
    filas = []
    for nm in L.BRAZOS:
        c, U_est, U_tr = series_canonicas(nm)
        fila = dict(brazo=nm)
        if nm in ref_series:
            ref = pd.read_parquet(ref_series[nm])
            assert np.allclose(ref.y.values, c["y_t"], rtol=0, atol=1e-6)
            for k, U in (('U_est', U_est), ('U_tr', U_tr)):
                a, b = ref[k].values, U
                fin = np.isfinite(a) & np.isfinite(b)
                same_inf = bool(((~np.isfinite(a)) == (~np.isfinite(b))).all())
                rel = np.abs(a[fin] - b[fin]) / np.maximum(1.0, np.abs(a[fin]))
                fila[f'{k}_max_dif_rel'] = float(rel.max())
                fila[f'{k}_mismos_infinitos'] = same_inf
        else:   # hurdle_es: contra el CSV de obj1d
            ref = pd.read_csv(L.REPO / 'resultados/verificacion/obj1d_deteccion_temprana.csv')
            ref = ref[ref.modelo == 'hurdle_es']
            dmax = 0.0
            for per, ini, fin in L.PER_TODOS:
                m = L.mascara(c['f_t'], ini, fin)
                for met, U in (('estatico', U_est), ('transporte_g05', U_tr)):
                    r = R.resumen_metrico('', per, c['f_t'][m], c['y_t'][m], U[m])
                    o = ref[(ref.metodo == met) & (ref.periodo == per)].iloc[0]
                    dmax = max(dmax, abs(r['cobertura'] - o.cobertura),
                               abs(r['ancho_medio'] - o.ancho_medio) / o.ancho_medio * 100,
                               abs(r['pct_infinito'] - o.pct_infinito))
            fila['obj1d_max_desvio'] = dmax
        filas.append(fila)
        L.log(f'control {nm}: {fila}', LOG)
    T = pd.DataFrame(filas)
    T.to_csv(L.RES / 'r2_01_verificacion.csv', index=False)
    print(T.to_string(index=False))


if __name__ == '__main__':
    main()
