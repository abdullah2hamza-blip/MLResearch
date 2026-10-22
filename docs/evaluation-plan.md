# Evaluation plan

This is a prospective specification. No performance numbers, power calculation, or biological replication claim has been produced.

## 1. Separate the tasks

| Task | Recipient information | Purpose |
| --- | --- | --- |
| A: zero-recipient-perturbation reference | Paid controls only; no recipient perturbation labels. | Establish the starting transfer gap. |
| B: budgeted calibration, primary task | Paid controls plus acquired non-query calibration interventions. | Test whether a measurement policy improves sealed recipient-query effects. |
| C: direct-query measurement reference | Measurement of each query in the recipient, charged to budget. | Estimate when indirect transfer stops being economical. Excluded from the primary sealed-query comparison. |
| D: unseen perturbation and unseen context | No source measurement for the query. | A later, harder task; not implied by success on B. |

Arc's 2026 challenge supplies recipient basal cells without recipient perturbation measurements. Task B must not be presented as a compliant zero-shot submission or compared as if it had the same information. As of this cutoff, Arc schedules final test-set release for October 22, 2026; this plan does not depend on obtaining its withheld response labels. [Official task and timeline](https://arcinstitute.org/news/virtual-cell-challenge-2026).

## 2. Dataset and split policy

Use Frangieh's multi-condition cohort for initial development, then freeze the design and test external transfer on the Replogle K562-essential/RPE1 pair if the metadata audit supports it. These resources differ in perturbation modality and experimental setting, so report results separately. Additional HepG2/Jurkat files are candidate replication resources, not guaranteed compatible data.

For every evaluation episode:

1. Declare source and recipient contexts, measured gene axis, transformation, eligible intervention identities, and permitted metadata.
2. Fix recipient query identities before acquisition. Their source responses are allowed input, but their recipient responses are inaccessible to every acquisition policy and predictor.
3. Split non-query recipient identities into purchasable calibration candidates. No free recipient training or validation panel is allowed. Hyperparameters are frozen on development contexts; any within-episode validation labels must be purchased.
4. Divide recipient condition pools, including controls, into an acquisition bank and a disjoint assessment bank. Estimate scoring effects with assessment controls that are independent of the paid controls used for prediction. Prefer independent biological/guide/batch blocks where available. Otherwise label this a cell-subsampling study, not biological replication.
5. Reveal acquisition cells only after a logged action. A repeated action reveals unused cells, never a second copy of a previously seen cell.
6. Fit transformations and representations using the declared source data and paid recipient observations. Never fit gene selection, normalization statistics, transfer coordinates, early stopping, or thresholds to recipient query responses.
7. Freeze all predictions and action logs before the scorer opens recipient-query assessment outcomes.

Bank eligibility may use predeclared counts and guide/batch identifiers, identically available to all methods; it may not use effect sizes or query expression. Counts can themselves carry biological information, so record this interface and include a count-blind sensitivity analysis.

Keep gene identity groups disjoint between recipient calibration and query sets. Where multiple guides target the same gene, keep them together for this split. Do not randomly split cells and call that intervention generalization.

The assessment bank is a fixed, scorer-only evaluation resource. Its cells are not available to a policy and are excluded from the acquisition budget; publish their counts separately. Do not reuse paid controls as scoring controls, which could reward shared measurement noise. Report assessment-effect reliability and the estimated noise floor alongside model error. Independent assessment noise adds a common error component in expectation, but still affects precision and paired uncertainty analysis.

## 3. Budget accounting

Start with abstract measurement units, not claimed laboratory dollars. Charge all recipient controls, calibration pilots, validation samples, and extra depth. Source-atlas construction is a declared sunk cost shared by all policies; report its scale separately.

Candidate replay budgets are 1,024, 2,048, 4,096, and 8,192 recipient cells, with actions in blocks of 16 or 32 cells. **These values are provisional** until unlabeled inventory counts establish feasibility. Lock the feasible grid before reading final effects. Record exhaustion of finite pools, new-intervention setup charges, and control allocation.

Run separate sensitivity analyses for setup-cost-to-cell-cost ratios 0, 16, and 64. These are experimental assumptions, not estimates of real screen prices. Pooled screens do not offer perfectly independent per-gene cell purchases; successful replay would require validation of that abstraction with an experimental collaborator.

## 4. Mandatory comparators

Cross acquisition policies with the same prediction backbone wherever possible. This separates a better measurement plan from a better response model.

