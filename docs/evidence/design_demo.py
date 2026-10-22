"""Exact arithmetic illustrations for docs/technical-notes.md.

These are standard design calculations, not ML or biological performance results.
Run with --write to refresh the adjacent, deterministic JSON artifact.
"""

from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path


def dot(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    return sum(a * b for a, b in zip(left, right, strict=True))


def number(value: Fraction) -> dict[str, str | float]:
    return {"exact": str(value), "decimal": float(value)}


def calculations() -> dict:
    anchor = (1, 0)
    query = (0, 1)
    theta_plus = (0, 1)
    theta_minus = (0, -1)
    assert dot(anchor, theta_plus) == dot(anchor, theta_minus) == 0
    assert dot(query, theta_plus) == 1
    assert dot(query, theta_minus) == -1

    equal_variance = Fraction(1, 50) + Fraction(9, 50)
    best_pair = min(
        (Fraction(1, n1) + Fraction(9, 100 - n1), n1, 100 - n1)
        for n1 in range(1, 100)
    )
    assert best_pair == (Fraction(4, 25), 25, 75)

    perturbation_variance = Fraction(1, 50)
    control_variance = Fraction(4, 20)
    effect_variance = perturbation_variance + control_variance
    true_mean_variance = (2 * effect_variance + 2 * control_variance) / 4
    false_independent_variance = 2 * effect_variance / 4
    assert true_mean_variance == Fraction(21, 100)
    assert false_independent_variance == Fraction(11, 100)

    equal_control_design = Fraction(1, 4 * 40) * 2 + Fraction(4, 40)
    best_control_design = min(
        (
            Fraction(1, 4 * n1) + Fraction(1, 4 * n2) + Fraction(4, 120 - n1 - n2),
            n1,
            n2,
            120 - n1 - n2,
        )
        for n1 in range(1, 119)
        for n2 in range(1, 120 - n1)
    )
    assert best_control_design == (Fraction(3, 40), 20, 20, 80)

    return {
        "scope": "Synthetic exact-arithmetic illustrations; not biological or ML results.",
        "assumptions": [
            "Correct linear response model and exact features for the identification example.",
            "Independent per-cell noise within each pool and an explicitly shared control pool.",
            "Equal per-cell costs and no intervention setup costs for allocation examples.",
        ],
        "identification": {
            "observed_feature": anchor,
            "query_feature": query,
            "observed_values_in_two_worlds": [0, 0],
            "query_values_in_two_worlds": [1, -1],
        },
        "known_baseline_allocation": {
            "total_cells": 100,
            "per_cell_variances": [1, 9],
            "query_feature": [1, 1],
            "equal_allocation": [50, 50],
            "equal_variance": number(equal_variance),
            "optimal_integer_allocation": list(best_pair[1:]),
            "optimal_variance": number(best_pair[0]),
            "relative_variance_reduction": number(1 - best_pair[0] / equal_variance),
        },
        "shared_control_covariance": {
            "perturbation_cells_each": 50,
            "control_cells": 20,
            "per_cell_variances_perturbed_control": [1, 4],
            "off_diagonal_covariance": number(control_variance),
            "true_variance_of_mean_effect": number(true_mean_variance),
            "incorrect_independence_variance": number(false_independent_variance),
        },
        "joint_control_allocation": {
            "total_cells": 120,
            "objective": "Variance of the mean of two control-relative effects.",
            "per_cell_variances": [1, 1, 4],
            "equal_allocation_perturbation1_perturbation2_control": [40, 40, 40],
            "equal_variance": number(equal_control_design),
            "optimal_integer_allocation": list(best_control_design[1:]),
            "optimal_variance": number(best_control_design[0]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Refresh design-demo.json.")
    args = parser.parse_args()
    result = json.dumps(calculations(), indent=2) + "\n"
    if args.write:
        Path(__file__).with_name("design-demo.json").write_text(result, encoding="utf-8")
    print(result, end="")


if __name__ == "__main__":
    main()
