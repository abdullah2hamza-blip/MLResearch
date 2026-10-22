# Research log and evidence limits

Research date: October 21, 2026. The goal was to find a promising, interdisciplinary ML research opportunity with a defensible novelty argument and an executable initial study.

## Search strategy

The search proceeded from broad frontiers to direct attempts to invalidate a narrower project. It used web search, primary publication/preprint pages, author documentation, and a public dataset API. It was not a systematic database review and did not retrieve every relevant manuscript.

| Search pass | Representative queries actually used | How the evidence changed the project |
| --- | --- | --- |
| Frontier scan | `2026 machine learning frontier perturbation response single cell virtual cell benchmark generalization causal`; `PDE foundation model 2026 out of distribution uncertainty`; `autonomous science benchmark 2026 experiment design`; `causal world models 2026 intervention benchmark` | Compared experimental biology, scientific surrogates, autonomous agents, and embodied causal modeling. |
| Active-design prior art | `single cell perturbation active learning experimental design 2025 2026`; `optimal design single cell perturbation screen` | Rejected generic active perturbation selection; found existing combination/hit-discovery and agent methods. |
| Transfer and anchoring | `cross context perturbation prediction few shot active learning optimal design anchor experiments`; `single cell perturbation active learning transfer learning context generalization` | Located close anchor and response-transfer methods. Restricted the claim to acquiring calibration information. |
| Identifiability | `single-cell identifiability experimental design`; `perturbation prediction experimental design identifiability 2026 single cell anchors`; `transductive linear bandits experimental design Fiez 2019` | Found older design theory and modern causal representations. Identifiability alone is not novel. |
| Reliability and budgets | `Reliable single-cell perturbations explain and improve model performance repeat depth`; `perturbation breadth depth active 2026`; `Perturb-seq optimal allocation controls` | Added cell depth and shared controls, and found multidimensional design as a serious overlapping lead. |
| Specificity and negative evidence | Exact-title searches and direct preprint inspection for PerturbMap, intervention geometry compression, and AmbiModBench. | Added identity/gene-coordinate controls and rejected a metrics-only or reliability-gating contribution. |
| Data feasibility | Searches for scPerturb and original experiments, followed by `https://zenodo.org/api/records/7041848`. | Verified a versioned public inventory rather than assuming data access. Actual intervention overlap remains an implementation-stage audit. |

Many narrow quoted queries returned empty or unrelated results. Those results were **not** interpreted as evidence that a method does not exist. Single-title checks and stable primary URLs were used when search retrieval was unreliable. Secondary aggregators and discussion forums were discovery aids only; the dossier's substantive claims point to primary sources.

## How the proposed gap changed

1. Initial candidate: cross-context virtual-cell prediction. Too broad after inspecting current transfer models.
2. Narrower candidate: identify informative calibration anchors. CausalPert and earlier design work already occupy much of that claim.
3. Narrower candidate: reliable transfer with deferral. PerturbMap's query-adaptive harm-control ablation invalidates a generic novelty claim.
4. Selected candidate: transfer-specific joint allocation of intervention identities, perturbed-cell depth, and shared controls, with sealed recipient queries and explicit identification limits.

The final formulation is a synthesis and a research hypothesis. Combining ingredients is not sufficient for publication; it must outperform a correctly adapted classical design or reveal a substantial new scientific boundary.

## Evidence quality and unresolved access

- Several bioRxiv, Nature, PMC, and OpenReview links were inaccessible through direct retrieval. The register explicitly distinguishes indexed excerpts from full methods.
- Two especially relevant OpenReview PDFs also returned HTTP 403 during a normal public-URL retrieval attempt. Their identities and complete methods remain the largest novelty uncertainty. No access controls or verification challenges were bypassed.
- The X-Cell PDF exceeded the web reader's content-size limit. Only its indexed discussion was used, with no independent performance endorsement.
- Official abstract pages verify paper scope and authors' claims, not the correctness or reproducibility of those claims.
- The scPerturb metadata endpoint resolved successfully and its relevant entries were saved. It did not verify local dataset checksums, assay alignment, or effective sample sizes.
- Search results can include publication dates beyond the cutoff. Future-dated material was excluded from the research argument. A November 2026 traffic-modeling result returned by an anchor query was irrelevant and was not used.

## Competing interpretations worth testing

**The problem may be measurement quality, not acquisition geometry.** A reliability-based depth policy could explain nearly all gains. It must be a comparator.

**The problem may be standard optimal design, not a new ML algorithm.** A nuisance-aware transductive design may already solve the useful part. That is the central algorithmic falsifier.

**The problem may be intervention-specific rewiring that other anchors cannot resolve.** The result could be a boundary favoring direct query measurements, rather than a successful transfer policy.

**The problem may be a replay artifact.** Shared batches, data-dependent eligibility, and cell-level resampling can generate apparent precision without independent biological evidence.

**Large models and diverse data may reduce the need for calibration.** The study should measure the remaining value of paid recipient information, not assume that scaling necessarily fails.

## Scope of the completed research deliverable

The dossier supplies a current frontier comparison, an interdisciplinary project recommendation, a bounded novelty claim with closest rivals, a formal problem, verified data-access evidence, and a prospective evaluation/roadmap. Its elementary design calculations are reproducible.

The next work is **executing the proposed research project**: obtaining complete competitor manuscripts, auditing experimental arrays, implementing baselines, and testing hypotheses. Those tasks are clearly separated from findings already established in this literature-and-design pass. No empirical project result or guaranteed priority claim is asserted.
