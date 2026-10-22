import numpy as np
import pytest

from mlresearch.episodes import EpisodeConfig, build_episode
from mlresearch.experiment import RunConfig, run_experiment
from mlresearch.policies import PolicyConfig
from mlresearch.provenance import file_hash, read_json, write_json
from mlresearch.simulation import SimulationConfig, make_simulation
from mlresearch.uncertainty import analyze_run, area_weights, projected_summary


def test_paired_projection_exactly_matches_direct_quadratic_area():
    rng = np.random.default_rng(43)
    budgets = [10, 15, 30]
    weights = area_weights(budgets)
    a, b = rng.normal(size=(2, 3, 4, 5, 7))
    treatments = rng.normal(size=(5, 8, 7))
    controls = rng.normal(size=(10, 7))
    truth = treatments.mean(axis=1) - controls.mean(axis=0)
    errors = np.mean((a - truth) ** 2 - (b - truth) ** 2, axis=(2, 3))
    direct = np.trapezoid(errors.mean(axis=1), budgets) / (budgets[-1] - budgets[0])
    coefficients = np.einsum("b,bsqg->qg", weights, a - b) / 4
    constants = np.einsum("b,bsq->q", weights, np.mean(a * a - b * b, axis=-1)) / 4
    t_projected = [treatments[i] @ coefficients[i] / 7 for i in range(5)]
    c_projected = controls @ coefficients.T / 7
    result = projected_summary(constants, t_projected, c_projected, samples=2000)
    assert result["paired_difference"] == pytest.approx(direct, abs=1e-14)


def test_shared_control_uncertainty_does_not_shrink_with_duplicate_query_loadings():
    rng = np.random.default_rng(44)
    control = rng.normal(size=100)
    constants = np.zeros(5)
    treatments = [np.zeros(20) for _ in constants]
    controls = np.tile(control[:, None], (1, 5))
    result = projected_summary(constants, treatments, controls, samples=20000)
    check = result["iid_measurement_variance_check"]
    assert check["shared_control_component"] == pytest.approx(4 * control.var(ddof=1) / 100)
    estimated = result["iid_cell_bootstrap_fixed_queries"]["resampling_standard_deviation"] ** 2
    assert estimated == pytest.approx(4 * control.var(ddof=0) / 100, rel=0.04)
    # An independent control resample per query would wrongly divide this by five.
    assert estimated > 4 * check["shared_control_component"] / 5


@pytest.mark.parametrize("missing", ["", "nan", "None", " null ", None, np.nan])
def test_fixed_strata_are_preserved_and_unknown_batches_are_unavailable(missing):
    result = projected_summary(
        np.zeros(2),
        [np.array([0.0, 10.0])] * 2,
        np.tile(np.array([[0.0], [10.0]]), (1, 2)),
        samples=500,
        treatment_strata=[["a", "b"]] * 2,
        control_strata=["a", "b"],
        treatment_batches=[["a", missing]] * 2,
        control_batches=["a", missing],
    )
    strata = result["stratified_cell_bootstrap_fixed_queries"]
    assert strata["resampling_standard_deviation"] == 0
    assert strata["control_strata"]["singleton_strata"] == 2
    assert not result["batch_reweighting_sensitivity"]["available"]


def test_shared_batch_reweighting_cancels_identical_treatment_control_profiles():
    values = np.array([1.0, 1.0, 3.0, 3.0])
    result = projected_summary(
        np.zeros(2),
        [values] * 2,
        np.tile(values[:, None], (1, 2)),
        samples=1000,
        treatment_batches=[["a", "a", "b", "b"]] * 2,
        control_batches=["a", "a", "b", "b"],
    )
    batch = result["batch_reweighting_sensitivity"]
    assert batch["available"]
    assert batch["resampling_standard_deviation"] < 1e-14


def test_completed_run_projection_matches_float32_checkpoint_scoring_and_rejects_tampering(
    tmp_path,
):
    data, episode, run = tmp_path / "data", tmp_path / "episode", tmp_path / "run"
    make_simulation(
        data,
        SimulationConfig(
            interventions=12,
            genes=12,
            latent_rank=2,
            source_cells=4,
            acquisition_cells=8,
            assessment_cells=8,
            controls_each_bank=16,
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
            acquisition_cells=8,
            assessment_cells=8,
            acquisition_controls=16,
            assessment_controls=16,
        )
    )
    run_experiment(
        RunConfig(
            str(episode),
            str(run),
            budgets=[32, 48],
            seeds=[0, 1],
            policies=["worst_query", "bias_aware"],
            policy=PolicyConfig(
                rank=2, block_cells=4, pilot_controls=4, pilot_interventions=3, setup_cost=2
            ),
        )
    )
    output = tmp_path / "uncertainty.json"
    summary = analyze_run(run, output, backbone="ridge", samples=200)
    assert summary["paired_difference"] == pytest.approx(
        summary["original_metric_paired_difference"], abs=1e-13
    )
    with pytest.raises(ValueError, match="distinct"):
        analyze_run(run, tmp_path / "same.json", policy="worst_query", reference="worst_query")
    index_path = run / "prediction-index.json"
    items = read_json(index_path)
    write_json(index_path, items + [items[0]])
    manifest = read_json(run / "manifest.json")
    manifest["predictions_sha256"] = file_hash(index_path)
    write_json(run / "manifest.json", manifest)
    access = read_json(run / "assessment-access.json")
    access["prediction_index_sha256_before_opening"] = manifest["predictions_sha256"]
    write_json(run / "assessment-access.json", access)
    with pytest.raises(ValueError, match="every declared checkpoint once"):
        analyze_run(run, tmp_path / "duplicate.json")
