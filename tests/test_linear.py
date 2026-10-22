import numpy as np
import pytest

from mlresearch.linear import design_information, fit_gls, query_support, shared_precision


def test_shared_covariance_inverse_matches_dense_inverse():
    perturbation = np.array([0.2, 0.7, 1.4])
    covariance = np.diag(perturbation) + 0.3 * np.ones((3, 3))
    np.testing.assert_allclose(shared_precision(perturbation, 0.3), np.linalg.inv(covariance))


def test_extreme_shared_variance_does_not_cancel_single_response():
    np.testing.assert_allclose(shared_precision(np.array([1e-8]), 1e10), [[1e-10]])
    result = fit_gls(np.array([[1.0]]), np.array([[2.0]]), np.array([1e-8]), 1e10, ridge=0)
    np.testing.assert_allclose(result, [[2.0]])
    with pytest.raises(ValueError, match="conditioning"):
        shared_precision(np.array([1e-8, 1e-8]), 1e10)


def test_factored_gls_matches_independent_dense_solve():
    rng = np.random.default_rng(34)
    x, y = rng.normal(size=(11, 3)), rng.normal(size=(11, 5))
    v, c = rng.uniform(0.1, 2, 11), 3.0
    covariance = np.diag(v) + c * np.ones((11, 11))
    information = x.T @ np.linalg.solve(covariance, x) + 0.4 * np.eye(3)
    expected = np.linalg.solve(information, x.T @ np.linalg.solve(covariance, y))
    np.testing.assert_allclose(fit_gls(x, y, v, c, ridge=0.4), expected, atol=1e-12)


def test_information_matches_augmented_nuisance_model_and_gls():
    x = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, -2.0]])
    n = np.array([20.0, 30.0, 40.0])
    v = np.array([1.0, 2.0, 3.0])
    augmented = np.column_stack([x, np.ones(3)])
    full = augmented.T @ np.diag(n / v) @ augmented
    full[-1, -1] += 50 / 4
    expected = full[:-1, :-1] - np.outer(full[:-1, -1], full[-1, :-1]) / full[-1, -1]
    information = design_information(x, n, v, 50, 4)
    np.testing.assert_allclose(information, expected)
    np.testing.assert_allclose(information, x.T @ shared_precision(v / n, 4 / 50) @ x)


def test_unobserved_direction_is_not_identified_by_ridge():
    information = design_information(
        np.array([[1.0, 0.0]]), np.array([100.0]), np.array([1.0]), 100, 1
    )
    query = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]])
    support = query_support(query, information)
    assert support.identified.tolist() == [True, False, True]
    assert np.isinf(support.ideal_variance[1])
    assert support.ideal_variance[2] == 0
    assert support.rank == 1


def test_unknown_baseline_cannot_be_recovered_from_one_treatment_without_controls():
    information = design_information(np.array([[1.0]]), np.array([100.0]), np.array([1.0]), 0, 1)
    assert not query_support(np.array([[1.0]]), information).identified[0]


@pytest.mark.parametrize("feature", [0.1, 1 / 3, 1e-5, -0.7])
def test_roundoff_does_not_invent_information_without_control_or_treatment_contrasts(feature):
    x = np.array([[feature], [feature]])
    information = design_information(x, np.array([5.0, 7.0]), np.array([9.0, 13.0]), 0, 1)
    np.testing.assert_array_equal(information, np.zeros((1, 1)))
    support = query_support(np.array([[feature]]), information)
    assert support.rank == 0
    assert not support.identified[0]
    assert np.isinf(support.ideal_variance[0])


def test_orthogonal_feature_rotation_preserves_query_variance():
    rng = np.random.default_rng(381)
    x, query = rng.normal(size=(9, 3)), rng.normal(size=(4, 3))
    rotation, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    original = design_information(x, np.full(9, 30.0), np.ones(9), 50, 1)
    rotated = design_information(x @ rotation, np.full(9, 30.0), np.ones(9), 50, 1)
    np.testing.assert_allclose(
        query_support(query, original).ideal_variance,
        query_support(query @ rotation, rotated).ideal_variance,
    )


def test_shared_control_covariance_against_independent_monte_carlo():
    rng = np.random.default_rng(18)
    control = rng.normal(scale=np.sqrt(4 / 20), size=100_000)
    treatment = rng.normal(scale=np.sqrt(1 / 50), size=(100_000, 2))
    effects = treatment - control[:, None]
    empirical = np.cov(effects, rowvar=False)
    np.testing.assert_allclose(empirical, np.array([[0.22, 0.20], [0.20, 0.22]]), atol=0.003)
    assert np.var(np.mean(effects, axis=1)) == pytest.approx(0.21, abs=0.003)


def test_exact_linear_response_fit_and_invalid_variance():
    x = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    coefficients = np.array([[2.0, -1.0], [-3.0, 2.0]])
    fit = fit_gls(x, x @ coefficients, np.ones(3), 0.5, ridge=0)
    np.testing.assert_allclose(fit, coefficients, atol=1e-12)
    with pytest.raises(ValueError, match="positive"):
        shared_precision(np.array([0.0]), 1)
