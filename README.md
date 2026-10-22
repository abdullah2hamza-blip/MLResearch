# MLResearch

A Python workspace for machine learning research, scaffolded with `uv init`.

## Research

Start with the [research dossier](docs/README.md), a literature-backed frontier
assessment and proposed project on budgeted cross-context perturbation prediction.
The research snapshot is dated October 21, 2026.

## Getting started

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```sh
uv sync --locked
uv run mlresearch --help
```

The implementation provides verified downloads, streaming preparation, frozen
episodes, paid finite-pool acquisition, transfer predictors, replay experiments,
and standalone result plots. Run a small example without downloading data:

```sh
uv run --locked mlresearch demo --directory runs/offline-demo --five-seeds
uv run --locked mlresearch report runs/offline-demo/experiment --output runs/offline-demo/report
```

See the [implementation guide](docs/implementation-guide.md)
and [current milestone status](docs/implementation-status.md). The complete
study remains in progress. The [first synthetic pilot](docs/results/synthetic-pilot-v1/results.md)
retains a negative result for the extension; it is not a completed study.

## Development

- Python 3.12 or newer is required; `.python-version` pins the default to 3.12.
- Application code lives in `src/mlresearch/`.
- Add dependencies with `uv add <package>`.
- Add development tools with `uv add --dev <package>`.
- Commit `uv.lock` when dependencies change to keep environments reproducible.
- Install development tools with `uv sync --locked --group dev`.

The [controlled simulation protocol](docs/controlled-study-protocol.md) and `configs/study-controlled-v1.json` define the larger synthetic study. Run it with `uv run mlresearch study configs/study-controlled-v1.json`; use a fresh output directory for another run. This study is separate from the still-pending external evaluation. The [risk-retention analysis correction](docs/retention-analysis-correction.md) preserves the original pilot findings while correcting their diagnostic selection rule.
