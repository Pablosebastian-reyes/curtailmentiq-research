# Supplementary material: registry of energy storage systems in the Chilean SEN

Companion to *Probabilistic forecasting of renewable curtailment under regime change*
(manuscript SEGAN-D-26-03850). Compiled 4 August 2026; every source consulted on that date.

This registry is provided so that the hypothesis discussed in Section 6, that the entry of
battery storage contributes to the flattening of the curtailment trend at the turn of 2024 to
2025, can be tested independently. It is **not** part of the released dataset: the dataset
records curtailment, not the assets that absorb it, and no causal claim in the manuscript rests
on this table.

---

## 1. Why commissioning dates cannot be taken from connection records

Chile's system operator (Coordinador Eléctrico Nacional, CEN) publishes two distinct milestones
for every generation or storage installation:

- **PES** (*período de puesta en servicio*), the start of the commissioning and testing period.
- **EO** (*entregada a la operación*), the authorisation to operate commercially.

The lag between them is large and highly variable, so a capacity series built on connection or
testing dates systematically dates the arrival of storage too early:

| System | PES | EO | Lag |
|---|---|---|---|
| BESS Uribe Solar | 2024-01-03 | 2024-10-16 | 9.5 months |
| BESS PFV María Elena | 2025-02-21 | 2025-11-11 | 8.7 months |
| BESS PFV Desierto de Atacama | 2025-05-19 | 2025-12-03 | 6.5 months |
| BESS Tocopilla | 2025-09-09 | 2026-02-05 | 4.9 months |
| BESS Víctor Jara | 2025-10-07 | 2026-03-23 | 5.5 months |
| Arena BESS | 2026-02-09 | 2026-06-17 | 4.3 months |
| Ampliación BESS-ALFALFAL (34.9 MW) | 2023-07-06 | not granted | **> 28 months in testing** |

The last row is the clearest case: the unit entered testing in July 2023 and was still listed as
"En Pruebas" in the operator's November 2025 monthly report. **All dates in Section 2 below are
commercial operation dates.**

---

## 2. Registry

Ordered by commercial operation date. "Certainty" flags what is not confirmed by a primary source.

