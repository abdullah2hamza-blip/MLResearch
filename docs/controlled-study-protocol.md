# Controlled simulation protocol

Frozen implementation study, October 22, 2026. The executable declaration is [study-controlled-v1.json](../configs/study-controlled-v1.json). This extends the exploratory pilots; it is not external biological confirmation. The external K562/RPE1 assessment banks remain unopened. The full [implementation objective](implementation-objective.md) still governs completion.

## Question and endpoint

Compare `bias_aware` against covariance-correct `worst_query` using the same `ridge_cv` predictor, information interface, pilot, costs, and finite inventory. The primary endpoint is normalized trapezoidal area of full-gene mean squared error over recipient budgets 96, 144, and 192. The simulation endpoint uses the known population contrast, opened by a separate diagnostic scorer only after every prediction has been frozen and ordinary assessment scoring has completed. Lower error is better; positive paired differences mean that the extension is worse. Report all scenarios, policies, backbones, budgets, and signs. No success threshold or retrospective choice of a favorable scenario is allowed.

Five independent generative seeds, 71–75, each provide a full paired world. Within each world, average the six query interventions and five acquisition seeds, 0–4, before calculating each policy's error area. Paired differences and their Monte Carlo standard errors use the five world-level differences. Acquisition seeds and genes do not increase the number of independent worlds. Five worlds provide an initial controlled diagnostic, not precise tail probabilities or biological replication. Cross-scenario differences use common random draws to isolate a changed factor; scenario results are dependent and are not pooled as independent replicates.

## Generator and information

Generator version 2 separates the latent/data random stream from the query-split stream using a domain-separated seed. Each world has 24 interventions, 64 measured genes, and three latent response coordinates. A metadata-only split reserves six identities as queries and 18 as calibration candidates. Source responses for all 24 identities are public, including queries. Source coordinates are learned from these public responses; no recipient query response enters acquisition or prediction.

Source observations have 32 cells per intervention. Each recipient intervention has 24 acquisition and 24 independent assessment cells; query acquisition cells are absent from the acquisition interface. Recipient controls have 64 acquisition and 64 independent assessment cells. The scorer's reserved cells are not charged as predictor access, and their counts are reported separately. Every returned acquisition block contains new cell IDs. All source, acquisition, and assessment banks have distinct IDs. The generator writes population contrasts and latent coordinates to an oracle artifact; neither enters `PublicEpisode`, policies, or predictors.

The base model has Gaussian expression with distinct source and recipient loading matrices. Thus raw source copy is not the population transfer map. Persistent source-feature error, source measurement noise, recipient measurement noise, control noise, missing calibration directions, nonlinear mechanism shift, and batch effects are distinct mechanisms. Batch effects are balanced across full recipient conditions so the declared population contrast remains valid, while randomly sampled acquisition/assessment banks can be imbalanced. In this stress scenario, the two disjoint cell banks share technical batch offsets and are independent only conditional on those offsets. These synthetic batches are technical structure, not biological replicates. Prepared values are expression measurements; no count normalization or biological regulatory interpretation is attached to them.

## Frozen scenario matrix

| Scenario | Change from base |
| --- | --- |
| baseline | Source noise SD .5; recipient noise SD 1; no structural shift |
| recipient_noise_half / recipient_noise_double | Recipient noise SD .5 / 2 only |
| source_measurement_noise_two | Source measurement noise SD 2 only |
| source_feature_error_half / source_feature_error_one | Persistent independent source-response error SD .5 / 1 |
| mechanism_shift_2 | Add twice a sinusoidal latent response with independent gene loadings |
| rank_missing | Set the last latent coordinate of every calibration candidate to zero |
| control_noise_four | Multiply recipient control-cell noise SD by four |
| batch_shift_one | Add shared recipient batch offsets, SD 1, across four batches |
| exact_rank_full / exact_rank_missing | Source measurement noise zero; second member additionally removes the last calibration direction |
| source_identity_permutation | Derange public source identities jointly with their variance/reliability summaries |
| query_gene_permutation | Permute only query source gene coordinates; retain the recipient gene axis and calibration source responses |

