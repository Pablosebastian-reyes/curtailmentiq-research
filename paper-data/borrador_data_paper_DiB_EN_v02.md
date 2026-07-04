# DATA PAPER DRAFT v0.2 — numbers verified against Neon (2026-07-03 report)
# Maps 1:1 to the official Data in Brief Word template.
# Purely descriptive: NO conclusions, NO interpretation. Avoid "study/results/conclusions".
# [TODO] = still pending. [HOLD] = do not freeze v1.0 until resolved (see PENDING GATES).

## ⚠ PENDING GATES BEFORE FREEZING DATASET v1.0
# G1. Hourly backfill: decide after CEN file inventory (hourly series currently
#     covers only Dec 2022, Dec 2023, Dec 2024, Dec 2025 and Jan–Apr 2026 = 244 days).
# G2. Resolve CENTRALBONITO-MC1 / CENTRALFEO-MC2 (real CEN codes or load artifacts?).
# G3. Missing day 2022-05-31 in daily table: recover or document.
# G4. Strip placeholder months (2026-03 onward, gwh=0) from resumen_mensual if included.
# Scope decision (final): tables `predicciones` and `centrales_ranking_2024_2025`
# are EXCLUDED from the public deposit (model outputs / derivable).

---

## TITLE

An errata-corrected, plant-level dataset of solar, wind and hydropower
curtailment in Chile's National Electricity System (2022–2026)

## AUTHORS

Pablo Reyes Cerda (a,*) — ORCID: [TODO]
Kerven Cea Morales (b) — ORCID: [TODO]

(a) Universidad de Santiago de Chile, Magíster en Gestión de la Innovación y el
    Emprendimiento Tecnológico, Santiago, Chile / Synapta SpA, Concepción, Chile
(b) Universidad del Bío-Bío, Doctorado en Matemática Aplicada, Concepción, Chile
(*) Corresponding author: [institutional email]

## KEYWORDS (4–8, do not repeat title words)

renewable energy integration; power system operations; open energy data;
energy transition; battery energy storage; grid congestion; Latin America

## ABSTRACT (100–500 words, purely descriptive)

This data article describes an open, plant-level dataset of renewable energy
curtailment in Chile's National Electricity System (Sistema Eléctrico
Nacional, SEN). The dataset consolidates the public curtailment records
published by the Chilean National Electricity Coordinator (Coordinador
Eléctrico Nacional, CEN) into validated relational tables. The daily table
contains 266,381 records covering 1 January 2022 to 28 February 2026 with
continuous coverage (a single missing calendar day is documented). The hourly
table contains 1,413,319 records covering 244 days: December of 2022, 2023,
2024 and 2025, and January to April 2026 [HOLD: update if backfill extends
coverage]. Records span 295 generation plants across four technologies: solar
photovoltaic (72 plants), wind (54), run-of-river hydropower (140) and
reservoir hydropower (29); hydropower curtailment records are present from
June 2024 onward. Each plant is linked to a metadata registry (293 of 295
plants matched to the CEN installation catalogue) including official CEN
identifier, installed capacity (MW), owner, region, province, municipality,
geographic coordinates, commissioning date, connection point and regulatory
classification. Days and hours without curtailment are stored explicitly as
zero-valued records (48.1% of daily and 82.4% of hourly rows). The processing
pipeline detects and corrects six classes of errata identified in the original
CEN files using deterministic, code-verifiable rules; every rule, affected
file and correction is documented in an accompanying errata log, and the
original unmodified source files are preserved with SHA-256 checksums.
Hourly records reconcile against daily totals with a median discrepancy of
0.00% (99.76% of comparable plant-day pairs within 1%; energy-weighted
absolute discrepancy 0.09%), and aggregate 2022 values reproduce the
curtailment figures reported by Fraunhofer Chile with a deviation of 0.07%.
The dataset totals 17,965 GWh of recorded curtailment (1,471 GWh in 2022;
2,667 in 2023; 6,224 in 2024; 6,202 in 2025; 1,402 in January–February 2026).
The data are available at Zenodo [TODO: reserved DOI] in CSV and Parquet
formats, together with a data dictionary, the errata log, the processing
scripts and integrity checksums. The data enable research on renewable energy
integration, curtailment forecasting, uncertainty quantification and
distribution-shift analysis in a national power system that experienced
large-scale battery energy storage deployment during 2025.

## SPECIFICATIONS TABLE

