"""Cost-aware acquisition from source features and paid statistics only.

Classical design is prior art. The optional kernel-discrepancy term encodes a
specific bias model; empirical comparison, not its name, determines its value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from mlresearch.acquisition import CONTROL, Action
from mlresearch.episodes import PublicEpisode
from mlresearch.linear import design_information, query_support
from mlresearch.models import Observations, SourceCoordinates

POLICIES = (
    "random_equal",
    "fixed_grid",
    "diversity",
    "d_optimal",
    "worst_query",
    "reliability",
    "disagreement",
    "bias_aware",
)


@dataclass(frozen=True)
class PolicyConfig:
    rank: int = 4
    block_cells: int = 8
    pilot_controls: int = 16
    pilot_interventions: int = 6
    setup_cost: int = 4
    cell_cost: int = 1
    control_cell_cost: int = 1
    ridge: float = 0.1
    ridge_grid: tuple[float, ...] = (0.1, 1.0, 10.0, 100.0, 1000.0)
    fixed_control_fraction: float = 0.25
    discrepancy_weight: float = 0.25
    kernel_length: float = 1.0

    def __post_init__(self) -> None:
        for name in (
            "rank",
            "block_cells",
            "pilot_controls",
            "pilot_interventions",
            "setup_cost",
            "cell_cost",
            "control_cell_cost",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < (0 if name == "setup_cost" else 1)
            ):
                raise ValueError(f"Invalid integer policy setting: {name}")
        if self.block_cells < 2 or self.pilot_controls < 2:
            raise ValueError("At least two cells are required for paid variance estimates")
        if not np.isfinite(self.ridge) or self.ridge < 0 or not 0 < self.fixed_control_fraction < 1:
            raise ValueError("Invalid ridge or fixed control fraction")
        if (
            not self.ridge_grid
            or len(set(self.ridge_grid)) != len(self.ridge_grid)
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not np.isfinite(value)
                or value < 0
                for value in self.ridge_grid
            )
        ):
            raise ValueError("Declare distinct finite nonnegative ridge-grid penalties")
        if not np.isfinite(self.discrepancy_weight) or self.discrepancy_weight < 0:
            raise ValueError("Discrepancy weight must be finite and nonnegative")
        if not np.isfinite(self.kernel_length) or self.kernel_length <= 0:
            raise ValueError("Kernel length must be finite and positive")


def action_price(action: Action, state: dict[str, Any]) -> int:
    control = action.intervention == CONTROL
    setup = state["setup_cost"] if not control and state["counts"][action.intervention] == 0 else 0
    return int(setup + action.cells * state["control_cell_cost" if control else "cell_cost"])


class Policy:
    def __init__(
        self,
        name: str,
        public: PublicEpisode,
        coordinates: SourceCoordinates,
        config: PolicyConfig,
        seed: int,
    ) -> None:
        if name not in POLICIES:
            raise ValueError(f"Unknown policy: {name}")
        self.name, self.public, self.coordinates, self.config = name, public, coordinates, config
        self.rng = np.random.default_rng(seed)
        self.candidates = list(public.candidate_ids)
        self.x = coordinates.features[[public.index(key) for key in self.candidates]]
        self.query = coordinates.features[[public.index(key) for key in public.query_ids]]
        self.fixed_order = self.rng.permutation(self.candidates).tolist()
        distances = (
            np.mean((self.query[:, None, 1:] - self.x[None, :, 1:]) ** 2, axis=2)
            if self.x.shape[1] > 1
            else np.zeros((len(self.query), len(self.x)))
        )
        self.cross_kernel = np.exp(-distances / (2 * config.kernel_length**2))
        distances_cc = (
            np.mean((self.x[:, None, 1:] - self.x[None, :, 1:]) ** 2, axis=2)
            if self.x.shape[1] > 1
            else np.zeros((len(self.x), len(self.x)))
        )
        self.kernel = np.exp(-distances_cc / (2 * config.kernel_length**2))

    def pilot(self) -> list[Action]:
        if self.config.pilot_interventions > len(self.candidates):
            raise ValueError("Pilot exceeds eligible candidate identities")
        return [
            Action(CONTROL, self.config.pilot_controls),
            *[
                Action(identity, self.config.block_cells)
                for identity in self.fixed_order[: self.config.pilot_interventions]
            ],
        ]

    def choose(
        self, state: dict[str, Any], observations: Observations, checkpoint: int
    ) -> Action | None:
        available = [
            Action(key, min(self.config.block_cells, remaining))
            for key, remaining in sorted(state["remaining_cells"].items())
            if remaining >= 2
        ]
        available = [
            action
            for action in available
            if state["spent"] + action_price(action, state) <= checkpoint
        ]
        if not available:
            return None
        if self.name in ("random_equal", "fixed_grid"):
            control_actions = [action for action in available if action.intervention == CONTROL]
            noncontrol = [action for action in available if action.intervention != CONTROL]
            control_cost = state["counts"][CONTROL] * self.config.control_cell_cost
            if control_actions and (
                not noncontrol
                or control_cost < self.config.fixed_control_fraction * max(state["spent"], 1)
            ):
                return control_actions[0]
            minimum = min(state["counts"][action.intervention] for action in noncontrol)
            tied = [
                action for action in noncontrol if state["counts"][action.intervention] == minimum
            ]
            if self.name == "random_equal":
                return tied[int(self.rng.integers(len(tied)))]
            return min(tied, key=lambda action: self.fixed_order.index(action.intervention))
        counts = np.asarray([state["counts"][key] for key in self.candidates], dtype=float)
        variance = np.asarray(
            [
                observations.moments[key].per_cell_variance
                if key in observations.moments
                else self.public.source_per_cell_variance[self.public.index(key)]
                for key in self.candidates
            ]
        )
        control = observations.moments[CONTROL]
        control_count = state["counts"][CONTROL]
        current = design_information(
            self.x, counts, variance, control_count, control.per_cell_variance
        )
        before = query_support(self.query, current)

        # A weak prior is used only for finite design scores, never to declare identification.
        def query_risk(matrix: np.ndarray) -> np.ndarray:
            return np.einsum(
                "ij,jk,ik->i",
                self.query,
                np.linalg.inv(matrix + 0.01 * np.eye(matrix.shape[0])),
                self.query,
            )

        before_risk = query_risk(current)
        scores: list[float] = []
        opened = np.flatnonzero(counts)
        disagreement_weights = (
            self._disagreement(observations) if self.name == "disagreement" else None
        )
        for action in available:
            index = (
                self.candidates.index(action.intervention)
                if action.intervention != CONTROL
                else None
            )
            new_counts = counts.copy()
            new_control = control_count
            if index is None:
                new_control += action.cells
            else:
                new_counts[index] += action.cells
            after_matrix = design_information(
                self.x, new_counts, variance, new_control, control.per_cell_variance
            )
            after = query_support(self.query, after_matrix)
            cost = action_price(action, state)
            # Cover the fixed queries, not every source-coordinate direction.
            # Once queries are supported, a new irrelevant direction earns no bonus.
            support_gain = 0.0
            if self.name in ("worst_query", "disagreement", "bias_aware") and not np.all(
                before.identified
            ):
                support_gain = max(
                    0.0, float(np.sum(before.residual_fraction - after.residual_fraction))
                )
            if self.name == "d_optimal":
                score = (
                    np.linalg.slogdet(after_matrix + 0.01 * np.eye(self.x.shape[1]))[1]
                    - np.linalg.slogdet(current + 0.01 * np.eye(self.x.shape[1]))[1]
                )
            elif self.name == "diversity":
                score = (
                    float(np.linalg.norm(self.x[index]))
                    if index is not None and not len(opened)
                    else 0.0
                )
                if index is not None and len(opened):
                    score = (
                        float(np.min(np.sum((self.x[opened] - self.x[index]) ** 2, axis=1)))
                        if counts[index] == 0
                        else 0.0
                    )
                if index is None:
                    score = float(before_risk.max() - query_risk(after_matrix).max())
            elif self.name == "reliability":
                score = (
                    (
                        control.per_cell_variance / control_count
                        - control.per_cell_variance / new_control
                    )
                    if index is None
                    else variance[index] / max(counts[index], 1)
                    - variance[index] / new_counts[index]
                )
            else:
                improvement = before_risk - query_risk(after_matrix)
                score = float(before_risk.max() - query_risk(after_matrix).max())
                if self.name == "disagreement":
                    # Disagreement between coordinate resolutions, evaluated only
                    # on source-query features and purchased calibration effects.
                    assert disagreement_weights is not None
                    score = float(np.mean((1 + disagreement_weights) * improvement))
                elif self.name == "bias_aware":
                    score += self.config.discrepancy_weight * self._discrepancy_gain(
                        counts,
                        new_counts,
                        variance,
                        control_count,
                        new_control,
                        control.per_cell_variance,
                    )
            scores.append((float(score) + 1e6 * support_gain) / cost)
        return available[int(np.argmax(scores))]

    def _disagreement(self, observations: Observations) -> np.ndarray:
        from mlresearch.linear import fit_gls

        identities, y, variances, control_variance = observations.training(self.public)
        rows = [self.candidates.index(key) for key in identities]
        small = max(1, self.x.shape[1] // 2)
        a = self.query @ fit_gls(
            self.x[rows], y, variances, control_variance, ridge=self.config.ridge
        )
        b = self.query[:, :small] @ fit_gls(
            self.x[rows, :small],
            y,
            variances,
            control_variance,
            ridge=10 * max(self.config.ridge, 0.01),
        )
        disagreement = np.mean((a - b) ** 2, axis=1)
        return disagreement / max(float(disagreement.mean()), 1e-8)

    def _discrepancy_gain(
        self,
        counts: np.ndarray,
        new_counts: np.ndarray,
        variance: np.ndarray,
        controls: int,
        new_controls: int,
        control_variance: float,
    ) -> float:
        def residual_risk(depth: np.ndarray, control_depth: int) -> float:
            selected = np.flatnonzero(depth)
            if not len(selected):
                return 1.0
            noise = np.diag(variance[selected] / depth[selected])
            noise += control_variance / control_depth * np.ones_like(noise)
            covariance = (
                self.kernel[np.ix_(selected, selected)] + noise + 1e-6 * np.eye(len(selected))
            )
            cross = self.cross_kernel[:, selected]
            risk = 1 - np.einsum("ij,ji->i", cross, np.linalg.solve(covariance, cross.T))
            return float(np.mean(np.maximum(risk, 0)))

        return residual_risk(counts, controls) - residual_risk(new_counts, new_controls)
