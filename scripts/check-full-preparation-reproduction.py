"""Reprepare every retained value from pinned raw inputs; preserve original artifacts."""

from __future__ import annotations

import argparse
import time
import zipfile
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

from mlresearch.prepare import PrepareConfig, prepare_h5ad
from mlresearch.provenance import (
    environment_record,
    file_hash,
    read_json,
    resource_record,
    snapshot_sources,
    utc_now,
    write_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    root = args.directory.resolve()
    if not root.is_relative_to(Path.cwd().resolve()):
        raise ValueError("Use a fresh reproduction directory inside this workspace")
    if args.evidence.exists():
        raise ValueError("Preparation comparison evidence exists")
    started, cpu_started = time.perf_counter(), time.process_time()
    environment = environment_record()
    sources = {name: Path(f"configs/prepare-{name}.json") for name in ("frangieh", "k562", "rpe1")}
    identity = {
        "analysis_source_sha256": file_hash(Path(__file__)),
        "package_source_sha256": environment["source_tree_sha256"],
        "configuration_sha256": {name: file_hash(path) for name, path in sources.items()},
    }
    if root.exists():
        if not args.resume or read_json(root / "identity.json") != identity:
            raise ValueError(
                "Preparation reproduction exists or resume source/configuration differs"
            )
    else:
        root.mkdir(parents=True)
        write_json(root / "identity.json", identity)
        (root / "analysis-source.py").write_bytes(Path(__file__).read_bytes())
        snapshot_sources(root / "code.zip", environment["source_hashes"])
    records = []
    for name, path in sources.items():
        config = PrepareConfig.load(path)
        original = Path(config.output_directory)
        old = read_json(original / "manifest.json")
        receipt = root / f"{name}-comparison.json"
        if receipt.exists():
            record = read_json(receipt)
            fresh = Path(record["rebuilt_directory"])
            if file_hash(original / "manifest.json") != record["original_manifest_sha256"]:
                raise ValueError("Original preparation provenance changed during resume")
            if file_hash(fresh / "manifest.json") != record["rebuilt_manifest_sha256"]:
                raise ValueError("Rebuilt preparation provenance changed during resume")
            if file_hash(fresh / "values.npy") != record["rebuilt_values_sha256"]:
                raise ValueError("Completed reproduced matrix changed")
            if file_hash(original / "values.npy") != old["values_sha256"]:
                raise ValueError("Original matrix changed during resume")
            records.append(record)
            print("Reusing complete preparation comparison", name, flush=True)
            continue
        attempt = 0
        fresh = root / f"{name}-attempt-{attempt}"
        while fresh.exists():
            attempt += 1
            fresh = root / f"{name}-attempt-{attempt}"
        rebuilt_config = replace(config, output_directory=str(fresh))
        write_json(root / f"{name}-configuration.json", asdict(rebuilt_config))
        before = time.perf_counter(), time.process_time()
        resources_start = resource_record(root)
        if file_hash(Path(config.input_path)) != old["input_sha256"]:
            raise ValueError("Pinned raw input changed")
        print("Full raw preparation reproduction", name, flush=True)
        rebuilt = prepare_h5ad(rebuilt_config)
        if (
            rebuilt["input_sha256"] != old["input_sha256"]
            or not rebuilt["source_unchanged_during_preparation"]
            or rebuilt["environment"]["source_tree_sha256"] != identity["package_source_sha256"]
        ):
            raise ValueError("Raw input or preparation source changed")
        if read_json(original / "metadata.json") != read_json(fresh / "metadata.json"):
            raise ValueError("Complete retained metadata differs on reconstruction")
        actual_old, actual_new = file_hash(original / "values.npy"), file_hash(fresh / "values.npy")
        if actual_old != old["values_sha256"] or actual_new != rebuilt["values_sha256"]:
            raise ValueError("A full prepared file failed its actual byte hash")
        unequal, maximum = 0, 0.0
        if actual_old != actual_new:
            left = np.load(original / "values.npy", mmap_mode="r", allow_pickle=False)
            right = np.load(fresh / "values.npy", mmap_mode="r", allow_pickle=False)
            if left.shape != right.shape or left.dtype != right.dtype:
                raise ValueError("Reproduced matrix axes/dtype differ")
            for start in range(0, len(left), 64):
                a, b = (
                    left[start : start + 64].astype(float),
                    right[start : start + 64].astype(float),
                )
                difference = np.abs(a - b)
                maximum = max(maximum, float(difference.max()))
                unequal += int(np.count_nonzero(a != b))
                if not np.all(difference <= 2e-7 + 2e-7 * np.abs(a)):
                    raise ValueError(
                        "Full matrix exceeds the previously declared float32 tolerance"
                    )
            del left, right, a, b, difference
        record = {
            "dataset": name,
            "original_directory": str(original),
            "rebuilt_directory": str(fresh),
            "raw_sha256": rebuilt["input_sha256"],
            "original_manifest_sha256": file_hash(original / "manifest.json"),
            "rebuilt_manifest_sha256": file_hash(fresh / "manifest.json"),
            "original_values_sha256": actual_old,
            "rebuilt_values_sha256": actual_new,
            "entire_npy_file_byte_identical": actual_old == actual_new,
            "complete_metadata_equal": True,
            "shape": rebuilt["shape"],
            "numeric_entries_verified": int(np.prod(rebuilt["shape"])),
            "unequal_float32_entries": unequal,
            "maximum_absolute_difference": maximum,
            "runtime_seconds_including_comparison": time.perf_counter() - before[0],
            "process_cpu_seconds_including_comparison": time.process_time() - before[1],
            "resources_start": resources_start,
            "resources_end": resource_record(root),
            "preparation_io": {
                key: {
                    "original": old["configuration"][key],
                    "rebuilt": rebuilt["configuration"][key],
                }
                for key in ("row_block_size", "column_block_size")
            },
        }
        write_json(receipt, record)
        records.append(record)
        print(
            "Full preparation matches", name, record["entire_npy_file_byte_identical"], flush=True
        )
    if file_hash(Path(__file__)) != identity["analysis_source_sha256"]:
        raise ValueError("Preparation reproduction analysis changed during execution")
    archive = args.evidence.with_suffix(".zip")
    if archive.exists():
        raise ValueError("Preparation metadata archive exists")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as packed:
        for filename in ("analysis-source.py", "code.zip", "identity.json"):
            packed.write(root / filename, filename)
        for record in records:
            name = record["dataset"]
            for filename in (f"{name}-configuration.json", f"{name}-comparison.json"):
                packed.write(root / filename, filename)
            packed.write(
                Path(record["rebuilt_directory"]) / "manifest.json", f"{name}-manifest.json"
            )
    write_json(
        args.evidence,
        {
            "state": "passed",
            "recorded_at": utc_now(),
            **identity,
            "datasets": records,
            "numeric_entries_verified": sum(r["numeric_entries_verified"] for r in records),
            "all_full_matrices_byte_identical": all(
                r["entire_npy_file_byte_identical"] for r in records
            ),
            "archive_sha256": file_hash(archive),
            "environment": environment,
            "runtime_seconds_this_pass": time.perf_counter() - started,
            "process_cpu_seconds_this_pass": time.process_time() - cpu_started,
            "qualification": (
                "All retained metadata and prepared values rebuilt from pinned raw files. "
                "Original artifacts remain unchanged; source-history hashes are preserved. "
                "IO batch sizes may differ, not scientific selection or transformation. "
                "Raw/rebuilt matrices remain ignored; archive contains only code/config/manifests."
            ),
        },
    )


if __name__ == "__main__":
    main()
