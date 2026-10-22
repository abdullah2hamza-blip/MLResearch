"""Standalone plots and paired intervention summaries, conditional on scoring banks."""

from __future__ import annotations

import csv
import gzip
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from mlresearch.experiment import _write_csv
from mlresearch.provenance import (
    environment_record,
    file_hash,
    read_json,
    snapshot_sources,
    write_json,
)


def summarize_run(
    directory: Path, output: Path, *, bootstrap_seed: int = 513, bootstrap_samples: int = 2000
) -> dict[str, Any]:
    manifest = read_json(directory / "manifest.json")
    if manifest.get("state") != "complete":
        raise ValueError("Only a completed experiment can be reported")
    if file_hash(directory / "metrics.csv") != manifest["results_sha256"]:
        raise ValueError("Results checksum mismatch")
    if output.exists():
        raise ValueError("Report output exists; choose a fresh directory")
    analysis_environment = environment_record()
    if (
        isinstance(bootstrap_samples, bool)
        or not isinstance(bootstrap_samples, int)
        or bootstrap_samples < 100
    ):
        raise ValueError("At least 100 bootstrap samples are required")
    with (directory / "metrics.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    budgets = manifest["configuration"]["budgets"]
    if len(budgets) < 2:
        raise ValueError("At least two frozen budgets are required for the area endpoint")
    grouped: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    trajectories: dict[tuple[str, str, int, str], dict[int, float]] = defaultdict(dict)
    risks: dict[tuple[str, int], list[tuple[float, float]]] = defaultdict(list)
    for row in rows:
        policy, backbone, budget = row["policy"], row["backbone"], int(row["budget"])
        grouped[(policy, backbone, budget)].append(float(row["mse"]))
        trajectories[(policy, backbone, int(row["seed"]), row["query"])][budget] = float(row["mse"])
        if backbone == "ridge" and row["ideal_variance"]:
            risks[(policy, budget)].append((float(row["ideal_variance"]), float(row["mse"])))
    curves = [
        {"policy": p, "backbone": b, "budget": n, "mse": float(np.mean(v))}
        for (p, b, n), v in sorted(grouped.items())
    ]
    areas: list[dict[str, Any]] = []
    by_query: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for (policy, backbone, seed, query), trajectory in sorted(trajectories.items()):
        if set(trajectory) != set(budgets):
            raise ValueError("Incomplete or unmatched budget grid")
        area = float(
            np.trapezoid([trajectory[n] for n in budgets], budgets) / (budgets[-1] - budgets[0])
        )
        areas.append(
            {
                "policy": policy,
                "backbone": backbone,
                "seed": seed,
                "query": query,
                "normalized_area": area,
            }
        )
        by_query[(policy, backbone, query)].append(area)
    comparator, backbone = manifest["primary_comparator"], manifest["primary_backbone"]
    policies = manifest["configuration"]["policies"]
    queries = sorted({row["query"] for row in rows})
    comparisons = []
    if comparator in policies:
        reference = np.asarray([np.mean(by_query[(comparator, backbone, q)]) for q in queries])
        rng = np.random.default_rng(bootstrap_seed)
        indices = rng.integers(0, len(queries), size=(bootstrap_samples, len(queries)))
        for policy in policies:
            estimate = np.asarray([np.mean(by_query[(policy, backbone, q)]) for q in queries])
            delta = estimate - reference
            distribution = delta[indices].mean(axis=1)
            comparisons.append(
                {
                    "policy": policy,
                    "comparator": comparator,
                    "mean_normalized_area": float(estimate.mean()),
                    "paired_difference": float(delta.mean()),
                    "relative_error_change": float(delta.mean() / reference.mean())
                    if reference.mean()
                    else None,
                    "conditional_low": float(np.quantile(distribution, 0.025)),
                    "conditional_high": float(np.quantile(distribution, 0.975)),
                    "query_interventions": len(queries),
                    "acquisition_seeds": len(manifest["configuration"]["seeds"]),
                }
            )
    output.mkdir(parents=True)
    _write_csv(output / "curves.csv", curves)
    _write_csv(output / "areas-by-query-seed.csv", areas)
    if comparisons:
        _write_csv(output / "paired-comparisons.csv", comparisons)
    risk_rows = []
    for (policy, budget), values in sorted(risks.items()):
        ordered = np.asarray(sorted(values))
        for retention in (0.25, 0.5, 0.75, 1.0):
            retained = max(1, int(len(ordered) * retention))
            risk_rows.append(
                {
                    "policy": policy,
                    "budget": budget,
                    "retention": retention,
                    "mse": float(ordered[:retained, 1].mean()),
                }
            )
    if risk_rows:
        _write_csv(output / "risk-retention.csv", risk_rows)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "figure.dpi": 140, "svg.hashsalt": "mlresearch"})
    noise_floor = float(np.mean([float(row["assessment_noise_floor"]) for row in rows]))
    for kind in ("acquisition", "predictor"):
        figure, axis = plt.subplots(figsize=(7.2, 4.2), layout="constrained")
        display_policy = "bias_aware" if "bias_aware" in policies else policies[0]
        labels = policies if kind == "acquisition" else sorted({row["backbone"] for row in rows})
        for label in labels:
            p, b = (label, backbone) if kind == "acquisition" else (display_policy, label)
            axis.plot(
                budgets, [np.mean(grouped[(p, b, n)]) for n in budgets], marker="o", label=label
            )
        if kind == "acquisition":
            axis.axhline(
                np.mean(grouped[(policies[0], "zero", budgets[0])]),
                color="black",
                linestyle="--",
                linewidth=1,
                label="zero effect",
            )
        axis.axhline(
            noise_floor,
            color="gray",
            linestyle=":",
            linewidth=1,
            label="estimated assessment noise",
        )
        axis.set(
            xlabel="Frozen acquisition budget (abstract cost units)",
            ylabel="Mean full aligned-gene squared error",
            title=f"Same {backbone} predictor across acquisition policies"
            if kind == "acquisition"
            else f"Predictors under {display_policy} acquisition",
        )
        axis.legend(fontsize=7, ncols=2)
        for extension in ("png", "svg"):
            figure.savefig(
                output / f"{kind}-curves.{extension}",
                metadata={"Date": None} if extension == "svg" else None,
            )
        plt.close(figure)
    scope = (
        "Descriptive query-intervention bootstrap conditional on source data, fixed split, "
        "acquisition seeds, and fixed assessment/control bank. Excludes biological, "
        "guide/batch and common scoring-control uncertainty."
    )
    summary = {
        "run_manifest_sha256": file_hash(directory / "manifest.json"),
        "comparisons": comparisons,
        "bootstrap_seed": bootstrap_seed,
        "bootstrap_samples": bootstrap_samples,
        "interval_scope": scope,
        "assessment_noise_floor": noise_floor,
        "interpretation": "Lower error area and negative differences favor the named policy.",
        "limitations": manifest["limitations"],
    }
    write_json(output / "summary.json", summary)
    lines = [
        "# Replay results",
        "",
        f"Run label: `{manifest['configuration']['label']}`.",
        "",
        "Source-query responses are public; recipient-query responses are scorer-only.",
        "",
        "| Policy | Mean error area | Difference vs worst-query | Conditional 95% interval |",
        "| --- | ---: | ---: | ---: |",
    ]
    for item in comparisons:
        lines.append(
            f"| {item['policy']} | {item['mean_normalized_area']:.6g} | "
            f"{item['paired_difference']:.6g} | "
            f"[{item['conditional_low']:.6g}, {item['conditional_high']:.6g}] |"
        )
    lines.extend(
        [
            "",
            "![Acquisition curves](acquisition-curves.png)",
            "",
            "![Predictor curves](predictor-curves.png)",
            "",
            scope,
            "",
            "Gaussian coverage and risk-retention tables are diagnostic. "
            "Adaptive coverage is unvalidated.",
            "",
            "These results do not establish prospective benefit, causal transportability, "
            "biological replication, or a novel method.",
            "",
        ]
    )
    (output / "results.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    for name in ("manifest.json", "allocations.csv", "prediction-index.json", "code.zip"):
        if (directory / name).is_file():
            shutil.copyfile(
                directory / name,
                output / ("run-manifest.json" if name == "manifest.json" else name),
            )
    with (
        (directory / "metrics.csv").open("rb") as source,
        (output / "metrics.csv.gz").open("wb") as sink,
    ):
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, mtime=0) as packed:
            shutil.copyfileobj(source, packed)
    analysis_snapshot = snapshot_sources(
        output / "analysis-code.zip", analysis_environment["source_hashes"]
    )
    write_json(
        output / "retained-artifacts.json",
        {
            "run_directory": str(directory),
            "metrics_uncompressed_sha256": file_hash(directory / "metrics.csv"),
            "analysis_environment": analysis_environment,
            "analysis_source_snapshot": analysis_snapshot,
            "raw_cells_included": False,
            "sha256": {path.name: file_hash(path) for path in output.iterdir() if path.is_file()},
            "large_outputs": (
                "Raw/prepared cells and prediction arrays remain ignored; "
                "regenerate from pinned inputs and saved configurations."
            ),
        },
    )
    return summary
