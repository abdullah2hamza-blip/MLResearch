"""Stage small, authenticated saved results for the public reanalysis notebook."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

INPUTS = {
    "primary_curves": (
        "docs/results/external-evaluation-v1/supplement/curves-and-specificity.csv",
        "results/primary-curves.csv",
    ),
    "paired_query_areas": (
        "docs/results/publication-robustness-v1/analysis/paired-query-areas.csv",
        "results/paired-query-areas.csv",
    ),
    "paired_area_comparisons": (
        "docs/results/publication-robustness-v1/analysis/paired-area-comparisons.csv",
        "results/paired-area-comparisons.csv",
    ),
}

AI_DISCLOSURE = (
    "Artificial intelligence (AI) tools were used for manuscript editing and code preparation. "
    "OpenAI Codex (OpenAI) assisted with research planning, literature review and experimental "
    "design, code preparation, statistical analysis and interpretation, figure and table "
    "preparation, manuscript drafting and revision, internal review, and release preparation. "
    "These AI-assisted reviews were internal quality checks, not independent human peer review. "
    "The human author retains responsibility for the final work."
)


def stage_inputs(root: Path, destination: Path, commit: str, tag: str) -> Path:
    """Copy exact first-party outputs; preserve the established mixed terms."""
    root, destination = root.resolve(), destination.resolve()
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None or not tag.strip():
        raise ValueError("Supply the actual 40-character release commit and nonempty release tag")
    if destination.exists():
        raise ValueError("Preserve existing staged inputs; choose a new destination")
    destination.mkdir(parents=True)
    files = {}
    for key, (source_name, name) in INPUTS.items():
        payload = (root / source_name).read_bytes()
        path = destination / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(payload)
        files[key] = {
            "path": name,
            "source_path": source_name,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "terms": (
                "Unmodified retained analysis output; existing project/upstream terms preserved."
            ),
        }
    licenses = destination / "licenses"
    licenses.mkdir()
    (licenses / "SOFTWARE-LICENSE.txt").write_bytes((root / "LICENSE").read_bytes())
    (licenses / "MANUSCRIPT-LICENSE.txt").write_bytes((root / "paper/LICENSE").read_bytes())
    scope = (
        "Mixed-artifact container; no blanket relicensing.\n"
        "Original software and supporting repository documentation: MIT; "
        "see SOFTWARE-LICENSE.txt.\n"
        "Manuscript text and original manuscript figures/tables: CC BY 4.0; "
        "see MANUSCRIPT-LICENSE.txt.\n"
        "The CSV files are exact retained first-party analysis outputs. Their established project\n"
        "and upstream terms are preserved. No new blanket data license is granted.\n"
        "The original scPerturb release is Zenodo record 13350497, version 1.4, CC BY 4.0.\n"
        "No raw expression, restricted data, model weights, credentials or private correspondence\n"
        "are included. Preserve attribution and obtain raw data from the pinned upstream.\n"
        "Use Kaggle Dataset license Other (specified in description), with this scope visible.\n"
    )
    (licenses / "SCOPE.txt").write_text(scope, encoding="utf-8")
    card = (
        "# MLResearch saved-result reanalysis inputs\n\n"
        "This compact artifact contains unmodified retained analysis summaries for Abdullah "
        "Hamza's technical report, Evaluating fixed-kernel joint acquisition for cross-context "
        "perturbation prediction. Hosting is not peer review or journal acceptance.\n\n"
        "The notebook recomputes two original primary budget-normalized error areas and all "
        "32 post-primary robustness contrasts. This is re-analysis of saved outputs, not a "
        "repeat of raw-data acquisition, preprocessing, fitting or experimental scoring.\n\n"
        "Upstream: scPerturb Zenodo record 13350497, version 1.4; original experimental and "
        "resource attribution is in the manuscript. No raw expression is redistributed.\n\n"
        "Files: results/primary-curves.csv (original policy/backbone curves); "
        "results/paired-query-areas.csv (131 paired queries per robustness contrast); "
        "results/paired-area-comparisons.csv (all 32 retained summaries and conditional ranges). "
        "The manifest binds exact bytes, source paths and the release commit/tag.\n\n"
        "Negative paired differences favor the extension. Primary seeds vary acquisition "
        "order/ties, not biological replicates. New splits/directions reuse cells and queries. "
        "Conditional query ranges are not biological confidence intervals. Prices are abstract. "
        "No biological transportability or prospective laboratory savings are established.\n\n"
        "Licensing: Other (specified here), with per-file scope in licenses/SCOPE.txt. Original "
        "software is MIT; manuscript text/figures/tables are CC BY 4.0; retained outputs and "
        "third-party material keep existing terms. This is not a new blanket data license.\n\n"
        "Project: https://github.com/abdullah2hamza-blip/MLResearch . Cite the manuscript and "
        "release version using CITATION.cff; no DOI is invented.\n\n"
        "AI assistance: " + AI_DISCLOSURE + "\n"
    )
    (destination / "DATASET-CARD.md").write_text(card, encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "title": "MLResearch saved-result reanalysis inputs",
        "release": {"commit": commit, "tag": tag},
        "notebook_source_sha256": hashlib.sha256(
            (root / "notebooks/joint-acquisition-reanalysis.ipynb").read_bytes()
        ).hexdigest(),
        "repository_url": "https://github.com/abdullah2hamza-blip/MLResearch",
        "publication_status": "Technical report / public research release; not peer reviewed",
        "upstream_data": {
            "record": "https://zenodo.org/records/13350497",
            "version": "1.4",
            "raw_data_redistributed": False,
        },
        "scientific_versions": {
            "primary": "Frozen v0.1.0 snapshots retained with original runs",
            "robustness": "v0.2.0 numerical source tree",
            "robustness_source_tree_sha256": (
                "1a3392680a7abfd4fdd7a5b2fc808e595bfc5e2628271f207c0e5cb789f569a3"
            ),
        },
        "files": files,
        "licenses": {
            "container": "Other; per-file scope, no blanket new license",
            "scope": "licenses/SCOPE.txt",
            "software": "licenses/SOFTWARE-LICENSE.txt",
            "manuscript": "licenses/MANUSCRIPT-LICENSE.txt",
        },
        "verification_scope": (
            "The notebook re-analyzes saved summary outputs; it does not repeat full-data "
            "acquisition, preprocessing, fitting or experimental scoring."
        ),
    }
    path = destination / "mlresearch-results-manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--release-commit", required=True)
    parser.add_argument("--release-tag", required=True)
    args = parser.parse_args()
    path = stage_inputs(args.root, args.destination, args.release_commit, args.release_tag)
    print(f"Staged three authenticated saved-result tables at {path.parent}")


if __name__ == "__main__":
    main()
