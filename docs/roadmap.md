# Project roadmap and decision gates

This is a proposed work plan for a future research project. It does not schedule an automation, commit funds, or represent experiments already performed. The duration assumes one researcher working substantially on the project; data quality and collaborator access can change it.

## First 48 hours: try to invalidate the idea

1. Obtain and read the full CausalPert and multi-axis screen-design manuscripts listed in the [research log](research-log.md). Recover their exact bibliographic identities and inspect references for newer overlapping work.
2. Compare their formal objectives with the proposed three-way allocation of interventions, depth, and shared controls for a separate recipient query set.
3. Read the closest methods beyond their abstracts: reliability-based cell planning, classical transductive design, and PerturbMap's calibration/gating rules.
4. Freeze a concise claim-comparison table. If an equivalent prior formulation exists, either build a real extension with a new scientific question or change projects.

**Decision:** do not spend weeks on a model until the novelty claim survives these checks. Inaccessible papers remain uncertainty, not evidence of absence.

## Staged execution

| Stage | Main work | Reviewable artifact | Continue only if |
| --- | --- | --- | --- |
| Week 1: data feasibility | Download only the first selected files; verify checksums; audit overlap, counts, guides, and batches. | Versioned data manifest and eligibility table. | At least one valid development setting and one distinct evaluation setting support the frozen interface. |
| Week 2: establish the transfer gap | Build zero/mean/source-copy/ridge baselines and sealed-query scoring. | Reproducible baseline curves and a read-access audit. | There is meaningful recipient-specific signal and sufficient measurement reliability to distinguish methods. |
| Week 3: classical design | Implement nuisance-aware transductive design, fixed allocation grids, and finite cell/control pools. | Matched-budget comparator suite. | Acquisition choices have measurable consequences beyond seed noise. |
| Week 4: candidate extension | Add bias-aware disagreement and source-feature uncertainty; avoid changing the predictor at the same time. | Ablation report and failure examples. | Benefit exceeds the strongest classical design or exposes a substantial, reproducible limitation. |
| Weeks 5-6: external evaluation | Freeze development choices; run both external transfer directions, noise/shift stress tests, and repeated acquisitions. | Locked results, uncertainty analysis, and complete cost logs. | The primary result survives information matching, query sealing, and context separation. |
| Week 7: scientific interpretation | Inspect biology with an appropriate collaborator; analyze missingness, controls, and negative results. | Evidence-to-claim table and draft paper outline. | Conclusions remain valid after restricting them to the evaluated populations and assays. |
| Week 8: release and next study | Prepare code, manifests, documentation, and a prospective experiment proposal if justified. | Reproducible research release and a concrete next-study plan. | Claims are supported; any laboratory work has a separate partner/resource agreement. |

## Explicit stop or pivot conditions

| Finding | Consequence |
| --- | --- |
| Shared-control-aware classical design matches the proposed extension. | Drop the new-algorithm claim. Keep an application/measurement-design paper only if the scientific finding is strong. |
| Query effects remain unpredictable after diverse calibration. | Report the transfer boundary; evaluate whether direct query measurement is the rational use of budget. |
| Benefits depend on free pilot cells or source tokens unavailable to baselines. | Repair the experiment and rerun before interpreting the result. |
| Interventions overlap too little, or metadata confound biology and batch. | Restrict to a justified task or change datasets; do not silently merge incompatible conditions. |
| Only cell resampling supports the gain. | Treat it as a statistical pilot and seek independent experimental replication. |
| Novelty is already occupied. | The backup direction is budgeted validation of PDE surrogates under discontinuous-regime shift, with its own new novelty search. Do not automatically reuse this claim in another domain. |

## First experiment specification

The first project milestone is a **small, sealed-query replay** comparing source-copy, ridge transfer with random calibration, and ridge transfer with classical joint design. Use a source-derived feature rank selected on development data and charge every recipient cell. Produce error-versus-cost curves plus an allocation ledger.

This experiment answers whether there is a useful design problem before building a complex method. It does not require an LLM, a large pretrained encoder, or new wet-lab data.

## What would justify a stronger publication claim

The preferred result is a consistent reduction in cost at a fixed response-error target, with improvements explained by appropriate breadth/depth/control choices and replicated in independent contexts. A convincing negative result would instead show that calibration of other interventions cannot resolve particular queries, despite adequate sampling precision.

Any eventual paper should publish failed settings and identify assumptions under which its uncertainty estimates are informative. Prospective validation, a new scientific discovery, and cross-domain generality are separate achievements; the initial replay would not establish them.
