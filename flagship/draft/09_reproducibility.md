# 9. Reproducibility

Contenido previsto (ver `../INDICE_PAPER.md`, seccion 9):
- Codigo: metodos compartidos, sintetico, real, modelo base y modelo heterocedastico.
- Datos: dataset v1.0 en Zenodo (DOI) y predicciones locales.
- Salidas de referencia: tablas, figura de cobertura rodante, archivos de hallazgos; semillas fijas y versiones de librerias.
- Auditoria metodologica.

## Material del repo que alimenta esta seccion

- Codigo: `../conformal_metodos.py` (metodos compartidos), `../conformal_v2.py` y `../conformal_v2_cierre.py` (sintetico), `../conformal_v3_real.py` (real), `../entrenar_baselines.py` (modelo base y predicciones), `../entrenar_hurdle_hetero.py` (heterocedastico).
- Datos: deposito Zenodo (ver data paper `../../paper-data/`), `../predicciones/` (pred_hurdle.csv oficial y pred_hurdle_hetero.csv comparador), `../predicciones/README.md` (versiones y semillas).
- Salidas de referencia: `../conformal_v3_salida.txt`, `../conformal_v3_tabla.csv`, `../conformal_v3_hallazgos.txt`, `../conformal_v2_cierre_salida.txt`, `../conformal_v2_cierre_tabla.csv`, figuras `../conformal_v3_cobertura_rodante.png` y `../hurdle_hetero_pit.png`.
- Auditoria: `../AUDIT_METODOLOGICO.md`. Bitacora de decisiones: `../../DECISIONS.md`.
