# Saved-result reanalysis on Kaggle

The editable notebook is [joint-acquisition-reanalysis.ipynb](../notebooks/joint-acquisition-reanalysis.ipynb). It recomputes the original primary normalized error areas and all 32 later robustness contrasts from compact, retained CSVs. It produces two figures, three CSV tables and a verification JSON. It is re-analysis of saved outputs, not a repetition of raw-data acquisition, preprocessing, fitting, frozen prediction generation or experimental scoring. The [full reproduction instructions](external-reproduction.md) cover the larger experiment.

The notebook requires Python 3.12 and Matplotlib, with ordinary standard-library CSV/statistics operations. It uses no GPU, internet connection, credentials, raw expression, downloaded model weights or package-install cell. Actual runtime/package versions and elapsed time are written into its verification output. A successful local run is recorded separately from successful execution of the uploaded Kaggle version.

## Exact compact input

The staging helper copies these original saved outputs without editing their bytes:

| Input key | Original repository file | Staged file | Original bytes |
| --- | --- | --- | ---: |
| `primary_curves` | `docs/results/external-evaluation-v1/supplement/curves-and-specificity.csv` | `results/primary-curves.csv` | 224,402 |
| `paired_query_areas` | `docs/results/publication-robustness-v1/analysis/paired-query-areas.csv` | `results/paired-query-areas.csv` | 685,638 |
| `paired_area_comparisons` | `docs/results/publication-robustness-v1/analysis/paired-area-comparisons.csv` | `results/paired-area-comparisons.csv` | 11,402 |

`mlresearch-results-manifest.json` binds the three file hashes, original paths, upstream scPerturb Zenodo record 13350497/version 1.4, scientific software versions, release commit/tag and intended notebook source checksum. The staged directory also contains a dataset card and unchanged software/manuscript notices with a mixed-artifact scope file. The staged input is about 0.93 MB before compression, plus its small manifest/card/notices; other manuscript/release assets may be added to the surrounding dataset by the release workflow.

From the project root, after the real release tag exists:

```sh
uv run --locked python notebooks/prepare_saved_result_inputs.py --destination output/kaggle/reanalysis-inputs-v0.2.1 --release-commit "$(git rev-parse v0.2.1^{commit})" --release-tag v0.2.1
uv run --locked python notebooks/validate_saved_results_notebook.py --inputs output/kaggle/reanalysis-inputs-v0.2.1 --output .cache/notebook-validation-v0.2.1
```

Use a new staging destination; the helper refuses to overwrite an existing directory. `--release-commit` must be the actual full 40-character commit of the release and `--release-tag` its actual tag. Local tests deliberately use a `local-validation` label; those test manifests are not publication artifacts. The local validator executes all ordinary Python cells in order from an empty namespace with the supplied input and output directories. It does not claim a hosted Kaggle execution or persist fabricated notebook outputs.

## Kaggle inputs and execution

Attach the intended version of the released dataset, choose CPU execution and disable internet. The notebook finds exactly one `mlresearch-results-manifest.json` below `/kaggle/input`, so no private account path or guessed dataset slug is embedded in code. If multiple releases are attached, remove the unintended attachment or set `MLRESEARCH_INPUT_ROOT` explicitly to the intended manifest directory. Local validation sets that environment variable automatically.

All three input hashes must match before analysis. Duplicate query identities, missing checkpoint/contrast cells, non-finite numbers, inconsistent metadata or mismatched retained comparisons fail the run. The notebook checks the original primary points at the manuscript's stated precision and recomputes all 32 robustness means/relative changes from 131 paired query records each. Absolute comparison tolerances are `1e-14` for paired mean differences and `1e-12` for relative changes. The original 2,000-draw query-bootstrap ranges are retained metadata, not regenerated bootstrap draws in this notebook.

Kaggle outputs go to `/kaggle/working/mlresearch-reanalysis`:

- `primary-areas.csv`: ten areas, comprising two directions and four paid-validation ridge policies plus a standalone zero reference.
- `primary-comparisons.csv`: six extension-minus-reference comparisons (worst-query, mean-query and reliability, in both directions).
- `robustness-contrasts.csv`: every grid/reference/direction/split/rank contrast, with recomputed means, sign counts, query medians and leave-one-query-out mean bounds; retained conditional ranges are explicitly identified.
- `primary-curves.png` and `robustness-matrix.png`: descriptive curves and all 32 point comparisons, with units and sign conventions.
- `reanalysis-verification.json`: completion state, release binding, input/output checksums, counts, numerical discrepancies and observed runtime/environment.

