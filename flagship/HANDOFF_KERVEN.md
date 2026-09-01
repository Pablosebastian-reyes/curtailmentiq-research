# Documento de traspaso — Kerven Cea

> **Nota de la revision mayor (2026-09-01).** Este es un documento fechado y no se
> reescribe: es el registro de lo que se penso en su momento. La nomenclatura que usa
> (`test_ramp`, "rampa BESS", "quiebre BESS") quedo obsoleta. La ventana se llama hoy
> `test_transition` y se define como la de maxima divergencia respecto de la
> distribucion de calibracion, sin atribucion causal a ninguna tecnologia. Ver
> `REVISION_PLAN.md` (comentario R2.2) y `HALLAZGOS_CRITICOS.md`.


**De:** Pablo Reyes · **Fecha:** 2026-07-05 · **Estado de los datos:** release v1.0 (2022-01 a 2026-05), EDA completo en commit `9256444`

---

## 1. El proyecto en una página

Estamos escribiendo un **paper metodológico sobre pronóstico probabilístico de curtailment eléctrico** en el Sistema Eléctrico Nacional de Chile, con datos horarios por central de enero 2022 a mayo 2026. La revista objetivo es **Sustainable Energy, Grids and Networks (SEGAN, Elsevier)**; el manuscrito ya está montado en Overleaf con la plantilla `elsarticle`.

El estado del arte es este: **predecir curtailment ya existe** (modelos puntuales, algunos probabilísticos). Lo que casi no existe es **predecir con garantías estadísticas de cobertura que sobrevivan a un cambio de régimen del sistema**. Y nuestro dataset contiene exactamente eso: en 2025 la entrada masiva de baterías (BESS) quebró la distribución de magnitudes de curtailment de un año para otro (los números están en la sección 2). Un método de intervalos de predicción calibrado en 2022–2024 y evaluado en 2025–2026, sin corrección, pierde su cobertura nominal precisamente cuando más importa.

Tu contribución es la pieza diferenciadora del paper: **predicción conforme (conformal prediction) con validez bajo ese cambio de régimen**, corrigiendo el drift mediante reponderación fundamentada en transporte óptimo, que es tu especialidad. El resto del paper (datos, pipeline, modelo base, evaluación) lo llevo yo; tú entras donde el paper deja de ser un ejercicio de forecasting y pasa a ser una contribución metodológica.

---

## 2. Los hechos de los datos que importan para tu parte

Resumen del EDA (figuras `flagship-eda/eda1..eda6`, estadísticos completos en `flagship-eda/eda_resumen.txt`). Solo lo que condiciona el modelamiento probabilístico:

### 2.1 Estructura de ceros: la ocurrencia es un proceso aparte

- Fracción de central-días con curtailment cero: **solar 27.1%, eólica 28.3%, hidro pasada 78.4%, embalse 94.6%**.
- En solar/eólica las rachas alternan rápido: mediana de **1 día sin curtailment y 3 días con**. En hidro las rachas de ceros duran cientos de días.
- Consecuencia de diseño (ya decidida): **modelo de dos partes (hurdle)** — ocurrencia y magnitud se modelan por separado, e hidro queda como target secundario o solo-ocurrencia. Tus intervalos operarán sobre la **magnitud condicional a ocurrencia** (o sobre la distribución predictiva completa del hurdle; eso lo discutimos el martes).

### 2.2 Magnitudes positivas: cola pesada

- Forma lognormal con cola pesada en las cuatro tecnologías. Percentiles diarios en MWh (p50 / p90 / p99 / max): **solar 83 / 485 / 1,260 / 3,402; eólica 39 / 263 / 721 / 4,995; hidro pasada 4.9 / 46 / 209 / 744; embalse 113 / 1,005 / 2,020 / 2,627**.
- La razón **p99/p50 es ~15× en solar y ~18× en eólica**: el error en escala natural lo dominan los extremos. Cualquier garantía de cobertura marginal que ignore la cola va a producir intervalos inútiles (o gigantes, o que fallan justo en los eventos grandes). Esto sugiere trabajar con conformal sobre cuantiles (tipo CQR) más que sobre residuos simétricos.

### 2.3 Persistencia temporal

- ACF del agregado sistema: **0.845 (lag 1), 0.800 (lag 7, con ciclo semanal visible), 0.634 (lag 30)**. Centrales top-5: lag-1 entre 0.61 y 0.85.
- Dos implicaciones: (a) el baseline de persistencia será exigente, y (b) los datos **no son i.i.d. ni de cerca** — la dependencia serial ya tensiona el supuesto de exchangeability antes de cualquier quiebre de régimen.

### 2.4 El quiebre BESS 2025: magnitud sí, forma intradía no

Este es el hallazgo que define tu problema. Medimos drift interanual con distancia de Wasserstein (W1) en dos ejes:

