# Flagship: prototipo de la capa de incertidumbre

## Advertencia

`conformal_prototype.py` corre sobre DATOS SINTETICOS calibrados a las características del EDA del release v1.0 (proporción de ceros, cola lognormal, persistencia AR(1) 0.85, ciclo semanal, quiebre BESS desde fines de 2024). Sus resultados NO son citables. Es un banco de pruebas de la metodología, no evidencia empírica.

## Hallazgo que documenta

Bajo el quiebre BESS, el conformal split estándar mantiene la cobertura (97-99% frente al 90% nominal) pero pierde sharpness: los intervalos quedan sistemáticamente sobreanchos porque el régimen post-quiebre tiene magnitudes menores que la ventana de calibración. El weighted conformal (Tibshirani et al. 2019) no repara el problema por falta de solapamiento entre regímenes: el tamaño efectivo de muestra (ESS) cae a 1.203 sobre 9.760 observaciones de calibración. El problema del flagship se reformula, por tanto, de cobertura a sharpness bajo cambio de régimen (ver DECISIONS.md, entrada 2026-07-18).

## Reemplazo por datos reales

La sección 1 del script (generación del panel sintético) se reemplazará por predicciones reales del modelo hurdle sobre el dataset v1.0. El resto del pipeline (hurdle, conformal split, weighted conformal, recalibración, métricas de cobertura, ancho y CRPS) corre igual sin cambios.

## Ejecución

Requiere numpy, pandas, scipy y scikit-learn. Verificado con el venv de `../curtailmentiq-model` (numpy 2.4.6, pandas 3.0.3, scipy 1.17.1, scikit-learn 1.9.0):

```bash
../curtailmentiq-model/venv/bin/python conformal_prototype.py
```

La salida de referencia está en `conformal_prototype_salida.txt` (semilla fija, ejecución determinística salvo cambios de versión de librerías).

## Archivos

- `conformal_prototype.py`: prototipo hurdle + conformal sobre panel sintético.
- `conformal_prototype_salida.txt`: salida de la ejecución de referencia (2026-07-18).
- `HANDOFF_KERVEN.md`: documento de traspaso sobre conformal bajo cambio de régimen vía OT.
