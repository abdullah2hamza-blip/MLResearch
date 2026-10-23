# Manuscript, evidence and submission package

The manuscript is **Evaluating fixed-kernel joint acquisition for cross-context perturbation prediction**, by Abdullah Hamza (Independent Researcher). The PDF includes the main article, references and technical supplement. It reports the original frozen comparison and every cell of the later split/rank/budget study, including the favorable forward split. Internal automated reviews are documented in [the response ledger](publication-review-response.md); they are not external peer review or acceptance.

## Deliverables and reader access

- `output/pdf/joint-acquisition-study.pdf`: article and supplement.
- `output/release/manuscript-source-v0.2.0.zip`: self-contained TeX sources, bibliography, vector figures, generated tables, compiled bibliography and build helper. No expression data are needed to compile it.
- `output/release/code-and-evidence-v0.2.0.zip`: original software, tests, locked environment, configurations, retained evidence, manuscript pipeline and PDF. It excludes raw/prepared expression data, large predictions, credentials, Git history and machine caches.
- `output/release/release-manifest-v0.2.0.json`: archive/PDF checksums and member inventories.

The GitHub repository is private during preparation. Deposit the code/evidence archive with the paper or in a persistent archive so readers actually receive it; a private GitHub URL alone is not an availability statement. The manuscript accurately describes the accompanying archive and does not claim a public repository or code DOI. Making the repository public would expose its existing history and requires a separate user decision. No submission or visibility change is performed by these instructions.

Original code uses [MIT](../LICENSE); the manuscript uses [CC BY 4.0](../paper/LICENSE). Third-party data retain their original terms. [CITATION.cff](../CITATION.cff) contains versioned citation metadata without an invented publication or DOI. The supplied author reports no external funding or competing interests. AI assistance is disclosed in the manuscript.

## Lightweight evidence and paper reproduction

Use Python 3.12 and the locked uv environment from the archive root. On PowerShell set `$env:OPENBLAS_NUM_THREADS='1'`; on other shells set `OPENBLAS_NUM_THREADS=1`. Use fresh output directories except for the explicit asset regeneration command.

```sh
uv sync --locked --group dev
uv run --locked python scripts/verify-publication-package.py --output .cache/publication-evidence-check.json
uv run --locked python scripts/generate-paper-assets.py --replace --robustness docs/results/publication-robustness-v1/analysis
uv run --locked python scripts/build-paper.py
```

The verifier checks retained indexes, compressed/nested payloads, manuscript evidence bindings, review audits and numerical contrasts. The figure/table generator reads authenticated small summaries; it does not need raw expression or prediction arrays. It retains exact numeric registries and hashes rather than silently editing manuscript numbers. Matplotlib figure bytes can differ with rendering environment; compare numeric tables/registries and visually inspect regenerated figures. The build helper refuses incomplete or changed generated assets.

