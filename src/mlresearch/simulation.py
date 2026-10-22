"""Small offline generative experiments with independently controlled mechanisms."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from mlresearch.episodes import EpisodeConfig, build_episode
from mlresearch.experiment import RunConfig, run_experiment
from mlresearch.policies import PolicyConfig
from mlresearch.provenance import file_hash, write_json


@dataclass(frozen=True)
class SimulationConfig:
    seed: int = 71
    interventions: int = 24
    genes: int = 64
    latent_rank: int = 3
    source_cells: int = 32
    acquisition_cells: int = 24
    assessment_cells: int = 24
    controls_each_bank: int = 64
    mechanism_shift: float = 0.0
    measurement_noise: float = 1.0
    source_feature_error: float = 0.0
    control_noise_multiplier: float = 1.0
    calibration_last_axis_scale: float = 1.0

    def __post_init__(self) -> None:
        for name in (
            "seed",
            "interventions",
            "genes",
            "latent_rank",
            "source_cells",
            "acquisition_cells",
            "assessment_cells",
            "controls_each_bank",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < (0 if name == "seed" else 2)
            ):
                raise ValueError(f"Invalid simulation integer: {name}")
        for name in (
            "mechanism_shift",
            "measurement_noise",
            "source_feature_error",
            "control_noise_multiplier",
            "calibration_last_axis_scale",
        ):
            value = getattr(self, name)
            if not np.isfinite(value) or value < 0:
                raise ValueError(f"Invalid simulation scale: {name}")
        if self.measurement_noise == 0 or self.control_noise_multiplier == 0:
            raise ValueError("Noise scales must be positive")


def make_simulation(directory: Path, config: SimulationConfig) -> dict[str, Any]:
    if directory.exists():
        raise ValueError("Simulation directory exists")
    rng = np.random.default_rng(config.seed)
    names = [f"target-{i:03}" for i in range(config.interventions)]
    genes = [f"gene-{i:04}" for i in range(config.genes)]
    latent = rng.normal(size=(config.interventions, config.latent_rank))
    query_count = max(1, int(config.interventions * 0.25))
    query_names = set(np.random.default_rng(config.seed).permutation(names).tolist()[:query_count])
    for index, identity in enumerate(names):
        if identity not in query_names:
            latent[index, -1] *= config.calibration_last_axis_scale
    source_loadings = rng.normal(scale=0.3, size=(config.latent_rank, config.genes))
    target_loadings = rng.normal(scale=0.3, size=(config.latent_rank, config.genes))
    source_effects = latent @ source_loadings + config.source_feature_error * rng.normal(
        size=(config.interventions, config.genes)
    )
    nonlinear = np.sin(latent[:, :1]) * rng.normal(scale=0.3, size=(1, config.genes))
    target_effects = latent @ target_loadings + config.mechanism_shift * nonlinear
    directory.mkdir(parents=True)
    write_json(directory / "generative-configuration.json", asdict(config))
    for label, effects in (("source", source_effects), ("target", target_effects)):
        output = directory / label
        output.mkdir()
        controls = 2 * config.controls_each_bank
        cells = (
            config.source_cells
            if label == "source"
            else config.acquisition_cells + config.assessment_cells
        )
        baseline = rng.normal(scale=0.5, size=config.genes)
        values = [
            baseline
            + rng.normal(
                scale=config.measurement_noise * config.control_noise_multiplier,
                size=(controls, config.genes),
            )
        ]
        interventions = ["control"] * controls
        guides = ["negative-control"] * controls
        for index, identity in enumerate(names):
            values.append(
                baseline
                + effects[index]
                + rng.normal(scale=config.measurement_noise, size=(cells, config.genes))
            )
            interventions.extend([identity] * cells)
            guides.extend([identity + "-guide"] * cells)
        matrix = np.concatenate(values).astype(np.float32)
        identifiers = [f"{label}:cell-{i:06}" for i in range(len(matrix))]
        metadata = {
            "genes": genes,
            "cell_ids": identifiers,
            "original_cell_ids": identifiers,
            "contexts": [label] * len(matrix),
            "interventions": interventions,
            "guides": guides,
            "batches": ["synthetic"] * len(matrix),
            "control_labels": ["control"],
        }
        np.save(output / "values.npy", matrix)
        write_json(output / "metadata.json", metadata)
        write_json(
            output / "manifest.json",
            {
                "state": "complete",
                "schema_version": 1,
                "configuration": asdict(config),
                "input_sha256": "synthetic:" + label,
                "metadata_sha256": file_hash(output / "metadata.json"),
                "values_sha256": file_hash(output / "values.npy"),
                "shape": list(matrix.shape),
                "transformation": (
                    "Simulated continuous expression; as provided, not count log fold changes."
                ),
            },
        )
    # Truth is deliberately outside the episode/public policy objects.
    np.savez(
        directory / "generative-truth.npz",
        source_effects=source_effects,
        target_effects=target_effects,
        latent=latent,
    )
    return asdict(config)


def run_demo(directory: Path, *, seed: int = 71, full: bool = False) -> dict[str, Any]:
    simulation = SimulationConfig(seed=seed)
    make_simulation(directory / "data", simulation)
    episode = directory / "episode"
    build_episode(
        EpisodeConfig(
            str(directory / "data/source"),
            str(directory / "data/target"),
            "source",
            "target",
            str(episode),
            seed=seed,
            acquisition_cells=simulation.acquisition_cells,
            assessment_cells=simulation.assessment_cells,
            acquisition_controls=simulation.controls_each_bank,
            assessment_controls=simulation.controls_each_bank,
        )
    )
    config = RunConfig(
        str(episode),
        str(directory / "experiment"),
        budgets=[96, 144, 192],
        seeds=[0, 1, 2, 3, 4] if full else [0],
        policies=list(("random_equal", "worst_query", "bias_aware")),
        policy=PolicyConfig(rank=3),
        label="offline-synthetic-demo",
    )
    write_json(directory / "run-config.json", asdict(config))
    return run_experiment(config)
