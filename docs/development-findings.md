# First development findings

This is an executed exploratory pilot, not the completed research study. The [pre-scoring protocol](pilot-protocol.md), [implemented methods](implemented-methods.md), and [complete tables/figures](results/frangieh-development-v1/results.md) define what was run. Five acquisition seeds share one frozen split and assessment/control bank; they are not biological replicates.

The central finding is that **zero-effect prediction outperformed all measured acquisition/predictor combinations on the predeclared full aligned-gene endpoint** in this Frangieh direction. Its normalized error area was 0.00239045, compared with an estimated assessment mean-noise floor of 0.00227677. Their difference is only about 0.00011368. This estimate is noisy, conditional on the scoring bank, and does not prove that perturbations have no biological effects. It does show that gains between complex acquisition rules cannot establish useful overall prediction in this pilot.

The run used 205 overlapping eligible interventions, 51 sealed query genes, 154 calibration candidates, 23,712 expression genes, budgets 128/256/512, eight acquisition policies and six crossed predictors. Every policy paid for the common 88-unit pilot. Full local acquisition, prediction and scoring completed in about 378 seconds while data preparation also ran. Raw/prepared matrices and large prediction arrays remain ignored. Compressed per-query metrics, provenance, allocations, code snapshot and standalone figures are retained in `docs/results/frangieh-development-v1/`.

The primary, same-backbone comparison is negative for the proposed extension:

| Ridge acquisition policy | Normalized full-gene error area | Relative change vs classical worst-query |
| --- | ---: | ---: |
| Worst-query classical design | 0.00544972 | reference |
| D-optimal | 0.00545880 | +0.17% |
| Disagreement weighted | 0.00477201 | -12.44% |
| Fixed-kernel discrepancy extension | 0.00690950 | +26.79% |
| Random/equal depth | 0.01075034 | +97.26% |

These relative changes are descriptive within the fixed ridge predictor. Disagreement weighting was a secondary comparator among several policies and still failed to beat zero effect. The intervention bootstrap in the detailed report conditions on the source data, split, acquisition seeds and one assessment/control bank. Its narrow intervals must not be read as biological replication, valid common-control uncertainty, or evidence of a general ranking.

The extension changed allocation substantially. At the 512-unit ceiling, across five seeds it opened an average 36.4 interventions and acquired 62.4 controls, compared with 15.6 interventions and 137.6 controls for classical worst-query design. Disagreement weighting opened 12.2 interventions and acquired 184 controls. Mean actual spends were 510.4, 508.8 and 509.6 respectively; unused block remainders are included in the retained accounting. These allocations are observed evidence. The explanation that an overly large discrepancy prior diverts resources from controls is a **hypothesis**, not a demonstrated causal attribution; control-allocation and discrepancy-weight ablations are still needed.

Simple predictors remain essential. Under classical worst-query acquisition, source copy had area 0.00308340, the shared mean 0.00430830, and pooled scalar affine adaptation 0.00240801. The affine fit nearly matches zero, while the current low-rank ridge overfits at small budgets. Its ridge penalty is a predeclared untuned .1. A stronger shrinkage baseline and validation procedure must be developed without free recipient labels before final external claims.

One subtle validation risk needs explicit handling: calibration contrasts share noisy controls, so ordinary leave-one-intervention-out error can reward fitting that same control error. Any future paid-label cross-validation must either use separately purchased validation controls or account for this covariance. Reusing scorer controls for tuning would invalidate the boundary. Improving this baseline is authorized implementation work; changing the original pilot's primary endpoint or hiding its negative result is not.

The subsequent implementation adds paid-label `ridge_cv` with a tested shared-control correction. Its follow-up is development work on an already studied context, not a new held-out confirmation. Since the first pilot's scoring results now inform method development, those observations must also be disclosed as development resources. [Union accounting](evidence/development-resource-accounting.json) records 448 control cells, 3,704 perturbed cells and 202 opened target identities across the exposed acquisition/scoring banks: 4,960 abstract units with the declared setup/cell schedule. This counts shared retrospective observations once; each counterfactual policy still has its own acquisition ledger. These fixed development resources belong alongside incremental recipient budgets in any final cost claim. Scorer labels are not passed into the follow-up predictor or its penalty selection, and external outcomes remain unopened.

The offline linear simulation also retained a negative extension result: area 0.241864 versus 0.234487 for worst-query (about +3.15%), with random/equal depth at 0.283840. It had six query interventions and five acquisition seeds. That small example checks execution and a specific noise/mechanism setting; it is not the complete controlled simulation study.

## Stronger shrinkage follow-up

The [separate v2 report](results/frangieh-development-v2/results.md) was executed at published code commit `c347560`, using the same paid acquisitions and adding covariance-correct `ridge_cv`. Its primary backbone was specified as `ridge_cv` before that run scored, but it remains exploratory follow-up on an already studied development split. Source-code snapshots and all original fixed-ridge outputs are retained.

Worst-query error area fell from 0.00544972 for fixed ridge to 0.00306947 for paid-validated ridge. With that stronger backbone, discrepancy-extension area was 0.00319709, or **4.16% worse** than worst-query. D-optimal had area 0.00289337, and disagreement weighting 0.00297663. Zero effect remained best at 0.00239045. The method ranking and gap sizes therefore depend substantially on prediction regularization; an acquisition result alone is insufficient evidence of useful prediction.

All 120 policy/seed/budget checkpoints selected the maximum declared penalty, 1000. This is a boundary diagnostic, not evidence that the penalty grid is optimal. Further shrinkage or an explicitly selectable null predictor should be assessed from permitted development observations before freezing a final external predictor. The original fixed-ridge contrast is not replaced by this new result. Its manifest records about 411 seconds, 19,708 fixed public-source cells and 1,888 scorer-only query/control cells.

The implemented selector's fixed-design shared-control correction passed independent Monte Carlo checks, but its practical variances are estimated and acquisition is adaptive. Its error estimates and the report's conditional bootstrap are not biological or post-selection guarantees. Source uncertainty, batch dependence and common assessment-control uncertainty remain outstanding analysis requirements.

Both Replogle inputs are now verified and prepared. Metadata-only overlap is 525 targets with at least 96 cells each in both cell lines. External scoring has not been used for development. Their prepared manifests record that unrelated package sources changed during preprocessing; input/output hashes and start source hashes are retained. The released gene panels differ and normalization uses each file's available-gene denominator, a compositional limitation that must accompany their exact aligned-gene evaluation. The original arms also differ in sampling time and CRISPRi effector, so this is a combined protocol/biological transfer test, as detailed in [external compatibility](external-data-compatibility.md). Batch and guide fields are preserved, without assuming batches are independent biological replicates.

Outstanding work includes accounted development tuning, complete controlled simulations, faithful feasible prior-method comparisons, source/block uncertainty, permutation checks, full allocation/covariance/extension ablations, external evaluation in both directions, and a final evidence-to-claim assessment. The implementation goal remains active.
