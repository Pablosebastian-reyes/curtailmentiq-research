# Flagship: prototipo de la capa de incertidumbre

## Advertencia

`conformal_prototype.py` corre sobre DATOS SINTETICOS calibrados a las características del EDA del release v1.0 (proporción de ceros, cola lognormal, persistencia AR(1) 0.85, ciclo semanal, quiebre BESS desde fines de 2024). Sus resultados NO son citables. Es un banco de pruebas de la metodología, no evidencia empírica.

## Hallazgo que documenta

Bajo el quiebre BESS, el conformal split estándar mantiene la cobertura (97-99% frente al 90% nominal) pero pierde sharpness: los intervalos quedan sistemáticamente sobreanchos porque el régimen post-quiebre tiene magnitudes menores que la ventana de calibración. El weighted conformal (Tibshirani et al. 2019) no repara el problema por falta de solapamiento entre regímenes: el tamaño efectivo de muestra (ESS) cae a 1.203 sobre 9.760 observaciones de calibración. El problema del flagship se reformula, por tanto, de cobertura a sharpness bajo cambio de régimen (ver DECISIONS.md, entrada 2026-07-18).

## Diseño de trabajo (audit Kerven)

El audit metodológico de Kerven (`AUDIT_METODOLOGICO.md`, 2026-07-19) define los cuatro pilares del flagship:

1. **Weighted conformal como negative result.** La versión pooled del prototipo es un artefacto: sustituye el peso del punto de test (mediana 166) por la media de los pesos de calibración (0.228), tres órdenes de magnitud menos. La versión por-punto correcta (Tibshirani et al. 2019) entrega intervalos infinitos [0, ∞) en ~46% de los casos de test post-quiebre: esa es la respuesta honesta del método ante el colapso del ESS, y es el negative result que motiva el paper.
2. **El quiebre BESS es una rampa de 15 meses, no un escalón.** Ninguna calibración estática lo rastrea: la cobertura del intervalo recalibrado con 60 días deriva 94.1% a 98.6% a 99.4% semestre a semestre, en paralelo con la rampa, sin importar la geometría del score.
3. **Resultado positivo: ventana deslizante de 60 días con score de geometría multiplicativa/PIT.** En el sintético restaura cobertura y sharpness a la vez: 91.5% de cobertura con ancho medio 212, contra ~400 a 415 de las alternativas estáticas.
4. **Contribución teórica: transporte del score.** Mapa monótono OT 1D (T = F_new⁻¹∘F_old) aplicado a los scores de calibración viejos, envuelto en conformal adaptativo (ACI) para que la validez venga del control online y el transporte aporte sharpness; alternativa: cota del gap de cobertura en distancia TV (Barber et al. 2023).

Nota: `audit_experiments.py` (los seis experimentos de verificación del audit) llegará desde Kerven y se agregará a esta carpeta.

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
- `conformal_prototype_salida.txt`: salida de la ejecución de referencia (2026-07-19, tras las correcciones del audit).
- `HANDOFF_KERVEN.md`: documento de traspaso sobre conformal bajo cambio de régimen vía OT.
- `AUDIT_METODOLOGICO.md`: audit metodológico de Kerven Cea (2026-07-19); define el diseño de trabajo del flagship.
