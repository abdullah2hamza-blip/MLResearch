"""Post-primary sign, scoring-permutation, 90/95 interval and distance-retention checks."""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections import defaultdict
from dataclasses import fields
from pathlib import Path
from statistics import NormalDist

import numpy as np

from mlresearch.acquisition import CONTROL, verify_ledger
from mlresearch.controls import transform_source
from mlresearch.episodes import load_prepared, load_public_episode
from mlresearch.experiment import _assessment, _write_csv
from mlresearch.external import validate_joint_freeze
from mlresearch.models import BACKBONES, source_coordinates
from mlresearch.provenance import (
    environment_record,
    file_hash,
    read_json,
    resource_record,
    utc_now,
    write_json,
)
from mlresearch.report import risk_retention_rows


def cosine_rows(left: np.ndarray, right: np.ndarray) -> tuple[float | None, int]:
    denominator = np.linalg.norm(left, axis=1) * np.linalg.norm(right, axis=1)
    valid = denominator > 0
    if not valid.any():
        return None, 0
    values = np.sum(left[valid] * right[valid], axis=1) / denominator[valid]
    return float(values.mean()), int(valid.sum())


def nearest_distance(queries: np.ndarray, purchased: np.ndarray) -> np.ndarray:
    if len(purchased) == 0:
        return np.full(len(queries), np.inf)
    return np.mean((queries[:, None] - purchased[None, :]) ** 2, axis=2).min(axis=1)


def coordinate_metrics(prediction: np.ndarray, truth: np.ndarray, permutation: np.ndarray) -> dict:
    cosine, defined = cosine_rows(prediction, truth)
    specific, specific_defined = cosine_rows(
        prediction - prediction.mean(axis=0), truth - truth.mean(axis=0)
    )
    pearson, pearson_defined = cosine_rows(
        prediction - prediction.mean(axis=1, keepdims=True),
        truth - truth.mean(axis=1, keepdims=True),
    )
    return {
        "mse": float(np.mean((prediction - truth) ** 2)),
        "sign_agreement_including_explicit_zero_ties": float(
            np.mean(np.sign(prediction) == np.sign(truth))
        ),
        "prediction_nonzero_fraction": float(np.mean(prediction != 0)),
        "direction_cosine": cosine,
        "direction_cosine_defined_queries": defined,
        "response_specific_cosine": specific,
        "response_specific_cosine_defined_queries": specific_defined,
        "within_query_gene_pearson": pearson,
        "within_query_gene_pearson_defined_queries": pearson_defined,
        "scoring_gene_permuted_mse": float(np.mean((prediction[:, permutation] - truth) ** 2)),
    }


def interval_diagnostics(prediction, truth, ideal, noise, scope) -> dict:
    result = {}
    finite = np.isfinite(ideal)
    for level, z in ((90, NormalDist().inv_cdf(0.95)), (95, 1.96)):
        result[f"finite_queries_{level}"] = int(finite.sum())
        width = z * np.sqrt(ideal[:, None] + (noise if scope == "external_assessment" else 0))
        result[f"coverage_or_compatibility_{level}"] = (
            float(np.mean(np.abs(prediction[finite] - truth[finite]) <= width[finite]))
            if finite.any()
            else None
        )
        result[f"mean_width_{level}"] = float(np.mean(2 * width[finite])) if finite.any() else None
    return result


