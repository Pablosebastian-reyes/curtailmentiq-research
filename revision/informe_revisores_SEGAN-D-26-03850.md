# Informe de los revisores, SEGAN-D-26-03850

Texto literal recibido del sistema editorial de Elsevier. Se conserva sin editar
para poder citarlo en `response_to_reviewers`. No se transcribe de memoria
ninguna parte: todo lo que aparece aqui viene del correo de decision.

---

## Reviewer's Responses to Questions

Note: In order to effectively convey your recommendations for improvement to the author(s), and help editors make well-informed and efficient decisions, we ask you to answer the following specific questions about the manuscript and provide additional suggestions where appropriate.

**1. Are the objectives and the rationale of the study clearly stated?**

Reviewer #1: Yes
Reviewer #2: yes

**2. If applicable, is the application/theory/method/study reported in sufficient detail to allow for its replicability and/or reproducibility?**

Reviewer #1: Yes [X] No [] N/A []
Reviewer #2: Yes [x] No [] N/A []

**3. If applicable, are statistical analyses, controls, sampling mechanism, and statistical reporting (e.g., P-values, CIs, effect sizes) appropriate and well described?**

Reviewer #1: Yes [] No [X] N/A []
Reviewer #2: Yes [x] No [] N/A []

**4. Could the manuscript benefit from additional tables or figures, or from improving or removing (some of the) existing ones?**

Reviewer #1: Yes
Reviewer #2: yes

**5. If applicable, are the interpretation of results and study conclusions supported by the data?**

Reviewer #1: No
Reviewer #2: needs more expansion

**6. Have the authors clearly emphasized the strengths of their study/theory/methods/argument?**

Reviewer #1: Yes
Reviewer #2: yes

**7. Have the authors clearly stated the limitations of their study/theory/methods/argument?**

Reviewer #1: No
Reviewer #2: no

**8. Does the manuscript structure, flow or writing need improving (e.g., the addition of subheadings, shortening of text, reorganization of sections, or moving details from one section to another)?**

Reviewer #1: Yes
Reviewer #2: yes

**9. Could the manuscript benefit from language editing?**

Reviewer #1: Yes
Reviewer #2: Yes

---

## Editorial note

> Editorial note: the title of the article is very long. Is it necessary to mention "for Chile's National Electricity System" in the title? Journal articles should have more general validity that the application to a single country.

---

## Reviewer #1

> This manuscript addresses probabilistic forecasting of renewable energy curtailment. Based on plant-level data from Chile's National Electricity System, the authors develop a two-part probabilistic forecasting model and combine PIT scoring, adaptive conformal inference (ACI), and an optimal transport mechanism to calibrate prediction intervals under distributional shifts. The study has potential value in terms of both data resources and practical applications. However, the current manuscript still has several important issues that need to be addressed. Therefore, I recommend major revision.

### R1.1

> 1. This work uses only the hurdle mixture model as the base probabilistic forecasting model, which is insufficient to validate the stability of the proposed calibration method across different base models. Although the hurdle model aims to fit a full predictive distribution instead of optimising point prediction errors, PIT scoring, transport mapping and ACI updates all rely on this base distribution. The quality of the base model directly determines the sharpness and calibration performance of final prediction intervals. Current results cannot tell whether the performance advantages of Transport+ACI originate from the calibration mechanism itself or merely its compatibility with this specific base distribution setup. It is recommended to adopt at least one competitive probabilistic forecasting model (e.g., multi quantile GBM), repeat all Transport+ACI experiments, and verify the model agnostic property and stability of the proposed method.

### R1.2

> 2. The description of the Transport+ACI method remains conceptual and lacks essential implementation details. Critical practical information is not adequately specified, including the length of the recent observation window, selection rules for empirical quantiles, interpolation schemes, bootstrap resampling repetitions, the exact tail shrinkage function, shrinkage strength, and the execution order between transport mapping computation and ACI updates. It is recommended that the authors add an algorithm flowchart to fully illustrate the complete workflow of Transport+ACI: from input processing, PIT score calculation, transport map estimation, tail robustification and ACI updates, to the generation of final prediction intervals.

### R1.3

> 3. Ablation experiments for the Transport+ACI method are still inadequate, and the actual contribution of each core component to performance improvement cannot be clearly identified. Existing experiments lack targeted validation for the internal key mechanisms of Transport+ACI. In particular, the authors introduce a bootstrap variance based tail shrinkage strategy built upon score transport, yet experimental results with this strategy disabled are not reported. Therefore, it is difficult to judge whether performance gains are mainly attributed to score transport, ACI adaptive updates, or the tail robustification mechanism. The authors are suggested to add ablation groups including pure ACI, Transport+ACI (without tail shrinkage), and the full Transport+ACI model, to further verify whether newly introduced mechanisms and their computational complexity bring tangible performance improvements.