| # | System | Owner | Region | Municipality | MW | MWh | Commercial operation | Certainty |
|---|---|---|---|---|---|---|---|---|
| 1 | Andes Solar IIB (BESS component) | AES Andes | Antofagasta | Antofagasta | 112.0 | ~560 | 2023-07-12 | MWh derived as 112 MW x 5 h, not a published figure |
| 2 | BESS Coya | ENGIE Chile | Antofagasta | María Elena | 139.0 | 638 | 2024-03-18 | day approximate (CEN authorisation that week) |
| 3 | BESS Ampliación Andes II-B | AES Andes | Antofagasta | Antofagasta | 17.0 | 85 | 2024-05 | high |
| 4 | BESS PFV Salvador | Innergex | Atacama | Diego de Almagro | 50.0 | 250 | 2024-07 | high |
| 5 | BESS PE La Cabaña | Enel | La Araucanía | Angol | 32.0 | 64 | 2024-07 | high |
| 6 | BESS Andes IV | AES Andes | Antofagasta | Antofagasta | 130.0 | 650 | 2024-10 | high |
| 7 | BESS PFV El Manzano | Enel | Metropolitana | Til-Til | 60.0 | 120 | 2024-10 | high |
| 8 | BESS PFV Uribe Solar | X-Elio | Antofagasta | Antofagasta | 2.5 | 4.5 | 2024-10-16 | high |
| 9 | BESS Diego de Almagro Sur | Colbún | Atacama | Diego de Almagro | 8.0 | 32 | 2024-10/11 | **medium**, inferred from removal from the testing table; no source publishes the day |
| 10 | BESS PFV Don Humberto | Enel | Metropolitana | Til-Til | 60.0 | 120 | 2024-11 | high; sources disagree on rating (60 vs 67 MW) |
| 11 | Ampliación BESS PE La Cabaña | Enel | La Araucanía | Angol | 32.0 | 64 | 2024-11-04 | high |
| 12 | BESS S/E Nueva Imperial | n/a | La Araucanía | Nueva Imperial | 5.2 | 26 | 2024, month unknown | **low**, appears only in the annual consolidation |
| 13 | BESS PFV Andes IIA | AES Andes | Antofagasta | Antofagasta | 80.0 | 268.8 | 2024-12 | high |
| 14 | BESS PFV San Andrés | Innergex | Atacama | Copiapó | 35.0 | 175 | 2024-12 | high |
| 15 | BESS PFV Tamaya Solar | ENGIE | Antofagasta | Tocopilla | 68.3 | 341.3 | 2025-02 | high |
| 16 | BESS pilot PE Punta Sierra | Pacific Hydro | Coquimbo | Ovalle | 3.0 | 6 | 2025-04 | **medium**, the two official sources differ by about two months |
| 17 | BESS PFV Capricornio | ENGIE | Antofagasta | Antofagasta | 48.0 | 264.2 | 2025-05 | high |
| 18 | BESS PFV Quillagua I | ContourGlobal | Antofagasta | María Elena | 95.0 | 586 | 2025-07 | high |
| 19 | BESS del Desierto | Atlas | Antofagasta | María Elena | 200.0 | 800 | 2025-09 | high |
| 20 | BESS PFV Quillagua II | ContourGlobal | Antofagasta | María Elena | 105.0 | 651 | 2025-09 | high |
| 21 | BESS Fragata | oEnergy | Valparaíso | Zapallar | 3.0 | 7 | 2025-09 | high |
| 22 | BESS PFV María Elena | WEG Capital | Antofagasta | María Elena | 61.0 | 121 | 2025-11-11 | high |
| 23 | BESS PFV Desierto de Atacama | Pacific Hydro | Atacama | Tierra Amarilla | 110.0 | 220 | 2025-12-03 | date high; one source misplaces the region as Antofagasta |
| 24 | BESS Tocopilla | ENGIE | Antofagasta | Tocopilla | 116.0 | 580 | 2026-02-05 | high |
| 25 | BESS Víctor Jara | ContourGlobal | Tarapacá | Pozo Almonte | 200.0 | 1000 | 2026-03-23 | high |
| 26 | BESS PFV Andes III Stage I | AES Andes | Antofagasta | Antofagasta | 171.0 | 514 | 2026-03 | high |

Systems reaching commercial operation after the end of the dataset (31 May 2026) and therefore
outside the study period: Arena BESS (220 MW, Antofagasta, 2026-06-17), Punta de Talca BESS
(60 MW, Coquimbo, 2026-06-15) and BESS Arica II (30 MW, Arica y Parinacota, 2026-06-25).

---

## 3. Cumulative operating capacity

Commercial operation only. "North" is Antofagasta plus Atacama, the two regions that account for
the large majority of curtailment in the dataset.

| Month | Country MW | Country MWh | North MW | North MWh | Official total, all storage (MW) |
|---|---|---|---|---|---|
| 2023-01 to 2023-06 | 0 | 0 | 0 | 0 | n/a |
| 2023-07 to 2024-02 | 112.0 | 560 | 112.0 | 560 | n/a |
| 2024-03 | 251.0 | 1198 | 251.0 | 1198 | n/a |
| 2024-05 | 268.0 | 1283 | 268.0 | 1283 | 404 |
| 2024-07 to 2024-09 | 350.0 | 1597 | 318.0 | 1533 | 486 |
| **2024-10** | 542.5 | 2372 | **450.5** | **2188** | 679 |
| **2024-11** | 647.7 | 2614 | **458.5** | **2220** | 771 |
| **2024-12** | 762.7 | 3057 | **573.5** | **2663** | 886 |
| 2025-01 | 762.7 | 3057 | 573.5 | 2663 | 886 |
| 2025-02 to 2025-03 | 831.0 | 3399 | 641.8 | 3005 | 954 |
| 2025-04 | 834.0 | 3405 | 641.8 | 3005 | 957 |
| **2025-05 to 2025-06** | 882.0 | 3669 | **689.8** | **3269** | 1005 |
| 2025-07 to 2025-08 | 977.0 | 4255 | 784.8 | 3855 | 1100 |
| 2025-09 to 2025-10 | 1285.0 | 5713 | 1089.8 | 5306 | 1413 |
| 2025-11 | 1346.0 | 5834 | 1150.8 | 5427 | 1474 |
| 2025-12 to 2026-01 | 1456.0 | 6054 | 1260.8 | 5647 | 1584 |
| 2026-02 | 1572.0 | 6634 | 1376.8 | 6227 | 1700 |
| 2026-03 to 2026-05 | 1943.0 | 8148 | 1547.8 | 6741 | n/a |

