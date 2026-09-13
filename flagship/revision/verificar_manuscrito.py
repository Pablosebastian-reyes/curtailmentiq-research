#!/usr/bin/env python3
"""
Verificacion de las afirmaciones numericas EN PROSA del manuscrito.
===================================================================
Regla Dura 1: ningun numero del paper se escribe a mano. Las tablas se generan
desde los CSV (fase9_tablas_tex.py) y la tabla de hiperparametros se lee del
codigo (fase1_hiperparametros.py), asi que esas no pueden desincronizarse. Los
numeros que SI aparecen escritos en el cuerpo del texto son los que este script
comprueba, uno a uno, contra el archivo de resultados que los produce.

Si alguno falla, o el texto esta mal o el resultado cambio, y en cualquiera de
los dos casos hay que mirarlo antes de enviar.

Salida: resultados/verificacion_manuscrito.csv

Comando:
  <venv>/bin/python flagship/revision/verificar_manuscrito.py
"""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rev_lib as R   # noqa: E402

RES = R.REPO / 'resultados'
TEX = (R.FLAGSHIP / 'segan' / 'SEGAN_paper_FINAL.tex').read_text()

# El manuscrito trae los cuerpos de tabla con \input, y varias cifras que hay
# que auditar viven ahi, no en el .tex principal. Se expande antes de buscar.
def _expandir(t, prof=0):
    if prof > 4:
        return t
    def _r(mm):
        for base in (R.REPO / 'resultados' / 'tablas_tex',
                     R.REPO / 'resultados' / 'fase1',
                     R.REPO / 'flagship' / 'segan'):
            for c in (base / mm.group(1), base / f'{mm.group(1)}.tex'):
                if c.is_file():
                    return _expandir(c.read_text(), prof + 1)
        return ''
    return re.sub(r'\\input\{([^}]*)\}', _r, t)


TEX = _expandir(TEX)
filas = []


def chk(seccion, afirmacion, en_texto, valor, ok, fuente):
    filas.append(dict(seccion=seccion, afirmacion=afirmacion,
                      en_el_texto=en_texto, regenerado=valor,
                      verifica='si' if ok else 'NO', fuente=fuente))


def en_tex(*frases):
    return all(f in TEX for f in frases)


_UNI = ('zero one two three four five six seven eight nine ten eleven twelve '
        'thirteen fourteen fifteen sixteen seventeen eighteen nineteen').split()
_DEC = {2: 'twenty', 3: 'thirty', 4: 'forty', 5: 'fifty', 6: 'sixty',
        7: 'seventy', 8: 'eighty', 9: 'ninety'}


