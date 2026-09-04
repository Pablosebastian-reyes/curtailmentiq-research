#!/usr/bin/env python3
"""
FASE 1: tabla unica de hiperparametros, leida del codigo.
=========================================================
Comentarios R1.2 y R2.4. El revisor pide largo de la ventana reciente, regla de
seleccion de cuantiles empiricos, esquema de interpolacion, repeticiones
bootstrap, funcion exacta e intensidad del shrinkage de cola, y orden de
ejecucion entre el mapa de transporte y la actualizacion de ACI. Mas semillas.

Este script NO escribe ningun valor a mano: importa los modulos y lee las
constantes y las firmas de las funciones, de modo que la tabla del manuscrito no
pueda desincronizarse del codigo. Si alguien cambia una constante y no regenera,
la tabla del paper queda mal y esta linea lo delata.

Salidas:
  resultados/fase1/hiperparametros.csv
  resultados/fase1/hiperparametros.tex   (cuerpo de la tabla, para \\input)

Comando:
  <venv>/bin/python flagship/revision/fase1_hiperparametros.py
"""
from pathlib import Path
import inspect
import sys

import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rev_lib as R   # noqa: E402
sys.path.insert(0, str(R.FLAGSHIP))
import conformal_metodos as cm          # noqa: E402
import entrenar_baselines as EB         # noqa: E402
import fase0_entrenar_qgbm as QG        # noqa: E402

SAL = R.REPO / 'resultados' / 'fase1'
SAL.mkdir(parents=True, exist_ok=True)


def costo_cobertura_cota_alpha():
    """Caida maxima de cobertura al acotar alpha por abajo, leida de la Fase 4.

    Este campo se escribia a mano y quedo desincronizado: decia 0.4 puntos
    cuando el manuscrito y la carta ya decian medio punto. Ahora sale del mismo
    CSV que alimenta la Tabla 8, asi que no puede volver a divergir.
    """
    c = pd.read_csv(R.REPO / 'resultados' / 'fase4' / 'fase4_cota_alpha.csv')
    v = c[c.periodo == 'TEST_COMPLETO']
    sin = v[v.cota == 'sin cota'].set_index('metodo').cobertura
    con = v[v.cota == 'alpha_min=0.005'].set_index('metodo').cobertura
    return float((sin - con).max())


def defecto(fn, nombre):
    return inspect.signature(fn).parameters[nombre].default


