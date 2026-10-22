"""Source-only coordinates, paid sufficient statistics, and transfer predictors."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from mlresearch.acquisition import CONTROL, Purchase
from mlresearch.episodes import PublicEpisode
from mlresearch.linear import design_information, fit_gls, query_support

BACKBONES = (
    "zero",
    "mean",
    "source_copy",
    "affine",
    "ridge",
    "ridge_cv",
    "local_residual_adaptation",
)


def ridge_validation_scores(
    features: np.ndarray,
    effects: np.ndarray,
    mean_variances: np.ndarray,
    control_variance: float,
    grid: tuple[float, ...],
) -> np.ndarray:
    """Paid-label leave-one-intervention-out scores with shared-control correction.

    For fixed features/variances and linear held-out predictor a' y_train,
    E[(y_i-a'y_train)^2 - (v_i+c) + 2c sum(a)] equals its true-effect risk.
    Plug-in/adaptive scores are not guaranteed unbiased. No scorer labels enter.
    """
    x, y = np.asarray(features, dtype=float), np.asarray(effects, dtype=float)
    variance = np.asarray(mean_variances, dtype=float)
    if x.ndim != 2 or y.ndim != 2 or len(x) != len(y) or len(x) < 3:
        raise ValueError("Ridge validation needs at least three aligned paid interventions")
    if variance.shape != (len(x),) or not np.all(np.isfinite(variance)) or np.any(variance <= 0):
        raise ValueError("Invalid paid mean variances")
    if not grid or any(not np.isfinite(value) or value < 0 for value in grid):
        raise ValueError("Declare a finite nonnegative ridge grid")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)) or y.shape[1] == 0:
        raise ValueError("Paid validation arrays must be finite with a nonempty gene axis")
    if not np.isfinite(control_variance) or control_variance < 0:
        raise ValueError("Invalid control mean variance")
    response_gram = y @ y.T / y.shape[1]
    scores = []
    for penalty in grid:
        errors = []
        for held_out in range(len(x)):
            training = np.delete(np.arange(len(x)), held_out)
            operator = fit_gls(
                x[training],
                np.eye(len(training)),
                variance[training],
                control_variance,
                ridge=penalty,
            )
            weights = x[held_out] @ operator
            residual_weights = np.zeros(len(x))
            residual_weights[held_out], residual_weights[training] = 1, -weights
            residual_mse = float(residual_weights @ response_gram @ residual_weights)
            errors.append(
                residual_mse
                - variance[held_out]
                - control_variance
                + 2 * control_variance * weights.sum()
            )
        scores.append(float(np.mean(errors)))
    return np.asarray(scores)


@dataclass(frozen=True)
class SourceCoordinates:
    features: np.ndarray
    explained_fraction: float
    rank: int
    source_half_noise: float


def source_coordinates(public: PublicEpisode, rank: int) -> SourceCoordinates:
    """PCA of all permitted source responses (including query sources), plus an intercept.

    The eigendecomposition is intervention by intervention; no gene covariance
    matrix or recipient expression is constructed. Coordinates have unit RMS.
    """
    if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
        raise ValueError("Source rank must be a positive integer")
    centered = public.source_effects - public.source_effects.mean(axis=0)
    gram = centered @ centered.T / centered.shape[1]
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    order = np.argsort(eigenvalues)[::-1]
    positive = order[eigenvalues[order] > max(float(eigenvalues.max()) * 1e-10, 1e-12)]
    selected = positive[:rank]
    coordinates = eigenvectors[:, selected] * np.sqrt(len(centered))
    # Fix arbitrary eigensolver signs for reproducible serialized coordinates.
    for column in range(coordinates.shape[1]):
        if coordinates[np.argmax(np.abs(coordinates[:, column])), column] < 0:
            coordinates[:, column] *= -1
    features = np.column_stack([np.ones(len(centered)), coordinates])
    features.setflags(write=False)
    explained = (
        float(eigenvalues[selected].sum() / eigenvalues[positive].sum()) if len(positive) else 0.0
    )
    return SourceCoordinates(
        features, explained, len(selected), float(np.mean(public.source_half_difference**2))
    )


@dataclass
class Moment:
    count: int
    mean: np.ndarray
    scalar_m2: float

    @property
    def per_cell_variance(self) -> float:
        if self.count < 2:
            raise ValueError("At least two purchased cells are needed to estimate variance")
        return max(self.scalar_m2 / (self.count - 1), 1e-8)


class Observations:
    """Sufficient statistics updated only through paid, audited Purchase objects."""

    def __init__(self) -> None:
        self.moments: dict[str, Moment] = {}
        self.cell_ids: set[str] = set()

    def update(self, purchase: Purchase) -> None:
        if self.cell_ids.intersection(purchase.cell_ids):
            raise ValueError("Repeated cells cannot update paid sufficient statistics")
        values = purchase.values
        count, mean = len(values), values.mean(axis=0)
        m2 = float(np.sum((values - mean) ** 2) / values.shape[1])
        if purchase.intervention in self.moments:
            old = self.moments[purchase.intervention]
            total = old.count + count
            delta = mean - old.mean
            m2 += old.scalar_m2 + float(np.mean(delta**2)) * old.count * count / total
            mean = old.mean + delta * count / total
            count = total
        self.moments[purchase.intervention] = Moment(count, mean, m2)
        self.cell_ids.update(purchase.cell_ids)

    def training(self, public: PublicEpisode) -> tuple[list[str], np.ndarray, np.ndarray, float]:
        if CONTROL not in self.moments:
            raise ValueError("Recipient effect prediction requires purchased controls")
        control = self.moments[CONTROL]
        identities = sorted(key for key in self.moments if key != CONTROL)
        if set(identities) & set(public.query_ids):
            raise ValueError("Query labels cannot enter predictor training")
        effects = np.asarray([self.moments[key].mean - control.mean for key in identities])
        variances = np.asarray(
            [self.moments[key].per_cell_variance / self.moments[key].count for key in identities]
        )
        return identities, effects, variances, control.per_cell_variance / control.count


def predict(
    public: PublicEpisode,
    coordinates: SourceCoordinates,
    observations: Observations,
    identities: tuple[str, ...],
    *,
    ridge: float,
    ridge_grid: tuple[float, ...] = (0.1, 1.0, 10.0, 100.0, 1000.0),
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray | int | float]]:
    training_ids, effects, variances, control_variance = observations.training(public)
    if not training_ids:
        raise ValueError("At least one paid calibration intervention is required")
    rows = [public.index(key) for key in training_ids]
    query_rows = [public.index(key) for key in identities]
    x, query = coordinates.features[rows], coordinates.features[query_rows]
    coefficients = fit_gls(x, effects, variances, control_variance, ridge=ridge)
    fitted = query @ coefficients
    validation_scores = ridge_validation_scores(x, effects, variances, control_variance, ridge_grid)
    selected_ridge = ridge_grid[int(np.argmin(validation_scores))]
    cv_fitted = query @ fit_gls(x, effects, variances, control_variance, ridge=selected_ridge)
    mean = effects.mean(axis=0)
    # Global affine adaptation: y = intercept + scale * source, using ordinary
    # least squares and all genes pooled. The slope/intercept are scalars, making
    # this deliberately strong but low-capacity and affordable on a CPU.
    source_training = public.source_effects[rows]
    centered_source = source_training - source_training.mean()
    centered_target = effects - effects.mean()
    scale = float(
        np.sum(centered_source * centered_target) / max(np.sum(centered_source**2), 1e-12)
    )
    intercept = float(effects.mean() - scale * source_training.mean())
    affine = intercept + scale * public.source_effects[query_rows]
    # Reliability-gated local residual transfer: a documented adaptation of
    # PerturbMap's information interface, not an original-method reproduction.
    distances = (
        np.mean((query[:, None, 1:] - x[None, :, 1:]) ** 2, axis=2)
        if x.shape[1] > 1
        else np.zeros((len(query), len(x)))
    )
    weights = np.exp(-distances / 2) / (variances[None, :] + control_variance + 0.1)
    weights /= np.maximum(weights.sum(axis=1, keepdims=True), 1e-12)
    residuals = effects - source_training
    reliability = len(rows) / (len(rows) + 4)
    local = public.source_effects[query_rows] + reliability * (weights @ residuals)
    counts = np.asarray(
        [
            observations.moments[key].count if key in observations.moments else 0
            for key in public.candidate_ids
        ],
        dtype=float,
    )
    per_cell = np.asarray(
        [
            observations.moments[key].per_cell_variance
            if key in observations.moments
            else public.source_per_cell_variance[public.index(key)]
            for key in public.candidate_ids
        ]
    )
    control = observations.moments[CONTROL]
    information = design_information(
        coordinates.features[[public.index(key) for key in public.candidate_ids]],
        counts,
        per_cell,
        control.count,
        control.per_cell_variance,
    )
    support = query_support(query, information)
    # These are conditional ideal-model variances; they exclude transfer bias,
    # source-coordinate error and adaptive-selection effects.
    diagnostics: dict[str, np.ndarray | int | float] = {
        "identified": support.identified,
        "span_residual_fraction": support.residual_fraction,
        "ideal_variance": support.ideal_variance,
        "information_rank": support.rank,
        "source_half_noise": coordinates.source_half_noise,
        "ridge_cv_selected": selected_ridge,
        "ridge_cv_scores": validation_scores,
        "paid_training_residual_mse": float(np.mean((effects - x @ coefficients) ** 2)),
    }
    return {
        "zero": np.zeros_like(fitted),
        "mean": np.broadcast_to(mean, fitted.shape).copy(),
        "source_copy": public.source_effects[query_rows].copy(),
        "affine": affine,
        "ridge": fitted,
        "ridge_cv": cv_fitted,
        "local_residual_adaptation": local,
    }, diagnostics
