"""Prepare capped, deterministic cell pools by streaming dense/CSR/CSC H5AD data.

Selection uses identifiers and declared metadata filters, never effect sizes.
The output retains the complete original gene axis and original guide labels.
"""

from __future__ import annotations

import logging
import shutil
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from scipy import sparse

from mlresearch.data import (
    _text,
    dataframe_index,
    matrix_shape,
    read_column,
    read_columns,
    read_rows,
)
from mlresearch.provenance import environment_record, file_hash, object_hash, read_json, write_json


@dataclass(frozen=True)
class PrepareConfig:
    input_path: str
    output_directory: str
    perturbation_column: str
    control_labels: list[str]
    input_scale: str
    context_column: str | None = None
    context_value: str | None = None
    guide_column: str | None = None
    batch_column: str | None = None
    filters: dict[str, list[Any]] = field(default_factory=dict)
    max_cells_per_condition: int = 96
    max_control_cells_per_context: int = 512
    seed: int = 20261021
    column_block_size: int = 16
    row_block_size: int = 128
    target_library_size: float = 10_000.0

    def __post_init__(self) -> None:
        if (self.context_column is None) == (self.context_value is None):
            raise ValueError("Specify exactly one context_column or context_value")
        if self.input_scale not in ("counts", "as_provided"):
            raise ValueError("input_scale must explicitly be counts or as_provided")
        if (
            not isinstance(self.control_labels, list)
            or not self.control_labels
            or any(not isinstance(label, str) or not label for label in self.control_labels)
            or len(set(self.control_labels)) != len(self.control_labels)
        ):
            raise ValueError("Declare distinct nonempty control labels")
        for name in (
            "max_cells_per_condition",
            "max_control_cells_per_context",
            "column_block_size",
            "row_block_size",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if not np.isfinite(self.target_library_size) or self.target_library_size <= 0:
            raise ValueError("target_library_size must be finite and positive")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if any(not isinstance(allowed, list) or not allowed for allowed in self.filters.values()):
            raise ValueError("Metadata filters must have explicit nonempty allowed-value lists")

    @classmethod
    def load(cls, path: Path) -> PrepareConfig:
        try:
            return cls(**read_json(path))
        except TypeError as error:
            raise ValueError(f"Invalid preparation configuration: {error}") from error


def select_metadata(handle: h5py.File, config: PrepareConfig) -> tuple[dict[str, Any], np.ndarray]:
    obs, var = handle["obs"], handle["var"]
    identifiers, genes = dataframe_index(obs), dataframe_index(var)
    if matrix_shape(handle["X"]) != (len(identifiers), len(genes)):
        raise ValueError("Expression and metadata axes do not agree")
    if len(set(identifiers)) != len(identifiers) or len(set(genes)) != len(genes):
        raise ValueError("Unique cell/gene identifiers are required; resolve duplicates explicitly")
    perturbations = read_column(obs, config.perturbation_column).astype(str)
    contexts = (
        read_column(obs, config.context_column).astype(str)
        if config.context_column is not None
        else np.full(len(identifiers), config.context_value, dtype=object)
    )
    mask = np.ones(len(identifiers), dtype=bool)
    for column, allowed in config.filters.items():
        values = np.asarray([_text(value) for value in read_column(obs, column)], dtype=object)
        mask &= np.isin(values, [_text(value) for value in allowed])
    mask &= ~np.isin(perturbations, ["", "nan", "None"])
    mask &= ~np.isin(contexts, ["", "nan", "None"])
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index in np.flatnonzero(mask):
        groups[(str(contexts[index]), str(perturbations[index]))].append(int(index))
    rng = np.random.default_rng(config.seed)
    selected: list[int] = []
    inventory: list[dict[str, Any]] = []
    sampling_groups: dict[tuple[str, bool, str], list[int]] = defaultdict(list)
    for (context, perturbation), indices in groups.items():
        is_control = perturbation in config.control_labels
        sampling_groups[(context, is_control, "" if is_control else perturbation)].extend(indices)
    for (_context, is_control, _perturbation), indices in sorted(sampling_groups.items()):
        # Sorting IDs before sampling makes the selected identity set row-order invariant.
        ordered = np.asarray(sorted(indices, key=lambda index: identifiers[index]), dtype=int)
        cap = config.max_control_cells_per_context if is_control else config.max_cells_per_condition
        chosen = rng.choice(ordered, size=min(cap, len(ordered)), replace=False)
        selected.extend(chosen.tolist())
    chosen_set = set(selected)
    for (context, perturbation), indices in sorted(groups.items()):
        inventory.append(
            {
                "context": context,
                "intervention": perturbation,
                "eligible_cells": len(indices),
                "retained_cells": sum(index in chosen_set for index in indices),
                "is_control": perturbation in config.control_labels,
            }
        )
    if not selected:
        raise ValueError("The declared metadata filters retain no cells")
    selected_rows = np.asarray(sorted(selected), dtype=int)
    metadata: dict[str, Any] = {
        "original_cell_ids": identifiers[selected_rows].tolist(),
        "contexts": contexts[selected_rows].tolist(),
        "interventions": perturbations[selected_rows].tolist(),
        "genes": genes.tolist(),
        "control_labels": config.control_labels,
        "input_cells": len(identifiers),
        "metadata_eligible_cells": int(np.sum(mask)),
        "retained_cells": len(selected_rows),
        "condition_inventory": inventory,
        "original_column_mapping": {
            "intervention": config.perturbation_column,
            "context": config.context_column,
            "guide": config.guide_column,
            "batch": config.batch_column,
        },
    }
    for label, metadata_column in (
        ("guides", config.guide_column),
        ("batches", config.batch_column),
    ):
        metadata[label] = (
            [_text(value) for value in read_column(obs, metadata_column)[selected_rows]]
            if metadata_column is not None
            else [""] * len(selected_rows)
        )
    return metadata, selected_rows


def count_metadata(config: PrepareConfig) -> dict[str, Any]:
    with h5py.File(config.input_path, "r") as handle:
        metadata, _ = select_metadata(handle, config)
    return {
        key: value
        for key, value in metadata.items()
        if key
        not in ("original_cell_ids", "contexts", "interventions", "genes", "guides", "batches")
    }


def _validate_counts(values: Any) -> None:
    entries = values.data if sparse.issparse(values) else values.ravel()
    if (
        not np.all(np.isfinite(entries))
        or np.any(entries < 0)
        or not np.allclose(entries, np.round(entries), atol=1e-5, rtol=0)
    ):
        raise ValueError(
            "Declared count matrix contains nonfinite, negative, or fractional entries"
        )


def _transform(values: np.ndarray, totals: np.ndarray, config: PrepareConfig) -> np.ndarray:
    if not np.all(np.isfinite(values)):
        raise ValueError("Expression contains nonfinite values")
    if config.input_scale == "counts":
        if np.any(totals <= 0):
            raise ValueError("A retained cell has zero total counts; revise QC explicitly")
        return np.log1p(values * (config.target_library_size / totals[:, None]))
    return values


def prepare_h5ad(config: PrepareConfig) -> dict[str, Any]:
    start_environment = environment_record()
    output = Path(config.output_directory)
    if output.exists():
        raise ValueError("Preparation output already exists; choose a new output directory")
    with h5py.File(config.input_path, "r") as handle:
        metadata, selected = select_metadata(handle, config)
        matrix = handle["X"]
        rows, columns = matrix_shape(matrix)
        encoding = _text(matrix.attrs.get("encoding-type", "dense"))
        if encoding not in ("dense", "array", "csr_matrix", "csc_matrix"):
            raise ValueError(f"Unsupported matrix encoding: {encoding}")
        output.mkdir(parents=True)
        if shutil.disk_usage(output).free < len(selected) * columns * 4 + 64 * 1024**2:
            raise ValueError("Insufficient free disk for the declared prepared matrix")
        configuration = asdict(config)
        write_json(output / "manifest.json", {"state": "preparing", "configuration": configuration})
        values_path = output / "values.npy"
        values = np.lib.format.open_memmap(
            values_path, mode="w+", dtype=np.float32, shape=(len(selected), columns)
        )
        totals = np.zeros(rows, dtype=np.float64)
        if encoding == "csc_matrix":
            if config.input_scale == "counts":
                for left in range(0, columns, config.column_block_size):
                    block = read_columns(
                        matrix, left, min(left + config.column_block_size, columns)
                    )
                    _validate_counts(block)
                    totals += np.asarray(block.sum(axis=1)).ravel()
                logging.info("Validated count matrix and computed full-gene library totals")
            for left in range(0, columns, config.column_block_size):
                right = min(left + config.column_block_size, columns)
                block = read_columns(matrix, left, right)[selected, :].toarray()
                values[:, left:right] = _transform(block, totals[selected], config)
        else:
            for start in range(0, rows, config.row_block_size):
                stop = min(start + config.row_block_size, rows)
                positions = np.flatnonzero((selected >= start) & (selected < stop))
                if len(positions) == 0:
                    continue
                block = read_rows(matrix, start, stop)
                if config.input_scale == "counts":
                    _validate_counts(block)
                row_totals = np.asarray(block.sum(axis=1)).ravel()
                block = block[selected[positions] - start, :]
                dense = block.toarray() if sparse.issparse(block) else block
                values[positions, :] = _transform(
                    dense, row_totals[selected[positions] - start], config
                )
        values.flush()
        del values  # Close mapping before hashing / later Windows readers.
    namespace = file_hash(Path(config.input_path))
    metadata["cell_ids"] = [f"{namespace[:16]}:{value}" for value in metadata["original_cell_ids"]]
    write_json(output / "metadata.json", metadata)
    manifest = {
        "schema_version": 1,
        "state": "complete",
        "configuration": configuration,
        "configuration_sha256": object_hash(configuration),
        "input_sha256": namespace,
        "metadata_sha256": file_hash(output / "metadata.json"),
        "values_sha256": file_hash(values_path),
        "shape": [len(selected), columns],
        "dtype": "float32",
        "transformation": (
            f"log1p({config.target_library_size} * counts / full_gene_library_total)"
            if config.input_scale == "counts"
            else "as_provided"
        ),
        "selection": (
            "Declared metadata filters and seeded identity sampling; no effect-size filter."
        ),
        "environment": start_environment,
        "source_unchanged_during_preparation": (
            start_environment["source_tree_sha256"] == environment_record()["source_tree_sha256"]
        ),
        "limitations": [
            "Capped cell pools represent retrospective replay, not new experiments.",
            "Guide/batch labels are preserved; biological independence is not assumed.",
        ],
    }
    write_json(output / "manifest.json", manifest)
    return manifest
