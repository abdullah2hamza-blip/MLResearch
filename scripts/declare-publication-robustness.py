"""Freeze the PI-requested split/rank/budget robustness matrix before acquisition."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from mlresearch.episodes import load_public_episode
from mlresearch.external import ExternalConfig
from mlresearch.identifiers import verify_identifier_record
from mlresearch.provenance import (
    environment_record,
    file_hash,
    object_hash,
    read_json,
    resource_record,
    snapshot_sources,
    utc_now,
    write_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/publication-robustness-v1.json")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/evidence/publication-robustness-declaration-v1.json"),
    )
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".zip").exists():
        raise ValueError("Preserve the original robustness declaration")
    config = ExternalConfig.load(args.config)
    if len(config.runs) != 8 or Path(config.output_directory).exists():
        raise ValueError("Expected eight unstarted robustness runs")
    environment = environment_record()
    original_policy = read_json(Path("configs/external-evaluation-v1.json"))["runs"][0]["policy"]
    combinations, episodes = set(), {}
    for run in config.runs:
        if Path(run.output_directory).exists():
            raise ValueError("Robustness acquisition already started")
        if object_hash(asdict(run.policy)) != object_hash(
            original_policy | {"rank": run.policy.rank}
        ):
            raise ValueError("An undeclared policy setting changed from the frozen main design")
        if (
            run.budgets != [128, 256, 512, 1024, 2048]
            or run.seeds != [0, 1, 2]
            or run.policies != ["worst_query", "mean_query", "bias_aware"]
            or run.primary_backbone != "ridge_cv"
            or run.transfer is not None
            or run.variants
            or run.policy.discrepancy_weight != 1
            or not run.source_sensitivity
        ):
            raise ValueError("Robustness matrix differs from declared settings")
        episode = Path(run.episode_directory)
        manifest = read_json(episode / "manifest.json")
        public = load_public_episode(episode)
        verify_identifier_record(
            public,
            manifest,
            Path(run.identifier_record),
            episode_sha256=file_hash(episode / "manifest.json"),
        )
        declaration = manifest["configuration"]
        combinations.add((declaration["seed"], declaration["source_context"], run.policy.rank))
        if len(public.query_ids) != 131 or len(public.genes) != 7226:
            raise ValueError("Changed eligible query/gene panel")
        episodes[str(episode)] = file_hash(episode / "manifest.json")
    expected = {
        (seed, context, rank)
        for seed in (20261023, 20261024)
        for context in ("K562", "RPE1")
        for rank in (4, 16)
    }
    if combinations != expected or len(episodes) != 4:
        raise ValueError("Incomplete split/direction/rank crossing")
    evidence = {
        name: file_hash(Path(name))
        for name in config.evidence_files
        if Path(name).resolve() != args.output.resolve()
    }
    snapshot = snapshot_sources(args.output.with_suffix(".zip"), environment["source_hashes"])
    write_json(
        args.output,
        {
            "state": "declared_before_robustness_acquisition",
            "recorded_at": utc_now(),
            "analysis_source_sha256": file_hash(Path(__file__)),
            "configuration_file_sha256": file_hash(args.config),
            "configuration_sha256": object_hash(asdict(config)),
            "evidence_sha256": evidence,
            "episode_manifests_sha256": episodes,
            "environment": environment,
            "resources": resource_record(Path(config.output_directory).parent),
            "code_snapshot": snapshot,
            "run_count": 8,
            "checkpoints": 360,
            "paid_policy_seed_ledgers": 72,
            "query_metric_rows": 330120,
            "qualification": (
                "Post-primary robustness on reused released cells/targets. New splits/ranks/"
                "budgets are not untouched confirmation or biological replication. "
                "Every matrix cell retained; no outcome-dependent selection."
            ),
        },
    )
    print("Frozen eight-run/360-checkpoint post-primary robustness declaration", flush=True)


if __name__ == "__main__":
    main()
