"""Replay experiments with an explicit predict-then-score phase boundary."""

from __future__ import annotations

import csv
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from mlresearch.acquisition import CONTROL, AcquisitionService, IndexedCellPool, Pool, verify_ledger
from mlresearch.controls import SOURCE_CONTROLS, transform_source
from mlresearch.episodes import load_prepared, load_public_episode
from mlresearch.models import BACKBONES, Observations, predict, source_coordinates
from mlresearch.policies import POLICIES, Policy, PolicyConfig
from mlresearch.provenance import (
    environment_record,
    event_log,
    file_hash,
    object_hash,
    read_json,
    resource_record,
    snapshot_sources,
    utc_now,
    write_json,
)


@dataclass(frozen=True)
class RunConfig:
    episode_directory: str
    output_directory: str
    budgets: list[int] = field(default_factory=lambda: [128, 256, 512])
    seeds: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    policies: list[str] = field(default_factory=lambda: list(POLICIES))
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    label: str = "exploratory"
    primary_backbone: str = "ridge"
    variants: dict[str, dict[str, Any]] = field(default_factory=dict)
    source_control: str = "none"
    source_control_seed: int = 20261022
    development_resource_record: str | None = None

    def __post_init__(self) -> None:
        if self.source_control not in SOURCE_CONTROLS:
            raise ValueError("Unknown source-information control")
        if (
            isinstance(self.source_control_seed, bool)
            or not isinstance(self.source_control_seed, int)
            or self.source_control_seed < 0
        ):
            raise ValueError("Invalid source-control seed")
        if set(self.variants) & set(POLICIES):
            raise ValueError("Variant labels cannot replace canonical policy names")
        for name in self.variants:
            if not name or any(
                character not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for character in name
            ):
                raise ValueError("Variant labels must be safe directory names")
            base, variant = self.policy_for(name)
            if base not in POLICIES:
                raise ValueError("A variant requires a known base policy")
            for field_name in (
                "rank",
                "pilot_controls",
                "pilot_interventions",
                "setup_cost",
                "cell_cost",
                "control_cell_cost",
                "ridge",
                "ridge_grid",
                "ridge_include_null",
            ):
                if getattr(variant, field_name) != getattr(self.policy, field_name):
                    raise ValueError(
                        "Variants must share prediction settings, pilot access and costs"
                    )
            if variant.pilot_cell_count != self.policy.pilot_cell_count:
                raise ValueError("Variants must share pilot cell depth")
        if self.primary_backbone not in BACKBONES:
            raise ValueError("Unknown primary predictor backbone")
        if self.policy.pilot_interventions < 3:
            raise ValueError("Paid ridge validation requires at least three pilot interventions")
        if not self.budgets or sorted(set(self.budgets)) != self.budgets:
            raise ValueError("Budgets must be a strictly increasing nonempty list")
        if any(isinstance(x, bool) or not isinstance(x, int) or x < 1 for x in self.budgets):
            raise ValueError("Budgets must be positive integers")
        if not self.seeds or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Acquisition seeds must be distinct and nonempty")
        if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in self.seeds):
            raise ValueError("Acquisition seeds must be nonnegative integers")
        if (
            not self.policies
            or len(set(self.policies)) != len(self.policies)
            or set(self.policies) - (set(POLICIES) | set(self.variants))
        ):
            raise ValueError("Policies must be distinct known policies")
        pilot_cost = (
            self.policy.pilot_controls * self.policy.control_cell_cost
            + self.policy.pilot_interventions
            * (self.policy.setup_cost + self.policy.pilot_cell_count * self.policy.cell_cost)
        )
        if pilot_cost > self.budgets[0]:
            raise ValueError("The first budget cannot pay for the common pilot")

    def policy_for(self, name: str) -> tuple[str, PolicyConfig]:
        if name not in self.variants:
            return name, self.policy
        declaration = self.variants[name]
        if set(declaration) - {"base", "overrides"}:
            raise ValueError("Unknown policy-variant fields")
        try:
            settings = PolicyConfig(**(asdict(self.policy) | declaration.get("overrides", {})))
        except TypeError as error:
            raise ValueError(f"Invalid policy variant: {error}") from error
        return declaration.get("base", "bias_aware"), settings

    @classmethod
    def load(cls, path: Path) -> RunConfig:
        value = read_json(path)
        try:
            value["policy"] = PolicyConfig(**value.get("policy", {}))
            return cls(**value)
        except TypeError as error:
            raise ValueError(f"Invalid run configuration: {error}") from error


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("Cannot write an empty results table")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _assessment(
    matrix: np.ndarray, banks: dict[str, Any], query_ids: tuple[str, ...]
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Called only after every prediction artifact is closed and hashed."""
    columns = banks["target_columns"]
    control = np.asarray(
        matrix[np.ix_(banks["assessment_rows"][CONTROL], columns)], dtype=np.float64
    )
    control_mean, control_variance = (
        control.mean(axis=0),
        control.var(axis=0, ddof=1) / len(control),
    )
    effects, noise = [], []
    for identity in query_ids:
        block = np.asarray(
            matrix[np.ix_(banks["assessment_rows"][identity], columns)], dtype=np.float64
        )
        effects.append(block.mean(axis=0) - control_mean)
        noise.append(block.var(axis=0, ddof=1) / len(block) + control_variance)
    return (
        np.asarray(effects),
        np.asarray(noise),
        {
            "phase": "scorer_only_assessment",
            "opened_at": utc_now(),
            "query_cell_ids": {key: banks["assessment_cell_ids"][key] for key in query_ids},
            "control_cell_ids": banks["assessment_cell_ids"][CONTROL],
            "resource_cells": sum(
                len(banks["assessment_rows"][key]) for key in [CONTROL, *query_ids]
            ),
            "candidate_assessment_cells": "Reserved and unused; no free validation observations.",
        },
    )


def run_experiment(config: RunConfig) -> dict[str, Any]:
    output = Path(config.output_directory)
    if output.exists():
        raise ValueError("Run directory exists; use a fresh path")
    output.mkdir(parents=True)
    write_json(output / "manifest.json", {"state": "validating", "configuration": asdict(config)})
    with event_log(output / "events.jsonl"):
        try:
            return _run_experiment(config)
        except Exception as error:
            logger = logging.getLogger(__name__)
            logger.error("Run failed: %s", error)
            manifest = read_json(output / "manifest.json")
            manifest.update(
                state="failed",
                error_type=type(error).__name__,
                error=str(error),
                failed_at=utc_now(),
            )
            write_json(output / "manifest.json", manifest)
            raise


def _run_experiment(config: RunConfig) -> dict[str, Any]:
    started = time.perf_counter()
    output, episode = Path(config.output_directory), Path(config.episode_directory)
    environment = environment_record()
    public = load_public_episode(episode)
    public, source_control_record = transform_source(
        public, config.source_control, config.source_control_seed
    )
    banks = read_json(episode / "private-banks.json")
    target_path = Path(banks["target_prepared"])
    if not target_path.is_absolute():
        target_path = episode / target_path
    target_metadata, target_values, target_manifest = load_prepared(target_path)
    episode_manifest = read_json(episode / "manifest.json")
    if target_manifest != episode_manifest["prepared_inputs"]["target"]:
        raise ValueError("Target preparation manifest changed after episode freezing")
    if set(banks["acquisition_rows"]) != {CONTROL, *public.candidate_ids}:
        raise ValueError("Acquisition bank identities do not match the public candidate set")
    acquisition_ids = {key for ids in banks["acquisition_cell_ids"].values() for key in ids}
    assessment_ids = {key for ids in banks["assessment_cell_ids"].values() for key in ids}
    if acquisition_ids & assessment_ids or set(banks["source_cell_ids"]) & (
        acquisition_ids | assessment_ids
    ):
        raise ValueError("Cell banks overlap")
    pools: dict[str, Pool] = {}
    for identity, bank_rows in banks["acquisition_rows"].items():
        ids = tuple(target_metadata["cell_ids"][row] for row in bank_rows)
        if list(ids) != banks["acquisition_cell_ids"][identity]:
            raise ValueError("Acquisition row identifiers changed")
        pools[identity] = IndexedCellPool(
            ids, target_values, tuple(bank_rows), tuple(banks["target_columns"])
        )
    write_json(output / "source-control.json", source_control_record)
    development: dict[str, Any] = {
        "unique_resource_cost_units": 0,
        "status": "No fixed development record supplied.",
    }
    if config.development_resource_record is not None:
        record_path = Path(config.development_resource_record)
        development = read_json(record_path)
        cost = development.get("unique_resource_cost_units")
        if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
            raise ValueError("Invalid fixed development-resource accounting")
        development = {
            "record": development,
            "sha256": file_hash(record_path),
            "unique_resource_cost_units": cost,
        }
    configuration = asdict(config)
    manifest: dict[str, Any] = {
        "state": "acquiring",
        "schema_version": 1,
        "configuration": configuration,
        "configuration_sha256": object_hash(configuration),
        "environment": environment,
        "source_snapshot": snapshot_sources(output / "code.zip", environment["source_hashes"]),
        "resources_start": resource_record(output),
        "episode_manifest_sha256": file_hash(episode / "manifest.json"),
        "fixed_public_source_cells": len(banks["source_cell_ids"]),
        "fixed_development_resources": development,
        "total_program_budget_grid": [
            budget + development["unique_resource_cost_units"] for budget in config.budgets
        ],
        "source_control": source_control_record,
        "policy_specifications": {
            name: {
                "base": config.policy_for(name)[0],
                "settings": asdict(config.policy_for(name)[1]),
            }
            for name in config.policies
        },
        "primary_comparator": "worst_query",
        "primary_backbone": config.primary_backbone,
        "primary_endpoint": (
            "Mean full aligned-gene squared control-relative error; trapezoidal area "
            "over the fixed budget grid divided by grid width."
        ),
        "inference_unit": (
            "Paired query intervention; seeds measure acquisition variability, "
            "not biological replication."
        ),
    }
    write_json(output / "manifest.json", manifest)
    coordinates = source_coordinates(public, config.policy.rank)
    np.save(output / "source-coordinates.npy", coordinates.features)
    predictions: list[dict[str, Any]] = []
    allocations: list[dict[str, Any]] = []
    for seed in config.seeds:
        for name in config.policies:
            logging.getLogger(__name__).info("Acquiring", extra={"seed": seed, "policy": name})
            policy_started = time.perf_counter()
            directory = output / f"seed-{seed}" / name
            base_policy, settings = config.policy_for(name)
            service = AcquisitionService(
                pools,
                public.query_ids,
                budget=max(config.budgets),
                setup_cost=config.policy.setup_cost,
                cell_cost=config.policy.cell_cost,
                control_cell_cost=config.policy.control_cell_cost,
                ledger_path=directory / "ledger.jsonl",
            )
            observations = Observations()
            policy = Policy(base_policy, public, coordinates, settings, seed)
            for pilot_action in policy.pilot():
                if (
                    service.public_state()["spent"] + service.price(pilot_action)
                    > config.budgets[0]
                ):
                    raise ValueError("Pilot exceeds first budget")
                observations.update(service.buy(pilot_action))
            for budget in config.budgets:
                while True:
                    action = policy.choose(service.public_state(), observations, budget)
                    if action is None:
                        break
                    observations.update(service.buy(action))
                estimates, diagnostics = predict(
                    public,
                    coordinates,
                    observations,
                    public.query_ids,
                    ridge=settings.ridge,
                    ridge_grid=tuple(settings.ridge_grid),
                    ridge_include_null=settings.ridge_include_null,
                )
                artifact = directory / f"budget-{budget}.npz"
                payload: dict[str, Any] = {
                    key: value.astype(np.float32) for key, value in estimates.items()
                }
                payload.update(diagnostics)
                np.savez(artifact, **payload)
                state = service.public_state()
                predictions.append(
                    {
                        "seed": seed,
                        "policy": name,
                        "budget": budget,
                        "spent": state["spent"],
                        "artifact": str(artifact.relative_to(output)),
                        "sha256": file_hash(artifact),
                    }
                )
                allocations.append(
                    {
                        "seed": seed,
                        "policy": name,
                        "budget": budget,
                        "spent": state["spent"],
                        "control_cells": state["counts"][CONTROL],
                        "ridge_cv_selected": diagnostics["ridge_cv_selected"],
                        "variance_prior_scale": policy.variance_ratio(observations),
                        "interventions_opened": sum(
                            count > 0 for key, count in state["counts"].items() if key != CONTROL
                        ),
                        "perturbed_cells": sum(
                            count for key, count in state["counts"].items() if key != CONTROL
                        ),
                        "runtime_seconds_cumulative": time.perf_counter() - policy_started,
                    }
                )
            verify_ledger(
                service.ledger(),
                budget=max(config.budgets),
                setup_cost=config.policy.setup_cost,
                cell_cost=config.policy.cell_cost,
                control_cell_cost=config.policy.control_cell_cost,
                query_ids=public.query_ids,
            )
    write_json(output / "prediction-index.json", predictions)
    _write_csv(output / "allocations.csv", allocations)
    manifest["state"] = "predictions_frozen"
    manifest["predictions_sha256"] = file_hash(output / "prediction-index.json")
    write_json(output / "manifest.json", manifest)
    if environment["source_tree_sha256"] != environment_record()["source_tree_sha256"]:
        raise ValueError(
            "Package sources changed during acquisition; predictions retained, scoring refused"
        )
    effects, noise, access = _assessment(target_values, banks, public.query_ids)
    manifest["scorer_only_assessment_cells"] = access["resource_cells"]
    access["prediction_index_sha256_before_opening"] = manifest["predictions_sha256"]
    write_json(output / "assessment-access.json", access)
    np.savez(output / "assessment.npz", effects=effects, mean_noise_variance=noise)
    source = public.source_effects[[public.index(key) for key in public.query_ids]]
    source_norm = np.mean(source**2, axis=1)
    median_signal = float(np.median(source_norm))
    rows: list[dict[str, Any]] = []
    for item in predictions:
        artifact = output / item["artifact"]
        if file_hash(artifact) != item["sha256"]:
            raise ValueError("A prediction artifact changed before scoring")
        with np.load(artifact, allow_pickle=False) as arrays:
            for backbone in BACKBONES:
                estimated = arrays[backbone]
                errors = np.mean((estimated - effects) ** 2, axis=1)
                specificity = np.mean(
                    ((estimated - estimated.mean(axis=0)) - (effects - effects.mean(axis=0))) ** 2,
                    axis=1,
                )
                ideal_variance = arrays["ideal_variance"]
                for index, identity in enumerate(public.query_ids):
                    variance = float(ideal_variance[index])
                    width = 1.96 * np.sqrt(variance + noise[index])
                    coverage = (
                        float(np.mean(np.abs(estimated[index] - effects[index]) <= width))
                        if backbone == "ridge" and np.isfinite(variance)
                        else None
                    )
                    rows.append(
                        {
                            "seed": item["seed"],
                            "policy": item["policy"],
                            "budget": item["budget"],
                            "spent": item["spent"],
                            "total_program_cost": item["spent"]
                            + development["unique_resource_cost_units"],
                            "recipient_measurements_used_cost": 0
                            if backbone in ("zero", "source_copy")
                            else item["spent"],
                            "backbone": backbone,
                            "query": identity,
                            "mse": float(errors[index]),
                            "assessment_noise_floor": float(noise[index].mean()),
                            "noise_subtracted_mse": float(errors[index] - noise[index].mean()),
                            "specificity_mse": float(specificity[index]),
                            "source_signal": float(source_norm[index]),
                            "source_stratum": "strong"
                            if source_norm[index] >= median_signal
                            else "weak",
                            "identified": bool(arrays["identified"][index]),
                            "source_unstable": bool(arrays["source_unstable"][index]),
                            "deferral_recommended": bool(arrays["deferral_recommended"][index]),
                            "source_mean_noise_estimate": float(
                                arrays["source_mean_noise_estimate"][index]
                            ),
                            "ideal_variance": variance if np.isfinite(variance) else None,
                            "gaussian_coverage_diagnostic": coverage,
                            "gaussian_mean_width_diagnostic": float(2 * width.mean())
                            if coverage is not None
                            else None,
                        }
                    )
    _write_csv(output / "metrics.csv", rows)
    manifest.update(
        state="complete",
        completed_at=utc_now(),
        runtime_seconds=time.perf_counter() - started,
        source_coordinates={
            "rank": coordinates.rank,
            "explained_fraction": coordinates.explained_fraction,
            "source_half_noise": coordinates.source_half_noise,
        },
        results_sha256=file_hash(output / "metrics.csv"),
        resources_end=resource_record(output),
        limitations=[
            "Intervals are ideal Gaussian diagnostics; post-selection coverage is unvalidated.",
            "Scalar variances omit gene heteroskedasticity, guide/batch effects "
            "and source-coordinate uncertainty.",
            "Unregularized ideal variances do not account for ridge shrinkage bias.",
            "The discrepancy objective uses fixed-kernel variance as a surrogate "
            "for the ridge predictor's residual risk.",
            "Seeds and cells are not independent biological replicates.",
            "Local residual baseline is an adaptation, not a PerturbMap reproduction.",
            "Fixed-grid settings have not yet been tuned on a development validation design.",
        ],
    )
    write_json(output / "manifest.json", manifest)
    return manifest