Creating or uploading a notebook is not successful execution. The release workflow must start a fresh Kaggle session, wait for completion, inspect actual logs/outputs, and verify that the public notebook version is the tested version. If executable cells or inputs change, repeat the affected checks and publish a coherent version. Local validation artifacts use `passed_local_notebook_execution`; the analysis JSON uses `passed_saved_result_reanalysis`. Neither status alone establishes successful remote execution, public accessibility or full experimental reproduction.

## Data dictionary and scientific limits

`primary-curves.csv` contains the original six-run suite's policy/backbone/budget summaries. `run` and `source_control` distinguish the two unmodified runs from permutation controls. `policy` and `backbone` identify acquisition/prediction; `budget` is an abstract recipient ceiling; `mse` is full-gene/query/seed mean squared transformed-expression error. `specificity_mse` removes across-query shared components. `assessment_noise_floor` is plug-in independent-cell context, `noise_subtracted_mse` is unclipped, and `mean_spent`/`predictor_used_cost` distinguish charged observations from prediction-use costs. `query_seed_predictions` gives the query/seed denominator. This notebook selects the two unmodified runs, `ridge_cv`, extension/worst/mean/reliability and the standalone zero reference.

`paired-query-areas.csv` has `run`, `split_seed`, `source_context`, `target_context`, `rank`, `grid`, `reference` and `query` keys. `extension_area` and `reference_area` are query-specific normalized error areas with the three acquisition seeds already averaged; `paired_difference` is their difference. The 4,192 rows form 32 contrasts of 131 distinct queries each, rather than 4,192 independent biological replications.

`paired-area-comparisons.csv` retains the same contrast metadata plus budget endpoints, policy/backbone, absolute areas, paired differences, relative changes and denominators. `conditional_query_low`/`high` are the original conditional query-resampling ranges. Query-difference min/max/median and fraction fields describe heterogeneity. Their ranges fix source/split/fits/scoring banks; they are not biological confidence intervals. The notebook independently reconstructs means, relative changes, median/sign distribution and leave-one-query-out means, while retaining the original conditional interval metadata.

The directions/splits reuse observations; fixed acquisition-order seeds are not biological replicates; a favorable post-primary cell is not a confirmatory discovery. The original primary rule does not demonstrate a benefit over worst-query, and the later matrix is mixed. No equivalence, biological transportability, calibrated adaptive uncertainty or prospective laboratory savings follow from these arithmetic checks. The manuscript contains the full selected-cohort, protocol, scorer-noise, source-error, shrinkage, comparator and hypothetical-price qualifications.

## Rights, disclosure and platform metadata

Preserve original MIT software/supporting-documentation terms, CC BY 4.0 manuscript/figure/table terms and all third-party attribution. The input helper does not assign a new blanket data license to retained CSVs. Its `licenses/SCOPE.txt` explains the container's mixed scope. Kaggle's official [dataset metadata reference](https://github.com/Kaggle/kaggle-cli/blob/main/docs/datasets_metadata.md) permits exactly one `licenses` entry and supports `other` (specified in the description), so the mixed container can use `licenses: [{"name": "other"}]` with that scope visible. The [official dataset guide](https://www.kaggle.com/docs/datasets) also instructs authors to specify custom terms in the description.

The [official kernel metadata reference](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md) defines `code_file`, `dataset_sources`, `kernel_type`, `enable_gpu`, `enable_internet` and visibility fields. Use only the verified account/dataset identifiers and actual created URLs; do not publish an example account or a guessed asset URL. Metadata used for upload is generated by the release workflow, separate from this account-independent notebook. Kaggle's notebook code-license defaults must also be checked before public publication: an additional platform-imposed code license is a separate rights choice, not silently inferred from authorization to publish under the project's MIT terms.

The author has explicitly approved the additional Apache 2.0 terms for the original code/text/charts of this same hosted notebook. Repository software stays MIT, the manuscript stays CC BY 4.0, and input/third-party terms are preserved. The artifact dataset is versioned in place and includes the complete implementation/configurations/evidence, rather than relying only on an external code link.

The visible notebook and staged dataset card use the canonical disclosure:

> Artificial intelligence (AI) tools were used for manuscript editing and code preparation.
>
> OpenAI Codex (OpenAI) assisted with research planning, literature review and experimental design, code preparation, statistical analysis and interpretation, figure and table preparation, manuscript drafting and revision, internal review, and release preparation. These AI-assisted reviews were internal quality checks, not independent human peer review. The human author retains responsibility for the final work.

No exact model identifier, new DOI, human peer-review status or additional author attestation is invented. The prior human author statement is established separately by the author; automated/local checks do not themselves provide human approval.
