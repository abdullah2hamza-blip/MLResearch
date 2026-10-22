"""Freeze metadata-defined gene splits and independent finite replay banks.

The episode directory contains public source summaries and a private row map.
Only the runner loads the row map. Policies receive PublicEpisode, never paths,
recipient outcomes, source cells, or a scorer. This is a cooperative API boundary.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from mlresearch.acquisition import CONTROL
from mlresearch.provenance import environment_record, file_hash, object_hash, read_json, write_json


@dataclass(frozen=True)
class EpisodeConfig:
    source_prepared: str
    target_prepared: str
    source_context: str
    target_context: str
    output_directory: str
    seed: int = 20261021
    query_fraction: float = 0.25
    min_source_cells: int = 32
    acquisition_cells: int = 64
    assessment_cells: int = 32
    acquisition_controls: int = 256
    assessment_controls: int = 256

    def __post_init__(self) -> None:
        if not 0 < self.query_fraction < 1:
            raise ValueError("query_fraction must lie between zero and one")
        for name in (
            "seed",
            "min_source_cells",
            "acquisition_cells",
            "assessment_cells",
            "acquisition_controls",
            "assessment_controls",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < (0 if name == "seed" else 2)
            ):
                raise ValueError(f"Invalid integer {name}")

    @classmethod
    def load(cls, path: Path) -> EpisodeConfig:
        try:
            return cls(**read_json(path))
        except TypeError as error:
            raise ValueError(f"Invalid episode configuration: {error}") from error


@dataclass(frozen=True)
class PublicEpisode:
    interventions: tuple[str, ...]
    query_ids: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    genes: tuple[str, ...]
    source_effects: np.ndarray
    source_per_cell_variance: np.ndarray
    source_effect_mean_variance: np.ndarray
    source_half_difference: np.ndarray

    def index(self, identity: str) -> int:
        return self.interventions.index(identity)


def load_prepared(
    path: Path, *, verify_values: bool = True
) -> tuple[dict[str, Any], np.ndarray, dict[str, Any]]:
    manifest = read_json(path / "manifest.json")
    if manifest.get("state") != "complete":
        raise ValueError("Prepared input is incomplete")
    if file_hash(path / "metadata.json") != manifest["metadata_sha256"]:
        raise ValueError("Prepared metadata checksum mismatch")
    if verify_values and file_hash(path / "values.npy") != manifest["values_sha256"]:
        raise ValueError("Prepared expression checksum mismatch")
    metadata = read_json(path / "metadata.json")
    matrix = np.load(path / "values.npy", mmap_mode="r", allow_pickle=False)
    if list(matrix.shape) != manifest["shape"] or len(metadata["cell_ids"]) != len(matrix):
        raise ValueError("Prepared axes disagree")
    if (
        len(set(metadata["cell_ids"])) != len(matrix)
        or len(set(metadata["genes"])) != matrix.shape[1]
    ):
        raise ValueError("Prepared identifiers must be unique")
    return metadata, matrix, manifest


def condition_rows(metadata: dict[str, Any], context: str) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = {}
    if context not in metadata["contexts"]:
        raise ValueError(f"Unknown context: {context}")
    for row, (label, cell_context) in enumerate(
        zip(metadata["interventions"], metadata["contexts"], strict=True)
    ):
        if cell_context == context:
            identity = CONTROL if label in metadata["control_labels"] else label
            if not identity or (identity == CONTROL and label not in metadata["control_labels"]):
                raise ValueError("Invalid or reserved intervention identity")
            groups.setdefault(identity, []).append(row)
    return groups


def _ordered_sample(rows: list[int], ids: list[str], seed: int, label: str) -> list[int]:
    # Independent streams prevent an added group from changing all later splits.
    entropy = int(object_hash([seed, label])[:16], 16)
    ordered = np.asarray(sorted(rows, key=lambda row: ids[row]), dtype=int)
    return np.random.default_rng(entropy).permutation(ordered).tolist()


def _summary(
    matrix: np.ndarray, rows: list[int], columns: list[int]
) -> tuple[np.ndarray, float, np.ndarray]:
    # One condition at a time, never all cells by all genes.
    block = np.asarray(matrix[np.ix_(rows, columns)], dtype=np.float64)
    if not np.all(np.isfinite(block)) or len(block) < 2:
        raise ValueError("Source summary requires at least two finite cells")
    mean = block.mean(axis=0)
    variance = float(np.var(block, axis=0, ddof=1).mean())
    halfway = len(block) // 2
    half_difference = block[:halfway].mean(axis=0) - block[halfway:].mean(axis=0)
    return mean, max(variance, 1e-8), half_difference


def build_episode(config: EpisodeConfig) -> dict[str, Any]:
    output = Path(config.output_directory)
    if output.exists():
        raise ValueError("Episode output exists; choose a new directory")
    start_environment = environment_record()
    source, source_values, source_manifest = load_prepared(Path(config.source_prepared))
    if Path(config.source_prepared).resolve() == Path(config.target_prepared).resolve():
        target, target_values, target_manifest = source, source_values, source_manifest
    else:
        target, target_values, target_manifest = load_prepared(Path(config.target_prepared))
    source_groups = condition_rows(source, config.source_context)
    target_groups = condition_rows(target, config.target_context)
    if len(source_groups.get(CONTROL, [])) < config.min_source_cells:
        raise ValueError("Insufficient independent source controls")
    if (
        len(target_groups.get(CONTROL, []))
        < config.acquisition_controls + config.assessment_controls
    ):
        raise ValueError("Insufficient recipient controls for disjoint banks")
    identities = sorted(
        identity
        for identity in source_groups.keys() & target_groups.keys()
        if identity != CONTROL
        and len(source_groups[identity]) >= config.min_source_cells
        and len(target_groups[identity]) >= config.acquisition_cells + config.assessment_cells
    )
    if len(identities) < 8:
        raise ValueError("At least eight overlapping eligible intervention identities are required")
    # Exact original intervention labels are gene-level identities. All guide IDs
    # attached to one label follow the same split; no guide is split into a query.
    guide_owners: dict[str, str] = {}
    for label, guide in zip(target["interventions"], target["guides"], strict=True):
        if label in identities and guide not in ("", "nan", "None"):
            owner = guide_owners.setdefault(guide, label)
            if owner != label:
                raise ValueError(
                    "A guide maps to multiple intervention labels; canonical mapping required"
                )
    genes = sorted(set(source["genes"]) & set(target["genes"]))
    if not genes:
        raise ValueError("Source and recipient have no exact matching gene identifiers")
    source_lookup = {gene: index for index, gene in enumerate(source["genes"])}
    target_lookup = {gene: index for index, gene in enumerate(target["genes"])}
    source_columns, target_columns = (
        [source_lookup[g] for g in genes],
        [target_lookup[g] for g in genes],
    )
    permutation = np.random.default_rng(config.seed).permutation(identities).tolist()
    queries = sorted(permutation[: max(1, int(len(identities) * config.query_fraction))])
    candidates = sorted(set(identities) - set(queries))
    acquisition: dict[str, list[int]] = {}
    assessment: dict[str, list[int]] = {}
    for identity in [CONTROL, *identities]:
        rows = _ordered_sample(target_groups[identity], target["cell_ids"], config.seed, identity)
        acquired = config.acquisition_controls if identity == CONTROL else config.acquisition_cells
        assessed = config.assessment_controls if identity == CONTROL else config.assessment_cells
        # Reserve the same assessment position even for sealed queries. No query
        # cell appears in the acquisition row map.
        assessment[identity] = rows[acquired : acquired + assessed]
        if identity not in queries:
            acquisition[identity] = rows[:acquired]
    source_rows = {
        identity: _ordered_sample(
            source_groups[identity], source["cell_ids"], config.seed, "source:" + identity
        )
        for identity in [CONTROL, *identities]
    }
    source_ids = {source["cell_ids"][row] for rows in source_rows.values() for row in rows}
    acquired_ids = {target["cell_ids"][row] for rows in acquisition.values() for row in rows}
    assessed_ids = {target["cell_ids"][row] for rows in assessment.values() for row in rows}
    if source_ids & (acquired_ids | assessed_ids) or acquired_ids & assessed_ids:
        raise ValueError("Source/acquisition/assessment cell banks overlap")
    control_mean, control_variance, control_half = _summary(
        source_values, source_rows[CONTROL], source_columns
    )
    effects, variances, mean_variances, half_differences = [], [], [], []
    for identity in identities:
        mean, variance, half_difference = _summary(
            source_values, source_rows[identity], source_columns
        )
        effects.append(mean - control_mean)
        variances.append(variance)
        mean_variances.append(
            variance / len(source_rows[identity]) + control_variance / len(source_rows[CONTROL])
        )
        half_differences.append(half_difference - control_half)
    output.mkdir(parents=True)
    np.savez(
        output / "source.npz",
        effects=np.asarray(effects, dtype=np.float32),
        per_cell_variance=variances,
        mean_variance=mean_variances,
        half_difference=np.asarray(half_differences, dtype=np.float32),
    )
    public = {
        "interventions": identities,
        "query_ids": queries,
        "candidate_ids": candidates,
        "genes": genes,
        "source_query_access": (
            "All retained source responses, including the recipient-query identities, are public."
        ),
        "gene_alignment": "Exact identifier intersection; no outcome-based gene selection.",
    }
    write_json(output / "public.json", public)
    try:
        target_location = os.path.relpath(Path(config.target_prepared).resolve(), output.resolve())
    except ValueError:  # Windows inputs on a different drive cannot have a relative path.
        target_location = str(Path(config.target_prepared).resolve())
    private = {
        "target_prepared": target_location,
        "target_path_rule": "Relative paths are resolved against the episode directory.",
        "target_columns": target_columns,
        "acquisition_rows": acquisition,
        "assessment_rows": assessment,
        "source_cell_ids": sorted(source_ids),
        "acquisition_cell_ids": {
            key: [target["cell_ids"][row] for row in rows] for key, rows in acquisition.items()
        },
        "assessment_cell_ids": {
            key: [target["cell_ids"][row] for row in rows] for key, rows in assessment.items()
        },
        "source_counts": {key: len(value) for key, value in source_rows.items()},
    }
    write_json(output / "private-banks.json", private)
    manifest = {
        "schema_version": 1,
        "state": "complete",
        "configuration": asdict(config),
        "environment": start_environment,
        "source_unchanged_during_build": start_environment["source_tree_sha256"]
        == environment_record()["source_tree_sha256"],
        "prepared_inputs": {"source": source_manifest, "target": target_manifest},
        "sha256": {
            name: file_hash(output / name)
            for name in ("source.npz", "public.json", "private-banks.json")
        },
        "inventory": {
            "genes": len(genes),
            "interventions": len(identities),
            "candidates": len(candidates),
            "queries": len(queries),
            "acquisition_cells": len(acquired_ids),
            "assessment_cells": len(assessed_ids),
        },
        "limitations": [
            "Exact gene labels do not resolve aliases or annotation versions.",
            "Cell resampling is not independent biological replication.",
            "Input preparation provenance must be assessed separately.",
        ],
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def load_public_episode(path: Path) -> PublicEpisode:
    manifest = read_json(path / "manifest.json")
    if manifest.get("state") != "complete":
        raise ValueError("Episode is incomplete")
    for name, expected in manifest["sha256"].items():
        if file_hash(path / name) != expected:
            raise ValueError(f"Episode checksum mismatch: {name}")
    public = read_json(path / "public.json")
    with np.load(path / "source.npz", allow_pickle=False) as arrays:
        effects = arrays["effects"].astype(np.float64)
        variance, mean_variance = arrays["per_cell_variance"], arrays["mean_variance"]
        difference = arrays["half_difference"].astype(np.float64)
    if effects.shape != (len(public["interventions"]), len(public["genes"])):
        raise ValueError("Public source axes disagree")
    if set(public["query_ids"]) & set(public["candidate_ids"]):
        raise ValueError("Recipient query and calibration identities overlap")
    for array in (effects, variance, mean_variance, difference):
        if not np.all(np.isfinite(array)):
            raise ValueError("Public source data must be finite")
        array.setflags(write=False)
    return PublicEpisode(
        tuple(public["interventions"]),
        tuple(public["query_ids"]),
        tuple(public["candidate_ids"]),
        tuple(public["genes"]),
        effects,
        variance,
        mean_variance,
        difference,
    )
