#!/usr/bin/env python3
"""
R2-12. Verifica contra los resultados cada afirmacion CUALITATIVA del texto.

Las cifras del texto vienen de r2_07 y no pueden divergir; lo que si puede
divergir son las palabras: "el peor", "en todos", "nunca", "a toda razon de
costo". Cada chequeo imprime OK o FALLA con los numeros que lo deciden.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_lib as L                      # noqa: E402
import numpy as np                      # noqa: E402
import pandas as pd                     # noqa: E402

RES = L.RES
fallas = []


def chk(nombre, cond, detalle):
    print(f'[{"OK" if cond else "FALLA"}] {nombre}: {detalle}')
    if not cond:
        fallas.append(nombre)


def main():
    M = pd.read_csv(RES / 'r2_02_metricas.csv')
    OP = pd.read_csv(RES / 'r2_04_operacional.csv')
    CO = pd.read_csv(RES / 'r2_04_condicional.csv')
    AB = pd.read_csv(RES / 'r2_08_ablaciones.csv')
    CE = pd.read_csv(RES / 'r2_03_celdas.csv')
    D = json.load(open(RES / 'r2_03_resumen.json'))
    SIM = pd.read_csv(RES / 'r2_05_sim_celdas.csv')
    SE = pd.read_csv(RES / 'r2_06_sensibilidad.csv')
    T = pd.read_csv(RES / 'r2_13_tiempos.csv' if (RES / 'r2_13_tiempos.csv').exists() else RES / 'r2_02_tiempos.csv')
    H1, H3 = 'H1 ex post (cal. P90)', 'H3 ex ante (regime known at origin)'
    base_m = OP[OP.base.isin(L.PRINCIPALES) & OP.metodo.isin(['static', 'aci_sel', 'tr_sel', 'tr_g05', 'cqr'])
                & np.isclose(OP.alpha, 0.10)]
    allr = base_m[base_m.subconjunto == 'all'].set_index(['base', 'metodo'])
    h1 = base_m[base_m.subconjunto == H1].set_index(['base', 'metodo'])
    h3 = base_m[base_m.subconjunto == H3].set_index(['base', 'metodo'])

    # 1. en H1 todo metodo pierde cobertura y solo los que sobre-cubren en promedio llegan a 90
    caen = all(h1.loc[i, 'cobertura'] < allr.loc[i, 'cobertura'] for i in h1.index)
    chk('H1: todo metodo pierde cobertura respecto de su promedio', caen, '')
    sobre = [i for i in h1.index if h1.loc[i, 'cobertura'] >= 90]
    chk('H1: los que llegan a 90% sobre-cubren en promedio (>= 90.5)', all(allr.loc[i, 'cobertura'] >= 90.5 for i in sobre),
        ', '.join(f'{i}: prom {allr.loc[i, "cobertura"]:.1f}' for i in sobre))
    ra = OP[(OP.base == 'hurdle_800') & (OP.metodo == 'static') & (OP.subconjunto == H1) & np.isclose(OP.alpha, .1)].ancho_medio.iloc[0]
    rq = OP[(OP.base == 'qgbm_54x400') & (OP.metodo.isin(['static', 'cqr'])) & (OP.subconjunto == H1) & np.isclose(OP.alpha, .1)].ancho_medio.max()
    chk('H1: limites QGBM "less than half as wide" que estatico ref', rq < ra / 2, f'razon {ra / rq:.2f}')
    chk('H3: metodos sobre QGBM cerca del nominal (+-1.5)',
        all(abs(h3.loc[('qgbm_54x400', m), 'cobertura'] - 90) <= 1.5 for m in ('static', 'cqr')),
        f"static {h3.loc[('qgbm_54x400', 'static'), 'cobertura']:.1f}, cqr {h3.loc[('qgbm_54x400', 'cqr'), 'cobertura']:.1f}")
    # 2. energia no cubierta: T+ACI 0.05 ref es la mayor
    nc = allr.energia_no_cubierta
    chk('Energia no cubierta maxima: T+ACI 0.05 ref', nc.idxmax() == ('hurdle_800', 'tr_g05'),
        f'max {nc.idxmax()} {nc.max():.1f}; ' + ', '.join(f'{i[0]}:{i[1]} {v:.1f}' for i, v in nc.items()))
    # 3. costo: QGBM estatico y CQR mas baratos que T+ACI ref a toda razon
    for a in (0.10, 0.05, 0.01):
        c = OP[(OP.subconjunto == 'all') & np.isclose(OP.alpha, a)].set_index(['base', 'metodo']).IS_finitos
        tr_ref = [c.get(('hurdle_800', m), np.nan) for m in ('tr_sel', 'tr_g05')]
        tr_ref = [x for x in tr_ref if not np.isnan(x)]
        q = [c.get(('qgbm_54x400', m), np.nan) for m in ('static', 'cqr')]
        chk(f'Costo alpha={a}: QGBM (static/CQR) < T+ACI ref', all(x < min(tr_ref) for x in q if not np.isnan(x)),
            f'QGBM {q}, T+ACI ref {tr_ref}')
        bm = c[[i for i in c.index if i[0] == 'model-free']]
        print(f'       benchmarks alpha={a}: ' + ', '.join(f'{i[1][:2]} {v:.0f}' for i, v in bm.items()))
    bcov = OP[(OP.subconjunto == 'all') & (OP.base == 'model-free') & np.isclose(OP.alpha, .1)][['metodo', 'cobertura', 'IS_finitos']]
    print('       benchmarks k=10:', bcov.round(1).to_dict('records'))
    # 4. ablaciones
    ab = AB[AB.periodo == 'TEST_COMPLETO'].set_index(['brazo', 'componente'])
    for b in ('hurdle_800', 'hurdle_es'):
        r = ab.loc[(b, 'Online adaptation (ACI over static)')]
        chk(f'ACI mejora sobre estatico ({b})', r.d_IS < 0 and r.significativo, f'{r.d_IS:+.1f} [{r.lo:+.1f},{r.hi:+.1f}]')
        r2 = ab.loc[(b, 'Transport alone (over static)')]
        chk(f'Transporte solo mejora y es similar a ACI ({b})', r2.d_IS < 0 and abs(r2.d_IS - r.d_IS) < 0.5 * abs(r.d_IS),
            f'transporte {r2.d_IS:+.1f}, ACI {r.d_IS:+.1f}')
    r = ab.loc[('qgbm_54x400', 'Online adaptation (ACI over static)')]
    print(f'       ACI sobre estatico QGBM: {r.d_IS:+.1f} [{r.lo:+.1f},{r.hi:+.1f}]')
    for b in L.PRINCIPALES:
        r = ab.loc[(b, 'Transport added to ACI')]
        chk(f'Transporte sobre ACI empeora ({b})', r.d_IS > 0, f'{r.d_IS:+.1f} [{r.lo:+.1f},{r.hi:+.1f}] sig={r.significativo}')
        s = ab.loc[(b, 'Tail shrinkage added to transport')]
        base_is = M[(M.brazo == b) & (M.metodo == 'tr_g05') & (M.periodo == 'TEST_COMPLETO')].IS_finitos.iloc[0]
        chk(f'Shrinkage < 1% del IS ({b})', abs(s.d_IS) / base_is < 0.01, f'{s.d_IS:+.1f} sobre {base_is:.0f}')
        f = ab.loc[(b, 'Full scheme (over static)')]
        print(f'       esquema completo vs estatico ({b}): {f.d_IS:+.1f} [{f.lo:+.1f},{f.hi:+.1f}] sig={f.significativo}')
    tt = T[T.brazo == 'hurdle_800'].set_index('componente').segundos
    share = (tt['tr_g05'] - tt['ab_tr_sinshrink_g05']) / tt['tr_g05']
    chk('Shrinkage = mayor parte del tiempo (ref)', share > 0.5, f'{100 * share:.0f}% del tiempo de T+ACI')
    # 6. CQR mejor capa sobre ref, cerca del mejor sobre QGBM
    tot = M[(M.periodo == 'TEST_COMPLETO') & np.isclose(M.alpha, .1)]
    capas = ['sw60', 'aci_g05', 'tr_g05', 'aci_sel', 'tr_sel', 'cqr', 'aci_g05_amin005', 'tr_g05_amin005', 'static']
    for b in ('hurdle_800', 'qgbm_54x400'):
        s = tot[(tot.brazo == b) & tot.metodo.isin(capas) & (tot.pct_infinito == 0)].set_index('metodo').IS_finitos.sort_values()
        print(f'       ranking {b}: ' + ', '.join(f'{k} {v:.0f}' for k, v in s.items()))
    s = tot[(tot.brazo == 'hurdle_800') & tot.metodo.isin(capas) & (tot.pct_infinito == 0)].set_index('metodo').IS_finitos
    chk('CQR es la mejor capa sobre ref', s.idxmin() == 'cqr', f'mejor {s.idxmin()} {s.min():.0f}')
    # 7. residuos: "never ... beat the best constant level"
    for conf in ('tr_g05_amin005', 'aci_g05_amin005'):
        c = CE[CE.config == conf]
        print(f'       residuo {conf}: min {c.resid.min():+.2f}, max {c.resid.max():+.2f}, '
              f'negativos {int((c.resid < 0).sum())} de {len(c)}')
    c = CE[CE.config == 'tr_g05_amin005']
    D2 = json.load(open(RES / 'r2_03_resumen.json'))
    rm = [D2[f'{k}|r2_45']['resid_media'] for k in ('tr_sel', 'aci_sel')]
    chk('"on average at most a fraction of a per cent": residuo medio seleccionados en (-1, +1)', all(-1 < x < 1 for x in rm), str(rm))
    # 8. simulacion
    post = SIM[SIM.ventana.isin(['W2 transition', 'W3', 'W4', 'W5'])]
    mod = {x.split(' ')[0]: x for x in SIM.modelo.unique()}
    oc = post.groupby(['modelo', 'escenario']).oc.mean()
    for e in ('S1 level only', 'S2 level + dispersion'):
        chk(f'Sim: M1 cerca del nominal en {e}', abs(oc[(mod['M1'], e)]) < 1.0, f"{oc[(mod['M1'], e)]:+.2f}")
    chk('Sim: M2 absorbido sin shift', abs(oc[(mod['M2'], 'S0 no shift')]) < 1.0, f"{oc[(mod['M2'], 'S0 no shift')]:+.2f}")
    chk('Sim: M4 sobre-cubre en S2', oc[(mod['M4'], 'S2 level + dispersion')] > 2, f"{oc[(mod['M4'], 'S2 level + dispersion')]:+.2f}")
    w2 = SIM[(SIM.ventana == 'W2 transition') & (SIM.modelo == mod['M7'])].groupby('escenario').oc.mean()
    chk('Sim: M7 subcubre durante la rampa (S1, S2)', w2['S1 level only'] < 0 and w2['S2 level + dispersion'] < 0,
        w2.round(2).to_dict())
    # 9. sensibilidad
    e2 = SE[(SE.bloque == 'E2') & (SE.metodo == 'Transport+ACI') & (SE.parametro == 'gamma')]
    e2s = e2[e2.valor.astype(float) <= 0.05]
    chk('Sens: con alpha_min, T+ACI dentro de +-0.5 del nominal para gamma <= 0.05', (abs(e2s.cobertura - 90) <= 0.5).all(),
        e2s[['brazo', 'valor', 'cobertura']].values.tolist())
    e20 = e2[e2.valor.astype(float) == 0.2]
    chk('Sens: gamma 0.20 cae a 88-89%', ((e20.cobertura >= 88) & (e20.cobertura < 89.05)).all(), e20.cobertura.tolist())
    print('\n' + ('TODO OK' if not fallas else f'FALLAS: {fallas}'))


if __name__ == '__main__':
    main()
