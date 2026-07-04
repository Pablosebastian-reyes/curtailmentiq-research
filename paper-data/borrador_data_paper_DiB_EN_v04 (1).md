# DATA PAPER DRAFT v0.4 — dataset v1.0 FROZEN (2026-07-04, cut-off 2026-05-31)
# Maps 1:1 to the official Data in Brief Word template.
# Purely descriptive: NO conclusions, NO interpretation.
# Gates G-A and G-B: RESOLVED (metadata 300/300; errata log consolidated = 7).
# REMAINING [TODO]s before submission:
#   1. Zenodo reserved DOI + URL (Pablo, manual upload of release/v1.0 data files)
#   2. SAIP response from CEN (ethics statement) — in progress, ~Aug 2026
#   3. Exact title of the Fraunhofer Chile 2022 report + compared quantity
#   4. ORCID iDs (both) + corresponding email
#   5. Kerven's full review pass (methods wording, competing interests confirmation)
# Scope (final): tables `predicciones` and `centrales_ranking_2024_2025` EXCLUDED.

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
Nacional, SEN), consolidating the public curtailment records published by the
Chilean National Electricity Coordinator (Coordinador Eléctrico Nacional,
CEN) into validated relational tables. The daily table contains 293,678
records and the hourly table 6,906,761 records, both covering the continuous
period from 1 January 2022 to 31 May 2026 (1,612 days, built from all 53
monthly CEN reports) with no missing days. Records span 300 generation plants
across four technologies: solar photovoltaic (75 plants), wind (56),
run-of-river hydropower (140) and reservoir hydropower (29); hydropower
curtailment records are present from June 2024 onward, with hourly
hydropower detail from July 2024. Each plant is linked to a metadata registry
fully matched to the CEN installation catalogue (300 of 300 plants) with 19
fields including official CEN identifier, installed capacity
(MW), owner, region, province, municipality, geographic coordinates,
commissioning date, connection point and regulatory classification; the
matching method is recorded per plant. Days and hours without curtailment
are stored explicitly as zero-valued records (49.8% of daily and 83.6% of
hourly rows). The processing pipeline documents seven
classes of errata identified in the original CEN files using deterministic,
code-verifiable rules — including a structural continuity check that detects
omitted calendar days even when they carry zero energy — and two omitted
days were recovered from the corresponding monthly hourly sheets with
independent cross-checks against the source files' total columns. Every
rule, affected file and treatment is documented in an accompanying errata
log, and the original unmodified source files are preserved with SHA-256
checksums. Annual totals from the daily table match the CEN official summary
exactly (difference 0.000 GWh) in all five years, and aggregate 2022 values
reproduce the curtailment figures reported by Fraunhofer Chile with a
deviation of 0.07%. In a census month-by-month reconciliation of hourly sums
against daily totals, 50 of 53 months agree within 1% (42 exactly); the
three remaining months reflect documented inconsistencies within the CEN's
own publications. The dataset totals 19,030 GWh of recorded curtailment
(1,471 GWh in 2022; 2,667 in 2023; 6,224 in 2024; 6,205 in 2025; 2,463 in
January–May 2026). The data are available at Zenodo [TODO: reserved DOI] in
CSV and Parquet formats, together with a data dictionary, the errata log,
the processing scripts and integrity checksums. The data enable research on
renewable energy integration, curtailment forecasting, uncertainty
quantification and distribution-shift analysis in a national power system
that experienced large-scale battery energy storage deployment during 2025.

## SPECIFICATIONS TABLE

