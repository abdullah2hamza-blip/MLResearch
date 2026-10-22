"""Charged distinct-task query measurements after the sealed primary suite completes."""

from __future__ import annotations

import argparse
import json
import time
import zipfile
from pathlib import Path

import numpy as np

from mlresearch.acquisition import CONTROL, verify_ledger
from mlresearch.episodes import _ordered_sample, condition_rows, load_prepared, load_public_episode
from mlresearch.experiment import _write_csv
from mlresearch.external import validate_joint_freeze
from mlresearch.provenance import (
    environment_record,
    file_hash,
    object_hash,
    read_json,
    resource_record,
    utc_now,
    write_json,
)

GRID = ((2, 16), (4, 16), (8, 16), (16, 64), (32, 128), (64, 256))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--retained", type=Path, required=True)
    args = parser.parse_args()
    if read_json(args.suite / "manifest.json")["state"] != "complete":
        raise ValueError("Finish the sealed primary study before this stronger-information task")
    if args.output.exists() or args.retained.exists():
        raise ValueError("Direct-query output exists")
    freeze = validate_joint_freeze(args.suite / "joint-prediction-freeze.json")
    started = time.perf_counter()
    cpu_started = time.process_time()
    environment = environment_record()
    resources_start = resource_record(args.output.parent)
    args.output.mkdir(parents=True)
    records, metrics, summaries, ledger_paths, bindings = [], [], [], [], []
    for entry in freeze["runs"]:
        run = Path(entry["run_directory"])
        manifest = read_json(run / "manifest.json")
        if manifest["configuration"]["source_control"] != "none":
            continue
        episode = Path(manifest["configuration"]["episode_directory"])
        public = load_public_episode(episode)
        epi = read_json(episode / "manifest.json")
        banks = read_json(episode / "private-banks.json")
        prepared = Path(banks["target_prepared"])
        if not prepared.is_absolute():
            prepared = episode / prepared
        metadata, matrix, prepared_manifest = load_prepared(prepared)
        if prepared_manifest != epi["prepared_inputs"]["target"]:
            raise ValueError("Prepared recipient changed")
        groups = condition_rows(metadata, epi["configuration"]["target_context"])
        reserve = {}
        for identity in public.query_ids:
            ordered = _ordered_sample(
                groups[identity], metadata["cell_ids"], epi["configuration"]["seed"], identity
            )
            if ordered[64:96] != banks["assessment_rows"][identity]:
                raise ValueError("Original reserved query positions differ")
            reserve[identity] = ordered[:64]
        reserve[CONTROL] = banks["acquisition_rows"][CONTROL]
        forbidden = {cell for ids in banks["assessment_cell_ids"].values() for cell in ids}
        if any(metadata["cell_ids"][row] in forbidden for rows in reserve.values() for row in rows):
            raise ValueError("Direct measurement overlaps scorer cells")
        local = []
        print("Direct-query reference", run.name, flush=True)
        for seed in range(5):
            orders = {
                identity: _ordered_sample(rows, metadata["cell_ids"], seed, "direct:" + identity)
                for identity, rows in reserve.items()
            }
            for depth, controls in GRID:
                directory = args.output / run.name / f"seed-{seed}" / f"depth-{depth}"
                directory.mkdir(parents=True)
                events, spent, previous = [], 0, None
                selected = {CONTROL: orders[CONTROL][:controls]}
                selected.update({q: orders[q][:depth] for q in public.query_ids})
                for identity, rows in selected.items():
                    cost = len(rows) + (4 if identity != CONTROL else 0)
                    spent += cost
                    event = {
                        "sequence": len(events),
                        "previous_sha256": previous,
                        "action": {"intervention": identity, "cells": len(rows)},
                        "cell_ids": [metadata["cell_ids"][row] for row in rows],
                        "cost": cost,
                        "spent": spent,
                    }
                    event["sha256"] = object_hash(event)
                    previous = event["sha256"]
                    events.append(event)
                expected_cost = len(public.query_ids) * (depth + 4) + controls
                if spent != expected_cost:
                    raise ValueError("Direct cost arithmetic failed")
                # No sealed-query prohibition here: this is explicitly different task C.
                verify_ledger(events, budget=expected_cost, setup_cost=4)
                ledger = directory / "ledger.jsonl"
                ledger.write_text(
                    "".join(json.dumps(e, sort_keys=True) + "\n" for e in events), encoding="utf-8"
                )
                ledger_paths.append(ledger)
                control = np.asarray(matrix[np.ix_(selected[CONTROL], banks["target_columns"])])
                mean_control = control.mean(axis=0, dtype=np.float64)
                prediction = np.asarray(
                    [
                        np.asarray(matrix[np.ix_(selected[q], banks["target_columns"])]).mean(
                            axis=0, dtype=np.float64
                        )
                        - mean_control
                        for q in public.query_ids
                    ],
                    dtype=np.float32,
                )
                artifact = directory / "prediction.npz"
                np.savez(artifact, direct_query=prediction)
                local.append(
                    {
                        "run": run.name,
                        "seed": seed,
                        "query_depth": depth,
                        "control_depth": controls,
                        "spent": spent,
                        "artifact": str(artifact.relative_to(args.output)),
                        "artifact_sha256": file_hash(artifact),
                        "ledger": str(ledger.relative_to(args.output)),
                        "ledger_sha256": file_hash(ledger),
                        "query_count": len(public.query_ids),
                    }
                )
        # All distinct-task predictions for this direction close before its diagnostic scoring.
        write_json(args.output / run.name / "prediction-index.json", local)
        with np.load(run / "assessment.npz", allow_pickle=False) as arrays:
            truth = np.asarray(arrays["effects"], dtype=np.float64)
        assessment_control = np.asarray(
            matrix[np.ix_(banks["assessment_rows"][CONTROL], banks["target_columns"])],
            dtype=np.float64,
        ).mean(axis=0)
        rebuilt_truth = np.asarray(
            [
                np.asarray(
                    matrix[np.ix_(banks["assessment_rows"][q], banks["target_columns"])],
                    dtype=np.float64,
                ).mean(axis=0)
                - assessment_control
                for q in public.query_ids
            ]
        )
        np.testing.assert_array_equal(truth, rebuilt_truth)
        bindings.append(
            {
                "run": run.name,
                "episode_manifest_sha256": file_hash(episode / "manifest.json"),
                "prepared_values_sha256": prepared_manifest["values_sha256"],
                "primary_assessment_sha256": file_hash(run / "assessment.npz"),
                "assessment_independently_recomputed_from_verified_rows": True,
            }
        )
        for item in local:
            with np.load(args.output / item["artifact"], allow_pickle=False) as arrays:
                prediction = arrays["direct_query"].astype(np.float64)
            errors = np.mean((prediction - truth) ** 2, axis=1)
            centered = np.mean(
                ((prediction - prediction.mean(axis=0)) - (truth - truth.mean(axis=0))) ** 2,
                axis=1,
            )
            for i, query in enumerate(public.query_ids):
                metrics.append(
                    {
                        **{
                            k: item[k]
                            for k in ("run", "seed", "query_depth", "control_depth", "spent")
                        },
                        "query": query,
                        "mse": float(errors[i]),
                        "specificity_mse": float(centered[i]),
                    }
                )
            summaries.append({**item, "mean_mse": float(errors.mean())})
        records.extend(local)
    args.retained.mkdir(parents=True)
    _write_csv(args.retained / "per-query-metrics.csv", metrics)
    _write_csv(args.retained / "checkpoint-summary.csv", summaries)
    write_json(args.retained / "prediction-index.json", records)
    with zipfile.ZipFile(
        args.retained / "charged-query-ledgers.zip", "x", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for ledger in ledger_paths:
            archive.write(ledger, ledger.relative_to(args.output).as_posix())
    result = {
        "state": "complete",
        "recorded_at": utc_now(),
        "analysis_source_sha256": file_hash(Path(__file__)),
        "primary_suite_manifest_sha256": file_hash(args.suite / "manifest.json"),
        "runtime_seconds": time.perf_counter() - started,
        "process_cpu_seconds": time.process_time() - cpu_started,
        "environment": environment,
        "resources_start": resources_start,
        "resources_end": resource_record(args.output),
        "prediction_checkpoints": len(records),
        "metric_rows": len(metrics),
        "charged_cost_grid": sorted({r["spent"] for r in records}),
        "bindings": bindings,
        "role": (
            "Distinct stronger-information task C; post-primary diagnostic, not sealed acquisition"
        ),
        "qualification": (
            "Even minimum all-query cost802 exceeds primary budget512. No equal-cost primary "
            "comparison is observed; no economic crossover is inferred. Assessment cells disjoint. "
            "Counterfactual depth/seed ledgers reuse pools separately; "
            "no repeated cell within a ledger."
        ),
    }
    write_json(args.output / "manifest.json", result)
    write_json(args.retained / "manifest.json", result)
    print("Direct-query reference complete", len(records), "checkpoints", flush=True)


if __name__ == "__main__":
    main()
