# Independent literature verification for implementation

Audit date: **October 21, 2026**. This is a bounded follow-up audit of the closest competitors, not a systematic review. It updates the evidence state without editing the original dossier. Direct primary manuscripts, indexed primary excerpts, institutional publication lists, and author documentation are distinguished below. No published performance result was reproduced.

## Outcome

The two unnamed/partly named OpenReview leads can now be assigned bibliographic identities. Their full methods still could not be retrieved directly because OpenReview served a verification page. The central transfer baseline, PerturbMap, is independently confirmed from its primary arXiv record and HTML methods.

Two important additional predecessors were missing from the dossier: **IterPert** and **PerturbPlan**. Together they rule out broad claims that prediction-directed experiment selection or cost-aware cell/control planning is new. The remaining candidate contribution is the specific cross-context prediction problem with joint intervention/depth/control acquisition and correlated measurement errors. Priority for that combination remains unproven.

## Verification ledger

| Item | Newly checked evidence | Status and consequence |
| --- | --- | --- |
| PerturbMap identity | Primary [arXiv record](https://arxiv.org/abs/2607.28090) and [HTML manuscript](https://arxiv.org/html/2607.28090v1). | **Verified:** title, authors Panpan Cui/Yiqi Liu/Wenhao Sun, July 30, 2026 submission, and preprint identity. The dossier's metadata agree. |
| PerturbMap method scope | Primary HTML sections 3-4 and relevant evaluation sections. | **Verified:** source-query measurements are allowed; recipient-query effects are held out. Reliability fusion and a query-adaptive harm-control ablation already exist. Generic gating is not a new contribution. |
| CausalPert identity | Indexed primary [OpenReview PDF](https://openreview.net/pdf?id=euqNpvs4sb), plus indexed official author-search results. | **Partly resolved:** exact title and authors recovered; full direct methods remain unverified. Use workshop attribution, not an inferred main-conference acceptance. |
| Multidimensional design identity | Indexed primary [PDF](https://openreview.net/pdf/b16b6eae7237923d23630b07290115f7b229b7a2.pdf), institutional list, and author page. | **Resolved bibliographic identity:** Zheng et al., described below. Full direct manuscript access remains limited. |
| Equivalent complete joint acquisition method | Targeted searches for prediction-directed acquisition, biological-context selection, control allocation, and Perturb-seq design. | **Not established either way.** No absence or priority claim follows from a bounded search or inaccessible papers. |

## CausalPert: recovered identity and scope

**Title:** CausalPert: Grounding LLM Hypotheses in Regulatory Networks for Gene Perturbation Prediction.

**Authors:** Marc Boubnovski Martell, Josefa Lia Stoisser, Lawrence Phillips, Aditya Misra, Robert Kitchen, Jesper Ferkinghoff-Borg, Jialin Yu, Philip Torr, and Kaspar Märtens.

The indexed primary PDF names these authors and describes directed regulatory hypotheses, few-shot prediction, and informative-anchor selection. The indexed [official OpenReview author search](https://openreview.net/search?content=authors&group=all&sort=cdate%3Adesc&source=forum&term=~Kaspar_M%C3%A4rtens1) lists **MLGenX 2026 Poster**. The PDF's generic ICLR header should not be presented as proof of main-conference acceptance. [Primary PDF](https://openreview.net/pdf?id=euqNpvs4sb).

**Remaining uncertainty:** the complete algorithm, exact acquisition objective, and treatment of measurement/control budgets could not be independently inspected. The indexed excerpts establish close prior art, not the absence of the proposed extension.

## Multidimensional design: recovered identity and scope

**Title:** Beyond single-axis designs: multi-objective optimization for complex perturbation atlases.

**Authors:** Zihe Zheng, Soroor Hediyeh Zadeh, Jenni Liu, and Fabian Theis. The author spelling varies in capitalization/hyphenation across primary listings.

The [Helmholtz institutional publication list](https://www.helmholtz-munich.de/computational-health-center/conference-contributions) and [coauthor publication page](https://soroorh.github.io/) corroborate the identity; the latter assigns it to **ICLR 2026 MLGenX**. The institutional link resolves to [OpenReview forum identifier FIAgwjf3i1](https://openreview.net/forum?id=FIAgwjf3i1).

Indexed primary methods describe Bayesian optimization of donor, cell-type, and cytokine axes using HuCIRA, with multiple objectives and sensitivity analysis. This is direct prior art for multidimensional biological experiment design. [Primary PDF](https://openreview.net/pdf?id=FIAgwjf3i1).

**Remaining uncertainty:** those excerpts do not settle whether the complete work includes cell-depth or shared-control allocation. Do not report those features as absent without the full method. The title/authors should no longer be called unknown, while the full-method limitation should remain.

## Missing predecessor: IterPert

Huang, Lopez, Hütter, Kudo, Rios, and Regev, **Sequential Optimal Experimental Design of Perturbation Screens Guided by Multi-modal Priors**. Preprint posted December 13, 2023, DOI [10.1101/2023.12.12.571389](https://www.biorxiv.org/content/10.1101/2023.12.12.571389v1); the [RECOMB 2024 proceedings](https://link.springer.com/book/10.1007/978-1-0716-3989-4) list the chapter. An [author publication page](https://biologicalml.org/publication/iterpert-recomb/) corroborates the authors and venue; [author code](https://github.com/Genentech/iterative-perturb-seq) is linked publicly.

Its acquisition objective improves predictions for remaining unprofiled perturbations using multimodal priors. This is closer to the proposal than a pure hit-discovery baseline. **Prediction-directed acquisition is therefore already occupied.** An adaptation must be labeled as such when its feature inputs, predictor, or budget interface differ. Cross-context transfer and joint cell/control allocation require separate evidence.

## Missing predecessor: PerturbPlan

Niu, He, Galante, Gschwind, Ray, Steinmetz, Engreitz, and Katsevich, **PerturbPlan: An analytical framework for designing Perturb-seq experiments**. The [primary preprint record](https://www.biorxiv.org/content/10.64898/2026.05.22.727199v1) and [PubMed record](https://pubmed.ncbi.nlm.nih.gov/42239142/) identify a May 23, 2026 preprint, DOI `10.64898/2026.05.22.727199`; PMC indexing does not make it a peer-reviewed journal article.

The directly inspected [author app documentation](https://katsevich-lab.github.io/perturbplanApp/articles/perturbplanapp.html) and [cost-constrained API](https://katsevich-lab.github.io/perturbplan/reference/cost_power_computation.html) expose power/cost design, cells per target, reads per cell, non-targeting guides, and control-group choices. The objective is detection of perturbation-expression associations, not the proposal's sealed-query prediction estimand. Nevertheless, **cost-aware cell/control design alone is not novel**. A prediction error reduction does not demonstrate adequate association-testing power, and vice versa.

## Concrete implications for implementation

1. **Credit classical and existing biological design.** Present the package initially as a reproducible acquisition study. Do not assert a new field, first use of active learning for unmeasured responses, or first allocation of controls.
2. **Make the comparison objective explicit.** Separate prediction-error reduction from hit discovery, association-testing power, and multi-objective atlas optimization. A baseline adapted from another objective needs its original purpose documented.
3. **Specify baseline fidelity.** A PerturbMap-style reproduction needs its low-rank coordinates, recipient base, affine source experts, and paid disjoint validation calibration documented. A simplified ridge-plus-fusion model is an adaptation, not an exact reproduction. No author implementation for PerturbMap was verified in the inspected manuscript links.
4. **Match acquisition information.** IterPert-style multimodal priors and CausalPert's external knowledge can change the information budget. Either provide identical permitted priors or report this difference instead of interpreting a head-to-head score as isolated acquisition superiority.
5. **Charge model selection.** If recipient observations calibrate route weights, feature rank, gates, variance, or validation, they are acquired data. They cannot become a free validation set just because a predecessor supplies one.
6. **Keep the narrow contribution falsifiable.** The candidate extension should beat covariance-correct classical design under identical features, control access, costs, and query sealing. Otherwise report the resulting scientific boundary or negative result.
7. **Record citations and adaptations per method.** Each method artifact should identify the reference, source implementation/version if any, omitted components, adapted objective, predictor inputs, charged validation observations, and tuning interface.

## Claim status after this audit

**Supported:** there is close prior art for transfer, anchor selection, prediction-directed acquisition, multidimensional design, and cost/power allocation. These need attribution and suitable comparators.

**Not established:** that any identified method already solves the complete proposed joint acquisition problem, or that none does. Full-method access and a broader systematic review would be needed for a stronger priority statement.

**No contradiction found** in the inspected PerturbMap metadata or the dossier's narrow description of its reliability gate. **Stale uncertainty corrected:** both OpenReview paper identities can now be named; only their complete method inspection remains unresolved. Avoid upgrading workshop work to main-conference acceptance based on a PDF header.

The implementation can proceed while keeping novelty provisional. No positive result or publication-priority conclusion follows from this literature audit.
