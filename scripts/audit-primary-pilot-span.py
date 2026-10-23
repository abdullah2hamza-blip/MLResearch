"""Check the actual primary pilot's source-feature span using public sources and ledgers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from mlresearch.acquisition import CONTROL, verify_ledger
from mlresearch.episodes import load_public_episode
from mlresearch.models import source_coordinates
from mlresearch.provenance import file_hash, read_json, utc_now, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve the existing pilot audit")
    records, inputs = [], {}
    for direction in ("k562-to-rpe1", "rpe1-to-k562"):
        run = Path(f"runs/external-{direction}-v1")
        manifest = read_json(run / "manifest.json")
        episode = Path(manifest["configuration"]["episode_directory"])
        if file_hash(episode / "manifest.json") != manifest["episode_manifest_sha256"]:
            raise ValueError("Primary episode changed")
        public = load_public_episode(episode)
        coordinates = source_coordinates(public, 4)
        queries = coordinates.features[[public.index(q) for q in public.query_ids]]
        inputs[str(episode / "manifest.json")] = file_hash(episode / "manifest.json")
        models = Path("src/mlresearch/models.py")
        if file_hash(models) != manifest["environment"]["source_hashes"]["models.py"]:
            raise ValueError("Source-coordinate implementation differs from the primary freeze")
        for seed in range(5):
            path = run / f"seed-{seed}/worst_query/ledger.jsonl"
            with path.open(encoding="utf-8") as stream:
                events = [json.loads(line) for line in stream]
            pilot = events[:7]
            verify_ledger(pilot, budget=88, setup_cost=4, query_ids=public.query_ids)
            identities = [e["action"]["intervention"] for e in pilot[1:]]
            if (
                pilot[0]["action"] != {"intervention": CONTROL, "cells": 16}
                or len(identities) != 6
                or any(e["action"]["cells"] != 8 for e in pilot[1:])
                or pilot[-1]["spent"] != 88
            ):
                raise ValueError("Unexpected original pilot")
            features = coordinates.features[[public.index(i) for i in identities]]
            _, singular, vectors = np.linalg.svd(features, full_matrices=False)
            rank = int(np.sum(singular > singular[0] * 1e-9))
            basis = vectors[:rank]
            residual = np.linalg.norm(queries - queries @ basis.T @ basis, axis=1)
            relative = residual / np.linalg.norm(queries, axis=1)
            if rank != 5 or np.max(relative) >= 1e-9:
                raise ValueError("The primary pilot did not span every source query")
            for policy in manifest["configuration"]["policies"]:
                peer = run / f"seed-{seed}/{policy}/ledger.jsonl"
                with peer.open(encoding="utf-8") as stream:
                    if [json.loads(next(stream)) for _ in range(7)] != pilot:
                        raise ValueError("Primary policies have different pilot prefixes")
            records.append(
                {
                    "direction": direction,
                    "seed": seed,
                    "pilot_interventions": identities,
                    "pilot_feature_rank": rank,
                    "feature_dimension_including_intercept": features.shape[1],
                    "maximum_relative_query_projection_residual": float(np.max(relative)),
                    "minimum_pilot_feature_singular_value": float(singular[-1]),
                    "all_policy_pilot_prefixes_equal": True,
                    "ledger_sha256": file_hash(path),
                    "pilot_spend": 88,
                }
            )
    write_json(
        args.output,
        {
            "state": "passed",
            "recorded_at": utc_now(),
            "analysis_source_sha256": file_hash(Path(__file__)),
            "input_episode_sha256": inputs,
            "public_source_rank": 4,
            "pilot_fraction_of_first_budget": 88 / 128,
            "records": records,
            "qualification": (
                "Source-feature span at the actual pilot, not population transport identification. "
                "No recipient outcomes were read; positive control precision makes this span "
                "the ideal fixed-feature GLS estimability condition. Frozen numeric support "
                "at reported budgets is a separate retained diagnostic."
            ),
        },
    )
    print("All10 primary pilots span all5 source coefficients; all160 policy prefixes matched")


if __name__ == "__main__":
    main()
