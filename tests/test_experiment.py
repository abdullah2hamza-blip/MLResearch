import csv
import hashlib
import shutil
import zipfile
from dataclasses import asdict

import numpy as np
import pytest

from mlresearch.episodes import EpisodeConfig, build_episode, load_public_episode
from mlresearch.experiment import RunConfig, run_experiment
from mlresearch.models import Observations, source_coordinates
from mlresearch.policies import Policy, PolicyConfig
from mlresearch.provenance import file_hash, read_json, write_json
from mlresearch.simulation import SimulationConfig, make_simulation


def fixture(tmp_path):
    data = tmp_path / "data"
    config = SimulationConfig(
        interventions=12,
        genes=12,
        latent_rank=2,
        acquisition_cells=8,
        assessment_cells=8,
        controls_each_bank=16,
    )
    make_simulation(data, config)
    episode = tmp_path / "episode"
    build_episode(
        EpisodeConfig(
            str(data / "source"),
            str(data / "target"),
            "source",
            "target",
            str(episode),
            acquisition_cells=8,
            assessment_cells=8,
            acquisition_controls=16,
            assessment_controls=16,
        )
    )
    return data, episode


def config(episode, output, policies=None):
    return RunConfig(
        str(episode),
        str(output),
        budgets=[32, 48],
        seeds=[0],
        policies=policies or ["random_equal", "worst_query", "bias_aware"],
        policy=PolicyConfig(
            rank=2, pilot_controls=4, pilot_interventions=3, block_cells=4, setup_cost=2
        ),
    )


def refresh_prepared(path):
    manifest = read_json(path / "manifest.json")
    manifest["metadata_sha256"] = file_hash(path / "metadata.json")
    manifest["values_sha256"] = file_hash(path / "values.npy")
    write_json(path / "manifest.json", manifest)


def test_offline_end_to_end_is_deterministic_and_pays_for_all_visible_cells(tmp_path):
    _, episode = fixture(tmp_path)
    outputs = [tmp_path / "first", tmp_path / "second"]
    for output in outputs:
        result = run_experiment(config(episode, output))
        assert result["state"] == "complete"
        assert result["configuration"]["seeds"] == [0]
        with zipfile.ZipFile(output / "code.zip") as archive:
            for name, checksum in result["environment"]["source_hashes"].items():
                assert hashlib.sha256(archive.read("mlresearch/" + name)).hexdigest() == checksum
        access = read_json(output / "assessment-access.json")
        assert access["prediction_index_sha256_before_opening"] == result["predictions_sha256"]
    for name in config(episode, outputs[0]).policies:
        first = outputs[0] / "seed-0" / name
        second = outputs[1] / "seed-0" / name
        assert (first / "ledger.jsonl").read_text() == (second / "ledger.jsonl").read_text()
        for budget in [32, 48]:
            with (
                np.load(first / f"budget-{budget}.npz") as a,
                np.load(second / f"budget-{budget}.npz") as b,
            ):
                for key in a.files:
                    np.testing.assert_array_equal(a[key], b[key])
    banks = read_json(episode / "private-banks.json")
    acquired = {x for ids in banks["acquisition_cell_ids"].values() for x in ids}
    assessed = {x for ids in banks["assessment_cell_ids"].values() for x in ids}
    assert not acquired & assessed
    assert not set(load_public_episode(episode).query_ids) & set(banks["acquisition_rows"])
    with (outputs[0] / "metrics.csv").open() as stream:
        metrics = list(csv.DictReader(stream))
    assert len(metrics) == 3 * 2 * 7 * 3
    assert all(int(row["spent"]) <= int(row["budget"]) for row in metrics)


def test_sealed_query_and_assessment_control_changes_cannot_change_predictions(tmp_path):
    data, episode = fixture(tmp_path)
    first = tmp_path / "first"
    run_experiment(config(episode, first, ["worst_query"]))
    banks = read_json(episode / "private-banks.json")
    queries = load_public_episode(episode).query_ids
    matrix = np.load(data / "target/values.npy", mmap_mode="r+")
    sealed_rows = [
        row for identity in ["__control__", *queries] for row in banks["assessment_rows"][identity]
    ]
    matrix[sealed_rows, :] += 500
    matrix.flush()
    del matrix
    refresh_prepared(data / "target")
    new_episode = tmp_path / "changed-episode"
    declaration = read_json(episode / "manifest.json")["configuration"]
    declaration["output_directory"] = str(new_episode)
    build_episode(EpisodeConfig(**declaration))
    second = tmp_path / "second"
    run_experiment(config(new_episode, second, ["worst_query"]))
    for budget in [32, 48]:
        with (
            np.load(first / f"seed-0/worst_query/budget-{budget}.npz") as a,
            np.load(second / f"seed-0/worst_query/budget-{budget}.npz") as b,
        ):
            for key in a.files:
                np.testing.assert_array_equal(a[key], b[key])
    assert (first / "seed-0/worst_query/ledger.jsonl").read_text() == (
        second / "seed-0/worst_query/ledger.jsonl"
    ).read_text()