The exact-rank pair tests true null-space support without source observation noise hiding the missing direction. Noisy coordinates can have full numerical rank despite missing true latent support; that failure is measured, not declared identified by regularization. Permutations modify only public source inputs and never use recipient outcomes. Their fixed seed and exact mappings are retained.

## Costs, models, and matched allocations

Opening an intervention costs four units plus one per cell. Control cells cost one unit each. Every policy purchases the same seed-dependent pilot: six interventions with eight cells each and 16 controls, costing 88 units. Actions normally purchase eight cells. At a budget boundary, affordable partial blocks are permitted; a newly opened intervention must supply at least two cells. Common costs, pilot, source rank three, ridge candidates, and prediction backbones cannot be overridden by an acquisition ablation.

Paid leave-one-intervention-out selection compares ridge penalties .1, 1, 10, 100, 1,000, 10,000, and 100,000 and an explicit zero-effect candidate. Its known-variance correction includes the covariance induced by paid shared controls. All validation observations have already been purchased; choosing zero does not refund their cost. The correction is a fixed-design identity with known variances; its plug-in use after adaptive selection is not an unbiased-risk or coverage guarantee. Zero and source-copy predictors require no recipient measurements, and their separate zero recipient cost is retained.

Unopened-arm variance forecasts multiply public source variances by the median recipient/source variance ratio estimated from paid pilot/calibration cells. Opened-arm forecasts use their observed variances. This accounts for differing source and recipient measurement scales without revealing unpurchased recipient cells. Classical design uses the correct shared-control covariance and explicit unregularized query-span checks. The extension adds a fixed source-coordinate Gaussian-kernel discrepancy-variance reduction, weight .25 and length scale 1, to the classical gain per cost. This is a design surrogate, not an estimator of the actual backbone's predictive risk and not a novelty claim about Gaussian-process design. These hyperparameters remain untuned in this controlled study.

Run eight canonical policies: random/equal allocation, fixed grid, source diversity, D-optimal, worst-query variance, reliability, disagreement, and bias-aware. The fixed grid retains its declared defaults; development tuning and prior-method fidelity remain separate outstanding work. Run six explicitly labeled extension ablations: fixed identity order; no additional depth for opened interventions; fixed pilot controls; independent-control covariance approximation in acquisition; zero discrepancy weight; and no new interventions after the pilot. All share the same predictor, which continues to account for shared controls. The zero-weight ablation must reproduce classical acquisition exactly; dense numerical tests independently verify the cached design updates.

## Diagnostics, execution, and limits

Retain assessment MSE/noise floor, true MSE, response-specific centered MSE, source weak/strong strata, source-feature error, source-stability flags, estimated versus oracle latent support, selected shrinkage/null choices, and allocation ledgers. Oracle support is a latent linear-span diagnostic; it does not establish identification under a nonlinear mechanism. Coverage conditions on finite-width queries and includes the eligible fraction and denominator. Gaussian intervals are ideal-model diagnostics around a regularized predictor; source uncertainty, adaptive selection, and structural bias preclude nominal coverage claims. Risk/retention selects using predictor-side variance/support only, preserves unsupported queries in the denominator, and never breaks ties using assessment error.

The study runs 70 cases with one CPU worker process, reduced from the initial two-worker declaration before execution because available memory was below the two-worker guard. Configuration, sources, fixed development-resource record, predictions, splits, and oracle access are hashed. Sources and configuration must remain unchanged during execution. Worker failures produce an explicit failed manifest; no failed world is silently removed. Own-process lifetime peak memory and runtime are recorded, with their scope stated. Raw matrices and full predictions stay in ignored `runs/`; manageable tables, plots, manifests, and source snapshots are retained in `docs/results/`.

The 4,960-unit fixed Frangieh development resource is disclosed alongside incremental budgets. Its inclusion does not make simulations independent external confirmation or equate source/computation resources with recipient cell costs. Existing exploratory negative results remain in the record. This matrix can expose a failure of the proposed extension; it cannot establish effectiveness on real external recipients. Remaining requirements include stronger development-tuned comparators, feasible prior-method reconstruction, appropriate empirical common-control uncertainty, and the frozen real external study.

Reproduce from the repository root with `uv sync --locked --dev` followed by `uv run mlresearch study configs/study-controlled-v1.json`. Use a fresh output directory for another execution; the command refuses to overwrite an existing study.
