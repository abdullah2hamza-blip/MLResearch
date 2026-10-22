"""Verify an explicit release-specific canonical annotation freeze before acquisition."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mlresearch.episodes import PublicEpisode
from mlresearch.provenance import file_hash, read_json


def verify_identifier_record(
    public: PublicEpisode, episode: dict[str, Any], path: Path, *, episode_sha256: str
) -> dict[str, Any]:
    record = read_json(path)
    if record["state"] != "complete" or not record["metadata_only"]:
        raise ValueError("Canonical identifier audit is incomplete")
    if episode_sha256 not in record["episode_manifest_sha256"].values():
        raise ValueError("Canonical audit does not bind the frozen episode")
    by_raw = {dataset["raw_sha256"]: dataset for dataset in record["datasets"].values()}
    mappings = []
    for arm in ("source", "target"):
        raw = episode["prepared_inputs"][arm]["input_sha256"]
        if raw not in by_raw:
            raise ValueError("Canonical audit uses different raw inputs")
        dataset = by_raw[raw]
        targets = dataset["eligible_target_to_canonical"]
        genes = dataset["aligned_expression_gene_to_canonical"]
        if set(targets) != set(public.interventions) or set(genes) != set(public.genes):
            raise ValueError("Canonical audit and public identity/gene axes differ")
        for mapping in (targets, genes):
            if any(
                not isinstance(v, str) or v.strip().lower() in ("", "nan", "none", "null")
                for v in mapping.values()
            ) or len(set(mapping.values())) != len(mapping):
                raise ValueError("Canonical IDs are missing, ambiguous or alias multiple labels")
        mappings.append((targets, genes))
    if mappings[0] != mappings[1]:
        raise ValueError("Canonical annotations disagree across source and recipient")
    target_map = mappings[0][0]
    if {target_map[key] for key in public.query_ids} & {
        target_map[key] for key in public.candidate_ids
    }:
        raise ValueError("Canonical identities cross the sealed query split")
    return {
        "record": str(path),
        "sha256": file_hash(path),
        "canonical_targets": len(target_map),
        "canonical_expression_genes": len(mappings[0][1]),
        "query_canonical_ids": [target_map[key] for key in public.query_ids],
        "qualification": "Release-specific ID verification; no universal alias resolution.",
    }
