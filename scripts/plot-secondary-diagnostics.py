"""Export actual ordinal ranking and both nominal interval diagnostic figures."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mlresearch.models import BACKBONES  # noqa: E402
from mlresearch.provenance import file_hash, read_json, write_json  # noqa: E402


def table(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Diagnostic figure output exists")
    if read_json(args.analysis / "summary.json")["state"] != "complete":
        raise ValueError("Complete diagnostic synthesis first")
    coordinates = table(args.analysis / "coordinate-metrics-by-world.csv")
    ranking = table(args.analysis / "ranking-by-world.csv")
    intervals = table(args.analysis / "intervals-by-world.csv")
    primary = [
        r
        for r in read_json(args.primary / "supplement/summary.json")["runs"]
        if r["source_control"] == "none"
    ]
    args.output.mkdir(parents=True)
    plt.rcParams.update({"font.size": 9, "figure.dpi": 160, "svg.hashsalt": "mlresearch"})

    def save(fig, name):
        for extension in ("png", "svg", "pdf"):
            fig.savefig(
                args.output / f"{name}.{extension}",
                bbox_inches="tight",
                metadata={"Date": None} if extension == "svg" else None,
            )
        plt.close(fig)

    labels = [
        "Zero",
        "Shared mean",
        "Source copy",
        "Affine",
        "Fixed ridge",
        "Paid ridge CV",
        "Local residual",
        "Recipient network",
        "Reconstruction",
    ]
    figure, axes = plt.subplots(2, 2, figsize=(11, 7), layout="constrained")
    for i, run in enumerate(primary):

        def selected(rows, name, run=run):
            return next(
                r
                for r in rows
                if r["run"] == run["run"]
                and r["policy"] == "bias_aware"
                and r["budget"] == "512"
                and r["backbone"] == name
            )

        y = np.arange(len(BACKBONES))
        axes[i, 0].barh(
            y, [float(selected(coordinates, b)["mse"]) for b in BACKBONES], color="#0072B2"
        )
        axes[i, 0].set(
            yticks=y,
            yticklabels=labels,
            xlabel="Full-gene MSE (lower is better)",
            title=run["source_context"] + " → " + run["target_context"],
        )
        axes[i, 0].invert_yaxis()
        axes[i, 1].barh(
            y - 0.17,
            [float(selected(ranking, b)["fixed_gene_rank_score"]) for b in BACKBONES],
            height=0.32,
            label="Original genes",
            color="#009E73",
        )
        axes[i, 1].barh(
            y + 0.17,
            [float(selected(ranking, b)["permuted_fixed_gene_rank_score"]) for b in BACKBONES],
            height=0.32,
            label="Genes permuted in scoring",
            color="#999999",
        )
        axes[i, 1].set(
            yticks=y,
            yticklabels=labels,
            xlabel="Mean rank score (undefined genes contribute0)",
            title="Perturbation ordering within each gene (higher is better)",
        )
        axes[i, 1].invert_yaxis()
        axes[i, 1].legend(fontsize=7)
    figure.suptitle("Same extension purchases, budget512; mean over five acquisition seeds")
    save(figure, "absolute-error-versus-ordinal-ranking")

    scenarios = [
        "baseline",
        "mechanism_shift_2",
        "source_feature_error_one",
        "batch_shift_one",
        "rank_missing",
        "exact_rank_missing",
    ]
    names = [
        "Base",
        "Nonlinear\nshift",
        "Source\nerror SD1",
        "Shared\nbatches",
        "Missing\n+ noise",
        "Missing,\nexact source",
    ]
    values = []
    for scenario in scenarios:
        rows = [
            r
            for r in intervals
            if r["scope"] == "controlled_truth"
            and r["scenario"] == scenario
            and r["policy"] == "worst_query"
            and r["budget"] == "192"
        ]
        if len(rows) != 5:
            raise ValueError("Expected five complete independent worlds per shown scenario")
        n = sum(int(r["finite_query_seed_intervals"]) for r in rows)
        total = sum(int(r["total_query_seed_observations"]) for r in rows)
        values.append(
            {
                "n": n,
                "total": total,
                **{
                    key: sum(
                        float(r[key] or 0) * int(r["finite_query_seed_intervals"]) for r in rows
                    )
                    / n
                    if n
                    else np.nan
                    for key in (
                        "coverage_or_compatibility_90",
                        "coverage_or_compatibility_95",
                        "mean_width_90",
                        "mean_width_95",
                    )
                },
            }
        )
    figure, axes = plt.subplots(1, 2, figsize=(11.5, 4.5), layout="constrained")
    x = np.arange(len(scenarios))
    for offset, level, color in ((-0.18, 90, "#0072B2"), (0.18, 95, "#D55E00")):
        axes[0].bar(
            x + offset,
            [r[f"coverage_or_compatibility_{level}"] for r in values],
            width=0.34,
            color=color,
            label=f"{level}% diagnostic",
        )
        axes[0].axhline(level / 100, color=color, ls="--", lw=1)
        axes[1].bar(
            x + offset,
            [r[f"mean_width_{level}"] for r in values],
            width=0.34,
            color=color,
            label=f"{level}% diagnostic",
        )
    ticks = [f"{name}\n[{r['n']}/{r['total']}]" for name, r in zip(names, values, strict=True)]
    axes[0].set(ylim=(0, 1.06), ylabel="Known-truth coverage, conditional on finite widths")
    axes[1].set(yscale="log", ylabel="Mean full interval width (log scale)")
    for axis in axes:
        axis.set(xticks=x, xticklabels=ticks, xlabel="Scenario [finite query/seed intervals / all]")
        axis.legend(fontsize=7)
        for j, row in enumerate(values):
            if row["n"] == 0:
                axis.annotate(
                    "No finite\nintervals",
                    (j, 0.05),
                    xycoords=("data", "axes fraction"),
                    ha="center",
                    fontsize=7,
                )
    figure.suptitle("Fixed ridge / classical worst query; budget192; five generated worlds")
    save(figure, "known-truth-90-and-95-diagnostics")
    write_json(
        args.output / "figure-provenance.json",
        {
            "analysis_source_sha256": file_hash(Path(__file__)),
            "input_sha256": {
                str(p): file_hash(p)
                for p in [
                    args.analysis / "coordinate-metrics-by-world.csv",
                    args.analysis / "ranking-by-world.csv",
                    args.analysis / "intervals-by-world.csv",
                    args.primary / "supplement/summary.json",
                ]
            },
            "qualification": [
                "Rank scores and absolute effects answer different questions.",
                "Undefined-gene neutral scores and correlation denominators remain in tables.",
                "Intervals are ideal-model diagnostics, not validated adaptive/biological CIs.",
            ],
        },
    )


if __name__ == "__main__":
    main()
