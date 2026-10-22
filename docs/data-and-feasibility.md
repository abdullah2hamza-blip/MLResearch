# Data and feasibility

## Verified public inventory

The scPerturb API was queried directly on October 21, 2026. The concept endpoint `7041848` resolved to **record 13350497, version 1.4**, with a CC BY 4.0 metadata license declaration. The record was created and modified on August 26, 2024. Pin the resolved record rather than relying on a moving concept endpoint.

The [saved metadata snapshot](evidence/data-inventory.json) records the source endpoint, resolved DOI, file URLs, byte sizes, and published MD5 checksums. **Only metadata were retrieved.** No H5AD matrix was downloaded or inspected. A checksum listed by the host is not a checksum verified against a local download. [Pinned record](https://zenodo.org/records/13350497), [metadata API](https://zenodo.org/api/records/13350497).

| Public filename | Bytes in the inventory | Proposed use |
| --- | ---: | --- |
| `ReplogleWeissman2022_K562_essential.h5ad` | 1,546,729,675 | Source/recipient transfer candidate with the RPE1 resource. |
| `ReplogleWeissman2022_rpe1.h5ad` | 1,236,886,900 | Reverse transfer direction and external evaluation. |
| `FrangiehIzar2021_RNA.h5ad` | 1,458,928,348 | Development across biological conditions, subject to metadata audit. |
| `FrangiehIzar2021_protein.h5ad` | 24,714,445 | Potential orthogonal readout; verify barcode alignment before use. |
| `NadigOConner2024_hepg2.h5ad` | 850,590,740 | Optional additional cell context. |
| `NadigOConner2024_jurkat.h5ad` | 1,293,665,804 | Optional additional cell context. |

The [scPerturb resource paper](https://www.nature.com/articles/s41592-023-02144-y) documents harmonization and links back to original experiments. Harmonization improves interoperability; it does not make assays, guides, perturbation strength, or biological populations exchangeable.

## Dataset suitability

**Frangieh:** the original study combines perturbations with RNA and surface-protein readouts in patient-derived tumor/immune models. This provides a plausible setting for studying condition changes and an eventual orthogonal readout. [Original author-hosted manuscript](https://ccsp.hms.harvard.edu/wp-content/uploads/2021/10/Frangieh-2021.pdf). PerturbMap demonstrates a concrete multi-context use of this cohort, but its processed support counts must not be assumed to match the downloaded scPerturb files.

**Replogle:** the two named files offer a plausible cross-cell-line comparison. Establish the actual overlapping gene targets and match experimental time points, library versions, and controls before declaring an episode valid. Cell lines are a tractable first test; successful transfer between them would not demonstrate patient-level or primary-cell generalization.

**Additional contexts:** the HepG2/Jurkat filenames are verified. Their relationship to the desired intervention panel, raw-count availability, replicate structure, and overlap with the first pair remains unknown. These files are a replication option, not evidence that a broad multi-tissue benchmark is already feasible.

## Required data audit before model work

Produce an inventory table and preserve the original metadata names alongside canonical fields:

| Audit | Required record or decision |
| --- | --- |
| Identity | Stable gene IDs, intervention IDs, guide IDs, multi-guide handling, duplicates, and source-to-recipient target intersection. |
| Assay comparability | Perturbation chemistry, dose/knockdown efficacy if available, assay technology, time point, and condition definitions. |
| Measurement representation | Raw counts versus normalized values; `.X`, `.layers`, and `.raw` contents; gene mapping and normalization provenance. |
| Sampling | Cells per intervention/control by guide, batch, donor, and biological replicate; captured-cell selection and missing conditions. |
| Paired readouts | RNA/protein barcode intersection and consistency of intervention labels. |
| File integrity | Published checksum versus downloaded checksum, plus a locally computed SHA-256 and exact source version. |
| Licensing | Record license, original-study terms, required attribution, and any discrepancy between code and data licenses. |
| Contamination | Shared samples or source studies across development/test cohorts; training-corpus exposure if a pretrained model is used. |

Feasibility gate for a small pilot: aim for at least 100 overlapping intervention identities per selected pair, including 40 sealed queries and 60 calibration candidates, with sufficient disjoint cells for the chosen budget grid. These are proposed engineering minima, not observed dataset counts or statistically powered sample sizes. Revise the design before final evaluation if the inventory fails them.

If independent batches or biological replicates do not exist, the replay can still quantify subsampling behavior, but its uncertainty intervals describe that restricted procedure. Do not call resampled cells new independent experiments.

## Resource plan

The verified K562-essential/RPE1 files total about 2.8 GB on disk. All six selected files total about 6.4 GB. Storage, parsing overhead, sparse-matrix conversions, and cached views can require substantially more space. Do not download the much larger K562 genome-wide file by default when the essential-gene file addresses the first question.

Planning envelope, to be replaced with measurements:

- **Initial statistical baseline:** one workstation with approximately 32 GB RAM; read sparse/backed data, aggregate by intervention, and fit small linear models. This is a feasibility estimate, not a benchmarked requirement.
- **Storage:** reserve roughly 20-40 GB for selected inputs, manifests, cached summaries, and outputs. Avoid committing experimental matrices to Git.
- **GPU:** optional for the initial acquisition study. A later pretrained or generative comparison needs its own measured memory/runtime budget.
- **Software:** a future implementation will likely need AnnData/HDF5, numerical linear algebra, and statistical modeling libraries. The current Python scaffold was left unchanged; this dossier does not imply those dependencies were installed.

For scale intuition only, densifying 100,000 cells by 20,000 genes into float32 requires 8 GB for one array before intermediates. Aggregate or subset without accidental full densification. This is an arithmetic illustration, not the measured size of one of these datasets.

## What retrospective replay cannot prove

Within a fixed screen, replay can test which already observed cells a policy would reveal. It cannot reproduce guide-library engineering, unpredictable cell capture, new biological batches, real laboratory turnaround, or treatment-dependent survival. Nominal cell allocations are abstractions of a pooled screen. A prospective study must validate them.

The 2026 challenge is contextual motivation rather than a guaranteed training/evaluation data source. Its official interface withholds response ground truth, so the project should remain executable using the verified public resources even if no additional challenge data become available.
