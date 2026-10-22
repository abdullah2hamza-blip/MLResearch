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

- [The controlled simulation protocol](controlled-study-protocol.md) now freezes 14 scenarios, five generative worlds, five acquisition seeds and 14 policies/ablations. A separate two-case, full-size smoke at world 81 completed in 73.8 seconds; its zero-discrepancy ledgers exactly matched classical acquisition. The full 70-case study has not yet completed. One worker is selected from the local memory audit.
- [Analysis version 2](retention-analysis-correction.md) corrects outcome-based variance tie breaking, retention denominators and backbone selection in all four retained pilot bundles. Primary error areas, paired comparisons and noise floors were verified unchanged.

## Requirement ledger

| Full specification requirement | Status | Authoritative evidence / remaining work |
| --- | --- | --- |
| 1. Evidence and scope | Partial | Follow-up audit written; full competitor-method inspection still limited. Novelty remains provisional. |
| 2. Package and CLI | Partial | End-to-end offline and real replay commands execute; controlled scenario/config support and bounded-worker smoke execute; updated hosted checks remain to be verified. |
| 3. Real data | Partial | Three inputs verified/audited/prepared; external compatibility and panel/replication limitations recorded; more metadata/QC analysis remains. |
| 4. Information boundary | Partial | Episode/scorer integration, no-free-observation path, ledgers/access records and adversarial invariance tests work; final tuning/access audit remains. |
| 5. Model and uncertainty | Partial | Source coordinates, GLS and span diagnostics execute; source/block uncertainty and valid empirical interval analysis remain. |
| 6. Matched baselines | Partial | Eight policies, six acquisition ablations and seven predictors execute; paid shrinkage includes an expanded grid and null candidate. Tuned fixed grid and prior-method fidelity remain. |
| 7. Proposed extension | Partial | Fixed-kernel discrepancy surrogate implemented and negative in both initial pilots; full ablations and sharper bias model remain. |
| 8. Verification/CI | Partial | 62 tests/lint/types, isolated-wheel replay, and Linux/Windows hosted CI passed; additional full-study tests remain. |
| 9. Empirical study | Partial | Five-seed synthetic and Frangieh pilots finished; simulation grid and frozen external evaluation remain. |
| 10. Scientific analysis | Partial | Error areas, paired conditional summaries, noise floors, strata/coverage fields and allocation evidence exist; biological/common-control uncertainty, permutations and ablations remain. |
| 11. Research artifacts | Partial | Actual retained pilot tables/figures/metrics, methods, provenance and findings exist; final claim assessment remains. |

## Resume from authoritative state

Inspect `data/raw/*.provenance.json`, `data/raw/*.part`, `data/prepared/*/manifest.json`, and the current process/session state before restarting a download or preparation. A partial file or `state=preparing` alone does not prove a live job. A verified live tool-session handle must be polled rather than restarted due to an observation timeout.

Both external episode builds are complete with unchanged code during each build: 394 candidates, 131 queries and 7,226 aligned genes per direction. `ridge_cv` implements stronger shrinkage using only paid labels with a tested shared-control correction, and its development follow-up is complete. No download/preparation/replay job remains live at this milestone. Next: resolve the shrinkage-grid boundary with permitted development observations; implement the remaining matched comparator/ablation interfaces; execute the controlled simulation grid; address common-control/source/block uncertainty; then freeze and run both external directions. Retain the 4,960-unit fixed development-resource accounting alongside incremental recipient budgets. Preserve both exploratory pilots and their negative findings. Do not silently promote development results to external confirmation.
