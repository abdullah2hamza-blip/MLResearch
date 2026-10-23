"""Descriptive query influence, acquisition-seed variation and signal/noise context."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mlresearch.experiment import _write_csv  # noqa: E402
from mlresearch.provenance import file_hash, read_json, utc_now, write_json  # noqa: E402


def table(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("docs/results/external-evaluation-v1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve an existing influence analysis")
    index = read_json(args.results / "supplement-artifacts.json")
    inputs = {}

    def authenticated(relative: str) -> Path:
        path = args.results / relative
        if file_hash(path) != index["sha256"][relative]:
            raise ValueError(f"Retained input changed: {path}")
        inputs[relative] = file_hash(path)
        return path

    original = read_json(authenticated("supplement/summary.json"))
    comparisons = table(authenticated("supplement/paired-primary-comparisons.csv"))
    curves = table(authenticated("supplement/curves-and-specificity.csv"))
    strata = table(authenticated("supplement/public-source-strata.csv"))
    primary = [r for r in original["runs"] if r["source_control"] == "none"]
    records, per_query, seed_rows, context, retained_strata = [], [], [], [], []
    figure, axes = plt.subplots(2, 2, figsize=(10, 6.5), layout="constrained")
    for number, run in enumerate(primary):
        name = run["run"]
        areas = defaultdict(dict)
        for row in table(authenticated(f"runs/{name}/areas-by-query-seed.csv")):
            if row["backbone"] == "ridge_cv":
                areas[row["policy"], row["query"]][int(row["seed"])] = float(row["normalized_area"])
        queries = sorted(q for policy, q in areas if policy == "bias_aware")
        if len(queries) != 131:
            raise ValueError("Unexpected primary query count")
        for column, reference in enumerate(("worst_query", "mean_query")):
            if any(
                set(areas[policy, q]) != set(range(5))
                for policy in ("bias_aware", reference)
                for q in queries
            ):
                raise ValueError("Incomplete query/acquisition-seed pairing")
            matrix = np.array(
                [
                    [areas["bias_aware", q][s] - areas[reference, q][s] for s in range(5)]
                    for q in queries
                ]
            )
            differences = matrix.mean(axis=1)
            mean = float(differences.mean())
            frozen = next(
                r
                for r in comparisons
                if r["run"] == name
                and r["policy"] == "bias_aware"
                and r["backbone"] == "ridge_cv"
                and r["reference"] == reference
            )
            if not np.isclose(mean, float(frozen["paired_difference"]), atol=1e-14, rtol=1e-10):
                raise ValueError("Influence mean differs from the frozen primary analysis")
            leave_one_out = (len(queries) * mean - differences) / (len(queries) - 1)
            by_seed = matrix.mean(axis=0)
            records.append(
                {
                    "run": name,
                    "reference": reference,
                    "mean_paired_area_difference": mean,
                    "query_quantiles": dict(
                        zip(
                            ["minimum", "p10", "p25", "median", "p75", "p90", "maximum"],
                            np.quantile(differences, [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1]).tolist(),
                            strict=True,
                        )
                    ),
                    "queries_positive": int(np.sum(differences > 0)),
                    "queries_negative": int(np.sum(differences < 0)),
                    "queries_zero": int(np.sum(differences == 0)),
                    "leave_one_query_out_mean_range": [
                        float(leave_one_out.min()),
                        float(leave_one_out.max()),
                    ],
                    "leave_one_query_out_sign_reversals": int(
                        np.sum(np.sign(leave_one_out) != np.sign(mean))
                    ),
                    "acquisition_seed_difference_range": [
                        float(by_seed.min()),
                        float(by_seed.max()),
                    ],
                    "acquisition_seed_difference_sd": float(np.std(by_seed, ddof=1)),
                    "queries": len(queries),
                    "acquisition_seeds": 5,
                }
            )
            for i, q in enumerate(queries):
                per_query.append(
                    {
                        "run": name,
                        "reference": reference,
                        "query": q,
                        "paired_area_difference_seed_mean": float(differences[i]),
                        "leave_one_out_mean_difference": float(leave_one_out[i]),
                    }
                )
            seed_rows.extend(
                {"run": name, "reference": reference, "seed": i, "mean_difference": float(v)}
                for i, v in enumerate(by_seed)
            )
            axis = axes[number, column]
            axis.hist(differences, bins=25, color="#0072B2", alpha=0.8)
            axis.axvline(0, color="black", linewidth=0.8)
            axis.axvline(mean, color="#D55E00", linewidth=1.5, label="Mean")
            reference_label = "classical worst query" if column == 0 else "classical mean query"
            axis.set(
                title=f"{run['source_context']} to {run['target_context']}: vs {reference_label}",
                xlabel="Paired error-area difference",
                ylabel="Query count",
            )
            axis.ticklabel_format(axis="x", style="sci", scilimits=(0, 0))
            axis.legend()
        zero = next(r["mse_area"] for r in run["areas"] if r["backbone"] == "zero")
        extension = next(
            r["mse_area"]
            for r in run["areas"]
            if r["policy"] == "bias_aware" and r["backbone"] == "ridge_cv"
        )
        floors = [float(r["assessment_noise_floor"]) for r in curves if r["run"] == name]
        noise = float(np.mean(floors))
        context.append(
            {
                "run": name,
                "zero_area": zero,
                "extension_ridge_area": extension,
                "plug_in_assessment_noise_floor": noise,
                "floor_fraction_of_zero": noise / zero,
                "relative_improvement_over_zero": (zero - extension) / zero,
                "estimated_excess_zero_error_after_noise_subtraction": zero - noise,
                "estimated_excess_extension_error_after_noise_subtraction": extension - noise,
            }
        )
        retained_strata.extend(
            r
            for r in strata
            if r["run"] == name
            and r["backbone"] == "ridge_cv"
            and r["policy"] in ("bias_aware", "worst_query", "mean_query")
        )
    args.output.mkdir(parents=True)
    for name, rows in (
        ("per-query-influence.csv", per_query),
        ("per-acquisition-seed.csv", seed_rows),
        ("signal-noise-context.csv", context),
        ("frozen-source-strata.csv", retained_strata),
    ):
        _write_csv(args.output / name, rows)
    figure.suptitle("Original frozen comparison: descriptive heterogeneity; no query exclusions")
    for extension in ("pdf", "png", "svg"):
        figure.savefig(
            args.output / f"query-contributions.{extension}",
            bbox_inches="tight",
            metadata={"Date": None} if extension == "svg" else None,
        )
    plt.close(figure)
    write_json(
        args.output / "summary.json",
        {
            "state": "complete",
            "recorded_at": utc_now(),
            "analysis_source_sha256": file_hash(Path(__file__)),
            "input_sha256": inputs,
            "comparisons": records,
            "qualification": [
                "Post-primary descriptive influence; no exclusions, threshold tuning or new tests.",
                "Seeds vary pilot order/ties on fixed cell order, not biological replication.",
                "Query signs/leave-one-out shifts are dependent diagnostics, not significance.",
                "Noise floors are plug-in independent-cell approximations, not known truth.",
                "Source strata retain the original source-only threshold; no recipient selection.",
            ],
        },
    )
    print("Influence/seed/noise/strata summaries complete for both original directions")


if __name__ == "__main__":
    main()
