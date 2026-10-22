# Project proposal

Working title: **Which experiment makes a virtual cell prediction identifiable? Budgeted calibration across cellular contexts.**

## Research question

Can a measurement policy reduce the cost of predicting a fixed set of perturbation effects in a new cellular context by deciding jointly:

1. Which additional intervention to measure in that context;
2. How many cells to allocate to each measured intervention;
3. How many cells to allocate to the shared negative controls;
4. When a requested response remains unsupported and should be deferred?

The primary target is research-use response prediction, not causal-network recovery or clinical treatment selection. The initial contribution should work with a transparent transfer model; a foundation model is an optional later component.

## Information setting and estimand

Let `s` denote a source context, `t` the recipient context, `p` a perturbation, and `0` a matched non-targeting control. Define the population response on a declared expression transformation `T`:

\[
\Delta_{t,p}=E[T(X)\mid t,p]-E[T(X)\mid t,0].
\]

This is a contrast between assayed cell populations. If survival or capture depends on treatment, it is not automatically the effect on the original population. If `T` is log-normalization, the estimand is a difference in transformed means, not a log fold change of raw mean counts.

Source responses for the query interventions are available. Recipient controls and a paid set of recipient calibration interventions are available. Recipient responses for the final query identities are sealed throughout acquisition and model selection. The query set is fixed before acquisition and excluded from the purchasable recipient panel in the primary experiment.

This is a **source-observed, recipient-unmeasured** task, closely related to PerturbMap's interface. Its novelty must come from experimental acquisition rather than the interface alone. [PerturbMap](https://arxiv.org/html/2607.28090v1).

For the first method, construct a low-dimensional feature vector `phi_p` from source response profiles. Fit a recipient response map to acquired calibration data. A scalar version targets a fixed gene program `w`:

\[
E[w^T T(X)\mid t,p]=\mu_{t,0}+\phi_p^T\theta_t+b_{t,p}.
\]

Here `b` is transfer-model error; pretending it is zero is a testable approximation, not a biological law. A constant coordinate in `phi` can represent a shared perturbation response. Controls have treatment-feature vector zero. Multivariate prediction can fit several recipient coefficients while retaining full-gene evaluation.

## Candidate method

**Stage A: estimate useful source coordinates.** Fit PCA or a reduced-rank representation using permitted source data. Start with ranks 4, 8, 16, and 32, chosen using development contexts. Keep a source-copy and affine-ridge comparator. Avoid using recipient query responses to learn a response basis.

**Stage B: model the observation process.** Estimate measurement variance from paid pilot cells or allowed source data. Represent the covariance induced by a shared recipient control pool. Use guide/batch blocks when available, rather than treating every cell as an independent experimental replicate. Propagate source-feature estimation error through resampling as an empirical sensitivity check.

**Stage C: choose a paid action.** An action either opens a new calibration intervention, adds a disjoint block of cells to an opened intervention, or enlarges the control pool. Charge setup cost for new interventions and per-cell cost for additional observations. All pilot and validation observations count toward the same budget.

The first acquisition rule minimizes worst-query linear uncertainty per unit cost using the nuisance-aware information matrix in [technical notes](technical-notes.md). It is an adaptation of classical transductive design, not an algorithmic novelty claim. [Fiez et al.](https://papers.neurips.cc/paper_files/paper/2019/hash/8ba6c657b03fc7c8dd4dff8e45defcd2-Abstract.html).

The research extension is a **bias-aware acquisition rule**: maintain several plausible transfer fits and residual models learned on development contexts, and favor actions expected to shrink disagreement on the fixed recipient query set. Residual-bias penalties cannot be guaranteed valid on arbitrary new mechanisms. Their calibration must be assessed on genuinely held-out contexts. Compare this extension directly with the classical rule before attributing novelty to it.

**Stage D: report supported predictions and unresolved queries.** Return the point prediction, design-support diagnostic, empirical error estimate, and remaining budget. A query outside the observed feature span must be flagged even if ridge regularization gives a confident point prediction. Under model misspecification, intervals are empirical until their assumptions are justified; no distribution-free coverage claim is proposed.

## Falsifiable hypotheses

| Hypothesis | Planned test | Evidence against it |
| --- | --- | --- |
| H1: Joint acquisition improves transfer per unit cost. | Fixed-budget query-effect error curves against matched classical and random policies. | No material improvement over the strongest matched baseline. |
| H2: The best depth/breadth balance depends on response geometry and noise. | Vary mechanism shifts, rank coverage, and measurement noise separately in simulation; inspect stratified real-data curves. | The same simple fixed allocation performs equivalently throughout. |
| H3: Explicit shared-control covariance changes useful choices. | Equal-information ablation that removes only the off-diagonal covariance terms. | No allocation or error improvement in regimes with substantial control noise. |
| H4: Bias-aware diagnostics identify queries that should be deferred. | Risk-versus-retained-query curves on sealed recipient queries; compare simple distance and uncertainty scores. | Apparent reliability is explained entirely by easy or near-null queries, or vanishes on an external context. |

These are proposed experiments. The [toy calculation](technical-notes.md) establishes only elementary consequences of its assumptions.

## What a strong paper would contribute

- A formal costed acquisition problem that distinguishes intervention coverage, sampling precision, and shared-control uncertainty.
- A method that improves over an information-matched transductive-design baseline, or a strong empirical finding explaining why the classical method suffices.
- A replay benchmark with sealed queries, biological replication limits, and explicit accounting of all acquired measurements.
- A measured boundary showing when a calibration panel supports transfer and when query-specific mechanisms force direct measurement.

The project has high interdisciplinary upside if it changes screen-design choices. A stronger biological result would require prospective experiments; retrospective transcriptomic improvements alone support a narrower claim.
