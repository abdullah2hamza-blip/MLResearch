from dataclasses import asdict, replace

import pytest

from mlresearch import experiment, external
from mlresearch.episodes import EpisodeConfig, build_episode, load_public_episode
from mlresearch.experiment import RunConfig, run_experiment
from mlresearch.external import ExternalConfig, run_suite, score_suite, validate_joint_freeze
from mlresearch.identifiers import verify_identifier_record
from mlresearch.policies import PolicyConfig
from mlresearch.provenance import file_hash, read_json, write_json
from mlresearch.simulation import SimulationConfig, make_simulation


@pytest.fixture
def declaration(tmp_path):
    data, episode = tmp_path / "data", tmp_path / "episode"
    make_simulation(
        data,
        SimulationConfig(
            interventions=8,
            genes=8,
            latent_rank=2,
            source_cells=4,
            acquisition_cells=4,
            assessment_cells=4,
            controls_each_bank=4,
        ),
    )
    build_episode(
        EpisodeConfig(
            str(data / "source"),
            str(data / "target"),
            "source",
            "target",
            str(episode),
            min_source_cells=4,
            acquisition_cells=4,
            assessment_cells=4,
            acquisition_controls=4,
            assessment_controls=4,
        )
    )
    run = RunConfig(
        str(episode),
        str(tmp_path / "first"),
        budgets=[24, 32],
        seeds=[0],
        policies=["worst_query"],
        policy=PolicyConfig(
            rank=2, block_cells=4, pilot_controls=4, pilot_interventions=3, setup_cost=2
        ),
        defer_assessment=True,
    )
    return ExternalConfig(
        str(tmp_path / "suite"), [run, replace(run, output_directory=str(tmp_path / "second"))]
    )


