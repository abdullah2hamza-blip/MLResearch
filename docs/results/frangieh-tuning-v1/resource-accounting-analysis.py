"""Recompute unique exposed development resources from authenticated saved runs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from mlresearch.acquisition import CONTROL, verify_ledger
from mlresearch.episodes import load_public_episode
from mlresearch.provenance import file_hash, object_hash, read_json, write_json


def account_development(runs: list[Path]) -> dict[str, Any]:
    if not runs:
        raise ValueError("At least one development run required")
    groups: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    sources: dict[str, set[str]] = defaultdict(set)
    contexts: dict[str, dict[str, Any]] = {}
    context_owners: dict[str, dict[str, str]] = defaultdict(dict)
    records = []
    costs = None
    for run in dict.fromkeys(path.resolve() for path in runs):
        manifest = read_json(run / "manifest.json")
        if manifest["state"] != "complete":
            raise ValueError("Only completed development runs may inform accounting")
        policy = manifest["configuration"]["policy"]
        schedule = {key: policy[key] for key in ("setup_cost", "cell_cost", "control_cell_cost")}
        if costs is not None and costs != schedule:
            raise ValueError("Development costs use inconsistent unit schedules")
        costs = schedule
        episode = Path(manifest["configuration"]["episode_directory"])
        if file_hash(episode / "manifest.json") != manifest["episode_manifest_sha256"]:
            raise ValueError("Frozen episode changed")
        public = load_public_episode(episode)
        declaration = read_json(episode / "manifest.json")
        banks = read_json(episode / "private-banks.json")
        context = declaration["configuration"]["target_context"]
        raw_sha = declaration["prepared_inputs"]["target"]["input_sha256"]
        namespace = object_hash({"input_sha256": raw_sha, "context": context})
        contexts[namespace] = {"input_sha256": raw_sha, "context": context}
        source_key = declaration["prepared_inputs"]["source"]["input_sha256"]
        sources[source_key].update(banks["source_cell_ids"])
        owners: dict[str, str] = {}
        acquisition = {}
        for identity, identifiers in banks["acquisition_cell_ids"].items():
            acquisition[identity] = set(identifiers)
            for key in identifiers:
                if key in owners and owners[key] != identity:
                    raise ValueError("Cell identity has multiple intervention owners")
                owners[key] = identity
        for identity, identifiers in banks["assessment_cell_ids"].items():
            for key in identifiers:
                if key in owners:
                    raise ValueError("Acquisition and assessment cell IDs overlap")
                owners[key] = identity
        for key, identity in owners.items():
            if key in context_owners[namespace] and context_owners[namespace][key] != identity:
                raise ValueError("Cell intervention ownership differs between development runs")
            context_owners[namespace][key] = identity
        ledger_hashes = {}
        for seed in manifest["configuration"]["seeds"]:
            for name in manifest["configuration"]["policies"]:
                path = run / f"seed-{seed}" / name / "ledger.jsonl"
                events = [
                    json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                ]
                verify_ledger(
                    events,
                    budget=manifest["configuration"]["budgets"][-1],
                    query_ids=public.query_ids,
                    **costs,
                )
                ledger_hashes[path.relative_to(run).as_posix()] = file_hash(path)
                for event in events:
                    identity = event["action"]["intervention"]
                    if not set(event["cell_ids"]) <= acquisition[identity]:
                        raise ValueError("Purchase contains cells outside its acquisition bank")
                    groups[namespace][identity].update(event["cell_ids"])
        access = read_json(run / "assessment-access.json")
        if (
            file_hash(run / "prediction-index.json") != manifest["predictions_sha256"]
            or access["prediction_index_sha256_before_opening"] != manifest["predictions_sha256"]
        ):
            raise ValueError("Assessment access does not match frozen predictions")
        if set(access["query_cell_ids"]) != set(public.query_ids):
            raise ValueError("Assessment access identities differ from queries")
        if access["control_cell_ids"] != banks["assessment_cell_ids"][CONTROL]:
            raise ValueError("Control assessment bank changed")
        groups[namespace][CONTROL].update(access["control_cell_ids"])
        for identity, identifiers in access["query_cell_ids"].items():
            if identifiers != banks["assessment_cell_ids"][identity]:
                raise ValueError("Query assessment bank changed")
            groups[namespace][identity].update(identifiers)
        records.append(
            {
                "run": str(run),
                "manifest_sha256": file_hash(run / "manifest.json"),
                "assessment_access_sha256": file_hash(run / "assessment-access.json"),
                "episode_manifest_sha256": manifest["episode_manifest_sha256"],
                "ledger_sha256": ledger_hashes,
            }
        )
    assert costs is not None
    rows = []
    for namespace, by_intervention in sorted(groups.items()):
        controls = len(by_intervention.get(CONTROL, set()))
        perturbed = sum(len(ids) for key, ids in by_intervention.items() if key != CONTROL)
        opened = len(set(by_intervention) - {CONTROL})
        rows.append(
            {
                **contexts[namespace],
                "unique_controls": controls,
                "unique_perturbed_cells": perturbed,
                "unique_opened_interventions": opened,
                "unique_resource_cost_units": controls * costs["control_cell_cost"]
                + perturbed * costs["cell_cost"]
                + opened * costs["setup_cost"],
            }
        )
    return {
        "schema_version": 1,
        "analysis_source_sha256": file_hash(Path(__file__)),
        "description": (
            "Union of predictor-visible acquisitions and scorer cells that informed development"
        ),
        **costs,
        "unique_controls_acquisition_and_assessment": sum(row["unique_controls"] for row in rows),
        "unique_perturbed_cells_acquisition_and_assessment": sum(
            row["unique_perturbed_cells"] for row in rows
        ),
        "unique_opened_interventions_acquisition_and_assessment": sum(
            row["unique_opened_interventions"] for row in rows
        ),
        "unique_resource_cost_units": sum(row["unique_resource_cost_units"] for row in rows),
        "fixed_public_source_cells": sum(len(ids) for ids in sources.values()),
        "recipient_contexts": rows,
        "runs": records,
        "limitations": (
            "Unique retrospective union counts shared cells once; counterfactual policy ledgers "
            "each pay separately. Source/computation resources are separate. "
            "No biological replication is implied."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("runs", type=Path, nargs="+")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Accounting output exists")
    result = account_development(args.runs)
    write_json(args.output, result)
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key not in ("runs", "recipient_contexts")
            },
            indent=2,
        )
    )