- **Forma hora-del-día (perfil intradía normalizado):** el drift es chico y **decreciente** — W1 sistema: **0.44 h en 2024, 0.32 en 2025, 0.24 en 2026**. El quiebre NO se ve aquí. El peak vespertino (h16–17) domina en todas las estaciones y todos los años; el único rastro intradía nuevo aparece recién en 2026 (spike matinal h10 en marzo 2026).
- **Magnitud (distribución de MWh horario, YoY):** el quiebre es inconfundible — el promedio horario **colapsa de 409 MWh en 2024 (con peaks >1,200 a fines de 2024) a 161 en 2025 desde enero, y a 134 en 2026**. Antofagasta y Atacama replican el patrón del sistema.

En otras palabras: el quiebre BESS es un **frenazo en la escala, no un desplazamiento de horas**. Para ti esto significa que el drift que rompe la exchangeability es esencialmente un **shift en la marginal de magnitudes**, con la estructura condicional intradía estable — un escenario mucho más tratable que un drift arbitrario, y donde W1 entre la distribución de calibración y la de test ya es, de hecho, el estadístico natural de drift del paper.

---

## 3. Tu contribución, definida

**El problema:** split conformal estándar garantiza cobertura marginal 1−α bajo exchangeability entre calibración y test. Nuestro escenario la viola dos veces: dependencia serial (§2.3) y, sobre todo, el quiebre de régimen 2025 (§2.4). Calibrar en pre-BESS y predecir en post-BESS sin corrección produce sobre-cobertura sistemática (intervalos calibrados para un mundo con magnitudes 2.5× mayores), que es tan inválido como la sub-cobertura para efectos de un paper metodológico.

**La propuesta:** predicción conforme reponderada, donde los pesos de calibración corrigen la discrepancia entre la distribución del período de calibración y la del período de test. La línea de Tibshirani et al. (2019) hace esto para covariate shift con pesos = likelihood ratio; nuestro caso es más duro (cambia la distribución del target, no solo de las covariables), y ahí entra tu especialidad: **estimar la corrección vía transporte óptimo** — el plan de transporte entre la distribución de magnitudes de calibración y una estimación de la de test induce la reponderación (o el remapeo de los nonconformity scores), y la distancia W1 que ya usamos como diagnóstico se convierte en el objeto que controla la pérdida de cobertura. Tu formación en sistemas dinámicos también es pertinente para la parte online/adaptativa: el drift no es un evento único sino una trayectoria (409 → 161 → 134).

**Dos niveles de ambición — la decisión es tuya según tu tiempo:**

1. **Aplicación sólida (target Q2):** tomar weighted conformal / conformal beyond exchangeability existentes, diseñar los pesos vía OT con criterio, y demostrar empíricamente que recuperan cobertura a través del quiebre 2025 donde el conformal estándar falla. Riguroso, publicable en SEGAN, acotado en tiempo.
2. **Además, un resultado teórico propio (candidato Q1):** un bound de cobertura bajo no-exchangeability en la línea de Barber et al. (2023), pero donde el gap de cobertura queda controlado explícitamente por una **distancia de transporte** entre las distribuciones de calibración y test — es decir, convertir el W1 empírico del EDA en el término que aparece en el teorema. Hasta donde sabemos, la conexión OT ↔ coverage gap con esta estructura (marginal shift con condicional estable) tiene espacio genuino. Más riesgo, más tiempo, más upside.

No necesitas decidir hoy; sí el martes (sección 5).

---

## 4. La interfaz de trabajo

Para que tu doctorado no compita con la logística de este proyecto, la interfaz es deliberadamente mínima:

- **Tu input:** un archivo de predicciones que yo genero desde mi pipeline, con columnas `fecha, central, tecnologia, valor_real_mwh, prediccion_mwh` (cuando definamos el modelo cuantílico, agregaré columnas de cuantiles). **No trabajas sobre datos crudos ni sobre mi pipeline** — todo lo que necesitas para calibrar, reponderar y evaluar cobertura está en ese archivo.
- **Tu entorno:** **Overleaf** para la matemática (el proyecto ya existe, plantilla `elsarticle`; te doy acceso de edición) y **Claude en el navegador** para tu código y exploración (le puedes subir el CSV de predicciones directamente). **No necesitas Claude Code ni clonar mi repositorio en esta fase.**
- **Sincronización:** yo respaldo el Overleaf al repo semanalmente; tus experimentos de código viven donde te acomode y los resultados relevantes los integramos al paper.

---

## 5. Qué necesito de ti y cuándo

**Para la sesión del martes**, llega con tres cosas:

- **(a) Tu enfoque metodológico:** un sketch (informal, verbal está bien) de cómo atacarías el problema de la sección 3 — qué variante de conformal, cómo entrarían los pesos OT, qué asumes del drift.
- **(b) Tu decisión sobre el nivel de profundidad:** nivel 1 (aplicación, Q2) o nivel 1+2 (con resultado teórico, candidato Q1).
- **(c) Tus horas semanales reales**, con el doctorado en curso. Prefiero un número honesto y chico que uno optimista: el plan del paper se dimensiona con eso.

