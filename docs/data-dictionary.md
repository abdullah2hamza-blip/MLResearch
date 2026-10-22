# Data and artifact dictionary

This describes the actual retained inputs and executable artifacts, not an assumed universal H5AD schema. [Prepared provenance](evidence/prepared-input-provenance.json), the raw audits and [external compatibility](external-data-compatibility.md) preserve release attribution, checksums and missingness. The pinned registry is `src/mlresearch/datasets.json`; raw files and prepared expression remain ignored.

## Input fields and preparation

| Meaning | Frangieh RNA | Replogle K562-essential/RPE1 |
| --- | --- | --- |
| Cell identifier | Original `obs` index | Original `obs` index |
| Gene identifier used for matrix alignment | Original `var` index | Original `var` index; independently checked against `var/ensembl_id` |
| Intervention label | `obs/perturbation` | `obs/perturbation` |
| Canonical target annotation | Original labels retained; no universal alias claim | `obs/gene_id`; all 525 eligible targets have unique nonempty matching IDs |
| Guide label | `obs/guide_id`, original string retained | `obs/guide_id`, original paired-guide combination retained |
| Context | `obs/perturbation_2`: Control, IFNγ, Co-culture | `obs/cell_line`: K562 or RPE1 |
| Technical batch | Not supplied to preparation; empty unavailable sentinel | `obs/batch`, original string retained; 48/56 observed labels |
| Control label | `control` | `control` |
| Metadata restriction | `MOI=1` | Metadata-overlapping 525 targets with at least 96 cells each, plus controls |
| Donor / independent biological replicate / per-cell knockdown | Unavailable for the declared analysis | Unavailable; a sequencing batch is not inferred to be a donor |
| Retained matrix | 64,294 × 23,712 | 50,912 × 8,563 K562; 50,912 × 8,749 RPE1 |

Three RPE1 target labels with missing canonical IDs occur outside the eligible overlap. They are not collapsed into one empty canonical identity. The [canonical freeze](evidence/external-canonical-identifiers-v1.json) preserves all eligible target→Ensembl and expression-gene→Ensembl mappings, original guides, raw hashes and query/candidate canonical sets. It does not resolve arbitrary aliases or reconcile external annotation versions.

All declared inputs use `input_scale=counts`. The prepared float32 value is `log1p(10000 * count / sum_of_counts_over_all_released_input_genes)`. Nonpositive library totals, negative/nonfinite values and inconsistent count declarations are checked by the loader/preparer. Gene intersection occurs later; its columns do not redefine the normalization denominator. The result is a transformed-expression value, not a raw-count fold change. Different released panels retain different denominators.

Metadata caps use seeded identity sampling, independent of response magnitude: at most 96 cells per intervention/context and 512 controls/context. Original annotations and the retained cell set are deterministic at seed 20261021. RPE1's original row block 128 versus reproduction config 969 changes IO batching only; complete scientific selection/normalization settings are preserved. The [post-scoring audit](evidence/prepared-row-audit-v1.json) verifies all retained metadata and 20 full-gene expression rows per input, with explicit bounded expression scope.

## Prepared directory

| Artifact / field | Meaning |
| --- | --- |
| `values.npy` | Memory-mapped float32 cell × complete released-gene matrix; no full dense in-memory copy required. |
| `metadata.json: genes` | Ordered original expression-gene axis. |
| `original_cell_ids` | Original release barcodes, in prepared row order. |
| `cell_ids` | Original barcode prefixed by the first 16 hexadecimal characters of raw-input SHA-256; cross-file identity namespace. |
| `interventions`, `contexts`, `guides`, `batches` | One original annotation string per retained row; unavailable batch remains unavailable. |
| `control_labels`, `original_column_mapping` | Declared control strings and exact input-column mapping. |
| `condition_inventory`, eligibility/retention counts | Metadata-based available/retained counts and selection accounting. |
| `manifest.json` | Validated preparation config, raw SHA-256, metadata/values hashes, source environment and completed state. Historical source hashes remain intact. |

## Episode information boundary

Frangieh development uses Control→IFNγ, 205 eligible identities, 154 calibration candidates and 51 queries. The external pair uses both K562/RPE1 directions, 525 identities, 394 candidates, 131 queries and 7,226 aligned genes. All guides of one eligible gene identity follow that identity's split.

