"""Stream authenticated external metrics into prespecified diagnostic supplements."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

from mlresearch.experiment import _write_csv
from mlresearch.external import validate_joint_freeze
from mlresearch.models import BACKBONES, BASE_BACKBONES
from mlresearch.provenance import file_hash, read_json, utc_now, write_json
from mlresearch.uncertainty import area_weights


def analyze(
    run: Path, seed: int, samples: int
) -> tuple[dict, list[dict], list[dict], list[dict], list[dict]]:
    manifest = read_json(run / "manifest.json")
    if (
        manifest["state"] != "complete"
        or file_hash(run / "metrics.csv") != manifest["results_sha256"]
    ):
        raise ValueError("Only complete authenticated metrics may be analyzed")
    cfg = manifest["configuration"]
    episode = Path(cfg["episode_directory"])
    if file_hash(episode / "manifest.json") != manifest["episode_manifest_sha256"]:
        raise ValueError("Episode manifest changed")
    epi = read_json(episode / "manifest.json")
    if file_hash(episode / "public.json") != epi["sha256"]["public.json"]:
        raise ValueError("Public metadata changed")
    queries = read_json(episode / "public.json")["query_ids"]
    backbones = BACKBONES if cfg["transfer"] is not None else BASE_BACKBONES
    grouped = defaultdict(lambda: np.zeros(6))
    strata = defaultdict(lambda: np.zeros(4))
    support = defaultdict(lambda: np.zeros(7))
    intervals = defaultdict(lambda: np.zeros(4))
    trajectories = defaultdict(dict)
    rows = 0
    with (run / "metrics.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            p, b, n, q, s = (
                row["policy"],
                row["backbone"],
                int(row["budget"]),
                row["query"],
                int(row["seed"]),
            )
            if (
                p not in cfg["policies"]
                or b not in backbones
                or n not in cfg["budgets"]
                or q not in queries
                or s not in cfg["seeds"]
            ):
                raise ValueError("Metric row outside declared axes")
            mse, specific, noise = (
                float(row["mse"]),
                float(row["specificity_mse"]),
                float(row["assessment_noise_floor"]),
            )
            if not np.isfinite([mse, specific, noise]).all():
                raise ValueError("Nonfinite metric")
            grouped[p, b, n] += np.array(
                [
                    mse,
                    specific,
                    noise,
                    float(row["spent"]),
                    float(row["recipient_measurements_used_cost"]),
                    1,
                ]
            )
            strata[p, b, n, row["source_stratum"]] += np.array([mse, specific, noise, 1])
            if b == cfg["primary_backbone"]:
                key = p, s, q
                if n in trajectories[key]:
                    raise ValueError("Duplicate primary checkpoint/query")
                trajectories[key][n] = mse
                support[p, n] += np.array(
                    [
                        row["identified"] == "True",
                        row["source_unstable"] == "True",
                        row["deferral_recommended"] == "True",
                        row["source_half_support_disagreement"] == "True",
                        row["source_half_identified_both"] == "True",
                        float(row["source_half_max_prediction_shift_mse"] or 0),
                        1,
                    ]
                )
            if b == "ridge":
                intervals[p, n][3] += 1
                if row["gaussian_coverage_diagnostic"]:
                    intervals[p, n][:3] += np.array(
                        [
                            float(row["gaussian_coverage_diagnostic"]),
                            float(row["gaussian_mean_width_diagnostic"]),
                            1,
                        ]
                    )
            rows += 1
    expected = {(p, b, n) for p in cfg["policies"] for b in backbones for n in cfg["budgets"]}
    if set(grouped) != expected or any(
        v[-1] != len(queries) * len(cfg["seeds"]) for v in grouped.values()
    ):
        raise ValueError("Incomplete policy/backbone/budget/query/seed grid")
    if set(trajectories) != {
        (p, s, q) for p in cfg["policies"] for s in cfg["seeds"] for q in queries
    }:
        raise ValueError("Primary query pairing incomplete")
    weights = area_weights(cfg["budgets"])
    query_areas = {}
    for p in cfg["policies"]:
        means = []
        for q in queries:
            values = []
            for s in cfg["seeds"]:
                trajectory = trajectories[p, s, q]
                if set(trajectory) != set(cfg["budgets"]):
                    raise ValueError("Missing primary budget")
                values.append(float(weights @ [trajectory[n] for n in cfg["budgets"]]))
            means.append(float(np.mean(values)))
        query_areas[p] = np.asarray(means)
    rng = np.random.default_rng(seed)
    indices = rng.integers(len(queries), size=(samples, len(queries)))
    comparisons = []
    for p in cfg["policies"]:
        for reference in ("worst_query", "mean_query"):
            if reference not in cfg["policies"]:
                continue
            delta = query_areas[p] - query_areas[reference]
            band = np.quantile(delta[indices].mean(axis=1), [0.025, 0.975])
            comparisons.append(
                {
                    "run": run.name,
                    "source_control": cfg["source_control"],
                    "policy": p,
                    "reference": reference,
                    "backbone": cfg["primary_backbone"],
                    "mean_area": float(query_areas[p].mean()),
                    "paired_difference": float(delta.mean()),
                    "relative_change": float(delta.mean() / query_areas[reference].mean())
                    if query_areas[reference].mean()
                    else None,
                    "conditional_low": float(band[0]),
                    "conditional_high": float(band[1]),
                    "queries": len(queries),
                    "seeds": len(cfg["seeds"]),
                }
            )
    curves = []
    for (p, b, n), v in sorted(grouped.items()):
        mean = v[:-1] / v[-1]
        curves.append(
            {
                "run": run.name,
                "source_control": cfg["source_control"],
                "policy": p,
                "backbone": b,
                "budget": n,
                "mse": float(mean[0]),
                "specificity_mse": float(mean[1]),
                "assessment_noise_floor": float(mean[2]),
                "noise_subtracted_mse": float(mean[0] - mean[2]),
                "mean_spent": float(mean[3]),
                "predictor_used_cost": float(mean[4]),
                "query_seed_predictions": int(v[-1]),
            }
        )
    stratum_rows = [
        {
            "run": run.name,
            "policy": p,
            "backbone": b,
            "budget": n,
            "public_source_stratum": label,
            "mse": float(v[0] / v[-1]),
            "specificity_mse": float(v[1] / v[-1]),
            "assessment_noise_floor": float(v[2] / v[-1]),
            "query_seed_predictions": int(v[-1]),
        }
        for (p, b, n, label), v in sorted(strata.items())
    ]
    diagnostics = []
    for (p, n), v in sorted(support.items()):
        interval = intervals[p, n]
        diagnostics.append(
            {
                "run": run.name,
                "policy": p,
                "budget": n,
                "primary_backbone": cfg["primary_backbone"],
                "query_seed_predictions": int(v[-1]),
                "identified": int(v[0]),
                "source_unstable": int(v[1]),
                "deferral_recommended": int(v[2]),
                "source_half_support_disagreements": int(v[3]),
                "source_half_identified_both": int(v[4]),
                "mean_source_half_shift_mse": float(v[5] / v[-1]),
                "fixed_ridge_total_predictions": int(interval[3]),
                "fixed_ridge_finite_intervals": int(interval[2]),
                "fixed_ridge_noisy_contrast_compatibility": float(interval[0] / interval[2])
                if interval[2]
                else None,
                "fixed_ridge_mean_width": float(interval[1] / interval[2]) if interval[2] else None,
            }
        )
    areas = []
    for p in cfg["policies"]:
        for b in backbones:
            area = sum(
                float(w) * grouped[p, b, n][0] / grouped[p, b, n][-1]
                for w, n in zip(weights, cfg["budgets"], strict=True)
            )
            specific_area = sum(
                float(w) * grouped[p, b, n][1] / grouped[p, b, n][-1]
                for w, n in zip(weights, cfg["budgets"], strict=True)
            )
            areas.append(
                {"policy": p, "backbone": b, "mse_area": area, "specificity_area": specific_area}
            )
    details = {
        "run": run.name,
        "run_directory": str(run),
        "run_manifest_sha256": file_hash(run / "manifest.json"),
        "configuration_sha256": manifest["configuration_sha256"],
        "source_control": cfg["source_control"],
        "source_context": epi["configuration"]["source_context"],
        "target_context": epi["configuration"]["target_context"],
        "metric_rows": rows,
        "areas": areas,
        "runtime_seconds": manifest["runtime_seconds"],
        "acquisition_runtime_seconds": manifest["acquisition_runtime_seconds"],
        "scoring_runtime_seconds": manifest["scoring_runtime_seconds"],
        "resources_end": manifest["resources_end"],
        "source_coordinates": manifest["source_coordinates"],
        "scorer_only_cells": manifest["scorer_only_assessment_cells"],
        "public_source_cells": manifest["fixed_public_source_cells"],
        "development_cost": manifest["fixed_development_resources"]["unique_resource_cost_units"],
    }
    return details, curves, stratum_rows, diagnostics, comparisons


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--samples", type=int, default=2000)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Supplement output exists")
    suite = read_json(args.suite / "manifest.json")
    if suite["state"] != "complete":
        raise ValueError("Complete the frozen suite before analysis")
    if args.samples < 200 or args.seed < 0:
        raise ValueError("Invalid descriptive bootstrap settings")
    freeze = validate_joint_freeze(args.suite / "joint-prediction-freeze.json")
    records = []
    curves = []
    strata = []
    diagnostics = []
    comparisons = []
    for entry in freeze["runs"]:
        detail, c, s, d, p = analyze(Path(entry["run_directory"]), args.seed, args.samples)
        records.append(detail)
        curves.extend(c)
        strata.extend(s)
        diagnostics.extend(d)
        comparisons.extend(p)
    args.output.mkdir(parents=True)
    for name, rows in [
        ("curves-and-specificity.csv", curves),
        ("public-source-strata.csv", strata),
        ("support-source-and-interval-diagnostics.csv", diagnostics),
        ("paired-primary-comparisons.csv", comparisons),
    ]:
        _write_csv(args.output / name, rows)
    write_json(
        args.output / "summary.json",
        {
            "analysis_source_sha256": file_hash(Path(__file__)),
            "analyzed_at": utc_now(),
            "suite_manifest_sha256": file_hash(args.suite / "manifest.json"),
            "bootstrap_samples": args.samples,
            "bootstrap_seed": args.seed,
            "runs": records,
            "qualifications": [
                "Queries averaged over acquisition seeds before paired descriptive bootstrap.",
                "Directions reuse observations and are not independent biological replications.",
                "Gaussian fields measure noisy-contrast compatibility, not population coverage.",
                "Source-half support and instability/deferral flags are uncalibrated diagnostics.",
                "Weak/strong strata use permitted public sources, including deliberate corruption.",
            ],
        },
    )
    print(
        "Analyzed",
        len(records),
        "frozen runs and",
        sum(r["metric_rows"] for r in records),
        "metric rows",
    )


if __name__ == "__main__":
    main()