### R1.4

> 4. The rationale for selecting key hyperparameters and the model tuning procedure are not sufficiently validated, which may undermine the objectivity of experimental results. Independent validation or systematic selection procedures are missing for hyperparameters such as window length, gamma, and parameters of the base forecasting model. This may introduce result selection bias, and it cannot be confirmed whether the reported performance depends on a specific favourable parameter combination. It is recommended that major hyperparameters be determined via an independent validation set or rolling origin validation in the training and calibration phases. Sensitivity analysis for key hyperparameters including window length and gamma should be carried out. In addition, the final test set must be strictly reserved for one off performance evaluation to improve the reliability and reproducibility of experiments.

### R1.5

> 5. The current evaluation framework is insufficient for measuring the performance of final prediction intervals generated by different calibration methods. This paper mainly uses empirical coverage, mean interval width computed only over finite intervals, and the fraction of infinite intervals to evaluate conformal calibration methods. Note that CRPS characterises only the base predictive distribution and cannot reflect performance differences among calibration schemes such as Static split, ACI and Transport+ACI. Especially for scenarios that produce infinite upper prediction bounds, calculating mean interval width solely on finite intervals in Table 2 may give an overly optimistic view of sharpness for certain methods. On top of existing coverage and width metrics, the authors should adopt comprehensive metrics suitable for one sided prediction limits, and clarify how infinite prediction bounds are handled in overall performance assessment. This allows a more fair comparison of the trade off between reliability and sharpness across different calibration methods.

---

## Reviewer #2

> Manuscript: SEGAN-D-26-03850
> Recommendation: Major Revision
>
> The manuscript presents a potentially valuable plant-level curtailment dataset and a conformal forecasting framework for Chile's electricity system. However, the literature review, evidence supporting the storage-driven regime change, methodological reproducibility, and statistical validation require substantial improvement before publication. The paper currently claims a dataset covering 53 months and 300 plants and attributes a major change in curtailment behaviour to battery deployment.
>
> Major comments

### R2.1

> The literature review is inadequate. The manuscript contains only ten references and focuses mainly on conformal prediction, while largely omitting curtailment forecasting, BESS operation, transmission congestion, grid capacity, cable ampacity, thermal constraints, and hybrid physics-data modelling. The authors should also cite broader independent literature to maintain balance.

### R2.2

> The BESS-related regime change is not sufficiently demonstrated. The authors should provide BESS capacities, commissioning dates, locations, charging-discharging data, and their relationship to affected renewable plants. Changes in renewable capacity, transmission outages, demand, hydrology, and marginal prices should also be evaluated. Otherwise, the wording should be changed from "storage-driven regime change" to "a regime change coincident with BESS deployment."

### R2.3

> The regime timeline is inconsistent. The manuscript refers to a 2025 change, while the evaluation defines October-December 2024 as the BESS ramp. The authors should provide one consistent chronology and conduct sensitivity tests using alternative change-point dates.

### R2.4

> Methodological novelty and reproducibility are unclear. The authors should identify precisely what is new in the PIT, transport, shrinkage, and ACI combination. A complete algorithm, parameter settings, calibration-window length, bootstrap procedure, random seed, and ablation study are required.

### R2.5

> The conformal validity under panel dependence requires stronger treatment. Plant observations are strongly correlated by date. Clustered standard errors quantify uncertainty in reported coverage but do not restore exchangeability. Block-, group-, or plant-level conformal calibration should be tested, with coverage reported by technology, plant size, region, and high-curtailment events.

### R2.6

> The benchmarking and evaluation should be expanded. Add probabilistic baselines such as empirical quantiles, conformalized quantile regression, rolling historical distributions, and zero-inflated parametric models. Report interval score, CRPS, Brier score, conditional coverage, infinite-interval frequency, and uncertainty in differences between methods.

### R2.7

> The claims should be moderated. The conclusion that point forecasting offers little value applies only to the tested models, features, horizon, and MAE metric. The Abstract and Conclusion should clearly distinguish finite-sample validity under exchangeability, long-run adaptive control, and empirical coverage in the dependent real dataset.

> The manuscript has publication potential, but the above issues require substantial revision.
