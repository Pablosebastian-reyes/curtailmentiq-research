# Bitácora de decisiones metodológicas

Formato: fecha · decisión · alternativas consideradas · justificación · responsable.

---

## 2026-07-03 · Arquitectura de publicación en dos papers
**Decisión:** secuencia data paper (Data in Brief) → flagship (SEGAN: hurdle + conformal + Wasserstein/OT para drift BESS).
**Alternativas:** un solo paper aplicado; paper "causal" de transmisión vs generación.
**Justificación:** el data paper desriesga y funda el DOI citable; el ángulo causal puro contradice la atribución oficial del CEN y carece de estrategia de identificación; la fusión método+drift convierte el quiebre BESS 2025 de amenaza en contribución.
**Responsable:** Pablo + Kerven (pendiente ratificación en sesión de definición).

## 2026-07-03 · Herramientas
**Decisión:** flagship en Overleaf (elsarticle) · data paper en template Word oficial DiB (obligatorio) · datos en Zenodo con DOI reservado · referencias en Zotero grupal · repo GitHub privado.

## PENDIENTES (completar en sesión Pablo-Kerven)
- [ ] Target exacto de predicción (MWh/central/día · prob. de evento · ambos).
- [ ] Definición de splits temporales train/calibración/test (fechas exactas) considerando tren alcista y quiebre BESS.
- [ ] Pieza de Kerven: OT/drift, conformal, o ambas. ¿Toma la línea teórica (cobertura bajo no-intercambiabilidad)?
- [ ] Baselines comprometidos: persistencia, naive estacional, XGBoost punto, GBM cuantílico. ¿LSTM sí/no?
- [ ] Fecha de corte del dataset v1.0.
