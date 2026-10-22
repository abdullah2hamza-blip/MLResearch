# Reproducing the frozen external study

Use a clean checkout, Python 3.12 and the locked uv environment. This reproduces the published released-data comparison; it is not a new untouched external dataset or biological replication. The [frozen protocol](external-evaluation-protocol.md) defines the scientific settings. Raw/prepared matrices, environments and large predictions remain ignored.

First inspect available memory/disk and use one worker. Keep package sources and declared evidence unchanged during acquisition/scoring. Set `OPENBLAS_NUM_THREADS=1` in the shell; in PowerShell use `$env:OPENBLAS_NUM_THREADS='1'`. The complete six-run suite has 720 checkpoints and produces roughly 25 GB of prediction files, in addition to raw/prepared data and reports. Actual resource fields are measured per process, with explicit lifetime-peak scope.

```sh
uv sync --locked --group dev
uv run --locked mlresearch resources
uv run --locked mlresearch data fetch replogle-k562
uv run --locked mlresearch data fetch replogle-rpe1
uv run --locked mlresearch data prepare configs/prepare-k562.json
uv run --locked mlresearch data prepare configs/prepare-rpe1.json
uv run --locked mlresearch episode configs/episode-k562-to-rpe1.json
uv run --locked mlresearch episode configs/episode-rpe1-to-k562.json
```

All output directories must be fresh. Downloads verify the pinned registry checksums, and preparation preserves the complete per-file gene panel before intersection. Rebuilding the episodes changes their provenance timestamps/environment hashes even when the deterministic split and numeric inputs agree. Therefore, generate a new canonical annotation audit bound to the newly built manifests rather than overwriting the historical audit:

```sh
uv run --locked python scripts/audit-external-identifiers.py --output runs/reproduced-identifiers.json
uv run --locked python scripts/freeze-external-reproduction.py --identifiers runs/reproduced-identifiers.json --directory runs/reproduction-v1
uv run --locked mlresearch external runs/reproduction-v1/configuration.json
```

The helper requires the published template's exact configuration hash. It validates pinned raw inputs, canonical identities, the original query/calibration split, metadata filters, cell caps, expression transformation and every model/acquisition/cost setting. It changes only output/provenance paths and descriptive labels, and writes a new declaration. Altering a budget or other template setting is rejected. `--forward` and `--reverse` can name rebuilt episode directories if the defaults already contain older artifacts. Preserve existing artifacts; do not reset or overwrite them.

IO batching is recorded separately from scientific selection/transformation. The historical RPE1 preparation used row blocks of 128 while the checked-in reproduction config uses its HDF5 chunk height, 969. This changes reading batches, not which cells/genes are selected or the per-cell full-panel normalization formula. The helper records such IO differences and still rejects changed scientific preparation settings. A separate post-scoring raw-row audit verifies complete retained metadata and a bounded sample of full-gene transformations; it does not claim to recompute every matrix entry.

`external` acquires all six runs before any scorer opens. Confirm the specific live process handle after an observation timeout; never infer termination from a state file alone. If a confirmed interruption occurs during scoring and the joint gate exists, resume with:

```sh
uv run --locked mlresearch score-external runs/reproduction-v1/suite
```

This does not repeat acquisition or refit predictors. A partial acquisition is preserved and cannot be silently resumed as a completed prediction set. The helper's declaration states that these are reused released datasets; it does not relabel a reproduction as new blinded evidence.

The generated configuration records each experiment path as `runs/reproduction-v1/experiments/run-N`. After the whole suite completes, these helpers use the declared 2,000 draws and seed 20261022 for the six reports and four paired assessment analyses. They then build the full diagnostic supplement and standalone figures:

```sh
uv run --locked python scripts/report-external-suite.py runs/reproduction-v1/suite --output runs/reproduction-reports-v1
uv run --locked python scripts/analyze-external-suite.py runs/reproduction-v1/suite --output runs/reproduction-reports-v1/supplement
uv run --locked python scripts/plot-external-results.py runs/reproduction-reports-v1 --output runs/reproduction-reports-v1/figures
uv run --locked python scripts/audit-external-completion.py runs/reproduction-v1/suite --output runs/reproduction-completion-audit.json
uv run --locked python scripts/audit-prepared-rows.py --suite runs/reproduction-v1/suite --output runs/reproduction-prepared-audit.json
```

The raw-row audit also requires the Frangieh development preparation; fetch and prepare it with `configs/prepare-frangieh.json` if reproducing that three-input check. The completion audit rechecks all prediction artifacts and ledger prefixes, independently recomputes costs and purchased-cell membership, and tests zero-weight/classical equivalence plus fixed-grid query-gene permutation invariance. The generic `report` CLI uses its historical bootstrap default seed 513; the external helper explicitly supplies the protocol's seed 20261022. The [implementation guide](implementation-guide.md) describes retained artifacts and interpretation. Absolute errors, conditional resampling and technical batch sensitivity must retain their qualifications.

The [actual rebuild check](evidence/rebuilt-external-episodes-v1.json) regenerated both real episodes into fresh directories from existing verified preparations. Every public source array, query/candidate/gene axis and private source/acquisition/assessment bank map matched exactly. A new canonical metadata audit and six-run reproduction declaration then passed; their [retained freeze evidence](evidence/rebuilt-reproduction-freeze-v1.json) preserves the regenerated paths and hashes. This verifies real episode rebuilding plus the fresh-manifest binding workflow. It is not a second raw-data preparation or an independently rerun external study. To repeat the bounded check after the original suite completes, use `scripts/check-external-episode-rebuild.py --suite <completed-suite> --directory <fresh-directory> --evidence <fresh-json>`.
