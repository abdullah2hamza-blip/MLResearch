"""Paired frozen-error analysis with shared-control and qualified resampling scopes."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from mlresearch.acquisition import CONTROL
from mlresearch.episodes import load_prepared, load_public_episode
from mlresearch.provenance import file_hash, read_json, write_json


def area_weights(budgets: list[int]) -> np.ndarray:
    x = np.asarray(budgets, dtype=float)
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all() or np.any(np.diff(x) <= 0):
        raise ValueError("Need increasing common budgets")
    weights = np.zeros(len(x))
    weights[:-1] += np.diff(x) / 2
    weights[1:] += np.diff(x) / 2
    return weights / (x[-1] - x[0])


def _band(values: np.ndarray, point: float) -> dict[str, float]:
    lo, hi = np.quantile(values, [0.025, 0.975])
    return {
        "point": float(point),
        "percentile_low": float(lo),
        "percentile_high": float(hi),
        "resampling_standard_deviation": float(values.std(ddof=1)),
    }


def _sample_mean(
    values: np.ndarray, rng: np.random.Generator, samples: int, strata: list[str] | None = None
) -> tuple[np.ndarray, dict[str, int]]:
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("Finite one-dimensional projections with at least two cells required")
    if strata is None:
        strata = ["all"] * len(values)
    if len(strata) != len(values):
        raise ValueError("Stratum axis mismatch")
    groups: dict[str, list[int]] = defaultdict(list)
    for row, label in enumerate(strata):
        groups[label].append(row)
    result = np.zeros(samples)
    singletons = 0
    for indices in groups.values():
        n = len(indices)
        draws = rng.multinomial(n, np.full(n, 1 / n), size=samples)
        result += draws @ values[indices] / len(values)
        singletons += n == 1
    return result, {
        "strata": len(groups),
        "singleton_strata": singletons,
        "cells_in_singleton_strata": singletons,
        "cells": len(values),
    }


def projected_summary(
    constants: np.ndarray,
    treatments: list[np.ndarray],
    controls: np.ndarray,
    *,
    seed: int = 20261022,
    samples: int = 2000,
    treatment_strata: list[list[str]] | None = None,
    control_strata: list[str] | None = None,
    treatment_batches: list[list[str]] | None = None,
    control_batches: list[str] | None = None,
) -> dict[str, Any]:
    if constants.ndim != 1:
        raise ValueError("Constants must have one query axis")
    q = len(constants)
    if q < 2 or len(treatments) != q or controls.ndim != 2 or controls.shape[1] != q:
        raise ValueError("Query axes disagree or fewer than two queries")
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 200:
        raise ValueError("Need at least 200 resampling draws")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("Resampling seed must be a nonnegative integer")
    if len(controls) < 2 or any(
        t.ndim != 1 or len(t) < 2 or not np.isfinite(t).all() for t in treatments
    ):
        raise ValueError("Each query and control projection needs at least two finite cells")
    if (treatment_strata is None) != (control_strata is None):
        raise ValueError("Declare both treatment and control strata")
    if treatment_strata is not None and len(treatment_strata) != q:
        raise ValueError("Treatment stratum query axis mismatch")
    if (treatment_batches is None) != (control_batches is None):
        raise ValueError("Declare both treatment and control batches")
    if not np.isfinite(constants).all() or not np.isfinite(controls).all():
        raise ValueError("Nonfinite projected values")
    means = np.asarray([t.mean() for t in treatments])
    differences = constants - 2 * means + 2 * controls.mean(axis=0)
    point = float(differences.mean())
    control_profile = controls.mean(axis=1)
    rng = np.random.default_rng(seed)
    query = differences[rng.integers(q, size=(samples, q))].mean(axis=1)
    result: dict[str, Any] = {
        "paired_difference": point,
        "queries": q,
        "samples": samples,
        "seed": seed,
        "query_bootstrap_conditional_on_bank": _band(query, point),
        "per_query_differences": differences.tolist(),
    }
    for name, strata_t, strata_c in (
        ("iid_cell_bootstrap_fixed_queries", None, None),
        ("stratified_cell_bootstrap_fixed_queries", treatment_strata, control_strata),
    ):
        if name.startswith("stratified") and (strata_t is None or strata_c is None):
            continue
        sampled_control, c_info = _sample_mean(control_profile, rng, samples, strata_c)
        values = np.full(samples, constants.mean()) + 2 * sampled_control
        treatment_info = []
        for i, treatment in enumerate(treatments):
            draw, info = _sample_mean(
                treatment, rng, samples, None if strata_t is None else strata_t[i]
            )
            values -= 2 * draw / q
            treatment_info.append(info)
        result[name] = {
            **_band(values, point),
            "control_strata": c_info,
            "treatment_strata": treatment_info,
            "shared_control_resample_reused_for_all_queries": True,
        }
    treatment_variance = 4 * sum(t.var(ddof=1) / len(t) for t in treatments) / q**2
    control_variance = 4 * control_profile.var(ddof=1) / len(control_profile)
    result["iid_measurement_variance_check"] = {
        "treatment_component": float(treatment_variance),
        "shared_control_component": float(control_variance),
        "standard_error": float(np.sqrt(treatment_variance + control_variance)),
        "qualification": (
            "Plug-in IID variance conditional on fixed predictions and query identities"
        ),
    }
    if treatment_batches is not None and control_batches is not None:
        if len(treatment_batches) != q or len(control_batches) != len(controls):
            raise ValueError("Batch axes disagree")
        labels = set(control_batches)
        for values, batches in zip(treatments, treatment_batches, strict=True):
            if len(values) != len(batches):
                raise ValueError("Treatment batch axis mismatch")
            labels.update(batches)
        missing_batch = any(
            str(label).strip().lower() in ("", "nan", "none", "null") for label in labels
        )
        if missing_batch or len(labels) < 2:
            result["batch_reweighting_sensitivity"] = {
                "available": False,
                "reason": "Missing batch labels or fewer than two observed batches",
            }
        else:
            ordered = sorted(labels)
            positions = {label: i for i, label in enumerate(ordered)}
            weights = rng.exponential(size=(samples, len(ordered)))

            def weighted_mean(values: np.ndarray, batches: list[str]) -> np.ndarray:
                indices = [positions[label] for label in batches]
                counts = np.bincount(indices, minlength=len(ordered))
                sums = np.bincount(indices, weights=values, minlength=len(ordered))
                return (weights @ sums) / (weights @ counts)

            values = np.full(samples, constants.mean())
            values += 2 * weighted_mean(control_profile, control_batches)
            for treatment, batches in zip(treatments, treatment_batches, strict=True):
                values -= 2 * weighted_mean(treatment, batches) / q
            result["batch_reweighting_sensitivity"] = {
                "available": True,
                **_band(values, point),
                "observed_technical_batches": len(ordered),
                "shared_batch_weights_reused": True,
                "qualification": (
                    "Positive batch-weight sensitivity, not a biological confidence interval"
                ),
            }
    return result


def analyze_run(
    run: Path,
    output: Path,
    *,
    policy: str = "bias_aware",
    reference: str = "worst_query",
    backbone: str = "ridge_cv",
    samples: int = 2000,
    seed: int = 20261022,
) -> dict[str, Any]:
    if output.exists():
        raise ValueError("Analysis output exists")
    if policy == reference:
        raise ValueError("Comparison requires distinct policies")
    manifest = read_json(run / "manifest.json")
    if manifest["state"] != "complete":
        raise ValueError("Only frozen completed runs can be analyzed")
    if {policy, reference} - set(manifest["configuration"]["policies"]):
        raise ValueError("Requested policies were not run")
    index_path = run / "prediction-index.json"
    if file_hash(index_path) != manifest["predictions_sha256"]:
        raise ValueError("Prediction index changed")
    access = read_json(run / "assessment-access.json")
    if access["prediction_index_sha256_before_opening"] != manifest["predictions_sha256"]:
        raise ValueError("Assessment access does not match frozen predictions")
    episode = Path(manifest["configuration"]["episode_directory"])
    if file_hash(episode / "manifest.json") != manifest["episode_manifest_sha256"]:
        raise ValueError("Episode changed")
    public = load_public_episode(episode)
    banks = read_json(episode / "private-banks.json")
    prepared = Path(banks["target_prepared"])
    if not prepared.is_absolute():
        prepared = episode / prepared
    metadata, matrix, prepared_manifest = load_prepared(prepared)
    if prepared_manifest != read_json(episode / "manifest.json")["prepared_inputs"]["target"]:
        raise ValueError("Prepared input changed")
    budgets = manifest["configuration"]["budgets"]
    seeds = manifest["configuration"]["seeds"]
    weights = area_weights(budgets)
    items = read_json(index_path)
    index = {(item["policy"], item["seed"], item["budget"]): item for item in items}
    expected = {
        (name, acquisition_seed, budget)
        for name in manifest["configuration"]["policies"]
        for acquisition_seed in seeds
        for budget in budgets
    }
    if len(index) != len(items) or set(index) != expected:
        raise ValueError("Prediction index does not cover every declared checkpoint once")
    coefficients = np.zeros((len(public.query_ids), len(public.genes)))
    constants = np.zeros(len(public.query_ids))
    for b, weight in zip(budgets, weights, strict=True):
        for acquisition_seed in seeds:
            predictions = []
            for name in (policy, reference):
                item = index[(name, acquisition_seed, b)]
                path = run / item["artifact"]
                if file_hash(path) != item["sha256"]:
                    raise ValueError("Prediction artifact changed")
                with np.load(path, allow_pickle=False) as arrays:
                    if backbone not in arrays:
                        raise ValueError("Requested backbone was not run")
                    predictions.append(np.asarray(arrays[backbone], dtype=float))
            a, b_pred = predictions
            coefficients += weight * (a - b_pred) / len(seeds)
            constants += weight * np.mean(a * a - b_pred * b_pred, axis=1) / len(seeds)
    columns = banks["target_columns"]
    treatments, t_strata, t_batches = [], [], []

    def labels(rows: list[int]) -> tuple[list[str], list[str]]:
        batches = [metadata["batches"][row] for row in rows]
        strata = [json.dumps([metadata["batches"][row], metadata["guides"][row]]) for row in rows]
        return strata, batches

    for i, identity in enumerate(public.query_ids):
        rows = banks["assessment_rows"][identity]
        if banks["assessment_cell_ids"][identity] != access["query_cell_ids"][identity]:
            raise ValueError("Query assessment cells changed")
        block = np.asarray(matrix[np.ix_(rows, columns)], dtype=float)
        treatments.append(block @ coefficients[i] / len(public.genes))
        strata, batches = labels(rows)
        t_strata.append(strata)
        t_batches.append(batches)
    control_rows = banks["assessment_rows"][CONTROL]
    if banks["assessment_cell_ids"][CONTROL] != access["control_cell_ids"]:
        raise ValueError("Control assessment cells changed")
    controls = np.empty((len(control_rows), len(public.query_ids)))
    for start in range(0, len(control_rows), 32):
        rows = control_rows[start : start + 32]
        block = np.asarray(matrix[np.ix_(rows, columns)], dtype=float)
        controls[start : start + len(rows)] = block @ coefficients.T / len(public.genes)
    c_strata, c_batches = labels(control_rows)
    result = projected_summary(
        constants,
        treatments,
        controls,
        seed=seed,
        samples=samples,
        treatment_strata=t_strata,
        control_strata=c_strata,
        treatment_batches=t_batches,
        control_batches=c_batches,
    )
    metric_file = run / "metrics.csv"
    if file_hash(metric_file) != manifest["results_sha256"]:
        raise ValueError("Metric file changed")
    differences: dict[tuple[str, int], dict[int, float]] = defaultdict(dict)
    with metric_file.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["backbone"] == backbone and row["policy"] in (policy, reference):
                key = (row["query"], int(row["seed"]))
                budget = int(row["budget"])
                differences[key][budget] = differences[key].get(budget, 0) + (
                    1 if row["policy"] == policy else -1
                ) * float(row["mse"])
    metric_point = np.mean(
        [weights @ [values[b] for b in budgets] for values in differences.values()]
    )
    if not np.isclose(result["paired_difference"], metric_point, atol=1e-12, rtol=1e-10):
        raise ValueError("Projected analysis disagrees with original paired error area")
    result.update(
        policy=policy,
        reference=reference,
        backbone=backbone,
        original_metric_paired_difference=float(metric_point),
        run_manifest_sha256=file_hash(run / "manifest.json"),
        prediction_index_sha256=manifest["predictions_sha256"],
        analysis_source_sha256=file_hash(Path(__file__)),
        qualification=(
            "Separate conditional query and measurement uncertainty. "
            "No biological replication, source-error or adaptive-selection coverage claim."
        ),
    )
    write_json(output, result)
    return result
