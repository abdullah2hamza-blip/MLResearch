# Internal software and release review

October 28, 2026. This review inspected the current implementation and release
tools against the manuscript rather than accepting previous passing audits as
proof. It is internal quality assurance, not external peer review or acceptance.

## Coverage and findings

The inspected scientific implementation includes `src/mlresearch/linear.py`,
`design.py`, `policies.py`, `models.py`, `acquisition.py`, `episodes.py`,
`experiment.py`, `external.py`, `controls.py`, `transfer.py`, `uncertainty.py`,
the metadata-selection portion of `prepare.py`, and relevant validation,
covariance, acquisition, transfer, source-control and joint-freeze tests.
The release inspection covers `scripts/build-paper.py`,
`scripts/package-publication.py`, `scripts/verify-publication-package.py`,
`.github/workflows/checks.yml`, the project metadata, licenses, citation record,
dataset registry and reproduction/publication instructions.

Within that scope, the implementation agrees with the manuscript on the
shared-control covariance, nuisance-baseline elimination, ridge penalty,
unregularized support check, paid-only covariance-corrected validation,
fixed-amplitude kernel variance, finite-pool prices and query-label boundary.
The acquisition service refuses query purchases and repeated cells. The runner
authenticates checkpoint artifacts and ledger prefixes, and a joint suite closes
every run before opening its first scorer. This is a cooperative workflow boundary,
as the manuscript states, rather than an operating-system security boundary.
Transfer reconstruction excludes validation/query tokens from the fitted response
basis and labels its reused validation gain as an in-sample quantity. Conditional
resampling retains the common control draw. No additional core scientific code
defect was identified in these inspected paths.

One confirmed release defect required repair: the previous packager checked
generated assets but accepted any existing PDF and compiled bibliography. A later
edit to a handwritten section could therefore produce an archive whose editable
source and PDF disagreed, while the package still passed its own checks.

The repaired build helper records a portable inventory and SHA-256 hashes for the
saved manuscript payloads, excluding known build products. It compares the
inventory before and after compilation and records the generated-asset manifest,
PDF and compiled-bibliography hashes. The packager now requires that build receipt,
rejects missing or legacy receipts, refuses changed, added or deleted inputs or
altered compiled outputs, and rejects recorded unresolved references or overfull
boxes. The release manifest binds the receipt's hash. A source-only manuscript
can still rebuild in its own directory or after relocation. These changes affect
release tools; numerical package sources, configurations and historical scientific
evidence were not modified by this repair.

## Fresh checks

Twelve focused tests in `tests/test_publication_build.py` passed in 1.90 seconds.
They exercise a valid relocated binding, edited/deleted/added manuscript inputs,
changed bibliography source and figure inventory, altered PDF or compiled
bibliography, absent/legacy receipts, source changes during compilation, and
repeated source-only builds with outputs beside the sources. Compiler execution
is stubbed in these unit tests; an actual final TeX build and visual inspection
remain part of the integrated release check. Ruff formatting and lint checks
passed for both changed scripts and the new test file.

A separate fresh algebra check used 200 random cases with seed 20261028, varying
the treatment, feature and response dimensions, positive variances and ridge
penalties. GLS fits were compared with an independently assembled augmented
raw-mean weighted least-squares problem that explicitly includes the control
baseline. The maximum absolute coefficient discrepancy was
`1.4210854715202004e-14`. The centered information matrix was compared with a dense
`X.T @ solve(diag(d) + c * ones, X)` calculation; its maximum absolute discrepancy
was `1.0089706847793423e-12`. These checks support the inspected algebra, not every
possible numerical regime or a biological model.

A pattern scan of the 983 tracked files in the inspected snapshot and their nested
ZIP/gzip contents examined 9,458 payloads, including 8,448 nested archive members.
It found no matching GitHub/OpenAI/AWS credential prefixes, private-key headers,
or archived credential/environment directories. It did not print candidate secret
values. The largest tracked file was approximately 27.8 MB. Public study cell
identifiers and the supplied author correspondence are intentional materials.
Pattern matching cannot certify the absence of arbitrary credentials; the scan
does not cover every historical Git blob or files added after that snapshot.

## Release scope and limits

GitHub is the supported release path. The repository supplies a locked Python 3.12
environment, CPU-only offline example, tests, a Windows/Ubuntu workflow, separate
software/manuscript licenses, citation metadata, pinned public data and compact
retained evidence. Final readiness still depends on the integrated current-tree
tests, actual PDF rebuild and rendering, archive checks, and clean unpack/rebuild
checks performed after the manuscript and release edits finish. Earlier CI
receipts describe their recorded revisions and must not be presented as checks
of a later working tree.

No Kaggle runtime, notebook or deployment was validated in this review. A Kaggle
release would require a separately tested notebook or script entry point and
platform metadata, suitable input/data packaging and license attribution, and
resource validation inside that runtime. GitHub readiness must not be described
as a tested Kaggle publication.

This review does not repeat the full raw-data acquisition study, independently
validate all biological assumptions, establish calibrated adaptive inference,
or confer acceptance by a venue. It preserves the manuscript's stated limits
on selected cohorts, shared observations, estimated source features, hypothetical
costs and conditional uncertainty.
