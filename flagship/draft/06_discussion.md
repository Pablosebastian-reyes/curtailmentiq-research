# 6. Discussion

Contenido previsto (ver `../INDICE_PAPER.md`, seccion 6):
- Por que la geometria del score (PIT o multiplicativa) convierte el quiebre en una traslacion de la ley de scores, y por que eso vuelve la adaptacion un problema de drift-tracking de baja dimension y no de reweighting.
- Por que el modelo base real absorbe el quiebre mejor que el sintetico (features de rezago y media movil) y que implica para la generalizacion a shifts en la direccion adversa (subcobertura silenciosa).
- Ubicacion del cuello de botella de sharpness en el shift de ubicacion, no en la especificacion de la varianza del modelo base.

## Material del repo que alimenta esta seccion

- Argumento de la geometria del score y el drift-tracking: `../AUDIT_METODOLOGICO.md` (puntos 2 y 5), `../HANDOFF_KERVEN.md`.
- Absorcion del quiebre por el modelo base real y el riesgo de shift adverso: `../RESULTADOS_REALES.md` (secciones 2 y 3), `../conformal_v3_hallazgos.txt` (parte C).
- El cuello de botella como shift de ubicacion: `../RESULTADOS_REALES.md` (seccion 6) y `../entrenar_hurdle_hetero_salida.txt` (diagnostico condicional train vs OOS).
