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

## 2026-07-04 · Corte v1.0 y backfill horario completo
**Decisión:** dataset v1.0 con corte 2026-05-31 en AMBAS tablas (curtailment_diario y curtailment_horario); serie horaria completa con los 53 reportes mensuales del CEN (enero-2022 a mayo-2026).
**Alternativas:** congelar solo años cerrados 2022-2025; mantener horario parcial (solo diciembres).
**Justificación:** los 53 reportes mensuales existen y fueron verificados en el portal del CEN; el corte idéntico en ambas tablas evita cortes incoherentes (antes: diario a feb-2026, horario a abr-2026). Junio-2026 aún no publicado al momento del corte.
**Responsable:** Pablo.

## 2026-07-04 · Política de versiones de archivos CEN: "última publicada gana"
**Decisión:** cuando el CEN publicó más de una versión de un reporte mensual se usa la última (sufijos v2/_2/Final): Diciembre-2023_v2, Enero-24_v2, Marzo-24_publicar_2, Junio-24_publicar_v2, Agosto/Septiembre/Octubre-24_publicar_v2, Abril-25_Final.
**Alternativas:** primera versión publicada; comparar y elegir por mes.
**Justificación:** la versión más reciente incorpora las correcciones del propio CEN; regla simple y determinística.
**Responsable:** Pablo.

## 2026-07-04 · data-raw/ como fuente canónica del ETL
**Decisión:** los loaders leen exclusivamente de curtailmentiq-research/data-raw/ (53 archivos, inmutables, SHA-256 + fecha de descarga en CHECKSUMS.sha256).
**Justificación:** trazabilidad y reproducibilidad para el data paper; las copias dispersas (DATOS/, datos 2022-2026/) quedan como respaldo histórico.
**Responsable:** Pablo.

## 2026-07-04 · Días faltantes: recuperación determinística en el ETL (no ediciones manuales)
**Decisión:** los días ausentes del desglose diario por erratas de plantilla del CEN (2022-05-31 todas las tecnologías; 2025-05-31 solo Solar) se recuperan agregando la hoja horaria del reporte mensual del propio mes (PARCHES_DIARIO en parsers.py), con contraste contra la columna "Total" por central del bloque errado. Detalle en ERRATA_LOG.md.
**Alternativas:** dejar los días ausentes y documentarlos; imputar.
**Justificación:** el dato existe en otra hoja oficial del mismo origen (no es imputación); dos vías independientes coinciden al milésimo de MWh; la recuperación es código reproducible, no edición manual.
**Responsable:** Pablo.

## 2026-07-18 · Ética y licencia del depósito: respuesta SAIP del CEN
**Decisión:** con la respuesta SAIP del CEN recibida el 13-jul-2026 (uso académico permitido citando la fuente, sin licencia particular sobre los datos), el depósito en Zenodo se publica bajo licencia CC BY 4.0.
**Alternativas:** CC0; CC BY-NC 4.0; esperar un pronunciamiento formal adicional del CEN.
**Justificación:** el CEN no impone licencia y solo exige cita de la fuente; CC BY 4.0 es la licencia estándar recomendada para datasets académicos, maximiza reutilización y hace obligatoria la atribución, coherente con la condición del CEN. Cierra el punto de ética del data paper.
**Responsable:** Pablo.

## 2026-07-18 · Reformulación del problema del flagship: de cobertura a sharpness
**Decisión:** a la luz del prototipo conformal sobre datos sintéticos (flagship/conformal_prototype.py), el problema central del flagship se reformula: no es pérdida de cobertura bajo el quiebre BESS, sino pérdida de sharpness.
**Evidencia (sintética, no citable):** el conformal split estándar mantiene cobertura post-quiebre (97-99% vs 90% nominal) con intervalos sobreanchos; el weighted conformal no corrige por falta de solapamiento entre regímenes (ESS 1.203 de 9.760 en calibración).
**Justificación:** el quiebre BESS reduce las magnitudes, así que el intervalo calibrado pre-quiebre sobrecubre en vez de subcubrir; la contribución metodológica pasa a ser recuperar intervalos ajustados (sharp) con garantía bajo cambio de régimen, línea que conecta con la pieza OT/drift de Kerven.
**Responsable:** Pablo.

## 2026-07-19 · Diseño metodológico del flagship definido por el audit de Kerven
**Decisión:** el diseño de trabajo del flagship queda definido por el audit metodológico de Kerven (flagship/AUDIT_METODOLOGICO.md): score distribucional/PIT como geometría del score de no-conformidad, ventana deslizante de 60 días como mecanismo de recalibración, y ACI sobre scores transportados (mapa monótono OT) como contribución teórica; el weighted conformal en su versión por-punto correcta (intervalos infinitos en ~46% de los casos) queda como negative result que motiva el paper.
**Alternativas:** mantener el weighted conformal pooled del prototipo (descartado: es un artefacto que oculta el fallo del método); calibración estática recalibrada una vez (descartada: el quiebre BESS es una rampa de 15 meses y ninguna calibración estática la rastrea).
**Justificación:** el audit verificó empíricamente sobre el panel sintético (mismo seed) que la ventana deslizante con score multiplicativo/PIT restaura cobertura y sharpness (91.5% de cobertura, ancho 212), mientras toda alternativa estática deriva con la rampa. Ratificación formal y calendario en la sesión del martes.
**Adicional:** por la dependencia transversal detectada en el audit (las 40 centrales comparten el estado sistémico diario, ~244 bloques efectivos en calibración), los errores estándar de toda cobertura reportada se clusterizan por fecha.
**Responsable:** Kerven (diseño) + Pablo (implementación del prototipo v2); pendiente ratificación martes.

## PENDIENTES (completar en sesión Pablo-Kerven)
- [ ] Target exacto de predicción (MWh/central/día · prob. de evento · ambos).
- [ ] Definición de splits temporales train/calibración/test (fechas exactas) considerando tren alcista y quiebre BESS.
- [ ] Pieza de Kerven: OT/drift, conformal, o ambas. ¿Toma la línea teórica (cobertura bajo no-intercambiabilidad)?
- [ ] Baselines comprometidos: persistencia, naive estacional, XGBoost punto, GBM cuantílico. ¿LSTM sí/no?
- [x] Fecha de corte del dataset v1.0. → **2026-05-31** (decisión 2026-07-04, arriba).
