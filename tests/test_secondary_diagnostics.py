"""Independent geometric examples and Gaussian calibration for scorer-only supplements."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "secondary_diagnostics", Path(__file__).parents[1] / "scripts/secondary-frozen-diagnostics.py"
)
assert _SPEC is not None and _SPEC.loader is not None
diagnostics = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(diagnostics)


def test_gene_coordinate_permutation_and_zero_direction_are_not_spurious_success():
    truth = np.array([[1.0, 0.0]])
    correct = diagnostics.coordinate_metrics(truth, truth, np.array([1, 0]))
    assert correct["mse"] == 0
    assert correct["scoring_gene_permuted_mse"] == 1
    assert correct["direction_cosine"] == 1
    zero = diagnostics.coordinate_metrics(np.zeros_like(truth), truth, np.array([1, 0]))
    assert zero["direction_cosine"] is None
    assert zero["direction_cosine_defined_queries"] == 0
    assert zero["prediction_nonzero_fraction"] == 0
    assert zero["sign_agreement_including_explicit_zero_ties"] == 0.5


def test_90_and_95_gaussian_fields_match_independent_sampling_and_assessment_noise():
    rng = np.random.default_rng(811)
    for scope, scale, noise in (("controlled_truth", 1, 0), ("external_assessment", 2, 3)):
        truth = rng.normal(0, scale, size=(1, 100_000))
        result = diagnostics.interval_diagnostics(
            np.zeros_like(truth), truth, np.array([1.0]), np.full_like(truth, noise), scope
        )
        assert result["coverage_or_compatibility_90"] == pytest.approx(0.90, abs=0.003)
        assert result["coverage_or_compatibility_95"] == pytest.approx(0.95, abs=0.003)
        assert result["mean_width_95"] == pytest.approx(3.92 * scale)
        assert result["mean_width_90"] < result["mean_width_95"]


def test_unsupported_directions_have_no_reported_finite_width_coverage():
    result = diagnostics.interval_diagnostics(
        np.zeros((2, 3)), np.ones((2, 3)), np.full(2, np.inf), np.zeros((2, 3)), "controlled_truth"
    )
    for level in (90, 95):
        assert result[f"finite_queries_{level}"] == 0
        assert result[f"coverage_or_compatibility_{level}"] is None
        assert result[f"mean_width_{level}"] is None


def test_distance_only_geometry_has_known_values_and_rotation_invariance():
    queries = np.array([[-2.0, 0], [0, 1], [3, 0]])
    purchased = np.array([[-1.0, 0], [1, 0]])
    rotation = np.array([[0.0, -1], [1, 0]])
    np.testing.assert_array_equal(diagnostics.nearest_distance(queries, purchased), [0.5, 1, 2])
    np.testing.assert_array_equal(
        diagnostics.nearest_distance(queries @ rotation, purchased @ rotation), [0.5, 1, 2]
    )
    assert np.isinf(diagnostics.nearest_distance(queries, np.empty((0, 2)))).all()
