"""Command-line entry points; import heavy numeric libraries only for relevant commands."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from mlresearch import __version__
from mlresearch.provenance import JsonLogFormatter, environment_record, resource_record, write_json


def emit(value: Any, output: Path | None) -> None:
    if output is not None:
        write_json(output, value)
    print(json.dumps(value, indent=2, allow_nan=False))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Budgeted perturbation-transfer research")
    result.add_argument("--version", action="version", version=__version__)
    commands = result.add_subparsers(dest="command", required=True)
    resources = commands.add_parser("resources", help="Record local memory/CPU/disk availability")
    resources.add_argument("--output", type=Path)
    provenance = commands.add_parser("provenance", help="Record environment and source hashes")
    provenance.add_argument("--output", type=Path)
    episode = commands.add_parser(
        "episode", help="Freeze source summaries and disjoint recipient banks"
    )
    episode.add_argument("config", type=Path)
    run = commands.add_parser(
        "run", help="Acquire, freeze predictions, then score a configured replay"
    )
    run.add_argument("config", type=Path)
    demo = commands.add_parser("demo", help="Run a small offline synthetic experiment")
    demo.add_argument("--directory", type=Path, required=True)
    demo.add_argument("--seed", type=int, default=71)
    demo.add_argument("--five-seeds", action="store_true")
    report = commands.add_parser("report", help="Create standalone replay plots and tables")
    report.add_argument("run_directory", type=Path)
    report.add_argument("--output", type=Path, required=True)
    uncertainty = commands.add_parser(
        "uncertainty", help="Analyze paired frozen errors with shared-control resampling"
    )
    uncertainty.add_argument("run_directory", type=Path)
    uncertainty.add_argument("--output", type=Path, required=True)
    uncertainty.add_argument("--policy", default="bias_aware")
    uncertainty.add_argument("--reference", default="worst_query")
    uncertainty.add_argument("--backbone", default="ridge_cv")
    uncertainty.add_argument("--samples", type=int, default=2000)
    uncertainty.add_argument("--seed", type=int, default=20261022)
    accounting = commands.add_parser(
        "account-development", help="Authenticate and count unique exposed development cells"
    )
    accounting.add_argument("--output", type=Path, required=True)
    accounting.add_argument("run_directories", type=Path, nargs="+")
    simulate = commands.add_parser(
        "simulate", help="Generate a configured offline source/recipient dataset"
    )
    simulate.add_argument("config", type=Path)
    simulate.add_argument("--directory", type=Path, required=True)
    study = commands.add_parser(
        "study", help="Run a frozen controlled simulation study with bounded workers"
    )
    study.add_argument("config", type=Path)
    data = commands.add_parser("data", help="Pinned public data acquisition and inspection")
    operations = data.add_subparsers(dest="operation", required=True)
    operations.add_parser("list", help="List the pinned public dataset registry")
    fetch = operations.add_parser("fetch", help="Download, resume, and verify one pinned file")
    fetch.add_argument("dataset")
    fetch.add_argument("--directory", type=Path, default=Path("data/raw"))
    fetch.add_argument("--restart", action="store_true")
    audit = operations.add_parser("audit", help="Inspect H5AD metadata with bounded memory")
    audit.add_argument("path", type=Path)
    audit.add_argument("--sample-rows", type=int, default=32)
    audit.add_argument("--output", type=Path)
    for name, help_text in (
        ("counts", "Metadata-only eligibility inventory from a config"),
        ("prepare", "Stream full-gene expression into capped local replay pools"),
    ):
        operation = operations.add_parser(name, help=help_text)
        operation.add_argument("config", type=Path)
        if name == "counts":
            operation.add_argument("--output", type=Path)
    return result


def main(argv: list[str] | None = None) -> None:
    arguments = parser().parse_args(argv)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    try:
        if arguments.command == "resources":
            emit(resource_record(Path.cwd()), arguments.output)
        elif arguments.command == "provenance":
            emit(environment_record(), arguments.output)
        elif arguments.command == "episode":
            from mlresearch.episodes import EpisodeConfig, build_episode

            emit(build_episode(EpisodeConfig.load(arguments.config)), None)
        elif arguments.command == "run":
            from mlresearch.experiment import RunConfig, run_experiment

            emit(run_experiment(RunConfig.load(arguments.config)), None)
        elif arguments.command == "demo":
            from mlresearch.simulation import run_demo

            emit(
                run_demo(arguments.directory, seed=arguments.seed, full=arguments.five_seeds), None
            )
        elif arguments.command == "report":
            from mlresearch.report import summarize_run

            emit(summarize_run(arguments.run_directory, arguments.output), None)
        elif arguments.command == "uncertainty":
            from mlresearch.uncertainty import analyze_run

            analysis = analyze_run(
                arguments.run_directory,
                arguments.output,
                policy=arguments.policy,
                reference=arguments.reference,
                backbone=arguments.backbone,
                samples=arguments.samples,
                seed=arguments.seed,
            )
            emit(
                {key: value for key, value in analysis.items() if key != "per_query_differences"},
                None,
            )
        elif arguments.command == "account-development":
            from mlresearch.accounting import account_development

            if arguments.output.exists():
                raise ValueError("Accounting output exists")
            accounting_result = account_development(arguments.run_directories)
            emit(accounting_result, arguments.output)
        elif arguments.command == "simulate":
            from mlresearch.provenance import read_json
            from mlresearch.simulation import SimulationConfig, make_simulation

            try:
                simulation = SimulationConfig(**read_json(arguments.config))
            except TypeError as error:
                raise ValueError(f"Invalid simulation configuration: {error}") from error
            emit(make_simulation(arguments.directory, simulation), None)
        elif arguments.command == "study":
            from mlresearch.study import StudyConfig, run_study

            config_study = StudyConfig.load(arguments.config)
            result = run_study(config_study)
            emit(
                {
                    "manifest": str(Path(config_study.output_directory) / "manifest.json"),
                    "state": result["state"],
                    "cases": len(result["cases"]),
                    "runtime_seconds": result["runtime_seconds"],
                },
                None,
            )
        elif arguments.command == "data":
            from mlresearch.data import audit_h5ad, datasets, fetch_dataset

            registry = datasets()
            if arguments.operation == "list":
                from dataclasses import asdict

                emit({key: asdict(value) for key, value in registry.items()}, None)
            elif arguments.operation == "fetch":
                if arguments.dataset not in registry:
                    raise ValueError(f"Unknown dataset; choose from {', '.join(registry)}")
                path = fetch_dataset(
                    registry[arguments.dataset], arguments.directory, restart=arguments.restart
                )
                emit({"verified_path": str(path)}, None)
            elif arguments.operation == "audit":
                emit(
                    audit_h5ad(arguments.path, sample_rows=arguments.sample_rows), arguments.output
                )
            elif arguments.operation in ("counts", "prepare"):
                from mlresearch.prepare import PrepareConfig, count_metadata, prepare_h5ad

                config = PrepareConfig.load(arguments.config)
                if arguments.operation == "counts":
                    emit(count_metadata(config), arguments.output)
                else:
                    emit(prepare_h5ad(config), None)
    except (ValueError, OSError, KeyError) as error:
        logging.error("%s", error)
        sys.exit(2)