| Field | Value |
|---|---|
| Subject | Energy: Renewable Energy, Sustainability and the Environment |
| Specific subject area | Curtailment of utility-scale solar, wind and hydropower generation in a national power system (Chile's SEN) |
| Type of data | Tables (CSV, Parquet); errata log (CSV); data dictionary (Markdown); processing scripts (Python) |
| Data collection | Raw curtailment files were downloaded from the CEN public information portal (www.coordinador.cl) between [TODO: first download date] and [TODO: last date]. Files were parsed, harmonized and loaded into PostgreSQL; plant identifiers were matched against the CEN installation catalogue to attach technology, capacity, owner and geolocation (match method recorded per plant in field `match_metodo`). Six classes of errata were detected and corrected with deterministic rules (see Methods). Original files are preserved unmodified with SHA-256 checksums. |
| Data source location | Coordinador Eléctrico Nacional (CEN), Chile — public information portal. Country: Chile. System: Sistema Eléctrico Nacional (SEN), spanning 14 administrative regions in the dataset. |
| Data accessibility | Repository name: Zenodo. Data identification number: [TODO: reserved DOI]. Direct URL: [TODO]. Original CEN sources listed in the data dictionary; provenance file recorded per row in field `archivo_origen`. |
| Related research article | None |

## VALUE OF THE DATA

- These data provide plant-level curtailment records at daily and hourly
  resolution for an entire national power system across four technologies;
  open curtailment datasets at this granularity are not otherwise available
  for Latin American grids, and published open datasets in this domain cover
  renewable *generation* rather than curtailment [refs: GODEEEP; SGCC
  competition dataset].
- Researchers can reuse the data to develop and benchmark curtailment
  forecasting models, including probabilistic approaches; the explicit
  zero-valued records (48.1% of daily rows) directly support research on
  zero-inflated and two-part models for semicontinuous energy data.
- The 2022–2026 span covers the large-scale deployment of battery energy
  storage systems in the SEN during 2025, making the data suitable for
  research on distribution shift, regime change and model recalibration in
  power systems.
- The documented errata-detection rules are reusable by any practitioner or
  researcher working with CEN public files, independently of this dataset.
- Asset owners, regulators and system planners can use the data to benchmark
  curtailment exposure by plant, technology, owner and region.
- Row-level provenance (`archivo_origen`) and per-plant match method
  (`match_metodo`) allow independent auditing of every record against the
  original CEN publications.

## DATA DESCRIPTION

The Zenodo deposit contains the following files.

1. `curtailment_daily` (.parquet / .csv) — 266,381 records, one per plant per
   day with recorded curtailment activity coverage from 2022-01-01 to
   2026-02-28. Columns: `fecha` (date), `central_codigo` (CEN plant/unit
   code), `tecnologia` (Solar / Eólica / Hidro Pasada / Hidro Embalse),
   `mwh` (curtailed energy, MWh), `archivo_origen` (source CEN file).
   Key (`fecha`, `central_codigo`) is unique; no NULL values. Days without
   curtailment are stored explicitly with `mwh` = 0 (48.1% of rows).
2. `curtailment_hourly` (.parquet / .csv) — 1,413,319 records, one per plant
   per hour, covering 244 days: December 2022, December 2023, December 2024,
   December 2025 and January–April 2026 [HOLD: update after backfill
   decision]. Columns: as above plus `hora` (hour of day, convention 1–24).
   Key (`fecha`, `hora`, `central_codigo`) is unique; no NULL values. Hours
   without curtailment are stored explicitly with `mwh` = 0 (82.4% of rows).
   293 of the 295 plants appear in this table (see Limitations).
3. `plants` (.csv) — registry of 295 plants: 72 solar photovoltaic, 54 wind,
   140 run-of-river hydro, 29 reservoir hydro.
4. `plants_metadata` (.csv) — 293 plants matched to the CEN installation
   catalogue with 19 fields at 100% coverage except commissioning date
   (97.3%): CEN catalogue id and official name, match method, region (14
   distinct), province, municipality, latitude, longitude, installed capacity
   (MW), commissioning date (1909-07-31 to 2025-08-28), owner, coordinated
   entity, operational status, technology type (fotovoltaico 72, eólico 54,
   hidro de pasada 81, minihidro de pasada 55, hidro de embalse 31), energy
   conversion type, connection point, and conventional/ERNC classification.
5. `errata_log.csv` — one row per detected erratum: source file, file date,
   affected field, erroneous value, detection rule, corrected value,
   cross-check evidence. [TODO: Pablo completes from ERRATA_LOG.md]
6. `data_dictionary.md` — column-by-column description, units, types and
   provenance of every table.
7. `CHECKSUMS.sha256` — SHA-256 of every original CEN file and every published
   file, with download/creation dates.
8. `scripts/` — Python pipeline that regenerates the curated tables from the
   original files.

[Figure 1 (optional, descriptive only): map of plant locations coloured by
technology and sized by cumulative curtailed energy. Figure 2 (optional):
temporal coverage diagram per table.]

## EXPERIMENTAL DESIGN, MATERIALS AND METHODS

**Acquisition.** [TODO: exact CEN portal sections/file families, update
cadence, download dates, automated vs manual.]

**Harmonization.** Plant codes across heterogeneous CEN files were matched to
the CEN installation catalogue to attach metadata; the method used for each
plant is recorded in `match_metodo`. 293 of 295 plant codes were matched
[HOLD: two unmatched codes under verification, see gate G2].

**Errata detection and correction.** Six classes of errata were identified in
the original files. Each class is detected by a deterministic,
code-verifiable rule and corrected only when an independent cross-check
confirms the corrected value. [TODO: one short paragraph per erratum class,
from ERRATA_LOG.md; Kerven reviews the formal statement of each rule.]
Original files are never modified; corrections are applied in the curated
tables only.

**Internal consistency validation.** For a reproducible random sample of 30
dates (fixed seed) among the 183 dates present in both tables, hourly sums
were reconciled against daily totals for 6,205 plant-day pairs (6,188 present
in both tables). Among the 3,363 comparable pairs with non-zero daily totals,
the median absolute percentage discrepancy is 0.00% (mean 0.69%), 99.76% of
pairs fall within 1%, and the energy-weighted absolute discrepancy is 0.09%
of the 625,710 MWh compared; matched aggregate energy is identical across the
two tables. The few outlier pairs are concentrated in mini-hydro sister units
where daily files allocate energy across units differently from hourly files
(absolute magnitudes ≤ 82 MWh; see Limitations). Uniqueness of keys and
absence of NULL values were verified for both fact tables. Annual totals from
the daily table were cross-checked against the CEN monthly summary series,
agreeing within 0.02% overall (largest single-year difference: 3.7 GWh in
2025, i.e. 0.06%).

**External validation.** Aggregate 2022 curtailment computed from the curated
tables reproduces the figures reported by Fraunhofer Chile (2022) with a
deviation of 0.07% [ref; TODO: exact report title and compared quantity].

**Tooling.** Python [TODO: version], pandas, PostgreSQL. Pipeline and
environment specification included in the deposit.

## LIMITATIONS

- Hourly records cover 244 days (December 2022–2025 and January–April 2026),
  not the full daily period [HOLD: update after backfill decision; if
  backfilled, replace with full-coverage statement].
- One calendar day (2022-05-31) is absent from the daily table [HOLD: recover
  or keep documented].
- Hydropower curtailment records are present from June 2024 onward, following
  the coverage of the underlying CEN publications.
- Two plant codes could not be matched to the CEN installation catalogue and
  two plants appear only in the daily table with zero-valued records [HOLD:
  final wording after gate G2].
- In a small number of mini-hydro sister units, daily source files allocate
  energy across units differently from hourly source files; totals agree at
  aggregate level (see internal consistency validation).
- Records reflect the CEN's curtailment estimation methodology; no independent
  metering was performed. The dataset does not attribute a cause to individual
  curtailment events.
- The CEN may republish corrected versions of its files; this dataset is a
  documented snapshot, and checksums identify the exact source versions used.
- The hour field follows the 1–24 convention used by the source files.

## ETHICS STATEMENT

The authors have read and follow the ethical requirements for publication in
Data in Brief and confirm that the current work does not involve human
subjects, animal experiments, or any data collected from social media
platforms. The dataset is derived from public information published by the
Coordinador Eléctrico Nacional under Chile's public-information regime for the
electricity sector (Law No. 20,936, art. 212-2). [Update upon SAIP response:
"Redistribution for research purposes with attribution was confirmed by the
CEN in response to a formal public-information request (ref. No. [TODO],
dated [TODO])."]

## CREDIT AUTHOR STATEMENT

Pablo Reyes Cerda: Conceptualization, Data curation, Software, Validation,
Investigation, Writing – original draft. Kerven Cea Morales: Methodology,
Validation, Formal analysis, Writing – review & editing.

## DECLARATION OF COMPETING INTERESTS

The authors declare the following competing interest: P.R.C. is the founder of
Synapta SpA and of CurtailmentIQ, a commercial forecasting service that uses
data sources related to those described in this article. [Kerven: confirm
none on his side.]

## ACKNOWLEDGEMENTS / FUNDING

This research did not receive any specific grant from funding agencies in the
public, commercial, or not-for-profit sectors. [Update if VIU/Despega awarded.]

## DECLARATION OF GENERATIVE AI IN SCIENTIFIC WRITING

During the preparation of this work the authors used Claude (Anthropic) in
order to improve the readability and language of the manuscript. After using
this tool, the authors reviewed and edited the content as needed and take full
responsibility for the content of the published article.

## REFERENCES (verify every entry against the source before use)

[1] E. O'Shaughnessy, J.R. Cruce, K. Xu, Too much of a good thing? Global
    trends in the curtailment of solar PV, Solar Energy 208 (2020) 1068–1077.
    [VERIFY DOI]
[2] [GODEEEP descriptor] A multi-decadal hourly coincident wind and solar
    power production dataset for the contiguous United States, Scientific
    Data 11 (2024). [VERIFY authors + DOI]
[3] [SGCC descriptor] Solar and wind power data from the Chinese State Grid
    Renewable Energy Generation Forecasting Competition, Scientific Data 9
    (2022). [VERIFY authors + DOI]
[4] Fraunhofer Chile Research, [TODO: exact 2022 report title].
[5] Coordinador Eléctrico Nacional, public information portal,
    www.coordinador.cl (accessed [TODO dates]).
