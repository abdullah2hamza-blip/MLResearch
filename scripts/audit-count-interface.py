"""Verify the capped count interface and invariance to unused count annotations."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from dataclasses import fields
from pathlib import Path

import numpy as np

from mlresearch.acquisition import CONTROL
from mlresearch.episodes import load_public_episode
from mlresearch.external import validate_joint_freeze
from mlresearch.provenance import file_hash, read_json, utc_now, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if read_json(args.suite / "manifest.json")["state"] != "complete":
        raise ValueError("Finish the primary study before its secondary count audit")
    if args.output.exists():
        raise ValueError("Count audit output exists")
    freeze = validate_joint_freeze(args.suite / "joint-prediction-freeze.json")
    cache = Path(".cache").resolve()
    if not cache.is_relative_to(Path.cwd().resolve()):
        raise ValueError("Temporary audit files must remain inside the workspace")
    cache.mkdir(exist_ok=True)
    records = []
    for entry in freeze["runs"]:
        run = Path(entry["run_directory"])
        manifest = read_json(run / "manifest.json")
        if manifest["configuration"]["source_control"] != "none":
            continue
        episode = Path(manifest["configuration"]["episode_directory"])
        epi = read_json(episode / "manifest.json")
        public = load_public_episode(episode)
        banks = read_json(episode / "private-banks.json")
        candidate_sizes = {len(v) for k, v in banks["acquisition_rows"].items() if k != CONTROL}
        source_sizes = {v for k, v in banks["source_counts"].items() if k != CONTROL}
        if candidate_sizes != {64} or source_sizes != {96}:
            raise ValueError("Declared count-uniform external interface changed")
        prepared = Path(banks["target_prepared"])
        if not prepared.is_absolute():
            prepared = episode / prepared
        metadata_path = prepared / "metadata.json"
        if file_hash(metadata_path) != epi["prepared_inputs"]["target"]["metadata_sha256"]:
            raise ValueError("Inventory metadata changed")
        inventory = read_json(metadata_path)["condition_inventory"]
        uncapped = {
            r["intervention"]: r["eligible_cells"]
            for r in inventory
            if r["intervention"] in public.interventions
        }
        with tempfile.TemporaryDirectory(prefix="count-interface-", dir=cache) as temporary:
            copied = Path(temporary).resolve()
            # Verify the exact target before TemporaryDirectory's recursive cleanup.
            if not copied.is_relative_to(cache):
                raise ValueError("Temporary cleanup target escaped the verified cache")
            for name in ("source.npz", "public.json", "private-banks.json"):
                shutil.copyfile(episode / name, copied / name)
            annotated = read_json(copied / "public.json")
            annotated["uncapped_raw_counts"] = uncapped
            annotated["adversarial_count_annotation"] = {
                q: 1 + i * i for i, q in enumerate(public.interventions)
            }
            write_json(copied / "public.json", annotated)
            copied_manifest = read_json(episode / "manifest.json")
            copied_manifest["sha256"]["public.json"] = file_hash(copied / "public.json")
            write_json(copied / "manifest.json", copied_manifest)
            decoded = load_public_episode(copied)
            for field in fields(public):
                left, right = getattr(public, field.name), getattr(decoded, field.name)
                if isinstance(left, np.ndarray):
                    np.testing.assert_array_equal(left, right)
                elif left != right:
                    raise ValueError("Count annotation altered a policy input")
        records.append(
            {
                "run": run.name,
                "episode_manifest_sha256": file_hash(episode / "manifest.json"),
                "uniform_candidate_pool_cells": sorted(candidate_sizes),
                "uniform_source_condition_cells": sorted(source_sizes),
                "actual_uncapped_eligible_counts_range": [
                    min(uncapped.values()),
                    max(uncapped.values()),
                ],
                "all_policy_public_fields_identical_after_count_annotation": True,
                "public_fields": [f.name for f in fields(public)],
            }
        )
    write_json(
        args.output,
        {
            "state": "passed",
            "recorded_at": utc_now(),
            "analysis_source_sha256": file_hash(Path(__file__)),
            "primary_suite_manifest_sha256": file_hash(args.suite / "manifest.json"),
            "runs": records,
            "qualification": (
                "Conditional fixed-cohort count-blind interface check: varying unused raw-count "
                "annotations leaves every policy input identical; deterministic predictions "
                "cannot depend on those annotations. No new cohort or policy rerun is claimed. "
                "Eligibility still requires counts>=96; capture/survival selection bias remains. "
                "Paid sample counts and finite remaining availability are necessarily visible."
            ),
        },
    )
    print("Count-uniform interface and annotation invariance passed", len(records), "directions")


if __name__ == "__main__":
    main()
