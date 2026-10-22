"""Frozen, bounded-worker controlled simulations and scorer-only truth diagnostics."""

from __future__ import annotations

import csv
import json
import logging
import os
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np

from mlresearch.acquisition import CONTROL
from mlresearch.controls import SOURCE_CONTROLS, transform_source
from mlresearch.episodes import EpisodeConfig, build_episode, load_public_episode
from mlresearch.experiment import RunConfig, _write_csv, run_experiment
from mlresearch.linear import design_information, query_support
from mlresearch.models import BACKBONES
from mlresearch.policies import POLICIES, PolicyConfig
from mlresearch.provenance import (
    environment_record,
    event_log,
    file_hash,
    object_hash,
    read_json,
    resource_record,
    snapshot_sources,
    write_json,
)
from mlresearch.simulation import SimulationConfig, make_simulation


@dataclass(frozen=True)
class StudyConfig:
    output_directory: str
    scenarios: dict[str, dict[str, Any]]
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    generative_seeds: list[int] = field(default_factory=lambda: [71, 72, 73, 74, 75])
    acquisition_seeds: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    budgets: list[int] = field(default_factory=lambda: [96, 144, 192])
    policies: list[str] = field(default_factory=lambda: list(POLICIES))
    variants: dict[str, dict[str, Any]] = field(default_factory=dict)
    primary_backbone: str = "ridge_cv"
    workers: int = 2
    development_resource_record: str | None = None

    def __post_init__(self) -> None:
        if len(self.budgets) < 2:
            raise ValueError("A simulation study needs at least two budget checkpoints")
        if (
            not self.scenarios
            or not self.generative_seeds
            or len(set(self.generative_seeds)) != len(self.generative_seeds)
        ):
            raise ValueError("Declare scenarios and distinct generative seeds")
        if any(
            isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
            for seed in self.generative_seeds
        ):
            raise ValueError("Generative seeds must be nonnegative integers")
        if (
            isinstance(self.workers, bool)
            or not isinstance(self.workers, int)
            or not 1 <= self.workers <= (os.cpu_count() or 1)
        ):
            raise ValueError("Invalid bounded worker count")
        for name, overrides in self.scenarios.items():
            if not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in name):
                raise ValueError("Scenario names must be safe directory names")
            forbidden = {
                "seed",
                "interventions",
                "genes",
                "latent_rank",
                "source_cells",
                "acquisition_cells",
                "assessment_cells",
                "controls_each_bank",
                "query_fraction",
            }
            if set(overrides) & forbidden:
                raise ValueError("Controlled scenarios must retain a common inventory and split")
            if overrides.get("source_control", "none") not in SOURCE_CONTROLS:
                raise ValueError("Unknown simulation source-information control")
            self.simulation_for(name, self.generative_seeds[0])
        RunConfig(
            "unused",
            "unused",
            self.budgets,
            self.acquisition_seeds,
            self.policies,
            self.policy,
            primary_backbone=self.primary_backbone,
            variants=self.variants,
        )

    @classmethod
    def load(cls, path: Path) -> StudyConfig:
        value = read_json(path)
        try:
            value["simulation"] = SimulationConfig(**value.get("simulation", {}))
            value["policy"] = PolicyConfig(**value.get("policy", {}))
            return cls(**value)
        except TypeError as error:
            raise ValueError(f"Invalid simulation study configuration: {error}") from error

    def simulation_for(self, scenario: str, seed: int) -> SimulationConfig:
        parameters = {
            key: value for key, value in self.scenarios[scenario].items() if key != "source_control"
        }
        return replace(self.simulation, seed=seed, **parameters)


