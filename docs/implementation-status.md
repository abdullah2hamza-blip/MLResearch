# Implementation status

Last substantive update: October 22, 2026 (America/New_York). The implementation goal remains **active**. This file records completed artifacts and outstanding requirements, not a claim of study completion.

## Current evidence

- Locked numerical/data/plotting and development dependencies are installed in the project environment.
- The Frangieh RNA file was downloaded and verified at 1,458,928,348 bytes against the pinned published checksum; its local sidecar records SHA-256.
- The [actual H5AD audit](evidence/frangieh-rna-audit.json) reports 218,331 cells, 23,712 unique genes, CSC encoding, and 249 perturbation labels including controls across three contexts.
- The [metadata eligibility inventory](evidence/frangieh-eligibility.json) applies `MOI=1`: 126,966 cells are eligible, of which 64,294 are retained by the declared caps. There are 248 non-control interventions in each context; this does not yet prove a valid sealed-query split or independent biological replication.
- The two Replogle RNA inputs are verified, audited and prepared: each has 50,912 retained cells across the 525 metadata-overlapping targets plus controls. Their raw gene panels have 8,563 and 8,749 genes; exact aligned-gene eligibility is recorded in `evidence/replogle-overlap.json`.
- Episode construction, eight acquisition policies, six acquisition ablations, seven crossed predictors, predict-before-score replay, source snapshots, and standalone result reporting are implemented.
- **62 tests passed** locally, including sealed-query/assessment-control perturbation invariance, exact gene alignment, conflicting-guide rejection, independent cost recomputation, source-snapshot integrity, deterministic reruns, relocation of a frozen episode with its data, and covariance-correct paid-label ridge validation against independent Monte Carlo. Lint/format/type checks passed. The built wheel imported its registry and executed an offline replay from an isolated installation target. [Hosted CI evidence](evidence/ci-c347560.json) confirms all checks and the offline example passed on both Linux and Windows for published commit `c347560`.
- The first five-seed synthetic and real Frangieh pilots executed. [Development findings](development-findings.md) retain the negative extension result and the stronger finding that zero effect beats the measured methods in the real pilot's primary endpoint.
- The separate five-seed Frangieh v2 follow-up executed at code commit `c347560` with `ridge_cv`. Strong shrinkage reduced errors and altered policy rankings, while zero effect remained best and the extension remained worse than classical worst-query. All 120 selections hit the largest penalty; the final predictor is not yet frozen.
- [Independent literature verification](literature-verification.md) recovered previously unresolved paper identities and identified IterPert and PerturbPlan as important missing predecessors.

- [The controlled simulation protocol](controlled-study-protocol.md) now freezes 14 scenarios, five generative worlds, five acquisition seeds and 14 policies/ablations. A separate two-case, full-size smoke at world 81 completed in 73.8 seconds; its zero-discrepancy ledgers exactly matched classical acquisition. All 70 full-study cases have now completed with no failures; the initial sentence records the earlier smoke milestone. One worker is selected from the local memory audit.
- [Analysis version 2](retention-analysis-correction.md) corrects outcome-based variance tie breaking, retention denominators and backbone selection in all four retained pilot bundles. Primary error areas, paired comparisons and noise floors were verified unchanged.

- [Completed controlled findings](controlled-study-findings.md) retain all 70 cases. The extension is 1.41% worse in the base setting and 5.08% better under nonlinear shift; other comparators remain competitive. Source noise can make conditional numerical support misleading. All 350 zero-weight/classical ledgers are identical.
- [Development tuning](development-tuning-findings.md) evaluated nine fixed grids and five weights at seven backbones. The selected grid is fraction .125/depth 8 and weight 1, but zero remains best and 163/210 ridge-CV selections are null. Updated fixed development cost: 6,344 units.
- [Hosted CI at 536e822](evidence/ci-536e822.json) passed both matrices, including the bounded two-worker study smoke. [Pending prototypes](evidence/pending-analysis-prototypes.zip) preserve the prior-method reconstruction, paired common-control analysis and generic development accounting, with 12 prototype checks and three typed/linted modules. These are not yet production CLI components.

## Requirement ledger

| Full specification requirement | Status | Authoritative evidence / remaining work |
| --- | --- | --- |
| 1. Evidence and scope | Partial | Follow-up audit written; full competitor-method inspection still limited. Novelty remains provisional. |
| 2. Package and CLI | Partial | End-to-end offline and real replay commands execute; controlled runner and two-worker smoke pass on Windows and Linux; pending analysis prototypes require CLI integration. |
| 3. Real data | Partial | Three inputs verified/audited/prepared; external compatibility and panel/replication limitations recorded; more metadata/QC analysis remains. |
| 4. Information boundary | Partial | Episode/scorer integration, no-free-observation path, ledgers/access records and adversarial invariance tests work; final tuning/access audit remains. |
| 5. Model and uncertainty | Partial | Source coordinates, GLS and span diagnostics execute; source/block uncertainty and valid empirical interval analysis remain. |
| 6. Matched baselines | Partial | Eight policies, six acquisition ablations and seven predictors execute; paid shrinkage includes an expanded grid and null candidate. A nine-point fixed grid and five discrepancy weights were evaluated on development data. Prior-method reconstruction is prototyped; matched integration remains. |
| 7. Proposed extension | Partial | Fixed-kernel discrepancy surrogate implemented and negative in both initial pilots; six allocation/covariance/extension ablations executed in the controlled grid; empirical benefit is mixed and prior mismatch remains. |
| 8. Verification/CI | Partial | 62 core tests/lint/types and Linux/Windows CI at 536e822 pass; 12 separate prototype tests pass. Full-study zero-weight equivalence was checked across 350 ledgers. |
| 9. Empirical study | Partial | Five-seed pilots, all 70 controlled simulation cases and 14-policy development tuning finished; frozen external evaluation remains. |
| 10. Scientific analysis | Partial | Error areas, paired conditional summaries, noise floors, strata/coverage fields and allocation evidence exist; controlled permutations/ablations and source-support stress now execute; external biological/common-control uncertainty and source propagation remain. |
| 11. Research artifacts | Partial | Actual retained pilot tables/figures/metrics, methods, provenance and findings exist; final claim assessment remains. |

## Resume from authoritative state

Inspect `data/raw/*.provenance.json`, `data/raw/*.part`, `data/prepared/*/manifest.json`, and the current process/session state before restarting a download or preparation. A partial file or `state=preparing` alone does not prove a live job. A verified live tool-session handle must be polled rather than restarted due to an observation timeout.

Both external episode builds are complete: 394 candidates, 131 queries and 7,226 aligned genes per direction. No experiment remains live at this milestone. All 70 controlled cases and development tuning are complete; source/analysis archives and actual results are authoritative.

Next integrate the pending prototype archive into the typed CLI, add a mean-query classical variance comparator aligned with average MSE, verify the feasible prior-method reconstruction in matched replay, and finish source/common-control/batch uncertainty analyses. Then freeze all external choices and run both directions, retaining the original and development-selected discrepancy weights. The two directions reuse the same dataset pair and are not independent biological replications; no cross-direction result may inform tuning. Future external configurations must use the 6,344-unit development record. Keep the earlier 4,960-unit record unchanged for the already-frozen simulation study. Preserve every negative result and do not mark the goal complete before the full external/final-report requirements are met.
