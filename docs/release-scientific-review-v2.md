# Internal scientific review of the release manuscript

Reviewed October 28, 2026. This is an internal review of the current manuscript and selected underlying evidence, not external peer review or journal acceptance. Historical protocols, predictions and audit records were not modified. The base repository revision was `3302c7c17c1aab7bd8c4f7408636d0b4d26de9a9`; the author-statements revision was present in the working tree during this review.

## Assessment and required scientific changes

No unresolved scientific correction requiring a manuscript change or additional experiment was identified in the inspected scope. The manuscript supports a narrowly framed computational evaluation of a fixed acquisition surrogate, including negative primary results, conditional successes and constructed failures. It does not establish a generally superior acquisition method, biological transportability, calibrated adaptive uncertainty or prospective laboratory savings.

The favorable post-primary result remains visible in the abstract, main results and discussion. The original primary comparison is not replaced by a favorable exploratory contrast. The stated limitations address the principal reasons that stronger claims would not follow from these experiments.

This assessment is conditional on preserving that scope and completing the separate software, artifact and platform checks. It is not a guarantee that all defects have been excluded or that a particular venue will accept the paper.

## Actual coverage

Read the complete abstract, all twelve section files, every main and supplementary table specification, and the ten-entry bibliography. Coverage included:

- Information and cost interface: source-observed query responses, unavailable recipient query outcomes, distinct paid acquisition and scorer banks, shared pilots, setup/cell/control prices, partial blocks and counterfactual ledgers.
- Estimand and preprocessing: difference of cell-level normalized-log means; full released-panel normalization before exact gene intersection; source-only transductive coordinates and selected target cohort.
- Methods and algebra: shared-control covariance, nuisance-baseline elimination, fixed-feature estimability, ridge penalization, paid validation correction, fixed-kernel variance and its distinction from the fitted predictor's risk.
- Study chronology: development, the actual pre-scoring primary comparator, controlled worlds, post-primary diagnostics and the separately declared robustness matrix.
- Statistical interpretation: conditioning of each resampling procedure, common-control dependence, fixed acquisition cell order in the primary seeds, reused queries/cells/directions, sparse guide/batch strata, Monte Carlo units and absence of biological replication.
- Results: primary, mean-query and development-reference contrasts; zero/noise context; support transition; query heterogeneity; ranking versus absolute error; controlled support/coverage failures; cost sensitivity and the stronger-information direct-query reference.
- Comparator fidelity: explicit heuristics and reconstruction differences, reused paid validation and the historical diagnostic-gate correction without a claim of reproducing or refuting another article's published performance.
- Availability and resources: separate lightweight/full reproduction paths, historical software versions, excluded large data/predictions, private repository status and an accompanying archive that still requires a public deposit for reader access.

The method descriptions were also compared with the relevant acquisition-policy implementation and declared controlled/external configurations. This review did not replace the separate full software review.

## Independent arithmetic checks

The calculations below were recomputed during this review from retained CSV rows, rather than accepted solely because a previous audit or manifest passed.

### Original primary curves

Read `docs/results/external-evaluation-v1/supplement/curves-and-specificity.csv`. For each direction and predictor/policy, independently sorted the 128/256/512 checkpoints and calculated the budget-normalized trapezoidal area. Percent changes use the reference's own area.

| Quantity | K562 to RPE1 | RPE1 to K562 |
| --- | ---: | ---: |
| Extension/CV-ridge area | 0.007868435417438814 | 0.005723834580602765 |
| Change versus worst-query | +0.5650687% | +0.0137794% |
| Change versus mean-query | +0.8015334% | -0.4677913% |
| Change versus reliability/CV ridge | +1.6938934% | -0.6227189% |
| Error reduction versus zero | 3.1587180% | 0.6232360% |

These agree with the manuscript's stated rounding. Positive comparison changes mean larger error for the extension. The manuscript appropriately describes the original primary result as no demonstrated benefit, without claiming equivalence or proving absence of benefit.

### Complete robustness comparisons

Read `docs/results/publication-robustness-v1/analysis/paired-query-areas.csv` and `paired-area-comparisons.csv`. Independently regrouped all query records by run, budget grid and reference. Each of the 32 contrasts contains 131 distinct paired-query records. Recomputed every mean area difference and relative change; all matched the retained comparison values to absolute tolerances of `1e-14` and `1e-12`, respectively.

| Budget grid | Reference | Cells with lower extension error | Total cells |
| --- | --- | ---: | ---: |
| 128-512 | Worst-query | 3 | 8 |
| 128-512 | Mean-query | 2 | 8 |
| 128-2,048 | Worst-query | 2 | 8 |
| 128-2,048 | Mean-query | 5 | 8 |

For the favorable forward split-20261023/rank-four/full-grid contrast against worst-query, independently recomputed 47/131 negative paired-query differences, median `+0.00013621101886853847`, and leave-one-query-out mean range `[-0.00033133727658873164, -0.00023477854970664164]`. These agree with the main text. A favorable aggregate is neither a majority-query benefit nor a single-query sign artifact. The manuscript also correctly notes that this split's benefit already exists on the shorter grid, preventing attribution of the benefit to the budget extension alone.

