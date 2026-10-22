"""Sequential acquisition followed by a joint, authenticated scoring barrier."""

from __future__ import annotations

import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from mlresearch.episodes import load_public_episode
from mlresearch.experiment import (
    RunConfig,
    run_experiment,
    score_frozen_experiment,
    verify_frozen_predictions,
)
from mlresearch.provenance import (
    environment_record,
    file_hash,
    object_hash,
    read_json,
    resource_record,
    snapshot_sources,
    utc_now,
    write_json,
)


@dataclass(frozen=True)
class ExternalConfig:
    output_directory: str
    runs: list[RunConfig]
    evidence_files: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.runs) < 2 or any(not run.defer_assessment for run in self.runs):
            raise ValueError("A joint suite needs at least two deferred runs")
        root = Path(self.output_directory).resolve()
        paths = [Path(run.output_directory).resolve() for run in self.runs]
        if len(set(paths)) != len(paths):
            raise ValueError("Joint run directories must be distinct")
        if any(path == root or path in root.parents or root in path.parents for path in paths):
            raise ValueError("Suite and run output directories must not contain each other")
        if any(a in b.parents for a in paths for b in paths if a != b):
            raise ValueError("Run output directories must not contain each other")
        if len(set(self.evidence_files)) != len(self.evidence_files):
            raise ValueError("Duplicate evidence file declarations")
        declared = {Path(name).resolve() for name in self.evidence_files}
        required = {
            Path(name).resolve()
            for run in self.runs
            for name in (run.identifier_record, run.development_resource_record)
            if name is not None
        }
        if required - declared:
            raise ValueError("Joint evidence must include every identifier/development record")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ExternalConfig:
        try:
            return cls(**(value | {"runs": [RunConfig.from_dict(v) for v in value["runs"]]}))
        except TypeError as error:
            raise ValueError(f"Invalid external suite: {error}") from error

    @classmethod
    def load(cls, path: Path) -> ExternalConfig:
        return cls.from_dict(read_json(path))


def _configuration(root: Path) -> tuple[dict[str, Any], ExternalConfig]:
    manifest = read_json(root / "manifest.json")
    if object_hash(manifest["configuration"]) != manifest["configuration_sha256"]:
        raise ValueError("Joint suite configuration changed")
    config = ExternalConfig.from_dict(manifest["configuration"])
    if Path(config.output_directory).resolve() != root.resolve():
        raise ValueError("Joint suite directory differs from its declaration")
    if environment_record()["source_tree_sha256"] != manifest["environment"]["source_tree_sha256"]:
        raise ValueError("Package sources changed during the joint suite")
    for item in manifest["evidence"]:
        if (
            file_hash(root / item["snapshot"]) != item["sha256"]
            or file_hash(Path(item["original"])) != item["sha256"]
        ):
            raise ValueError("Declared evaluation evidence changed")
    return manifest, config


def validate_joint_freeze(gate: Path) -> dict[str, Any]:
    """Recheck all frozen indexes before any one run opens scorer outcomes."""
    root = gate.parent
    manifest, config = _configuration(root)
    if gate.name != "joint-prediction-freeze.json" or file_hash(gate) != manifest.get(
        "joint_gate_sha256"
    ):
        raise ValueError("Joint prediction gate is absent or changed")
    freeze = read_json(gate)
    if freeze["configuration_sha256"] != manifest["configuration_sha256"] or len(
        freeze["runs"]
    ) != len(config.runs):
        raise ValueError("Joint gate does not contain every declared run")
    for entry, declaration in zip(freeze["runs"], config.runs, strict=True):
        output = Path(declaration.output_directory).resolve()
        archived_path = root / entry["acquisition_manifest"]
        if (
            entry["run_directory"] != str(output)
            or entry["configuration_sha256"] != object_hash(asdict(declaration))
            or file_hash(archived_path) != entry["acquisition_manifest_sha256"]
        ):
            raise ValueError("Joint gate run declaration or acquisition record changed")
        archived = read_json(archived_path)
        current = read_json(output / "manifest.json")
        if archived["state"] != "predictions_frozen" or current["state"] not in (
            "predictions_frozen",
            "complete",
        ):
            raise ValueError("Every joint prediction must be frozen before scoring")
        for key, value in archived.items():
            if key != "state" and current.get(key) != value:
                raise ValueError(f"Immutable acquisition manifest field changed: {key}")
        for record in (archived, current):
            if (
                record["configuration_sha256"] != entry["configuration_sha256"]
                or object_hash(record["configuration"]) != entry["configuration_sha256"]
                or record["predictions_sha256"] != entry["predictions_sha256"]
                or record["environment"]["source_tree_sha256"]
                != manifest["environment"]["source_tree_sha256"]
            ):
                raise ValueError("Frozen run configuration, predictions or sources changed")
        if file_hash(output / "prediction-index.json") != entry["predictions_sha256"]:
            raise ValueError("A peer prediction index changed before scoring")
        if current["state"] == "complete":
            binding = current.get("joint_prediction_freeze", {})
            if binding.get("sha256") != manifest["joint_gate_sha256"]:
                raise ValueError("A completed peer was scored outside this joint freeze")
            access = read_json(output / "assessment-access.json")
            if (
                file_hash(output / "metrics.csv") != current["results_sha256"]
                or access["prediction_index_sha256_before_opening"] != entry["predictions_sha256"]
                or access["joint_prediction_freeze"]["sha256"] != manifest["joint_gate_sha256"]
            ):
                raise ValueError("Completed peer results or assessment access changed")
    return freeze


