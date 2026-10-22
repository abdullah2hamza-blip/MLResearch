"""Actual within-gene perturbation ranks, distinct from absolute or centered MSE."""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import time
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

from mlresearch.episodes import load_prepared, load_public_episode
from mlresearch.experiment import _assessment, _write_csv
from mlresearch.models import BACKBONES
from mlresearch.provenance import (
    environment_record,
    file_hash,
    read_json,
    resource_record,
    utc_now,
    write_json,
)


def unit_ranks(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if values.ndim != 2 or 0 in values.shape or not np.isfinite(values).all():
        raise ValueError("Ranking requires a finite nonempty query-by-gene matrix")
    ranks = rankdata(values, axis=0, method="average")
    ranks -= ranks.mean(axis=0)
    norms = np.linalg.norm(ranks, axis=0)
    valid = norms > 0
    return np.divide(ranks, norms, out=np.zeros_like(ranks), where=valid), valid


def rank_scores(prediction: np.ndarray, truth: np.ndarray, permutation: np.ndarray) -> dict:
    return scores_from_ranks(*unit_ranks(prediction), *unit_ranks(truth), permutation)


def scores_from_ranks(p, p_valid, t, t_valid, permutation) -> dict:
    result = {
        "declared_genes": p.shape[1],
        "target_nonconstant_genes": int(t_valid.sum()),
        "prediction_nonconstant_genes": int(p_valid.sum()),
    }
    for label, values, valid in (
        ("original", p, p_valid),
        ("scoring_gene_permutation", p[:, permutation], p_valid[permutation]),
    ):
        usable = valid & t_valid
        correlations = np.clip(np.sum(values[:, usable] * t[:, usable], axis=0), -1, 1)
        result[label + "_defined_genes"] = int(usable.sum())
        result[label + "_mean_defined_spearman"] = (
            float(correlations.mean()) if usable.any() else None
        )
        result[label + "_fixed_gene_score"] = float(correlations.sum() / p.shape[1])
    return result


def target(run: Path, scope: str):
    manifest = read_json(run / "manifest.json")
    episode = Path(manifest["configuration"]["episode_directory"])
    if file_hash(episode / "manifest.json") != manifest["episode_manifest_sha256"]:
        raise ValueError("Episode changed before ranking")
    public = load_public_episode(episode)
    if scope == "controlled_truth":
        path = run.parent / "data" / "generative-truth.npz"
        if file_hash(path) != read_json(run / "truth-access.json")["truth_sha256"]:
            raise ValueError("Simulation truth changed")
        with np.load(path, allow_pickle=False) as arrays:
            identities = arrays["intervention_ids"].astype(str).tolist()
            genes = arrays["gene_ids"].astype(str).tolist()
            truth = arrays["target_effects"][
                np.ix_(
                    [identities.index(q) for q in public.query_ids],
                    [genes.index(g) for g in public.genes],
                )
            ]
    else:
        banks = read_json(episode / "private-banks.json")
        prepared = Path(banks["target_prepared"])
        if not prepared.is_absolute():
            prepared = episode / prepared
        _, matrix, prep = load_prepared(prepared)
        if prep != read_json(episode / "manifest.json")["prepared_inputs"]["target"]:
            raise ValueError("Prepared recipient changed before ranking")
        truth, _, _ = _assessment(matrix, banks, public.query_ids)
        with np.load(run / "assessment.npz", allow_pickle=False) as arrays:
            np.testing.assert_array_equal(truth, arrays["effects"])
    return public, truth


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    started, cpu_started = time.perf_counter(), time.process_time()
    source_sha = file_hash(Path(__file__))
    source = read_json(args.diagnostics / "summary.json")
    if source["state"] != "complete" or source["controlled_world_filter"] is not None:
        raise ValueError("Use the complete unfiltered secondary diagnostic suite")
    environment, resources = environment_record(), resource_record(args.output.parent)
    declaration = {
        "source_sha256": source_sha,
        "diagnostic_summary_sha256": file_hash(args.diagnostics / "summary.json"),
        "coordinate_metrics_sha256": file_hash(
            args.diagnostics / "coordinate-and-interval-diagnostics.csv"
        ),
    }
    if args.output.exists():
        if not args.resume or read_json(args.output / "declaration.json") != declaration:
            raise ValueError("Ranking output exists or resume source/input differs")
    else:
        args.output.mkdir(parents=True)
        write_json(args.output / "declaration.json", declaration)
        shutil.copyfile(Path(__file__), args.output / "analysis-source.py")
    expected = {}
    with (args.diagnostics / "coordinate-and-interval-diagnostics.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = tuple(
                row[k]
                for k in (
                    "scope",
                    "scenario",
                    "generative_seed",
                    "run",
                    "policy",
                    "seed",
                    "budget",
                    "backbone",
                )
            )
            if key in expected:
                raise ValueError("Duplicate reference coordinate row")
            expected[key] = float(row["mse"])
    shards, records = [], []
    for number, binding in enumerate(source["runs"]):
        run = Path(binding["run_directory"])
        if file_hash(run / "manifest.json") != binding["run_manifest_sha256"]:
            raise ValueError("Run changed before ranking")
        receipt = args.output / f"run-{number}.json"
        if receipt.exists():
            record = read_json(receipt)
            shard = args.output / record["shard"]
            if file_hash(shard) != record["sha256"] or record["input"] != binding:
                raise ValueError("Completed ranking shard changed")
            print("Reusing ranking shard", number, flush=True)
        else:
            attempt = 0
            shard = args.output / f"run-{number}-attempt-{attempt}.csv"
            while shard.exists():
                attempt += 1
                shard = args.output / f"run-{number}-attempt-{attempt}.csv"
            public, truth = target(run, binding["scope"])
            t, valid_t = unit_ranks(truth)
            permutation = np.random.default_rng(20261022).permutation(len(public.genes))
            manifest = read_json(run / "manifest.json")
            if file_hash(run / "prediction-index.json") != manifest["predictions_sha256"]:
                raise ValueError("Prediction index changed")
            prefix = {k: binding[k] for k in ("scope", "scenario", "generative_seed", "run")}
            cache = {}
            count = [0]

            def rows(
                run=run,
                truth=truth,
                binding=binding,
                cache=cache,
                t=t,
                valid_t=valid_t,
                permutation=permutation,
                count=count,
                prefix=prefix,
            ):
                for item in read_json(run / "prediction-index.json"):
                    path = run / item["artifact"]
                    if file_hash(path) != item["sha256"]:
                        raise ValueError("Prediction checkpoint changed")
                    with np.load(path, allow_pickle=False) as arrays:
                        for backbone in BACKBONES:
                            if backbone not in arrays:
                                continue
                            p = arrays[backbone]
                            if p.shape != truth.shape:
                                raise ValueError("Ranking axes differ")
                            key = tuple(
                                str(v) if v is not None else ""
                                for v in (
                                    binding["scope"],
                                    binding["scenario"],
                                    binding["generative_seed"],
                                    binding["run"],
                                    item["policy"],
                                    item["seed"],
                                    item["budget"],
                                    backbone,
                                )
                            )
                            mse = float(np.mean((p.astype(np.float64) - truth) ** 2))
                            if key not in expected or not np.isclose(
                                mse, expected[key], atol=1e-12, rtol=1e-10
                            ):
                                raise ValueError(
                                    "Ranking truth/order differs from authenticated errors"
                                )
                            fingerprint = hashlib.sha256(
                                p.dtype.str.encode() + p.tobytes()
                            ).hexdigest()
                            if fingerprint not in cache:
                                cache[fingerprint] = scores_from_ranks(
                                    *unit_ranks(p), t, valid_t, permutation
                                )
                            count[0] += 1
                            yield {
                                **prefix,
                                "policy": item["policy"],
                                "seed": item["seed"],
                                "budget": item["budget"],
                                "backbone": backbone,
                                **cache[fingerprint],
                            }

            _write_csv(shard, rows())
            record = {
                "input": binding,
                "shard": shard.name,
                "sha256": file_hash(shard),
                "rows": count[0],
            }
            write_json(receipt, record)
            print("Completed ranking", number + 1, "/", len(source["runs"]), run, flush=True)
        shards.append(shard)
        records.append(record)
    if file_hash(Path(__file__)) != source_sha:
        raise ValueError("Ranking analysis source changed during execution")
    if sum(r["rows"] for r in records) != len(expected):
        raise ValueError("Ranking does not cover every original coordinate checkpoint")
    complete = args.output / "summary.json"
    if complete.exists():
        previous = read_json(complete)
        if (
            file_hash(args.output / "within-gene-perturbation-ranking.csv")
            != previous["ranking_csv_sha256"]
        ):
            raise ValueError("Completed ranking output changed")
        print("Ranking already complete; authenticated shards reused", flush=True)
        return

    def combined():
        for path in shards:
            with path.open(encoding="utf-8", newline="") as stream:
                yield from csv.DictReader(stream)

    _write_csv(args.output / "within-gene-perturbation-ranking.csv", combined())
    write_json(
        args.output / "summary.json",
        {
            **declaration,
            "state": "complete",
            "recorded_at": utc_now(),
            "run_count": len(records),
            "rows": sum(r["rows"] for r in records),
            "ranking_csv_sha256": file_hash(args.output / "within-gene-perturbation-ranking.csv"),
            "shards": records,
            "environment": environment,
            "resources_start": resources,
            "resources_end": resource_record(args.output),
            "runtime_seconds_this_pass": time.perf_counter() - started,
            "process_cpu_seconds_this_pass": time.process_time() - cpu_started,
            "qualification": [
                "Spearman ranks perturbations within each gene, with average ties.",
                "Conditional correlations exclude constant genes and report their denominator.",
                "Fixed-gene score assigns undefined genes0 as an explicitly neutral aggregate; "
                "a constant-vector correlation remains undefined.",
                "Common gene shifts preserve ranks; ranks do not identify absolute effects.",
                "No gene significance, biological replication or new primary superiority claim.",
                "Scoring permutation seed20261022; predictions/acquisitions are never refitted.",
            ],
        },
    )


if __name__ == "__main__":
    main()
