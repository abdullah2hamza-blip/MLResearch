"""Retain authenticated, manageable study outputs without raw expression/predictions."""

import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path

from mlresearch.provenance import file_hash, object_hash, read_json, write_json


def retain_study(run: Path, output: Path) -> None:
    manifest = read_json(run / "manifest.json")
    if manifest["state"] != "complete" or manifest["errors"]:
        raise ValueError("Only a fully completed controlled study may be retained")
    configuration = read_json(run / "configuration.json")
    if (
        object_hash(configuration) != manifest["configuration_sha256"]
        or file_hash(run / "code.zip") != manifest["source_snapshot"]["sha256"]
    ):
        raise ValueError("Study configuration or source archive changed")
    expected = len(configuration["generative_seeds"]) * len(configuration["scenarios"])
    if len(manifest["cases"]) != expected:
        raise ValueError("Study case count is incomplete")
    if output.exists():
        raise ValueError("Retention directory exists")
    output.mkdir(parents=True)
    for name in [
        "configuration.json",
        "code.zip",
        "curves-by-world.csv",
        "paired-world-comparisons.csv",
        "uncertainty-diagnostics.csv",
        "controlled-scenarios.png",
        "controlled-scenarios.svg",
        "events.jsonl",
    ]:
        shutil.copyfile(run / name, output / name)
    shutil.copyfile(run / "manifest.json", output / "study-manifest.json")
    shutil.copyfile(Path(__file__), output / "retention-analysis.py")
    source_hash = manifest["environment"]["source_tree_sha256"]
    audit_hashes, metric_hashes, records = {}, {}, []
    with (
        zipfile.ZipFile(
            output / "case-audits.zip", "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as audits,
        zipfile.ZipFile(
            output / "per-query-metrics.zip", "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as metrics,
    ):
        for case in manifest["cases"]:
            case_run = Path(case["run"])
            prefix = f"world-{case['generative_seed']}/{case['scenario']}"
            if file_hash(case_run / "manifest.json") != case["manifest_sha256"]:
                raise ValueError("Case manifest changed")
            meta = read_json(case_run / "manifest.json")
            if (
                meta["state"] != "complete"
                or meta["environment"]["source_tree_sha256"] != source_hash
                or file_hash(case_run / "prediction-index.json") != meta["predictions_sha256"]
                or file_hash(case_run / "metrics.csv") != meta["results_sha256"]
                or file_hash(case_run / "truth-metrics.csv") != case["truth_metrics_sha256"]
            ):
                raise ValueError("Case outputs changed or used different source code")
            access = read_json(case_run / "truth-access.json")
            if access["prediction_index_sha256_before_opening"] != meta["predictions_sha256"]:
                raise ValueError("Truth access does not match frozen predictions")
            paths = [
                case_run / name
                for name in [
                    "manifest.json",
                    "prediction-index.json",
                    "assessment-access.json",
                    "source-control.json",
                    "truth-access.json",
                    "allocations.csv",
                    "events.jsonl",
                ]
            ]
            paths.extend(sorted(case_run.glob("seed-*/*/ledger.jsonl")))
            for path in paths:
                key = prefix + "/" + path.relative_to(case_run).as_posix()
                audits.write(path, key)
                audit_hashes[key] = file_hash(path)
            episode = Path(meta["configuration"]["episode_directory"]) / "manifest.json"
            if file_hash(episode) != meta["episode_manifest_sha256"]:
                raise ValueError("Case episode changed")
            key = prefix + "/episode-manifest.json"
            audits.write(episode, key)
            audit_hashes[key] = file_hash(episode)
            for name in ["metrics.csv", "truth-metrics.csv"]:
                key = prefix + "/" + name
                metrics.write(case_run / name, key)
                metric_hashes[key] = file_hash(case_run / name)
            records.append(
                {
                    **case,
                    "runtime_seconds": meta["runtime_seconds"],
                    "resources_end": meta["resources_end"],
                    "predictions_sha256": meta["predictions_sha256"],
                    "episode_manifest_sha256": meta["episode_manifest_sha256"],
                }
            )
    for name, hashes in [
        ("case-audits.zip", audit_hashes),
        ("per-query-metrics.zip", metric_hashes),
    ]:
        with zipfile.ZipFile(output / name) as archive:
            for key, expected in hashes.items():
                if hashlib.sha256(archive.read(key)).hexdigest() != expected:
                    raise ValueError("Retained ZIP content mismatch")
    write_json(
        output / "case-index.json",
        {
            "cases": records,
            "case-audit-member-sha256": audit_hashes,
            "metric-member-sha256": metric_hashes,
        },
    )
    write_json(
        output / "retained-artifacts.json",
        {
            "study_manifest_sha256": file_hash(run / "manifest.json"),
            "source_tree_sha256": source_hash,
            "raw_cell_expression_included": False,
            "full_prediction_arrays_included": False,
            "cell_identifiers_included": True,
            "retention_source_sha256": file_hash(Path(__file__)),
            "sha256": {path.name: file_hash(path) for path in output.iterdir() if path.is_file()},
            "qualification": (
                f"All {len(records)} cases retained; per-query metrics are descriptive within "
                "each frozen synthetic world. Large raw arrays remain in ignored runs; "
                "regenerate with saved configuration and exact source ZIP."
            ),
        },
    )
    print("Retained cases", len(records), "bytes", sum(p.stat().st_size for p in output.iterdir()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    retain_study(args.run, args.output)