def process(
    run: Path,
    scope: str,
    scenario: str,
    world: int | None,
    retention: list,
    bindings: list,
    retention_only: bool = False,
):
    manifest = read_json(run / "manifest.json")
    if manifest["state"] != "complete":
        raise ValueError("Only complete frozen runs may be diagnosed")
    cfg = manifest["configuration"]
    index_path = run / "prediction-index.json"
    if file_hash(index_path) != manifest["predictions_sha256"]:
        raise ValueError("Prediction index changed")
    episode = Path(cfg["episode_directory"])
    if file_hash(episode / "manifest.json") != manifest["episode_manifest_sha256"]:
        raise ValueError("Episode changed")
    public = load_public_episode(episode)
    public, control = transform_source(public, cfg["source_control"], cfg["source_control_seed"])
    if control != manifest["source_control"]:
        raise ValueError("Source control changed")
    banks = read_json(episode / "private-banks.json")
    prepared = Path(banks["target_prepared"])
    if not prepared.is_absolute():
        prepared = episode / prepared
    _, matrix, prepared_manifest = load_prepared(prepared)
    if prepared_manifest != read_json(episode / "manifest.json")["prepared_inputs"]["target"]:
        raise ValueError("Prepared input changed")
    assessment, noise, _ = _assessment(matrix, banks, public.query_ids)
    with np.load(run / "assessment.npz", allow_pickle=False) as stored:
        np.testing.assert_array_equal(assessment, stored["effects"])
        np.testing.assert_array_equal(noise, stored["mean_noise_variance"])
    truth = assessment
    if scope == "controlled_truth":
        access = read_json(run / "truth-access.json")
        path = run.parent / "data" / "generative-truth.npz"
        if file_hash(path) != access["truth_sha256"]:
            raise ValueError("Oracle truth changed")
        with np.load(path, allow_pickle=False) as arrays:
            ordering, genes = arrays["intervention_ids"].tolist(), arrays["gene_ids"].tolist()
            truth = arrays["target_effects"][
                np.ix_(
                    [ordering.index(q) for q in public.query_ids],
                    [genes.index(g) for g in public.genes],
                )
            ]
    features = source_coordinates(public, cfg["policy"]["rank"]).features[:, 1:]
    q_features = features[[public.index(q) for q in public.query_ids]]
    permutation = np.random.default_rng(20261022).permutation(len(public.genes))
    risk, distances, ledgers = defaultdict(list), defaultdict(list), {}
    prefix = {"run": run.name, "scenario": scenario, "generative_seed": world, "scope": scope}
    if scope == "external_assessment":
        prefix["run"] = run.name
    for item in read_json(index_path):
        key = item["policy"], item["seed"]
        if key not in ledgers:
            events = [
                json.loads(s)
                for s in (run / f"seed-{key[1]}" / key[0] / "ledger.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            verify_ledger(
                events,
                budget=max(cfg["budgets"]),
                setup_cost=cfg["policy"]["setup_cost"],
                cell_cost=cfg["policy"]["cell_cost"],
                control_cell_cost=cfg["policy"]["control_cell_cost"],
                query_ids=public.query_ids,
            )
            ledgers[key] = events
        events = [e for e in ledgers[key] if e["spent"] <= item["spent"]]
        purchased = sorted({e["action"]["intervention"] for e in events} - {CONTROL})
        distance = nearest_distance(q_features, features[[public.index(q) for q in purchased]])
        artifact = run / item["artifact"]
        if file_hash(artifact) != item["sha256"]:
            raise ValueError("Prediction checkpoint changed")
        with np.load(artifact, allow_pickle=False) as arrays:
            ideal = arrays["ideal_variance"]
            for backbone in BACKBONES:
                if backbone not in arrays:
                    continue
                if retention_only and backbone != cfg["primary_backbone"]:
                    continue
                prediction = arrays[backbone].astype(np.float64)
                if not retention_only:
                    row = {
                        **prefix,
                        "policy": item["policy"],
                        "seed": item["seed"],
                        "budget": item["budget"],
                        "backbone": backbone,
                        **coordinate_metrics(prediction, truth, permutation),
                    }
                    row.update(
                        interval_diagnostics(prediction, truth, ideal, noise, scope)
                        if backbone == "ridge"
                        else {
                            f"{name}_{level}": None
                            for level in (90, 95)
                            for name in (
                                "finite_queries",
                                "coverage_or_compatibility",
                                "mean_width",
                            )
                        }
                    )
                    yield row
                if backbone == cfg["primary_backbone"]:
                    errors = np.mean((prediction - truth) ** 2, axis=1)
                    k = item["policy"], item["budget"]
                    risk[k].extend(
                        zip(
                            ideal.tolist(),
                            errors.tolist(),
                            arrays["source_unstable"].tolist(),
                            strict=True,
                        )
                    )
                    distances[k].extend(zip(distance.tolist(), errors.tolist(), strict=True))
    for (policy, budget), values in risk.items():
        retention.extend(
            {**prefix, **r}
            for r in risk_retention_rows(policy, budget, cfg["primary_backbone"], values)
        )
        d = distances[policy, budget]
        order = np.argsort([x[0] for x in d], kind="stable")
        for fraction in (0.25, 0.5, 0.75, 1.0):
            kept = max(1, int(len(d) * fraction))
            retention.append(
                {
                    **prefix,
                    "policy": policy,
                    "budget": budget,
                    "backbone": cfg["primary_backbone"],
                    "criterion": "distance_only",
                    "requested_retention": fraction,
                    "actual_retention": kept / len(d),
                    "retained_query_seed_observations": kept,
                    "total_query_seed_observations": len(d),
                    "mse": float(np.mean([d[i][1] for i in order[:kept]])),
                }
            )
    bindings.append(
        {
            **prefix,
            "run_directory": str(run),
            "run_manifest_sha256": file_hash(run / "manifest.json"),
            "checkpoints": len(read_json(index_path)),
            "queries": len(public.query_ids),
            "uniform_candidate_pool_cells": sorted(
                {len(v) for k, v in banks["acquisition_rows"].items() if k != CONTROL}
            ),
            "source_condition_counts": sorted(
                {v for k, v in banks["source_counts"].items() if k != CONTROL}
            ),
            "public_interface_fields": [f.name for f in fields(public)],
            "uncapped_counts_absent_from_public_interface": not any(
                f.name in ("condition_inventory", "raw_counts", "uncapped_counts")
                for f in fields(public)
            ),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-suite", type=Path, required=True)
    parser.add_argument("--controlled-study", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reuse-external-diagnostics", type=Path)
    parser.add_argument("--controlled-only", action="store_true")
    parser.add_argument("--controlled-worlds", type=int, nargs="+")
    args = parser.parse_args()
    started, cpu_started = time.perf_counter(), time.process_time()
    environment, resources_start = environment_record(), resource_record(args.output.parent)
    if args.output.exists():
        raise ValueError("Secondary diagnostics output exists")
    if read_json(args.external_suite / "manifest.json")["state"] != "complete":
        raise ValueError("Complete the primary suite first")
    freeze = validate_joint_freeze(args.external_suite / "joint-prediction-freeze.json")
    jobs = [
        (Path(e["run_directory"]), "external_assessment", "external", None) for e in freeze["runs"]
    ]
    if args.controlled_only:
        jobs = []
    if args.controlled_study:
        study = read_json(args.controlled_study / "manifest.json")
        if study["state"] != "complete":
            raise ValueError("Complete the controlled study first")
        for case in study["cases"]:
            if args.controlled_worlds and case["generative_seed"] not in args.controlled_worlds:
                continue
            run = Path(case["run"])
            if file_hash(run / "manifest.json") != case["manifest_sha256"]:
                raise ValueError("Controlled case changed")
            jobs.append((run, "controlled_truth", case["scenario"], case["generative_seed"]))
    args.output.mkdir(parents=True)
    retention, bindings = [], []

    reused = []
    if args.reuse_external_diagnostics:
        with args.reuse_external_diagnostics.open(encoding="utf-8", newline="") as stream:
            reused = list(csv.DictReader(stream))
        expected = defaultdict(lambda: np.zeros(4))
        for run, scope, _, _ in jobs:
            if scope != "external_assessment":
                continue
            current = read_json(run / "manifest.json")
            if file_hash(run / "metrics.csv") != current["results_sha256"]:
                raise ValueError("Original metrics changed before diagnostic recovery")
            with (run / "metrics.csv").open(encoding="utf-8", newline="") as stream:
                for r in csv.DictReader(stream):
                    k = run.name, r["policy"], int(r["seed"]), int(r["budget"]), r["backbone"]
                    expected[k] += (
                        float(r["mse"]),
                        1,
                        float(r["gaussian_coverage_diagnostic"] or 0),
                        bool(r["gaussian_coverage_diagnostic"]),
                    )
        seen = set()
        for r in reused:
            k = r["run"], r["policy"], int(r["seed"]), int(r["budget"]), r["backbone"]
            if k in seen or k not in expected or r["scope"] != "external_assessment":
                raise ValueError("Reused table has duplicate or undeclared checkpoints")
            seen.add(k)
            v = expected[k]
            if not np.isclose(float(r["mse"]), v[0] / v[1], atol=1e-12, rtol=1e-10):
                raise ValueError("Reused MSE differs from authenticated primary metrics")
            if (
                r["backbone"] == "ridge"
                and v[3]
                and not np.isclose(
                    float(r["coverage_or_compatibility_95"]), v[2] / v[3], atol=1e-12
                )
            ):
                raise ValueError("Reused95% compatibility differs from original scorer")
        if seen != set(expected):
            raise ValueError("External diagnostic recovery is incomplete")

    def rows():
        yield from reused
        for job in jobs:
            print("Frozen diagnostics", job[0], flush=True)
            yield from process(
                *job,
                retention,
                bindings,
                retention_only=bool(reused) and job[1] == "external_assessment",
            )

    _write_csv(args.output / "coordinate-and-interval-diagnostics.csv", rows())
    _write_csv(args.output / "distance-and-variance-retention.csv", retention)
    write_json(
        args.output / "summary.json",
        {
            "state": "complete",
            "recorded_at": utc_now(),
            "analysis_source_sha256": file_hash(Path(__file__)),
            "runs": bindings,
            "scoring_gene_permutation_seed": 20261022,
            "runtime_seconds": time.perf_counter() - started,
            "process_cpu_seconds": time.process_time() - cpu_started,
            "environment": environment,
            "resources_start": resources_start,
            "resources_end": resource_record(args.output),
            "reused_external_table": {
                "path": str(args.reuse_external_diagnostics),
                "sha256": file_hash(args.reuse_external_diagnostics),
                "rows": len(reused),
                "all_mse_and_legacy95_fields_match_original_authenticated_metrics": True,
            }
            if reused
            else None,
            "controlled_world_filter": args.controlled_worlds,
            "qualification": [
                "Post-primary secondary analyses, with no fitting or primary retuning.",
                "Real intervals describe noisy-contrast compatibility; "
                "controlled intervals use known truth.",
                "Numerical Gaussian fields are unvalidated after adaptation/model/source error.",
                "Sign zero ties and undefined cosine denominators are reported explicitly.",
                "Distance retention uses purchased identities and permitted source coordinates.",
                "Uniform capped counts do not remove count-selected-cohort/capture bias.",
            ],
        },
    )


if __name__ == "__main__":
    main()
