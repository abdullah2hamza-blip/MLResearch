# Manuscript and GitHub release review, October 28, 2026

This is the historical prepublication-readiness review. The later [public-release checklist](public-release-checklist.md) governs the actual GitHub/Kaggle release and the restored canonical assistance disclosure.

This review examines the current manuscript, code and distributable artifacts afresh. The October 23 audits remain historical evidence; they do not certify this revision. The author has confirmed personally reviewing and verifying the work. Author statements are being edited at the author's direction; venue submission and public deposition await the author's next instructions.

The supported release target is the Python/uv GitHub repository and its accompanying manuscript/source/code archives. The repository remains private. There is no Kaggle notebook, Kaggle dataset metadata or Kaggle competition submission in this release, and no claim of a tested Kaggle execution. A Kaggle integration would be a separate deliverable. No platform upload or visibility change is part of this readiness review.

## Acceptance criteria

| Requirement | Evidence required | Current state |
| --- | --- | --- |
| Scientific claims and prior work | Full-manuscript internal review; independent headline arithmetic and primary-source checks; resolved essential findings | Passed; [scientific review](release-scientific-review-v2.md) found no unresolved essential scientific correction within the stated scope. |
| Mathematical/code fidelity | Fresh inspection of GLS, paid validation, support, acquisition and prediction/scoring boundaries | Passed in the inspected scope; [software review](release-software-review-v2.md) includes an independent 200-case algebra check. |
| Current author statements | Requested statement edits in editable prose, compiled PDF and all new manuscript/code archives; no invented human peer review | Passed in the current manuscript and refreshed archive payloads; author-confirmed review and responsibility retained. |
| Scientific evidence integrity | Retained-payload authentication, all 32 robustness contrasts, numerical registry/table regeneration and unchanged numerical source/configuration | Passed: 150 manuscript inputs/25 outputs authenticated; registry and 12 TeX assets reproduced byte-for-byte in the checkout and clean archive; 23 numerical package payloads equal the frozen source. |
| Software checks | Locked installation, full tests, lint/format/type checks and offline workflow | Passed: 123 tests, 72-file Ruff checks, 22-module mypy, locked installation and 19 clean-wheel offline workflow commands. |
| Reliable packaging | Source/PDF/bibliography binding, no stale manuscript packaging, inventories/hashes/CRC, clean unpack/build and code/evidence verification | Passed: 12 regression tests plus a real stale-package CLI refusal; full and minimal source archives independently rebuild the exact final PDF. |
| Reader access and licensing | Valid software/manuscript attribution and citation metadata, current release guide, portable commands, no redistributed raw expression or caches | Passed: citation validates against CFF 1.2.0; MIT notice and source payloads verified in distributions; data/manuscript terms remain distinct. Public reader access still requires the author-directed deposit. |
| Repository readiness | Current-file and history scan for recognizable credentials, GitHub file-size checks, working documentation links, explicit scope of prior CI | Passed: current/nested payload scan, 997 reachable Git blobs, file sizes and editable links checked; historical snapshot links have documented resolution. Prior CI is explicitly scoped to its base revision. |
| PDF quality | Successful build, no unresolved references/overfull boxes, all changed pages inspected, remaining pages compared with reviewed version | Passed: 28 pages, author statements together on page 17; pages 16/17 inspected and the other 26 pages pixel-identical to the reviewed version; no unresolved references or overfull boxes. |

## Findings and resolution

1. **Stale manuscript packaging (release correctness, fixed).** The packager checked generated assets but accepted any existing PDF and compiled bibliography. Editing a handwritten manuscript section without rebuilding could silently produce contradictory release artifacts. The build and package tools now bind the complete manuscript input inventory, final PDF and compiled bibliography, with 12 regression checks for stale or changed inputs. An actual edited manuscript was also rejected by the real packaging command before it created an archive.
2. **Historical snapshot links (documentation).** Nine relative links inside immutable, copied protocol snapshots resolve from their original `docs/` location, rather than their snapshot subdirectory. Those authenticated snapshots must keep their exact bytes. The current reproduction guide will explain how to resolve them; current editable documentation links are checked separately.

## Interpretation of readiness

The scientific scope remains a conditional computational evaluation of one fixed acquisition surrogate. It does not establish biological transportability, general superiority, prospective laboratory savings, equivalence or independent biological replication. Internal reviews and engineering verification do not constitute external peer review or acceptance.

The [fresh local check record](evidence/release-local-checks-v2.json) records commands, inspected source hashes, PDF quality, exact clean builds, retained evidence, schema/credential/link checks and their limits. Final current-archive member hashes and the comparison with the clean-tested candidate are recorded in `output/release/release-manifest-v0.2.0.json` and `output/release/final-payload-verification-v0.2.0.json`. These output records are outside the code archive to avoid a self-referential checksum cycle. The final code archive incorporates only the documented release-tool, author-statement, review and completion-record changes; numerical package sources/configurations and historical evidence remain unchanged.

The current changes are prepared locally for GitHub. The existing remote `main` revision is `3302c7c17c1aab7bd8c4f7408636d0b4d26de9a9`, whose Windows/Ubuntu workflow passed. That historical CI is not presented as a run of the current uncommitted release edits. The fresh current-tree tests and clean offline workflow are local checks on Windows/Python 3.12.

Remaining author/platform actions are the requested next instructions for final author statements, a decision about public repository/archive access, selection of a venue and upload under the author's account, and inspection of any platform-generated PDF. These are publication actions, not unresolved scientific or artifact repairs identified by this review.
