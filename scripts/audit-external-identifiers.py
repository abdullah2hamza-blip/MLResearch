"""Freeze metadata-only canonical identifiers for the retained Replogle pair.

This audit reads labels/annotations, never X, raw expression or scorer outcomes.
It does not silently merge aliases or change an already-frozen episode.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import h5py

from mlresearch.data import dataframe_index, read_column
from mlresearch.episodes import load_public_episode
from mlresearch.provenance import file_hash, read_json, utc_now, write_json


def missing(value: str) -> bool:
    return value.strip().lower() in ("", "nan", "none", "null")


def audit(
    path: Path, expected_sha: str, identities: tuple[str, ...], genes: tuple[str, ...]
) -> dict:
    checksum = file_hash(path)
    sidecar = read_json(Path(str(path) + ".provenance.json"))
    if checksum != expected_sha or sidecar["sha256"] != checksum:
        raise ValueError("Raw input differs from the verified frozen preparation")
    with h5py.File(path, "r") as handle:
        labels = read_column(handle["obs"], "perturbation").astype(str)
        canonical = read_column(handle["obs"], "gene_id").astype(str)
        guides = read_column(handle["obs"], "guide_id").astype(str)
        contexts = read_column(handle["obs"], "cell_line").astype(str)
        original_genes = dataframe_index(handle["var"]).astype(str)
        stable_genes = read_column(handle["var"], "ensembl_id").astype(str)
        symbol_genes = read_column(handle["var"], "gene_name").astype(str)
    target_ids: dict[str, set[str]] = defaultdict(set)
    target_guides: dict[str, set[str]] = defaultdict(set)
    guide_owners: dict[str, set[str]] = defaultdict(set)
    eligible = set(identities)
    for label, target, guide in zip(labels, canonical, guides, strict=True):
        if label in eligible:
            target_ids[label].add(target)
            target_guides[label].add(guide)
            if not missing(guide):
                guide_owners[guide].add(target)
    if set(target_ids) != eligible:
        raise ValueError("An episode target is absent from raw metadata")
    if any(len(values) != 1 or any(missing(v) for v in values) for values in target_ids.values()):
        raise ValueError("An eligible target has missing or ambiguous canonical IDs")
    mapping = {label: next(iter(values)) for label, values in sorted(target_ids.items())}
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("Multiple eligible labels share a canonical gene; split must be rebuilt")
    if any(len(owners) != 1 for owners in guide_owners.values()):
        raise ValueError("An eligible guide maps to multiple canonical targets")
    if len(set(original_genes)) != len(original_genes):
        raise ValueError("Original expression gene identifiers are duplicated")
    if any(missing(value) for value in stable_genes) or len(set(stable_genes)) != len(stable_genes):
        raise ValueError("Canonical expression gene IDs are missing or duplicated")
    gene_mapping = dict(zip(original_genes, stable_genes, strict=True))
    if any(gene not in gene_mapping for gene in genes):
        raise ValueError("An aligned expression gene is absent from the raw annotation")
    return {
        "raw_path": str(path),
        "raw_sha256": checksum,
        "raw_provenance_sha256": file_hash(Path(str(path) + ".provenance.json")),
        "original_target_column": "obs/perturbation",
        "canonical_target_column": "obs/gene_id",
        "original_expression_gene_axis": "var index",
        "canonical_expression_gene_column": "var/ensembl_id",
        "contexts": sorted(set(contexts)),
        "raw_cells": len(labels),
        "raw_expression_genes": len(original_genes),
        "symbols_disagreeing_with_var_gene_name": int(sum(original_genes != symbol_genes)),
        "eligible_target_to_canonical": mapping,
        "eligible_target_guides": {
            label: sorted(values) for label, values in sorted(target_guides.items())
        },
        "aligned_expression_gene_to_canonical": {gene: gene_mapping[gene] for gene in genes},
        "eligible_missing_guide_cells": sum(
            missing(guide) for label, guide in zip(labels, guides, strict=True) if label in eligible
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--k562", type=Path, default=Path("data/raw/ReplogleWeissman2022_K562_essential.h5ad")
    )
    parser.add_argument(
        "--rpe1", type=Path, default=Path("data/raw/ReplogleWeissman2022_rpe1.h5ad")
    )
    parser.add_argument("--forward", type=Path, default=Path("data/episodes/k562-to-rpe1-v1"))
    parser.add_argument("--reverse", type=Path, default=Path("data/episodes/rpe1-to-k562-v1"))
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Audit output exists")
    public = load_public_episode(args.forward)
    reverse = load_public_episode(args.reverse)
    forward_manifest = read_json(args.forward / "manifest.json")
    reverse_manifest = read_json(args.reverse / "manifest.json")
    if public.interventions != reverse.interventions or public.genes != reverse.genes:
        raise ValueError("The declared pair does not share its eligible identity/gene panel")
    k562_sha = forward_manifest["prepared_inputs"]["source"]["input_sha256"]
    rpe1_sha = forward_manifest["prepared_inputs"]["target"]["input_sha256"]
    if (
        reverse_manifest["prepared_inputs"]["source"]["input_sha256"] != rpe1_sha
        or reverse_manifest["prepared_inputs"]["target"]["input_sha256"] != k562_sha
    ):
        raise ValueError("The reverse direction uses different raw inputs")
    k562 = audit(args.k562, k562_sha, public.interventions, public.genes)
    rpe1 = audit(args.rpe1, rpe1_sha, public.interventions, public.genes)
    for field in ("eligible_target_to_canonical", "aligned_expression_gene_to_canonical"):
        if k562[field] != rpe1[field]:
            raise ValueError(f"Cross-file canonical identifier mismatch: {field}")
    queries, candidates = set(public.query_ids), set(public.candidate_ids)
    mapping = k562["eligible_target_to_canonical"]
    if {mapping[label] for label in queries} & {mapping[label] for label in candidates}:
        raise ValueError("Canonical gene identities cross the sealed split")
    result = {
        "state": "complete",
        "audited_at": utc_now(),
        "analysis_source_sha256": file_hash(Path(__file__)),
        "metadata_only": True,
        "recipient_expression_or_assessment_opened": False,
        "episode_manifest_sha256": {
            str(args.forward): file_hash(args.forward / "manifest.json"),
            str(args.reverse): file_hash(args.reverse / "manifest.json"),
        },
        "eligible_interventions": len(public.interventions),
        "aligned_expression_genes": len(public.genes),
        "same_queries_in_both_directions": public.query_ids == reverse.query_ids,
        "canonical_query_ids": sorted(mapping[label] for label in public.query_ids),
        "canonical_candidate_ids": sorted(mapping[label] for label in public.candidate_ids),
        "datasets": {"k562": k562, "rpe1": rpe1},
        "limitations": [
            "IDs are release-provided annotations; external annotation versions are unreconciled.",
            "This verifies the retained pair; it is not a universal gene-alias resolver.",
            "Missing IDs outside the eligible target set remain outside this frozen analysis.",
            "Guide combinations retain original strings; eligible guides follow their gene split.",
        ],
    }
    write_json(args.output, result)
    print(f"Verified {len(public.interventions)} canonical targets and {len(public.genes)} genes")


if __name__ == "__main__":
    main()
