"""Summarize the declared price sensitivity and charged direct-query reference."""

from __future__ import annotations

import argparse
import csv
import io
import zipfile
from collections import defaultdict
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mlresearch.experiment import _write_csv  # noqa: E402
from mlresearch.provenance import file_hash, read_json, write_json  # noqa: E402


def table(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supplement", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Secondary allocation output exists")
    rows, sources = [], {}
    for cost in (0, 16, 64):
        root = args.supplement / f"setup-cost-{cost}"
        manifest = read_json(root / "study-manifest.json")
        if manifest["state"] != "complete" or len(manifest["cases"]) != 10:
            raise ValueError("Incomplete cost sensitivity")
        sources[str(root / "study-manifest.json")] = file_hash(root / "study-manifest.json")
        spends = defaultdict(list)
        with zipfile.ZipFile(root / "case-audits.zip") as archive:
            for name in archive.namelist():
                if name.endswith("allocations.csv"):
                    scenario = name.split("/")[1]
                    for record in csv.DictReader(io.StringIO(archive.read(name).decode())):
                        spends[scenario, record["policy"], int(record["budget"])].append(
                            int(record["spent"])
                        )
        for record in manifest["summary"]["comparisons"]:
            rows.append(
                {
                    "setup_cell_ratio": cost,
                    **record,
                    **{
                        f"mean_actual_spend_budget_{b}": float(
                            np.mean(spends[record["scenario"], record["policy"], b])
                        )
                        for b in (512, 768, 1024)
                    },
                }
            )
    direct_path = args.supplement / "direct-query" / "checkpoint-summary.csv"
    direct = table(direct_path)
    if read_json(direct_path.parent / "manifest.json")["state"] != "complete":
        raise ValueError("Direct reference incomplete")
    sources[str(direct_path)] = file_hash(direct_path)
    grouped = defaultdict(list)
    for record in direct:
        grouped[
            record["run"],
            int(record["query_depth"]),
            int(record["control_depth"]),
            int(record["spent"]),
        ].append(float(record["mean_mse"]))
    direct_rows = [
        {
            "run": run,
            "query_depth": depth,
            "control_depth": controls,
            "spent": spent,
            "mean_mse": float(np.mean(values)),
            "seeds": len(values),
            "seed_min_mse": min(values),
            "seed_max_mse": max(values),
        }
        for (run, depth, controls, spent), values in sorted(grouped.items())
    ]
    args.output.mkdir(parents=True)
    _write_csv(args.output / "setup-cost-comparisons.csv", rows)
    _write_csv(args.output / "direct-query-curves.csv", direct_rows)
    plt.rcParams.update({"font.size": 9, "figure.dpi": 160, "svg.hashsalt": "mlresearch"})

    def save(fig, name):
        for extension in ("png", "svg", "pdf"):
            fig.savefig(
                args.output / f"{name}.{extension}",
                bbox_inches="tight",
                metadata={"Date": None} if extension == "svg" else None,
            )
        plt.close(fig)

    figure, axes = plt.subplots(2, 2, figsize=(10.5, 7), layout="constrained")
    for row, scenario in enumerate(("baseline", "mechanism_shift_2")):
        for policy in ("bias_aware", "mean_query"):
            points = sorted(
                [r for r in rows if r["scenario"] == scenario and r["policy"] == policy],
                key=lambda r: r["setup_cell_ratio"],
            )
            axes[row, 0].errorbar(
                [r["setup_cell_ratio"] for r in points],
                [r["paired_difference"] for r in points],
                yerr=[r["monte_carlo_standard_error"] for r in points],
                fmt="o-",
                capsize=3,
                label=policy,
            )
        axes[row, 0].axhline(0, color="gray", ls="--", lw=1)
        axes[row, 0].set(
            title=scenario + ": paired difference ±1 MCSE",
            xlabel="Hypothetical setup / cell price",
            ylabel="True error area minus worst query",
        )
        axes[row, 0].ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
        axes[row, 0].legend(fontsize=7)
        for policy in (
            "random_equal",
            "fixed_grid",
            "worst_query",
            "mean_query",
            "bias_aware",
            "bias_identity_only",
        ):
            points = sorted(
                [r for r in rows if r["scenario"] == scenario and r["policy"] == policy],
                key=lambda r: r["setup_cell_ratio"],
            )
            axes[row, 1].plot(
                [r["setup_cell_ratio"] for r in points],
                [r["mean_true_error_area"] for r in points],
                "o-",
                label=policy,
            )
        axes[row, 1].set(
            title=scenario + ": all six policies",
            xlabel="Hypothetical setup / cell price",
            ylabel="Mean true error area; common budget grid512–1024",
        )
        axes[row, 1].legend(fontsize=7, ncols=2)
    save(figure, "setup-price-sensitivity")

    curves = table(args.primary / "supplement" / "curves-and-specificity.csv")
    primary_summary = read_json(args.primary / "supplement" / "summary.json")
    contexts = {
        r["run"]: r["source_context"] + " → " + r["target_context"] for r in primary_summary["runs"]
    }
    sources[str(args.primary / "supplement" / "summary.json")] = file_hash(
        args.primary / "supplement" / "summary.json"
    )
    sources[str(args.primary / "supplement" / "curves-and-specificity.csv")] = file_hash(
        args.primary / "supplement" / "curves-and-specificity.csv"
    )
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), layout="constrained")
    for axis, run in zip(axes, sorted({r["run"] for r in direct_rows}), strict=True):
        points = [r for r in direct_rows if r["run"] == run]
        axis.plot(
            [r["spent"] for r in points],
            [r["mean_mse"] for r in points],
            "o-",
            label="Direct query measurements (task C)",
        )
        for policy in ("bias_aware", "worst_query"):
            selected = sorted(
                [
                    r
                    for r in curves
                    if r["run"] == run and r["policy"] == policy and r["backbone"] == "ridge_cv"
                ],
                key=lambda r: int(r["budget"]),
            )
            axis.plot(
                [float(r["mean_spent"]) for r in selected],
                [float(r["mse"]) for r in selected],
                "o-",
                label=policy + " (sealed queries)",
            )
        zero = next(r for r in curves if r["run"] == run and r["backbone"] == "zero")
        axis.axhline(float(zero["mse"]), color="gray", ls="--", label="Zero effect (use cost0)")
        axis.set(
            xscale="log",
            yscale="log",
            xlabel="Actual incremental cost; distinct tasks",
            ylabel="Full-gene assessment MSE",
            title=contexts[run],
        )
        axis.legend(fontsize=7)
    save(figure, "charged-direct-measurement")
    write_json(
        args.output / "summary.json",
        {
            "analysis_source_sha256": file_hash(Path(__file__)),
            "sources": sources,
            "cost_cases": 30,
            "worlds_per_price_scenario": 5,
            "direct_checkpoints": len(direct),
            "qualification": [
                "Post-primary supplements; original primary result unchanged.",
                "Price0/16 exhaust pools and constrained policies may underspend.",
                "MCSE uses paired independent generated worlds, not biological replication.",
                "Direct starts802 > primary max512; no equal-cost crossover observed.",
            ],
        },
    )


if __name__ == "__main__":
    main()
