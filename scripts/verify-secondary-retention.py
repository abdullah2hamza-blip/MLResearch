"""Verify retained supplementary files, nested archives, ranking rows and charged ledgers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from pathlib import Path

from mlresearch.acquisition import verify_ledger
from mlresearch.provenance import file_hash, read_json, utc_now, write_json


def checked_files(root: Path, hashes: dict) -> int:
    for relative, expected in hashes.items():
        path = root / relative
        if not path.resolve().is_relative_to(root.resolve()) or file_hash(path) != expected:
            raise ValueError(f"Retained artifact changed: {path}")
    return len(hashes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve existing retention verification")
    root = args.bundle
    index = read_json(root / "supplement-artifacts.json")
    files = checked_files(root, index["sha256"])
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != set(index["sha256"]) | {"supplement-artifacts.json"}:
        raise ValueError("Unindexed or missing supplementary file")
    primary = read_json(args.primary / "supplement-artifacts.json")
    primary_files = checked_files(args.primary, primary["sha256"])
    members, cases = 0, 0
    for cost in (0, 16, 64):
        case_root = root / f"setup-cost-{cost}"
        retained = read_json(case_root / "retained-artifacts.json")
        checked_files(case_root, retained["sha256"])
        case_index = read_json(case_root / "case-index.json")
        cases += len(case_index["cases"])
        for name, key in (
            ("case-audits.zip", "case-audit-member-sha256"),
            ("per-query-metrics.zip", "metric-member-sha256"),
        ):
            expected = case_index[key]
            with zipfile.ZipFile(case_root / name) as archive:
                if set(archive.namelist()) != set(expected):
                    raise ValueError("Nested archive membership changed")
                for member, digest in expected.items():
                    if hashlib.sha256(archive.read(member)).hexdigest() != digest:
                        raise ValueError("Nested archive bytes changed")
                    members += 1
    rank_root = root / "ranking"
    rank = read_json(rank_root / "summary.json")
    if rank["state"] != "complete" or rank["run_count"] != 76:
        raise ValueError("Incomplete original ranking analysis")
    if file_hash(rank_root / "analysis-source.py") != rank["source_sha256"]:
        raise ValueError("Ranking source copy changed")
    diagnostic = root / "frozen-diagnostics-complete"
    if (
        file_hash(diagnostic / "summary.json") != rank["diagnostic_summary_sha256"]
        or file_hash(diagnostic / "coordinate-and-interval-diagnostics.csv")
        != rank["coordinate_metrics_sha256"]
        or file_hash(rank_root / "within-gene-perturbation-ranking.csv")
        != rank["ranking_csv_sha256"]
    ):
        raise ValueError("Ranking input/output binding changed")
    rows = 0
    with (rank_root / "within-gene-perturbation-ranking.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        combined = iter(csv.DictReader(stream))
        for number, shard in enumerate(rank["shards"]):
            if read_json(rank_root / f"run-{number}.json") != shard:
                raise ValueError("Ranking receipt differs from summary")
            checked_files(rank_root, {shard["shard"]: shard["sha256"]})
            count = 0
            with (rank_root / shard["shard"]).open(encoding="utf-8", newline="") as part:
                for row in csv.DictReader(part):
                    if next(combined, None) != row:
                        raise ValueError("Combined ranking differs from shard")
                    count += 1
            if count != shard["rows"]:
                raise ValueError("Ranking shard row count changed")
            rows += count
        if next(combined, None) is not None or rows != rank["rows"] or rows != 109380:
            raise ValueError("Unexpected ranking row total")
    direct = read_json(root / "direct-query/prediction-index.json")
    with zipfile.ZipFile(root / "direct-query/charged-query-ledgers.zip") as archive:
        expected_names = {r["ledger"].replace("\\", "/") for r in direct}
        if set(archive.namelist()) != expected_names or len(direct) != 60:
            raise ValueError("Direct-task ledger membership changed")
        for item in direct:
            payload = archive.read(item["ledger"].replace("\\", "/"))
            if hashlib.sha256(payload).hexdigest() != item["ledger_sha256"]:
                raise ValueError("Direct-task ledger bytes changed")
            events = [json.loads(line) for line in payload.splitlines()]
            # Query measurement is expressly permitted only for stronger-information Task C.
            verify_ledger(events, budget=item["spent"], setup_cost=4, query_ids=())
            if events[-1]["spent"] != item["spent"]:
                raise ValueError("Direct-task actual spend changed")
    zip_members = 0
    for path in root.rglob("*.zip"):
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError(f"ZIP checksum failure: {path}")
            zip_members += len(archive.namelist())
    write_json(
        args.output,
        {
            "state": "passed",
            "recorded_at": utc_now(),
            "verification_source_sha256": file_hash(Path(__file__)),
            "secondary_index_sha256": file_hash(root / "supplement-artifacts.json"),
            "primary_index_sha256": file_hash(args.primary / "supplement-artifacts.json"),
            "secondary_files_verified": files,
            "unchanged_primary_files_verified": primary_files,
            "setup_cost_cases": cases,
            "nested_hash_bound_members_verified": members,
            "all_zip_crc_members_verified": zip_members,
            "ranking_rows_matched_to_76_receipts_and_shards": rows,
            "direct_task_ledgers_independently_verified": len(direct),
            "qualification": (
                "Retention/cost integrity, not a new independent biological experiment. "
                "Direct-task primary/scorer bank membership was verified at generation; "
                "this offline check reauthenticates retained bytes, chain, nonreuse and prices."
            ),
        },
    )
    print("Secondary retention verified", files, "files; primary unchanged", primary_files)


if __name__ == "__main__":
    main()
