# Literature and novelty audit

## Evidence that changes the project

General perturbation prediction is an active and crowded field. A benchmark evaluates 27 methods across 29 datasets and multiple generalization settings; its results motivate careful treatment of cellular context. This supports the problem's importance, not a claim that all complex models are inferior. [Benchmark paper](https://www.nature.com/articles/s41592-025-02980-0).

The following work materially narrows the proposed contribution. “Not established” means that the inspected evidence did not settle the question; it does not mean the paper lacks the feature.

| Prior work | What is already occupied | Remaining distinction to test | Inspection boundary |
| --- | --- | --- | --- |
| [Virtual Cells Need Context, Not Just Scale](https://www.biorxiv.org/content/10.64898/2026.02.04.703804v1) | Context dependence and causal transport as explanations for generalization failures. | An explicit costed acquisition policy and a measurable transition from unsupported to supported queries. | Indexed abstract and substantial full-text excerpts; preprint. |
| [Mechanisms Matter](https://www.biorxiv.org/content/10.64898/2026.05.08.723625v2) | Mechanism-shift simulation, cross-context evaluation, and diversity diagnostics. | Joint acquisition of recipient interventions, depth, and controls. | Indexed version-2 abstract; full manuscript inaccessible. |
| [PerturbMap](https://arxiv.org/html/2607.28090v1) | Same-query source measurements, recipient transfer maps, reliability weighting, and a query-level harm-control ablation. | Choosing the recipient calibration data under a shared-control-aware budget, rather than only fitting a transfer rule to a supplied panel. | Full HTML methods and evaluation sections inspected. |
| [Intervention geometry compression](https://www.biorxiv.org/content/10.64898/2026.08.21.746243v1) | Perturbation-specific geometry and the benefit of empirical intervention-identity anchoring across contexts. | Whether *other* recipient calibration interventions resolve a sealed query, and when direct measurement is unavoidable. | Indexed abstract, figures, and methods excerpts; preprint. |
| [Reliable single-cell perturbations](https://www.biorxiv.org/content/10.64898/2026.08.11.744177v1) | Reliability assessment and pilot-informed cell-count planning. | The marginal value of measurement reliability for transferring *different* unmeasured interventions, jointly with shared controls. | Indexed abstract; [author code documentation](https://github.com/cbg-ethz/scReliability_paper) also inspected. |
| [Identifiability and experimental design in perturbation studies](https://academic.oup.com/bioinformatics/article/36/Supplement_1/i482/5870467) | Identifiability-guided experiment selection, including network-parameter recovery. This dates to 2020. | A prediction-query estimand under cross-context transfer, uncertain features, and noisy cell/control allocation. | Indexed article text; journal publication. |
| [NAIAD](https://proceedings.mlr.press/v267/qin25g.html) and [Probability-of-Hit](https://proceedings.mlr.press/v306/rubbi26a.html) | Active selection of perturbations for combination optimization and hit discovery. | Acquiring experiments to reduce uncertainty on a separate, fixed query set. | Official conference abstracts. |
| [PerTurboAgent](https://proceedings.mlr.press/v311/hao25b.html) | LLM-assisted iterative perturbation-panel design. | A statistical allocation mechanism whose benefit can be isolated without an agent harness. | Official conference abstract. |
| [CausalPert manuscript](https://openreview.net/pdf?id=euqNpvs4sb) | Indexed methods explicitly describe informative anchors and few-shot prediction. | Shared-control-aware allocation and cross-context query-specific guarantees are not established by the available excerpts. | **High-priority uncertainty:** direct PDF blocked; full title/authors not verified. |
| [Multi-axis screen-design manuscript](https://openreview.net/pdf/b16b6eae7237923d23630b07290115f7b229b7a2.pdf) | Indexed text discusses biological-context selection and multidimensional atlas design. | Whether it already jointly allocates intervention breadth, cell depth, and negative controls for transfer must be checked. | **High-priority uncertainty:** workshop header only; bibliographic identity and full method unresolved. |
| [Transductive linear bandits](https://papers.neurips.cc/paper_files/paper/2019/hash/8ba6c657b03fc7c8dd4dff8e45defcd2-Abstract.html) | Different measurement/query sets and sequential design for linear decision problems. | A biological setting with learned, noisy source-response features and shared recipient controls. | Official NeurIPS abstract. Classical design must be a baseline, not claimed as invented here. |

## Additional counterevidence to an easy story

[PerturbedVAE](https://proceedings.mlr.press/v306/jiang26ad.html) already studies perturbation-specific representations and their identifiability. [LCD/CLIPR](https://arxiv.org/abs/2601.15341) connects generative dynamics to causal-effect identification under an explicit linear-drift assumption. The project cannot claim to introduce causal identifiability to single-cell ML.

[AmbiModBench](https://arxiv.org/abs/2609.32527), submitted September 26, 2026, already audits shared-background effects, gene-coordinate permutations, and representation coverage. Consequently, adding specificity metrics or plotting a coverage curve alone is insufficient novelty.

The [X-Cell/X-Atlas-Pisces manuscript](https://www.cdn.xaira.com/papers/X_CELL_V1_0316_final.pdf) also reports benefits from scale and diverse perturbation-context data. Its relevant discussion was available through indexed excerpts; full-paper access exceeded the web reader's size limit. This is evidence against assuming that scaling can never help, not independent confirmation of its performance claims.

## Ideas rejected during this search

1. **“A causal virtual cell that generalizes to a new context.”** Too broad; direct competitors already make closely related claims.
2. **“Use active learning to choose important gene knockdowns.”** Extensively occupied by experimental-design, hit-discovery, and agent work.
3. **“Add uncertainty or abstention to cross-context response transfer.”** PerturbMap already includes reliability and query-adaptive harm control; a generic wrapper would have a weak claim.
4. **“Show that response metrics hide failures.”** Important but already developed in recent benchmarks and geometry studies.

## Candidate claim that survives, provisionally

> Develop and evaluate a transfer-specific acquisition policy that jointly chooses recipient calibration interventions, perturbed-cell allocation, and shared negative-control allocation, targeting identifiability and error on a fixed set of source-observed but recipient-unmeasured interventions.

The distinct scientific object is the **cost of obtaining enough information to support a query**, including when no affordable calibration panel can do so. Candidate technical additions are correlated-noise design, uncertainty in learned source features, and bias-aware stopping. Each needs comparison with a classical design adapted to the same information interface.

This is a high-novelty **research hypothesis**, not a verified priority claim. No inspected source conclusively establishes the entire combination; incomplete manuscript access prevents inferring that nobody has done it. The project should proceed only through a short feasibility phase until the two closest unresolved manuscripts have been checked.

## Conditions that invalidate the claim

- A prior method already implements the same joint allocation problem with an equivalent transfer estimand and convincing evaluation. Compare directly or abandon the novelty claim.
- An off-the-shelf transductive design with a nuisance intercept matches the proposed policy. Report an application study only if the empirical finding is itself substantial; do not relabel ordinary optimal design as a new algorithm.
- The apparent gains disappear when query labels are sealed, all calibration cells are charged, and baseline methods get identical controls.
- Changes in recipient mechanisms are not captured by a low-dimensional transfer relation, so other interventions cannot constrain query responses. A useful negative finding would be a reproducible boundary, not a claimed universal solution.

The [evaluation plan](evaluation-plan.md) turns these objections into experiments rather than leaving them as discussion points.
