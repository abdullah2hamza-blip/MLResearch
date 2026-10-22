"""Fast, algebraically exact updates for the classical design surrogates."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def nuisance_center(
    features: np.ndarray,
    counts: np.ndarray,
    variances: np.ndarray,
    controls: float,
    control_variance: float,
) -> tuple[float, np.ndarray]:
    """Weighted center including the zero-feature control; inputs are validated upstream."""
    weights, control_weight = counts / variances, controls / control_variance
    total = float(weights.sum() + control_weight)
    active = np.flatnonzero(weights)
    reference = (
        np.zeros(features.shape[1]) if control_weight or not len(active) else features[active[0]]
    )
    if total == 0:
        return 0.0, reference
    center = reference + ((features - reference).T @ weights - control_weight * reference) / total
    return total, center


def information_step(
    current: np.ndarray, total: float, center: np.ndarray, feature: np.ndarray, added_weight: float
) -> tuple[np.ndarray, float, np.ndarray]:
    """Update centered scatter when one weighted group gains observations."""
    if not np.isfinite(added_weight) or added_weight < 0 or not np.isfinite(total) or total < 0:
        raise ValueError("Information weights must be finite and nonnegative")
    factor = added_weight / (1 + added_weight / total) if total else 0.0
    difference = feature - center
    return current + factor * np.outer(difference, difference), factor, difference


def independent_control_information(
    features: np.ndarray,
    counts: np.ndarray,
    variances: np.ndarray,
    controls: float,
    control_variance: float,
) -> np.ndarray:
    """Deliberately incorrect shared-control independence assumption, for ablation only."""
    if controls <= 0:
        raise ValueError("The independent-control ablation needs paid controls")
    precision = counts / (variances + counts * control_variance / controls)
    return features.T @ (precision[:, None] * features)


@dataclass
class DiscrepancyState:
    kernel: np.ndarray
    cross: np.ndarray
    counts: np.ndarray
    variances: np.ndarray
    controls: float
    control_variance: float
    shared: bool = True

    def __post_init__(self) -> None:
        if self.controls <= 0:
            raise ValueError("GP discrepancy design requires purchased controls")
        self.selected = np.flatnonzero(self.counts)
        self.c = self.control_variance / self.controls
        covariance = self.kernel[np.ix_(self.selected, self.selected)].copy()
        covariance += np.diag(self.variances[self.selected] / self.counts[self.selected] + 1e-6)
        covariance += self.c * (
            np.ones_like(covariance) if self.shared else np.eye(len(covariance))
        )
        self.covariance = covariance
        self.precision = np.linalg.solve(covariance, np.eye(len(covariance)))
        self.projected = self.cross[:, self.selected] @ self.precision

    def gain(self, index: int | None, cells: int) -> float:
        """Mean query posterior-variance decrease; includes shared-control covariance."""
        if isinstance(cells, bool) or not isinstance(cells, int) or cells < 1:
            raise ValueError("Discrepancy action must contain positive integer cells")
        if index is None:
            delta = self.control_variance / (self.controls + cells) - self.c
            if not self.shared:
                after = self.covariance + delta * np.eye(len(self.selected))
                new = np.linalg.solve(after, self.cross[:, self.selected].T)
                before = np.sum(self.projected * self.cross[:, self.selected], axis=1)
                return max(
                    0.0,
                    float(np.mean(np.sum(self.cross[:, self.selected] * new.T, axis=1) - before)),
                )
            ones = np.ones(len(self.selected))
            denominator = 1 + delta * float(ones @ self.precision @ ones)
            projection = self.projected @ ones
            numerator = -delta * float(np.mean(projection**2))
        elif self.counts[index] > 0:
            position = int(np.flatnonzero(self.selected == index)[0])
            delta = (
                self.variances[index] / (self.counts[index] + cells)
                - self.variances[index] / self.counts[index]
            )
            denominator = 1 + delta * self.precision[position, position]
            numerator = -delta * float(np.mean(self.projected[:, position] ** 2))
        else:
            covariance = self.kernel[self.selected, index] + (self.c if self.shared else 0)
            diagonal = self.kernel[index, index] + self.variances[index] / cells + self.c + 1e-6
            denominator = diagonal - float(covariance @ self.precision @ covariance)
            residual = self.cross[:, index] - self.projected @ covariance
            numerator = float(np.mean(residual**2))
        if denominator <= 0 or not np.isfinite(denominator):
            raise ValueError("Discrepancy covariance is numerically ill-conditioned")
        return max(0.0, float(numerator / denominator))
