> Historical primary-study report. The later [internally reviewed manuscript and publication package](publication-guide.md) add the complete split/rank/budget robustness matrix, including conditional successes. Original frozen results below are preserved.

# Budgeted identification of transferable perturbation effects

Computational research report, October 22, 2026.

## AI assistance disclosure for this distributed report

Artificial intelligence (AI) tools were used for manuscript editing and code preparation.

OpenAI Codex (OpenAI) assisted with research planning, literature review and experimental design, code preparation, statistical analysis and interpretation, figure and table preparation, manuscript drafting and revision, internal review, and release preparation. These AI-assisted reviews were internal quality checks, not independent human peer review. The human author retains responsibility for the final work.

The implemented study finds **no demonstrated primary benefit from adding the proposed fixed-kernel discrepancy term to classical joint acquisition design**. In the frozen external replay, its error area is 0.565% higher for K562→RPE1 and 0.0138% higher in reverse, with conditional query-bootstrap bands spanning zero. Controlled simulations show mixed effects, and the real development improvement is negligible. These results support retaining the simpler classical comparator rather than claiming a new acquisition advantage.

This conclusion concerns the specified extension. External paid transfer can outperform zero effect, and other matched acquisition/predictor combinations remain competitive. The study does not establish that transfer or joint budgeting is useless. It also does not establish novel priority, biological identification, calibrated selective coverage or prospective laboratory savings.

## Question and implemented method

The question is whether a fixed recipient acquisition budget should buy another calibration intervention, deeper measurement of an existing intervention, or additional shared controls to predict interventions left unmeasured in that recipient. Source responses for those query identities are public. Queries are gene-grouped and recipient calibration identities are disjoint. Every purchased cell comes from a finite pool; independent scorer-only query/control banks remain sealed through prediction.

The estimand is a difference of cell means after `log1p(10000 * count / released-panel library total)`. It is not count-mean log fold change. Source-only coordinates define a low-rank linear transfer model. Classical design accounts for the unknown recipient baseline and shared-control covariance. Unregularized span diagnostics are evaluated separately from ridge regularization. The extension adds the per-cost reduction of a fixed RBF discrepancy-variance surrogate to worst-query variance reduction. It does not estimate realized structural bias online, and its surrogate need not equal the fitted predictor's risk.

The [formal implemented methods](implemented-methods.md) give the covariance, paid validation correction, greedy objectives, assumptions and failure cases. [Comparator reconstruction](transfer-comparator-protocol.md), [source-half sensitivity](source-sensitivity-protocol.md) and [separate assessment uncertainty](assessment-uncertainty-protocol.md) specify additional choices. Nine prediction backbones share each policy's same purchases. Nine canonical acquisition rules, original weight .25 and six allocation/covariance/extension ablations are retained. There are no pretrained weights or uncharged recipient validation labels.

## Completed evidence stages

| Stage | Executed scope | Scientific result |
| --- | --- | --- |
| Initial synthetic/Frangieh pilots | At least five acquisition seeds; matched predictors and ledgers | Negative extension result; zero effect wins the initial real full-gene endpoint. [Pilot findings](development-findings.md). |
| Controlled simulations | 14 scenarios × five independent worlds × five acquisition seeds, with 14 policies/ablations | Extension is 1.41% worse in the base setting and 5.08% better under nonlinear shift; higher mean error in ten scenarios and lower in four. Source noise can create false apparent support. [Controlled findings](controlled-study-findings.md). |
| Development tuning | Nine fixed grids and five discrepancy weights; seven predictors | Selected fixed fraction .125/depth 8 and weight 1; heavy shrinkage and near-null responses. Choices frozen before external scoring. [Tuning findings](development-tuning-findings.md). |
| Integrated development | Ten policies × nine predictors × five seeds × three budgets | Exact fidelity for 20 matched ledgers and 420 legacy prediction arrays. Extension gain versus worst-query only 0.022%; all separate uncertainty bands include zero. Reconstruction loses to its local base in absolute error. [Integrated findings](integrated-development-findings.md). |
| Frozen external evaluation | Both K562/RPE1 directions; all ablations and four permutation controls; 720 checkpoints and 848,880 metric rows | No primary extension benefit. Secondary mean-query comparison changes sign across directions. Full source/control/deferral failures retained. [External findings](external-evaluation-findings.md). |
| Declared post-primary supplement | 30 setup-cost cases; 60 charged direct-query checkpoints; 109,380 frozen coordinate/ranking rows | Mixed price sensitivity; actual ranking differs from absolute error; 90/95 diagnostics fail under misspecification. [Secondary findings](secondary-supplement-findings.md). |

