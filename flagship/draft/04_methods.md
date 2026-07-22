# 4. Methods

Contenido previsto (ver `../INDICE_PAPER.md`, seccion 4). Subsecciones y su material:

## 4.1 Modelo base hurdle
Ocurrencia (clasificador de P(Y mayor que 0)) mas magnitud lognormal; predictiva de mezcla y su cuantil superior.
- Material: `../conformal_prototype.py` (clase Hurdle, derivacion del cuantil de la mezcla), `../entrenar_baselines.py`, `../AUDIT_METODOLOGICO.md` (punto 1, verificacion del cuantil).

## 4.2 Score de no-conformidad PIT
Score distribucional en [0,1] con randomizacion en el atomo de cero.
- Material: `../conformal_metodos.py` (funcion pit_score), `../AUDIT_METODOLOGICO.md` (punto 2).

## 4.3 Conformal split y correccion de muestra finita
Estadistico de orden, garantia bajo intercambiabilidad, manejo conservador de la cola.
- Material: `../conformal_metodos.py` (q_conformal, q_desde_pool), `../AUDIT_METODOLOGICO.md` (punto 3).

## 4.4 Dependencia y errores estandar clusterizados
Dependencia serial (AR(1), y_lag1) y transversal (estado sistemico compartido por central el mismo dia); errores estandar de cobertura clusterizados por fecha.
- Material: `../conformal_metodos.py` (filas_por_periodo, se_cluster), `../conformal_v3_tabla.csv` (columna se_cluster), `../AUDIT_METODOLOGICO.md` (punto 3).

## 4.5 Adaptacion por recencia: ventana deslizante y pesos
Ventana deslizante de 60 dias con refresco; pesos de recencia (Barber et al. 2023).
- Material: `../conformal_v3_real.py` (metodo 2), `../conformal_v2_cierre.py` (parte A.a, pool deslizante).

## 4.6 Conformal adaptativo online (ACI)
ACI sobre el score PIT; rol de gamma.
- Material: `../conformal_v3_real.py` (funcion correr_aci).

## 4.7 Transporte de scores entre regimenes
Mapa monotono 1D (increasing rearrangement) sobre los scores de calibracion; transporte mas ACI; validez via cota TV o control online; banda de bootstrap.
- Material: `../conformal_metodos.py` (mapa_transporte_banda), `../conformal_v3_real.py` (correr_transporte_aci), `../HANDOFF_KERVEN.md`, `../AUDIT_METODOLOGICO.md` (punto 5).

## 4.8 Weighted conformal por punto (comparador)
Formulacion correcta por punto de test (Tibshirani et al. 2019), sostiene el resultado negativo.
- Material: `../conformal_v2_cierre.py` (parte A.c), `../conformal_v2_cierre_salida.txt`, `../AUDIT_METODOLOGICO.md` (punto 4).

## 4.9 Embargo de horizonte
Embargo de 7 dias en ventanas de calibracion online y en la retroalimentacion de alpha del ACI.
- Material: `../conformal_v3_real.py` (constante EMBARGO_DIAS y su uso), `../conformal_v3_hallazgos.txt` (parte F), `../../DECISIONS.md` (2026-07-20, embargo).

## 4.10 Metricas
Cobertura con error estandar clusterizado, ancho medio (sharpness), CRPS y log-score, diagnostico PIT con distancia KS a la uniforme.
- Material: `../conformal_metodos.py` (crps), `../conformal_v3_salida.txt` (CRPS por periodo), `../entrenar_hurdle_hetero_salida.txt` (KS del PIT, CRPS y log-score).
