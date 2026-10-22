# Implementation guide

## Working environment and checks

Use Python 3.12 and uv. From the repository root:

```sh
uv sync --locked --group dev
uv run --locked mlresearch --help
uv run --locked mlresearch resources
uv run --locked mlresearch provenance --output .cache/environment.json
python -c "from pathlib import Path; Path('.cache').mkdir(exist_ok=True)"
uv run --locked python -m pytest --basetemp .cache/pytest
uv run --locked ruff check src tests scripts
uv run --locked ruff format --check src tests scripts
uv run --locked python -m mypy src/mlresearch
```

The GitHub workflow defines these fast offline checks for Python 3.12 on Windows and Linux. Local Windows checks are run during implementation; defining the workflow does not establish a successful hosted CI run.

## Pinned data and provenance

```sh
uv run --locked mlresearch data list
uv run --locked mlresearch data fetch frangieh-rna
uv run --locked mlresearch data audit data/raw/FrangiehIzar2021_RNA.h5ad --output runs/reproduced-frangieh-audit.json
uv run --locked mlresearch data counts configs/prepare-frangieh.json --output runs/reproduced-frangieh-eligibility.json
```

Downloads are incoming public files from the pinned registry. A `.part` file can be resumed; a server that ignores byte ranges causes a safe restart rather than appending incompatible content. A final filename is accepted only after exact byte-size and published MD5 verification. A provenance sidecar also records SHA-256, the release DOI, and license declaration. `--restart` requests a fresh partial download when necessary. Existing final files are verified again before use.

Raw datasets and generated replay arrays live under ignored `data/`. Keep source configs, small audit summaries, and eventual aggregate research outputs in version control. License attribution and original-study provenance still matter even when a registry's license field is available.

## Bounded-memory preparation

```sh
uv run --locked mlresearch data prepare configs/prepare-frangieh.json
```

This command is a substantial local preprocessing job, not a smoke test. The first Frangieh configuration explicitly selects cells with `MOI=1`, retains up to 96 cells per intervention/context and 512 controls/context, and keeps the full gene axis. Capping uses seeded cell-identity sampling and metadata counts; it never filters on response magnitude. Original cell and guide identifiers are retained alongside namespaced cell IDs.

`input_scale` must be declared. `counts` validates the matrix and computes `log1p(10000 * count / full_gene_library_total)`. This changes the target to a difference of normalized-log means, not a log fold change of raw means. `as_provided` leaves the supplied expression transformation unchanged. Integer-like samples alone do not establish raw-count provenance.

Dense and CSR inputs stream row blocks. CSC inputs stream column blocks and compute full-gene library totals in a first pass. The output is a float32 memory-mapped NPY matrix plus metadata and a final manifest containing input/output/config/source hashes. It avoids loading a full dense matrix or all sparse nonzero arrays at once. The Frangieh gene axis has 23,712 entries; a prepared artifact can still require several GB of disk space.

A preparation directory is never silently overwritten. An interrupted run retains `state=preparing`; it cannot be mistaken for a complete artifact. Diagnose failures before choosing a fresh output path. Reproduction of the scientific result will require later episode and run manifests in addition to this preprocessing manifest.

## Implemented statistical and acquisition primitives

`mlresearch.linear` implements the classical covariance matrix for effects sharing a control pool, nuisance-baseline information, generalized least squares, and numerical row-space diagnostics. Unsupported query directions receive infinite ideal-model variance before regularization. The formulas assume a correct linear map and known variances; they do not supply a general biological or adaptive-inference guarantee.

`mlresearch.acquisition` accepts calibration/control pools only. Query outcomes are rejected at construction and query purchases are forbidden. It tracks unused cell identities, charges new-intervention setup and per-cell/control costs, and records a deterministic hash-chained ledger. Purchases return copies of paid observations. Policies must receive only public state and paid observations; never pass them a raw dataset or scorer object. The service is an experimental API boundary, not a sandbox for malicious Python introspection or arbitrary filesystem access.

Assessment-bank independence is checked separately. A hash chain detects accidental ledger edits but does not authenticate an adversary who can rewrite both records and hashes. Run manifests and scorer validation provide additional experiment-integrity checks alongside the completed joint-freeze and scoring pipeline.

## Episodes and replay

```sh
uv run --locked mlresearch demo --directory runs/offline-demo --five-seeds
uv run --locked mlresearch report runs/offline-demo/experiment --output runs/offline-demo/report
uv run --locked mlresearch episode configs/episode-frangieh-development.json
uv run --locked mlresearch run configs/run-frangieh-development.json
uv run --locked mlresearch report runs/frangieh-development-v1 --output runs/frangieh-development-report
```

The offline example generates independent source and recipient cells, freezes a gene-level query split, executes three policies across five acquisition seeds, and scores only after predictions are closed. It needs no network or raw dataset. Fresh directories are required; completed or partial runs are never silently overwritten. Real-data commands require the prepared inputs. The [pilot protocol](pilot-protocol.md) specifies the development comparison and its limitations.

An episode freezes exact gene alignment, eligible query/calibration identities, randomized finite acquisition banks, independent assessment cells/controls and public source summaries. Policies receive a `PublicEpisode` and paid statistics, not the recipient matrix, private bank map, or scorer. The runner's final scoring phase opens only scorer banks. A regression test changes sealed outcomes and confirms unchanged ledgers and predictions. Guide IDs cannot map to two different target labels.

