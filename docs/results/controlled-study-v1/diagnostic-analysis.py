"""Descriptive world-level strata, deferral, interval-width and allocation diagnostics."""

import argparse
import csv
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np

from mlresearch.experiment import _write_csv
from mlresearch.provenance import (
    environment_record,
    file_hash,
    read_json,
    snapshot_sources,
    write_json,
)
from mlresearch.report import risk_retention_rows

parser = argparse.ArgumentParser()
parser.add_argument("--run", type=Path, default=Path("runs/controlled-study-v1"))
parser.add_argument("--output", type=Path, default=Path("docs/results/controlled-study-v1"))
arguments = parser.parse_args()
run, output = arguments.run, arguments.output
output.mkdir(parents=True, exist_ok=True)
manifest = read_json(run / "manifest.json")
assert manifest["state"] == "complete"
assert not (output / "diagnostic-analysis.py").exists()
environment = environment_record()
strata_rows, retention_rows, width_rows, allocation_rows = [], [], [], []
for case in manifest["cases"]:
    case_run = Path(case["run"])
    header = {"scenario": case["scenario"], "world": case["generative_seed"]}
    assert file_hash(case_run / "manifest.json") == case["manifest_sha256"]
    assert file_hash(case_run / "truth-metrics.csv") == case["truth_metrics_sha256"]
    meta = read_json(case_run / "manifest.json")
    assert file_hash(case_run / "metrics.csv") == meta["results_sha256"]
    true = {}
    strata = defaultdict(list)
    with (case_run / "truth-metrics.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["backbone"] == "ridge_cv":
                key = (row["policy"], int(row["budget"]), int(row["seed"]), row["query"])
                true[key] = float(row["true_mse"])
                strata[(key[0], key[1], row["source_stratum"])].append(row)
    for (policy, budget, stratum), rows in strata.items():
        strata_rows.append(
            {
                **header,
                "policy": policy,
                "budget": budget,
                "source_stratum": stratum,
                "query_seed_observations": len(rows),
                "true_mse": float(np.mean([float(row["true_mse"]) for row in rows])),
                "true_specificity_mse": float(
                    np.mean([float(row["true_specificity_mse"]) for row in rows])
                ),
                "source_unstable_fraction": float(
                    np.mean([row["source_unstable"] == "True" for row in rows])
                ),
            }
        )
    risks, widths = defaultdict(list), defaultdict(list)
    with (case_run / "metrics.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            policy, budget = row["policy"], int(row["budget"])
            variance = float(row["ideal_variance"]) if row["ideal_variance"] else np.inf
            if row["backbone"] == "ridge_cv":
                key = (policy, budget, int(row["seed"]))
                risks[key].append(
                    (variance, true[(*key, row["query"])], row["source_unstable"] == "True")
                )
            elif row["backbone"] == "ridge":
                widths[(policy, budget)].append(3.92 * np.sqrt(variance))
    grouped_retention = defaultdict(list)
    for (policy, budget, _seed), values in risks.items():
        for row in risk_retention_rows(policy, budget, "ridge_cv", values):
            grouped_retention[
                (policy, budget, row["criterion"], row["requested_retention"])
            ].append(row)
    for (policy, budget, criterion, requested), rows in grouped_retention.items():
        retained = sum(row["retained_query_seed_observations"] for row in rows)
        total = sum(row["total_query_seed_observations"] for row in rows)
        mse = sum(
            row["mse"] * row["retained_query_seed_observations"]
            for row in rows
            if row["mse"] is not None
        )
        retention_rows.append(
            {
                **header,
                "policy": policy,
                "budget": budget,
                "criterion": criterion,
                "requested_retention": requested,
                "actual_retention": retained / total,
                "retained_query_seed_observations": retained,
                "total_query_seed_observations": total,
                "true_mse": mse / retained if retained else None,
                "empty_acquisition_seeds": sum(row["mse"] is None for row in rows),
            }
        )
    for (policy, budget), values in widths.items():
        finite = [value for value in values if np.isfinite(value)]
        width_rows.append(
            {
                **header,
                "policy": policy,
                "budget": budget,
                "fixed_ridge_true_interval_mean_width_conditional_on_finite": float(np.mean(finite))
                if finite
                else None,
                "finite_query_seed_observations": len(finite),
                "total_query_seed_observations": len(values),
            }
        )
    allocations = defaultdict(list)
    with (case_run / "allocations.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            allocations[(row["policy"], int(row["budget"]))].append(row)
    for (policy, budget), rows in allocations.items():
        allocation_rows.append(
            {
                **header,
                "policy": policy,
                "budget": budget,
                **{
                    field + "_mean": float(np.mean([float(row[field]) for row in rows]))
                    for field in [
                        "spent",
                        "control_cells",
                        "interventions_opened",
                        "perturbed_cells",
                        "variance_prior_scale",
                    ]
                },
                "null_choices": sum(float(row["ridge_cv_selected"]) == -1 for row in rows),
                "acquisition_seeds": len(rows),
            }
        )
for name, rows in [
    ("strata-by-world.csv", strata_rows),
    ("true-risk-retention-by-world.csv", retention_rows),
    ("interval-widths-by-world.csv", width_rows),
    ("allocation-by-world.csv", allocation_rows),
]:
    _write_csv(output / name, rows)
shutil.copyfile(Path(__file__), output / "diagnostic-analysis.py")
snapshot_sources(output / "diagnostic-code.zip", environment["source_hashes"])
write_json(
    output / "diagnostic-analysis.json",
    {
        "environment": environment,
        "script_sha256": file_hash(Path(__file__)),
        "risk_retention_scope": "Select separately within each world/acquisition seed using predictor variance/support only; aggregate retained query-seed error. No labels break ties.",
        "uncertainty_scope": "Descriptive diagnostics. Five independent worlds; query/seed/gene rows are not independent replicates. Fixed-ridge ideal Gaussian widths exclude source/adaptive/structural errors.",
        "sha256": {
            name: file_hash(output / name)
            for name in [
                "strata-by-world.csv",
                "true-risk-retention-by-world.csv",
                "interval-widths-by-world.csv",
                "allocation-by-world.csv",
                "diagnostic-code.zip",
            ]
        },
    },
)
print("Retained strata, retention, interval-width and allocation diagnostics")
