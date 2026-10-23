"""Authenticate the historical epsilon-only route flags without modifying predictions."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import Counter
from pathlib import Path

import numpy as np

from mlresearch.provenance import file_hash, read_json, utc_now, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--retained", type=Path, default=Path("docs/results/external-evaluation-v1")
    )
    parser.add_argument("--run-root", type=Path, default=Path("runs"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve the existing gate audit")
    diagnostic = args.retained / "diagnostics/checkpoint-diagnostics.jsonl.gz"
    retained = read_json(args.retained / "supplement-artifacts.json")
    if (
        file_hash(diagnostic)
        != retained["sha256"][diagnostic.relative_to(args.retained).as_posix()]
    ):
        raise ValueError("Frozen diagnostics changed")
    with gzip.open(diagnostic, "rt", encoding="utf-8") as stream:
        records = [json.loads(line) for line in stream]
    if len(records) != 720:
        raise ValueError("Expected all 720 original checkpoints")
    indexes, changed, bindings = {}, [], {}
    positives = 0
    for row in records:
        run = args.run_root / row["run"]
        if row["run"] not in indexes:
            manifest = read_json(run / "manifest.json")
            index = run / "prediction-index.json"
            if file_hash(index) != manifest["predictions_sha256"]:
                raise ValueError("Original prediction index changed")
            indexes[row["run"]] = read_json(index)
            bindings[row["run"]] = file_hash(index)
        checkpoint, values = row["checkpoint"], row["diagnostics"]
        if checkpoint not in indexes[row["run"]]:
            raise ValueError("Retained checkpoint differs from authenticated index")
        gain = max(0.0, values["base_validation_mse"] - values["proposal_validation_mse"])
        corrected_rho = gain / max(values["base_validation_mse"], 1e-12)
        accepted = values["alpha"] > 0 and gain > 0
        if not values["route_accepted"]:
            raise ValueError("Unexpected historical gate state")
        if accepted:
            positives += 1
            continue
        if values["alpha"] != 0 or gain != 0:
            raise ValueError("Unexpected nonzero-alpha gate rejection; investigate predictions")
        path = run / checkpoint["artifact"].replace("\\", "/")
        if file_hash(path) != checkpoint["sha256"]:
            raise ValueError("Affected historical prediction file changed")
        with np.load(path, allow_pickle=False) as arrays:
            reconstruction = arrays["perturbmap_reconstruction"]
            baseline = arrays["recipient_local_lowrank"]
            exact = (
                reconstruction.dtype == baseline.dtype
                and reconstruction.shape == baseline.shape
                and reconstruction.tobytes() == baseline.tobytes()
            )
        if not exact:
            raise ValueError("A rejected historical route changed predictions")
        changed.append(
            {
                "run": row["run"],
                "seed": checkpoint["seed"],
                "policy": checkpoint["policy"],
                "budget": checkpoint["budget"],
                "artifact_sha256": checkpoint["sha256"],
                "alpha": values["alpha"],
                "legacy_rho": values["rho"],
                "corrected_rho": corrected_rho,
                "reconstruction_equals_local_base_bytes": exact,
            }
        )
    if len(changed) != 20 or positives != 700:
        raise ValueError("Gate counts differ from the independent review; investigate")
    args.output.mkdir(parents=True)
    with (args.output / "affected-checkpoints.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(changed[0]))
        writer.writeheader()
        writer.writerows(changed)
    write_json(
        args.output / "summary.json",
        {
            "state": "passed",
            "recorded_at": utc_now(),
            "analysis_source_sha256": file_hash(Path(__file__)),
            "historical_diagnostics_sha256": file_hash(diagnostic),
            "prediction_index_sha256": bindings,
            "historical_accepted_flags": len(records),
            "strict_positive_calibration_gain": positives,
            "epsilon_only_zero_alpha_flags": len(changed),
            "affected_artifacts_authenticated_and_baseline_byte_equal": len(changed),
            "affected_counts_by_run": dict(Counter(r["run"] for r in changed)),
            "all_prediction_arrays_unaffected_by_gate_correction": True,
            "qualification": (
                "Twenty zero-alpha gates change diagnostic status only; all 700 positive-alpha "
                "strict gains remain routed. Alpha calculation is unchanged in version0.2.0; "
                "rho magnitude does not weight single-source predictions. Historical artifacts "
                "are preserved. Fitted calibration gain is not independent reliability."
            ),
        },
    )
    print("Authenticated all720 gate records;20 epsilon-only flags have identical baseline bytes")


if __name__ == "__main__":
    main()
