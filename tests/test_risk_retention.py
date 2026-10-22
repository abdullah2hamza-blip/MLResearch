import numpy as np

from mlresearch.report import risk_retention_rows


def test_equal_variance_ties_cannot_use_assessment_errors_for_selection():
    values = [(1.0, 100.0, False), (1.0, 80.0, False), (1.0, 2.0, False), (1.0, 1.0, False)]
    rows = risk_retention_rows("policy", 100, "ridge_cv", values)
    halfway = next(
        row
        for row in rows
        if row["criterion"] == "linear_support" and row["requested_retention"] == 0.5
    )
    assert halfway["mse"] == 90
    changed = values[:2] + [(1.0, 0.1, False), (1.0, 0.2, False)]
    again = risk_retention_rows("policy", 100, "ridge_cv", changed)
    assert (
        next(
            row
            for row in again
            if row["criterion"] == "linear_support" and row["requested_retention"] == 0.5
        )["mse"]
        == 90
    )


def test_unsupported_queries_stay_in_retention_denominator():
    rows = risk_retention_rows(
        "policy", 100, "ridge_cv", [(1.0, 4.0, False), (np.inf, 10.0, False)]
    )
    full = next(
        row
        for row in rows
        if row["criterion"] == "linear_support" and row["requested_retention"] == 1
    )
    assert full["actual_retention"] == 0.5
    assert full["mse"] == 4
    unavailable = risk_retention_rows("policy", 100, "ridge", [(np.inf, 10.0, None)])
    assert all(row["mse"] is None and row["actual_retention"] == 0 for row in unavailable)
    assert all(row["criterion"] == "linear_support" for row in unavailable)