**Cross-check.** The last column is the aggregate figure published monthly by the Ministry of
Energy, which counts all storage technologies and not only batteries. Its difference against the
registry is constant at 123 to 136 MW over 22 consecutive months, which is what one expects if
the residual is the Cerro Dominador concentrated-solar plant (110 MW of molten-salt storage) plus
minor units. A constant difference is the best available evidence that the registry has no
material omissions within the study period. A second cross-check: the operator's 2024 annual
performance report records 658.7 MW and 2499 MWh of storage entering operation during 2024, while
the registry above sums to 653.7 MW for the same year, a difference of 5 MW attributable to
rounding and to the disputed rating of Don Humberto.

Two facts of direct relevance to Section 6 of the manuscript. First, 318 to 573 MW of battery
storage were already operating in Antofagasta and Atacama throughout October to December 2024,
the quarter with the highest curtailment of the whole record, which is why the manuscript makes
no causal attribution for that window. Second, the operator's report for June 2025, the month of
the largest deseasonalised anomaly, states that no storage system entered operation that month.

---

## 4. Sources

All consulted 4 August 2026.

| Source | Location |
|---|---|
| CEN, monthly SEN reports (40 issues, Apr 2023 to Jul 2026; tables of installations in testing and delivered to operation) | `https://www.coordinador.cl/reportes-y-estadisticas/` |
| CEN, Annual Performance Report of the SEN (Art. 72-15), year 2024, Tables 10 and 11 | `https://www.coordinador.cl/wp-content/uploads/2025/04/CEN-Reporte-Art-72-15-ano-2024.pdf` |
| Ministry of Energy, Reporte de Proyectos (41 monthly issues, 2023-01 to 2026-06) | `https://energia.gob.cl/sites/default/files/documentos/reporte_de_proyectos_-_<month>_<year>.pdf` |
| CNE, Reporte Mensual del Sector Energético, January 2026 | `https://www.cne.cl/wp-content/uploads/2026/01/RMensual_v202601.pdf` |
| CNE, Reporte Ciudadano: Almacenamiento, July-August 2024 | `https://www.cne.cl/wp-content/uploads/2024/08/RCiudadano_v202408.pdf` |
| ENGIE Chile, start of commercial operation of BESS Coya | `https://www.engie.cl/inicia-su-operacion-comercial-el-sistema-de-almacenamiento-mas-grande-de-america-latina/` |
| AES Andes, Andes Solar IIB, 112 MW of batteries in operation from July 2023 | `https://www.aesandes.com/en/press-release/historic-milestone-aes-andes-latin-americas-largest-solar-battery-storage-system-goes` |

**Coverage note.** The operator lists in its delivered-to-operation table only storage entering as
a new installation; storage retrofitted to an already operating plant appears in the Ministry
series but not always in the operator's table. The registry combines both, and the two aggregates
reconcile as described above.

---

## 5. What this registry cannot establish

1. **Actual operation rather than nameplate capacity.** What matters for curtailment is how much
   energy each system actually charged during curtailment hours. The operator holds that
   measurement (hourly injections and withdrawals per unit, Infotécnica portal), which is not
   openly accessible. This is the only source that would turn the argument in Section 6 from
   circumstantial into direct.
2. **Electrical location.** Storage relieves curtailment only if it sits behind the same
   constraint as the curtailed plant. The registry gives region and municipality, not node or
   substation.
3. **Composition of the pre-March-2024 fleet.** The first published aggregate is from May 2024.
   The stable residual of about 136 MW is almost certainly Cerro Dominador plus minor units, but
   the official breakdown was not found and has not been inferred.
4. **Four dates at day resolution** (Diego de Almagro Sur, Nueva Imperial, Don Humberto, El
   Manzano), one two-month disagreement between official sources (Punta Sierra pilot) and one
   region disagreement (Desierto de Atacama). None affects the conclusions, and all are flagged
   in the table.
