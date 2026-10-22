"""Ordinal diagnostics must preserve common-control/scale invariance and explicit ties."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "ranking_diagnostics", Path(__file__).parents[1] / "scripts/ranking-diagnostics.py"
)
assert _SPEC is not None and _SPEC.loader is not None
ranking = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ranking)


def test_actual_rank_score_detects_wrong_gene_axis_and_reports_undefined_genes():
    effects = np.array([[0.0, 1, 5], [1, 0, 5], [2, -1, 5]])
    result = ranking.rank_scores(effects, effects, np.array([1, 0, 2]))
    assert result["original_mean_defined_spearman"] == pytest.approx(1)
    assert result["original_defined_genes"] == 2
    assert result["original_fixed_gene_score"] == pytest.approx(2 / 3)
    assert result["scoring_gene_permutation_mean_defined_spearman"] == pytest.approx(-1)
    zero = ranking.rank_scores(np.zeros_like(effects), effects, np.arange(3))
    assert zero["original_defined_genes"] == 0
    assert zero["original_mean_defined_spearman"] is None
    assert zero["original_fixed_gene_score"] == 0


def test_rank_score_cancels_shared_controls_and_ignores_effect_scale():
    effects = np.array([[0.0, 1, 5], [1, 0, 5], [2, -1, 5]])
    before = ranking.rank_scores(effects, effects, np.array([1, 0, 2]))
    after = ranking.rank_scores(
        effects * 0.0001 + [5, -10, 7], effects + [90, 30, -3], np.array([1, 0, 2])
    )
    assert after == before


def test_average_ties_match_hand_calculated_spearman_and_nonfinite_is_rejected():
    prediction = np.array([[0.0, 0], [0, 1], [1, 1]])
    truth = np.array([[0.0, 0], [1, 0], [1, 1]])
    result = ranking.rank_scores(prediction, truth, np.arange(2))
    assert result["original_mean_defined_spearman"] == pytest.approx(0.5)
    with pytest.raises(ValueError, match="finite"):
        ranking.unit_ranks(np.array([[1.0], [np.nan]]))
