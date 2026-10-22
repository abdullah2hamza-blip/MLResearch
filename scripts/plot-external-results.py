"""Standalone external figures from authenticated, retained analysis tables."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mlresearch.provenance import file_hash, read_json, write_json  # noqa: E402

LABELS = {
    "bias_aware": "Discrepancy extension",
    "worst_query": "Classical worst query",
    "mean_query": "Classical mean query",
    "fixed_grid": "Fixed grid",
}
COLORS = dict(zip(LABELS, ("#0072B2", "#D55E00", "#009E73", "#CC79A7"), strict=True))


def table(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Figure output exists")
    summary = read_json(args.results / "supplement" / "summary.json")
    curves = table(args.results / "supplement" / "curves-and-specificity.csv")
    paired = table(args.results / "supplement" / "paired-primary-comparisons.csv")
    primary = [run for run in summary["runs"] if run["source_control"] == "none"]
    if len(primary) != 2:
        raise ValueError("Expected both declared primary directions")
    args.output.mkdir(parents=True)
    plt.rcParams.update(
        {
            "font.size": 9,
            "figure.dpi": 160,
            "svg.hashsalt": "mlresearch",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )

    def save(fig, name):
        for extension in ("png", "svg", "pdf"):
            fig.savefig(
                args.output / f"{name}.{extension}",
                bbox_inches="tight",
                metadata={"Date": None} if extension == "svg" else None,
            )
        plt.close(fig)

    figure, axes = plt.subplots(2, 2, figsize=(11, 7), layout="constrained")
    for row, run in enumerate(primary):
        name = run["run"]
        title = run["source_context"] + " → " + run["target_context"]
        axis = axes[row, 0]
        for policy, label in LABELS.items():
            points = sorted(
                [
                    r
                    for r in curves
                    if r["run"] == name and r["policy"] == policy and r["backbone"] == "ridge_cv"
                ],
                key=lambda r: int(r["budget"]),
            )
            axis.plot(
                [int(r["budget"]) for r in points],
                [float(r["mse"]) for r in points],
                "o-",
                label=label,
                color=COLORS[policy],
            )
        zero = next(r for r in curves if r["run"] == name and r["backbone"] == "zero")
        axis.axhline(float(zero["mse"]), color="black", linestyle="--", label="Zero effect")
        axis.axhline(
            float(zero["assessment_noise_floor"]),
            color="gray",
            linestyle=":",
            label="Assessment noise estimate",
        )
        axis.set(
            title=title + ": matched ridge CV",
            xlabel="Incremental recipient budget",
            ylabel="Full aligned-gene mean squared error",
        )
        axis.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
        axis.legend(fontsize=7, ncols=2)
        axis = axes[row, 1]
        scopes = [
            "query_bootstrap_conditional_on_bank",
            "iid_cell_bootstrap_fixed_queries",
            "stratified_cell_bootstrap_fixed_queries",
            "batch_reweighting_sensitivity",
        ]
        labels = [
            "Query identities",
            "IID assessment cells",
            "Guide/batch stratified cells",
            "Technical batch sensitivity",
        ]
        plotted_labels = []
        for j, reference in enumerate(("worst_query", "mean_query")):
            analysis = read_json(args.results / "uncertainty" / f"{name}-vs-{reference}.json")
            for k, (scope, label) in enumerate(zip(scopes, labels, strict=True)):
                value = analysis.get(scope)
                if value is None:
                    continue
                # Summary schema is checked explicitly; unavailable batch metadata is not a band.
                if "percentile_low" not in value or "percentile_high" not in value:
                    if scope == "batch_reweighting_sensitivity" and not value.get(
                        "available", True
                    ):
                        continue
                    raise ValueError("Unexpected paired-band schema: " + scope)
                y = j * 5 + k
                axis.plot(
                    [value["percentile_low"], value["percentile_high"]],
                    [y, y],
                    color=COLORS[reference],
                    lw=2,
                )
                axis.plot(analysis["paired_difference"], y, "o", color=COLORS[reference], ms=4)
                plotted_labels.append((y, label + (" vs worst" if j == 0 else " vs mean")))
        axis.axvline(0, color="gray", linestyle="--", lw=1)
        axis.set(
            yticks=[x[0] for x in plotted_labels],
            yticklabels=[x[1] for x in plotted_labels],
            xlabel="Extension minus comparator: normalized error area",
            title=title + ": separate conditional scopes",
        )
        axis.invert_yaxis()
        axis.ticklabel_format(axis="x", style="sci", scilimits=(0, 0))
    save(figure, "primary-error-and-uncertainty")

    figure, axes = plt.subplots(1, 2, figsize=(11, 6), layout="constrained")
    for axis, run in zip(axes, primary, strict=True):
        points = [r for r in paired if r["run"] == run["run"] and r["reference"] == "worst_query"]
        for y, point in enumerate(points):
            color = COLORS.get(point["policy"], "#666666")
            axis.plot(
                [float(point["conditional_low"]), float(point["conditional_high"])],
                [y, y],
                color=color,
                lw=1.5,
            )
            axis.plot(float(point["paired_difference"]), y, "o", color=color, ms=4)
        axis.axvline(0, color="gray", linestyle="--", lw=1)
        axis.set(
            yticks=range(len(points)),
            yticklabels=[p["policy"] for p in points],
            title=run["source_context"] + " → " + run["target_context"],
            xlabel="Error area minus classical worst query (ridge CV)",
        )
        axis.invert_yaxis()
        axis.ticklabel_format(axis="x", style="sci", scilimits=(0, 0))
    figure.suptitle("All declared acquisition policies and ablations; conditional query bands")
    save(figure, "all-policies-and-ablations")

    figure, axes = plt.subplots(2, 2, figsize=(11, 7), layout="constrained")
    for row, run in enumerate(primary):
        related = [r for r in summary["runs"] if r["target_context"] == run["target_context"]]
        controls = ("none", "identity_permutation", "query_gene_permutation")
        for col, key in enumerate(("mse_area", "specificity_area")):
            axis = axes[row, col]
            for policy, label in LABELS.items():
                values = []
                for control in controls:
                    r = next(r for r in related if r["source_control"] == control)
                    point = next(
                        a
                        for a in r["areas"]
                        if a["policy"] == policy and a["backbone"] == "ridge_cv"
                    )
                    values.append(point[key])
                axis.plot(np.arange(3), values, "o-", label=label, color=COLORS[policy])
            axis.set(
                xticks=range(3),
                xticklabels=["Original", "Identity permuted", "Query genes permuted"],
                ylabel="Normalized error area",
                title=run["target_context"]
                + (": absolute effects" if col == 0 else ": response-specific centered effects"),
            )
            axis.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
            axis.legend(fontsize=7)
    save(figure, "source-permutation-specificity")

    figure, axes = plt.subplots(2, 3, figsize=(12, 7), layout="constrained")
    for row, run in enumerate(primary):
        allocations = table(args.results / "runs" / run["run"] / "allocations.csv")
        for col, field in enumerate(("control_cells", "interventions_opened", "perturbed_cells")):
            axis = axes[row, col]
            for policy, label in LABELS.items():
                points = []
                for budget in (128, 256, 512):
                    selected = [
                        r
                        for r in allocations
                        if r["policy"] == policy and int(r["budget"]) == budget
                    ]
                    points.append(np.mean([float(r[field]) for r in selected]))
                axis.plot((128, 256, 512), points, "o-", color=COLORS[policy], label=label)
            axis.set(
                xlabel="Incremental recipient budget",
                ylabel=field.replace("_", " "),
                title=run["target_context"],
            )
            if col == 0:
                axis.legend(fontsize=7)
    save(figure, "allocation-decisions")
    figure, axes = plt.subplots(2, 3, figsize=(12, 7), layout="constrained")
    for row, run in enumerate(primary):
        retention = table(args.results / "runs" / run["run"] / "risk-retention.csv")
        for col, budget in enumerate((128, 256, 512)):
            axis = axes[row, col]
            for policy, label in LABELS.items():
                for criterion, style in (
                    ("linear_support", "-"),
                    ("linear_support_and_source_stability", ":"),
                ):
                    points = [
                        r
                        for r in retention
                        if r["policy"] == policy
                        and int(r["budget"]) == budget
                        and r["criterion"] == criterion
                        and r["mse"]
                    ]
                    axis.plot(
                        [float(r["actual_retention"]) for r in points],
                        [float(r["mse"]) for r in points],
                        marker="o",
                        linestyle=style,
                        color=COLORS[policy],
                        label=label if style == "-" else None,
                    )
            axis.set(
                xlabel="Actual fraction of query/seed predictions retained",
                ylabel="MSE",
                title=run["target_context"] + f"; budget {budget}",
                xlim=(0, 1.03),
            )
            if col == 0:
                axis.legend(fontsize=7)
    figure.suptitle(
        "Predictor-only retention: support (solid), support + source stability (dotted)"
    )
    save(figure, "risk-retention")
    write_json(
        args.output / "figure-provenance.json",
        {
            "analysis_source_sha256": file_hash(Path(__file__)),
            "inputs": {
                str(p.relative_to(args.results)): file_hash(p)
                for p in args.results.rglob("*")
                if p.is_file() and p.suffix in (".csv", ".json") and args.output not in p.parents
            },
            "qualification": (
                "Standalone descriptive figures; directions share data; bands have separate scopes."
            ),
        },
    )


if __name__ == "__main__":
    main()
