import numpy as np
import pytest

from mlresearch.transfer import (
    CoefficientMLP,
    TransferConfig,
    calibrate_route,
    descriptors,
    reconstruct,
    response_basis,
)


def test_mlp_gradients_match_finite_differences_including_layernorm_affine():
    rng = np.random.default_rng(5)
    model = CoefficientMLP(4, 2, 3, 8)
    x, y = rng.normal(size=(5, 4)), rng.normal(size=(5, 2))
    _, gradients = model.loss_gradient(x, y)
    for name, parameter in model.parameters.items():
        for index in np.ndindex(parameter.shape):
            value = parameter[index]
            parameter[index] = value + 1e-6
            plus, _ = model.loss_gradient(x, y)
            parameter[index] = value - 1e-6
            minus, _ = model.loss_gradient(x, y)
            parameter[index] = value
            assert gradients[name][index] == pytest.approx((plus - minus) / 2e-6, abs=2e-8)


def test_response_basis_matches_independent_svd_projection():
    rng = np.random.default_rng(6)
    y = rng.normal(size=(8, 20))
    center, basis = response_basis(y, 3)
    _, _, reference = np.linalg.svd(y - y.mean(axis=0), full_matrices=False)
    np.testing.assert_allclose(basis @ basis.T, np.eye(3), atol=1e-12)
    np.testing.assert_allclose(basis.T @ basis, reference[:3].T @ reference[:3], atol=1e-12)
    np.testing.assert_array_equal(center, y.mean(axis=0))


def fixture():
    rng = np.random.default_rng(7)
    genes = tuple(f"g-{i}" for i in range(12))
    source = rng.normal(size=(8, 12))
    recipient = 0.3 * source + rng.normal(scale=0.1, size=(8, 12))
    control = rng.uniform(size=(16, 12))
    queries = rng.normal(size=(3, 12))
    config = TransferConfig(rank=3, hidden=8, anchors=4, max_rounds=5, patience=2)
    return control, genes, list(genes[:8]), recipient, source, list(genes[8:11]), queries, config


def test_query_tokens_cannot_change_train_basis_or_recipient_local_base():
    args = fixture()
    first = reconstruct(*args)
    second = reconstruct(*[*args[:6], args[6] + 10, args[7]])
    np.testing.assert_array_equal(
        first["recipient_local_lowrank"], second["recipient_local_lowrank"]
    )
    for field in ["basis_sha256", "coordinate_mean_sha256", "alpha", "rho", "selected_ridge"]:
        assert first["diagnostics"][field] == second["diagnostics"][field]
    # Validation recipient and source rows are excluded from the fitted response basis.
    validation = first["diagnostics"]["paid_validation_ids"]
    row = args[2].index(validation[0])
    altered = list(args)
    altered[3] = args[3].copy()
    altered[4] = args[4].copy()
    altered[3][row] += 50
    altered[4][row] -= 50
    changed = reconstruct(*altered)
    assert first["diagnostics"]["basis_sha256"] == changed["diagnostics"]["basis_sha256"]


def test_reordering_calibration_rows_preserves_all_predictions():
    args = fixture()
    first = reconstruct(*args)
    order = np.random.default_rng(8).permutation(8)
    changed = reconstruct(
        args[0],
        args[1],
        [args[2][i] for i in order],
        args[3][order],
        args[4][order],
        args[5],
        args[6],
        args[7],
    )
    for key in ["recipient_local_lowrank", "perturbmap_reconstruction"]:
        np.testing.assert_array_equal(first[key], changed[key])


def test_control_descriptor_constant_and_missing_genes_are_explicit():
    values, missing, _ = descriptors(np.ones((4, 3)), ("a", "b", "c"), ["a", "unknown"], 4)
    np.testing.assert_array_equal(values[0, :4], 0)
    np.testing.assert_array_equal(values[0, -3:], [1, 0, 1])
    np.testing.assert_array_equal(values[1], 0)
    assert missing == ["unknown"]


def test_zero_response_and_rank_degenerate_fit_remain_finite():
    args = list(fixture())
    args[3] = np.zeros_like(args[3])
    args[4] = np.zeros_like(args[4])
    args[6] = np.zeros_like(args[6])
    result = reconstruct(*args)
    assert result["diagnostics"]["basis_rank"] == 0
    for key in ["recipient_local_lowrank", "perturbmap_reconstruction"]:
        np.testing.assert_array_equal(result[key], 0)


def test_query_calibration_overlap_rejected():
    args = list(fixture())
    args[5] = [args[2][0], *args[5][1:]]
    with pytest.raises(ValueError, match="overlap"):
        reconstruct(*args)


def test_route_calibration_rejects_zero_weight_and_equal_error():
    target, base = np.zeros((2, 3)), np.ones((2, 3))
    assert calibrate_route(target, base, 2 * base) == (0.0, 0.0)
    assert calibrate_route(target, base, base) == (0.0, 0.0)
    # A perfect base cannot acquire positive reliability from an epsilon denominator.
    assert calibrate_route(target, target, base) == (0.0, 0.0)
    # A small coordinate improvement can be invisible beside a huge squared error.
    # A positive interpolation alone must not imply a positive numerical gain.
    assert calibrate_route(np.zeros(2), np.array([1e20, 1.0]), np.array([1e20, 0.0])) == (
        1.0,
        0.0,
    )


def test_route_calibration_has_exact_analytic_fractional_optimum():
    target, base = np.zeros((2, 3)), np.ones((2, 3))
    assert calibrate_route(target, base, -base) == (0.5, 1.0)
    assert calibrate_route(target, base, target) == (1.0, 1.0)
    # Orthogonal displacement has positive norm but cannot reduce squared error.
    assert calibrate_route(np.array([1.0, 0]), np.zeros(2), np.array([0.0, 1])) == (0.0, 0.0)


def test_route_calibration_rejects_invalid_arrays():
    with pytest.raises(ValueError, match="matching nonempty"):
        calibrate_route(np.zeros(2), np.zeros(3), np.zeros(2))
    with pytest.raises(ValueError, match="finite"):
        calibrate_route(np.array([np.nan]), np.zeros(1), np.ones(1))