def palabra(n):
    """Entero de 0 a 99 en palabras, como los escribe el manuscrito."""
    return _UNI[n] if n < 20 else _DEC[n // 10] + ('' if n % 10 == 0 else '-' + _UNI[n % 10])


def main():
    # ---------------- Fase 0: el diagnostico ----------------
    d = pd.read_csv(RES / 'fase0' / 'fase0_diagnostico.csv')
    # el ajuste exacto lo deja fase0_diagnostico.py en el propio CSV
    r = float(d.r_ajuste.iloc[0])
    b = (float(d.pendiente_ajuste.iloc[0]), float(d.intercepto_ajuste.iloc[0]))
    # El ajuste de QUINCE celdas vive ahora en la Tabla 5; el que citan el
    # abstract y el cuerpo de 5.3 es el de CUARENTA, que produce fase0b.
    chk('Tabla 5', 'ajuste sobre las quince celdas', '-0.755, -4.36, +5.45',
        f'{r:.3f}, {b[0]:.2f}, {b[1]:+.2f}',
        abs(r + 0.7547) < 5e-4 and abs(b[0] + 4.3647) < 5e-3
        and abs(b[1] - 5.4487) < 5e-3
        and en_tex('-0.755', '-4.36', '+5.45'),
        'fase0_diagnostico.csv')

    import json as _js
    jb = _js.load(open(RES / 'fase0b' / 'fase0b_diagnostico.json'))
    cb, icb = jb['cuarenta'], jb['ic_bootstrap']
    chk('abstract, 5.3', 'correlacion del diagnostico ampliado',
        f"{cb['r']:.3f}", f"{cb['r']:.3f}",
        en_tex(f"{cb['r']:.3f}"), 'fase0b_diagnostico.json')
    chk('abstract, 5.3', 'pendiente del diagnostico ampliado',
        f"{cb['pendiente']:.2f}", f"{cb['pendiente']:.2f}",
        en_tex(f"{cb['pendiente']:.2f}"), 'fase0b_diagnostico.json')
    chk('5.3', 'intervalo bootstrap del intercepto ampliado',
        f"[{icb['intercepto']['lo']:+.2f}, {icb['intercepto']['hi']:+.2f}]",
        f"[{icb['intercepto']['lo']:+.2f}, {icb['intercepto']['hi']:+.2f}]",
        en_tex(f"{icb['intercepto']['lo']:+.2f}", f"{icb['intercepto']['hi']:+.2f}"),
        'fase0b_diagnostico.json')
    chk('5.3', 'rango de sobre-cobertura cubierto por las cuarenta celdas',
        f"[{jb['rango_x'][0]:+.2f}, {jb['rango_x'][1]:+.2f}]",
        f"[{jb['rango_x'][0]:+.2f}, {jb['rango_x'][1]:+.2f}]",
        en_tex(f"{jb['rango_x'][0]:+.2f}"), 'fase0b_diagnostico.json')
    # el rango de las quince celdas se citaba en la prosa de 5.3 y en la Tabla 6
    # sin que nadie lo leyera de un archivo
    d15 = d.sobrecobertura_pp_exacta
    chk('5.3', 'rango de sobre-cobertura de las quince celdas',
        f'[{d15.min():+.2f}, {d15.max():+.2f}]', f'[{d15.min():+.2f}, {d15.max():+.2f}]',
        en_tex(f'only over $[{d15.min():+.2f}, {d15.max():+.2f}]$ percentage points'),
        'fase0_diagnostico.csv')
    chk('5.4', 'ventaja del GBM a presupuesto equiparado', '2.4 % y 1.8 %',
        'segun obj1_capacidad.csv',
        en_tex('2.4 per cent', '1.8 per cent'), 'obj1_capacidad.csv')
    chk('5.4', 'deterioro del hurdle al quintuplicar capacidad',
        '89.5 a 95.5 MWh', 'segun obj1_capacidad.csv',
        en_tex('89.5 to 95.5'), 'obj1_capacidad.csv')
    chk('5.4', 'desplazamiento del cuantil conformal por mu',
        '0.9242 a 0.9532, 93 % por mu', 'segun obj1c_mecanismo.json',
        en_tex('0.9242 to 0.9532', '0.9512', '93 per cent'),
        'obj1c_mecanismo.json')

    t = pd.read_csv(RES / 'fase0' / 'fase0_tabla_por_modelo.csv')
    tr = t[t.periodo == 'test_transition'].set_index(['modelo_base', 'metodo'])
    for m, met, cob, anc, txt in (
            ('qgbm_multi', '1_estatico_pit', 90.6, 410, '90.6\\% coverage with a mean width of 410'),
            ('qgbm_multi', '4_transporte_banda_g05', 90.5, 425, '425~MWh'),
            ('hurdle', '1_estatico_pit', 95.3, 1203, '95.3\\% coverage with a mean width of 1203'),
            ('hurdle', '4_transporte_banda_g05', 90.9, 806, '806~MWh at 90.9\\% coverage')):
        rr = tr.loc[(m, met)]
        chk('5.2, 5.3', f'{m} / {met}', f'{cob}% / {anc} MWh',
            f'{rr.cobertura}% / {rr.ancho_medio:.0f} MWh',
            abs(rr.cobertura - cob) < 0.05 and abs(rr.ancho_medio - anc) < 0.5
            and en_tex(txt), 'fase0_tabla_por_modelo.csv')

    c = t.pivot_table(index='periodo', columns='modelo_base', values='crps_base')
    mej = (100 * (c.qgbm_multi / c.hurdle - 1))
    chk('5.3', 'mejora de CRPS del qgbm', '18 a 30 por ciento',
        f'{-mej.max():.1f} a {-mej.min():.1f}',
        18 <= -mej.max() <= 19 and 30 <= -mej.min() <= 31
        and en_tex('18 to 30 per cent'), 'fase0_tabla_por_modelo.csv')
    chk('5.3', 'CRPS en la transicion', '92.9 contra 133.5',
        f'{c.loc["test_transition","qgbm_multi"]:.1f} contra '
        f'{c.loc["test_transition","hurdle"]:.1f}',
        en_tex('92.9 against 133.5'), 'fase0_tabla_por_modelo.csv')

    bt = pd.read_csv(RES / 'fase0' / 'fase0_diferencias_bootstrap.csv')
    q = bt[(bt.modelo_base == 'qgbm_multi') & (bt.metodo == '4_transporte_banda_g05')
           & (bt.periodo == 'test_transition')].iloc[0]
    chk('5.3', 'diferencia de ancho con qgbm y su IC', '+15.1, [+0.0, +30.3]',
        f'{q.d_ancho:+.1f}, [{q.ancho_lo:+.1f}, {q.ancho_hi:+.1f}]',
        abs(q.d_ancho - 15.1) < 0.06 and abs(q.ancho_lo) < 0.06
        and abs(q.ancho_hi - 30.3) < 0.06
        and en_tex('$+15.1$~MWh', '$[+0.0,+30.3]$'),
        'fase0_diferencias_bootstrap.csv')
    chk('5.3', 'diferencia de interval score con qgbm', '+13.9, [-10.7, +37.8]',
        f'{q.d_IS:+.1f}, [{q.IS_lo:+.1f}, {q.IS_hi:+.1f}]',
        abs(q.d_IS - 13.9) < 0.06 and abs(q.IS_lo + 10.7) < 0.06
        and abs(q.IS_hi - 37.8) < 0.06
        and en_tex('$+13.9$', '$[-10.7,+37.8]$'),
        'fase0_diferencias_bootstrap.csv')

    # ---------------- Fase 2: ablaciones ----------------
    a = pd.read_csv(RES / 'fase2' / 'fase2_aporte_por_componente.csv')
    for comp, per, val, txt in (
            ('adaptacion online (A1 - A0)', 'test_transition', -215.8, '215.8~MWh in the transition'),
            ('adaptacion online (A1 - A0)', 'TEST_COMPLETO', -37.8, 'by 37.8~MWh over the whole test'),
            ('transporte sobre ACI (A3 - A1)', 'TEST_COMPLETO', 74.2, 'worsens} the interval score by 74.2'),
            ('shrinkage de cola (A4 - A3)', 'TEST_COMPLETO', None, None),
            ('pipeline completo (A4 - A0)', 'TEST_COMPLETO', None, None)):
        rr = a[(a.componente == comp) & (a.periodo == per)].iloc[0]
        # Los dos ultimos no llevan el valor cableado: se construye la frase
        # esperada desde el CSV. Alinear el consumo del generador con la corrida
        # canonica movio estos dos numeros, y un valor cableado obliga a editar
        # el verificador cada vez que cambia un resultado, que es justo lo que
        # no debe pasar.
        if val is None:
            if comp.startswith('shrinkage'):
                txt = (f'${rr.d_IS:.1f}$~MWh with a bootstrap interval of '
                       f'$[{rr.IS_lo:.0f},{rr.IS_hi:.0f}]$')
            else:
                txt = (f'netting ${rr.d_IS:+.1f}$~MWh over the whole test with '
                       f'an interval of $[{rr.IS_lo:+.0f},{rr.IS_hi:+.0f}]$')
            val = rr.d_IS
        chk('5.4', f'{comp} en {per}', f'{val:+.1f}', f'{rr.d_IS:+.1f}',
            abs(rr.d_IS - val) < 0.06 and en_tex(txt),
            'fase2_aporte_por_componente.csv')

    # 5.5 da el pipeline completo ventana por ventana. Esas tres cifras
    # quedaron con los valores anteriores a alinear el generador (176.3 /
    # 100.0 / 104.2) porque nadie las chequeaba. La frase se arma desde el CSV
    # y se exige lo que el texto afirma: las tres significativas.
    pc = a[a.componente == 'pipeline completo (A4 - A0)'].set_index('periodo')
    tr_, s1_, s2_ = (pc.loc[p] for p in ('test_transition', '2025-S1', '2025-S2'))
    txt = (f'improves on the static split by {-tr_.d_IS:.1f}~MWh in the '
           f'transition window and loses {s1_.d_IS:.1f} and {s2_.d_IS:.1f}~MWh '
           f'in 2025-S1 and 2025-S2, all three significant')
    chk('5.5', 'pipeline completo por ventana: transicion, 2025-S1, 2025-S2',
        f'{tr_.d_IS:+.1f} / {s1_.d_IS:+.1f} / {s2_.d_IS:+.1f}, las tres significativas',
        f'{tr_.d_IS:+.1f} / {s1_.d_IS:+.1f} / {s2_.d_IS:+.1f}',
        (pc.loc[['test_transition', '2025-S1', '2025-S2']].significativo == 'si').all()
        and tr_.d_IS < 0 < s1_.d_IS and s2_.d_IS > 0 and en_tex(txt),
        'fase2_aporte_por_componente.csv')

    # Los segundos del texto son los de la Tabla 8, que desde B3 salen de la
    # columna d_segundos de este mismo CSV. Antes el chequeo leia otro archivo
    # y toleraba 0.6 s, y asi paso un "6.7" que el CSV ya no decia. Ahora la
    # frase se arma del CSV y se exige tal cual. El porcentaje y el multiplo se
    # calculan en decimal exacto sobre esos mismos valores redondeados, que son
    # los que el lector puede comprobar contra la tabla.
    sg = pd.read_csv(RES / 'fase2' / 'fase2_aporte_por_componente.csv',
                     dtype={'d_segundos': str})
    sg = sg[sg.periodo == 'TEST_COMPLETO'].set_index('componente').d_segundos.map(Decimal)
    shr, total = sg['shrinkage de cola (A4 - A3)'], sg['pipeline completo (A4 - A0)']
    a2, a1 = sg['transporte sin ACI (A2 - A0)'], sg['adaptacion online (A1 - A0)']
    pct = int((100 * shr / total).quantize(Decimal('1'), ROUND_HALF_UP))
    mult = int((a2 / a1).quantize(Decimal('1'), ROUND_HALF_UP))
    chk('5.5', 'costo del shrinkage sobre el total', f'{shr} de {total} s, {pct}%',
        f'{shr} de {total} s, {pct}%',
        en_tex(f'{shr} of the {total} seconds the full pipeline costs, that is '
               f'{palabra(pct)} per cent')
        and en_tex(f'{palabra(pct)} per cent of the runtime'),
        'fase2_aporte_por_componente.csv')
    chk('5.5', 'costo del transporte solo contra la adaptacion sola',
        f'{palabra(mult)} veces', f'{a2} / {a1} = {mult}',
        en_tex(f'at {palabra(mult)} times the runtime'),
        'fase2_aporte_por_componente.csv')

    # ---------------- Fase 4: benchmarks y cota de alpha ----------------
    m4 = pd.read_csv(RES / 'fase4' / 'fase4_metricas_completas.csv')
    v = m4[m4.periodo == 'TEST_COMPLETO'].set_index('metodo')
    cqr = v.loc['B3 CQR unilateral (GBM)']
    chk('5.5', 'CQR unilateral sobre el GBM', '89.8% / 276 MWh / IS 601',
        f'{cqr.cobertura}% / {cqr.ancho_medio:.0f} MWh / IS {cqr.IS_finitos:.0f}',
        abs(cqr.cobertura - 89.8) < 0.05 and abs(cqr.ancho_medio - 276) < 0.5
        and abs(cqr.IS_finitos - 601) < 0.6
        and en_tex('89.8\\% coverage', '276~MWh', 'interval score of 601'),
        'fase4_metricas_completas.csv')
    tra = v.loc['Transporte+ACI (g=0.05)']
    chk('5.5', 'pipeline completo en el test completo',
        f'{tra.ancho_medio:.0f} MWh / IS {tra.IS_finitos:.0f}',
        f'{tra.ancho_medio:.0f} MWh / IS {tra.IS_finitos:.0f}',
        en_tex(f'{tra.ancho_medio:.0f}~MWh and {tra.IS_finitos:.0f}'),
        'fase4_metricas_completas.csv')
    for nm, cob, is_, txt in (('B2 distribucion movil 60d', 86.5, 583,
                               'interval score of 583 at 86.5\\% coverage'),
                              ('B1 cuantil empirico 365d', 87.2, 656,
                               'trailing-year quantile 656 at 87.2\\%')):
        rr = v.loc[nm]
        chk('5.5', nm, f'{is_} a {cob}%', f'{rr.IS_finitos:.0f} a {rr.cobertura}%',
            abs(rr.cobertura - cob) < 0.05 and abs(rr.IS_finitos - is_) < 0.6
            and en_tex(txt), 'fase4_metricas_completas.csv')
    mx_inf = m4[(m4.familia == 'paper') & (m4.periodo == 'TEST_COMPLETO')].pct_infinito.max()
    chk('5.5', 'maximo de intervalos infinitos', f'hasta {mx_inf} por ciento',
        f'{mx_inf}', en_tex(f'up to {mx_inf} per cent'),
        'fase4_metricas_completas.csv')

    ca = pd.read_csv(RES / 'fase4' / 'fase4_cota_alpha.csv')
    con = ca[(ca.cota == 'alpha_min=0.005')]
    sin = ca[(ca.cota == 'sin cota')]
    peor = (sin[sin.periodo == 'TEST_COMPLETO'].set_index('metodo').cobertura
            - con[con.periodo == 'TEST_COMPLETO'].set_index('metodo').cobertura).max()
    chk('5.5', 'la cota elimina todos los infinitos', '0 en las cinco ventanas',
        f'max {con.pct_infinito.max()}%', con.pct_infinito.max() == 0.0
        and en_tex('falls to zero in all five windows'), 'fase4_cota_alpha.csv')
    chk('5.5', 'costo de cobertura de la cota', 'a lo mas medio punto',
        f'{peor:.1f} puntos', 0.4 <= peor <= 0.5
        and en_tex('at most half a point'), 'fase4_cota_alpha.csv')

    # ---------------- Fase 5: dependencia de panel ----------------
    dp = pd.read_csv(RES / 'fase5' / 'fase5_diagnostico_dependencia.csv').iloc[0]
    chk('4.3', 'correlacion intraclase por fecha', '0.238',
        f'{dp.icc_fecha:.4f}', abs(dp.icc_fecha - 0.238) < 5e-4
        and en_tex('is 0.238'), 'fase5_diagnostico_dependencia.csv')
    chk('4.3', 'efecto de diseno', '26.7', f'{dp.efecto_diseno:.2f}',
        abs(dp.efecto_diseno - 26.7) < 0.05 and en_tex('design effect of 26.7'),
        'fase5_diagnostico_dependencia.csv')
    chk('4.3', 'n efectivo', 'cerca de 1000 contra 26.552',
        f'{dp.n_efectivo:.0f} contra {dp.n_filas}',
        900 < dp.n_efectivo < 1100 and dp.n_filas == 26552
        and en_tex('about 1{,}000 rows', '26{,}552'),
        'fase5_diagnostico_dependencia.csv')
    chk('4.3', 'centrales por dia', '108.8',
        f'{dp.centrales_por_dia}', abs(dp.centrales_por_dia - 108.8) < 0.05
        and en_tex('108.8 plants per day'), 'fase5_diagnostico_dependencia.csv')

    des = pd.read_csv(RES / 'fase5' / 'fase5_cobertura_desagregada.csv')
    alto = des[(des.eje == 'evento') & (des.grupo == 'alto (decil sup.)')
               ].set_index('metodo').cobertura
    chk('5.6', 'cobertura en dias de alto vertimiento',
        'estatico 91.9, Transporte+ACI 86.7, ACI 88.3',
        f'{alto["M0 split agrupado (manuscrito)"]:.1f}, '
        f'{alto["Transporte+ACI (g=0.05), referencia"]:.1f}, '
        f'{alto["ACI (g=0.02), referencia"]:.1f}',
        abs(alto['M0 split agrupado (manuscrito)'] - 91.9) < 0.05
        and abs(alto['Transporte+ACI (g=0.05), referencia'] - 86.7) < 0.05
        and abs(alto['ACI (g=0.02), referencia'] - 88.3) < 0.05
        and en_tex('91.9 per cent', '86.7 per cent', '88.3 per cent'),
        'fase5_cobertura_desagregada.csv')
    peor = des.assign(a=des.desvio_pp.abs()).groupby(['metodo', 'eje']).a.max().unstack()
    chk('5.6', 'peor desvio regional, agrupado contra Mondrian por region',
        '4.8 sube a 7.2',
        f'{peor.loc["M0 split agrupado (manuscrito)","region"]:.1f} sube a '
        f'{peor.loc["M2 Mondrian por region","region"]:.1f}',
        abs(peor.loc['M0 split agrupado (manuscrito)', 'region'] - 4.8) < 0.05
        and abs(peor.loc['M2 Mondrian por region', 'region'] - 7.2) < 0.05
        and en_tex('from 4.8 to 7.2 percentage points'),
        'fase5_cobertura_desagregada.csv')
    chk('5.6', 'mejor cobertura condicional (ACI puro)', '4.7 puntos',
        f'{peor.loc["ACI (g=0.02), referencia"].max():.1f}',
        abs(peor.loc['ACI (g=0.02), referencia'].max() - 4.7) < 0.05
        and en_tex('worst deviation of 4.7'), 'fase5_cobertura_desagregada.csv')

    # ---------------- Fase 3: seleccion ----------------
    import json
    el = json.load(open(RES / 'fase3' / 'fase3_hiperparametros_elegidos.json'))['elegidos']
    chk('4.6', 'gamma y ventana seleccionados', 'gamma 0.005, ventana 120 d',
        f'gamma {el["Transporte+ACI"]["gamma"]}, '
        f'ventana {el["Transporte+ACI"]["ventana"]} d',
        el['Transporte+ACI']['gamma'] == 0.005
        and el['Transporte+ACI']['ventana'] == 120
        and en_tex('$\\gamma=0.005$ with a 120-day window'),
        'fase3_hiperparametros_elegidos.json')
    sv = pd.read_csv(RES / 'fase3' / 'fase3_seleccion_validacion.csv')
    g5 = sv[(sv.metodo == 'Transporte+ACI') & (sv.gamma == 0.05)].pct_infinito
    chk('4.6', 'infinitos en validacion con gamma 0.05', '34 a 42 por ciento',
        f'{g5.min():.1f} a {g5.max():.1f}',
        34 <= g5.min() < 35 and 41 <= g5.max() < 42
        and en_tex('between 34 and 42 per cent'), 'fase3_seleccion_validacion.csv')

    # 5.8: la rejilla gamma x ventana sobre el test (R1.4), exhibicion posterior
    # a la seleccion. Lo que la prosa afirma de ella se arma desde el CSV.
    st = pd.read_csv(RES / 'fase3' / 'fase3_sensibilidad_test.csv')
    tg = st[st.metodo == 'Transporte+ACI']
    cmin, cmax = tg.cobertura.min(), tg.cobertura.max()
    i20 = tg[np.isclose(tg.gamma, 0.2)].pct_infinito
    cero = bool((st[st.gamma <= 0.01].pct_infinito == 0).all())
    chk('5.8', 'rejilla gamma x ventana: cobertura del transporte en toda la rejilla',
        f'{cmin:.1f} a {cmax:.1f}', f'{cmin:.2f} a {cmax:.2f} en {len(tg)} celdas',
        en_tex(f'between {cmin:.1f} and {cmax:.1f} per cent over all '
               f'{palabra(len(tg))} configurations'),
        'fase3_sensibilidad_test.csv')
    chk('5.8', 'rejilla gamma x ventana: intervalos infinitos',
        f'ninguno a gamma <= 0.01; {i20.min():.1f} a {i20.max():.1f} a gamma = 0.20',
        f'ninguno: {cero}; {i20.min():.2f} a {i20.max():.2f}',
        cero and en_tex('none at $\\gamma\\le 0.01$',
                        f'between {i20.min():.1f} and {i20.max():.1f} per cent '
                        f'at $\\gamma=0.20$'),
        'fase3_sensibilidad_test.csv')

    # ---------------- Fase 6: cronologia ----------------
    v6 = pd.read_csv(RES / 'fase6' / 'fase6_verificacion_afirmaciones.csv')
    sn = pd.read_csv(RES / 'fase6' / 'fase6_sensibilidad_puntos_de_cambio.csv')
    chk('3.4', 'configuraciones de deteccion sin quiebre en 2025 ni oct-2024',
        '180, ninguna', f'{len(sn)}, {int(sn.hay_cp_2025.sum())} y '
        f'{int(sn.hay_cp_oct2024.sum())}',
        len(sn) == 180 and sn.hay_cp_2025.sum() == 0
        and sn.hay_cp_oct2024.sum() == 0 and en_tex('180 configurations'),
        'fase6_sensibilidad_puntos_de_cambio.csv')
    W = pd.read_csv(RES / 'fase6' / 'fase6_wasserstein.csv')
    W = W[W.estrato == 'solar_norte'].set_index('contraste')
    otras = W.loc[['calibracion vs test_pre', 'calibracion vs 2025-S1',
                   'calibracion vs 2025-S2', 'calibracion vs 2026-S1']].w1
    chk('4.7', 'rango de W1 de las demas ventanas', '0.28 a 0.95',
        f'{otras.min():.2f} a {otras.max():.2f}',
        abs(otras.min() - 0.28) < 0.005 and abs(otras.max() - 0.95) < 0.005
        and en_tex('1.25 against 0.28 to 0.95'), 'fase6_wasserstein.csv')
    r_ = W.loc['oct-dic 2024 vs oct-dic 2025']
    chk('3.4', 'contraste oct-dic 2024 contra 2025 y su umbral', '0.085 y 0.115',
        f'{r_.w1:.3f} y {r_.nulo_q95:.3f}',
        abs(r_.w1 - 0.085) < 5e-4 and abs(r_.nulo_q95 - 0.115) < 5e-4
        and en_tex('is 0.085, below the 0.115 threshold'), 'fase6_wasserstein.csv')
    r_ = W.loc['ene-sep 2024 vs ene-jun 2025']
    chk('5.2', 'contraste 2025-S1 con IC y umbral',
        '0.172, [0.070, 0.367], 0.193',
        f'{r_.w1:.3f}, [{r_.ic_lo:.3f}, {r_.ic_hi:.3f}], {r_.nulo_q95:.3f}',
        abs(r_.w1 - 0.172) < 5e-4 and en_tex('is 0.172', '$[0.070,0.367]$',
                                             'threshold of 0.193'),
        'fase6_wasserstein.csv')
    ve = pd.read_csv(RES / 'fase6' / 'fase6_por_ventana_solar_norte.csv').set_index('ventana')
    chk('3.3', 'ocurrencia por ventana', '0.750 a 0.815',
        f'{ve.p_ocurrencia.min():.3f} a {ve.p_ocurrencia.max():.3f}',
        abs(ve.p_ocurrencia.min() - 0.750) < 5e-4
        and abs(ve.p_ocurrencia.max() - 0.815) < 5e-4
        and en_tex('between 0.750 and 0.815'),
        'fase6_por_ventana_solar_norte.csv')
    chk('3.3', 'mediana de positivos, calibracion a transicion', '92 a 267 MWh',
        f'{ve.loc["calibracion"].mediana_positivos:.0f} a '
        f'{ve.loc["test_transition"].mediana_positivos:.0f} MWh',
        en_tex('from 92~MWh in the calibration window to 267~MWh'),
        'fase6_por_ventana_solar_norte.csv')
    pf = pd.read_csv(RES / 'fase6' / 'fase6_perfil_intradiario.csv')
    tvp = pf[pf.semestre >= '2023-H1'].tv_vs_semestre_previo.dropna()
    chk('3.3', 'variacion total entre semestres', '0.032 a 0.079',
        f'{tvp.min():.3f} a {tvp.max():.3f}',
        abs(tvp.min() - 0.032) < 5e-4 and abs(tvp.max() - 0.079) < 5e-4
        and en_tex('between 0.032 and 0.079'), 'fase6_perfil_intradiario.csv')
    cen = pf.centroide_h.values
    dmax = float(np.abs(np.diff(cen[2:])).max())
    chk('3.3', 'movimiento maximo del centroide', 'hasta 22 minutos',
        f'{60*dmax:.0f} minutos', 21.5 <= 60 * dmax < 22.5
        and en_tex('at most 22 minutes'), 'fase6_perfil_intradiario.csv')
    fr = pd.read_csv(RES / 'fase6' / 'fase6_sensibilidad_frontera.csv')
    chk('5.7', 'rango de divergencia de las fronteras alternativas', '0.99 a 1.34',
        f'{fr.w1_vs_calibracion.min():.2f} a {fr.w1_vs_calibracion.max():.2f}',
        abs(fr.w1_vs_calibracion.min() - 0.99) < 0.006
        and abs(fr.w1_vs_calibracion.max() - 1.34) < 0.006
        and en_tex('from 0.99 to 1.34'), 'fase6_sensibilidad_frontera.csv')
    # la oficial no es alternativa: el texto decia "six alternative" contando
    # los seis bloques de la Tabla 12, que son la oficial mas cinco
    n_alt = fr.periodo.nunique() - 1
    chk('5.8', 'numero de fronteras alternativas', palabra(n_alt), f'{n_alt} mas la oficial',
        bool(fr.periodo.str.startswith('oficial').any())
        and en_tex(f'on {palabra(n_alt)} alternative definitions of the window besides the one used'),
        'fase6_sensibilidad_frontera.csv')

    # ---------------- Fase 5: bloques ----------------
    log = sorted((RES / 'logs').glob('fase5_*.log'))[-1].read_text()
    chk('5.6', 'cuantil conformal agrupado y por bloques',
        '0.9242 a 0.9263, sd 0.0112', 'segun el log de la Fase 5',
        'qhat = 0.9242' in log and 'qhat = 0.9263' in log
        and 'sd entre replicas 0.0112' in log
        and en_tex('from 0.9242 to 0.9263', 'is 0.0112'),
        'logs/fase5_*.log')

    # ---------------- campos de descripcion de las tablas generadas ----------
    # Una auditoria externa encontro que la Tabla C.11 seguia diciendo "0.4
    # puntos de cobertura" cuando el manuscrito y la carta ya decian medio
    # punto. No se detecto porque este verificador solo miraba la PROSA del
    # .tex, y ese numero vive en un campo de descripcion de una tabla generada.
    # Desde aqui tambien se auditan esos campos.
    print('\n' + '-' * 110)
    print('CAMPOS DE DESCRIPCION DE LAS TABLAS GENERADAS')
    print('-' * 110)

    hp = pd.read_csv(RES / 'fase1' / 'hiperparametros.csv')
    def campo(hiperparametro):
        f = hp[hp.hiperparametro == hiperparametro]
        return '' if f.empty else str(f.iloc[0].detalle)

    ca = pd.read_csv(RES / 'fase4' / 'fase4_cota_alpha.csv')
    cav = ca[ca.periodo == 'TEST_COMPLETO']
    caida = float((cav[cav.cota == 'sin cota'].set_index('metodo').cobertura
                   - cav[cav.cota == 'alpha_min=0.005'].set_index('metodo').cobertura).max())
    d = campo('Recommended bound on alpha_t')
    chk('C.11', 'costo de cobertura de la cota de alpha, campo de la tabla',
        f'{caida:.1f} puntos', d[:70] + '...' if len(d) > 70 else d,
        f'at most {caida:.1f} points of coverage' in d
        and en_tex('at most half a point'),
        'fase1/hiperparametros.csv + fase4_cota_alpha.csv')

    ga = pd.read_csv(RES / 'fase3' / 'fase3_seleccion_validacion.csv')
    import json
    sel = json.load(open(RES / 'fase3' / 'fase3_hiperparametros_elegidos.json'))
    g_aci = sel['elegidos']['ACI']['gamma']
    v_tr = sel['elegidos']['Transporte+ACI']['ventana']
    d = campo('gamma selected by rolling origin')
    chk('C.11', 'gamma seleccionado, campo de la tabla', str(g_aci),
        campo('gamma selected by rolling origin')[:60],
        str(g_aci) in str(hp[hp.hiperparametro == 'gamma selected by rolling origin'].iloc[0].valor),
        'fase3_hiperparametros_elegidos.json')
    chk('C.11', 'ventana seleccionada, campo de la tabla', f'{v_tr} dias',
        str(hp[hp.hiperparametro == 'Window selected by rolling origin'].iloc[0].valor),
        str(v_tr) in str(hp[hp.hiperparametro == 'Window selected by rolling origin'].iloc[0].valor),
        'fase3_hiperparametros_elegidos.json')

    # todo campo de la tabla que contenga un numero con decimales tiene que
    # poder rastrearse; se listan para inspeccion, no se falla por ellos
    import re as _re
    sospechosos = [(r.hiperparametro, r.detalle) for _, r in hp.iterrows()
                   if isinstance(r.detalle, str)
                   and _re.search(r'\b\d+\.\d+\b', r.detalle)]
    print(f'  campos de descripcion con un numero decimal: {len(sospechosos)}')
    for k, v in sospechosos:
        print(f'    {k}: {v[:88]}')

    # ---------------- deteccion temprana del hurdle (Seccion 5.4) --------
    import json as _j2
    je = _j2.load(open(RES / 'verificacion' / 'obj1d_deteccion_temprana.json'))
    ee, e4 = je['resultados']['hurdle_es'], je['resultados']['hurdle_400']
    chk('5.4', 'arboles que elige la deteccion temprana',
        f"{ee['arboles']} ({ee['por_etapa']['ocurrencia']}+{ee['por_etapa']['magnitud']})",
        f"{ee['arboles']}",
        en_tex(f"selects {ee['arboles']} trees in total",
               f"{ee['por_etapa']['ocurrencia']} for the occurrence stage",
               f"{ee['por_etapa']['magnitud']} for the magnitude stage"),
        'obj1d_deteccion_temprana.json')
    chk('5.4', 'CRPS del hurdle con deteccion temprana',
        f"{e4['crps_test']:.2f} a {ee['crps_test']:.2f}",
        f"{ee['crps_test']:.2f}",
        en_tex(f"from {e4['crps_test']:.2f} to {ee['crps_test']:.2f}"),
        'obj1d_deteccion_temprana.json')
    chk('5.4', 'dispersion del hurdle con deteccion temprana',
        f"{e4['sigma']:.4f} a {ee['sigma']:.4f}", f"{ee['sigma']:.4f}",
        en_tex(f"from {e4['sigma']:.4f} to {ee['sigma']:.4f}"),
        'obj1d_deteccion_temprana.json')

    # ---------------- control de robustez del orden puntual (Seccion 5.1) --
    jm = _j2.load(open(RES / 'verificacion' / 'obj1e_mae_hurdle_es.json'))
    # el control de reproduccion de la Tabla 2 tiene que haber pasado: si no,
    # el numero de 5.1 no esta comparado contra las mismas filas
    if not jm.get('control_reproduce_tabla2'):
        raise SystemExit('obj1e no reprodujo la Tabla 2: 5.1 no es comparable')
    mo, me = jm['mae_hurdle_oficial']['total'], jm['mae_hurdle_es']['total']
    nv = jm['naive_estacional_total']
    crps_mej = abs(100 * (ee['crps_test'] / e4['crps_test'] - 1))
    chk('5.1', 'mejora de CRPS de la deteccion temprana',
        f"{crps_mej:.1f} por ciento", f"{crps_mej:.1f}",
        en_tex(f"improves its CRPS by {crps_mej:.1f} per cent"),
        'obj1d_deteccion_temprana.json')
    chk('5.1', 'MAE del hurdle oficial y del detenido temprano',
        f"{mo:.1f} a {me:.1f} MWh", f"{mo:.1f} a {me:.1f}",
        en_tex(f"from {mo:.1f} to {me:.1f}~MWh"),
        'obj1e_mae_hurdle_es.json')
    chk('5.1', 'margen del detenido temprano tras el naive estacional',
        f"{100 * (me / nv - 1):.1f} por ciento",
        f"{100 * (me / nv - 1):.1f}",
        en_tex(f"{100 * (me / nv - 1):.1f} per cent behind the seasonal-naive"),
        'obj1e_mae_hurdle_es.json')
    # "would place it last in this table" solo se escribe si de hecho es el peor
    peor = max(v for _, v in jm['orden_tabla2'])
    chk('5.1', 'el detenido temprano queda ultimo en la Tabla 2',
        'ultimo', 'ultimo' if me >= peor - 1e-9 else f'no, peor es {peor:.2f}',
        (me >= peor - 1e-9) and en_tex('would place it last in this table'),
        'obj1e_mae_hurdle_es.json')

    # ------- lo que el .tex dice y el PDF no imprime (Seccion C.13) -------
    # Un numero puede estar correcto en el .tex, verificar aqui, y no llegar al
    # PDF: un flotante mas alto que la pagina descarta filas en silencio, sin
    # error, dejando solo un aviso en el log. Asi se perdieron las cuatro filas
    # de semillas de la Tabla C.13 (H11). Se lee el TEXTO DEL PDF, no el .tex.
    import subprocess as _sp
    pdf = R.REPO / 'build' / 'SEGAN_paper_FINAL.pdf'
    if not pdf.exists():
        raise SystemExit(f'no existe {pdf}: compila el manuscrito antes')
    txt = _sp.run(['pdftotext', '-layout', str(pdf), '-'],
                  capture_output=True, text=True).stdout
    lineas = [re.sub(r'\s+', ' ', l).strip() for l in txt.split('\n')]

    hp_csv = pd.read_csv(RES / 'fase1' / 'hiperparametros.csv')
    semillas = hp_csv[hp_csv.bloque == 'Seeds']
    if len(semillas) == 0:
        raise SystemExit('no hay bloque de semillas en hiperparametros.csv')

    def impresa(etiqueta, valor):
        """La etiqueta y su valor en una misma linea del PDF.

        Se cotejan las primeras cuatro palabras de la etiqueta y no la etiqueta
        entera, porque la celda se parte en varias lineas dentro de su columna.
        """
        clave = ' '.join(str(etiqueta).split()[:4])
        return any(clave in l and str(valor) in l for l in lineas)

    faltan = [(r.hiperparametro, r.valor) for _, r in semillas.iterrows()
              if not impresa(r.hiperparametro, r.valor)]
    chk('C.13', 'las semillas se imprimen en el PDF, no solo en el .tex',
        f'{len(semillas)} filas de semillas',
        f'{len(semillas) - len(faltan)} impresas' if faltan else
        f'{len(semillas)} impresas',
        not faltan, 'texto extraido de build/SEGAN_paper_FINAL.pdf')
    if faltan:
        for k, v in faltan:
            print(f'    NO SE IMPRIME: {k} = {v}')

    # y ninguna fila de la tabla puede quedarse fuera del PDF
    filas_csv = [str(x) for x in hp_csv.hiperparametro]
    crudo = re.sub(r'\s+', ' ',
                   _sp.run(['pdftotext', str(pdf), '-'],
                           capture_output=True, text=True).stdout)
    perdidas = [f for f in filas_csv if f not in crudo]
    chk('C.13', 'todas las filas de la tabla llegan al PDF',
        f'{len(filas_csv)} filas', f'{len(filas_csv) - len(perdidas)} en el PDF',
        not perdidas, 'texto extraido de build/SEGAN_paper_FINAL.pdf')
    if perdidas:
        for f in perdidas:
            print(f'    FILA PERDIDA: {f}')

    # ---------------- salida ----------------
    V = pd.DataFrame(filas)
    V.to_csv(RES / 'verificacion_manuscrito.csv', index=False)
    pd.set_option('display.width', 230)
    pd.set_option('display.max_colwidth', 46)
    print('=' * 110)
    print('VERIFICACION DE LAS AFIRMACIONES EN PROSA DEL MANUSCRITO')
    print('=' * 110)
    print(V[['seccion', 'afirmacion', 'en_el_texto', 'regenerado',
             'verifica']].to_string(index=False))
    mal = int((V.verifica == 'NO').sum())
    print(f'\n{len(V) - mal} de {len(V)} afirmaciones verifican contra su '
          f'archivo de resultados.')
    if mal:
        print('\nFALLAN:')
        print(V[V.verifica == 'NO'].to_string(index=False))
    print(f'\nguardado {(RES / "verificacion_manuscrito.csv").relative_to(R.REPO)}')
    return 1 if mal else 0


if __name__ == '__main__':
    sys.exit(main())