| Field | Value |
|---|---|
| Subject | Energy: Renewable Energy, Sustainability and the Environment |
| Specific subject area | Curtailment of utility-scale solar, wind and hydropower generation in a national power system (Chile's SEN) |
| Type of data | Tables (CSV, Parquet); errata log (CSV); data dictionary (Markdown); processing scripts (Python) |
| Data collection | All 53 monthly curtailment reports covering January 2022 – May 2026 were retrieved from the CEN public information portal (www.coordinador.cl) [TODO: first/last download dates] using a versioned download script; where multiple versions of a monthly report exist, the most recently published version was used. Files were parsed and loaded into PostgreSQL; plant codes were matched against the CEN installation catalogue (method recorded per plant). Errata were detected with deterministic rules, including a structural continuity check per technology; corrections were applied only in the curated tables, each with an independent cross-check. Original files preserved unmodified with SHA-256 checksums. |
| Data source location | Coordinador Eléctrico Nacional (CEN), Chile — public information portal. Country: Chile. System: Sistema Eléctrico Nacional (SEN), spanning 14 administrative regions in the dataset. |
| Data accessibility | Repository name: Zenodo. Data identification number: [TODO: reserved DOI]. Direct URL: [TODO]. Original CEN source files listed in the data dictionary; provenance recorded per row (`archivo_origen`). |
| Related research article | None |

## VALUE OF THE DATA

- These data provide plant-level curtailment records at daily and hourly
  resolution, continuously over 53 months, for an entire national power
  system across four technologies; open curtailment datasets at this
  granularity are not otherwise available for Latin American grids, and
  published open datasets in this domain cover renewable *generation* rather
  than curtailment [refs: GODEEEP; SGCC competition dataset].
- Researchers can reuse the data to develop and benchmark curtailment
  forecasting models, including probabilistic approaches; the explicit
  zero-valued records (49.8% of daily rows, 83.6% of hourly rows) directly
  support research on zero-inflated and two-part models for semicontinuous
  energy data.
- The 2022–2026 span covers the large-scale deployment of battery energy
  storage systems in the SEN during 2025, enabling research on distribution
  shift, regime change and model recalibration in power systems.
- The documented errata-detection rules — including structural checks that
  identify omitted calendar days even when they carry zero energy — are
  reusable by any practitioner or researcher working with CEN public files.
- Asset owners, regulators and system planners can use the data to benchmark
  curtailment exposure by plant, technology, owner and region.
- Row-level provenance (`archivo_origen`) and per-plant match method
  (`match_metodo`) allow independent auditing of every record against the
  original CEN publications.

## DATA DESCRIPTION

The Zenodo deposit contains the following files.

1. `curtailment_daily` (.parquet / .csv) — 293,678 records, one per plant per
   day, 2022-01-01 to 2026-05-31 (1,612 continuous days, no missing days).
   Columns: `fecha` (date), `central_codigo` (CEN plant/unit code),
   `tecnologia` (Solar / Eólica / Hidro Pasada / Hidro Embalse), `mwh`
   (curtailed energy, MWh), `archivo_origen` (source CEN monthly report).
   Key (`fecha`, `central_codigo`) unique; no NULL values. Days without
   curtailment stored explicitly with `mwh` = 0 (49.8% of rows). Includes
   186 rows restored through documented errata recovery (see Methods).
2. `curtailment_hourly` (.parquet, zstd-compressed / .csv) — 6,906,761 records, one per plant
   per hour, 2022-01-01 to 2026-05-31, built from the hourly sheets of all
   53 monthly CEN reports. Columns: as above plus `hora` (hour of day,
   convention 1–24). Key (`fecha`, `hora`, `central_codigo`) unique; no NULL
   values. Hours without curtailment stored explicitly with `mwh` = 0
   (83.6% of rows). Hourly hydropower detail begins July 2024 (see
   Limitations).
3. `plants` (.csv) — registry of 300 plants: 75 solar photovoltaic, 56 wind,
   140 run-of-river hydro, 29 reservoir hydro.
4. `plants_metadata` (.csv) — all 300 plants matched to the CEN
   installation catalogue with 19 fields at 100% coverage except
   commissioning date (97.3%): CEN catalogue id and official name, match
   method (exact / unit-level / contained / fuzzy / manual), region (14
   distinct), province, municipality, latitude, longitude, installed
   capacity (MW), commissioning date, owner, coordinated entity, operational
   status, technology type, energy conversion type, connection point, and
   conventional/ERNC classification.
5. `errata_log.csv` — one row per documented erratum: source file, file
   date, affected sheet/field, detection rule, treatment (corrected /
   recovered / documented as source limitation), cross-check evidence.
   Seven documented erratum classes (see Methods).
6. `data_dictionary.md` — column-by-column description, units, types and
   provenance of every table.
7. `CHECKSUMS.sha256` — SHA-256 of every original CEN file (53 files) and
   every published file, with download/creation dates.
8. `scripts/` — Python pipeline that regenerates the curated tables from the
   original files, including the month-by-month reconciliation script.

[Figure 1 (descriptive): map of plant locations coloured by technology and
sized by cumulative curtailed energy. Figure 2 (descriptive): temporal
coverage diagram per table and technology.]

## EXPERIMENTAL DESIGN, MATERIALS AND METHODS

**Acquisition.** All 53 monthly curtailment reports published by the CEN for
January 2022 – May 2026 were retrieved from the CEN public portal between
14 May 2026 and 4 July 2026 using a versioned download script included in
the deposit. Where the CEN published multiple versions of a monthly report,
the most recently published version was used; the policy and the exact file
list are recorded in the deposit.

**Harmonization.** Plant codes across heterogeneous CEN files were matched
to the CEN installation catalogue; the method for each plant is recorded in
`match_metodo` (exact 129, unit-level 146, contained 10, fuzzy 4, manual
11). Two plant codes absent from the catalogue were matched manually to their operator's registered mini-hydro
units using capacity, technology and connection-point concordance; the
inference is documented in the deposit.

**Errata detection and correction.** Seven classes of errata were
documented in the original CEN files; of these, the first four were corrected
or recovered deterministically in the curated tables, and the last three are
limitations of the source, documented without correction. (1) *Repeated-header
month block (2022 reports)*: annual-accumulated sheets repeat the April header
for the May block, whose 30-day template also omits 31 May 2022; detected by
identical consecutive block headers and by a structural continuity check
(number of day-columns per block vs. calendar days of the month, per
technology). The month label was corrected deterministically (+1 month) and
the omitted day (106.431 MWh across three plants) was recovered from the
hourly sheet of the May 2022 monthly report, cross-checked to the millesimal
against the difference between each plant's total column and the sum of its
day columns. (2) *Omitted day in the December 2025 report*: 31 May 2025
absent from the Solar and reservoir-hydro sheets; recovered from the May 2025
report (3,718.971 MWh across ~70 solar plants; structurally zero for
reservoir hydro — a case detectable only by the structural check, since the
omitted day carries zero energy). (3) *Duplicated zero-valued plant row*
(PFV-DONAANTONIA, December 2024 report): removed by key-based deduplication.
(4) *Inconsistent date labels in hourly sheets*: dates are assigned by block
position and validated by a continuity check requiring all 1,612 calendar
days per technology before any load is committed. (5) *Missing hourly
hydropower sheets in the June 2024 report*: the hourly hydropower series
therefore begins in July 2024. (6) *October 2023 restatement*: three mutually
inconsistent official figures for the same month across CEN publications.
(7) *Systematic deficit of 2024 wind hourly sheets* relative to the restated
annual closing (February–October 2024). Original files are never modified;
corrections apply to the curated tables only, and every class is documented
in the errata log with its detection rule, treatment and cross-check
evidence.

**Internal consistency validation.** (a) Reproducible random sample (fixed
seed) of 30 dates over the 1,612 days common to both tables: median, mean
and maximum discrepancy between hourly sums and daily totals of 0.0000%;
100% of 2,767 comparable plant-day pairs within 1%; matched energy identical
across tables. (b) Census month-by-month reconciliation over all 53 months:
50 months within 1% (42 at exactly 0.0000%); the three remaining months
correspond to errata classes (iii)–(v) above. (c) Grand totals: the daily table
sums 19,030,463 MWh and the hourly table 18,982,206 MWh; the 0.25%
difference is fully attributable to errata classes (5)–(7), i.e. hourly
detail never published by the source. Key uniqueness and absence of NULL
values verified for both fact tables. Loaders include pre-commit continuity
checks per technology that abort the load when a calendar day is missing,
even if it carries zero energy.

**External validation.** Annual totals from the daily table match the CEN
official monthly summary exactly (difference 0.000 GWh) in every year
2022–2026. Aggregate 2022 curtailment reproduces the figures reported by
Fraunhofer Chile (2022) with a deviation of 0.07% [ref; TODO: exact report
title and compared quantity].

**Tooling.** Python 3.12.3 with pandas, openpyxl, psycopg2, pyproj and
pyarrow; PostgreSQL (Neon). The pipeline
(download script, parsers with declared monthly sources and deterministic
patches, loaders with pre-commit continuity checks, and the reconciliation
script) is included in the deposit.

## LIMITATIONS

- Hydropower curtailment records begin in June 2024, and hourly hydropower
  detail begins in July 2024, following the coverage of the underlying CEN
  publications.
- Three months exhibit hourly-vs-daily discrepancies above 1% attributable
  to inconsistencies within the CEN's own publications (October 2023
  restatement; missing June 2024 hydropower hourly sheets; understated 2024
  wind hourly sheets relative to the restated annual closing); these are
  documented in the errata log and no correction is possible from public
  sources.
