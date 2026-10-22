import numpy as np
import pytest

from mlresearch.design import DiscrepancyState, information_step, nuisance_center
from mlresearch.linear import design_information


@pytest.mark.parametrize("controls", [0, 5, 200])
@pytest.mark.parametrize("observed", [False, True])
def test_scatter_update_matches_full_nuisance_refit(controls, observed):
    rng = np.random.default_rng(981)
    x, v = rng.normal(size=(8, 4)), rng.uniform(0.2, 3, 8)
    n = rng.integers(0, 12, 8).astype(float) if observed else np.zeros(8)
    before = design_information(x, n, v, controls, 1.3)
    total, center = nuisance_center(x, n, v, controls, 1.3)
    for identity in [None, *range(8)]:
        counts, nc = n.copy(), controls
        feature = np.zeros(4) if identity is None else x[identity]
        variance = 1.3 if identity is None else v[identity]
        after, _, _ = information_step(before, total, center, feature, 3 / variance)
        if identity is None:
            nc += 3
        else:
            counts[identity] += 3
        expected = design_information(x, counts, v, nc, 1.3)
        np.testing.assert_allclose(after, expected, atol=1e-12)


def test_repeated_nonbinary_feature_has_exact_zero_information_without_controls():
    x, n, v = np.full((3, 1), 0.1), np.array([7.0, 0, 0]), np.ones(3)
    before = design_information(x, n, v, 0, 1)
    total, center = nuisance_center(x, n, v, 0, 1)
    after, _, _ = information_step(before, total, center, x[1], 5)
    np.testing.assert_array_equal(after, np.zeros((1, 1)))


@pytest.mark.parametrize("shared", [True, False])
@pytest.mark.parametrize("counts", [[0, 0, 0, 0], [5, 0, 8, 0], [4, 9, 3, 7]])
def test_gp_updates_match_independent_dense_posterior_covariance(shared, counts):
    rng = np.random.default_rng(98)
    points = rng.normal(size=(7, 3))
    covariance = np.exp(-np.mean((points[:, None] - points[None, :]) ** 2, axis=2) / 2)
    kernel, cross = covariance[:4, :4], covariance[4:, :4]
    n, variance = np.asarray(counts, dtype=float), np.array([0.3, 1, 2, 0.7])
    controls, control_variance = 6, 1.8

    def dense_risk(depth, nc):
        selected = np.flatnonzero(depth)
        noise = np.diag(variance[selected] / depth[selected])
        noise += control_variance / nc * (np.ones_like(noise) if shared else np.eye(len(noise)))
        observed = kernel[np.ix_(selected, selected)] + noise + 1e-6 * np.eye(len(noise))
        query = cross[:, selected]
        posterior = covariance[4:, 4:] - query @ np.linalg.inv(observed) @ query.T
        return np.trace(posterior) / 3

    cache = DiscrepancyState(kernel, cross, n, variance, controls, control_variance, shared)
    before = dense_risk(n, controls)
    for identity in [None, *range(4)]:
        new_n, new_control = n.copy(), controls
        if identity is None:
            new_control += 3
        else:
            new_n[identity] += 3
        expected = before - dense_risk(new_n, new_control)
        assert cache.gain(identity, 3) == pytest.approx(expected, abs=1e-11)
