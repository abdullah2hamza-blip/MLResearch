import numpy as np

from mlresearch.models import ridge_validation_scores


def test_null_candidate_uses_only_paid_risk_and_is_explicitly_indexed():
    x = np.column_stack([np.ones(4), np.arange(4)])
    effects = np.zeros((4, 12))
    scores = ridge_validation_scores(x, effects, np.ones(4), 0.5, (0.1, 1000), include_null=True)
    assert scores[-1] == -1.5
    assert np.argmin(scores) == 2


def test_shared_control_correction_matches_true_risk_in_independent_monte_carlo():
    rng = np.random.default_rng(90)
    x = np.column_stack([np.ones(6), np.linspace(-1, 1, 6)])
    mean = x @ np.array([0.4, -0.7]) + np.array([0, 0, 0.2, 0, -0.1, 0])
    variance, control = np.linspace(0.2, 0.6, 6), 1.5
    noise = rng.normal(size=(6, 50000)) * np.sqrt(variance[:, None])
    noise -= rng.normal(scale=np.sqrt(control), size=(1, 50000))
    observed = mean[:, None] + noise
    grid = (0.1, 10.0)
    corrected = ridge_validation_scores(x, observed, variance, control, grid)
    expected, naive = [], []
    for penalty in grid:
        risks, uncorrected = [], []
        for held_out in range(6):
            training = np.delete(np.arange(6), held_out)
            covariance = np.diag(variance[training]) + control * np.ones((5, 5))
            weighted_x = np.linalg.solve(covariance, x[training])
            operator = np.linalg.solve(
                x[training].T @ weighted_x + penalty * np.eye(2), weighted_x.T
            )
            weights = x[held_out] @ operator
            bias = weights @ mean[training] - mean[held_out]
            risks.append(
                bias**2 + np.sum(weights**2 * variance[training]) + control * weights.sum() ** 2
            )
            residual = observed[held_out] - weights @ observed[training]
            uncorrected.append(np.mean(residual**2) - variance[held_out] - control)
        expected.append(np.mean(risks))
        naive.append(np.mean(uncorrected))
    np.testing.assert_allclose(corrected, expected, atol=0.025)
    assert expected[0] - naive[0] > 1


def test_gram_score_matches_direct_full_gene_residuals():
    from mlresearch.linear import fit_gls

    rng = np.random.default_rng(154)
    x, y = rng.normal(size=(7, 3)), rng.normal(size=(7, 19))
    variance, control = np.linspace(0.1, 0.6, 7), 0.5
    expected = []
    for penalty in (0.1, 1.0, 100):
        errors = []
        for held_out in range(7):
            training = np.delete(np.arange(7), held_out)
            operator = fit_gls(x[training], np.eye(6), variance[training], control, ridge=penalty)
            weights = x[held_out] @ operator
            errors.append(
                np.mean((y[held_out] - weights @ y[training]) ** 2)
                - variance[held_out]
                - control
                + 2 * control * weights.sum()
            )
        expected.append(np.mean(errors))
    np.testing.assert_allclose(
        ridge_validation_scores(x, y, variance, control, (0.1, 1.0, 100)), expected
    )
