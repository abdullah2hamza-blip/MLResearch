import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from mlresearch.provenance import file_hash, read_json, utc_now, write_json

run = Path("runs/frangieh-tuning-v1")
manifest = read_json(run / "manifest.json")
if manifest["state"] != "complete":
    raise ValueError("Tuning run not complete")
declaration = read_json(Path("docs/evidence/development-tuning-declaration.json"))
assert file_hash(Path("docs/development-tuning-protocol.md")) == declaration["protocol_sha256"]
assert file_hash(Path("configs/run-frangieh-tuning-v1.json")) == declaration["configuration_sha256"]
assert file_hash(run / "metrics.csv") == manifest["results_sha256"]
grouped = defaultdict(lambda: defaultdict(list))
with (run / "metrics.csv").open(encoding="utf-8", newline="") as stream:
    for row in csv.DictReader(stream):
        if row["backbone"] == "ridge_cv":
            grouped[row["policy"]][int(row["budget"])].append(float(row["mse"]))
budgets = manifest["configuration"]["budgets"]
areas = {
    name: float(
        np.trapezoid([np.mean(rows[b]) for b in budgets], budgets) / (budgets[-1] - budgets[0])
    )
    for name, rows in grouped.items()
}
fixed_order = [
    ("fixed_grid", 0.25, 8),
    ("fixed_cf125_d8", 0.125, 8),
    ("fixed_cf500_d8", 0.5, 8),
    ("fixed_cf250_d16", 0.25, 16),
    ("fixed_cf125_d16", 0.125, 16),
    ("fixed_cf500_d16", 0.5, 16),
    ("fixed_cf250_d32", 0.25, 32),
    ("fixed_cf125_d32", 0.125, 32),
    ("fixed_cf500_d32", 0.5, 32),
]
bias_order = [
    ("worst_query", 0.0),
    ("bias_gamma001", 0.01),
    ("bias_gamma01", 0.1),
    ("bias_aware", 0.25),
    ("bias_gamma1", 1.0),
]
best_fixed = min(areas[item[0]] for item in fixed_order)
best_bias = min(areas[item[0]] for item in bias_order)
fixed = next(item for item in fixed_order if areas[item[0]] <= best_fixed + 1e-12)
bias = next(item for item in bias_order if areas[item[0]] <= best_bias + 1e-12)
choices = defaultdict(Counter)
index = read_json(run / "prediction-index.json")
assert file_hash(run / "prediction-index.json") == manifest["predictions_sha256"]
for item in index:
    path = run / item["artifact"]
    assert file_hash(path) == item["sha256"]
    with np.load(path, allow_pickle=False) as arrays:
        choices[item["policy"]][str(float(arrays["ridge_cv_selected"]))] += 1
write_json(
    Path("docs/evidence/development-tuning-selection.json"),
    {
        "recorded_at": utc_now(),
        "selection_scope": "Development only; not confirmatory",
        "run_manifest_sha256": file_hash(run / "manifest.json"),
        "protocol_sha256": declaration["protocol_sha256"],
        "configuration_sha256": declaration["configuration_sha256"],
        "primary_backbone": "ridge_cv",
        "normalized_error_areas": areas,
        "tie_tolerance": 1e-12,
        "selected_fixed_grid": {
            "policy": fixed[0],
            "fixed_control_fraction": fixed[1],
            "fixed_depth": fixed[2],
            "development_area": areas[fixed[0]],
        },
        "selected_discrepancy": {
            "policy": bias[0],
            "weight": bias[1],
            "development_area": areas[bias[0]],
        },
        "paid_ridge_cv_choices": {name: dict(counts) for name, counts in choices.items()},
        "zero_choice_sentinel": -1,
        "candidate_table_complete": len(areas) == len(manifest["configuration"]["policies"]),
        "script_sha256": file_hash(Path(__file__)),
    },
)
print(
    json.dumps(
        {
            "selected_fixed_grid": fixed,
            "selected_discrepancy": bias,
            "areas": areas,
            "paid_ridge_cv_choices": {name: dict(counts) for name, counts in choices.items()},
        },
        indent=2,
    )
)