- In a small number of mini-hydro sister units, daily source files allocate
  energy across units differently from hourly source files; totals agree at
  aggregate level.
- Records reflect the CEN's curtailment estimation methodology; no
  independent metering was performed. The dataset does not attribute a
  cause to individual curtailment events.
- The CEN may republish corrected versions of its files; this dataset is a
  documented snapshot, and checksums identify the exact source versions
  used.
- The hour field follows the 1–24 convention used by the source files.
- June 2026 had not been published by the CEN at the dataset cut-off
  (2026-05-31).

## ETHICS STATEMENT

The authors have read and follow the ethical requirements for publication in
Data in Brief and confirm that the current work does not involve human
subjects, animal experiments, or any data collected from social media
platforms. The dataset is derived from public information published by the
Coordinador Eléctrico Nacional under Chile's public-information regime for
the electricity sector (Law No. 20,936, art. 212-2). [Update upon SAIP
response: "Redistribution for research purposes with attribution was
confirmed by the CEN in response to a formal public-information request
(ref. No. [TODO], dated [TODO])."]

## CREDIT AUTHOR STATEMENT

Pablo Reyes Cerda: Conceptualization, Data curation, Software, Validation,
Investigation, Writing – original draft. Kerven Cea Morales: Methodology,
Validation, Formal analysis, Writing – review & editing.

## DECLARATION OF COMPETING INTERESTS

The authors declare the following competing interest: P.R.C. is the founder
of Synapta SpA and of CurtailmentIQ, a commercial forecasting service that
uses data sources related to those described in this article. [Kerven:
confirm none on his side.]

## ACKNOWLEDGEMENTS / FUNDING

This research did not receive any specific grant from funding agencies in
the public, commercial, or not-for-profit sectors. [Update if VIU/Despega
awarded.]

## DECLARATION OF GENERATIVE AI IN SCIENTIFIC WRITING

During the preparation of this work the authors used Claude (Anthropic) in
order to improve the readability and language of the manuscript. After using
this tool, the authors reviewed and edited the content as needed and take
full responsibility for the content of the published article.

## REFERENCES (verify every entry against the source before use)

[1] E. O'Shaughnessy, J.R. Cruce, K. Xu, Too much of a good thing? Global
    trends in the curtailment of solar PV, Solar Energy 208 (2020)
    1068–1077. [VERIFY DOI]
[2] [GODEEEP descriptor] A multi-decadal hourly coincident wind and solar
    power production dataset for the contiguous United States, Scientific
    Data 11 (2024). [VERIFY authors + DOI]
[3] [SGCC descriptor] Solar and wind power data from the Chinese State Grid
    Renewable Energy Generation Forecasting Competition, Scientific Data 9
    (2022). [VERIFY authors + DOI]
[4] Fraunhofer Chile Research, [TODO: exact 2022 report title].
[5] Coordinador Eléctrico Nacional, public information portal,
    www.coordinador.cl (accessed [TODO dates]).