| Family | Required comparators |
| --- | --- |
| Simple prediction | Zero effect; mean acquired recipient effect; raw source copy; affine/ridge source-to-recipient transfer. |
| Strong transfer | Low-rank transfer and a faithful PerturbMap-style baseline if its interface can be reproduced; report differences if reimplemented. |
| Uninformed acquisition | Random identities with equal depth; a fixed breadth/depth/control grid tuned only on development data. |
| Geometry acquisition | Source-feature diversity or k-center selection; D-optimal design with the same nuisance intercept. |
| Decision-aware classical design | Transductive worst-query-variance design with the **correct shared-control covariance**, identical learned features, and identical costs. |
| Noise allocation | Pilot-reliability-based depth allocation inspired by the reliability study; distinguish an adaptation from the authors' method. |
| Uncertainty acquisition | Maximum predictive variance and ensemble disagreement using paid pilot data. |
| Diagnostic references | Oracle variance/shift knowledge and direct-query measurement, clearly marked as stronger information or a different task. |

Match source-query access, target controls, pilot cells, tuning effort, model capacity, and compute caps. A foundation model is not mandatory for proving the design hypothesis. If used, record checkpoint and training-data overlap; do not claim untouched context generalization without auditing pretraining exposure.

## 5. Outcomes and analysis

**Primary endpoint:** equal-weighted, per-query error in the control-relative response vector as a function of total paid cost. Use full-gene squared error on a gene axis selected from development/source data. Normalize only by a scale frozen from development data. Report both each budget and trapezoidal area under the error-versus-cost curve over the same grid.

The main contrast is against the strongest development-selected, information-matched baseline. Predeclare that comparator before final scoring rather than selecting it from final results. Include paired differences and uncertainty intervals; publish individual context directions instead of only an aggregate.

**Required secondary endpoints:**

- Gain relative to zero-effect and shared-response baselines, including weak-effect strata.
- Gene-coordinate correctness, effect direction, and intervention-specific residual recovery. [AmbiModBench](https://arxiv.org/abs/2609.32527) motivates these checks; they are not new contributions.
- Risk-versus-retained-query curves for deferral, with retained-query counts and a distance-only comparator. Coverage here means the fraction of queries retained, distinct from prediction-interval coverage.
- Empirical interval coverage and width at 90% and 95% nominal levels, explicitly labeled descriptive unless a valid theorem covers the data and adaptive procedure.
- Shared-control allocation, unique interventions acquired, cells per intervention, query-support rank, runtime, and memory.
- Separate results for absolute-effect estimation and within-context ranking, because shared baseline error can cancel in ranking contrasts.

If a cell-distribution predictor is added, report a distributional distance as a secondary outcome. A small pseudobulk error does not establish accurate single-cell heterogeneity.

Use at least five acquisition seeds in the pilot, then size the final replication from pilot variability. Bootstrap perturbation identities and available independent biological/guide/batch blocks with pairing across methods. Report the resampling unit. Two cell-line directions do not provide a population of independent tissues, and thousands of cells do not fix that limitation.

## 6. Ablations and adversarial checks

| Check | Failure it detects |
| --- | --- |
| Fixed identities, optimize depth/control only | Whether most benefit is ordinary replication allocation. |
| Fixed depth/control, select identities only | Whether geometry adds anything beyond improved measurement quality. |
| Remove only shared-control covariance | Misattribution of covariance benefits to a model change. |
| Classical design versus proposed bias-aware extension | Whether the algorithmic contribution exceeds a standard design adaptation. |
| Shuffle source intervention identity while preserving recipient splits | Use of biological identity versus generic average-response fitting. |
| Permute gene coordinates in scoring | Metrics that remain high despite incorrect affected genes. |
| Increase noise without changing the mechanism; change the mechanism without increasing noise | Confounding of imprecision and nontransferability. |
| Add source-feature uncertainty and batch effects separately | Failure of exact-feature and independent-cell assumptions. |
| Near-null and strong-effect strata, including missing/captured-cell analysis | Wins obtained by ignoring hard or lethal perturbations. |
| Read-access audit and rerun with sealed recipient labels | Preprocessing or adaptive-selection leakage. |

## 7. Continuation rule

An engineering target, chosen for planning rather than derived from power, is a 10% reduction in primary error-versus-cost area over the best matched baseline, consistent direction across at least two external transfer directions, and a paired uncertainty interval that excludes zero improvement. If the data cannot support that comparison, report the actual weaker evidence and do not assert success.

Stop the method claim if the gain requires final-query labels, free calibration data, stronger source tokens, post-hoc metric selection, or pooling incompatible tasks. A negative result remains useful if it establishes a reproducible information boundary and releases a defensible protocol.
