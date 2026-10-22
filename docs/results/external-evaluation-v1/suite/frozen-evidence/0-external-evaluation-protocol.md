# Frozen external evaluation protocol

Declared October 22, 2026, before either external recipient assessment bank is opened. The full [implementation objective](implementation-objective.md) is unchanged. Development choices and their negative results are recorded in the [integrated findings](integrated-development-findings.md). This protocol freezes the external evaluation, not a new tuning stage.

## Data, estimand and information

Use the existing `k562-to-rpe1-v1` and `rpe1-to-k562-v1` episodes from the checksum-verified scPerturb v1.4 Replogle essential K562/RPE1 inputs. Each has 525 gene identities, 394 eligible calibration candidates, 131 sealed queries and 7,226 aligned expression genes. Their episode manifests, prepared input hashes and [canonical identifier freeze](evidence/external-canonical-identifiers-v1.json) are required inputs. All retained target and aligned expression-gene Ensembl IDs agree across files and are unique; canonical query/candidate sets are disjoint. Preserve original guide combinations. No target, gene, query or context is selected using external effect estimates.

The estimand is the difference of normalized-log cell means, using the already-frozen transformation `log1p(10000 * count / released-panel library total)`, followed by exact gene intersection. These are released panels with different normalization denominators, not identical complete transcriptomes or count-mean log fold changes. K562 day-6 dCas9-KRAB and RPE1 day-7 ZIM3-KRAB constitute combined biological/protocol transfer. [Compatibility and attribution](external-data-compatibility.md) retain these restrictions, survival/capture selection and missing efficacy/donor/biological-replicate metadata.

All source responses, including source query responses, are allowed public tokens. Source summaries use all retained source cells: 96 per gene and 512 controls, 50,912 cells per supplied context. A query's recipient response remains inaccessible to that run's policy and predictor. Each calibration has 64 finite acquisition cells; each query has 32 scorer-only cells. Independent controls split 256 acquisition/256 scorer cells. Thus each direction opens 4,448 scorer-only cells. Reserved candidate assessment cells remain unused. The two directions reuse observations in different roles, share query identities and are not independent biological replications. They must be reported separately.

Every run gets new policy/model/observation objects; no recipient labels, learned parameters or acquisition statistics are shared across runs. There are no pretrained weights. The prior method's article used related Replogle data in its original development; borrowing its specification does not create a new independent reproduction of that paper's benchmark. This specification overlap is disclosed, without claiming absent pretraining overlap for an actual pretrained model.

## Fixed decisions and matched costs

Budgets are **128, 256 and 512** abstract incremental recipient cost units. New intervention setup costs 4; each perturbed/control cell costs 1. Blocks contain 8 cells, affordable partial blocks are enabled, and a new condition requires at least two cells. Each policy buys the same 88-unit pilot: 16 controls plus six seeded calibration identities at depth 8, including six setup charges. There is no free recipient validation or descriptor control bank. Source rank is 4, fixed ridge .1, paid ridge-validation grid `[.1,1,10,100,1000,10000,100000]` plus the null candidate, and unopened-condition variance uses the already-declared paid/source median ratio.

Use the selected fixed allocation grid: control fraction .125 and depth 8. The main extension uses selected discrepancy weight **1** and length **1**. Retain original weight **.25** as a separate named comparator. Neither setting changes after any external score. The proposed kernel variance remains a specified surrogate with possible trend/model mismatch, not a learned proof of structural bias.

All nine prediction backbones run on each policy's same purchases: zero, shared mean, source copy, scalar affine, fixed-ridge GLS, paid-validation ridge, heuristic local residual adaptation, recipient-local low-rank network and reconstructed single-source PerturbMap. The reconstruction uses the unchanged [comparator protocol](transfer-comparator-protocol.md): rank 16, 64 paid-control anchors, LayerNorm/128-unit/GELU network, AdamW .001/.0001, batch 16, three epochs/round, 100-round cap, patience 15, 20% paid validation, split seed 20260718, model seed 20261022 and transport grid .001/.01/.1/1/10. Missing descriptors remain explicitly zero-filled and counted. No alternative settings are selected because of development or external reconstruction failures.

The fixed development exposure is **6,428 cost units**, from the authenticated [v3 union](evidence/development-resource-accounting-v3.json). Total program budget ceilings are therefore 6,556, 6,684 and 6,940; actual spend is also reported. Historical development/simulation records are not rewritten. Each counterfactual policy ledger pays separately. Zero/source-copy predictors need no recipient measurements; their use-cost is recorded as zero. Public-source, scorer, computation and hypothetical recipient costs retain separate scopes. Units are not verified laboratory prices.

## Policies, ablations and negative controls

Each unmodified direction crosses the nine canonical policies (`random_equal`, `fixed_grid`, `diversity`, `d_optimal`, `worst_query`, `mean_query`, `reliability`, `disagreement`, `bias_aware`), the original-weight comparator and six main-extension ablations:

| Named variant | Change from the main extension |
| --- | --- |
| `bias_gamma025` | Discrepancy weight .25 |
| `bias_no_extension` | Weight 0; must reproduce the classical worst-query ledger |
| `bias_fixed_order` | Fixed intervention opening order |
| `bias_fixed_interventions` | No opening after the common pilot |
| `bias_equal_depth` | No increasing an opened intervention's depth |
| `bias_fixed_controls` | No enlarging controls after the pilot |
| `bias_independent_controls` | Diagonal contrast-noise acquisition ablation; prediction still uses correct covariance |