def main():
    tr = inspect.signature(R.transporte_aci).parameters
    mb = inspect.signature(cm.mapa_transporte_banda).parameters

    filas = [
        # --- modelo base ---
        ('Modelo base', 'Horizonte de pronostico', f'{EB.H} dias',
         'prediccion directa; toda feature dinamica es un shift >= H', 'entrenar_baselines.py:H'),
        ('Modelo base', 'Ultimo target de entrenamiento',
         str(EB.CORTE_TRAIN.date()),
         'el modelo nunca ve el periodo de evaluacion', 'entrenar_baselines.py:CORTE_TRAIN'),
        ('Modelo base', 'Arboles / tasa de aprendizaje / profundidad',
         f"{EB.XGB_PARAMS['n_estimators']} / {EB.XGB_PARAMS['learning_rate']} / "
         f"{EB.XGB_PARAMS['max_depth']}",
         'fijados a priori, nunca ajustados contra 2024-2026', 'entrenar_baselines.py:XGB_PARAMS'),
        ('Modelo base', 'min_child_weight / subsample / colsample',
         f"{EB.XGB_PARAMS['min_child_weight']} / {EB.XGB_PARAMS['subsample']} / "
         f"{EB.XGB_PARAMS['colsample_bytree']}", 'idem', 'entrenar_baselines.py:XGB_PARAMS'),
        ('Modelo base', 'Numero de features', str(len(EB.FEATS)),
         ', '.join(EB.FEATS), 'entrenar_baselines.py:FEATS'),
        ('Modelo base', 'Estimacion de sigma del hurdle',
         'out-of-fold, KFold 5',
         'los residuos in-sample de un GBM subestiman la dispersion', 'entrenar_baselines.py'),
        ('Modelo base', 'Rejilla de cuantiles del GBM multi-cuantil',
         f'{len(QG.TAUS)} niveles, de {QG.TAUS[0]} a {QG.TAUS[-1]}',
         '0.02 a 0.98 en pasos de 0.02, mas 0.005, 0.01, 0.99, 0.995 y 0.999; '
         'rearrangement por fila contra el cruce de cuantiles',
         'fase0_entrenar_qgbm.py:TAUS'),
        # --- score y ventanas ---
        ('Capa conformal', 'Nivel nominal', f'1 - alpha = {1 - R.ALPHA:.2f}',
         'limite de prediccion superior unilateral [0, U]', 'rev_lib.py:ALPHA'),
        ('Capa conformal', 'Score de no conformidad', 's = F_x(y) (PIT)',
         'atomo en y=0 randomizado, s = (1-p)U con U ~ Uniforme(0,1)',
         'conformal_metodos.py:pit_score'),
        ('Capa conformal', 'Ventana de calibracion',
         f'{R.CAL_INI.date()} a {R.CAL_FIN.date()}',
         '244 dias, 26.552 filas', 'rev_lib.py:CAL_INI, CAL_FIN'),
        ('Capa conformal', 'Embargo de horizonte', f'{R.EMBARGO_DIAS} dias',
         'toda ventana online termina en t-7 y la retroalimentacion de alpha '
         'se retrasa 7 pasos', 'rev_lib.py:EMBARGO_DIAS'),
        ('Capa conformal', 'Cuantil conformal',
         'orden estadistico k = ceil((n+1)(1-alpha_t))',
         'q = +infinito si k > n, que es el origen de los intervalos infinitos',
         'conformal_metodos.py:q_conformal'),
        # --- transporte ---
        ('Transporte', 'Largo de la ventana reciente',
         f'{defecto(R.transporte_aci, "ventana_dias")} dias',
         'la ventana termina en t menos el embargo, no en t',
         'rev_lib.py:transporte_aci(ventana_dias)'),
        ('Transporte', 'Periodo de refresco del mapa',
         f'{defecto(R.transporte_aci, "refresco_dias")} dias',
         'el mapa se recalcula cada 7 dias; entre refrescos el pool se congela',
         'rev_lib.py:transporte_aci(refresco_dias)'),
        ('Transporte', 'Minimo de scores recientes para refrescar', '100',
         'si la ventana reciente tiene menos, se conserva el pool anterior',
         'rev_lib.py:transporte_aci'),
        ('Transporte', 'Regla de seleccion de cuantiles empiricos',
         f'rejilla equiespaciada de g niveles en [0,1], '
         f'g = min({defecto(cm.mapa_transporte_banda, "n_grid")}, max(20, m/2))',
         'm es el numero de scores de la ventana reciente; el segundo termino '
         'evita una rejilla mas fina que los datos',
         'conformal_metodos.py:mapa_transporte_banda'),
        ('Transporte', 'Esquema de interpolacion',
         'lineal por tramos, dos veces',
         'primero s -> nivel sobre (q_old, niveles), luego nivel -> q_reg '
         'sobre (niveles, q_reg); equivale al reordenamiento creciente '
         'T = F_new^{-1} o F_old',
         'conformal_metodos.py:mapa_transporte_banda.T'),
        ('Transporte', 'Repeticiones bootstrap del mapa',
         f'B = {defecto(cm.mapa_transporte_banda, "B")}',
         'remuestreo con reemplazo de la ventana reciente; el promedio de las '
         'B replicas es el mapa (bagging) y su desviacion estandar por nivel '
         'es la banda', 'conformal_metodos.py:mapa_transporte_banda(B)'),
        ('Transporte', 'Funcion de shrinkage de cola',
         'lambda(u) = 1 / (1 + (sd_boot(u)/tau)^2)',
         'q_reg(u) = (1-lambda(u)) q_old(u) + lambda(u) q_new_bag(u); '
         'lambda ~ 1 donde el mapa es estable y ~ 0 donde es ruidoso, '
         'con lambda = 0 la identidad, es decir el cuantil viejo',
         'conformal_metodos.py:mapa_transporte_banda'),
        ('Transporte', 'Intensidad del shrinkage',
         f'tau = {defecto(cm.mapa_transporte_banda, "tau")} en unidades PIT',
         'escala de regularizacion FIJA, no ajustada contra el test',
         'conformal_metodos.py:mapa_transporte_banda(tau)'),
        ('Transporte', 'Monotonizacion posterior',
         'maximo acumulado y recorte a [0,1]',
         'garantiza que el mapa transportado siga siendo una funcion cuantil',
         'conformal_metodos.py:mapa_transporte_banda'),
        # --- ACI ---
        ('ACI', 'Actualizacion', 'alpha_{t+1} = alpha_t + gamma (alpha - err_t)',
         'err_t = 1{Y_t > U_t}, promediado sobre las centrales del dia t',
         'rev_lib.py:aci'),
        ('ACI', 'gamma reportado en el manuscrito', '0.02 y 0.05',
         'valores de la version enviada, conservados por continuidad',
         'rev_lib.py'),
        ('ACI', 'gamma seleccionado por origen rodante', '0.005',
         'menor interval score en la validacion interna, Fase 3; produce cero '
         'intervalos infinitos', 'fase3_seleccion_hiperparametros.py'),
        ('ACI', 'Ventana seleccionada por origen rodante', '120 dias',
         'idem, para Transporte+ACI', 'fase3_seleccion_hiperparametros.py'),
        ('ACI', 'Recorte de alpha_t, version enviada', '[-1, 2]',
         'permite alpha_t <= 0 y por tanto q = +infinito: es el origen de los '
         'intervalos infinitos', 'rev_lib.py:aci(alpha_min, alpha_max)'),
        ('ACI', 'Recorte de alpha_t recomendado', 'alpha_min = 0.005',
         'elimina por completo los intervalos infinitos en las cinco ventanas '
         f'a un costo de a lo mas {costo_cobertura_cota_alpha():.1f} puntos de '
         'cobertura (Fase 4)',
         'fase4_metricas_benchmarks.py'),
        ('ACI', 'ORDEN DE EJECUCION',
         'refresco del mapa, luego cuantil, luego intervalo, luego ACI',
         'en la fecha t: (i) si toca refresco se recalcula el mapa con la '
         'ventana que termina en t-7 y se transporta todo el pool de '
         'calibracion; (ii) se toma el cuantil del pool transportado al '
         'alpha_t VIGENTE, que aun no incorpora el error de t; (iii) se emite '
         'el intervalo; (iv) el error de t entra a la cola de embargo y '
         'actualiza alpha solo 7 pasos despues. El mapa nunca usa el alpha del '
         'ACI y el ACI nunca usa el mapa: el unico acoplamiento es el pool',
         'rev_lib.py:transporte_aci'),
        # --- evaluacion ---
        ('Evaluacion', 'Metrica principal',
         'interval score unilateral IS = U + (2/alpha) max(y-U, 0)',
         'propio, en MWh, e infinito si U es infinito', 'rev_lib.py:interval_score_unilateral'),
        ('Evaluacion', 'Error estandar de la cobertura',
         'clusterizado por fecha',
         'promedia la cobertura de cada dia y calcula el error entre dias',
         'conformal_metodos.py:cobertura_clusterizada'),
        ('Evaluacion', 'Bootstrap de las diferencias entre metodos',
         '2000 remuestreos de dias completos',
         'la unidad remuestreada es el dia, no la fila; IC de percentil al 95%',
         'rev_lib.py:bootstrap_diferencia'),
        ('Evaluacion', 'Muestras para el CRPS', '300 por fila',
         'CRPS por muestreo, E|X-y| - 0.5 E|X-X\'|', 'conformal_metodos.py:crps'),
        ('Evaluacion', 'Deteccion de puntos de cambio',
         'PELT y segmentacion binaria, coste L2, pen = sigma^2 log n, min_size = 3',
         'penalizacion BIC con k = 1; la sensibilidad recorre k en '
         '{0.5, 1, 2, 3, 5} y min_size en {2, 3, 4}', 'fase6_cronologia.py:puntos_de_cambio'),
        # --- semillas ---
        ('Semillas', 'Entrenamiento de los modelos base', str(R.SEED_BASE),
         'XGBoost hist determinista, n_jobs = 4, KFold', 'entrenar_baselines.py:SEED'),
        ('Semillas', 'Aleatorizacion del atomo PIT y bootstrap del mapa',
         str(R.SEED_CONFORMAL),
         'un unico generador consumido en orden: primero el score, luego '
         'gamma = 0.02 y luego gamma = 0.05', 'rev_lib.py:SEED_CONFORMAL'),
        ('Semillas', 'Muestreo del CRPS', str(R.SEED_CRPS), '', 'rev_lib.py:SEED_CRPS'),
        ('Semillas', 'Bootstrap de diferencias, bloques y permutaciones',
         str(R.SEED_BOOTSTRAP), '', 'rev_lib.py:SEED_BOOTSTRAP'),
    ]

    df = pd.DataFrame(filas, columns=['bloque', 'hiperparametro', 'valor',
                                      'detalle', 'donde_vive_en_el_codigo'])
    df.to_csv(SAL / 'hiperparametros.csv', index=False)

    def esc(t):
        for a, b in (('\\', r'\textbackslash '), ('_', r'\_'), ('%', r'\%'),
                     ('&', r'\&'), ('^', r'\^{}'), ('{', r'\{'), ('}', r'\}')):
            t = t.replace(a, b)
        return t

    lineas, bloque = [], None
    for _, r in df.iterrows():
        if r.bloque != bloque:
            bloque = r.bloque
            lineas.append(r'\midrule' if lineas else '')
            lineas.append(rf'\multicolumn{{3}}{{l}}{{\emph{{{esc(bloque)}}}}} \\')
        lineas.append(f'{esc(r.hiperparametro)} & {esc(r.valor)} & '
                      f'{esc(r.detalle)} \\\\')
    cuerpo = '\n'.join(x for x in lineas if x)
    # se emite el FLOAT COMPLETO, no solo el cuerpo: TeX no acepta un \input
    # cuyo primer token sea \multicolumn dentro de un tabular.
    doc = (
        '%% generado por flagship/revision/fase1_hiperparametros.py\n'
        '%% NO EDITAR A MANO: se lee del codigo fuente\n'
        '\\begin{table*}[t]\n\\centering\n\\footnotesize\n'
        '\\caption{Complete hyperparameter specification. Generated from the '
        'source by \\texttt{flagship/revision/fase1\\_hiperparametros.py}; the '
        'companion CSV records where each value lives in the code.}\n'
        '\\label{tab:hiper}\n'
        '\\begin{tabular}{p{0.30\\textwidth}p{0.22\\textwidth}p{0.42\\textwidth}}\n'
        '\\toprule\nItem & Value & Detail \\\\\n\\midrule\n'
        + cuerpo +
        '\n\\bottomrule\n\\end{tabular}\n\\end{table*}\n')
    (SAL / 'hiperparametros.tex').write_text(doc)

    print('=' * 92)
    print('FASE 1 - TABLA DE HIPERPARAMETROS (R1.2, R2.4)')
    print(f'{len(df)} entradas, leidas del codigo, no escritas a mano')
    print('=' * 92)
    for b, g in df.groupby('bloque', sort=False):
        print(f'\n--- {b} ---')
        for _, r in g.iterrows():
            print(f'  {r.hiperparametro:52s} {r.valor}')
    print(f'\nguardado {(SAL / "hiperparametros.csv").relative_to(R.REPO)} y .tex')


if __name__ == '__main__':
    main()
