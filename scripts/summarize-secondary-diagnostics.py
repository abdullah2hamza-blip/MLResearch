"""Validate legacy95 fields and summarize secondary metrics without changing primary tests."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np

from mlresearch.experiment import _write_csv
from mlresearch.provenance import file_hash, read_json, utc_now, write_json


def metric_points(binary, expected_sha: str, coverage: str, error: str) -> dict:
    checksum = hashlib.sha256()

    def lines():
        for line in binary:
            checksum.update(line)
            yield line.decode("utf-8")

    result = defaultdict(lambda: np.zeros(4))
    for row in csv.DictReader(lines()):
        if row["backbone"] == "ridge":
            result[row["policy"], row["seed"], row["budget"]] += (
                float(row[coverage] or 0),
                bool(row[coverage]),
                float(row[error]),
                1,
            )
    if checksum.hexdigest() != expected_sha:
        raise ValueError("Retained legacy metric bytes changed")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supplement", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--controlled", type=Path, required=True)
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Secondary summary output exists")
    diagnostic = args.supplement / "frozen-diagnostics-complete"
    summary = read_json(diagnostic / "summary.json")
    ranking = args.supplement / "ranking"
    rank_summary = read_json(ranking / "summary.json")
    if summary["state"] != "complete" or rank_summary["state"] != "complete":
        raise ValueError("Complete every secondary diagnostic before summarizing")
    if (
        file_hash(ranking / "within-gene-perturbation-ranking.csv")
        != rank_summary["ranking_csv_sha256"]
    ):
        raise ValueError("Ranking table changed")
    legacy = {}
    member_index = read_json(args.controlled / "case-index.json")["metric-member-sha256"]
    with zipfile.ZipFile(args.controlled / "per-query-metrics.zip") as archive:
        for binding in summary["runs"]:
            prefix = tuple(
                str(binding[k]) if binding[k] is not None else ""
                for k in ("scope", "scenario", "generative_seed", "run")
            )
            if binding["scope"] == "controlled_truth":
                member = (
                    f"world-{binding['generative_seed']}/{binding['scenario']}/truth-metrics.csv"
                )
                with archive.open(member) as stream:
                    points = metric_points(
                        stream,
                        member_index[member],
                        "gaussian_true_coverage_diagnostic",
                        "true_mse",
                    )
            else:
                retained = args.primary / "runs" / binding["run"]
                receipt = read_json(retained / "retained-artifacts.json")
                if file_hash(retained / "run-manifest.json") != binding["run_manifest_sha256"]:
                    raise ValueError("Retained run manifest changed")
                with gzip.open(retained / "metrics.csv.gz", "rb") as stream:
                    points = metric_points(
                        stream,
                        receipt["metrics_uncompressed_sha256"],
                        "gaussian_coverage_diagnostic",
                        "mse",
                    )
            legacy.update({(*prefix, *key): value for key, value in points.items()})
    interval, coordinates, seen = (
        defaultdict(lambda: np.zeros(8)),
        defaultdict(lambda: np.zeros(12)),
        set(),
    )
    with (diagnostic / "coordinate-and-interval-diagnostics.csv").open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            prefix = tuple(row[k] for k in ("scope", "scenario", "generative_seed", "run"))
            point = (*prefix, row["policy"], row["seed"], row["budget"])
            group = (*prefix, row["policy"], row["budget"])
            key = (*group, row["backbone"])
            coordinates[key] += (
                float(row["mse"]),
                float(row["scoring_gene_permuted_mse"]),
                float(row["sign_agreement_including_explicit_zero_ties"]),
                float(row["prediction_nonzero_fraction"]),
                1,
                float(row["direction_cosine"] or 0) * int(row["direction_cosine_defined_queries"]),
                int(row["direction_cosine_defined_queries"]),
                float(row["response_specific_cosine"] or 0)
                * int(row["response_specific_cosine_defined_queries"]),
                int(row["response_specific_cosine_defined_queries"]),
                float(row["within_query_gene_pearson"] or 0)
                * int(row["within_query_gene_pearson_defined_queries"]),
                int(row["within_query_gene_pearson_defined_queries"]),
                0,
            )
            if row["backbone"] != "ridge":
                continue
            if point not in legacy or point in seen:
                raise ValueError("Missing or duplicate95% legacy comparison")
            seen.add(point)
            old = legacy[point]
            n = int(row["finite_queries_95"])
            if n != old[1] or (
                n
                and not np.isclose(
                    float(row["coverage_or_compatibility_95"]), old[0] / n, atol=1e-12
                )
            ):
                raise ValueError("Supplementary95% fields disagree with the original scorer")
            if not np.isclose(float(row["mse"]), old[2] / old[3], atol=1e-12, rtol=1e-10):
                raise ValueError("Supplementary fixed-ridge MSE differs from the original scorer")
            if int(row["finite_queries_90"]) != n:
                raise ValueError("Nominal levels changed the finite-width denominator")
            interval[group] += (
                float(row["coverage_or_compatibility_90"] or 0) * n,
                float(row["mean_width_90"] or 0) * n,
                n,
                float(row["coverage_or_compatibility_95"] or 0) * n,
                float(row["mean_width_95"] or 0) * n,
                n,
                old[3],
                1,
            )
    if seen != set(legacy):
        raise ValueError("Legacy95% verification does not cover every original checkpoint")
    names = ("scope", "scenario", "generative_seed", "run", "policy", "budget")
    interval_rows = [
        {
            **dict(zip(names, k, strict=True)),
            "finite_query_seed_intervals": int(v[2]),
            "total_query_seed_observations": int(v[6]),
            "finite_fraction": float(v[2] / v[6]),
            "coverage_or_compatibility_90": float(v[0] / v[2]) if v[2] else None,
            "mean_width_90": float(v[1] / v[2]) if v[2] else None,
            "coverage_or_compatibility_95": float(v[3] / v[5]) if v[5] else None,
            "mean_width_95": float(v[4] / v[5]) if v[5] else None,
            "acquisition_seeds": int(v[7]),
        }
        for k, v in sorted(interval.items())
    ]
    coordinate_rows = [
        {
            **dict(zip((*names, "backbone"), k, strict=True)),
            "mse": float(v[0] / v[4]),
            "scoring_gene_permuted_mse": float(v[1] / v[4]),
            "sign_agreement_including_zero_ties": float(v[2] / v[4]),
            "prediction_nonzero_fraction": float(v[3] / v[4]),
            "acquisition_seeds": int(v[4]),
            "direction_cosine": float(v[5] / v[6]) if v[6] else None,
            "direction_defined_query_seed_observations": int(v[6]),
            "response_specific_cosine": float(v[7] / v[8]) if v[8] else None,
            "response_specific_defined_query_seed_observations": int(v[8]),
            "within_query_gene_pearson": float(v[9] / v[10]) if v[10] else None,
            "pearson_defined_query_seed_observations": int(v[10]),
        }
        for k, v in sorted(coordinates.items())
    ]
    ranks = defaultdict(lambda: np.zeros(8))
    with (ranking / "within-gene-perturbation-ranking.csv").open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            key = tuple(row[k] for k in (*names, "backbone"))
            n, m = (
                int(row["original_defined_genes"]),
                int(row["scoring_gene_permutation_defined_genes"]),
            )
            ranks[key] += (
                float(row["original_fixed_gene_score"]),
                float(row["original_mean_defined_spearman"] or 0) * n,
                n,
                float(row["scoring_gene_permutation_fixed_gene_score"]),
                float(row["scoring_gene_permutation_mean_defined_spearman"] or 0) * m,
                m,
                int(row["declared_genes"]),
                1,
            )
    rank_rows = [
        {
            **dict(zip((*names, "backbone"), k, strict=True)),
            "fixed_gene_rank_score": float(v[0] / v[7]),
            "conditional_defined_spearman": float(v[1] / v[2]) if v[2] else None,
            "defined_gene_seed_fraction": float(v[2] / v[6]),
            "permuted_fixed_gene_rank_score": float(v[3] / v[7]),
            "permuted_conditional_spearman": float(v[4] / v[5]) if v[5] else None,
            "permuted_defined_gene_seed_fraction": float(v[5] / v[6]),
            "acquisition_seeds": int(v[7]),
        }
        for k, v in sorted(ranks.items())
    ]
    with args.development.open(encoding="utf-8") as stream:
        development = list(csv.DictReader(stream))
    candidates = sorted(
        (float(value), row["policy"], model)
        for row in development
        for model, value in row.items()
        if model != "policy"
    )
    best, paid = candidates[0], next(p for p in candidates if p[2] not in ("zero", "source_copy"))
    references = {
        "strongest_development_point": (best[1], best[2]),
        "strongest_paid_development_point": (paid[1], paid[2]),
        "selected_fixed_grid": ("fixed_grid", "ridge_cv"),
        "shared_mean": ("bias_aware", "mean"),
    }
    main = read_json(args.primary / "supplement" / "summary.json")
    comparisons = []
    for run in [r for r in main["runs"] if r["source_control"] == "none"]:
        directory = args.primary / "runs" / run["run"]
        if (
            file_hash(directory / "areas-by-query-seed.csv")
            != read_json(directory / "retained-artifacts.json")["sha256"]["areas-by-query-seed.csv"]
        ):
            raise ValueError("Retained query areas changed")
        wanted = {("bias_aware", "ridge_cv"), *references.values()}
        areas = defaultdict(dict)
        with (directory / "areas-by-query-seed.csv").open(encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                if (row["policy"], row["backbone"]) in wanted:
                    key = row["policy"], row["backbone"], row["query"]
                    seed = int(row["seed"])
                    if seed in areas[key]:
                        raise ValueError("Duplicated paired acquisition seed")
                    areas[key][seed] = float(row["normalized_area"])
        queries = sorted({q for p, b, q in areas if (p, b) == ("bias_aware", "ridge_cv")})
        vectors = {}
        for p, b in wanted:
            if any(set(areas[p, b, q]) != set(range(5)) for q in queries):
                raise ValueError("Incomplete paired baseline/query/seed grid")
            vectors[p, b] = np.array([np.mean(list(areas[p, b, q].values())) for q in queries])
        rng = np.random.default_rng(20261022)
        indices = rng.integers(0, len(queries), size=(2000, len(queries)))
        for label, reference in references.items():
            baseline = vectors[reference]
            delta = vectors["bias_aware", "ridge_cv"] - baseline
            band = np.quantile(delta[indices].mean(axis=1), [0.025, 0.975])
            comparisons.append(
                {
                    "run": run["run"],
                    "reference_selection": label,
                    "reference_policy": reference[0],
                    "reference_backbone": reference[1],
                    "extension_area": float(vectors["bias_aware", "ridge_cv"].mean()),
                    "reference_area": float(baseline.mean()),
                    "paired_difference": float(delta.mean()),
                    "relative_change": float(delta.mean() / baseline.mean())
                    if baseline.mean()
                    else None,
                    "conditional_query_low": float(band[0]),
                    "conditional_query_high": float(band[1]),
                    "queries": len(queries),
                    "acquisition_seeds": 5,
                }
            )
    args.output.mkdir(parents=True)
    for name, rows in (
        ("intervals-by-world.csv", interval_rows),
        ("coordinate-metrics-by-world.csv", coordinate_rows),
        ("ranking-by-world.csv", rank_rows),
        ("development-reference-comparisons.csv", comparisons),
    ):
        _write_csv(args.output / name, rows)
    write_json(
        args.output / "summary.json",
        {
            "state": "complete",
            "recorded_at": utc_now(),
            "analysis_source_sha256": file_hash(Path(__file__)),
            "legacy95_checkpoint_comparisons_passed": len(seen),
            "development_table_sha256": file_hash(args.development),
            "development_best": best,
            "development_best_paid": paid,
            "bootstrap_samples": 2000,
            "bootstrap_seed": 20261022,
            "input_sha256": {
                str(p): file_hash(p)
                for p in [
                    diagnostic / "summary.json",
                    diagnostic / "coordinate-and-interval-diagnostics.csv",
                    ranking / "summary.json",
                    ranking / "within-gene-perturbation-ranking.csv",
                ]
            },
            "qualification": [
                "All supplements are post-primary; original worst-query comparison is unchanged.",
                "References use development points, with no external performance selection.",
                "Query bands condition on the bank; no biological or combined interval claim.",
                "Tables retain worlds; correlated genes/seeds do not add replication.",
                "Fixed-gene rank scores use neutral0 for undefined genes; "
                "conditional correlations and denominators remain explicit.",
            ],
        },
    )
    print(
        "Verified legacy95% diagnostics at",
        len(seen),
        "checkpoints; secondary tables complete",
        flush=True,
    )


if __name__ == "__main__":
    main()