The stages are not interchangeable replications. Simulation uncertainty uses independent generated worlds; acquisition seeds summarize algorithmic variation at a fixed real split. The two external directions reuse observations and query identities. Technical batches, guides, cells and genes do not create independent biological replicates. Five fixed final seeds were justified by pilot variability and bounded local resources; no outcome-dependent extra seeds, stopping, exclusions or external hyperparameter search followed.

## What the results establish

The system can execute the intended joint finite-pool acquisition experiment with matched information and paid costs. Independent covariance/Monte Carlo checks, leakage adversaries, exact ledger/prediction consistency and the actual joint gate support that engineering claim. They do not prove biological transfer assumptions.

The primary external comparison does not justify the discrepancy extension. Its fixed source-smooth prior can allocate more openings and fewer controls without improving prediction. The simulations also show that a gain under nonlinear shift does not establish online bias detection: matched allocation sequences can remain identical across linear/nonlinear worlds. Changing the extension after these outcomes would be a new development hypothesis requiring a new evaluation, not a correction to this result.

Source correspondence carries some external signal. Paid-validation ridge improves over zero under extension acquisition by about 3.159% forward and 0.623% reverse; source-identity corruption largely removes that utility. Yet raw source copying and weakly regularized transfer can fail badly. Query-gene permutation does not eliminate every small shrinkage/global advantage. Absolute effects and centered response specificity differ substantially, especially for the reconstructed transport method. Full crossed tables prevent favorable secondary rankings from replacing the primary test.

Conditional numerical identification is insufficient. In the controlled noisy-source missing-direction case, all estimated queries appear supported while oracle population support is zero. Real source-half agreement likewise does not certify support. Heuristic source-stability deferral can select stronger, harder queries and increase retained absolute MSE. Ideal Gaussian fields on real data measure compatibility with noisy contrasts, not coverage of unknown population effects.

The paired assessment identity is checked against original metric differences, with one shared control resample across queries. Query bootstrap, fixed-query cell bootstrap and technical-batch sensitivity have separate scopes. In the external guide×batch-stratified bootstrap, 243/256 and 247/256 controls are singleton strata; its narrow bands condition away most control variation. None is a calibrated combined biological interval or an account of all source/adaptive/model uncertainty.

## Data, cost and reproducibility

Three pinned, checksum-verified public H5AD inputs supply Frangieh development and Replogle K562-essential/RPE1 evaluation. [Compatibility and attribution](external-data-compatibility.md) record release/license, original papers, actual identifiers, normalization panels, paired-guide grouping, survival/capture selection, day/effector differences and absent donor/biological replication metadata. The [canonical audit](evidence/external-canonical-identifiers-v1.json) validates all 525 external target IDs and 7,226 aligned expression-gene IDs, including sealed canonical split separation.

The initial [post-scoring raw/prepared audit](evidence/prepared-row-audit-v1.json) independently reselects all 166,118 retained metadata rows and reproduces 820,480 sampled full-panel float32 expression values exactly. The subsequent [complete preparation reproduction](evidence/full-preparation-reproduction-v1.json) rebuilds all three matrices from pinned raw inputs: every NPY byte and all retained metadata match, covering 2,405,927,872 values with zero differences. Historical source hashes and the RPE1 IO-batch difference remain explicit. This is numeric reproduction in the pinned environment, not biological replication.

All 720 prediction checkpoints closed before any external assessment opened. [Completion authentication](evidence/external-completion-audit-v1.json) verifies every artifact/index and ledger prefix, independently reconciles 240 paid ledgers, rejects scorer/repeated cells and recomputes prices. It also confirms ten zero-weight/classical ledger pairs and 30 fixed-grid query-gene invariant checkpoints. The cooperative API/hashing boundary protects against accidental leakage and corruption; it is not a hostile-process filesystem sandbox.

