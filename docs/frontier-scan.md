# Frontier comparison

Snapshot: October 21, 2026. This is a focused opportunity search, not an exhaustive ranking of machine learning. The selection assumes one researcher, access to ordinary research computing, and no guaranteed laboratory partner. Those are planning assumptions, not facts about the user's resources.

## Four current frontiers

| Frontier | Current primary evidence | Candidate opportunity | Main obstacle | Judgment for this repository |
| --- | --- | --- | --- | --- |
| Perturbation models and virtual cells | The 2026 challenge tests unseen cellular contexts; recent methods address transfer and intervention-specific information. [Arc](https://arcinstitute.org/news/virtual-cell-challenge-2026), [PerturbMap](https://arxiv.org/abs/2607.28090). | Decide which recipient measurements make unmeasured responses predictable, including their depth and shared controls. | Causal shift, experimental noise, and extensive nearby prior art. | **Selected:** strong practical question, public experimental resources, inexpensive initial falsification. |
| Scientific foundation models for PDEs | A March 2026 study tests pretrained PDE models on shock/interface and fracture regimes. [Rautela et al.](https://arxiv.org/abs/2603.04354). | Allocate expensive solver calls where a surrogate's downstream decision is least reliable. | Existing uncertainty-driven active operator learning already occupies much of the generic idea. [Winovich et al.](https://doi.org/10.1016/j.jcp.2026.114791). | Strong backup, especially with a computational-physics collaborator; weaker immediate biological decision link. |
| Autonomous scientific agents | An October 13, 2026 preprint evaluates budgeted discovery campaigns and separately scores discovered designs and predictions on unseen designs. [Autonomous Science Bench](https://arxiv.org/abs/2610.18449). | Make agents select experiments that distinguish competing explanations rather than merely generate promising designs. | Harness effects, changing model access, and difficult attribution of gains to an algorithm. | Attractive, but a general agent system would make the first project harder to isolate. |
| Causal world models for embodied systems | A May 2026 benchmark evaluates paired physical interventions rather than independent video plausibility. [What-If World](https://arxiv.org/abs/2605.27589). | Acquire actions that distinguish visually similar but causally different environments. | Simulator validity, evaluation subjectivity, and video-generation cost. | High upside; less tractable than a numerical experimental-replay study here. |

These are research opportunities inferred from the papers, not claims that the papers themselves establish an unoccupied niche. The frontier examples are current through the cutoff; older work is included elsewhere when it can invalidate novelty.

## Why virtual cells win this comparison

**The target decision is concrete.** An experimentalist has a finite screen budget and a set of responses they need to predict. The useful output is a measurement plan and an honest account of which queries remain unsupported.

**There is a productive tension in the literature.** Context and mechanism-shift critiques challenge naive transfer, while models such as State and newer causal approaches report progress. The appropriate question is therefore where transfer becomes reliable, not whether modern models categorically work or fail. [State](https://doi.org/10.1016/j.cell.2026.07.052), [Latent Causal Diffusions](https://arxiv.org/abs/2601.15341).

**A falsifiable starting point is affordable.** Public single-cell data support retrospective comparisons of acquisition policies. The [data inventory](data-and-feasibility.md) verifies file availability rather than assuming it. The first experiment can use pseudobulk responses and linear transfer before considering pretrained models.

**The novelty can live in the decision problem.** A new architecture with a small improvement in expression correlation would be hard to distinguish scientifically. A protocol showing when to acquire breadth, depth, or controls could change how future datasets are collected. This is a proposed impact, not a demonstrated result.

## Interdisciplinary impact and its limits

| Discipline | Specific possible contribution | Evidence required |
| --- | --- | --- |
| Machine learning | Learning under structured shift with active, noisy supervision. | Gains over strong acquisition and transfer baselines at identical information and cost. |
| Causal inference | Distinguish response information that is identified by observations from information supplied by assumptions. | Explicit assumptions, counterexamples, and stress tests under mechanism changes. |
| Experimental statistics | Allocate perturbation and control measurements while accounting for shared noise. | Correct covariance treatment and improvements over classical optimal design. |
| Functional genomics | More informative calibration panels for a new cellular setting. | Independent-context replication and eventually prospective validation. |
| Other experimental sciences | Transfer the measurement-allocation formulation to another domain. | A real second-domain study; analogy alone does not establish generality. |

The immediate deliverable would help plan research experiments. Transcriptomic agreement does not by itself demonstrate therapeutic benefit or the discovery of a causal regulatory network.
