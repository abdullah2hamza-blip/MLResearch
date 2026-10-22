# Primary-source register

Access date and research cutoff: **October 21, 2026**. This register includes papers, author code, an official challenge announcement, and a data release; its entries are not all peer-reviewed papers.

Inspection labels distinguish what was actually read:

- **Full sections:** substantive manuscript or author-documentation sections were retrieved.
- **Official abstract:** the primary publication/preprint landing page was inspected; this does not imply that its methods were reproduced.
- **Indexed excerpts:** the search service exposed primary-source passages, but direct article access was blocked or limited.
- **Metadata:** a repository API was queried; experimental arrays were not inspected.

Reported findings remain the authors' findings. No result was independently reproduced during this research pass. Where an exact publication date or bibliographic field was not verified, it is omitted rather than inferred from a DOI or filename.

## Problem and current context

### S01 — Arc Institute, 2026 Virtual Cell Challenge

[The 2026 Virtual Cell Challenge: predicting perturbation responses in cell contexts a model has never seen](https://arcinstitute.org/news/virtual-cell-challenge-2026). August 20, 2026. Official announcement; **full page**.

Establishes the current task interface and its distinction from paid recipient calibration. Used for task context, not proof that zero-shot responses are identifiable.

### S02 — Arc Institute, data generation

[Generating high-quality Perturb-seq data for the 2026 Virtual Cell Challenge](https://arcinstitute.org/news/behind-the-data-virtual-cell-challenge-2026). October 1, 2026. Institutional methods account; **full page**.

Documents attention to matched experimental conditions, non-targeting controls, and data quality. This is an account from the dataset producer, not an independent benchmark audit.

### S03 — Generalizable perturbation benchmark

[Benchmarking algorithms for generalizable single-cell perturbation response prediction](https://www.nature.com/articles/s41592-025-02980-0). Nature Methods, DOI `10.1038/s41592-025-02980-0`. Journal article; **indexed abstract and data/code statements**.

Supports the need to distinguish cellular-context and perturbation generalization. Does not justify a blanket judgment about every model or evaluation setting.

### S04 — Dibaeinia et al., context and scale

[Virtual Cells Need Context, Not Just Scale](https://www.biorxiv.org/content/10.64898/2026.02.04.703804v1). Posted February 9, 2026; bioRxiv v1. **Indexed abstract and full-text excerpts**.

A close conceptual predecessor for the context/transport motivation. Its interpretation is an argument supported by its analyses, not an unrestricted impossibility theorem.

### S05 — Qi and Chapfuwa, transportability

[Mechanisms Matter: Transportability of Cellular Perturbation Effects](https://www.biorxiv.org/content/10.64898/2026.05.08.723625v2). Version 2 posted July 2, 2026; bioRxiv. **Indexed versioned abstract and revision note**.

Important for separating mechanism shift from superficial distribution similarity. Simulator conclusions must be interpreted under its assumptions.

### S06 — State

[Predicting cellular responses to perturbation across diverse contexts with State](https://doi.org/10.1016/j.cell.2026.07.052). Cell, 2026 journal record. **Indexed primary abstract**; full journal text not retrieved.

A relevant modern predictor and counterweight to a purely negative assessment of the field. Its reported performance was not independently evaluated here.

## Closest methods and evaluation research

### S07 — Cui, Liu, and Sun, PerturbMap

[PerturbMap: Cross-Context Transfer of Single-Cell Perturbation Responses](https://arxiv.org/html/2607.28090v1). Submitted July 30, 2026; arXiv v1. **Full HTML method and evaluation sections**.

The closest inspected transfer baseline. Its query-adaptive harm control means that reliability gating alone cannot support this proposal's novelty.

### S08 — Huang, Wang, and Wilson, intervention geometry

[Virtual-cell models compress unseen intervention geometry through a target-specific generalization bottleneck](https://www.biorxiv.org/content/10.64898/2026.08.21.746243v1). Posted August 24, 2026; bioRxiv v1. **Indexed abstract, figure captions, and full-text excerpts**.

Direct prior art for intervention-identity anchoring and geometry diagnostics. Benefits from anchoring the same query must be separated from calibrating other recipient interventions.

### S09 — Wang et al., perturbation reliability

[Reliable single-cell perturbations explain and improve model performance](https://www.biorxiv.org/content/10.64898/2026.08.11.744177v1). Posted August 12, 2026; bioRxiv v1. **Indexed abstract**.

Direct prior art for reliability-aware training/evaluation and cell-depth planning. Its reported dataset-wide proportions are not generalized to every future screen in this dossier.

### S10 — Reliability study code

[scReliability paper analysis repository](https://github.com/cbg-ethz/scReliability_paper). Author code/documentation; **full README**.

Clarifies the quality diagnostics and workflow. The README identifies an MIT code license, distinct from the manuscript's and experimental data's licensing.

### S11 — Hao et al., PerTurboAgent

[PerTurboAgent: An LLM-based Agent for Designing Iterative Perturb-Seq Experiments](https://proceedings.mlr.press/v311/hao25b.html). MLCB 2025, PMLR 311:44-64. **Official abstract**.

Predecessor for agent-assisted iterative panel design. The proposed first study avoids an agent harness to isolate statistical allocation effects.

### S12 — Identifiability and experiment selection

[Identifiability and experimental design in perturbation studies](https://academic.oup.com/bioinformatics/article/36/Supplement_1/i482/5870467). Bioinformatics 36, Supplement 1, 2020; DOI `10.1093/bioinformatics/btaa404`. **Indexed article excerpts**.

Essential older prior art: identifiability-driven experimental design is not a new idea introduced by virtual-cell foundation models.

### S13 — Qin et al., NAIAD

[Active Learning for Efficient Discovery of Optimal Combinatorial Perturbations](https://proceedings.mlr.press/v267/qin25g.html). ICML 2025, PMLR 267:50363-50383. **Official abstract**.

Occupies active combination optimization and rules out a generic “active learning for gene perturbations” claim.

### S14 — Rubbi et al., Probability-of-Hit

[Many Needles in a Haystack: Active Hit Discovery for Perturbation Experiments](https://proceedings.mlr.press/v306/rubbi26a.html). ICML 2026, PMLR 306:106064-106087. **Official abstract**.

Shows that acquisition objectives already distinguish hit discovery from finding a single optimum. Its objective differs from estimating a fixed set of unmeasured recipient responses.

### S15 — Fiez et al., transductive design

[Sequential Experimental Design for Transductive Linear Bandits](https://papers.neurips.cc/paper_files/paper/2019/hash/8ba6c657b03fc7c8dd4dff8e45defcd2-Abstract.html). NeurIPS 2019. **Official abstract**.

Foundational comparator for separate measurement and query sets. A classical adaptation must be credited and tested before claiming a new acquisition algorithm.

### S16 — Jiang et al., PerturbedVAE

[What Makes a Representation Good for Single-Cell Perturbation Prediction?](https://proceedings.mlr.press/v306/jiang26ad.html). ICML 2026, PMLR 306:52722-52757. **Official abstract**.

Identifiability and perturbation-specific representation learning are already studied directly. The proposed contribution targets allocation of information rather than introducing these concepts.

### S17 — Lorch et al., LCD/CLIPR

[Latent Causal Diffusions for Single-Cell Perturbation Modeling](https://arxiv.org/abs/2601.15341). Submitted January 20, 2026; arXiv v1. The landing page also lists PNAS 123(41), e2602630123 (2026). **Official preprint abstract and bibliographic metadata**; final journal text not inspected.

Relevant progress in generative causal modeling. The stated identification result has a linear-drift assumption; it is not a universal guarantee for cellular networks.

### S18 — Huang et al., AmbiModBench

[AmbiModBench: Benchmarking Gene Perturbation Prediction Beyond Shared Responses](https://arxiv.org/abs/2609.32527). Submitted September 26, 2026; arXiv v1. **Official abstract**.

Recent direct prior art for specificity, gene-coordinate checks, and coverage-aware evaluation. Such diagnostics are required controls here, not novelty claims.

## Data foundations

### S19 — Peidli et al., scPerturb

[scPerturb: harmonized single-cell perturbation data](https://www.nature.com/articles/s41592-023-02144-y). Nature Methods 21:531-540; published January 26, 2024. **Indexed abstract and data-availability section**.

Primary provenance for the harmonized resources. Follow original-study provenance when interpreting assays or pooling contexts.

### S20 — Pinned scPerturb data release

[scPerturb RNA/protein H5AD release, version 1.4](https://zenodo.org/records/13350497). August 26, 2024; DOI `10.5281/zenodo.13350497`. **Metadata API**, queried October 21, 2026.

The [snapshot](evidence/data-inventory.json) independently records six relevant file entries. It proves inventory availability, not experimental suitability or local file integrity.

### S21 — Frangieh et al., Perturb-CITE-seq

[Multi-modal pooled Perturb-CITE-Seq screens in patient models define novel mechanisms of cancer immune evasion](https://ccsp.hms.harvard.edu/wp-content/uploads/2021/10/Frangieh-2021.pdf). Nature Genetics author manuscript, 2021. **Indexed author-hosted manuscript excerpts**.

Biological and multimodal provenance for a proposed development cohort. The initial project would not reproduce the study's mechanistic or clinical findings.

## Other frontiers and counterevidence

### S22 — Rautela et al., PDE transfer

[Out-of-distribution transfer of PDE foundation models to material dynamics under extreme loading](https://arxiv.org/abs/2603.04354). Submitted March 4, 2026; arXiv v1. **Official abstract**.

Evidence of a current scientific-ML transfer problem. The comparison in this dossier does not independently assess its models or datasets.

### S23 — Winovich et al., active operator learning

[Active operator learning with predictive uncertainty quantification for partial differential equations](https://doi.org/10.1016/j.jcp.2026.114791). Journal of Computational Physics 555, 114791; June 15, 2026. **Indexed journal abstract and highlights**.

Close prior art that weakens a generic uncertainty-driven PDE acquisition proposal.

### S24 — Wen and Liu, autonomous science

[Autonomous Science Bench: Evaluating AI Agents for Autonomous Scientific Discovery](https://arxiv.org/abs/2610.18449). Submitted October 13, 2026; arXiv v1. **Official abstract**, supplemented by author project documentation.

Separates discovery outcomes from learning on unmeasured designs. Its initial release is a pilot benchmark, not a comprehensive measure of autonomous science.

### S25 — Liu et al., BioProBench

[BioProBench: A Corpus and Benchmark for Biological Protocol Reasoning in Autonomous Science](https://proceedings.mlr.press/v306/liu26cu.html). ICML 2026, PMLR 306:77772-77806. **Official abstract**.

Additional evidence that scientific-agent evaluation extends beyond prediction to procedural reasoning. No claim about a current best model is made here.

### S26 — Cai et al., causal world-model evaluation

[What-If World: A Causal Benchmark for General World Models in Embodied Scenarios](https://arxiv.org/abs/2605.27589). Submitted May 26, 2026; arXiv v1. **Official abstract**.

Supports the distinction between plausible outputs and correct responses to interventions. Benchmark results do not establish universal limits of world models.

### S27 — X-Cell / X-Atlas-Pisces manuscript

[Author-hosted X-Cell manuscript](https://www.cdn.xaira.com/papers/X_CELL_V1_0316_final.pdf). **Indexed discussion excerpts**; full PDF exceeds the web reader's size limit. Exact title, author list, date, and publication status were not independently extracted.

Retained as counterevidence to a categorical anti-scaling narrative, with correspondingly limited evidential weight. It is not used to assert a verified performance ranking.

## Unresolved primary-source leads

### U01 — CausalPert manuscript

[OpenReview identifier euqNpvs4sb](https://openreview.net/pdf?id=euqNpvs4sb). Indexed PDF header states ICLR 2026, and methods excerpts name CausalPert and informative-anchor design. Direct access returned a verification page/403. Full bibliographic identity and the complete method remain unverified.

**Implementation-audit correction:** the title is *CausalPert: Grounding LLM Hypotheses in Regulatory Networks for Gene Perturbation Prediction*, Martell et al.; official indexed author metadata identifies an MLGenX 2026 poster. The identity is now recovered; full-method verification remains limited. Do not infer main-conference acceptance. See the [verification ledger](literature-verification.md).

### U02 — Multidimensional perturbation-screen design

[Indexed OpenReview workshop PDF](https://openreview.net/pdf/b16b6eae7237923d23630b07290115f7b229b7a2.pdf). Indexed header names the Machine Learning for Genomics Explorations Workshop at ICLR 2026. Excerpts discuss selection of biological contexts and multiple design axes. Direct retrieval returned 403. Recover the exact paper identity before making a priority claim.

**Implementation-audit correction:** this is *Beyond single-axis designs: multi-objective optimization for complex perturbation atlases*, Zheng, Hediyeh Zadeh, Liu, and Theis, [OpenReview FIAgwjf3i1](https://openreview.net/forum?id=FIAgwjf3i1). Identity is recovered; full methods remain limited. Indexed methods concern donor/cell-type/cytokine axes. See the [verification ledger](literature-verification.md) for exact evidence limits and the additional IterPert/PerturbPlan sources.

These two leads are documented because they could overturn the proposed novelty. They are not counted as fully verified bibliographic entries or treated as evidence that their uninspected methods lack a feature.
