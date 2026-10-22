"""Compare paid legacy predictions and summarize integrated comparator diagnostics."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from mlresearch.models import BASE_BACKBONES
from mlresearch.provenance import file_hash, read_json, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("tuning", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Fidelity output exists")
    manifests = [read_json(path / "manifest.json") for path in (args.run, args.tuning)]
    if any(m["state"] != "complete" for m in manifests):
        raise ValueError("Only completed runs can be compared")
    indices = []
    for path, manifest in zip((args.run, args.tuning), manifests, strict=True):
        index_path = path / "prediction-index.json"
        if file_hash(index_path) != manifest["predictions_sha256"]:
            raise ValueError("Prediction index changed")
        items = read_json(index_path)
        indices.append({(i["policy"], i["seed"], i["budget"]): i for i in items})
    matched = {
        "worst_query": "worst_query",
        "fixed_grid": "fixed_cf125_d8",
        "bias_aware": "bias_gamma1",
        "bias_gamma025": "bias_aware",
    }
    equality = []
    for new, old in matched.items():
        for seed in manifests[0]["configuration"]["seeds"]:
            new_ledger = args.run / f"seed-{seed}" / new / "ledger.jsonl"
            old_ledger = args.tuning / f"seed-{seed}" / old / "ledger.jsonl"
            if new_ledger.read_bytes() != old_ledger.read_bytes():
                raise ValueError("Matched policy acquisitions changed")
            for budget in manifests[0]["configuration"]["budgets"]:
                pair = [indices[0][new, seed, budget], indices[1][old, seed, budget]]
                paths = [args.run / pair[0]["artifact"], args.tuning / pair[1]["artifact"]]
                for path, item in zip(paths, pair, strict=True):
                    if file_hash(path) != item["sha256"]:
                        raise ValueError("Prediction checkpoint changed")
                with (
                    np.load(paths[0], allow_pickle=False) as a,
                    np.load(paths[1], allow_pickle=False) as b,
                ):
                    for name in BASE_BACKBONES:
                        if a[name].dtype != b[name].dtype or a[name].tobytes() != b[name].tobytes():
                            raise ValueError(
                                f"Legacy prediction changed: {new}/{seed}/{budget}/{name}"
                            )
                equality.append(
                    {
                        "policy": new,
                        "tuning_policy": old,
                        "seed": seed,
                        "budget": budget,
                        "all_seven_predictions_byte_equal": True,
                    }
                )
    diagnostics: dict[str, list[dict]] = {}
    for (policy, _seed, _budget), item in indices[0].items():
        path = args.run / item["artifact"]
        if file_hash(path) != item["sha256"]:
            raise ValueError("Prediction checkpoint changed")
        with np.load(path, allow_pickle=False) as arrays:
            details = json.loads(str(arrays["transfer_diagnostics_json"]))
            details.update(
                source_half_ridge_cv_mean_shift=float(
                    np.mean(arrays["source_half_ridge_cv_max_shift_mse"])
                ),
                source_half_support_disagreements=int(
                    np.sum(arrays["source_half_support_disagreement"])
                ),
            )
        diagnostics.setdefault(policy, []).append(details)
    summaries = {}
    for policy, values in sorted(diagnostics.items()):
        summaries[policy] = {
            "checkpoints": len(values),
            "accepted_routes": sum(d["route_accepted"] for d in values),
            "missing_descriptors_per_checkpoint": sorted(
                {len(d["missing_control_descriptors"]) for d in values}
            ),
            "basis_ranks": dict(Counter(str(d["basis_rank"]) for d in values)),
            "selected_ridge": dict(Counter(str(d["selected_ridge"]) for d in values)),
            "optimizer_rounds_range": [
                min(d["base_fitting"]["executed_rounds"] for d in values),
                max(d["base_fitting"]["executed_rounds"] for d in values),
            ],
            "source_half_ridge_cv_mean_shift": float(
                np.mean([d["source_half_ridge_cv_mean_shift"] for d in values])
            ),
            "source_half_support_disagreements": sum(
                d["source_half_support_disagreements"] for d in values
            ),
        }
    result = {
        "analysis_source_sha256": file_hash(Path(__file__)),
        "run_manifest_sha256": file_hash(args.run / "manifest.json"),
        "tuning_manifest_sha256": file_hash(args.tuning / "manifest.json"),
        "matched_ledger_pairs": len(matched) * len(manifests[0]["configuration"]["seeds"]),
        "matched_checkpoint_pairs": len(equality),
        "matched_prediction_arrays": len(equality) * len(BASE_BACKBONES),
        "checks": equality,
        "comparator_diagnostics": summaries,
        "qualification": (
            "Source-half shifts and paid route validation are conditional diagnostics, "
            "not coverage guarantees."
        ),
    }
    write_json(args.output, result)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("checks", "comparator_diagnostics")},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
