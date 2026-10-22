"""Independently reconcile complete external timing, paid inventory and invariance checks."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np

from mlresearch.episodes import load_public_episode
from mlresearch.experiment import verify_frozen_predictions
from mlresearch.external import validate_joint_freeze
from mlresearch.provenance import file_hash, read_json, utc_now, write_json


def audit(root: Path) -> dict:
    manifest = read_json(root / "manifest.json")
    if manifest["state"] != "complete":
        raise ValueError("Complete the frozen suite before this post-scoring audit")
    gate_path = root / "joint-prediction-freeze.json"
    gate = validate_joint_freeze(gate_path)
    frozen_at = datetime.fromisoformat(gate["frozen_at"])
    records, zero_pairs, fixed_pairs = [], [], []
    completed = {}
    for entry in gate["runs"]:
        run = Path(entry["run_directory"])
        current = read_json(run / "manifest.json")
        if current["state"] != "complete":
            raise ValueError("Incomplete peer")
        cfg = current["configuration"]
        episode = Path(cfg["episode_directory"])
        public = load_public_episode(episode)
        verify_frozen_predictions(run, current, public)
        frozen = read_json(root / entry["acquisition_manifest"])
        access = read_json(run / "assessment-access.json")
        if (
            not datetime.fromisoformat(frozen["predictions_frozen_at"])
            <= frozen_at
            < (datetime.fromisoformat(access["opened_at"]))
        ):
            raise ValueError("Assessment did not follow the joint prediction barrier")
        if access["joint_prediction_freeze"]["sha256"] != file_hash(gate_path):
            raise ValueError("Assessment binding changed")
        banks = read_json(episode / "private-banks.json")
        allowed = {k: set(v) for k, v in banks["acquisition_cell_ids"].items()}
        forbidden = {v for cells in banks["assessment_cell_ids"].values() for v in cells}
        if set(public.query_ids) & set(allowed):
            raise ValueError("Queries have acquisition banks")
        if forbidden & set().union(*allowed.values()):
            raise ValueError("Assessment/acquisition banks overlap")
        ledgers = []
        for seed in cfg["seeds"]:
            for policy in cfg["policies"]:
                ledger = run / f"seed-{seed}" / policy / "ledger.jsonl"
                seen, opened, spent = set(), set(), 0
                events = [
                    json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()
                ]
                for event in events:
                    action = event["action"]
                    identity, count = action["intervention"], action["cells"]
                    cells = event["cell_ids"]
                    if (
                        identity not in allowed
                        or count != len(cells)
                        or len(set(cells)) != count
                        or seen.intersection(cells)
                        or forbidden.intersection(cells)
                        or set(cells) - allowed[identity]
                    ):
                        raise ValueError("Invalid, repeated or scorer-only purchase")
                    control = identity == "__control__"
                    cost = count * cfg["policy"]["control_cell_cost" if control else "cell_cost"]
                    if not control and identity not in opened:
                        cost += cfg["policy"]["setup_cost"]
                        opened.add(identity)
                    spent += cost
                    if event["cost"] != cost or event["spent"] != spent:
                        raise ValueError("Independent cost recomputation failed")
                    seen.update(cells)
                if spent > max(cfg["budgets"]):
                    raise ValueError("Overspending")
                ledgers.append({"seed": seed, "policy": policy, "cells": len(seen), "spent": spent})
            if "bias_no_extension" in cfg["policies"]:
                a = run / f"seed-{seed}" / "bias_no_extension" / "ledger.jsonl"
                b = run / f"seed-{seed}" / "worst_query" / "ledger.jsonl"
                if a.read_bytes() != b.read_bytes():
                    raise ValueError("Zero-weight extension differs from classical acquisition")
                zero_pairs.append({"run": run.name, "seed": seed, "sha256": file_hash(a)})
        completed[str(episode.resolve()), cfg["source_control"]] = (run, current)
        records.append(
            {
                "run": run.name,
                "predictions_frozen_at": frozen["predictions_frozen_at"],
                "assessment_opened_at": access["opened_at"],
                "prediction_checkpoints": len(read_json(run / "prediction-index.json")),
                "prediction_index_sha256": current["predictions_sha256"],
                "run_manifest_sha256": file_hash(run / "manifest.json"),
                "assessment_access_sha256": file_hash(run / "assessment-access.json"),
                "scorer_only_cells": access["resource_cells"],
                "independently_reconciled_ledgers": ledgers,
            }
        )
    for (episode, control), (altered, cfg_record) in completed.items():
        if control != "query_gene_permutation":
            continue
        original, _ = completed[episode, "none"]
        cfg = cfg_record["configuration"]
        for seed in cfg["seeds"]:
            a = original / f"seed-{seed}" / "fixed_grid"
            b = altered / f"seed-{seed}" / "fixed_grid"
            if (a / "ledger.jsonl").read_bytes() != (b / "ledger.jsonl").read_bytes():
                raise ValueError("Query-gene permutation changed fixed purchases")
            for budget in cfg["budgets"]:
                with (
                    np.load(a / f"budget-{budget}.npz", allow_pickle=False) as left,
                    np.load(b / f"budget-{budget}.npz", allow_pickle=False) as right,
                ):
                    for name in ("zero", "mean", "recipient_local_lowrank"):
                        if name not in left.files:
                            raise ValueError("Expected fixed-grid invariant backbone absent")
                        if not np.array_equal(left[name], right[name]):
                            raise ValueError(
                                "Query-only corruption changed a recipient-only predictor"
                            )
                fixed_pairs.append({"run": altered.name, "seed": seed, "budget": budget})
    return {
        "recorded_at": utc_now(),
        "analysis_source_sha256": file_hash(Path(__file__)),
        "suite_manifest_sha256": file_hash(root / "manifest.json"),
        "joint_gate_sha256": file_hash(gate_path),
        "joint_frozen_at": gate["frozen_at"],
        "runs": records,
        "zero_weight_classical_byte_identical_pairs": zero_pairs,
        "query_gene_fixed_grid_unchanged_checkpoints": fixed_pairs,
        "qualification": (
            "Full artifact/index and ledger-prefix authentication plus independent inventory/cost "
            "reconciliation. Timestamps and hashes document the cooperative runner boundary; "
            "they do not sandbox a hostile filesystem process. Counterfactual policies reuse cells."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Audit output exists")
    result = audit(args.suite)
    write_json(args.output, result)
    print("Audited", sum(r["prediction_checkpoints"] for r in result["runs"]), "checkpoints")


if __name__ == "__main__":
    main()