def score_simulation_truth(run: Path, data: Path) -> None:
    """Truth never enters PublicEpisode, policies or predictors; open it after frozen scoring."""
    manifest = read_json(run / "manifest.json")
    index = read_json(run / "prediction-index.json")
    if (
        manifest["state"] != "complete"
        or file_hash(run / "prediction-index.json") != manifest["predictions_sha256"]
    ):
        raise ValueError("Simulation truth requires completed, authenticated predictions")
    public = load_public_episode(Path(manifest["configuration"]["episode_directory"]))
    public, transformed = transform_source(
        public,
        manifest["configuration"].get("source_control", "none"),
        manifest["configuration"].get("source_control_seed", 20261022),
    )
    if transformed != manifest["source_control"]:
        raise ValueError("Frozen source-control reconstruction changed")
    metadata = read_json(data / "target/metadata.json")
    ordering = sorted(set(metadata["interventions"]) - set(metadata["control_labels"]))
    with np.load(data / "generative-truth.npz", allow_pickle=False) as arrays:
        ordering = arrays["intervention_ids"].astype(str).tolist()
        genes = arrays["gene_ids"].astype(str).tolist()
        rows = [ordering.index(key) for key in public.query_ids]
        columns = [genes.index(key) for key in public.genes]
        truth = arrays["target_effects"][np.ix_(rows, columns)]
        source_truth = arrays["latent_source_effects"][np.ix_(rows, columns)]
        latent = np.column_stack([np.ones(len(ordering)), arrays["latent"]])
    with np.load(run / "assessment.npz", allow_pickle=False) as arrays:
        assessment = arrays["effects"]
    oracle_assessment_mse = np.mean((assessment - truth) ** 2, axis=1)
    source_error = np.mean(
        (public.source_effects[[public.index(key) for key in public.query_ids]] - source_truth)
        ** 2,
        axis=1,
    )
    source_signal = np.mean(
        public.source_effects[[public.index(key) for key in public.query_ids]] ** 2, axis=1
    )
    candidate_rows = [ordering.index(key) for key in public.candidate_ids]
    query_rows = [ordering.index(key) for key in public.query_ids]
    results: list[dict[str, Any]] = []
    for item in index:
        artifact = run / item["artifact"]
        if file_hash(artifact) != item["sha256"]:
            raise ValueError("Prediction changed before simulation truth scoring")
        ledger = [
            json.loads(line)
            for line in (artifact.parent / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        counts: dict[str, int] = defaultdict(int)
        for event in ledger:
            if event["spent"] <= item["spent"]:
                counts[event["action"]["intervention"]] += event["action"]["cells"]
        information = design_information(
            latent[candidate_rows],
            np.asarray([counts[key] for key in public.candidate_ids], dtype=float),
            np.ones(len(candidate_rows)),
            counts[CONTROL],
            1,
        )
        oracle_support = query_support(latent[query_rows], information).identified
        with np.load(artifact, allow_pickle=False) as arrays:
            for backbone in BACKBONES:
                if backbone not in arrays:
                    continue
                predictions = arrays[backbone]
                errors = np.mean((predictions - truth) ** 2, axis=1)
                specific = np.mean(
                    ((predictions - predictions.mean(axis=0)) - (truth - truth.mean(axis=0))) ** 2,
                    axis=1,
                )
                widths = 1.96 * np.sqrt(arrays["ideal_variance"])
                for position, identity in enumerate(public.query_ids):
                    coverage = (
                        float(
                            np.mean(
                                np.abs(predictions[position] - truth[position]) <= widths[position]
                            )
                        )
                        if backbone == "ridge" and np.isfinite(widths[position])
                        else None
                    )
                    results.append(
                        {
                            "policy": item["policy"],
                            "seed": item["seed"],
                            "budget": item["budget"],
                            "spent": item["spent"],
                            "backbone": backbone,
                            "query": identity,
                            "true_mse": float(errors[position]),
                            "true_specificity_mse": float(specific[position]),
                            "source_stratum": "strong"
                            if source_signal[position] >= np.median(source_signal)
                            else "weak",
                            "oracle_assessment_mse": float(oracle_assessment_mse[position]),
                            "source_feature_mse": float(source_error[position]),
                            "estimated_linear_identified": bool(arrays["identified"][position]),
                            "oracle_latent_linear_identified": bool(oracle_support[position]),
                            "gaussian_true_coverage_diagnostic": coverage,
                            "ridge_cv_selected": float(arrays["ridge_cv_selected"]),
                            "source_unstable": bool(arrays["source_unstable"][position]),
                        }
                    )
    _write_csv(run / "truth-metrics.csv", results)
    write_json(
        run / "truth-access.json",
        {
            "role": "scorer_only_oracle_diagnostic",
            "prediction_index_sha256_before_opening": manifest["predictions_sha256"],
            "truth_sha256": file_hash(data / "generative-truth.npz"),
            "truth_metrics_sha256": file_hash(run / "truth-metrics.csv"),
            "qualification": (
                "Oracle latent linear span diagnoses geometry; "
                "it does not identify nonlinear mechanism shifts."
            ),
        },
    )


def _run_case(payload: dict[str, Any]) -> dict[str, Any]:
    config, expected = (
        StudyConfig.load(Path(payload["configuration_path"])),
        payload["source_sha256"],
    )
    if object_hash(asdict(config)) != payload["configuration_sha256"]:
        raise ValueError("Study configuration changed before a case started")
    if (
        config.development_resource_record is not None
        and file_hash(Path(config.development_resource_record))
        != payload["development_resource_sha256"]
    ):
        raise ValueError("Fixed development resource record changed during study")
    if environment_record()["source_tree_sha256"] != expected:
        raise ValueError("Study sources changed before a case started")
    seed, name = payload["seed"], payload["scenario"]
    output = Path(config.output_directory) / f"world-{seed}" / name
    simulation = config.simulation_for(name, seed)
    data, episode, run = output / "data", output / "episode", output / "run"
    make_simulation(data, simulation)
    build_episode(
        EpisodeConfig(
            str(data / "source"),
            str(data / "target"),
            "source",
            "target",
            str(episode),
            seed=seed,
            query_fraction=simulation.query_fraction,
            min_source_cells=min(32, simulation.source_cells),
            acquisition_cells=simulation.acquisition_cells,
            assessment_cells=simulation.assessment_cells,
            acquisition_controls=simulation.controls_each_bank,
            assessment_controls=simulation.controls_each_bank,
        )
    )
    run_experiment(
        RunConfig(
            str(episode),
            str(run),
            config.budgets,
            config.acquisition_seeds,
            config.policies,
            config.policy,
            label=f"controlled:{name}:world-{seed}",
            primary_backbone=config.primary_backbone,
            variants=config.variants,
            source_control=config.scenarios[name].get("source_control", "none"),
            development_resource_record=config.development_resource_record,
        )
    )
    score_simulation_truth(run, data)
    return {
        "scenario": name,
        "generative_seed": seed,
        "run": str(run),
        "manifest_sha256": file_hash(run / "manifest.json"),
        "truth_metrics_sha256": file_hash(run / "truth-metrics.csv"),
    }


def summarize_study(
    output: Path, cases: list[dict[str, Any]], config: StudyConfig
) -> dict[str, Any]:
    grouped: dict[tuple[str, int, str, str, int], list[float]] = defaultdict(list)
    coverage: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    geometry: dict[tuple[str, str, int], list[tuple[bool, bool]]] = defaultdict(list)
    for case in cases:
        with (Path(case["run"]) / "truth-metrics.csv").open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                key = (
                    case["scenario"],
                    case["generative_seed"],
                    row["policy"],
                    row["backbone"],
                    int(row["budget"]),
                )
                grouped[key].append(float(row["true_mse"]))
                if row["backbone"] == "ridge":
                    diagnostic = (case["scenario"], row["policy"], int(row["budget"]))
                    if row["gaussian_true_coverage_diagnostic"]:
                        coverage[diagnostic].append(float(row["gaussian_true_coverage_diagnostic"]))
                    geometry[diagnostic].append(
                        (
                            row["estimated_linear_identified"] == "True",
                            row["oracle_latent_linear_identified"] == "True",
                        )
                    )
    curves = [
        {
            "scenario": s,
            "world": w,
            "policy": p,
            "backbone": b,
            "budget": n,
            "true_mse": float(np.mean(values)),
        }
        for (s, w, p, b, n), values in sorted(grouped.items())
    ]
    _write_csv(output / "curves-by-world.csv", curves)
    areas: dict[tuple[str, str, str], dict[int, float]] = defaultdict(dict)
    for scenario in config.scenarios:
        for world in config.generative_seeds:
            for policy in config.policies:
                for backbone in BACKBONES:
                    if (scenario, world, policy, backbone, config.budgets[0]) not in grouped:
                        continue
                    risk = [
                        np.mean(grouped[(scenario, world, policy, backbone, budget)])
                        for budget in config.budgets
                    ]
                    areas[(scenario, policy, backbone)][world] = float(
                        np.trapezoid(risk, config.budgets)
                        / (config.budgets[-1] - config.budgets[0])
                    )
    comparisons = []
    for (scenario, policy, backbone), world_values in sorted(areas.items()):
        reference = areas.get((scenario, "worst_query", backbone))
        if reference is None:
            continue
        values = np.asarray([world_values[world] for world in config.generative_seeds])
        difference = values - np.asarray([reference[world] for world in config.generative_seeds])
        reference_mean = float(np.mean(list(reference.values())))
        comparisons.append(
            {
                "scenario": scenario,
                "policy": policy,
                "backbone": backbone,
                "mean_true_error_area": float(values.mean()),
                "paired_difference": float(difference.mean()),
                "relative_error_change": float(difference.mean() / reference_mean)
                if reference_mean
                else None,
                "worlds": len(values),
                "monte_carlo_standard_error": float(difference.std(ddof=1) / np.sqrt(len(values)))
                if len(values) > 1
                else None,
            }
        )
    if comparisons:
        _write_csv(output / "paired-world-comparisons.csv", comparisons)
    diagnostics = [
        {
            "scenario": s,
            "policy": p,
            "budget": n,
            "ridge_gaussian_true_coverage_conditional_on_finite_width": float(
                np.mean(coverage[(s, p, n)])
            )
            if coverage[(s, p, n)]
            else None,
            "finite_interval_query_seed_observations": len(coverage[(s, p, n)]),
            "total_query_seed_observations": len(values),
            "finite_interval_fraction": len(coverage[(s, p, n)]) / len(values),
            "estimated_identified_fraction": float(np.mean([a for a, b in values])),
            "oracle_latent_identified_fraction": float(np.mean([b for a, b in values])),
            "false_linear_identification_fraction": float(
                np.mean([a and not b for a, b in values])
            ),
        }
        for (s, p, n), values in sorted(geometry.items())
    ]
    if diagnostics:
        _write_csv(output / "uncertainty-diagnostics.csv", diagnostics)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["svg.hashsalt"] = "mlresearch-study"

    names = list(config.scenarios)
    figure, axes = plt.subplots(
        int(np.ceil(len(names) / 3)),
        min(3, len(names)),
        squeeze=False,
        figsize=(11, max(3, int(np.ceil(len(names) / 3)) * 2.5)),
        layout="constrained",
    )
    shown = [
        name
        for name in ("random_equal", "d_optimal", "worst_query", "disagreement", "bias_aware")
        if name in config.policies
    ]
    for axis, scenario in zip(axes.flat, names, strict=False):
        for policy in shown:
            risk = [
                np.mean(
                    [
                        np.mean(grouped[(scenario, world, policy, config.primary_backbone, budget)])
                        for world in config.generative_seeds
                    ]
                )
                for budget in config.budgets
            ]
            axis.plot(config.budgets, risk, marker=".", label=policy)
        zero = np.mean(
            [
                np.mean(grouped[(scenario, world, config.policies[0], "zero", config.budgets[0])])
                for world in config.generative_seeds
            ]
        )
        axis.axhline(zero, linestyle="--", color="black", linewidth=0.8, label="zero effect")
        axis.set(title=scenario, xlabel="Recipient acquisition budget", ylabel="True full-gene MSE")
    for axis in list(axes.flat)[len(names) :]:
        axis.set_visible(False)
    if shown:
        axes.flat[0].legend(fontsize=6)
    figure.savefig(output / "controlled-scenarios.png", dpi=150)
    figure.savefig(output / "controlled-scenarios.svg", metadata={"Date": None})
    plt.close(figure)
    return {
        "cases": len(cases),
        "independent_generative_worlds": len(config.generative_seeds),
        "primary_backbone": config.primary_backbone,
        "comparisons": [row for row in comparisons if row["backbone"] == config.primary_backbone],
        "uncertainty_scope": (
            "Monte Carlo standard errors use paired independent generative worlds. "
            "Queries and acquisition seeds are averaged within world; "
            "they are not biological replicates."
        ),
        "limitations": [
            "Synthetic Gaussian expression is not a regulatory or biological validation model.",
            "Gaussian coverage is an ideal-model diagnostic; post-selection coverage is unproven.",
            "Coverage conditions on finite-width queries; the eligible fraction is reported.",
            "Batch stress shares technical batch effects across disjoint cell banks.",
            "Known truth and latent coordinates were scorer-only diagnostics.",
        ],
    }


def run_study(config: StudyConfig) -> dict[str, Any]:
    output = Path(config.output_directory)
    if output.exists():
        raise ValueError("Study output exists; choose a fresh directory")
    output.mkdir(parents=True)
    environment, resources = environment_record(), resource_record(output)
    development_sha256 = (
        file_hash(Path(config.development_resource_record))
        if config.development_resource_record is not None
        else None
    )
    simulated_rows = 4 * config.simulation.controls_each_bank + config.simulation.interventions * (
        config.simulation.source_cells
        + config.simulation.acquisition_cells
        + config.simulation.assessment_cells
    )
    worker_estimate = max(256 * 1024**2, simulated_rows * config.simulation.genes * 8 * 4)
    configuration = asdict(config)
    configuration_path = output / "configuration.json"
    write_json(configuration_path, configuration)
    manifest: dict[str, Any] = {
        "state": "running",
        "configuration_sha256": object_hash(configuration),
        "environment": environment,
        "resources_start": resources,
        "development_resource_sha256": development_sha256,
        "source_snapshot": snapshot_sources(output / "code.zip", environment["source_hashes"]),
        "cases": [],
        "errors": [],
    }
    write_json(output / "manifest.json", manifest)
    if resources.get("available_ram_bytes", 2**60) < config.workers * worker_estimate:
        manifest.update(
            state="failed",
            error="Insufficient available memory for requested simulation workers",
            estimated_worker_bytes=worker_estimate,
        )
        write_json(output / "manifest.json", manifest)
        raise ValueError(manifest["error"])
    payloads = [
        {
            "configuration_path": str(configuration_path.resolve()),
            "source_sha256": environment["source_tree_sha256"],
            "configuration_sha256": manifest["configuration_sha256"],
            "development_resource_sha256": development_sha256,
            "seed": seed,
            "scenario": scenario,
        }
        for seed in config.generative_seeds
        for scenario in config.scenarios
    ]
    started = time.perf_counter()
    with event_log(output / "events.jsonl"):
        with ProcessPoolExecutor(max_workers=config.workers) as executor:
            futures = {executor.submit(_run_case, payload): payload for payload in payloads}
            for future in as_completed(futures):
                payload = futures[future]
                try:
                    result = future.result()
                    manifest["cases"].append(result)
                    logging.getLogger(__name__).info(
                        "Completed simulation case: %s world=%s (%s/%s)",
                        payload["scenario"],
                        payload["seed"],
                        len(manifest["cases"]),
                        len(payloads),
                    )
                except Exception as error:
                    manifest["errors"].append(
                        {
                            "scenario": payload["scenario"],
                            "seed": payload["seed"],
                            "error": str(error),
                        }
                    )
                    logging.getLogger(__name__).error("Simulation case failed: %s", error)
                write_json(output / "manifest.json", manifest)
    if manifest["errors"]:
        manifest.update(
            state="failed",
            runtime_seconds=time.perf_counter() - started,
            resources_end=resource_record(output),
        )
        write_json(output / "manifest.json", manifest)
        raise ValueError("Simulation cases failed; retained manifest lists every failure")
    if environment_record()["source_tree_sha256"] != environment["source_tree_sha256"]:
        manifest.update(state="failed", error="Study source files changed")
        write_json(output / "manifest.json", manifest)
        raise ValueError("Study sources changed; completed cases retained, summary refused")
    if object_hash(read_json(configuration_path)) != manifest["configuration_sha256"]:
        manifest.update(state="failed", error="Study configuration changed")
        write_json(output / "manifest.json", manifest)
        raise ValueError("Study configuration changed; summary refused")
    if (
        config.development_resource_record is not None
        and file_hash(Path(config.development_resource_record)) != development_sha256
    ):
        manifest.update(state="failed", error="Fixed development resource record changed")
        write_json(output / "manifest.json", manifest)
        raise ValueError("Fixed development resource record changed; summary refused")
    manifest["cases"].sort(key=lambda item: (item["generative_seed"], item["scenario"]))
    manifest.update(
        state="complete",
        runtime_seconds=time.perf_counter() - started,
        resources_end=resource_record(output),
        summary=summarize_study(output, manifest["cases"], config),
    )
    write_json(output / "manifest.json", manifest)
    return manifest
