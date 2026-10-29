# Pre-publication repository exposure audit

Reviewed October 28, 2026. This is an AI-assisted internal technical audit of the existing GitHub repository and its potentially exposed historical material. It is not independent human peer review or a public-release action. The review used read-only Git, Git LFS and authenticated GitHub APIs; it did not change visibility, publish assets, rotate credentials or rewrite history.

The verified repository is `abdullah2hamza-blip/MLResearch` (repository ID `1428609138`). At review it was private, with default branch `main` at `3302c7c17c1aab7bd8c4f7408636d0b4d26de9a9`. The complete remote Git reference namespace contains only that branch. There are no remote tags, releases, issues or pull requests; the wiki and discussions are disabled. The current connection reports repository administration/push permission. The publication workflow must independently confirm the intended signed-in identity in the UI.

## Inspected exposure surfaces

| Surface | Actual coverage and result |
| --- | --- |
| Remote refs and history | All remote refs enumerated; one branch, no other refs/tags. The reviewed branch has 14 commits. Only the owner's GitHub noreply author/committer identity was observed. |
| Historical Git payloads | Fresh scan of 995 blobs reachable from the verified remote revision, recursively decoding ZIP/gzip content. It examined 8,677 payload encounters, including 7,682 nested members; 7,643 distinct payloads represented 1,014,655,405 bytes after deduplication. No recognized credential/private-key pattern, sensitive archive filename or archive decoding error was found. |
| LFS/submodules | `git lfs ls-files --all` completed with no pointers. No `.lfsconfig` or `.gitmodules` exists. No relevant LFS object or submodule publication requirement was identified. |
| Historical figures/documents | All named unique historical PDF/PNG/SVG blobs were checked: 15 PDFs/42 pages, 43 PNGs and 43 SVGs. Decoded PDF text and metadata had no recognized credential patterns, embedded-file/JavaScript name trees were absent, PNG metadata had no EXIF, and SVGs had no script tags. The metadata keys were ordinary document/Matplotlib fields. This is not OCR of every historical pixel. |
| GitHub Actions | All 13 existing workflow runs and their 26 jobs were enumerated. Every run completed successfully. All 26 job logs were fetched and scanned: 1,719,325 decoded characters and 22,887 lines, with no recognized GitHub/OpenAI/AWS token, private-key or unmasked Basic-authorization-header matches. All 13 per-run artifact lists are empty. |
| Other hosted surfaces | No releases/assets, issues or PRs were returned; wiki/discussions are disabled. There is no corresponding historical hosted-content payload to inspect on those surfaces. |
| Existing workflow | `.github/workflows/checks.yml` uses `contents: read`, Python 3.12 and Windows/Ubuntu jobs. It contains no custom credential input or artifact-upload step. The branch collection reports `protected=false`. |

The [machine-readable record](evidence/public-release-exposure-audit.json) contains exact run/job IDs, counts, scan qualifications and API coverage. Raw logs and potential secret values are not included in this report. The existing [local release checks](evidence/release-local-checks-v2.json) additionally document the earlier current-file/nested-archive scan and distribution checks at their stated snapshot.

## Access limitations and resolved fallbacks

The connector rejected the direct tags and repository-level Actions-artifact collection URLs. These were covered using the complete Git reference namespace and all 13 supported per-run artifact lists. No collection exceeded the 100-item page used for its retrieval.

The branch-protection detail endpoint returned `403 Resource not accessible by integration`; this is a connector administration-scope limitation. The authenticated branch collection independently reports `protected=false`. Ruleset enumeration returned a feature-availability message requiring GitHub Pro or public visibility for the present private repository. Neither response establishes a hidden protection requirement. The release manager should inspect the actual UI and recheck applicable rules/security settings after the visibility transition.

A redundant terminal `git ls-remote` attempt failed in the restricted execution environment; live authenticated GitHub APIs successfully verified all remote refs. No failed read was presented as successful verification.

## Release workflow and remaining final checks

No recognized exposure blocker requiring credential rotation, deletion or history rewriting was found in the inspected historical/hosted scope. An ordinary non-force push to the existing `main` branch is consistent with its current unprotected workflow and prior history. No repository `AGENTS.md` or `CONTRIBUTING.md` requirement was found. The remote tag `v0.2.0` is unused and matches the existing scientific package version; recheck that it remains unused before creating it.

Local `refs/codex/*` snapshots exist but are not remote refs and were not selected for publication. Publish only the intended branch and release tag; do not use a mirror push. Keep raw/prepared expression, large prediction arrays, local environments, caches, private prompts and authentication files outside the public release. The distributable ZIP belongs in release assets rather than Git history.

The audit above is bound to the reviewed remote revision, not to future edits. Before changing visibility, scan the final commit, release archives, notebook outputs/logs and final PDF metadata after they are finalized. Inspect the final release CI run's logs/artifacts as well. After publication, confirm the actual branch/rules/security state, intended tag/commit and downloadable assets, including unauthenticated public access. Kaggle account verification, hosted execution and its public-resource checks are separate release-manager responsibilities.

Pattern scanning, code inspection and metadata extraction cannot prove the absence of every arbitrary credential format or restricted fact. The report states the exact inspected surfaces and does not convert an untested new file, pending upload or later CI run into a passed check.