Run directories retain `manifest.json`, `code.zip` (exact package contents and dependency specifications), source coordinates, per-seed/policy ledgers and prediction arrays, a hashed prediction index, allocation tables, scorer access records, assessment arrays, and per-query metrics. Code changes during acquisition cause scoring to be refused. Do not edit `src/mlresearch` while an experiment is acquiring. Reports produce CSV tables, PNG/SVG figures and a Markdown interpretation. Their bootstrap intervals are conditional descriptive summaries; read [implemented methods](implemented-methods.md) before interpreting them.

The baseline suite and fixed-kernel discrepancy surrogate are executable. `ridge_cv` adds stronger shrinkage using only paid leave-one-intervention-out labels and a shared-control covariance correction; its grid is configurable. Fixed-ridge initial results remain preserved. The [first synthetic pilot](results/synthetic-pilot-v1/results.md) is actual evidence from a linear simulation, with the extension worse than its classical comparator in that setting. It does not establish benefit or failure across mechanisms. The local residual comparator is an adaptation, not an original PerturbMap reproduction.

Reports also retain compressed per-query metrics, the input run manifest, allocation and prediction indexes, the run's source snapshot when available, and a separate analysis source snapshot. `retained-artifacts.json` records checksums. To independently reanalyze a retained result, decompress `metrics.csv.gz` to `metrics.csv` in a new directory, copy `run-manifest.json` there as `manifest.json`, then invoke `report` on that directory. Acquisition/prediction reruns additionally require the pinned prepared data and frozen episode. Raw cells are not included in the retained report bundle.

For bounded external preparation, download both pinned Replogle files and run `configs/prepare-k562.json` and `configs/prepare-rpe1.json` through `data prepare`. These configs retain the 525 exact target identities having at least 96 cells in both files, plus controls. This metadata-only restriction is recorded in `docs/evidence/replogle-overlap.json`. The RPE1 row block follows its HDF5 chunk height to reduce repeated decompression. Preparation remains a substantial CPU/disk job.

## Executed study and limitations

The controlled grid, development tuning, integrated comparator check and six-run frozen external evaluation have executed. The [research report](research-report.md) and [external findings](external-evaluation-findings.md) retain the negative primary result, all declared controls/ablations and inference limits. The [data dictionary](data-dictionary.md) describes actual fields and artifact semantics. See [milestone status](implementation-status.md) for the final publication/completion audit.

## Integrated transfer and uncertainty

A run config may set `transfer` to an object of [declared reconstruction settings](transfer-comparator-protocol.md); `{}` selects those defaults. This enables `recipient_local_lowrank` and `perturbmap_reconstruction` alongside the seven earlier predictors, all using the same paid ledger. Omit the option or set it to null for legacy behavior. `source_sensitivity: true` adds [joint source-half diagnostics](source-sensitivity-protocol.md) for ridge predictors without purchasing more cells or changing acquisitions. The [integrated development protocol](integrated-development-protocol.md) records the completed fidelity check.

```sh
uv run --locked mlresearch run configs/run-frangieh-integrated-v1.json
uv run --locked mlresearch uncertainty runs/frangieh-integrated-v1 --output runs/frangieh-integrated-uncertainty.json --backbone ridge_cv
uv run --locked mlresearch account-development --output runs/development-resource-next.json runs/frangieh-development-v1 runs/frangieh-development-v2 runs/frangieh-tuning-v1 runs/frangieh-integrated-v1
```

Analysis requires complete runs, the original frozen episode and verified prepared inputs. Every output must use a fresh path. Query bootstrap, cell resampling and batch sensitivity have separate conditional scopes; none is biological replication. New checkpoint indexes authenticate ledger prefixes as well as predictions. Historical runs retain their original indexes and are reconciled against checkpoint spends without claiming missing historical hashes.

## Joint external prediction freeze

`defer_assessment: true` makes `run` stop at authenticated frozen predictions without opening scorer cells. The `external` command loads every full run definition, freezes supporting evidence and acquires sequentially. Only after all declared predictions and ledger prefixes authenticate does it archive acquisition manifests and write a joint gate. Every peer artifact is checked before the first scorer; immutable acquisition fields and peer indexes are checked before each subsequent scorer. The [external protocol](external-evaluation-protocol.md) fixes both directions, all ablations, four permutation controls, five seeds and the 6,428-unit development cost.

```sh
uv run --locked mlresearch external configs/external-evaluation-v1.json
uv run --locked mlresearch score-external runs/external-evaluation-v1
```

The second command is recovery for a confirmed interrupted scoring phase after the joint gate exists; it never repeats acquisition or refits predictors. A completed suite is validated and returned without rescoring. Preserve incomplete acquisitions and inspect their actual process handle before considering any restart. Settings/source/evidence edits invalidate a frozen suite. Use one worker and set `OPENBLAS_NUM_THREADS=1`; the CLI never buys cloud compute. Scoring and report input stream metric rows to keep large external panels within bounded local memory.

For a clean checkout that rebuilds episode manifests, follow [the external reproduction workflow](external-reproduction.md). It creates a newly bound identifier audit and fresh paths/declaration while preserving every published scientific setting, rather than overwriting historical provenance.
