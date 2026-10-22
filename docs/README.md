# Machine learning frontier research

The [research report](research-report.md) gives the completed computational study's results and evidence-to-claim assessment. The frozen external extension is 0.565% and 0.0138% worse than classical worst-query acquisition in the two directions; no primary benefit is demonstrated. Full [external findings](external-evaluation-findings.md), [data dictionary](data-dictionary.md), [reproduction commands](external-reproduction.md) and [status ledger](implementation-status.md) connect the implementation to authoritative artifacts.

**Original dossier cutoff: October 21, 2026. Computational evidence updated October 22, 2026.** The proposal below is retained as the original research rationale. Its novelty potential is not a finding of the implemented study. Prospective biological validation remains outside scope.

## Recommendation

Investigate **budgeted identification of transferable perturbation effects** at the intersection of machine learning, causal inference, experimental design, and single-cell biology.

The practical question is: **When adapting a predictor to a new cellular context, should the next unit of experimental budget buy another perturbation, more cells for an existing perturbation, or more negative-control cells?** Optimize that choice for responses that will remain unmeasured in the new context.

The proposed setting starts with measured perturbation responses in source contexts and unperturbed cells in a recipient context. A small recipient calibration panel can then be acquired. The final query perturbations have source measurements but no recipient measurements. This separates learning to transfer an intervention from inventing an entirely unseen intervention's effects.

The high-novelty hypothesis is that **jointly selecting calibration interventions, measurement depth, and shared controls according to query-specific identifiability can improve the cost of reliable cross-context prediction**. The potentially publishable contribution is the acquisition problem and its validated solution. Low-rank transfer, active learning, uncertainty estimation, and causal motivation already have substantial prior art.

**Original proposal assessment:** high novelty potential, substantial interdisciplinary relevance, moderate confidence that this exact intersection is open. Novelty is provisional. The [implementation literature audit](literature-verification.md) recovered the two OpenReview paper identities and added important IterPert and PerturbPlan predecessors; full-method access remains limited. Prediction-directed acquisition and cell/control budgeting individually are already occupied. Their implications and an explicit rejection rule are documented in the [novelty audit](literature-and-novelty.md). No claim of being first is justified yet.

## Read the dossier

| Document | Purpose |
| --- | --- |
| [Frontier comparison](frontier-scan.md) | Compare four current research directions and explain the choice. |
| [Literature and novelty audit](literature-and-novelty.md) | Closest competitors, rejected ideas, and the remaining defensible gap. |
| [Project proposal](project-proposal.md) | Scientific question, assumptions, candidate method, and falsifiable hypotheses. |
| [Implementation objective](implementation-objective.md) | Execution scope, expert requirements, and completion criteria for the implementation goal. |
| [Implementation literature verification](literature-verification.md) | Recovered citations, missing predecessors, and baseline-fidelity requirements. |
| [Implementation guide](implementation-guide.md) | Executable commands, artifact layout, checks and reproduction. |
| [Milestone status](implementation-status.md) | Completed evidence and outstanding requirements. |
| [Implemented methods](implemented-methods.md) | Actual algorithms, paid validation, assumptions and approximations. |
| [Pilot protocol](pilot-protocol.md) | Settings frozen before the first real-data policy scoring. |
| [Controlled simulation protocol](controlled-study-protocol.md) | Frozen scenario matrix, paired replication, matched ablations and oracle diagnostics. |
| [Risk-retention correction](retention-analysis-correction.md) | Corrected diagnostic ordering and denominators; unchanged primary pilot findings. |
| [Development findings](development-findings.md) | Actual results, zero baseline, allocation evidence and negative findings. |
| [Controlled study findings](controlled-study-findings.md) | Completed 70-case simulation, mixed acquisition effects and source-support failure. |
| [Development tuning findings](development-tuning-findings.md) | Predeclared grid/weight selection and updated fixed development resources. |
| [Assessment uncertainty protocol](assessment-uncertainty-protocol.md) | Separate query, common-control measurement and technical-batch sensitivity scopes. |
| [Transfer comparator protocol](transfer-comparator-protocol.md) | Prior-method reconstruction and explicit fidelity choices. |
| [External data compatibility](external-data-compatibility.md) | Target-ID checks, protocol differences, attribution and limits. |
| [Technical notes](technical-notes.md) | Identifiability argument, shared-control covariance, and a reproducible toy calculation. |
| [Evaluation plan](evaluation-plan.md) | Information boundaries, baselines, metrics, ablations, and failure criteria. |
| [Data and feasibility](data-and-feasibility.md) | Verified public files, access evidence, resource estimates, and data-audit requirements. |
| [Roadmap](roadmap.md) | A staged project with decisions about continuation. |
| [References](references.md) | Primary sources with dates/status where verified and exact inspection limits. |
| [Research log](research-log.md) | Search strategy, competing interpretations, and unresolved evidence. |

## Why this is timely

Arc's 2026 Virtual Cell Challenge explicitly targets prediction in previously unperturbed cell contexts. That establishes a current community problem, although this proposal's acquisition of recipient perturbations defines a different task from the competition's zero-shot interface. [Arc announcement](https://arcinstitute.org/news/virtual-cell-challenge-2026).

The central research judgment is that a small team can investigate the **value of additional information** more effectively than it can compete on foundation-model scale. The initial study can replay existing experiments; prospective laboratory validation would be a later, separate collaboration.

## What is established here

The dossier defines the original hypothesis. The implemented study verifies pinned inputs, tests cooperative information boundaries, and executes pilots, a 70-case controlled matrix, development selection, both external directions and all declared controls. The resulting negative/failure evidence does not establish a novel acquisition benefit, biological identification or prospective laboratory savings. Read the research report for the supported claims and qualifications.
