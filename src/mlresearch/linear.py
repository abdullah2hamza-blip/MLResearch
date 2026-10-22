"""Classical shared-control design and explicit identification diagnostics.

These functions assume a correct linear response map and known noise variances.
They are building blocks, not causal guarantees or new statistical theorems.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def _matrix(value: FloatArray, name: str) -> FloatArray:
    result = np.asarray(value, dtype=np.float64)
    if result.ndim != 2 or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite two-dimensional array")
    return result


def shared_precision(
    perturbed_mean_variances: FloatArray, control_mean_variance: float
) -> FloatArray:
    """Invert diag(v) + v_control * 11' without treating shared controls as independent."""
    variance = np.asarray(perturbed_mean_variances, dtype=np.float64)
    if variance.ndim != 1 or not np.all(np.isfinite(variance)) or np.any(variance <= 0):
        raise ValueError("Perturbation mean variances must be finite and positive")
    if not np.isfinite(control_mean_variance) or control_mean_variance < 0:
        raise ValueError("Control mean variance must be finite and nonnegative")
    if len(variance) == 1:
        return np.asarray([[1 / (variance[0] + control_mean_variance)]])
    inverse = 1 / variance
    if control_mean_variance == 0:
        return np.diag(inverse)
    # Explicit precision matrices cannot retain arbitrarily small common-mode
    # eigenvalues next to large contrast eigenvalues in float64.
    if np.max(variance) + len(variance) * control_mean_variance > 1e14 * np.min(variance):
        raise ValueError("Covariance conditioning exceeds explicit precision accuracy; use fit_gls")
    denominator = np.sum(inverse) + 1 / control_mean_variance
    result = -np.outer(inverse, inverse) / denominator
    # Compute each diagonal from the other weights, avoiding w_i - nearly w_i.
    for index, weight in enumerate(inverse):
        other = np.sum(np.delete(inverse, index)) + 1 / control_mean_variance
        result[index, index] = weight * other / denominator
    return result


def design_information(
    features: FloatArray,
    counts: FloatArray,
    per_cell_variances: FloatArray,
    control_count: float,
    control_per_cell_variance: float,
) -> FloatArray:
    """Schur-complement information for response slopes with an unknown control baseline."""
    x = _matrix(features, "features")
    n = np.asarray(counts, dtype=np.float64)
    v = np.asarray(per_cell_variances, dtype=np.float64)
    if n.shape != (len(x),) or v.shape != n.shape:
        raise ValueError("Counts and variances must match the intervention axis")
    if not np.all(np.isfinite(n)) or np.any(n < 0):
        raise ValueError("Counts must be finite and nonnegative")
    if not np.all(np.isfinite(v)) or np.any(v <= 0):
        raise ValueError("Per-cell variances must be finite and positive")
    if not np.isfinite(control_count) or control_count < 0:
        raise ValueError("Control count must be finite and nonnegative")
    if not np.isfinite(control_per_cell_variance) or control_per_cell_variance <= 0:
        raise ValueError("Control variance must be finite and positive")
    weights = n / v
    total = float(np.sum(weights) + control_count / control_per_cell_variance)
    if total == 0:
        return np.zeros((x.shape[1], x.shape[1]), dtype=np.float64)
    # Compute a weighted centered scatter, not the subtraction of two nearly
    # equal information matrices. With one observed treatment and no controls,
    # reference-relative differences are exactly zero even for nonbinary x.
    control_weight = control_count / control_per_cell_variance
    active = np.flatnonzero(weights)
    reference = np.zeros(x.shape[1]) if control_weight or not len(active) else x[active[0]]
    differences = x - reference
    center = (differences.T @ weights - control_weight * reference) / total
    centered = differences - center
    control_centered = -reference - center
    information = centered.T @ (weights[:, None] * centered)
    information += control_weight * np.outer(control_centered, control_centered)
    return (information + information.T) / 2


@dataclass(frozen=True)
class QuerySupport:
    identified: NDArray[np.bool_]
    residual_fraction: FloatArray
    ideal_variance: FloatArray
    rank: int


def query_support(
    query_features: FloatArray, information: FloatArray, *, rtol: float = 1e-9
) -> QuerySupport:
    """Give infinite variance to unsupported queries before any ridge regularization."""
    query, matrix = _matrix(query_features, "query_features"), _matrix(information, "information")
    if matrix.shape != (query.shape[1], query.shape[1]):
        raise ValueError("Query feature dimension does not match the information matrix")
    if not 0 < rtol < 1:
        raise ValueError("rtol must lie between zero and one")
    if not np.allclose(matrix, matrix.T, rtol=rtol, atol=1e-12):
        raise ValueError("Information matrix must be symmetric")
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    scale = float(np.max(np.abs(eigenvalues))) if len(eigenvalues) else 0.0
    if np.any(eigenvalues < -max(scale * rtol, 1e-12)):
        raise ValueError("Information matrix must be positive semidefinite")
    observed = eigenvalues > scale * rtol
    basis = eigenvectors[:, observed]
    coordinates = query @ basis
    residual = np.linalg.norm(query - coordinates @ basis.T, axis=1)
    norms = np.linalg.norm(query, axis=1)
    fraction = np.divide(residual, norms, out=np.zeros_like(residual), where=norms > 0)
    identified = fraction <= rtol
    variance = np.sum(coordinates**2 / eigenvalues[observed], axis=1)
    variance[~identified] = np.inf
    return QuerySupport(identified, fraction, variance, int(np.sum(observed)))


def fit_gls(
    features: FloatArray,
    effects: FloatArray,
    perturbed_mean_variances: FloatArray,
    control_mean_variance: float,
    *,
    ridge: float = 1e-6,
) -> FloatArray:
    """Fit a multivariate response map; ridge affects the point fit, never identification."""
    x, y = _matrix(features, "features"), _matrix(effects, "effects")
    if len(x) != len(y) or len(x) != len(perturbed_mean_variances):
        raise ValueError("Feature, effect, and variance rows must match")
    if not np.isfinite(ridge) or ridge < 0:
        raise ValueError("Ridge must be finite and nonnegative")
    variance = np.asarray(perturbed_mean_variances, dtype=np.float64)
    if variance.shape != (len(x),) or np.any(variance <= 0) or not np.all(np.isfinite(variance)):
        raise ValueError("Perturbation mean variances must be finite and positive")
    if not np.isfinite(control_mean_variance) or control_mean_variance < 0:
        raise ValueError("Control mean variance must be finite and nonnegative")
    if len(x) == 0:
        return np.zeros((x.shape[1], y.shape[1]))
    root = 1 / np.sqrt(variance)
    whitened_x, whitened_y = root[:, None] * x, root[:, None] * y
    # Rotate the shared-control direction onto the first axis with a Householder
    # reflection. Scale that axis directly; never subtract nearly equal matrices.
    unit = root / np.linalg.norm(root)
    reflector = unit.copy()
    reflector[0] += 1
    reflector /= np.linalg.norm(reflector)
    whitened_x -= 2 * np.outer(reflector, reflector @ whitened_x)
    whitened_y -= 2 * np.outer(reflector, reflector @ whitened_y)
    scale = 1 / np.sqrt(1 + control_mean_variance * np.sum(root**2))
    whitened_x[0] *= scale
    whitened_y[0] *= scale
    if ridge:
        whitened_x = np.vstack([whitened_x, np.sqrt(ridge) * np.eye(x.shape[1])])
        whitened_y = np.vstack([whitened_y, np.zeros((x.shape[1], y.shape[1]))])
    return np.linalg.lstsq(whitened_x, whitened_y, rcond=1e-12)[0]
