# MLResearch

A locked Python/uv package and computational study of budgeted cross-context
perturbation prediction: joint allocation of calibration identities, cell depth
and shared controls under sealed recipient queries.

The [research report](docs/research-report.md) retains the completed experiments
and negative primary result. The primary test found no demonstrated improvement
over classical worst-query acquisition in either frozen K562/RPE1 direction.

- [External results and standalone figures](docs/external-evaluation-findings.md)
- [Secondary cost, ranking and interval checks](docs/secondary-supplement-findings.md)
- [Methods and assumptions](docs/implemented-methods.md)
- [Data dictionary and provenance](docs/data-dictionary.md)
- [Reproduction workflow](docs/external-reproduction.md)
- [Implementation guide](docs/implementation-guide.md) and [milestone ledger](docs/implementation-status.md)
- [Original research dossier](docs/README.md)

## Quick start

Use Python 3.12 and [uv](https://docs.astral.sh/uv/getting-started/installation/).
The small offline example needs no dataset download:

```sh
uv sync --locked --group dev
uv run --locked mlresearch --help
uv run --locked mlresearch demo --directory runs/offline-demo --five-seeds
uv run --locked mlresearch report runs/offline-demo/experiment --output runs/offline-demo/report
```

Use fresh output directories. On PowerShell, set
`$env:OPENBLAS_NUM_THREADS='1'` before numerical commands. Large raw/prepared
matrices, environments, caches and prediction arrays remain ignored.

## Verification

```sh
uv run --locked python -m pytest --basetemp .cache/pytest
uv run --locked ruff check src tests scripts
uv run --locked ruff format --check src tests scripts
uv run --locked python -m mypy src/mlresearch
```

The fast offline workflow runs on Windows and Ubuntu. Full-data experiments are
separate: the retained study includes 70 controlled simulation cases,
five-seed development selection and six jointly frozen external runs with nine
prediction backbones and 720 checkpoints. Conditional resampling, technical
batches and reused transfer directions are not independent biological evidence.
