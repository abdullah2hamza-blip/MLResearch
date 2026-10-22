import numpy as np
import pytest

from mlresearch.episodes import PublicEpisode
from mlresearch.models import source_half_coordinates


def test_joint_half_perturbations_match_direct_source_halves_with_shared_controls():
    rng = np.random.default_rng(17)
    treatment = rng.normal(size=(6, 8, 5))
    controls = rng.normal(size=(12, 5))
    effects = treatment.mean(axis=1) - controls.mean(axis=0)
    first = treatment[:, :4].mean(axis=1) - controls[:6].mean(axis=0)
    second = treatment[:, 4:].mean(axis=1) - controls[6:].mean(axis=0)
    public = PublicEpisode(
        tuple("ABCDEF"),
        ("F",),
        tuple("ABCDE"),
        tuple(f"g{i}" for i in range(5)),
        effects,
        np.ones(6),
        np.ones(6),
        first - second,
    )
    halves = source_half_coordinates(public, 2)
    np.testing.assert_allclose(halves[0].public.source_effects, second, atol=1e-15)
    np.testing.assert_allclose(halves[1].public.source_effects, first, atol=1e-15)
    np.testing.assert_array_equal(public.source_effects, effects)
    assert all(not half.public.source_effects.flags.writeable for half in halves)


def test_half_difference_squared_recovers_source_mean_variance_only_in_repeated_iid_experiments():
    """Monte Carlo checks scale and common-control covariance, not coverage from one split."""
    rng = np.random.default_rng(18)
    treatment = rng.normal(scale=1.2, size=(30000, 3, 8))
    controls = rng.normal(scale=0.7, size=(30000, 12))
    difference = (
        treatment[:, :, :4].mean(axis=2)
        - treatment[:, :, 4:].mean(axis=2)
        - (controls[:, :6].mean(axis=1) - controls[:, 6:].mean(axis=1))[:, None]
    ) / 2
    expected = 1.2**2 / 8 + 0.7**2 / 12
    assert np.mean(difference**2) == pytest.approx(expected, rel=0.03)
    assert np.cov(difference, rowvar=False)[0, 1] == pytest.approx(0.7**2 / 12, rel=0.06)
