# Reproducing the secondary supplement

Use the locked Python 3.12 environment and one BLAS thread as in the [external reproduction guide](external-reproduction.md). Preserve existing outputs and use fresh paths. These analyses were declared after primary scoring; rerunning them does not create a new confirmatory test. The [findings](secondary-supplement-findings.md) state task, cost, replication and uncertainty qualifications.

The following commands assume a clean checkout in which the original controlled study and the six-run external suite have been regenerated at their configured `runs/` paths. The implementation guide supplies the controlled-study commands. A fresh external reproduction can instead supply its suite path to `--suite`/`--external-suite`. Analysis helpers use manifest source/target contexts rather than inferring direction from folder names. Retained originals under `docs/results` are read-only references; use `runs/reproduced-secondary-v1` below for new outputs.

```sh
uv run --locked mlresearch study configs/study-setup-cost-0-v1.json
uv run --locked mlresearch study configs/study-setup-cost-16-v1.json
uv run --locked mlresearch study configs/study-setup-cost-64-v1.json
uv run --locked python docs/results/controlled-study-v1/retention-analysis.py runs/setup-cost-0-v1 runs/reproduced-secondary-v1/setup-cost-0
uv run --locked python docs/results/controlled-study-v1/retention-analysis.py runs/setup-cost-16-v1 runs/reproduced-secondary-v1/setup-cost-16
uv run --locked python docs/results/controlled-study-v1/retention-analysis.py runs/setup-cost-64-v1 runs/reproduced-secondary-v1/setup-cost-64
uv run --locked python scripts/direct-measurement-reference.py --suite runs/external-evaluation-v1 --output runs/reproduced-direct-query-v1 --retained runs/reproduced-secondary-v1/direct-query
uv run --locked python scripts/plot-secondary-allocation.py --supplement runs/reproduced-secondary-v1 --primary docs/results/external-evaluation-v1 --output runs/reproduced-secondary-v1/allocation-analysis
uv run --locked python scripts/audit-count-interface.py --suite runs/external-evaluation-v1 --output runs/reproduced-count-interface.json
```

Setup costs use the frozen new worlds 171–175 and budgets 512/768/1,024. All 30 cases should complete; hypothetical prices alter affordable inventory. The direct reference writes predictions before opening its scorer and independently recomputes cell membership and charged costs. Its labels never enter the primary task. Reporting can use the retained original primary tables above; to analyze a new primary reproduction, substitute its completed report bundle.

Authenticate the completed external/controlled predictions and compute both coordinate/interval metrics and distance retention. Then compute actual within-gene perturbation ranks and synthesize world-level tables:

```sh
uv run --locked python scripts/secondary-frozen-diagnostics.py --external-suite runs/external-evaluation-v1 --controlled-study runs/controlled-study-v1 --output runs/reproduced-secondary-v1/frozen-diagnostics-complete
uv run --locked python scripts/ranking-diagnostics.py --diagnostics runs/reproduced-secondary-v1/frozen-diagnostics-complete --output runs/reproduced-secondary-v1/ranking
uv run --locked python scripts/summarize-secondary-diagnostics.py --supplement runs/reproduced-secondary-v1 --primary docs/results/external-evaluation-v1 --controlled docs/results/controlled-study-v1 --development docs/results/frangieh-integrated-v1/predictor-areas.csv --output runs/reproduced-secondary-v1/diagnostic-analysis
uv run --locked python scripts/plot-secondary-diagnostics.py --analysis runs/reproduced-secondary-v1/diagnostic-analysis --primary docs/results/external-evaluation-v1 --output runs/reproduced-secondary-v1/diagnostic-analysis/figures
```

The synthesis authenticates retained legacy metric bytes and compares all 15,420 fixed-ridge 95% fields. When reproducing changed provenance paths rather than the historical run names, use matching retained report/controlled bundles from that reproduction. Do not mix an unrelated regenerated run with historical byte hashes. Numerical results should agree under the pinned environment; provenance timestamps and process resources will differ.

Only after a **confirmed interruption**, ranking supports `--resume` with the identical source, input summary and output path. It authenticates every completed shard and rejects changed inputs; complete-output resume is idempotent. Frozen diagnostics reject existing outputs. The historical recovery used `--reuse-external-diagnostics` only for the separately preserved, authenticated 6,480-row external pass after a controlled-reader error. A fresh full reproduction needs no recovery option. The original failed source, error and completed rows remain evidence, not a hidden overwritten attempt.

For complete raw-to-prepared reproduction, fetch and prepare Frangieh as well as both external inputs, then run:

```sh
uv run --locked python scripts/check-full-preparation-reproduction.py --directory .cache/reproduced-full-preparation-v1 --evidence runs/reproduced-full-preparation-v1.json
```

This creates another approximately 9.6 GB of ignored matrices, verifies all metadata and every output-file byte, and archives code/config/manifests without expression matrices. It preserves the originals. The published execution verified all 2,405,927,872 values exactly. `--resume` requires identical source/config identity and authenticates finished comparisons; use it only after verifying the original process has stopped. The RPE1 IO block change is explicitly recorded. Historical preparation source hashes remain historical even when current output is exact.

The retained secondary bundle includes full CSV tables (largest about 22.3 MB), hash-bound ranking shards, compressed cell-ID ledgers and per-query metrics, and PNG/SVG/PDF figures. Raw/prepared expression and full prediction arrays stay ignored. `supplement-artifacts.json` covers all retained files except itself; `analysis-helpers.zip` preserves the actual supplementary scripts. Check the [retention verification](evidence/secondary-retention-verification-v1.json) before interpreting or modifying a copy. Reports record their own source/input hashes because Git environment status intentionally omits untracked files and alone cannot establish that a script was committed when run.
