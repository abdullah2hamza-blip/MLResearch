# MLResearch

A technical report, locked Python/uv package and computational study of budgeted cross-context
perturbation prediction: joint allocation of calibration identities, cell depth
and shared controls under sealed recipient queries.

The [manuscript and supplement](output/pdf/joint-acquisition-study.pdf) evaluate
a fixed RBF discrepancy-variance augmentation of worst-query acquisition. The
original frozen K562/RPE1 comparison found no demonstrated benefit. The later
split/rank/budget study shows sensitivity, including one favorable forward split;
all eight cells and both reference rules are retained. This is a conditional
computational evaluation, with no claim of biological transportability.

The [publication guide](docs/publication-guide.md) explains the editable sources,
shareable code/evidence archive, lightweight figure/table regeneration, full
replay, licensing and submission steps. The versioned [v0.2.1 artifact release](https://github.com/abdullah2hamza-blip/MLResearch/releases/tag/v0.2.1)
provides the paper, editable sources and retained code/evidence. Hosting is not
independent peer review or journal acceptance; no DOI is assigned.

The artifact release preserves numerical software version 0.2.0 and its recorded
scientific snapshots. It updates disclosure and distribution materials without
changing the scientific method or retained results. The [Kaggle research bundle](https://www.kaggle.com/datasets/abdullah2hamza/joint-acquisition-perturbation-prediction)
and [executable study writeup](https://www.kaggle.com/code/abdullah2hamza/joint-acquisition-saved-output-reanalysis)
provide the manuscript, implementation, configurations, evidence and a saved-output
reanalysis. Use their release bindings rather than assuming that a hosting date
identifies an original experiment. The [release follow-up checklist](docs/public-release-followup-20261029.md)
separates source preparation from verified publication.

The [October 28 release review](docs/release-review-v2.md) records the fresh
manuscript/code review and artifact verification before the subsequent
[public-release workflow](docs/public-release-checklist.md).

The [historical research report](docs/research-report.md) preserves the original
study and does not replace the later PI review and robustness results.

- [External results and standalone figures](docs/external-evaluation-findings.md)
- [Secondary cost, ranking and interval checks](docs/secondary-supplement-findings.md)
- [Methods and assumptions](docs/implemented-methods.md)
- [Data dictionary and provenance](docs/data-dictionary.md)
- [Reproduction workflow](docs/external-reproduction.md)
- [Implementation guide](docs/implementation-guide.md) and [milestone ledger](docs/implementation-status.md)
- [Original research dossier](docs/README.md)
- [PI review and responses](docs/publication-review-response.md)
- [Fresh scientific review](docs/release-scientific-review-v2.md)
- [Claim-to-evidence map](docs/claim-evidence-public-release.md)
- [Kaggle saved-result reanalysis](docs/kaggle-reproduction.md)
- [MIT software license](LICENSE) and [CC BY 4.0 manuscript terms](paper/LICENSE)

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

If Python discovery resolves to an unusable Windows Store execution alias,
pass the installed Python 3.12 interpreter explicitly, for example
`uv sync --locked --group dev --python C:/path/to/Python312/python.exe`.

## Verification

```sh
uv run --locked python -m pytest --basetemp .cache/pytest
uv run --locked ruff check src tests scripts notebooks
uv run --locked ruff format --check src tests scripts notebooks
uv run --locked python -m mypy src/mlresearch
```

The fast offline workflow runs on Windows and Ubuntu. Full-data experiments are
separate: the retained study includes 70 controlled simulation cases,
five-seed development selection and six jointly frozen external runs with nine
prediction backbones and 720 checkpoints. Conditional resampling, technical
batches and reused transfer directions are not independent biological evidence.

## AI assistance

Artificial intelligence (AI) tools were used for manuscript editing and code preparation.

OpenAI Codex (OpenAI) assisted with research planning, literature review and experimental design, code preparation, statistical analysis and interpretation, figure and table preparation, manuscript drafting and revision, internal review, and release preparation. These AI-assisted reviews were internal quality checks, not independent human peer review. The human author retains responsibility for the final work.

Tool/provider and scope details are recorded in [the assistance record](docs/ai-assistance.md).
