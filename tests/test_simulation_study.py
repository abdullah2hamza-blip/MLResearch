from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pytest

from mlresearch.policies import PolicyConfig
from mlresearch.provenance import environment_record, object_hash, read_json, write_json
from mlresearch.simulation import SimulationConfig, make_simulation
from mlresearch.study import StudyConfig, _run_case, summarize_study


def tiny_simulation():
    return SimulationConfig(
        seed=9,
        interventions=8,
        genes=8,
        latent_rank=2,
        source_cells=4,
        acquisition_cells=4,
        assessment_cells=4,
        controls_each_bank=4,
        source_measurement_noise=0.5,
    )


def test_simulation_axes_do_not_change_unrelated_response_banks(tmp_path):
    base = tiny_simulation()
    for name, config in (
        ("base", base),
        ("source_noise", replace(base, source_measurement_noise=0)),
        ("source_error", replace(base, source_feature_error=1)),
        ("recipient_noise", replace(base, measurement_noise=2)),
        ("blocks", replace(base, batch_noise_scale=1)),
    ):
        make_simulation(tmp_path / name, config)
    target = np.load(tmp_path / "base/target/values.npy")
    for name in ["source_noise", "source_error"]:
        np.testing.assert_array_equal(target, np.load(tmp_path / name / "target/values.npy"))
    source = np.load(tmp_path / "base/source/values.npy")
    for name in ["recipient_noise", "blocks"]:
        np.testing.assert_array_equal(source, np.load(tmp_path / name / "source/values.npy"))
    delta = np.load(tmp_path / "blocks/target/values.npy") - target
    np.testing.assert_allclose(delta[0], delta[4], atol=1e-6)
    with np.load(tmp_path / "source_error/generative-truth.npz") as arrays:
        assert np.mean((arrays["source_effects"] - arrays["latent_source_effects"]) ** 2) > 0.5


def test_controlled_case_freezes_config_then_scores_truth_without_policy_access(tmp_path):
    policy = PolicyConfig(
        rank=2,
        block_cells=4,
        pilot_controls=4,
        pilot_interventions=3,
        setup_cost=2,
        ridge_include_null=True,
        partial_blocks=True,
        variance_prior="paid_ratio",
    )
    config = StudyConfig(
        str(tmp_path / "study"),
        {"baseline": {}},
        tiny_simulation(),
        policy,
        generative_seeds=[9],
        acquisition_seeds=[0],
        budgets=[24, 32],
        policies=["worst_query", "bias_aware"],
        workers=1,
    )
    declaration = tmp_path / "config.json"
    write_json(declaration, asdict(config))
    payload = {
        "configuration_path": str(declaration),
        "source_sha256": environment_record()["source_tree_sha256"],
        "configuration_sha256": object_hash(asdict(config)),
        "seed": 9,
        "scenario": "baseline",
    }
    result = _run_case(payload)
    run = Path(result["run"])
    assert read_json(run / "manifest.json")["state"] == "complete"
    truth_access = read_json(run / "truth-access.json")
    assert truth_access["role"] == "scorer_only_oracle_diagnostic"
    assert (
        truth_access["prediction_index_sha256_before_opening"]
        == read_json(run / "manifest.json")["predictions_sha256"]
    )
    summary = summarize_study(tmp_path / "study", [result], config)
    assert summary["cases"] == 1
    assert all(row["monte_carlo_standard_error"] is None for row in summary["comparisons"])
    changed = asdict(config)
    changed["budgets"] = [24, 36]
    write_json(declaration, changed)
    with pytest.raises(ValueError, match="configuration changed"):
        _run_case(payload)
