"""Build manuscript tables, numerical macros and legible figures from retained evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import shutil
import zipfile
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mlresearch.models import BACKBONES  # noqa: E402
from mlresearch.provenance import file_hash, read_json, utc_now, write_json  # noqa: E402


def table(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def tex(value: str) -> str:
    return value.replace("_", r"\_").replace("%", r"\%")


def scaled_range(low: float, high: float, places: int = 3) -> str:
    return f"[{1e5 * low:+.{places}f}, {1e5 * high:+.{places}f}]"


POLICY_LABELS = {
    "random_equal": "Random/equal",
    "fixed_grid": "Fixed grid",
    "diversity": "Diversity",
    "d_optimal": "D-optimal",
    "worst_query": "Worst query",
    "mean_query": "Mean query",
    "reliability": "Reliability",
    "disagreement": "Disagreement",
    "bias_aware": "RBF aug.",
    "bias_gamma025": "RBF weight .25",
    "bias_no_extension": "RBF weight 0",
    "bias_fixed_order": "Fixed order",
    "bias_fixed_interventions": "No openings",
    "bias_equal_depth": "No extra depth",
    "bias_fixed_controls": "Fixed controls",
    "bias_independent_controls": "Diagonal noise",
}
SCENARIO_LABELS = {
    "baseline": "Baseline",
    "mechanism_shift_2": "Nonlinear shift",
    "source_feature_error_one": "Source error SD 1",
    "source_feature_error_half": "Source error SD .5",
    "source_measurement_noise_two": "Source noise SD 2",
    "recipient_noise_half": "Recipient noise SD .5",
    "recipient_noise_double": "Recipient noise SD 2",
    "batch_shift_one": "Shared batches",
    "control_noise_four": "Control SD x4",
    "rank_missing": "Missing direction, noisy",
    "exact_rank_full": "Full rank, exact source",
    "exact_rank_missing": "Missing direction, exact",
    "source_identity_permutation": "Source identity shuffled",
    "query_gene_permutation": "Query genes shuffled",
}


def tabular(headers: list[str], rows: list[list[str]], columns: str) -> str:
    return "\n".join(
        [
            r"\begin{tabular}{" + columns + "}",
            r"\toprule",
            " & ".join(headers) + r" \\",
            r"\midrule",
        ]
        + [" & ".join(row) + r" \\" for row in rows]
        + [r"\bottomrule", r"\end{tabular}", ""]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("paper/generated"))
    parser.add_argument("--figures", type=Path, default=Path("paper/figures"))
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--robustness", type=Path)
    args = parser.parse_args()
    if (args.output.exists() or args.figures.exists()) and not args.replace:
        raise ValueError("Use --replace explicitly to regenerate derived manuscript assets")
    args.output.mkdir(parents=True, exist_ok=True)
    args.figures.mkdir(parents=True, exist_ok=True)
    inputs, figure_sources = {}, {}

    def evidence(path: Path) -> Path:
        if not path.is_file():
            raise ValueError(f"Missing manuscript input: {path}")
        inputs[path.as_posix()] = file_hash(path)
        return path

    primary = Path("docs/results/external-evaluation-v1")
    secondary = Path("docs/results/secondary-supplement-v1")
    controlled = Path("docs/results/controlled-study-v1")
    primary_index = read_json(evidence(primary / "supplement-artifacts.json"))["sha256"]
    secondary_index = read_json(evidence(secondary / "supplement-artifacts.json"))["sha256"]
    controlled_index = read_json(evidence(controlled / "retained-artifacts.json"))["sha256"]

    def retained(root: Path, relative: str, index: dict) -> Path:
        path = evidence(root / relative)
        if file_hash(path) != index[relative]:
            raise ValueError(f"Changed retained manuscript input: {path}")
        return path

    def p(relative: str) -> Path:
        return retained(primary, relative, primary_index)

    def s(relative: str) -> Path:
        return retained(secondary, relative, secondary_index)

    original = read_json(p("supplement/summary.json"))
    comparisons = table(p("supplement/paired-primary-comparisons.csv"))
    curves = table(p("supplement/curves-and-specificity.csv"))
    references = table(s("diagnostic-analysis/development-reference-comparisons.csv"))
    interval = table(s("diagnostic-analysis/intervals-by-world.csv"))
    ranking = table(s("diagnostic-analysis/ranking-by-world.csv"))
    coordinates = table(s("diagnostic-analysis/coordinate-metrics-by-world.csv"))
    studies = read_json(retained(controlled, "study-manifest.json", controlled_index))
    run_info = [r for r in original["runs"] if r["source_control"] == "none"]
    if len(run_info) != 2:
        raise ValueError("Expected both original directions")
    headline, reference_rows, macros, registry = [], [], [], {}
    plt.rcParams.update(
        {
            "font.size": 8.5,
            "figure.dpi": 180,
            "svg.hashsalt": "publication-study",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )

    def macro(name: str, value: str) -> None:
        macros.append("\\newcommand{\\" + name + "}{" + value + "}")

    def save(figure, name: str) -> None:
        for suffix in ("pdf", "png", "svg"):
            figure.savefig(
                args.figures / f"{name}.{suffix}",
                bbox_inches="tight",
                metadata={"Date": None} if suffix == "svg" else None,
            )
        plt.close(figure)

    figure = plt.figure(figsize=(6.7, 6.0), layout="constrained")
    grid = figure.add_gridspec(2, 2, height_ratios=[1.1, 1])
    effect_axis = figure.add_subplot(grid[1, :])
    all_effects = []
    policy_labels = {
        "bias_aware": "Fixed-RBF augmentation",
        "worst_query": "Classical worst query",
        "mean_query": "Classical mean query",
        "reliability": "Development paid reference",
    }
    colors = {
        "bias_aware": "#0072B2",
        "worst_query": "#D55E00",
        "mean_query": "#CC79A7",
        "reliability": "#009E73",
    }
    for number, run in enumerate(run_info):
        name = run["run"]
        direction = run["source_context"] + r"$\to$" + run["target_context"]
        prefix = "Forward" if number == 0 else "Reverse"
        row = next(
            r
            for r in comparisons
            if r["run"] == name
            and r["policy"] == "bias_aware"
            and r["reference"] == "worst_query"
            and r["backbone"] == "ridge_cv"
        )
        delta = float(row["paired_difference"])
        ext = float(row["mean_area"])
        base = ext - delta
        macro(prefix + "Percent", f"{100 * float(row['relative_change']):.4g}")
        macro(prefix + "Area", f"{ext:.8f}")
        registry[prefix] = {"primary": row, "extension_area": ext, "worst_area": base}
        headline.append(
            [
                direction,
                f"{1000 * ext:.5f}",
                f"{1000 * base:.5f}",
                f"{1e5 * delta:+.4f}",
                f"[{1e5 * float(row['conditional_low']):+.4f}, "
                f"{1e5 * float(row['conditional_high']):+.4f}]",
                f"{100 * float(row['relative_change']):+.4f}",
            ]
        )
        for reference in ("worst_query", "mean_query"):
            item = next(
                r
                for r in comparisons
                if r["run"] == name
                and r["policy"] == "bias_aware"
                and r["reference"] == reference
                and r["backbone"] == "ridge_cv"
            )
            all_effects.append(
                (direction + " vs " + ("worst" if reference == "worst_query" else "mean"), item)
            )
        for reference in ("strongest_development_point", "strongest_paid_development_point"):
            item = next(
                r for r in references if r["run"] == name and r["reference_selection"] == reference
            )
            reference_rows.append(
                [
                    direction,
                    "Zero"
                    if reference == "strongest_development_point"
                    else "Reliability/CV ridge",
                    f"{100 * float(item['relative_change']):+.3f}",
                    f"{1e5 * float(item['paired_difference']):+.3f}",
                    f"[{1e5 * float(item['conditional_query_low']):+.3f}, "
                    f"{1e5 * float(item['conditional_query_high']):+.3f}]",
                ]
            )
        axis = figure.add_subplot(grid[0, number])
        for policy, label in policy_labels.items():
            rows = sorted(
                (
                    r
                    for r in curves
                    if r["run"] == name and r["policy"] == policy and r["backbone"] == "ridge_cv"
                ),
                key=lambda r: int(r["budget"]),
            )
            axis.plot(
                [int(r["budget"]) for r in rows],
                [float(r["mse"]) for r in rows],
                "o-",
                label=label,
                color=colors[policy],
                markersize=3,
            )
        zero = next(a["mse_area"] for a in run["areas"] if a["backbone"] == "zero")
        noise = float(next(r["assessment_noise_floor"] for r in curves if r["run"] == name))
        axis.axhline(zero, color="black", linestyle="--", label="Zero effect")
        axis.axhline(noise, color="gray", linestyle=":", label="Assessment variance estimate")
        axis.set(
            title=direction,
            xlabel="Incremental recipient cost",
            ylabel="Full-gene MSE",
            xticks=[128, 256, 512],
        )
        axis.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
        macro(prefix + "NoisePercent", f"{100 * noise / zero:.2f}")
        for suffix, table_rows, field in [
            ("Rank", ranking, "fixed_gene_rank_score"),
            ("Cosine", coordinates, "direction_cosine"),
        ]:
            value = float(
                next(
                    r[field]
                    for r in table_rows
                    if r["run"] == name
                    and r["policy"] == "bias_aware"
                    and r["budget"] == "512"
                    and r["backbone"] == "ridge_cv"
                )
            )
            macro(prefix + suffix, f"{value:.5f}")
        registry[prefix]["zero_area"] = zero
        registry[prefix]["noise_floor"] = noise
        areas = {(r["policy"], r["backbone"]): r["mse_area"] for r in run["areas"]}
        policies = list(dict.fromkeys(r["policy"] for r in run["areas"]))
        matrix = [
            [POLICY_LABELS[policy]] + [f"{1000 * areas[policy, b]:.3f}" for b in BACKBONES]
            for policy in policies
        ]
        (args.output / f"{prefix.lower()}-all-backbones.tex").write_text(
            tabular(
                [
                    "Policy",
                    "Zero",
                    "Mean",
                    "Copy",
                    "Affine",
                    "Ridge",
                    "CV",
                    "Residual",
                    "Local",
                    "Recon.",
                ],
                matrix,
                "lrrrrrrrrr",
            ),
            encoding="utf-8",
        )
    for i, (_label, row) in enumerate(all_effects):
        point = 1e5 * float(row["paired_difference"])
        low, high = 1e5 * float(row["conditional_low"]), 1e5 * float(row["conditional_high"])
        effect_axis.plot([low, high], [i, i], color="#0072B2", linewidth=2)
        effect_axis.plot(point, i, "o", color="#0072B2", markersize=4)
    effect_axis.axvline(0, linestyle="--", color="gray", linewidth=0.8)
    effect_axis.set(
        yticks=range(4),
        yticklabels=[a[0] for a in all_effects],
        xlabel=r"Extension minus reference: error area ($10^{-5}$)",
    )
    effect_axis.invert_yaxis()
    handles, labels = figure.axes[1].get_legend_handles_labels()
    figure.legend(handles, labels, loc="outside upper center", ncols=2, fontsize=8.5)
    save(figure, "primary-results")
    (args.output / "primary-comparison.tex").write_text(
        tabular(
            ["Direction", "$A_E$", "$A_W$", r"$\Delta$", "Query range", r"Change (\%)"],
            headline,
            "lrrrrr",
        ),
        encoding="utf-8",
    )
    (args.output / "development-references.tex").write_text(
        tabular(
            ["Direction", "Development reference", r"Change (\%)", r"$\Delta$", "Query range"],
            reference_rows,
            "llrrr",
        ),
        encoding="utf-8",
    )
    controlled_rows = [
        r
        for r in studies["summary"]["comparisons"]
        if r["policy"] == "bias_aware" and r["backbone"] == "ridge_cv"
    ]
    if len(controlled_rows) != 14:
        raise ValueError("Incomplete original controlled scenario matrix")
    (args.output / "controlled-scenarios.tex").write_text(
        tabular(
            ["Scenario", "$A_E$", r"$\Delta$", r"MC SE($\Delta$)", r"Change (\%)"],
            [
                [
                    SCENARIO_LABELS[r["scenario"]],
                    f"{r['mean_true_error_area']:.5f}",
                    f"{r['paired_difference']:+.5f}",
                    f"{r['monte_carlo_standard_error']:.5f}",
                    f"{100 * r['relative_error_change']:+.3f}",
                ]
                for r in controlled_rows
            ],
            "lrrrr",
        ),
        encoding="utf-8",
    )
    selected_scenarios = [
        "baseline",
        "mechanism_shift_2",
        "source_feature_error_one",
        "batch_shift_one",
        "rank_missing",
        "exact_rank_missing",
    ]
    intervals = []
    for scenario in selected_scenarios:
        rows = [
            r
            for r in interval
            if r["scope"] == "controlled_truth"
            and r["scenario"] == scenario
            and r["policy"] == "worst_query"
            and r["budget"] == "192"
        ]
        if len(rows) != 5:
            raise ValueError("Missing known-truth interval worlds")
        values = []
        for field in [
            "coverage_or_compatibility_90",
            "coverage_or_compatibility_95",
            "mean_width_90",
            "mean_width_95",
        ]:
            available = [float(r[field]) for r in rows if r[field]]
            values.append(f"{np.mean(available):.4f}" if available else "Undefined")
        intervals.append(
            [
                SCENARIO_LABELS[scenario],
                *values,
                f"{sum(int(r['finite_query_seed_intervals']) for r in rows)}/150",
            ]
        )
    (args.output / "interval-diagnostics.tex").write_text(
        tabular(
            ["Scenario", r"90\%", r"95\%", "Width90", "Width95", "Finite"], intervals, "lrrrrr"
        ),
        encoding="utf-8",
    )
    case_index = read_json(retained(controlled, "case-index.json", controlled_index))
    support = []
    archive_path = retained(controlled, "per-query-metrics.zip", controlled_index)
    with zipfile.ZipFile(archive_path) as archive:
        for scenario in ["exact_rank_full", "exact_rank_missing", "rank_missing"]:
            estimated, oracle = [], []
            for seed in range(71, 76):
                name = f"world-{seed}/{scenario}/truth-metrics.csv"
                payload = archive.read(name)
                if hashlib.sha256(payload).hexdigest() != case_index["metric-member-sha256"][name]:
                    raise ValueError("Controlled support member changed")
                for row in csv.DictReader(io.StringIO(payload.decode("utf-8"))):
                    if (
                        row["policy"] == "worst_query"
                        and row["backbone"] == "ridge"
                        and row["budget"] == "192"
                    ):
                        for key in (
                            "estimated_linear_identified",
                            "oracle_latent_linear_identified",
                        ):
                            if row[key] not in ("True", "False"):
                                raise ValueError("Unexpected boolean encoding in retained support")
                        estimated.append(int(row["estimated_linear_identified"] == "True"))
                        oracle.append(int(row["oracle_latent_linear_identified"] == "True"))
            if len(estimated) != 150:
                raise ValueError("Unexpected support denominator")
            support.append(
                {
                    "scenario": scenario,
                    "estimated": sum(estimated),
                    "oracle": sum(oracle),
                    "total": 150,
                }
            )
    registry["controlled_support"] = support
    f, axes = plt.subplots(2, 1, figsize=(6.5, 5.4), layout="constrained")
    x = np.arange(3)
    axes[0].bar(
        x - 0.18,
        [r["estimated"] / 150 for r in support],
        0.36,
        label="Estimated source coordinates",
        color="#0072B2",
    )
    axes[0].bar(
        x + 0.18,
        [r["oracle"] / 150 for r in support],
        0.36,
        label="Oracle latent coordinates",
        color="#D55E00",
    )
    axes[0].set(
        xticks=x,
        xticklabels=[
            "Exact source\nfull calibration",
            "Exact source\nmissing direction",
            "Noisy source\nmissing direction",
        ],
        ylabel="Supported fraction",
        ylim=(0, 1.17),
    )
    axes[0].legend(fontsize=8, ncols=2, loc="upper center")
    for i, key in enumerate(["coverage_or_compatibility_90", "coverage_or_compatibility_95"]):
        averages = []
        for scenario in selected_scenarios[:3]:
            rows = [
                r
                for r in interval
                if r["scope"] == "controlled_truth"
                and r["scenario"] == scenario
                and r["policy"] == "worst_query"
                and r["budget"] == "192"
            ]
            averages.append(np.mean([float(r[key]) for r in rows]))
        axes[1].bar(
            x + (-0.18 if i == 0 else 0.18),
            averages,
            0.36,
            label=["90% diagnostic", "95% diagnostic"][i],
            color=["#0072B2", "#D55E00"][i],
        )
        axes[1].axhline(
            [0.9, 0.95][i], color=["#0072B2", "#D55E00"][i], linestyle="--", linewidth=0.8
        )
    axes[1].set(
        xticks=x,
        xticklabels=["Baseline", "Nonlinear shift", "Source error SD1"],
        ylabel="Known-truth coverage",
        ylim=(0, 1.05),
    )
    axes[1].legend(fontsize=8, ncols=2, loc="lower left")
    save(f, "support-and-coverage")
    review = Path("docs/results/publication-review-v1")
    for relative in [
        "reconstruction-gate-audit/summary.json",
        "pilot-span-audit.json",
        "original-influence/summary.json",
        "original-influence/signal-noise-context.csv",
        "robustness-influence.json",
    ]:
        evidence(review / relative)
    contributions_path = evidence(review / "original-influence/per-query-influence.csv")
    contributions = table(contributions_path)
    f, axes = plt.subplots(2, 2, figsize=(6.7, 4.8), layout="constrained")
    for number, run in enumerate(run_info):
        for column, reference in enumerate(("worst_query", "mean_query")):
            values = np.array(
                [
                    float(r["paired_area_difference_seed_mean"])
                    for r in contributions
                    if r["run"] == run["run"] and r["reference"] == reference
                ]
            )
            if len(values) != 131:
                raise ValueError("Incomplete influence figure")
            axis = axes[number, column]
            axis.hist(values, bins=25, color="#0072B2")
            axis.axvline(0, color="black", linewidth=0.8)
            axis.axvline(values.mean(), color="#D55E00", label="Mean")
            axis.set(
                title=run["source_context"]
                + r"$\to$"
                + run["target_context"]
                + "\nvs classical "
                + ("worst query" if column == 0 else "mean query"),
                xlabel="Paired error-area difference",
                ylabel="Queries",
            )
            axis.ticklabel_format(axis="x", style="sci", scilimits=(0, 0))
            axis.legend(fontsize=8.5)
    save(f, "query-contributions")
    figure_sources["query-contributions.pdf"] = contributions_path.as_posix()
    ranking_rows = []
    for run in run_info:
        name = run["run"]
        direction = run["source_context"] + r"$\to$" + run["target_context"]
        for backbone, label in [
            ("zero", "Zero"),
            ("source_copy", "Source copy"),
            ("ridge_cv", "Paid ridge"),
            ("recipient_local_lowrank", "Local network"),
            ("perturbmap_reconstruction", "Reconstruction"),
        ]:
            rank_row = next(
                r
                for r in ranking
                if r["run"] == name
                and r["policy"] == "bias_aware"
                and r["budget"] == "512"
                and r["backbone"] == backbone
            )
            error_row = next(
                r
                for r in coordinates
                if r["run"] == name
                and r["policy"] == "bias_aware"
                and r["budget"] == "512"
                and r["backbone"] == backbone
            )
            ranking_rows.append(
                [
                    direction,
                    label,
                    f"{1000 * float(error_row['mse']):.4f}",
                    f"{float(rank_row['fixed_gene_rank_score']):.5f}",
                    f"{float(rank_row['permuted_fixed_gene_rank_score']):.5f}",
                    f"{float(rank_row['defined_gene_seed_fraction']):.2f}",
                ]
            )
    (args.output / "ranking-and-absolute.tex").write_text(
        tabular(
            ["Direction", "Predictor", "MSE", "Rank score", "Permuted", "Defined"],
            ranking_rows,
            "llrrrr",
        ),
        encoding="utf-8",
    )
    uncertainty_rows = []
    uncertainty_registry = []
    for run in run_info:
        report = read_json(p("uncertainty/" + run["run"] + "-vs-worst_query.json"))
        for key, label in [
            ("query_bootstrap_conditional_on_bank", "Queries; fixed bank"),
            ("iid_cell_bootstrap_fixed_queries", "Cells; fixed queries"),
            ("stratified_cell_bootstrap_fixed_queries", "Stratified cells"),
            ("batch_reweighting_sensitivity", "Technical-batch weights"),
        ]:
            values = report[key]
            uncertainty_rows.append(
                [
                    run["source_context"] + r"$\to$" + run["target_context"],
                    label,
                    scaled_range(values["percentile_low"], values["percentile_high"], 4),
                ]
            )
            uncertainty_registry.append({"run": run["run"], "scope": key, **values})
    (args.output / "uncertainty-scopes.tex").write_text(
        tabular(["Direction", "Scope", "Conditional range"], uncertainty_rows, "llr"),
        encoding="utf-8",
    )
    registry["uncertainty_scopes"] = uncertainty_registry
    if args.robustness is not None:
        robust_index = read_json(evidence(args.robustness / "retained-artifacts.json"))["sha256"]
        for relative, expected in robust_index.items():
            if file_hash(evidence(args.robustness.parent / relative)) != expected:
                raise ValueError("Changed robustness artifact: " + relative)
        robust = read_json(evidence(args.robustness / "summary.json"))
        if (
            robust["state"] != "complete"
            or robust["matrix_cells_count"] != 8
            or robust["prediction_checkpoints"] != 360
            or robust["paired_contrasts"] != 32
        ):
            raise ValueError("Robustness analysis has incomplete scientific scope")
        for grid_name in ("original_grid", "full_grid"):
            rows = []
            for cell in robust["matrix_cells"]:
                choices = {
                    row["reference"]: row for row in cell["comparisons"] if row["grid"] == grid_name
                }
                worst, mean = choices["worst_query"], choices["mean_query"]
                rows.append(
                    [
                        worst["source_context"] + r"$\to$" + worst["target_context"],
                        str(worst["split_seed"])[-2:],
                        str(worst["rank"]),
                        f"{1e5 * worst['paired_difference']:+.3f}",
                        scaled_range(
                            worst["conditional_query_low"], worst["conditional_query_high"]
                        ),
                        f"{1e5 * mean['paired_difference']:+.3f}",
                        scaled_range(mean["conditional_query_low"], mean["conditional_query_high"]),
                    ]
                )
            (args.output / ("robustness-" + grid_name + ".tex")).write_text(
                tabular(
                    [
                        "Direction",
                        "Split",
                        "Rank",
                        r"$\Delta_W$",
                        "Query range",
                        r"$\Delta_M$",
                        "Query range",
                    ],
                    rows,
                    "lrrrrrr",
                ),
                encoding="utf-8",
            )
        for suffix in ("pdf", "png", "svg"):
            original_figure = evidence(args.robustness / ("robustness-matrix." + suffix))
            shutil.copyfile(original_figure, args.figures / original_figure.name)
            figure_sources[original_figure.name] = original_figure.as_posix()
        absolute_rows = []
        for cell in robust["matrix_cells"]:
            comparison = cell["comparisons"][0]
            areas = cell["areas"]["full_grid"]
            absolute_rows.append(
                [
                    comparison["source_context"] + r"$\to$" + comparison["target_context"],
                    str(comparison["split_seed"])[-2:],
                    str(comparison["rank"]),
                    *[
                        f"{1000 * areas[policy]:.5f}"
                        for policy in ("bias_aware", "worst_query", "mean_query", "zero")
                    ],
                    f"{100 * (areas['bias_aware'] / areas['zero'] - 1):+.3f}",
                ]
            )
        (args.output / "robustness-absolute.tex").write_text(
            tabular(
                [
                    "Direction",
                    "Split",
                    "Rank",
                    r"$A_E$",
                    r"$A_W$",
                    r"$A_M$",
                    r"$A_0$",
                    r"vs zero (\%)",
                ],
                absolute_rows,
                "lrrrrrrr",
            ),
            encoding="utf-8",
        )
        registry["robustness"] = robust
    (args.output / "numbers.tex").write_text("\n".join(macros) + "\n", encoding="utf-8")
    write_json(args.output / "numerical-registry.json", registry)
    outputs = {
        p.as_posix(): file_hash(p)
        for root in (args.output, args.figures)
        for p in sorted(root.iterdir())
        if p.is_file() and p.name != "asset-manifest.json"
    }
    write_json(
        args.output / "asset-manifest.json",
        {
            "state": "complete" if args.robustness is not None else "core_only_robustness_pending",
            "recorded_at": utc_now(),
            "generator_sha256": file_hash(Path(__file__)),
            "input_sha256": inputs,
            "output_sha256": outputs,
            "copied_figure_sources": figure_sources,
            "qualification": (
                "Primary frozen results unchanged; later influence/gate/robustness analyses "
                "explicitly post-primary."
            ),
        },
    )
    print(
        "Generated manuscript numerical registry, tables and figures; robustness included",
        args.robustness is not None,
    )


if __name__ == "__main__":
    main()