**Primer entregable posterior a la sesión:** un **documento de notación de 2–3 páginas** en Overleaf — objetos, supuestos, definición formal del target de cobertura y del estadístico de drift. Ese documento es el contrato entre tu matemática y mi pipeline, y de él sale la sección de metodología del paper.

---

## 6. Lecturas recomendadas (ya están en el Zotero del proyecto)

1. **Angelopoulos & Bates — *A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification*.** El punto de entrada: split conformal, CQR y el vocabulario estándar del área. Empieza aquí si conformal te queda lejos.
2. **Tibshirani, Barber, Candès & Ramdas (2019) — *Conformal Prediction Under Covariate Shift*.** El mecanismo de reponderación (weighted exchangeability) que vamos a extender; nota que su corrección usa likelihood ratios donde nosotros queremos objetos de transporte.
3. **Barber, Candès, Ramdas & Tibshirani (2023) — *Conformal Prediction Beyond Exchangeability*.** El marco general de bounds de cobertura con pesos fijos bajo no-exchangeability; es la plantilla del resultado teórico del nivel 2 y su término de "cuánta exchangeability se viola" es exactamente lo que queremos reescribir en lenguaje OT.
4. **Gneiting & Raftery (2007) — *Strictly Proper Scoring Rules, Prediction, and Estimation*.** Cómo se evalúa todo esto (CRPS, pinball loss): define la vara con la que el paper compara métodos.
5. **Peyré & Cuturi — *Computational Optimal Transport*.** Tu terreno; te servirá como puente entre la teoría OT que ya dominas y lo computable en la práctica (Sinkhorn, OT 1-D con cuantiles, que es nuestro caso).

Orden sugerido si el tiempo aprieta: 1 → 2 → 3; la 4 y la 5 son de consulta.

---

## 7. Prompt listo para tu Claude del navegador

Copia esto tal cual en claude.ai (idealmente en un Project nuevo, adjuntando el CSV de predicciones cuando lo tengas):

```text
Soy candidato a doctor en matemática aplicada (transporte óptimo y sistemas
dinámicos). Soy co-autor de un paper metodológico sobre pronóstico
probabilístico de curtailment eléctrico en Chile (revista objetivo:
Sustainable Energy, Grids and Networks). Mi contribución: predicción conforme
(conformal prediction) con validez bajo un cambio de régimen documentado,
usando reponderación fundamentada en transporte óptimo.

Contexto de los datos (horarios por central, 2022-01 a 2026-05):
- Modelo de dos partes (hurdle): ~27-28% de central-días en cero para
  solar/eólica; mis intervalos operan sobre la magnitud condicional.
- Magnitudes positivas lognormales de cola pesada: p99/p50 ≈ 15-18x.
- Fuerte dependencia serial: ACF del sistema 0.845 en lag 1, 0.800 en lag 7.
- Cambio de régimen por entrada de baterías (BESS) en 2025: la distribución
  de magnitudes horarias colapsa (promedio 409 MWh en 2024 → 161 en 2025 →
  134 en 2026, medido con distancia Wasserstein-1 interanual), pero el perfil
  intradía normalizado se mantiene estable (W1 en forma hora-del-día: 0.44 h
  en 2024, 0.32 en 2025, 0.24 en 2026). Es decir: shift en la marginal de
  magnitudes con estructura condicional intradía estable.

Trabajaré sobre un archivo de predicciones con columnas: fecha, central,
tecnologia, valor_real_mwh, prediccion_mwh (más adelante, cuantiles).

Quiero que me ayudes a explorar el diseño metodológico ANTES de escribir
código definitivo:
1. Compara las variantes candidatas: split conformal estándar (baseline que
   debe fallar en 2025), CQR, weighted conformal à la Tibshirani et al. 2019,
   y conformal beyond exchangeability à la Barber et al. 2023 con pesos
   decaídos en el tiempo.
2. Discute cómo derivar los pesos desde transporte óptimo: plan de transporte
   1-D entre la distribución de nonconformity scores (o magnitudes) de
   calibración y una estimación rolling de la de test; contrasta con pesos
   por likelihood ratio y con decaimiento exponencial simple.
3. Ayúdame a precisar qué se puede probar: ¿un bound de coverage gap
   controlado por W1 entre calibración y test, bajo el supuesto de marginal
   shift con condicional estable? ¿Qué supuestos mínimos necesito?
4. Propón un experimento sintético pequeño (que puedas correr aquí mismo en
   Python) que simule el quiebre 2025 —caída de escala con forma condicional
   estable, cola pesada, dependencia serial— para comparar la cobertura
   empírica de las variantes antes de tocar los datos reales.

Sé crítico: si una variante es redundante o el resultado teórico propuesto ya
existe en la literatura, dímelo directamente.
```

---

*Cualquier duda antes del martes, me escribes. — Pablo*