def test_deferred_acquisition_never_opens_scorer(declaration, monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("Scorer opened during deferred acquisition")

    monkeypatch.setattr(experiment, "_assessment", forbidden)
    run = declaration.runs[0]
    result = run_experiment(run)
    assert result["state"] == "predictions_frozen"
    from pathlib import Path

    output = Path(run.output_directory)
    assert all(
        not (output / name).exists()
        for name in ("assessment-access.json", "assessment.npz", "metrics.csv")
    )
    assert len(read_json(output / "prediction-index.json")) == 2


def test_every_joint_prediction_precedes_first_assessment_and_scoring_is_idempotent(
    declaration, monkeypatch
):
    from pathlib import Path

    calls = []
    original = experiment._assessment
    root = Path(declaration.output_directory)

    def assessed(*args, **kwargs):
        freeze = validate_joint_freeze(root / "joint-prediction-freeze.json")
        assert len(freeze["runs"]) == 2
        assert all(
            read_json(root / item["acquisition_manifest"])["state"] == "predictions_frozen"
            for item in freeze["runs"]
        )
        calls.append(len(calls))
        return original(*args, **kwargs)

    monkeypatch.setattr(experiment, "_assessment", assessed)
    assert run_suite(declaration)["state"] == "complete"
    assert calls == [0, 1]
    for run in declaration.runs:
        access = read_json(Path(run.output_directory) / "assessment-access.json")
        assert access["joint_prediction_freeze"]["sha256"] == file_hash(
            root / "joint-prediction-freeze.json"
        )
    assert score_suite(root)["state"] == "complete"
    assert calls == [0, 1]


@pytest.mark.parametrize(
    "artifact",
    [
        "prediction-index.json",
        "seed-0/worst_query/budget-32.npz",
        "manifest_episode",
        "manifest_development",
    ],
)
def test_corrupted_peer_blocks_first_scorer_then_resumes_without_reacquisition(
    declaration, monkeypatch, artifact
):
    from pathlib import Path

    original = external.score_frozen_experiment

    def interrupted(*_args, **_kwargs):
        raise RuntimeError("Simulated interruption after all predictions froze")

    monkeypatch.setattr(external, "score_frozen_experiment", interrupted)
    with pytest.raises(RuntimeError, match="Simulated interruption"):
        run_suite(declaration)
    root = Path(declaration.output_directory)
    ledgers = {
        run.output_directory: (
            Path(run.output_directory) / "seed-0/worst_query/ledger.jsonl"
        ).read_bytes()
        for run in declaration.runs
    }
    changed = Path(declaration.runs[1].output_directory) / (
        "manifest.json" if artifact.startswith("manifest_") else artifact
    )
    saved = changed.read_bytes()
    if artifact.startswith("manifest_"):
        value = read_json(changed)
        if artifact == "manifest_episode":
            value["episode_manifest_sha256"] = "0" * 64
        else:
            value["fixed_development_resources"]["unique_resource_cost_units"] = 999
        write_json(changed, value)
    else:
        changed.write_bytes(saved + b"\n")

    def forbidden(*_args, **_kwargs):
        pytest.fail("A scorer opened despite a corrupted peer")

    with monkeypatch.context() as patch:
        patch.setattr(experiment, "_assessment", forbidden)
        with pytest.raises(
            ValueError,
            match="prediction index changed|prediction artifact changed|Immutable acquisition",
        ):
            score_suite(root)
    changed.write_bytes(saved)
    monkeypatch.setattr(external, "score_frozen_experiment", original)
    assert score_suite(root)["state"] == "complete"
    for path, expected in ledgers.items():
        assert (Path(path) / "seed-0/worst_query/ledger.jsonl").read_bytes() == expected


def test_suite_requires_declared_records_and_validated_deferred_configuration(
    declaration, tmp_path
):
    with pytest.raises(ValueError, match="deferred"):
        replace(
            declaration, runs=[replace(run, defer_assessment=False) for run in declaration.runs]
        )
    with pytest.raises(ValueError, match="evidence"):
        replace(
            declaration,
            runs=[replace(run, identifier_record="missing.json") for run in declaration.runs],
        )
    path = tmp_path / "suite.json"
    write_json(path, asdict(declaration))
    assert ExternalConfig.load(path) == declaration


@pytest.mark.parametrize("mutation", [None, "alias", "gene_mismatch", "unbound_episode"])
def test_canonical_guard_binds_raw_inputs_axes_and_gene_split(declaration, tmp_path, mutation):
    from pathlib import Path

    episode = Path(declaration.runs[0].episode_directory)
    public = load_public_episode(episode)
    manifest = read_json(episode / "manifest.json")
    target_ids = {label: f"canonical-{i}" for i, label in enumerate(public.interventions)}
    genes = {gene: f"stable-{i}" for i, gene in enumerate(public.genes)}
    record = {
        "state": "complete",
        "metadata_only": True,
        "episode_manifest_sha256": {str(episode): file_hash(episode / "manifest.json")},
        "datasets": {
            arm: {
                "raw_sha256": manifest["prepared_inputs"][arm]["input_sha256"],
                "eligible_target_to_canonical": dict(target_ids),
                "aligned_expression_gene_to_canonical": dict(genes),
            }
            for arm in ("source", "target")
        },
    }
    if mutation == "alias":
        record["datasets"]["source"]["eligible_target_to_canonical"][public.query_ids[0]] = (
            target_ids[public.candidate_ids[0]]
        )
    elif mutation == "gene_mismatch":
        record["datasets"]["target"]["aligned_expression_gene_to_canonical"][public.genes[0]] = (
            "different"
        )
    elif mutation == "unbound_episode":
        record["episode_manifest_sha256"] = {"different": "0" * 64}
    path = tmp_path / "identifiers.json"
    write_json(path, record)
    if mutation:
        with pytest.raises(ValueError, match="Canonical"):
            verify_identifier_record(
                public, manifest, path, episode_sha256=file_hash(episode / "manifest.json")
            )
    else:
        summary = verify_identifier_record(
            public, manifest, path, episode_sha256=file_hash(episode / "manifest.json")
        )
        assert summary["canonical_targets"] == 8
        run = replace(declaration.runs[0], identifier_record=str(path))
        assert run_experiment(run)["canonical_identifier_audit"] == summary
