"""Authenticate manageable publication evidence without raw data or prediction arrays."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import math
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath

from mlresearch.provenance import file_hash, read_json, utc_now, write_json


def checked(root: Path, hashes: dict) -> int:
    for relative, expected in hashes.items():
        path = root / relative
        if not path.resolve().is_relative_to(root.resolve()) or file_hash(path) != expected:
            raise ValueError("Changed retained artifact: " + str(path))
    return len(hashes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve existing verification records")
    base = Path("docs/results")
    counts = {}
    for name, index in [
        ("external-evaluation-v1", "supplement-artifacts.json"),
        ("secondary-supplement-v1", "supplement-artifacts.json"),
        ("controlled-study-v1", "retained-artifacts.json"),
        ("publication-robustness-v1", "analysis/retained-artifacts.json"),
    ]:
        root = base / name
        counts[name] = checked(root, read_json(root / index)["sha256"])
    archive_count = archive_members = 0
    for folder in (base, Path("docs/evidence")):
        for path in folder.rglob("*.zip"):
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if len(names) != len(set(names)) or archive.testzip() is not None:
                    raise ValueError("ZIP membership/CRC failure: " + str(path))
                for name in names:
                    parts = PurePosixPath(name.replace("\\", "/"))
                    if parts.is_absolute() or ".." in parts.parts or ":" in name:
                        raise ValueError("Unsafe archive member: " + name)
                archive_members += len(names)
                archive_count += 1
    robust_root = base / "publication-robustness-v1"
    robust = read_json(robust_root / "analysis/summary.json")
    if (
        robust["state"] != "complete"
        or robust["prediction_checkpoints"] != 360
        or robust["matrix_cells_count"] != 8
        or robust["paired_contrasts"] != 32
        or robust["authenticated_metric_rows"] != 330120
    ):
        raise ValueError("Incomplete robustness scope")
    for name, run in robust["retained_runs"].items():
        digest = hashlib.sha256()
        with gzip.open(robust_root / "runs" / name / "metrics.csv.gz", "rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != run["metrics_reinflated_sha256"]:
            raise ValueError("Robustness gzip does not reproduce recorded metrics")
        with zipfile.ZipFile(robust_root / "runs" / name / "paid-ledgers.zip") as archive:
            for member, expected in run["ledger_member_sha256"].items():
                if hashlib.sha256(archive.read(member)).hexdigest() != expected:
                    raise ValueError("Robustness nested paid ledger changed")
    grouped = defaultdict(list)
    with (robust_root / "analysis/paired-query-areas.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        for row in csv.DictReader(stream):
            grouped[(row["run"], row["grid"], row["reference"])].append(row)
    for cell in robust["matrix_cells"]:
        for contrast in cell["comparisons"]:
            rows = grouped[(contrast["run"], contrast["grid"], contrast["reference"])]
            if len(rows) != 131 or len({row["query"] for row in rows}) != 131:
                raise ValueError("Missing or duplicate paired queries")
            difference = statistics.mean(
                float(row["extension_area"]) - float(row["reference_area"]) for row in rows
            )
            if not math.isclose(difference, contrast["paired_difference"], abs_tol=1e-14):
                raise ValueError("Paired robustness area cannot be reconstructed")
            relative = difference / statistics.mean(float(row["reference_area"]) for row in rows)
            if not math.isclose(relative, contrast["relative_change"], abs_tol=1e-12):
                raise ValueError("Robustness relative denominator differs")
    reviews = base / "publication-review-v1"
    for name, script in [
        ("reconstruction-gate-audit/summary.json", "audit-reconstruction-gate.py"),
        ("pilot-span-audit.json", "audit-primary-pilot-span.py"),
        ("original-influence/summary.json", "analyze-publication-influence.py"),
        ("robustness-influence.json", "analyze-robustness-influence.py"),
    ]:
        report = read_json(reviews / name)
        if report["analysis_source_sha256"] != file_hash(Path("scripts") / script):
            raise ValueError("Review helper source changed: " + script)
    gate = read_json(reviews / "reconstruction-gate-audit/summary.json")
    if (
        not gate["all_prediction_arrays_unaffected_by_gate_correction"]
        or gate["affected_artifacts_authenticated_and_baseline_byte_equal"] != 20
    ):
        raise ValueError("Gate correction audit incomplete")
    assets = read_json(Path("paper/generated/asset-manifest.json"))
    if assets["state"] != "complete":
        raise ValueError("Manuscript assets omit completed robustness")
    checked(Path("."), assets["input_sha256"])
    checked(Path("."), assets["output_sha256"])
    if assets["generator_sha256"] != file_hash(Path("scripts/generate-paper-assets.py")):
        raise ValueError("Manuscript generator changed after generation")
    write_json(
        args.output,
        {
            "state": "passed",
            "recorded_at": utc_now(),
            "verification_source_sha256": file_hash(Path(__file__)),
            "retained_index_counts": counts,
            "zip_archives_checked": archive_count,
            "zip_members_checked": archive_members,
            "reconstructed_robustness_contrasts": 32,
            "robustness_checkpoints": 360,
            "robustness_metric_rows": 330120,
            "manuscript_inputs": len(assets["input_sha256"]),
            "manuscript_outputs": len(assets["output_sha256"]),
            "raw_expression_or_prediction_arrays_required": False,
            "qualification": "Retained evidence authentication and independent arithmetic checks; "
            "not a fresh acquisition or a biological validation.",
        },
    )
    print("Publication evidence verified; 32 contrasts reconstructed without raw data")


if __name__ == "__main__":
    main()
