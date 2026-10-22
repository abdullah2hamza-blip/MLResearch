# Integrated development findings

October 22, 2026. The [declared check](integrated-development-protocol.md) completed at code commit `43d77dc4a77142459f0f5d177a048cbe343c3fe3`. All five acquisition seeds, ten policies, three budgets and nine predictors ran on the original Frangieh development episode. No additional hyperparameter search was performed. Both external recipient assessments remain unopened. This is a completed development check, not the final research study.

The run took **421.17 seconds**, including acquisition and scoring but excluding subsequent reporting/uncertainty analysis. One process used `OPENBLAS_NUM_THREADS=1`; peak working set was **986,316,800 bytes** and peak commit was **767,275,008 bytes**, with the documented process-lifetime scope. The 1,888 scorer-only cells were the already-declared 51 query banks plus independent controls. The [retained bundle](results/frangieh-integrated-v1/results.md) includes actual plots, per-query metrics, ledgers, source snapshots and manifests. Both scientific plots were visually checked.

## Fidelity and matched access

The [fidelity audit](evidence/integrated-fidelity-v1.json) confirms exact equality of **20 matched ledger pairs and 420 prediction arrays at 60 matched checkpoints** against the completed tuning run. The matched policy pairs are worst-query, the selected fixed grid, weight 1 and original weight .25. All seven legacy predictors preserve their exact stored bytes. The two new predictors use each policy's existing purchased controls, calibrations and paid validation partition; they purchase no extra cells. This verifies integration consistency, not author-code fidelity to PerturbMap.

Across all 150 integrated checkpoints, paid validation accepted the reconstructed transport route. Its ridge selector chose 10 at 146 checkpoints and 1 at four, under the fixed article-derived grid. Under the main extension, basis ranks were 15 or 16, optimizer rounds ranged from 18 to 61, and 3–5 target descriptors per checkpoint were unavailable and explicitly zero-filled. These diagnostics are retained for every policy. The original paper, cohort, optimizer and source-count differences remain [documented limitations](transfer-comparator-protocol.md).

## Actual error areas

Values are the normalized trapezoidal full-gene MSE area over budgets 128/256/512, averaging five acquisition seeds and 51 fixed query interventions. Lower is better. Zero effect has area **0.00239044947** under every policy and uses no recipient observations. The [complete nine-predictor table](results/frangieh-integrated-v1/predictor-areas.csv) is retained.

| Acquisition | Ridge with paid validation | Recipient-local network | Reconstructed transport |
| --- | ---: | ---: | ---: |
| Random/equal | 0.00239072961 | 0.00334975413 | 0.00406161318 |
| Selected fixed grid | 0.00239049694 | 0.00327288895 | 0.00403864286 |
| Diversity | 0.00239054350 | 0.00388373819 | 0.00479951794 |
| D-optimal | 0.00239245555 | 0.00342345188 | 0.00391369707 |
| Worst-query | 0.00239117783 | 0.00357545363 | 0.00370492742 |
| Mean-query | 0.00239110832 | 0.00319527353 | 0.00330705212 |
| Reliability | 0.00239046937 | 0.00427545704 | 0.00568623721 |
| Disagreement | 0.00239127655 | 0.00319354939 | 0.00336627915 |
| Extension, weight 1 | 0.00239065087 | 0.00380997550 | 0.00488725558 |
| Extension, weight .25 | 0.00239071459 | 0.00361208531 | 0.00436306533 |

The main extension's ridge area is **0.0220% lower** than worst-query but **0.00842% higher** than zero effect. Mean-query is only **0.00291% lower** than worst-query. Across 150 paid-ridge selections, 87 select null and 63 select the largest finite penalty, 100,000. These near-null estimates do not demonstrate useful transferable response prediction. The estimated assessment noise floor is 0.00227676822; subtracting it does not create independent biological evidence or resolve systematic error.

The reconstruction is worse than its recipient-local base under every acquisition policy, despite accepting every route by paid validation. This is a negative result for this declared reconstruction and small-budget information setting, not a reproduction or refutation of the original paper's reported performance. No reconstruction hyperparameter is changed in response to this result.

## Separate uncertainty scopes

The [paired worst-query analysis](results/frangieh-integrated-v1/uncertainty-worst-query.json) reproduces the original area difference **−5.26962e−7** to numerical precision. Its 2,000-draw query-bootstrap band is **[−1.29136e−6, 2.52615e−7]** conditional on the observed bank. The separate fixed-query IID cell band is **[−1.40080e−6, 3.12464e−7]**, and the guide-stratified cell band is **[−1.30576e−6, 2.87002e−7]**. Every band includes zero. The [mean-query comparison](results/frangieh-integrated-v1/uncertainty-mean-query.json) likewise includes zero under all three scopes. These bands are separate conditional descriptions, not a combined biological confidence interval.

The shared control resample is reused for all queries. In the primary comparison, its analytic IID variance component is 2.55649e−14 versus 1.60984e−13 from treatment projections. Frangieh lacks usable batch metadata, so batch-weight sensitivity is explicitly unavailable. The stratified control bank has 70 observed guide strata, including five singleton strata; resampling cannot estimate within-stratum variation for those singleton cells.

The source-half diagnostic reports no conditional support disagreements across 7,650 query/checkpoint evaluations. That agreement is not a population-support certificate. Sixteen source conditions have odd counts, so their symmetric perturbations are not exact equal-half means. Ridge predictions are refitted with the fixed paid ledger; policies and neural predictors are not rerun. The controlled study's noisy-source support failure remains applicable, and no calibrated joint source interval is claimed.

## Exposure and next freeze

The strengthened [development accountant](evidence/development-resource-accounting-v3.json) records **6,428 unique recipient cost units**: 512 controls, 5,096 perturbed cells, and 205 opened interventions at setup cost 4. This adds **84 units** to the earlier union: 80 perturbed cells and one setup. Counterfactual policy ledgers still pay separately; this union accounts for development exposure rather than asserting that every policy physically ran at the union cost. Public source and scorer/computation resources retain their separate scopes.

Future external configurations must charge the 6,428-unit record. Historical 6,344- and 4,960-unit records remain unchanged. The [canonical metadata audit](evidence/external-canonical-identifiers-v1.json) now verifies all 525 retained target IDs, their guide grouping and all 7,226 aligned expression-gene Ensembl IDs directly against both checksum-verified raw files. It reads annotation metadata only and does not resolve arbitrary external annotation versions.

Before external scoring, finish a joint prediction freeze so every declared external run closes its predictions before any external scorer bank is opened. Then execute both directions, their ablations/permutation controls and appropriately qualified uncertainty analyses. The same pair and query identities recur across directions; they are not independent biological replications. The implementation goal remains active.
