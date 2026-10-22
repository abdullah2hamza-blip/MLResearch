# Secondary completion supplement

Declared October 22, 2026, **after** the six-run primary external results. These complete explicit secondary items in the original [evaluation plan](evaluation-plan.md); their omission from the first external analysis bundle was found by the final requirement audit. They cannot replace the original primary comparator/endpoint, select new hyperparameters, claim untouched external validation or turn the primary negative finding into superiority. All original predictions, gates, settings and reports remain intact.

The [dated declaration](evidence/secondary-supplement-declaration-v1.json) hashes the original plan, completed suite, source environment, resources and three simulation configurations before supplementary execution. No paid compute or additional external tuning is authorized or needed.

## Setup costs and combined allocation ablation

Execute `configs/study-setup-cost-{0,16,64}-v1.json`, one worker and one BLAS thread, for setup/cell ratios **0, 16 and 64**. Each uses the original controlled generator's 24 interventions/64 genes, 32 source cells, 24 recipient cells per acquisition/assessment intervention bank and 64 controls/bank, original rank 3 and discrepancy weight .25. Keep five new independent generated worlds **171–175**, acquisition seeds **0–4**, and two scenarios: baseline and mechanism shift 2. This is 30 additional cases in total.

Use common budgets **512, 768 and 1,024**. The largest setup cost makes the common pilot cost 448, so the original 96/144/192 grid is infeasible. At setup 0 or 16, inventory may exhaust before a budget ceiling; report actual spend/exhaustion rather than inventing more cells. Six matched policies are random/equal, fixed grid, worst-query, mean-query, extension and **identity-only extension** (`allow_depth=false`, `allow_controls=false` after the common pilot). This last comparator completes the original combined fixed-depth/control ablation. All seven legacy prediction backbones share each paid ledger. Fixed development exposure remains 6,428 units; these generated diagnostic cells are not additional real recipient exposure.

Use the standard study runner, scorer-only known truth, source/config/data hashes, actual ledgers/resources and world-level paired aggregation. Do not choose a favorable price/scenario or compare differently priced runs as if they bought identical resources. These are hypothetical prices and additional controlled diagnostics, not new laboratory savings or a replacement primary study.

## Frozen-prediction diagnostics

Without acquiring or refitting a primary model, authenticate saved predictions and compute:

- Full-gene sign agreement, prediction/truth direction cosine and centered gene-coordinate agreement, clearly qualified against noisy real assessment contrasts. Zero predictions are explicit ties, not correct signed discoveries.
- Both **90% and 95%** Gaussian width/coverage diagnostics. Known-truth controlled coverage uses ideal variance; real compatibility adds independent assessment noise exactly as the existing 95% scorer does. Include finite-width denominators. Neither is a validated biological confidence interval.
- **Distance-only retention**, using nearest purchased calibration distance in the same public source coordinates, without recipient query labels. Keep stable label-free ties and the full query/seed denominator. Compare with the existing variance/support retention and source-warning filter; never choose a retention threshold from observed errors.
- A count-information audit distinguishing the count-selected eligible cohort from policy inputs. The capped external candidate pools are uniformly 64 cells and source conditions uniformly 96; uncapped raw per-target counts are absent from `PublicEpisode`. Verify invariance to irrelevant inventory annotations and state that conditioning on the eligible cohort does not remove capture/survival bias.

## Direct-query reference

Task C is a distinct, stronger-information diagnostic, excluded from the sealed-query primary task. Use the previously reserved first 64 cells per query (omitted from acquisition maps) and paid-control acquisition cells; preserve disjoint scorer cells. Fix query depths **2,4,8,16,32,64** and control depths **16,16,16,64,128,256**, respectively. Use five deterministic cell-order seeds 0–4, the same transformed full-gene endpoint and setup cost 4 per measured query. Retain cell-ID ledgers, independent cost recomputation, bank-disjointness and per-query metrics.

For all 131 queries, total prices are **802,1,064,1,588,2,684,4,844,9,164** units. Even depth 2 exceeds the primary 512-unit maximum, so there is no matched full-query direct-measurement curve at the primary budgets. Compare outcomes only at their charged costs and retain the unobserved common-cost gap explicitly. No direct-query labels enter the original predictions or policies. Simulation oracle truth/support remains separately labeled stronger-information scorer diagnostics.
