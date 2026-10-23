"""Describe all robustness query influences without excluding queries or changing endpoints."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

from mlresearch.provenance import file_hash, read_json, utc_now, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis", type=Path, default=Path("docs/results/publication-robustness-v1/analysis")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve the original influence analysis")
    index = read_json(args.analysis / "retained-artifacts.json")["sha256"]
    source = args.analysis / "paired-query-areas.csv"
    if file_hash(source) != index["analysis/paired-query-areas.csv"]:
        raise ValueError("Changed paired-query input")
    grouped = defaultdict(list)
    with source.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            grouped[(row["run"], row["grid"], row["reference"])].append(row)
    comparisons = []
    for (run, grid, reference), rows in sorted(grouped.items()):
        if len(rows) != 131 or len({row["query"] for row in rows}) != 131:
            raise ValueError("Expected all 131 unique queries")
        values = np.array([float(row["paired_difference"]) for row in rows])
        mean = float(values.mean())
        leave_one_out = (values.sum() - values) / (len(values) - 1)
        comparisons.append(
            {
                "run": run,
                "grid": grid,
                "reference": reference,
                "queries": len(values),
                "mean_paired_area_difference": mean,
                "median_paired_area_difference": float(np.median(values)),
                "queries_extension_lower_error": int(np.count_nonzero(values < 0)),
                "leave_one_query_out_mean_range": [
                    float(leave_one_out.min()),
                    float(leave_one_out.max()),
                ],
                "leave_one_query_out_sign_reversals": int(
                    np.count_nonzero(np.sign(leave_one_out) != np.sign(mean))
                ),
            }
        )
    if len(comparisons) != 32:
        raise ValueError("Expected every matrix/grid/reference contrast")
    write_json(
        args.output,
        {
            "state": "complete",
            "recorded_at": utc_now(),
            "analysis_source_sha256": file_hash(Path(__file__)),
            "input_sha256": {source.as_posix(): file_hash(source)},
            "comparisons": comparisons,
            "qualification": (
                "Descriptive deletion sensitivity; no query excluded, no new endpoint, "
                "no independence or biological interval claim."
            ),
        },
    )
    print("Analyzed all 32 robustness influence contrasts")


if __name__ == "__main__":
    main()