| Artifact / field | Permitted role and meaning |
| --- | --- |
| `public.json` | Ordered intervention/gene axes and fixed query/candidate identities; public source-query access declaration. No recipient expression. |
| `source.npz: effects` | Public source treatment-minus-control normalized-log means for every identity, including queries. |
| `per_cell_variance`, `mean_variance` | Source scalar variance summaries used by the declared model/diagnostics, not known population variances. |
| `half_difference` | Joint source treatment/control half-contrast difference, including shared controls. Sensitivity input, not a calibrated uncertainty bound. |
| `private-banks.json: acquisition_rows/cell_ids` | Finite eligible recipient calibration/control pool only; queries omitted. |
| `assessment_rows/cell_ids` | Independent reserved recipient assessment banks. Only query identities plus independent controls are opened by the scorer; candidate assessment cells stay unused. |
| `source_cell_ids`, `source_counts` | Public source resource accounting; all external source counts are 96 per intervention and 512 controls. |
| `target_columns`, `target_prepared` | Exact recipient aligned-column mapping and relocatable prepared path. Private runtime plumbing, never a policy argument. |
| Episode manifest | Split/preparation configuration, inventories, environment and opaque hashes of every episode file. |

Recipient candidate pools contain 64 acquisition cells per identity; queries have 32 scorer-only cells. Controls have disjoint 256 acquisition/256 assessment cells. Source, acquisition and assessment IDs cannot overlap within an episode. Directions reuse observations in different roles and do not create independent biological replications.

## Acquisition, predictions and analysis

| Artifact / quantity | Meaning and units |
| --- | --- |
| `ledger.jsonl` | Append-only events: action, newly revealed cell IDs, event cost/cumulative spend, sequence and hash chain. |
| Budget / `spent` | Abstract recipient units: one per cell, four per newly opened intervention. Pilot/validation/control observations are paid. Each counterfactual policy pays separately. |
| Development exposure | Unique observed recipient union across development runs: 6,428 units, distinct from each policy ledger and later incremental budgets. |
| `allocations.csv` | Per seed/policy/budget spend, control/perturbed cells, opened interventions, selected penalty and cumulative elapsed runtime. |
| `budget-N.npz` | Frozen query × gene predictions for all configured backbones; support/source/validation/transfer diagnostics. Non-pickled JSON stores neural training details. |
| `prediction-index.json` | Checkpoint path/hash, policy/seed/budget, spend and exact ledger-prefix hash/event count. Historical indexes lacking prefixes are explicitly qualified. |
| Joint prediction gate | Six frozen acquisition-manifest/index bindings authenticated before the first external scorer opens. |
| `assessment-access.json` | Open time, frozen prediction/gate binding, exact scorer cell IDs and fixed scorer resource count. |
| `metrics.csv` / retained `.gz` | One row per policy × seed × budget × backbone × query. Full-gene MSE, scalar assessment noise estimate, centered specificity, predictor-use costs, public-source stratum and qualified diagnostics. |
| `specificity_mse` | Gene-wise effects centered across query identities before error calculation; common across-query components cancel. It is not absolute-effect error or a causal ranking guarantee. |
| `identified`, ideal variance | Unregularized numerical query-span support conditional on estimated source coordinates; unsupported directions have infinite variance. |
| `source_unstable`, `deferral_recommended` | Heuristic source-noise/support warnings; no calibrated selective-risk guarantee. |
| Gaussian fields | Ideal fixed-ridge interval width and compatibility against noisy real contrasts; known-truth simulation coverage is separate. |
| Normalized area | Trapezoidal MSE integral over the declared budget grid divided by grid width; excludes unobserved cost below the first budget. |
| Conditional query bands | Seeds averaged within query before resampling whole identities; fixed source/split/scoring bank. |
| Cell / batch analyses | Separate fixed-query measurement resampling and technical-batch weight sensitivity, retaining shared controls and singleton limitations. No biological CI claim. |
| Runtime / memory | Elapsed versus process CPU reported separately where measured; memory peak has process-lifetime scope. No claim that event gaps equal CPU work. |

The [implementation guide](implementation-guide.md), [reproduction workflow](external-reproduction.md) and [research report](research-report.md) connect these schemas to commands, exact scientific findings and limitations. Retained artifact manifests contain byte checksums; raw expression and large predictions are regenerated from pinned inputs rather than stored in Git.
