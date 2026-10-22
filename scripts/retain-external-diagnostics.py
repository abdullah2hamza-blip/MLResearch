"""Retain small authenticated training/validation and source-half diagnostics, without arrays."""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from mlresearch.external import validate_joint_freeze
from mlresearch.provenance import file_hash, read_json, utc_now, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if read_json(args.suite / "manifest.json")["state"] != "complete":
        raise ValueError("Complete the frozen suite first")
    if args.output.exists():
        raise ValueError("Diagnostic output exists")
    freeze = validate_joint_freeze(args.suite / "joint-prediction-freeze.json")
    groups = defaultdict(list)
    records = []
    for entry in freeze["runs"]:
        run = Path(entry["run_directory"])
        for item in read_json(run / "prediction-index.json"):
            artifact = run / item["artifact"]
            if file_hash(artifact) != item["sha256"]:
                raise ValueError("Prediction checkpoint changed")
            with np.load(artifact, allow_pickle=False) as arrays:
                details = json.loads(str(arrays["transfer_diagnostics_json"]))
                details.update(
                    source_half_ridge_cv_mean_shift=float(
                        np.mean(arrays["source_half_ridge_cv_max_shift_mse"])
                    ),
                    source_half_support_disagreements=int(
                        np.sum(arrays["source_half_support_disagreement"])
                    ),
                    source_half_paid_penalties=arrays["source_half_ridge_cv_penalties"].tolist(),
                    paid_ridge_cv_selected=float(arrays["ridge_cv_selected"]),
                )
            records.append({"run": run.name, "checkpoint": item, "diagnostics": details})
            groups[run.name, item["policy"]].append(details)
    summaries = []
    for (run, policy), values in sorted(groups.items()):
        summaries.append(
            {
                "run": run,
                "policy": policy,
                "checkpoints": len(values),
                "accepted_routes": sum(d["route_accepted"] for d in values),
                "missing_descriptors_per_checkpoint": sorted(
                    {len(d["missing_control_descriptors"]) for d in values}
                ),
                "basis_ranks": dict(Counter(str(d["basis_rank"]) for d in values)),
                "transport_selected_ridge": dict(Counter(str(d["selected_ridge"]) for d in values)),
                "paid_ridge_cv_selected": dict(
                    Counter(str(d["paid_ridge_cv_selected"]) for d in values)
                ),
                "optimizer_rounds_range": [
                    min(d["base_fitting"]["executed_rounds"] for d in values),
                    max(d["base_fitting"]["executed_rounds"] for d in values),
                ],
                "source_half_mean_ridge_cv_shift": float(
                    np.mean([d["source_half_ridge_cv_mean_shift"] for d in values])
                ),
                "source_half_support_disagreements": sum(
                    d["source_half_support_disagreements"] for d in values
                ),
            }
        )
    args.output.mkdir(parents=True)
    archive = args.output / "checkpoint-diagnostics.jsonl.gz"
    with archive.open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, mtime=0) as packed:
            for record in records:
                packed.write((json.dumps(record, sort_keys=True) + "\n").encode())
    write_json(
        args.output / "summary.json",
        {
            "recorded_at": utc_now(),
            "analysis_source_sha256": file_hash(Path(__file__)),
            "suite_manifest_sha256": file_hash(args.suite / "manifest.json"),
            "checkpoints": len(records),
            "archive_sha256": file_hash(archive),
            "groups": summaries,
            "qualification": (
                "Full paid training/validation identities and optimizer diagnostics retained. "
                "Validation acceptance is not independent assessment success; source-half "
                "displacements and conditional support are not population certificates."
            ),
        },
    )
    print("Retained small diagnostics for", len(records), "checkpoints", flush=True)


if __name__ == "__main__":
    main()
