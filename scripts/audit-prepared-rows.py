"""Post-freeze raw/prepared consistency audit; no model fitting or outcome selection."""

from __future__ import annotations

import argparse
from pathlib import Path

import h5py
import numpy as np
from scipy import sparse

from mlresearch.data import read_columns, read_rows
from mlresearch.episodes import load_prepared
from mlresearch.external import validate_joint_freeze
from mlresearch.prepare import PrepareConfig, select_metadata
from mlresearch.provenance import file_hash, read_json, utc_now, write_json


def audit(path: Path, samples: int, seed: int) -> dict:
    declared = PrepareConfig.load(path)
    prepared = Path(declared.output_directory)
    metadata, values, manifest = load_prepared(prepared)
    config = PrepareConfig(**manifest["configuration"])
    raw = Path(config.input_path)
    if file_hash(raw) != manifest["input_sha256"]:
        raise ValueError("Pinned raw input changed")
    with h5py.File(raw, "r") as handle:
        rebuilt, source_rows = select_metadata(handle, config)
        fields = (
            "original_cell_ids",
            "genes",
            "contexts",
            "interventions",
            "guides",
            "batches",
            "control_labels",
            "condition_inventory",
        )
        for name in fields:
            if rebuilt[name] != metadata[name]:
                raise ValueError("Prepared metadata differs: " + name)
        expected_ids = [
            manifest["input_sha256"][:16] + ":" + key for key in metadata["original_cell_ids"]
        ]
        if expected_ids != metadata["cell_ids"]:
            raise ValueError("Cell namespace differs")
        chosen = {0, len(values) - 1}
        for context in sorted(set(metadata["contexts"])):
            chosen.add(metadata["contexts"].index(context))
        for label in metadata["control_labels"]:
            chosen.add(metadata["interventions"].index(label))
        rng = np.random.default_rng(seed)
        for row in rng.permutation(len(values)):
            if len(chosen) >= min(samples, len(values)):
                break
            chosen.add(int(row))
        selected = sorted(chosen)
        raw_rows = source_rows[selected]
        matrix = handle["X"]
        encoding = matrix.attrs.get("encoding-type", "")
        encoding = encoding.decode() if isinstance(encoding, bytes) else str(encoding)
        if isinstance(matrix, h5py.Group) and encoding == "csc_matrix":
            counts = np.empty((len(selected), values.shape[1]))
            for start in range(0, values.shape[1], 16):
                block = read_columns(matrix, start, min(start + 16, values.shape[1]))[raw_rows, :]
                counts[:, start : start + block.shape[1]] = (
                    block.toarray() if sparse.issparse(block) else block
                )
        else:
            rows = []
            for row in raw_rows:
                block = read_rows(matrix, int(row), int(row) + 1)
                rows.append(block.toarray()[0] if sparse.issparse(block) else block[0])
            counts = np.asarray(rows, dtype=float)
    if counts.shape != (len(selected), values.shape[1]) or not np.isfinite(counts).all():
        raise ValueError("Raw sample axes or values invalid")
    if config.input_scale == "counts":
        if np.any(counts < 0) or np.any(np.abs(counts - np.round(counts)) > 1e-6):
            raise ValueError("Sample violates declared count input")
        totals = counts.sum(axis=1)
        if np.any(totals <= 0):
            raise ValueError("Nonpositive full-panel library total")
        # Independent direct formula; include every raw input gene in the denominator.
        expected = np.log1p(counts * config.target_library_size / totals[:, None]).astype(
            np.float32
        )
    else:
        expected = counts.astype(np.float32)
    actual = np.asarray(values[selected], dtype=np.float32)
    np.testing.assert_allclose(actual, expected, rtol=2e-7, atol=2e-7)
    return {
        "configuration": str(path),
        "raw_sha256": manifest["input_sha256"],
        "prepared_manifest_sha256": file_hash(prepared / "manifest.json"),
        "prepared_values_sha256": manifest["values_sha256"],
        "all_retained_metadata_rows_verified": len(values),
        "full_input_genes": values.shape[1],
        "sampled_rows": len(selected),
        "sampled_cell_ids": [metadata["cell_ids"][i] for i in selected],
        "max_absolute_float32_discrepancy": float(np.max(np.abs(actual - expected))),
        "unequal_float32_entries": int(np.count_nonzero(actual != expected)),
        "stored_io": {
            name: getattr(config, name) for name in ("row_block_size", "column_block_size")
        },
        "reproduction_io": {
            name: getattr(declared, name) for name in ("row_block_size", "column_block_size")
        },
        "prepare_module_matches_recorded_environment": manifest["environment"]["source_hashes"].get(
            "prepare.py"
        )
        == file_hash(Path("src/mlresearch/prepare.py")),
        "qualification": (
            "Full metadata/selection reproducibility and sampled full-gene expression rows; "
            "not a second computation of every matrix entry."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261022)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Audit output exists")
    if not 8 <= args.samples <= 64 or args.seed < 0:
        raise ValueError("Invalid bounded sample settings")
    manifest = read_json(args.suite / "manifest.json")
    if manifest["state"] != "complete":
        raise ValueError("Complete the frozen suite before raw-row auditing")
    validate_joint_freeze(args.suite / "joint-prediction-freeze.json")
    results = [
        audit(Path(name), args.samples, args.seed)
        for name in (
            "configs/prepare-frangieh.json",
            "configs/prepare-k562.json",
            "configs/prepare-rpe1.json",
        )
    ]
    write_json(
        args.output,
        {
            "state": "passed",
            "audited_at": utc_now(),
            "analysis_source_sha256": file_hash(Path(__file__)),
            "suite_manifest_sha256": file_hash(args.suite / "manifest.json"),
            "samples": args.samples,
            "seed": args.seed,
            "datasets": results,
            "raw_expression_retained": False,
            "information_scope": (
                "Scorer suite already complete; this audit neither refits models "
                "nor changes acquisitions or settings."
            ),
        },
    )
    print(
        "Verified full metadata and sampled full-gene transformations for", len(results), "datasets"
    )


if __name__ == "__main__":
    main()