def test_query_variance_policy_does_not_reward_irrelevant_rank_gain():
    from mlresearch.acquisition import CONTROL, Purchase
    from mlresearch.episodes import PublicEpisode

    ids = ("A", "B", "C", "Q")
    effects = np.array([[-1.0, 0], [1, np.sqrt(2)], [1, -np.sqrt(2)], [-1, 0]])
    public = PublicEpisode(
        ids,
        ("Q",),
        ("A", "B", "C"),
        ("g1", "g2"),
        effects,
        np.ones(4),
        np.ones(4),
        np.zeros((4, 2)),
    )
    observations = Observations()
    for identity in [CONTROL, "A"]:
        observations.update(
            Purchase(
                identity,
                tuple(f"{identity}-{i}" for i in range(4)),
                np.tile([[-1.0], [1.0], [-1.0], [1.0]], (1, 2)),
                4,
                4,
            )
        )
    state = {
        "setup_cost": 0,
        "cell_cost": 1,
        "control_cell_cost": 1,
        "spent": 8,
        "budget": 100,
        "counts": {CONTROL: 4, "A": 4, "B": 0, "C": 0},
        "remaining_cells": {CONTROL: 4, "A": 4, "B": 4, "C": 4},
    }
    declaration = PolicyConfig(
        rank=2, block_cells=4, pilot_controls=4, pilot_interventions=1, setup_cost=0
    )
    action = Policy("worst_query", public, source_coordinates(public, 2), declaration, 0).choose(
        state, observations, 12
    )
    assert action.intervention in (CONTROL, "A")


def test_gene_alignment_is_by_identifier_and_guide_conflicts_are_rejected(tmp_path):
    data, episode = fixture(tmp_path)
    target = data / "target"
    matrix = np.load(target / "values.npy")[:, ::-1]
    np.save(target / "values.npy", matrix)
    metadata = read_json(target / "metadata.json")
    metadata["genes"] = metadata["genes"][::-1]
    write_json(target / "metadata.json", metadata)
    refresh_prepared(target)
    declaration = read_json(episode / "manifest.json")["configuration"]
    declaration["output_directory"] = str(tmp_path / "reordered")
    build_episode(EpisodeConfig(**declaration))
    original = read_json(episode / "private-banks.json")["target_columns"]
    reordered = read_json(tmp_path / "reordered/private-banks.json")["target_columns"]
    assert reordered == [len(original) - 1 - column for column in original]
    metadata["guides"] = ["same-guide"] * len(metadata["guides"])
    write_json(target / "metadata.json", metadata)
    refresh_prepared(target)
    declaration["output_directory"] = str(tmp_path / "bad-guide")
    with pytest.raises(ValueError, match="guide maps"):
        build_episode(EpisodeConfig(**declaration))


def test_policy_interface_contains_no_recipient_arrays_or_scorer(tmp_path):
    _, episode = fixture(tmp_path)
    public = load_public_episode(episode)
    policy = Policy("worst_query", public, source_coordinates(public, 2), PolicyConfig(), 0)
    assert set(asdict(public)) == {
        "interventions",
        "query_ids",
        "candidate_ids",
        "genes",
        "source_effects",
        "source_per_cell_variance",
        "source_effect_mean_variance",
        "source_half_difference",
    }
    assert not any(
        "path" in key or "scorer" in key or "target_values" in key for key in vars(policy)
    )
    assert not Observations().moments
    with pytest.raises(ValueError, match="common pilot"):
        RunConfig(str(episode), "unused", budgets=[1])


def test_frozen_episode_can_be_relocated_with_its_data(tmp_path):
    data, episode = fixture(tmp_path)
    from pathlib import Path

    assert not Path(read_json(episode / "private-banks.json")["target_prepared"]).is_absolute()
    relocated = tmp_path / "relocated"
    relocated.mkdir()
    shutil.copytree(data, relocated / "data")
    shutil.copytree(episode, relocated / "episode")
    result = run_experiment(config(relocated / "episode", relocated / "run", ["worst_query"]))
    assert result["state"] == "complete"