The fixed development exposure is 6,428 abstract units. External budgets add 128/256/512; public-source, fixed scorer, actual predictor-used measurements and computation remain separate. Units are not laboratory prices. The external suite used one worker/one BLAS thread, 2,297.23 process CPU seconds and about 708 MB peak working set. Its 30,223.79 elapsed seconds include observed event gaps; CPU counters and process-lifetime memory scopes are retained. Reporting and audits are additional work. No paid compute was used.

The [implementation guide](implementation-guide.md) and [external reproduction workflow](external-reproduction.md) provide locked uv commands, fresh-path declarations, data preparation, deterministic episodes, acquisition/scoring recovery, reports and audits. Source snapshots and hashes preserve historical experiments. Raw/prepared matrices and large predictions stay ignored; manageable compressed metrics, cell-ID ledgers, standalone PNG/SVG/PDF figures and diagnostic tables are retained. The [101-test Windows/Ubuntu CI record](evidence/ci-a04f92f.json) and [isolated-wheel execution](evidence/installed-wheel-a04f92f.json) substantiate package/CLI reproduction within their tested scope. Supplementary ranking/interval tests bring the [final local suite](evidence/final-local-checks-v1.json) to 108 passing tests; [all 11 requirement checks](evidence/goal-completion-audit-v1.json) retain their evidence and final publication status.

An actual [fresh real-episode rebuild](evidence/rebuilt-external-episodes-v1.json) reproduces every public source array and all split/bank maps exactly from the verified preparations. A regenerated canonical audit and fresh-path six-run declaration also pass. Complete raw preparation was subsequently reproduced as described above; the 720-checkpoint external experiment was executed once, not independently repeated.

The [secondary completion findings](secondary-supplement-findings.md) preserve the original plan's remaining checks and their post-primary timing. Cost ratios 0/16/64 show pool exhaustion and mixed extension effects. Charged direct measurement starts at 802 units, above the primary 512 ceiling; no equal-cost crossover or total-program savings is established. Actual within-gene Spearman scores, undefined denominators, scoring permutations, direction agreement, distance retention and both 90/95 diagnostics are retained. Conditional count blindness does not undo cohort selection. The prospective strongest-development-reference rule changed explicitly to worst-query before scoring; post-primary contrasts against development's zero and reliability/ridge references document that deviation without replacing the primary result.

## Evidence-to-claim assessment

| Claim | Assessment |
| --- | --- |
| This exact discrepancy extension improves budgeted transfer | Not supported by the primary external comparison; controlled findings are mixed. |
| Permitted recipient calibration can carry useful external information | Supported descriptively in this released-data replay; limited by finite banks, protocol differences and absent biological replication. |
| Classical covariance-aware joint design is new | False priority framing; it is implemented as a baseline. |
| Cross-context prediction-directed acquisition or cell/control-aware planning is new | Unverified and restricted by IterPert/PerturbPlan and other predecessors. [Literature verification](literature-verification.md). |
| The original PerturbMap result was reproduced or refuted | Unsupported; this is an explicitly qualified single-source reconstruction. |
| Numerical source span or half agreement identifies population transport | Unsupported; the simulation provides a counterexample. |
| Deferral or real Gaussian bands provide calibrated biological guarantees | Unsupported. Reported diagnostics are conditional and sometimes fail. |
| Prospective experimental or monetary savings are established | Unsupported; acquisition is a retrospective abstraction with hypothetical prices. |

The complete CausalPert/multiaxis methods remain inaccessible despite resolved bibliographic identities; that is an explicit limit on novelty assessment. The supported contribution of this repository is a reproducible, audited computational evaluation and its negative/failure evidence. Prospective validation, biological replication, new acquisition methods and a fresh confirmatory dataset are future research, outside this completed experimental specification. Goal completion itself remains subject to the [full requirement ledger](implementation-status.md) and publication audit.

The original evaluation plan's secondary checks are complete, with [reproduction commands](secondary-supplement-reproduction.md), retained failure/recovery evidence and a separate post-primary interpretation. [Expanded Windows/Ubuntu CI](evidence/ci-f892907.json) passes all 108 tests, static checks and offline CLI/recovery/retention checks. The [requirement ledger](implementation-status.md) and [full audit](evidence/goal-completion-audit-v1.json) record completion; the scientific result remains the supported negative finding stated above.
