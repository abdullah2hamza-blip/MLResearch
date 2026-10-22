"""Create the declared external reports and separate paired uncertainty scopes."""

from __future__ import annotations

import argparse
from pathlib import Path

from mlresearch.external import validate_joint_freeze
from mlresearch.provenance import file_hash, read_json, utc_now, write_json
from mlresearch.report import summarize_run
from mlresearch.uncertainty import analyze_run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    suite = read_json(args.suite / "manifest.json")
    if suite["state"] != "complete":
        raise ValueError("Complete the frozen suite before reporting")
    freeze = validate_joint_freeze(args.suite / "joint-prediction-freeze.json")
    if args.output.exists():
        raise ValueError("Report output exists; preserve it and use a fresh directory")
    args.output.mkdir(parents=True)
    artifacts = []
    for entry in freeze["runs"]:
        run = Path(entry["run_directory"])
        manifest = read_json(run / "manifest.json")
        print("Reporting", run.name, flush=True)
        report = args.output / "runs" / run.name
        summarize_run(run, report, bootstrap_seed=20261022, bootstrap_samples=2000)
        artifacts.append(str(report.relative_to(args.output)))
        if manifest["configuration"]["source_control"] == "none":
            for reference in ("worst_query", "mean_query"):
                if reference not in manifest["configuration"]["policies"]:
                    continue
                print("Paired assessment", run.name, reference, flush=True)
                analysis = args.output / "uncertainty" / f"{run.name}-vs-{reference}.json"
                analyze_run(run, analysis, reference=reference, samples=2000, seed=20261022)
                artifacts.append(str(analysis.relative_to(args.output)))
    write_json(
        args.output / "report-execution.json",
        {
            "recorded_at": utc_now(),
            "analysis_source_sha256": file_hash(Path(__file__)),
            "suite_manifest_sha256": file_hash(args.suite / "manifest.json"),
            "bootstrap_seed": 20261022,
            "bootstrap_samples": 2000,
            "reports_and_analyses": artifacts,
            "qualification": (
                "Separate query, measurement and technical-batch scopes; no refitting."
            ),
        },
    )
    print("Reported", len(freeze["runs"]), "frozen runs", flush=True)


if __name__ == "__main__":
    main()