Install [Tectonic](https://tectonic-typesetting.github.io/book/latest/getting-started/first-document.html) or a conventional pdfLaTeX/BibTeX distribution, or pass `--compiler PATH`. Tectonic downloads its TeX support bundle on first use and needs a writable standard format cache. The verified build used official Tectonic 0.15.0 with the standard version-33 TeX bundle. From an unpacked manuscript-only archive run:

```sh
python build-paper.py --source main.tex --output joint-acquisition-study.pdf
```

That archive verifies supplied asset hashes; only the complete code/evidence archive can additionally verify original evidence inputs. The source is ordinary article-class LaTeX, with no shell escape or external code execution required. A separate visual audit checks every rendered page after the final build.

## Full numerical reproduction

The original primary predictions used the frozen 0.1.0 source retained in `docs/results/external-evaluation-v1/runs/*/code.zip` (consult its actual member paths/index). The current 0.2.0 release fixes an epsilon-only transport acceptance diagnostic. Twenty affected historical reconstruction arrays equal their local bases byte-for-byte; historical scores are unchanged. Re-running current code can change embedded diagnostic fields and NPZ bytes, so do not assert byte-identical original archives across those versions. Use the historical source snapshot for strict historical reproduction and current source for the new robustness suite.

For strict primary replay without Git history, unpack the code/evidence archive into a **separate fresh directory**, then run the following Python there to overlay its authenticated historical source snapshot. The ZIP stores package members as `mlresearch/...`; the project expects them under `src/mlresearch/...`:

```python
from pathlib import Path
from zipfile import ZipFile
snapshot = Path("docs/results/external-evaluation-v1/runs/external-k562-to-rpe1-v1/code.zip")
with ZipFile(snapshot) as archive:
    for name in archive.namelist():
        target = Path("src") / name if name.startswith("mlresearch/") else Path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(name))
```

Run `uv sync --locked --group dev` in that separate copy, then the original replay commands below. The historical project version and lock are restored together. The three new calibration-edge tests target the 0.2.0 fix and are not historical 0.1.0 tests; keep the original replay and the current robustness/release validation in separate copies. Preserve outputs and use newly bound reproduction declarations rather than overwriting historical evidence.

Follow [original full-data reproduction](external-reproduction.md), [secondary reproduction](secondary-supplement-reproduction.md), [controlled protocol](controlled-study-protocol.md) and their source/configuration bindings. Download/preparation starts from three checksum-pinned scPerturb H5AD files. Large data and predictions are intentionally regenerated. The original six-run suite has 720 checkpoints; the later eight-run suite has 360. Together their prediction arrays occupy tens of GB beyond raw/prepared data; inspect resources and use one worker. No claim of a second complete original acquisition run is made by the independent full preprocessing check.

For the additional matrix, prepare K562/RPE1 as above and build the four `configs/episode-publication-*-seed20261023-v1.json` and `*-seed20261024-v1.json` episodes with `mlresearch episode CONFIG`. Build the original `k562-to-rpe1-v1` and `rpe1-to-k562-v1` episodes too if regenerating the overlap analysis. Then create fresh metadata-only audits:

```sh
uv run --locked python scripts/audit-external-identifiers.py --forward data/episodes/publication-k562-to-rpe1-seed20261023-v1 --reverse data/episodes/publication-rpe1-to-k562-seed20261023-v1 --output runs/reproduced-identifiers-23.json
uv run --locked python scripts/audit-external-identifiers.py --forward data/episodes/publication-k562-to-rpe1-seed20261024-v1 --reverse data/episodes/publication-rpe1-to-k562-seed20261024-v1 --output runs/reproduced-identifiers-24.json
uv run --locked python scripts/freeze-publication-reproduction.py --identifiers-23 runs/reproduced-identifiers-23.json --identifiers-24 runs/reproduced-identifiers-24.json --directory runs/publication-reproduction-v1
uv run --locked mlresearch external runs/publication-reproduction-v1/configuration.json
uv run --locked python scripts/audit-external-completion.py runs/publication-reproduction-v1/suite --output runs/publication-reproduction-audit.json
uv run --locked python scripts/analyze-publication-robustness.py --suite runs/publication-reproduction-v1/suite --configuration runs/publication-reproduction-v1/configuration.json --output runs/publication-reproduction-analysis
```

The binding helper validates scientific settings, raw/preparation provenance and canonical split membership, while allowing new output/manifests and recorded IO batching differences. It permits only the separately documented [license-file packaging addition](publication-packaging-notes.md) to the frozen project metadata; numerical source, version and locked dependencies remain exact. It does not overwrite the published declaration. Keep source/configuration/evidence unchanged from declaration through scoring. A confirmed interrupted scoring pass with an existing joint gate can use `mlresearch score-external SUITE`; an observation timeout alone is not proof that a process ended. Every run must close before new scoring; no new split is an untouched biological confirmation.

The original influence and epsilon-gate audits require the historical predictions if rerun from scratch. Their authenticated small retained reports are sufficient for the lightweight manuscript path. The new query-deletion analysis uses retained paired-query areas:

```sh
uv run --locked python scripts/analyze-robustness-influence.py --output runs/reproduced-robustness-influence.json
```

## Verification and packaging

```sh
uv run --locked python -m pytest --basetemp .cache/pytest-publication
uv run --locked ruff check src tests scripts
uv run --locked ruff format --check src tests scripts
uv run --locked python -m mypy src/mlresearch
uv run --locked python scripts/package-publication.py --output output/release
```

Tests cover meaningful numerical/covariance, information-boundary, accounting and resume behavior. The release audit distinguishes these checks from the model's unverified biological assumptions. A clean unpack/install and manuscript-only unpack/compile are independently checked before completion.

## Human submission actions

Review the final paper and choose a suitable preprint category or journal; this is a focused computational evaluation with limited biological generalization. For arXiv, [the official submission guide](https://info.arxiv.org/help/submit/index.html) requires source submission for a TeX-authored article. Upload the contents of the manuscript-source archive, select `main.tex`, inspect the platform-generated PDF, and choose the author-approved CC BY 4.0 terms. Account registration, possible endorsement and moderation remain platform decisions. Deposit the accompanying code/evidence archive and supply its persistent URL/identifier when assigned; update the availability/citation metadata if a public archive is created. For a journal, adapt its template, data/code deposit and AI-disclosure fields without changing the scientific qualifications. No acceptance, endorsement, DOI or public deposition is implied by this preparation.