### Support and shrinkage

Read `docs/results/publication-robustness-v1/analysis/per-budget-primary-diagnostics.csv`. Independently checked the support fractions for every rank/policy/budget cell: rank four is supported throughout, whereas rank sixteen has support fraction zero at 128 and one from 256 onward. Summed the extension's checkpoint diagnostics:

| Rank | Null selections | Fits | Largest-penalty selections |
| --- | ---: | ---: | ---: |
| 4 | 9 | 60 | 9 |
| 16 | 10 | 60 | 30 |

These agree with the manuscript and support its distinction between estimated support and actual shrinkage-sensitive prediction risk.

### Other inspected evidence

Inspected the controlled scenario and interval tables, ranking/absolute table, original query-influence summary and pilot-span audit. Their reported directions, denominators, support qualifications and precision match the corresponding manuscript descriptions. This inspection is distinct from the fresh arithmetic recomputations listed above; it does not claim a fresh execution of their underlying experiments.

## Primary-source citation checks

Rechecked the bibliography and the specific prior-work relationships against primary publisher, author, preprint or dataset sources. No fabricated citation, mismatched title/author identity or unsupported novelty claim was found.

| Citation | Primary source and checked relationship |
| --- | --- |
| Replogle et al. (2022) | [Cell article DOI](https://doi.org/10.1016/j.cell.2022.05.013) and [author manuscript](https://pmc.ncbi.nlm.nih.gov/articles/PMC9380471/): bibliographic identity, essential-screen contexts, sampling days and differing CRISPRi effectors. |
| Frangieh et al. (2021) | [Nature Genetics article](https://www.nature.com/articles/s41588-021-00779-1): bibliographic identity and multimodal melanoma perturbation-screen setting. |
| Peidli et al. (2024) | [Nature Methods article](https://www.nature.com/articles/s41592-023-02144-y): harmonized-data resource, volume 21 and pages 531-540. |
| scPerturb data | [Pinned Zenodo record 13350497](https://zenodo.org/records/13350497): version 1.4, dataset identity and the three named H5AD files/checksum listings. |
| Huang et al. (2024), IterPert | [RECOMB publisher entry](https://link.springer.com/chapter/10.1007/978-1-0716-3989-4_2) and [author preprint](https://www.biorxiv.org/content/10.1101/2023.12.12.571389v1.full): sequential acquisition using multimodal priors, including RPE1 perturbation responses as an additional prior for K562. Publisher pages 17-37 and author list match. |
| Niu et al. (2026), PerturbPlan | [Author preprint](https://www.biorxiv.org/content/10.64898/2026.05.22.727199v1): bibliographic identity and analytical power/cost design for perturbation-expression association testing, a different objective from this manuscript's sealed-query prediction. |
| Cui et al. (2026), PerturbMap | [Pinned author preprint](https://arxiv.org/html/2607.28090v1): same-intervention measured-source response transfer, recipient-local low-rank base, affine experts, route calibration and network/settings relevant to the explicitly qualified reconstruction. |
| Fiez et al. (2019) | [NeurIPS proceedings](https://papers.neurips.cc/paper_files/paper/2019/hash/8ba6c657b03fc7c8dd4dff8e45defcd2-Abstract.html): bibliographic identity and separate measurement/item sets in transductive experimental design. |
| Rasmussen and Williams (2006) | [Authors' book site](https://gaussianprocess.org/gpml/): bibliographic identity for the classical Gaussian-process covariance reference. The manuscript explicitly states its known-trend and fixed-amplitude qualifications. |
| Huang et al. (2026), AmbiModBench | [Pinned author preprint](https://arxiv.org/html/2609.32527v1): bibliographic identity and the attributed shared-response, gene-coordinate permutation and representation-coverage diagnostics. |

Some direct bioRxiv fetches returned access errors; the indexed primary-source text and available author/publisher records supplied the checked passages. No secondary review or aggregator was used as the substantive basis for these citation checks.

## Review limits and release handoff

This review did not rerun the large-data acquisition suites, independently reproduce every original prediction array, establish new biological ground truth, validate the hypothetical prices in a wet laboratory or certify all possible numerical edge cases. It did not perform the final rebuilt-PDF visual inspection, current archive validation, fresh environment installation, security scan or GitHub/Kaggle execution; those belong to the release checks performed separately.

No essential new experiment is required for the present narrow evaluation. Independent biological contexts/replicates, prospective acquisition economics, a learned discrepancy model or a calibrated adaptive interval method would be needed to support stronger claims, rather than being silently inferred from this study.

Before delivery, rebuild and inspect the current PDF, refresh the archives after all edits, authenticate retained evidence, run the applicable software checks and verify the actual platform package. Public deposition and platform-generated links must be reported only after they exist. The manuscript currently describes the GitHub repository as private during preparation and does not invent a public code DOI.