def _seal(root: Path) -> Path:
    manifest, config = _configuration(root)
    entries = []
    for number, declaration in enumerate(config.runs):
        output = Path(declaration.output_directory).resolve()
        current = read_json(output / "manifest.json")
        if current["state"] != "predictions_frozen" or current[
            "configuration_sha256"
        ] != object_hash(asdict(declaration)):
            raise ValueError("Every declared run must finish acquisition before sealing")
        if any(
            (output / name).exists()
            for name in ("assessment-access.json", "assessment.npz", "metrics.csv")
        ):
            raise ValueError("A deferred run opened its scorer before the joint freeze")
        public = load_public_episode(Path(declaration.episode_directory))
        verify_frozen_predictions(output, current, public)
        archive = Path("acquisition-manifests") / f"run-{number}.json"
        (root / archive).parent.mkdir(exist_ok=True)
        shutil.copyfile(output / "manifest.json", root / archive)
        entries.append(
            {
                "run_directory": str(output),
                "configuration_sha256": current["configuration_sha256"],
                "predictions_sha256": current["predictions_sha256"],
                "acquisition_manifest": archive.as_posix(),
                "acquisition_manifest_sha256": file_hash(root / archive),
            }
        )
    gate = root / "joint-prediction-freeze.json"
    write_json(
        gate,
        {
            "configuration_sha256": manifest["configuration_sha256"],
            "frozen_at": utc_now(),
            "runs": entries,
            "boundary": "All declared predictions and paid ledgers authenticated before scoring.",
        },
    )
    manifest.update(state="all_predictions_frozen", joint_gate_sha256=file_hash(gate))
    write_json(root / "manifest.json", manifest)
    validate_joint_freeze(gate)
    return gate


def score_suite(root: Path) -> dict[str, Any]:
    """Resume scoring a sealed suite; a completed peer never acquires/refits again."""
    started = time.perf_counter()
    gate = root / "joint-prediction-freeze.json"
    freeze = validate_joint_freeze(gate)
    manifest, _ = _configuration(root)
    # A resumed suite may have sat on disk after sealing. Authenticate every
    # peer's actual artifacts again before opening even the first scorer.
    for entry in freeze["runs"]:
        output = Path(entry["run_directory"])
        current = read_json(output / "manifest.json")
        public = load_public_episode(Path(current["configuration"]["episode_directory"]))
        verify_frozen_predictions(output, current, public)
    if manifest["state"] == "complete":
        if any(
            read_json(Path(entry["run_directory"]) / "manifest.json")["state"] != "complete"
            for entry in freeze["runs"]
        ):
            raise ValueError("Completed suite has an incomplete peer")
        return manifest
    manifest["state"] = "scoring"
    write_json(root / "manifest.json", manifest)
    for entry in freeze["runs"]:
        output = Path(entry["run_directory"])
        if read_json(output / "manifest.json")["state"] != "complete":
            score_frozen_experiment(output, gate)
    manifest.update(
        state="complete",
        completed_at=utc_now(),
        resources_end=resource_record(root),
        scoring_pass_runtime_seconds=time.perf_counter() - started,
        run_runtime_seconds=sum(
            read_json(Path(e["run_directory"]) / "manifest.json")["runtime_seconds"]
            for e in freeze["runs"]
        ),
    )
    write_json(root / "manifest.json", manifest)
    return manifest


def run_suite(config: ExternalConfig) -> dict[str, Any]:
    started = time.perf_counter()
    root = Path(config.output_directory)
    if root.exists() or any(Path(run.output_directory).exists() for run in config.runs):
        raise ValueError("Suite or run output exists; preserve it and use a fresh declaration")
    environment = environment_record()
    root.mkdir(parents=True)
    evidence = []
    for number, name in enumerate(config.evidence_files):
        original = Path(name)
        snapshot = Path("frozen-evidence") / f"{number}-{original.name}"
        (root / snapshot).parent.mkdir(exist_ok=True)
        shutil.copyfile(original, root / snapshot)
        evidence.append(
            {
                "original": str(original),
                "snapshot": snapshot.as_posix(),
                "sha256": file_hash(original),
            }
        )
    manifest = {
        "state": "acquiring",
        "configuration": asdict(config),
        "configuration_sha256": object_hash(asdict(config)),
        "environment": environment,
        "source_snapshot": snapshot_sources(root / "code.zip", environment["source_hashes"]),
        "resources_start": resource_record(root),
        "evidence": evidence,
        "workers": 1,
    }
    write_json(root / "manifest.json", manifest)
    try:
        for run in config.runs:
            _configuration(root)
            result = run_experiment(run)
            if result["state"] != "predictions_frozen":
                raise ValueError("A joint run did not defer its assessment")
        _seal(root)
        result = score_suite(root)
        result["uninterrupted_suite_runtime_seconds"] = time.perf_counter() - started
        write_json(root / "manifest.json", result)
        return result
    except Exception as error:
        current = read_json(root / "manifest.json")
        current.update(error_type=type(error).__name__, error=str(error), failed_at=utc_now())
        write_json(root / "manifest.json", current)
        raise
