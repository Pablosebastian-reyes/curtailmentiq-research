# Manual operativo — Papers CurtailmentIQ (Pablo + Kerven)

Versión 1.0 · Julio 2026 · Documento vivo: actualizar al final de cada sprint.

---

## 1. Infraestructura (montar esta semana, ~medio día)

| Pieza | Herramienta | Detalle |
|---|---|---|
| Flagship (manuscrito) | Overleaf | Plantilla `elsarticle` de Elsevier. Proyecto compartido Pablo+Kerven. |
| Data paper (manuscrito) | Template Word oficial de Data in Brief | Descargar de la página "Guide for Authors" de DiB. Es obligatorio: no aceptan otro formato. |
| Código + logs | GitHub repo privado `curtailmentiq-research` | Estructura abajo. |
| Dataset congelado | Zenodo | Reservar DOI antes de publicar (opción "reserve DOI"). Versionado v1.0, v1.1... |
| Referencias | Zotero (grupo compartido) + Better BibTeX | Exporta `refs.bib` para Overleaf. |
| Identidad académica | ORCID (ambos) | 5 minutos. Requisito de facto en Elsevier. |
| Log de experimentos | `experiments.csv` en el repo (o MLflow si crece) | Cada fila: fecha, commit hash, config, split, seed, métricas. |

### Estructura del repo
```
curtailmentiq-research/
├── data-raw/          # Archivos CEN ORIGINALES, inmutables, con erratas. NO tocar.
│   └── CHECKSUMS.sha256   # hash + fecha de descarga de cada archivo
├── etl/               # Scripts de descarga, limpieza, corrección de erratas
├── notebooks/         # Exploración, validación Fraunhofer, figuras
├── experiments/       # Configs + resultados por corrida
├── figures/           # Solo salida de scripts (PDF vectorial), nunca a mano
├── paper-data/        # Template DiB + anexos
├── paper-flagship/    # Copia de respaldo del Overleaf (export semanal)
├── ERRATA_LOG.md      # La joya: tabla formal de las 7 erratas (consolidado v1.0)
├── DECISIONS.md       # Bitácora de decisiones metodológicas con fecha y porqué
├── experiments.csv
└── environment.yml    # Versiones exactas de todo
```

## 2. Qué guardar desde HOY (evidence locker)

