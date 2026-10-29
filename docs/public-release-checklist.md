# Public research release checklist

Release target: the existing `abdullah2hamza-blip/MLResearch` repository, tag `v0.2.0`, and the verified Kaggle account `abdullah2hamza`. The manuscript is a technical report, not a claim of journal acceptance or independent human peer review. Ordinary commits/pushes, release assets, Kaggle publication and the existing repository's public-visibility transition are authorized for this task. No new paid computation, authorship change, credential rotation, destructive history rewrite or force-push is included.

The earlier October 28 readiness review is historical. This checklist tracks the subsequent public-release task, including restored assistance statements and actual hosted publication/execution.

| Gate | Current evidence/state |
| --- | --- |
| Repository identity and workflow | Existing owner/repository verified through connected GitHub and the existing Git credential; only remote `main`, unprotected; `v0.2.0` unused. Ordinary main push, no mirror/force push. |
| Kaggle identity and existing assets | Signed-in UI verifies Abdullah Hamza, handle `abdullah2hamza`; the only existing resources are an unrelated Boundary Conformance dataset/notebook and an unused default starter draft, with no project inputs. They were not modified or run. |
| Exposure of history and hosted surfaces | [Exposure audit](public-release-exposure-audit.md) found no historical blocker; final new files, CI logs and public settings remain to be checked. |
| Claims and scientific evidence | [Claim-to-evidence map](claim-evidence-public-release.md) covers 18 claim groups, 12 generated assets, four figures and the inline study table; fresh saved-output arithmetic is distinguished from historical experimental execution. No essential scientific correction identified. |
| Current author statements and status | Restore the canonical assistance statement in manuscript, README, notebook and Kaggle descriptions; retain responsibility without extending a prior human-review attestation to new output. Canonical disclosure and technical-report wording are now present; no fresh human-review attestation is inferred. |
| Licenses and redistribution | Preserve MIT software, CC BY 4.0 paper/figures/tables and third-party terms; no raw expression or model weights to redistribute. Kaggle mixed bundle uses scoped Other terms, not a blanket new data license. Notebook's actual platform license requires verification. |
| Local tests and clean reproduction | Final local 145 tests, 77-file Ruff and 22-module mypy checks pass. New notebook saved-output/refusal tests and public-source provenance tests pass; historical 19-command clean-wheel workflow remains separately scoped. See [local verification](evidence/public-release-local-verification.json). |
| Kaggle executable subset | Notebook and authenticated three-CSV inputs are locally validated; no GPU, internet, new paid services or full-data experiment is required. Actual uploaded fresh-session execution remains required; the first upload was not performed because it requires tool approval. |
| Final manuscript | Build with established TeX toolchain; render and inspect every final page; authenticate source/PDF/bibliography bindings. Complete: all 28 final pages rendered and visually inspected; canonical assistance paragraph, report status, author metadata and no unresolved/overflow defects verified. |
| Clean tagged artifacts | Commit/tag final source through permitted workflow, build from clean tagged revision, record scientific snapshots separately from release commit, inventories/checksums/environment and explicit release file list. Pending. |
| GitHub release and public visibility | Stage release and assets; after exposure/check gates pass, change this existing repository to public and verify actual release/tag/commit, security/workflow state and unauthenticated downloads. Pending. |
| Kaggle publication and cross-links | Publish the intended dataset/notebook versions only after actual execution; verify public inputs/outputs, disclosures, licenses, downloads and compatible GitHub/manuscript links. Pending. |

This file records preparation at source freeze. Actual upload/execution/public-access status is closed by the publication-verification asset on the versioned GitHub Release; pending hosted actions here are not a claim that publication occurred.

Canonical assistance wording is in [the assistance record](ai-assistance.md). Final publication records must distinguish prepared, uploaded, executed, public and experimentally reproduced. No hosted action is complete merely because a local artifact or draft exists.
