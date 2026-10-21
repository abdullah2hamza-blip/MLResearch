# MLResearch

A Python workspace for machine learning research, scaffolded with `uv init`.

## Getting started

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```sh
uv sync --locked
uv run mlresearch
```

The starter command prints `Hello from mlresearch!`.

## Development

- Python 3.12 or newer is required; `.python-version` pins the default to 3.12.
- Application code lives in `src/mlresearch/`.
- Add dependencies with `uv add <package>`.
- Add development tools with `uv add --dev <package>`.
- Commit `uv.lock` when dependencies change to keep environments reproducible.