Run both source-identity derangement and query-source gene-coordinate permutation in each direction. These four negative-control runs cross fixed-grid, worst-query, mean-query and the main extension with all nine predictors. The control subset is fixed to isolate source correspondence without repeating every acquisition ablation. Use source-control seed 20261022 and retain the actual permutation record/hash. No recipient outcome selects a permutation. Under fixed-grid acquisition, query-gene permutation must leave purchases and the recipient-local network unchanged; its source-training basis excludes query tokens. Identity permutation may change that basis. Zero and source-copy responses must be interpreted according to their information use, not treated as certificates of specificity.

This gives **six declared runs**: two unmodified 16-policy runs and four 4-policy controls. With five seeds and three budgets, **720 prediction checkpoints** cross nine backbones. All comparisons and failures are retained. An observed negative or null result does not trigger another external hyperparameter search, exclusion or extra seed chosen by outcome.

## Replication, endpoint and analysis

Freeze acquisition seeds **0,1,2,3,4** for every run. The completed development studies already used five seeds, and their policy effects were tiny relative to conditional uncertainty and the zero-effect comparator. Five seeds describe acquisition/initialization variability at the fixed split; adding seeds cannot repair missing biological replication or source/model bias. A single worker and bounded local CPU/memory constrain the final replay. Retain per-seed differences and Monte Carlo variability rather than treating 655 query-seed pairs as independent biological units. There is no outcome-dependent stopping or claim of power to detect the dossier's planning target of 10%.

The **primary contrast** is main `bias_aware` versus `worst_query`, sharing **ridge_cv**. The endpoint is mean full aligned-gene control-relative squared error, integrated by the normalized trapezoidal area over 128/256/512. Lower is better; negative paired differences favor the main extension. Area below the first budget is not observed. Mean-query and all other policies/backbones are prespecified secondary comparisons, not replacements for an unfavorable primary result. Report each direction separately and every budget, absolute/relative paired changes, zero/source-copy performance, noise-subtracted errors without clipping, and actual costs. Do not pool two reused directions into a two-replicate biological test or claim multiplicity-adjusted discoveries from descriptive secondary rankings.

Average acquisition seeds within each query before the descriptive query bootstrap. Execute the [paired assessment protocol](assessment-uncertainty-protocol.md), with 2,000 draws and seed 20261022, for the main extension against worst-query and mean-query in each unmodified direction. Report separate conditional query, fixed-query IID cell, guide/batch-stratified cell and shared technical-batch reweighting scopes. Reuse each control resample/weight across all queries. Record missing metadata and singleton strata; observed technical batches are not donors. Bands are not a calibrated joint biological confidence interval and do not include adaptive source/acquisition uncertainty.

Execute [source-half sensitivity](source-sensitivity-protocol.md) in all six runs. Report conditional ridge displacement, selected penalties, support disagreement and odd source counts; all external source counts should be even. This refits predictors with fixed paid ledgers, not acquisition policies or neural networks. Half agreement and the source signal/noise warning remain heuristic, particularly given the controlled study's demonstrated false population support under noise.

Retain response-specific/centered errors, weak/strong public-source strata, per-query residuals, predictor-only risk-retention curves, allocation/depth/control decisions, source warnings and assessment reliability/noise floors. Real-data Gaussian interval fields are compatibility diagnostics against noisy contrasts, not measured coverage of unknown population effects. Known-truth coverage remains a separate controlled-simulation result. Preserve the full ablation/permutation tables and compare absolute effects with response specificity because common errors can cancel after centering.

## Joint freeze, execution and recovery

`configs/external-evaluation-v1.json` contains every complete run definition. `external` loads and hashes all definitions and copies the protocol, method/uncertainty specifications, selection record, canonical audit, development accounting and dated declaration before acquiring anything. All six runs set `defer_assessment=true`. Acquisition executes sequentially with `OPENBLAS_NUM_THREADS=1`, using one worker and ignored run/data directories. No external scorer opens during these stages.

After all acquisitions, authenticate every prediction artifact/index and complete paid-ledger prefix, require absence of any scorer access/output, and archive each acquisition manifest. Write the joint prediction gate only when the full declared set is frozen. Before scoring, reauthenticate every peer's artifacts; before each individual scorer opens, check all peer indexes, archived acquisition fields, source/config hashes and declared evidence again. Episode, development-resource and identifier bindings are immutable through scoring. This is a cooperative runner boundary against accidental leakage/corruption, not a hostile filesystem sandbox.

Only then score the six already-frozen runs, with no acquisition or refitting between scores. If scoring is interrupted, `score-external` rechecks the joint freeze and skips already-complete peers. It cannot silently restart a partial acquisition or replace a frozen run. Observation timeouts require polling the same live process; they do not authorize restarting. Keep exact code/config/data/split/prediction/ledger hashes, acquisition/scoring access records and measured resources. A source edit during acquisition/refitting rejects scoring. Report any genuine failure without weakening the declared task.

```sh
uv run --locked mlresearch external configs/external-evaluation-v1.json
# Only for a confirmed interrupted scoring phase with the joint gate already present:
uv run --locked mlresearch score-external runs/external-evaluation-v1
```

On PowerShell, set `$env:OPENBLAS_NUM_THREADS='1'` before execution. On a POSIX shell, prefix the command with `OPENBLAS_NUM_THREADS=1`. Raw/prepared expression and large prediction arrays remain ignored. Retain manageable compressed metrics, scientific plots, configuration/manifests, ledgers, diagnostic tables, method failures and an evidence-to-claim report. Completion remains governed by every requirement of the full objective.
