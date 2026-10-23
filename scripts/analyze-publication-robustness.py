"""Authenticate and retain the complete post-primary split/rank/budget robustness matrix."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import itertools
import json
import shutil
import time
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402

from mlresearch.acquisition import CONTROL, verify_ledger  # noqa: E402
from mlresearch.episodes import load_public_episode  # noqa: E402
from mlresearch.experiment import _write_csv, verify_frozen_predictions  # noqa: E402
from mlresearch.external import ExternalConfig, validate_joint_freeze  # noqa: E402
from mlresearch.models import BASE_BACKBONES  # noqa: E402
from mlresearch.provenance import (  # noqa: E402
    environment_record,
    file_hash,
    object_hash,
    read_json,
    resource_record,
    utc_now,
    write_json,
)
from mlresearch.uncertainty import area_weights  # noqa: E402

POLICIES = ("worst_query", "mean_query", "bias_aware")
GRIDS = {"original_grid": [128, 256, 512], "full_grid": [128, 256, 512, 1024, 2048]}


def pack(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as stream, destination.open("xb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, mtime=0) as output:
            shutil.copyfileobj(stream, output, length=1024 * 1024)
    digest = hashlib.sha256()
    with gzip.open(destination, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != file_hash(source):
        raise ValueError("Retained gzip does not reproduce original bytes")


def bind_episode(path: Path) -> dict:
    manifest = read_json(path / "manifest.json")
    public = load_public_episode(path)
    if file_hash(path / "private-banks.json") != manifest["sha256"]["private-banks.json"]:
        raise ValueError("Private bank mapping changed")
    banks = read_json(path / "private-banks.json")
    prepared = Path(banks["target_prepared"])
    if not prepared.is_absolute():
        prepared = path / prepared
    target = read_json(prepared / "manifest.json")
    if target != manifest["prepared_inputs"]["target"]:
        raise ValueError("Prepared target binding changed")
    if file_hash(prepared / "metadata.json") != target["metadata_sha256"]:
        raise ValueError("Prepared target metadata changed")
    metadata = read_json(prepared / "metadata.json")
    query_cells = set().union(*(set(banks["assessment_cell_ids"][q]) for q in public.query_ids))
    controls = set(banks["assessment_cell_ids"][CONTROL])
    all_assessment = set().union(*(set(v) for v in banks["assessment_cell_ids"].values()))
    acquisition = set().union(*(set(v) for v in banks["acquisition_cell_ids"].values()))
    if acquisition & all_assessment:
        raise ValueError("Within-episode acquisition/scorer bank overlap")
    sets = {
        "queries": set(public.query_ids),
        "calibrations": set(public.candidate_ids),
        "source_cells": set(banks["source_cell_ids"]),
        "target_acquisition_cells": acquisition,
        "query_assessment_cells": query_cells,
        "scorer_control_cells": controls,
        "all_assessment_cells": all_assessment,
        "target_retained_cells": set(metadata["cell_ids"]),
    }
    counts = {name: len(values) for name, values in sets.items()}
    counts["scorer_only_used_cells"] = len(query_cells | controls)
    counts["unused_reserved_query_cells"] = len(
        sets["target_retained_cells"] - acquisition - all_assessment
    )
    counts["unused_calibration_assessment_cells"] = len(all_assessment - query_cells - controls)
    counts["genes"] = len(public.genes)
    counts["source_condition_counts"] = sorted(set(banks["source_counts"].values()))
    counts["source_perturbation_condition_counts"] = sorted(
        {v for k, v in banks["source_counts"].items() if k != CONTROL}
    )
    counts["source_control_cells"] = banks["source_counts"][CONTROL]
    counts["acquisition_control_cells"] = len(banks["acquisition_cell_ids"][CONTROL])
    counts["assessment_control_cells"] = len(controls)
    return {
        "path": path,
        "manifest": manifest,
        "public": public,
        "banks": banks,
        "sets": sets,
        "record": {
            "episode": path.name,
            "split_seed": manifest["configuration"]["seed"],
            "source_context": manifest["configuration"]["source_context"],
            "target_context": manifest["configuration"]["target_context"],
            "manifest_sha256": file_hash(path / "manifest.json"),
            "public_sha256": file_hash(path / "public.json"),
            "private_banks_sha256": file_hash(path / "private-banks.json"),
            "counts": counts,
        },
    }


def overlap_rows(episodes: list[dict]) -> list[dict]:
    result = []
    for a, b in itertools.combinations(episodes, 2):
        row = {"episode_a": a["path"].name, "episode_b": b["path"].name}
        for side, episode in (("a", a), ("b", b)):
            for field in ("split_seed", "source_context", "target_context"):
                row[f"{field}_{side}"] = episode["record"][field]
        for name in a["sets"]:
            row[f"shared_{name}"] = len(a["sets"][name] & b["sets"][name])
        row["source_a_in_target_b"] = len(
            a["sets"]["source_cells"] & b["sets"]["target_retained_cells"]
        )
        row["source_b_in_target_a"] = len(
            b["sets"]["source_cells"] & a["sets"]["target_retained_cells"]
        )
        row["source_a_in_scorer_b"] = len(
            a["sets"]["source_cells"]
            & (b["sets"]["query_assessment_cells"] | b["sets"]["scorer_control_cells"])
        )
        row["source_b_in_scorer_a"] = len(
            b["sets"]["source_cells"]
            & (a["sets"]["query_assessment_cells"] | a["sets"]["scorer_control_cells"])
        )
        result.append(row)
    return result


def ledger_records(run: Path, cfg: dict, episode: dict) -> dict:
    result = {}
    banks = episode["banks"]
    allowed = {k: set(v) for k, v in banks["acquisition_cell_ids"].items()}
    forbidden = set().union(*(set(v) for v in banks["assessment_cell_ids"].values()))
    for seed in cfg["seeds"]:
        for policy in cfg["policies"]:
            path = run / f"seed-{seed}" / policy / "ledger.jsonl"
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            verify_ledger(
                events,
                budget=max(cfg["budgets"]),
                setup_cost=cfg["policy"]["setup_cost"],
                cell_cost=cfg["policy"]["cell_cost"],
                control_cell_cost=cfg["policy"]["control_cell_cost"],
                query_ids=episode["public"].query_ids,
            )
            for event in events:
                key, cells = event["action"]["intervention"], set(event["cell_ids"])
                if key not in allowed or cells - allowed[key] or cells & forbidden:
                    raise ValueError("Invalid or scorer-only cell purchase")
            result[policy, seed] = events
    return result


def retain_run(run: Path, root: Path, manifest: dict) -> dict:
    destination = root / "runs" / run.name
    destination.mkdir(parents=True)
    names = [
        "manifest.json",
        "prediction-index.json",
        "assessment-access.json",
        "source-control.json",
        "allocations.csv",
        "events.jsonl",
        "code.zip",
    ]
    for name in names:
        shutil.copyfile(run / name, destination / name)
    pack(run / "metrics.csv", destination / "metrics.csv.gz")
    members = {}
    with zipfile.ZipFile(
        destination / "paid-ledgers.zip", "x", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for path in sorted(run.glob("seed-*/*/ledger.jsonl")):
            member = path.relative_to(run).as_posix()
            archive.write(path, member)
            members[member] = file_hash(path)
    with zipfile.ZipFile(destination / "paid-ledgers.zip") as archive:
        for name, digest in members.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError("Retained ledger ZIP member changed")
    record = {
        "metrics_reinflated_sha256": manifest["results_sha256"],
        "ledger_member_sha256": members,
        "raw_expression_included": False,
        "prediction_arrays_included": False,
        "sha256": {p.name: file_hash(p) for p in sorted(destination.iterdir())},
    }
    write_json(destination / "retained-artifacts.json", record)
    return record


def analyze_run(run: Path, episode: dict, seed: int, samples: int) -> tuple:
    m = read_json(run / "manifest.json")
    cfg = m["configuration"]
    if m["state"] != "complete" or file_hash(run / "metrics.csv") != m["results_sha256"]:
        raise ValueError("Complete authenticated metrics required")
    public = episode["public"]
    verify_frozen_predictions(run, m, public)
    episode_cfg = episode["manifest"]["configuration"]
    axis = {
        "run": run.name,
        "split_seed": episode_cfg["seed"],
        "source_context": episode_cfg["source_context"],
        "target_context": episode_cfg["target_context"],
        "rank": cfg["policy"]["rank"],
    }
    if cfg["budgets"] != GRIDS["full_grid"] or cfg["seeds"] != [0, 1, 2]:
        raise ValueError("Robustness budget/seed grid differs from declaration")
    if set(cfg["policies"]) != set(POLICIES) or cfg["transfer"] is not None:
        raise ValueError("Robustness policies/backbones differ from declaration")
    if len(public.query_ids) != 131 or len(public.genes) != 7226:
        raise ValueError("Robustness target/gene axes changed")
    seen, groups, primary, zero = set(), defaultdict(list), {}, {}
    with (run / "metrics.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            p, s, n, b, q = (
                row["policy"],
                int(row["seed"]),
                int(row["budget"]),
                row["backbone"],
                row["query"],
            )
            key = p, s, n, b, q
            if (
                key in seen
                or p not in POLICIES
                or s not in cfg["seeds"]
                or n not in cfg["budgets"]
                or b not in BASE_BACKBONES
                or q not in public.query_ids
            ):
                raise ValueError("Duplicate or undeclared metric row")
            seen.add(key)
            if not np.isfinite(
                [float(row[k]) for k in ("mse", "specificity_mse", "assessment_noise_floor")]
            ).all():
                raise ValueError("Nonfinite metric")
            groups[p, b, n].append(row)
            if b == "ridge_cv":
                primary[p, s, n, q] = row
            elif b == "zero":
                zero[p, s, n, q] = row
    expected = (
        len(POLICIES)
        * len(cfg["seeds"])
        * len(cfg["budgets"])
        * len(BASE_BACKBONES)
        * len(public.query_ids)
    )
    if len(seen) != expected:
        raise ValueError("Incomplete metric grid")
    index = read_json(run / "prediction-index.json")
    ledgers = ledger_records(run, cfg, episode)
    checkpoints = []
    truth_path = run / "assessment.npz"
    with np.load(truth_path, allow_pickle=False) as arrays:
        truth = np.asarray(arrays["effects"], dtype=float)
        assessment_noise = np.asarray(arrays["mean_noise_variance"], dtype=float).mean(axis=1)
    zero_mse = np.mean(truth**2, axis=1)
    if truth.shape != (len(public.query_ids), len(public.genes)):
        raise ValueError("Assessment axes changed")
    for item in index:
        p, s, n = item["policy"], item["seed"], item["budget"]
        with np.load(run / item["artifact"], allow_pickle=False) as arrays:
            mse = np.mean((np.asarray(arrays["ridge_cv"], dtype=float) - truth) ** 2, axis=1)
            metrics = [primary[p, s, n, q] for q in public.query_ids]
            np.testing.assert_allclose(
                mse, [float(v["mse"]) for v in metrics], atol=1e-12, rtol=1e-10
            )
            np.testing.assert_allclose(
                zero_mse,
                [float(zero[p, s, n, q]["mse"]) for q in public.query_ids],
                atol=1e-12,
                rtol=1e-10,
            )
            np.testing.assert_allclose(
                assessment_noise,
                [float(v["assessment_noise_floor"]) for v in metrics],
                atol=1e-12,
                rtol=1e-10,
            )
            np.testing.assert_array_equal(
                arrays["identified"], [v["identified"] == "True" for v in metrics]
            )
            half_shift = arrays["source_half_ridge_cv_max_shift_mse"]
            np.testing.assert_allclose(
                half_shift,
                [float(v["source_half_max_prediction_shift_mse"]) for v in metrics],
                atol=1e-15,
                rtol=1e-12,
            )
            selected = float(arrays["ridge_cv_selected"])
            if selected not in [*cfg["policy"]["ridge_grid"], -1.0]:
                raise ValueError("Undeclared selected penalty")
            count = Counter()
            for event in ledgers[p, s][: item["ledger_events"]]:
                count[event["action"]["intervention"]] += event["action"]["cells"]
            checkpoints.append(
                {
                    **axis,
                    "policy": p,
                    "acquisition_seed": s,
                    "budget": n,
                    "actual_spend": item["spent"],
                    "prediction_sha256": item["sha256"],
                    "ledger_prefix_sha256": item["ledger_sha256"],
                    "ledger_events": item["ledger_events"],
                    "control_cells": count[CONTROL],
                    "perturbed_cells": sum(v for k, v in count.items() if k != CONTROL),
                    "interventions_opened": len(set(count) - {CONTROL}),
                    "selected_ridge_penalty": selected,
                    "selected_null": selected == -1,
                    "information_rank": int(arrays["information_rank"]),
                    "identified_queries": int(np.sum(arrays["identified"])),
                    "queries": len(public.query_ids),
                    "source_half_support_disagreements": int(
                        np.sum(arrays["source_half_support_disagreement"])
                    ),
                    "source_half_identified_both": int(
                        np.sum(arrays["source_half_identified_both"])
                    ),
                    "source_half_ridge_cv_mean_shift_mse": float(np.mean(half_shift)),
                    "source_half_ridge_cv_max_shift_mse": float(np.max(half_shift)),
                    "source_half_ridge_cv_selected_penalties": json.dumps(
                        arrays["source_half_ridge_cv_penalties"].tolist()
                    ),
                }
            )
    diagnostics, curves = [], []
    for p in cfg["policies"]:
        for n in cfg["budgets"]:
            records = [v for v in checkpoints if v["policy"] == p and v["budget"] == n]
            denominator = len(records) * len(public.query_ids)
            d = {
                **axis,
                "policy": p,
                "budget": n,
                "checkpoints": len(records),
                "query_seed_observations": denominator,
                "identified_fraction": sum(v["identified_queries"] for v in records) / denominator,
                "mean_actual_spend": float(np.mean([v["actual_spend"] for v in records])),
                "min_actual_spend": min(v["actual_spend"] for v in records),
                "max_actual_spend": max(v["actual_spend"] for v in records),
                "mean_control_cells": float(np.mean([v["control_cells"] for v in records])),
                "mean_perturbed_cells": float(np.mean([v["perturbed_cells"] for v in records])),
                "mean_interventions_opened": float(
                    np.mean([v["interventions_opened"] for v in records])
                ),
                "null_fits": sum(v["selected_null"] for v in records),
                "selected_penalty_counts": dict(
                    Counter(str(v["selected_ridge_penalty"]) for v in records)
                ),
                "source_half_support_disagreement_fraction": sum(
                    v["source_half_support_disagreements"] for v in records
                )
                / denominator,
                "source_half_identified_both_fraction": sum(
                    v["source_half_identified_both"] for v in records
                )
                / denominator,
                "source_half_ridge_cv_mean_shift_mse": float(
                    np.mean([v["source_half_ridge_cv_mean_shift_mse"] for v in records])
                ),
                "source_half_ridge_cv_max_shift_mse": max(
                    v["source_half_ridge_cv_max_shift_mse"] for v in records
                ),
            }
            diagnostics.append(d)
            for b in BASE_BACKBONES:
                rs = groups[p, b, n]
                values = {
                    name: float(np.mean([float(v[name]) for v in rs]))
                    for name in (
                        "mse",
                        "specificity_mse",
                        "assessment_noise_floor",
                        "recipient_measurements_used_cost",
                    )
                }
                curves.append(
                    {
                        **axis,
                        "policy": p,
                        "backbone": b,
                        "budget": n,
                        **values,
                        "noise_subtracted_mse": values["mse"] - values["assessment_noise_floor"],
                        "zero_mse": float(zero_mse.mean()),
                        "identified_fraction": d["identified_fraction"],
                        "mean_actual_spend": d["mean_actual_spend"],
                        "query_seed_observations": len(rs),
                    }
                )
    comparisons, query_rows, seed_rows, areas = [], [], [], {}
    for label, budgets in GRIDS.items():
        weights = area_weights(budgets)
        vectors = {}
        areas[label] = {"zero": float(zero_mse.mean())}
        for p in cfg["policies"]:
            by_seed = np.asarray(
                [
                    [
                        weights @ [float(primary[p, s, n, q]["mse"]) for n in budgets]
                        for q in public.query_ids
                    ]
                    for s in cfg["seeds"]
                ]
            )
            vectors[p] = by_seed.mean(axis=0)
            areas[label][p] = float(vectors[p].mean())
            for i, s in enumerate(cfg["seeds"]):
                seed_rows.append(
                    {
                        **axis,
                        "grid": label,
                        "policy": p,
                        "acquisition_seed": s,
                        "mean_area": float(by_seed[i].mean()),
                        "zero_area": float(zero_mse.mean()),
                    }
                )
        indices = np.random.default_rng(seed).integers(
            len(public.query_ids), size=(samples, len(public.query_ids))
        )
        for reference in ("worst_query", "mean_query"):
            a, b = vectors["bias_aware"], vectors[reference]
            delta = a - b
            low, high = np.quantile(delta[indices].mean(axis=1), [0.025, 0.975])
            c = {
                **axis,
                "grid": label,
                "budget_min": budgets[0],
                "budget_max": budgets[-1],
                "policy": "bias_aware",
                "reference": reference,
                "backbone": "ridge_cv",
                "extension_area": float(a.mean()),
                "reference_area": float(b.mean()),
                "paired_difference": float(delta.mean()),
                "relative_change": float(delta.mean() / b.mean()),
                "conditional_query_low": float(low),
                "conditional_query_high": float(high),
                "queries": len(public.query_ids),
                "acquisition_seeds": len(cfg["seeds"]),
                "query_difference_min": float(delta.min()),
                "query_difference_max": float(delta.max()),
                "query_difference_median": float(np.median(delta)),
                "query_fraction_extension_lower_error": float(np.mean(delta < 0)),
            }
            comparisons.append(c)
            for q, av, bv, difference in zip(public.query_ids, a, b, delta, strict=True):
                query_rows.append(
                    {
                        **axis,
                        "grid": label,
                        "reference": reference,
                        "query": q,
                        "extension_area": float(av),
                        "reference_area": float(bv),
                        "paired_difference": float(difference),
                    }
                )
    record = {
        **axis,
        "episode": episode["record"],
        "areas": areas,
        "comparisons": comparisons,
        "budget_diagnostics": diagnostics,
        "source_coordinates": m["source_coordinates"],
        "configuration_sha256": m["configuration_sha256"],
        "manifest_sha256": file_hash(run / "manifest.json"),
        "prediction_index_sha256": m["predictions_sha256"],
        "metric_sha256": m["results_sha256"],
        "assessment_sha256": file_hash(truth_path),
        "package_source_sha256": m["environment"]["source_tree_sha256"],
        "fixed_development_resources": m["fixed_development_resources"],
        "total_program_budget_grid": m["total_program_budget_grid"],
        "resources": {k: v for k, v in m.items() if "resources" in k or "runtime" in k},
    }
    return record, curves, checkpoints, diagnostics, comparisons, query_rows, seed_rows, len(seen)


def plot_matrix(records: list[dict], output: Path) -> None:
    records = sorted(records, key=lambda r: (r["split_seed"], r["source_context"], r["rank"]))
    columns = [(g, r) for g in GRIDS for r in ("worst_query", "mean_query")]
    matrix = np.asarray(
        [
            [
                next(
                    c["relative_change"] * 100
                    for c in row["comparisons"]
                    if (c["grid"], c["reference"]) == column
                )
                for column in columns
            ]
            for row in records
        ]
    )
    extent = max(float(np.max(np.abs(matrix))), 0.001)
    plt.rcParams.update(
        {"font.size": 8.5, "figure.dpi": 180, "svg.hashsalt": "mlresearch-robustness"}
    )
    figure, axis = plt.subplots(figsize=(6.7, 4.3), layout="constrained")
    shade = axis.imshow(
        matrix,
        cmap="RdBu_r",
        norm=TwoSlopeNorm(vcenter=0, vmin=-extent, vmax=extent),
        aspect="auto",
    )
    axis.set_xticks(
        range(4),
        ["128–512\nvs worst", "128–512\nvs mean", "128–2048\nvs worst", "128–2048\nvs mean"],
    )
    axis.set_yticks(
        range(8),
        [
            f"{r['split_seed']} · {r['source_context']}→{r['target_context']} · r{r['rank']}"
            for r in records
        ],
    )
    for i, j in np.ndindex(matrix.shape):
        axis.text(
            j,
            i,
            f"{matrix[i, j]:+.2f}%",
            ha="center",
            va="center",
            color="white" if abs(matrix[i, j]) > 0.65 * extent else "black",
            fontsize=8.5,
        )
    axis.set_title(
        "Post-primary robustness: every split/direction/rank\n"
        "Extension minus matched classical acquisition; ridge CV",
        fontsize=9,
    )
    color = figure.colorbar(shade, ax=axis, fraction=0.04, pad=0.03)
    color.set_label("Relative error-area change (%)\nNegative favors extension", fontsize=8.5)
    for extension in ("png", "svg", "pdf"):
        figure.savefig(
            output / f"robustness-matrix.{extension}",
            dpi=300,
            bbox_inches="tight",
            metadata={"Date": None} if extension == "svg" else None,
        )
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument(
        "--configuration", type=Path, default=Path("configs/publication-robustness-v1.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261022)
    args = parser.parse_args()
    started, cpu = time.perf_counter(), time.process_time()
    root = args.output.parent
    if any(p.exists() for p in (args.output, root / "frozen", root / "runs")):
        raise ValueError("Preserve existing robustness analysis/retained outputs")
    if args.samples != 2000 or args.seed != 20261022:
        raise ValueError("Keep the declared descriptive resampling settings")
    suite = read_json(args.suite / "manifest.json")
    if suite["state"] != "complete" or len(suite["configuration"]["runs"]) != 8:
        raise ValueError("Complete all8 robustness runs first")
    if (
        object_hash(asdict(ExternalConfig.load(args.configuration)))
        != suite["configuration_sha256"]
    ):
        raise ValueError("Configuration differs from complete suite")
    gate = validate_joint_freeze(args.suite / "joint-prediction-freeze.json")
    environment, resources = environment_record(), resource_record(root)
    args.output.mkdir(parents=True)
    shutil.copyfile(Path(__file__), args.output / "analysis-source.py")
    episodes = {}
    records, curves, checkpoints, diagnostics, comparisons, queries, seeds = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    metric_rows = 0
    retained = {}
    for entry in gate["runs"]:
        run = Path(entry["run_directory"])
        cfg = read_json(run / "manifest.json")["configuration"]
        episode_path = Path(cfg["episode_directory"])
        if episode_path not in episodes:
            episodes[episode_path] = bind_episode(episode_path)
        print("Authenticating and analyzing", run.name, flush=True)
        values = analyze_run(run, episodes[episode_path], args.seed, args.samples)
        records.append(values[0])
        for target, rows in zip(
            (curves, checkpoints, diagnostics, comparisons, queries, seeds),
            values[1:7],
            strict=True,
        ):
            target.extend(rows)
        metric_rows += values[7]
        retained[run.name] = retain_run(run, root, read_json(run / "manifest.json"))
        access = read_json(run / "assessment-access.json")
        if datetime.fromisoformat(access["opened_at"]) <= datetime.fromisoformat(gate["frozen_at"]):
            raise ValueError("Scoring preceded the joint barrier")
    matrix = {
        (r["split_seed"], r["source_context"], r["target_context"], r["rank"]) for r in records
    }
    expected_matrix = {
        (s, a, b, r)
        for s in (20261023, 20261024)
        for a, b in (("K562", "RPE1"), ("RPE1", "K562"))
        for r in (4, 16)
    }
    if matrix != expected_matrix:
        raise ValueError("Incomplete split/direction/rank matrix")
    for direction in ("k562-to-rpe1", "rpe1-to-k562"):
        path = Path(f"data/episodes/{direction}-v1")
        episodes[path] = bind_episode(path)
    overlaps = overlap_rows(list(episodes.values()))
    for filename, rows in (
        ("per-budget-curves.csv", curves),
        ("checkpoint-diagnostics.csv", checkpoints),
        (
            "per-budget-primary-diagnostics.csv",
            [
                {
                    **r,
                    "selected_penalty_counts": json.dumps(
                        r["selected_penalty_counts"], sort_keys=True
                    ),
                }
                for r in diagnostics
            ],
        ),
        ("paired-area-comparisons.csv", comparisons),
        ("paired-query-areas.csv", queries),
        ("acquisition-seed-areas.csv", seeds),
        ("episode-overlap.csv", overlaps),
    ):
        _write_csv(args.output / filename, rows)
    frozen = root / "frozen"
    shutil.copytree(args.suite, frozen / "suite")
    shutil.copyfile(args.configuration, frozen / "configuration.json")
    for episode in episodes.values():
        destination = frozen / "episodes" / episode["path"].name
        destination.mkdir(parents=True)
        for name in ("manifest.json", "public.json"):
            shutil.copyfile(episode["path"] / name, destination / name)
        pack(episode["path"] / "private-banks.json", destination / "private-banks.json.gz")
    plot_matrix(records, args.output)
    write_json(
        args.output / "summary.json",
        {
            "state": "complete",
            "recorded_at": utc_now(),
            "analysis_source_sha256": file_hash(Path(__file__)),
            "suite_manifest_sha256": file_hash(args.suite / "manifest.json"),
            "configuration_file_sha256": file_hash(args.configuration),
            "joint_gate_sha256": file_hash(args.suite / "joint-prediction-freeze.json"),
            "joint_frozen_at": gate["frozen_at"],
            "matrix_cells": records,
            "matrix_cells_count": len(records),
            "prediction_checkpoints": len(checkpoints),
            "authenticated_metric_rows": metric_rows,
            "all_backbone_curve_rows": len(curves),
            "paired_contrasts": len(comparisons),
            "conditional_query_resampling_samples": args.samples,
            "conditional_query_resampling_seed": args.seed,
            "episodes": [e["record"] for e in episodes.values()],
            "episode_pair_overlap_rows": len(overlaps),
            "retained_runs": retained,
            "environment": environment,
            "resources_start": resources,
            "resources_end": resource_record(root),
            "analysis_runtime_seconds": time.perf_counter() - started,
            "analysis_process_cpu_seconds": time.process_time() - cpu,
            "suite_resource_record": {
                k: v for k, v in suite.items() if "resources" in k or "runtime" in k
            },
            "qualification": [
                "All8 matrix cells and all models/policies/budgets retained; "
                "no refitting or new tuning.",
                "Both grids are post-primary exploratory sensitivity, "
                "not replacement confirmatory tests.",
                "Conditional query ranges average3 acquisition-order/tie seeds first; "
                "fixed split/source/scorer bank.",
                "Splits/ranks/directions reuse cell observations and source summaries; "
                "overlap documents dependence, not independent biological replication.",
                "Source-half displacement/support is finite split sensitivity, "
                "not calibrated confidence bounds.",
                "Runtime is wall clock; memory peaks are process lifetime. "
                "Analysis CPU is separate; suite CPU is not inferred.",
                "Historical development6428 and public-source/scorer resources "
                "remain separate from counterfactual purchases.",
            ],
        },
    )
    paths = [
        p
        for folder in (args.output, frozen, root / "runs")
        for p in folder.rglob("*")
        if p.is_file()
    ]
    write_json(
        args.output / "retained-artifacts.json",
        {
            "sha256": {p.relative_to(root).as_posix(): file_hash(p) for p in sorted(paths)},
            "total_bytes_excluding_this_manifest": sum(p.stat().st_size for p in paths),
            "raw_expression_included": False,
            "prediction_arrays_included": False,
        },
    )
    print(
        "Complete robustness analysis:",
        len(records),
        "matrix cells;",
        len(checkpoints),
        "checkpoints;",
        metric_rows,
        "metrics",
        flush=True,
    )


if __name__ == "__main__":
    main()
