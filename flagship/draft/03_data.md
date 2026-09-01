# 3. Data

Contenido previsto (ver `../INDICE_PAPER.md`, seccion 3):
- Fuente: dataset v1.0 de vertimiento por central del Sistema Electrico Nacional de Chile (2022 a 2026), corregido por erratas. Referencia al data paper y al deposito Zenodo, sin duplicar la descripcion.
- Panel sintetico: proceso generador calibrado al EDA del release v1.0, banco de pruebas controlado y no citable como evidencia empirica.
- Predicciones reales: salida del modelo base hurdle entrenado solo hasta 2023-12-31, con sigma out-of-fold = 1.70.
- Cortes temporales: calibracion, test_pre, test_transition y los semestres 2025-S1, 2025-S2, 2026-S1.

## Material del repo que alimenta esta seccion

- Descripcion del dataset v1.0 y su deposito: `../../paper-data/borrador_data_paper_DiB_EN_v08.md` (data paper) y la entrada de licencia CC BY 4.0 en `../../DECISIONS.md` (2026-07-18).
- Generacion del panel sintetico: `../conformal_prototype.py` (seccion 1) y `../conformal_v2.py`.
- Predicciones reales del modelo base: `../predicciones/pred_hurdle.csv` y `../predicciones/README.md`; entrenamiento en `../entrenar_baselines.py`.
- Cortes temporales exactos (fechas y tamanos): `../conformal_v3_salida.txt` (cabecera) y `../conformal_v3_real.py` (constantes CAL_INI, CAL_FIN y cm.PERIODOS).