1. **Archivos crudos CEN originales con erratas incluidas**, fechados y con SHA-256. Son la evidencia de la contribución del data paper. Si el CEN los corrige después, sin esto no demuestras nada.
2. **ERRATA_LOG.md**: por cada errata → archivo, fecha del archivo, campo, valor errado, regla determinística de detección, valor corregido, evidencia de contraste.
3. **Splits temporales congelados**: fechas exactas de train / calibración / test. La predicción conforme exige set de calibración separado. Documentar la decisión (el tren alcista 2022-2026 y el quiebre BESS hacen que esto sea la crítica #1 esperable de revisores).
4. **Validación Fraunhofer 2022 (error 0,07%)** como notebook reproducible de punta a punta.
5. **Respuesta escrita del CEN** sobre redistribución (ver §5).
6. Seeds, versiones de librerías, y commit hash por cada resultado. Regla: **todo número del paper se regenera con un comando.**

## 3. Roles y Sprint 0 (semanas 1-2)

### Pablo
- [ ] Enviar consulta formal al CEN (machote en §5) — el reloj de 20 días hábiles corre desde ya.
- [ ] Congelar dataset v1.0 + checksums.
- [ ] Cargar generación horaria real + costos marginales del CEN a Neon.
- [ ] Montar repo, Overleaf, Zotero, ORCID.
- [ ] Descargar template oficial DiB y pre-llenar Specifications Table.

### Kerven
- [ ] Lecturas núcleo (verificar cada referencia en la fuente, no confiar en listas generadas por IA):
  - Angelopoulos & Bates, "A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification" (2023).
  - Tibshirani, Barber, Candès, Ramdas, "Conformal Prediction Under Covariate Shift" (NeurIPS 2019).
  - Barber, Candès, Ramdas, Tibshirani, "Conformal Prediction Beyond Exchangeability" (Annals of Statistics, 2023).
  - Gneiting & Raftery, "Strictly Proper Scoring Rules, Prediction, and Estimation" (JASA 2007) — base de CRPS.
  - Peyré & Cuturi, "Computational Optimal Transport" (Foundations and Trends in ML, 2019).
  - Un review de modelos hurdle / zero-inflated para datos semicontinuos.
- [ ] Escribir **documento de notación y especificación** (2-3 páginas LaTeX): variables, target, modelo dos-partes, envoltorio conformal, métrica Wasserstein para drift. Es la piedra fundacional; todo lo demás lo hereda.
- [ ] Decidir si toma la línea teórica (proposición sobre cobertura conformal bajo el quiebre de régimen, vía "beyond exchangeability"). Opcional pero eleva el paper.
- [ ] Informar a Dante Carrasco del proyecto lateral.

## 4. Secuencia de armado

1. **Data paper primero** (sep-oct): llenar template DiB. Reglas duras del formato: abstract 100-500 palabras puramente descriptivo; prohibido interpretar o concluir; evitar "study/results/conclusions"; los datos deben estar depositados en repositorio público citado en el artículo; secciones fijas (Specifications Table, Value of the Data, Data Description, Experimental Design/Materials and Methods, Limitations, Ethics, CRediT).
2. **Experimentos flagship en paralelo** (oct-ene): orden = baselines fuertes → hurdle → conformal → análisis Wasserstein pre/post-BESS → adaptación de dominio. Nunca al revés: los baselines primero definen la vara.
3. **Redacción flagship** (dic-mar): orden de escritura = Métodos → Resultados → Introducción → Discusión → Abstract (el abstract SIEMPRE al final).
4. Preprint arXiv del flagship al enviarlo (verificar política de la revista elegida).

## 5. Machote de consulta al CEN (enviar por canal Atención & Contacto o SAIP)

> Estimados, junto con saludar: en el marco de una investigación académica (Universidad de Santiago de Chile / Universidad del Bío-Bío) sobre vertimiento de energía renovable en el SEN, hemos construido un dataset derivado de los archivos públicos de curtailment disponibles en el portal del Coordinador. Solicitamos confirmar por escrito: (1) que la información publicada en el portal puede ser utilizada y redistribuida con fines de investigación académica, citando al Coordinador Eléctrico Nacional como fuente; y (2) si existe una licencia o términos de uso específicos aplicables a dichos datos. Esta confirmación será citada en la declaración ética de una publicación científica en revista indexada. Agradecemos su respuesta.

Guardar la respuesta como PDF en el repo. Se cita en la sección Ethics del data paper.

## 6. Uso de IA (Claude) — reglas de la casa

- Arquitectura de chats: Estrategia (decisiones) · Data Engineering (ETL) · Modelamiento (métodos, outputs para Kerven) · Escritura (inglés, sección por sección). Cada chat reporta al de estrategia: contexto breve + resultados + pregunta.
- **Ninguna referencia bibliográfica generada por IA entra al paper sin verificarse** en Google Scholar / DOI / Scopus. Sin excepciones.
- Declarar el uso de IA como asistente de redacción en el manuscrito (política Elsevier: permitido para legibilidad y lenguaje, con declaración; prohibido como autor). Una línea estándar en "Declaration of generative AI in scientific writing".
- Todo contenido científico (números, métodos, claims) sale de los experimentos del repo, nunca del modelo de lenguaje.
- Nada de información comercial de Synapta/clientes en los chats del paper.

## 7. Estándar de calidad "magnífico y profesional"

- **Idioma:** inglés en ambos papers. Flujo: borrador → pulido con IA → lectura final humana de ambos autores.
- **Figuras:** generadas 100% por script, formato PDF vectorial, estilo matplotlib unificado definido una vez (mismo tamaño de fuente, misma paleta). Figuras estrella del flagship: (a) mapa de Chile con concentración geográfica del curtailment, (b) perfil horario con el peak 15-16h, (c) reliability diagrams antes/después de conformal, (d) distancia de Wasserstein en el tiempo mostrando el quiebre BESS.
- **Al someter (Elsevier):** Highlights (3-5 bullets, máx ~85 caracteres c/u), cover letter de media página (qué, por qué esta revista, por qué ahora), 3-4 revisores sugeridos (autores citados sin conflicto de interés), declaración CRediT honesta por autor.
- **Autoría:** solo quien contribuye. CRediT define quién hizo qué. Un tercer autor académico entra solo con contribución real (revisión metodológica, framing, revisiones).
- **Revisiones:** se responden punto por punto en documento aparte, tono neutro, cada cambio señalado. Nunca pelear con el revisor; convencer con evidencia.

## 8. Definición de "listo" por hito

- **Dataset v1.0 listo** = congelado + checksums + diccionario de datos + DOI Zenodo reservado + licencia resuelta.
- **Data paper listo para enviar** = template DiB completo + datos accesibles públicamente + ambos autores releyeron en frío + checklist de la revista al 100%.
- **Flagship listo para enviar** = todos los números regenerables por script + baselines completos + figuras finales + notación consistente + abstract escrito al final + cover letter + highlights.
