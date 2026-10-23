"""Single-source algorithm reconstruction; separate from author-code reproduction."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.special import ndtr


@dataclass(frozen=True)
class TransferConfig:
    rank: int = 16
    anchors: int = 64
    hidden: int = 128
    batch_size: int = 16
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    epochs_per_round: int = 3
    max_rounds: int = 100
    patience: int = 15
    validation_fraction: float = 0.2
    split_seed: int = 20260718
    model_seed: int = 20261022
    ridge_grid: tuple[float, ...] = (0.001, 0.01, 0.1, 1.0, 10.0)

    def __post_init__(self) -> None:
        for name in (
            "rank",
            "anchors",
            "hidden",
            "batch_size",
            "epochs_per_round",
            "max_rounds",
            "patience",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"Invalid model integer: {name}")
        for name in ("split_seed", "model_seed"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"Invalid seed: {name}")
        for name in ("validation_fraction", "learning_rate", "weight_decay"):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not np.isfinite(value)
            ):
                raise ValueError(f"Model rate must be finite: {name}")
        if not 0 < self.validation_fraction < 1 or self.learning_rate <= 0 or self.weight_decay < 0:
            raise ValueError("Invalid model rates")
        if (
            not self.ridge_grid
            or len(set(self.ridge_grid)) != len(self.ridge_grid)
            or any(
                isinstance(x, bool)
                or not isinstance(x, (int, float))
                or not np.isfinite(x)
                or x <= 0
                for x in self.ridge_grid
            )
        ):
            raise ValueError("Positive finite ridge penalties required")
        object.__setattr__(self, "ridge_grid", tuple(self.ridge_grid))


def response_basis(responses: np.ndarray, rank: int) -> tuple[np.ndarray, np.ndarray]:
    center = responses.mean(axis=0)
    centered = responses - center
    eigenvalues, vectors = np.linalg.eigh(centered @ centered.T)
    keep = np.argsort(eigenvalues)[::-1][: min(rank, len(responses) - 1, responses.shape[1])]
    keep = keep[eigenvalues[keep] > max(1e-12, eigenvalues.max() * 1e-12)]
    if not len(keep):
        return center, np.zeros((0, responses.shape[1]))
    basis = (vectors[:, keep].T @ centered) / np.sqrt(eigenvalues[keep, None])
    for row in basis:
        if row[np.argmax(np.abs(row))] < 0:
            row *= -1
    return center, basis


def descriptors(
    control: np.ndarray, genes: tuple[str, ...], identities: list[str], anchors: int
) -> tuple[np.ndarray, list[str], list[str]]:
    if control.ndim != 2 or len(control) < 2 or control.shape[1] != len(genes):
        raise ValueError("Paid control cells and measured gene axis required")
    mean = control.mean(axis=0)
    centered = control - mean
    variance = np.mean(centered**2, axis=0)
    anchor_columns = np.argsort(-variance, kind="stable")[: min(anchors, len(genes))]
    gene_index = {gene: i for i, gene in enumerate(genes)}
    columns = [gene_index.get(identity) for identity in identities]
    missing = [identity for identity, col in zip(identities, columns, strict=True) if col is None]
    output = np.zeros((len(identities), anchors + 3))
    for i, col in enumerate(columns):
        if col is None:
            continue
        covariance = centered[:, col] @ centered[:, anchor_columns] / len(control)
        denominator = np.sqrt(variance[col] * variance[anchor_columns])
        output[i, : len(anchor_columns)] = np.divide(
            covariance, denominator, out=np.zeros(len(anchor_columns)), where=denominator > 1e-12
        )
        output[i, -3:] = [mean[col], np.sqrt(variance[col]), np.mean(control[:, col] > 0)]
    return output, missing, [genes[col] for col in anchor_columns]


class CoefficientMLP:
    def __init__(self, inputs: int, outputs: int, hidden: int, seed: int):
        rng = np.random.default_rng(seed)
        self.parameters = {
            "gamma": np.ones(inputs),
            "beta": np.zeros(inputs),
            "w1": rng.uniform(-1 / np.sqrt(inputs), 1 / np.sqrt(inputs), (inputs, hidden)),
            "b1": rng.uniform(-1 / np.sqrt(inputs), 1 / np.sqrt(inputs), hidden),
            "w2": rng.uniform(-1 / np.sqrt(hidden), 1 / np.sqrt(hidden), (hidden, outputs)),
            "b2": rng.uniform(-1 / np.sqrt(hidden), 1 / np.sqrt(hidden), outputs),
        }
        self.first = {key: np.zeros_like(value) for key, value in self.parameters.items()}
        self.second = {key: np.zeros_like(value) for key, value in self.parameters.items()}
        self.steps = 0

    def forward(self, inputs: np.ndarray) -> tuple[np.ndarray, tuple[np.ndarray, ...]]:
        p = self.parameters
        normalized = (inputs - inputs.mean(axis=1, keepdims=True)) / np.sqrt(
            inputs.var(axis=1, keepdims=True) + 1e-5
        )
        layer = normalized * p["gamma"] + p["beta"]
        preactivation = layer @ p["w1"] + p["b1"]
        activation = preactivation * ndtr(preactivation)
        result = activation @ p["w2"] + p["b2"]
        return result, (normalized, layer, preactivation, activation)

    def loss_gradient(
        self, inputs: np.ndarray, targets: np.ndarray
    ) -> tuple[float, dict[str, np.ndarray]]:
        predictions, (normalized, layer, preactivation, activation) = self.forward(inputs)
        residual = predictions - targets
        output_gradient = 2 * residual / residual.size
        hidden_gradient = output_gradient @ self.parameters["w2"].T
        hidden_gradient *= ndtr(preactivation) + preactivation * np.exp(
            -(preactivation**2) / 2
        ) / np.sqrt(2 * np.pi)
        layer_gradient = hidden_gradient @ self.parameters["w1"].T
        return float(np.mean(residual**2)), {
            "w2": activation.T @ output_gradient,
            "b2": output_gradient.sum(axis=0),
            "w1": layer.T @ hidden_gradient,
            "b1": hidden_gradient.sum(axis=0),
            "gamma": np.sum(layer_gradient * normalized, axis=0),
            "beta": layer_gradient.sum(axis=0),
        }

    def step(self, inputs: np.ndarray, targets: np.ndarray, config: TransferConfig) -> None:
        _, gradients = self.loss_gradient(inputs, targets)
        self.steps += 1
        for name, parameter in self.parameters.items():
            gradient = gradients[name]
            first, second = self.first[name], self.second[name]
            first *= 0.9
            first += 0.1 * gradient
            second *= 0.999
            second += 0.001 * gradient**2
            parameter *= 1 - config.learning_rate * config.weight_decay
            parameter -= (
                config.learning_rate
                * (first / (1 - 0.9**self.steps))
                / (np.sqrt(second / (1 - 0.999**self.steps)) + 1e-8)
            )


def fit_base(
    train_x: np.ndarray,
    train_z: np.ndarray,
    validation_x: np.ndarray,
    validation_z: np.ndarray,
    validation_residual: np.ndarray,
    genes: int,
    config: TransferConfig,
) -> tuple[CoefficientMLP, dict[str, Any]]:
    model = CoefficientMLP(train_x.shape[1], train_z.shape[1], config.hidden, config.model_seed)
    rng = np.random.default_rng(config.model_seed)
    best, best_parameters, selected_round, waiting = np.inf, None, None, 0
    trace = []
    for round_number in range(1, config.max_rounds + 1):
        for _ in range(config.epochs_per_round):
            order = rng.permutation(len(train_x))
            for start in range(0, len(order), config.batch_size):
                rows = order[start : start + config.batch_size]
                model.step(train_x[rows], train_z[rows], config)
        val_predictions, _ = model.forward(validation_x)
        full_effect_mse = float(
            np.mean(np.sum((val_predictions - validation_z) ** 2, axis=1) + validation_residual)
            / genes
        )
        trace.append(full_effect_mse)
        if not np.isfinite(full_effect_mse):
            raise ValueError("Nonfinite validation loss")
        if full_effect_mse < best:
            best, selected_round, waiting = full_effect_mse, round_number, 0
            best_parameters = {key: value.copy() for key, value in model.parameters.items()}
        else:
            waiting += 1
        if waiting >= config.patience:
            break
    assert best_parameters is not None
    model.parameters = best_parameters
    return model, {
        "selected_round": selected_round,
        "executed_rounds": len(trace),
        "executed_epochs": len(trace) * config.epochs_per_round,
        "validation_full_effect_mse": trace,
    }


def calibrate_route(
    target: np.ndarray, base: np.ndarray, transport: np.ndarray
) -> tuple[float, float]:
    """Fit interpolation and its in-sample improvement; this is not a reliability test.

    The same paid calibration labels select the interpolation and report its gain.
    Zero interpolation or equal errors must have exactly zero reported gain.
    """
    if target.shape != base.shape or target.shape != transport.shape or target.size == 0:
        raise ValueError("Route calibration requires matching nonempty arrays")
    if not all(np.isfinite(value).all() for value in (target, base, transport)):
        raise ValueError("Route calibration requires finite arrays")
    displacement = transport - base
    denominator = float(np.sum(displacement**2))
    alpha = (
        float(np.clip(np.sum((target - base) * displacement) / denominator, 0, 1))
        if denominator
        else 0.0
    )
    base_mse = float(np.mean((target - base) ** 2))
    route_mse = float(np.mean((target - (base + alpha * displacement)) ** 2))
    improvement = max(0.0, base_mse - route_mse)
    return alpha, improvement / max(base_mse, 1e-12) if alpha > 0 else 0.0


def reconstruct(
    control_cells: np.ndarray,
    genes: tuple[str, ...],
    calibration_ids: list[str],
    recipient_effects: np.ndarray,
    calibration_source_effects: np.ndarray,
    query_ids: list[str],
    query_source_effects: np.ndarray,
    config: TransferConfig | None = None,
) -> dict[str, Any]:
    """Fit using paid calibrations/controls; query source tokens enter inference only."""
    config = TransferConfig() if config is None else config
    n, g = len(calibration_ids), len(genes)
    if g == 0 or len(set(genes)) != g or not query_ids:
        raise ValueError("Distinct nonempty gene and query axes required")
    if n < 3 or len(set(calibration_ids)) != n or len(set(query_ids)) != len(query_ids):
        raise ValueError("At least three distinct paid anchors required")
    if set(calibration_ids) & set(query_ids):
        raise ValueError("Query/calibration identity overlap")
    if (
        recipient_effects.shape != (n, g)
        or calibration_source_effects.shape != (n, g)
        or query_source_effects.shape != (len(query_ids), g)
    ):
        raise ValueError("Response axes disagree")
    if any(
        not np.isfinite(x).all()
        for x in (
            recipient_effects,
            calibration_source_effects,
            query_source_effects,
            control_cells,
        )
    ):
        raise ValueError("Nonfinite model inputs")
    order = np.argsort(calibration_ids)
    identities = [calibration_ids[i] for i in order]
    recipient = recipient_effects[order]
    source = calibration_source_effects[order]
    split = np.random.default_rng(config.split_seed).permutation(n)
    validation_count = min(n - 2, max(1, int(n * config.validation_fraction)))
    validation = np.sort(split[:validation_count])
    training = np.sort(split[validation_count:])
    # Neither validation source rows nor any query source rows enter coordinates.
    center, basis = response_basis(np.vstack([source[training], recipient[training]]), config.rank)
    source_z = (source - center) @ basis.T
    recipient_z = (recipient - center) @ basis.T
    descriptor, missing, anchors = descriptors(
        control_cells, genes, [*identities, *query_ids], config.anchors
    )
    if not len(basis):
        constant = np.broadcast_to(center, (len(query_ids), g)).copy()
        return {
            "perturbmap_reconstruction": constant,
            "recipient_local_lowrank": constant.copy(),
            "diagnostics": {
                "training_ids": [identities[i] for i in training],
                "paid_validation_ids": [identities[i] for i in validation],
                "basis_rank": 0,
                "basis_sha256": hashlib.sha256(basis.tobytes()).hexdigest(),
                "coordinate_mean_sha256": hashlib.sha256(center.tobytes()).hexdigest(),
                "missing_control_descriptors": missing,
                "control_anchor_genes": anchors,
                "paid_control_cells": len(control_cells),
                "selected_ridge": None,
                "alpha": 0.0,
                "rho": 0.0,
                "route_accepted": False,
                "base_fitting": {"executed_rounds": 0, "selected_round": None},
                "fallback": "Constant decoder because train responses have zero centered rank",
            },
        }
    validation_residual = np.maximum(
        0,
        np.sum((recipient[validation] - center) ** 2, axis=1)
        - np.sum(recipient_z[validation] ** 2, axis=1),
    )
    model, fitting = fit_base(
        descriptor[training],
        recipient_z[training],
        descriptor[validation],
        recipient_z[validation],
        validation_residual,
        g,
        config,
    )
    base_z, _ = model.forward(descriptor)
    base_validation = center + base_z[validation] @ basis
    base_query = center + base_z[n:] @ basis
    x_mean, y_mean = source_z[training].mean(axis=0), recipient_z[training].mean(axis=0)
    x, y = source_z[training] - x_mean, recipient_z[training] - y_mean
    # The article does not fully specify eta; use average per-coordinate Gram energy.
    eta = max(1e-12, float(np.sum(x * x) / x.shape[1]))
    rhs, gram = x.T @ y, x.T @ x
    query_z = (query_source_effects - center) @ basis.T
    selected, validation_predictions, query_predictions, scores = None, None, None, []
    best = np.inf
    for ridge in config.ridge_grid:
        mapping = np.linalg.solve(gram + ridge * eta * np.eye(len(gram)), rhs)
        val = center + ((source_z[validation] - x_mean) @ mapping + y_mean) @ basis
        score = float(np.mean((val - recipient[validation]) ** 2))
        scores.append(score)
        if score < best:
            best, selected, validation_predictions = score, ridge, val
            query_predictions = center + ((query_z - x_mean) @ mapping + y_mean) @ basis
    assert validation_predictions is not None and query_predictions is not None
    alpha, rho = calibrate_route(recipient[validation], base_validation, validation_predictions)
    proposal_validation = base_validation + alpha * (validation_predictions - base_validation)
    base_mse = float(np.mean((recipient[validation] - base_validation) ** 2))
    route_mse = float(np.mean((recipient[validation] - proposal_validation) ** 2))
    accepted = alpha > 0 and rho > 0
    prediction = base_query + alpha * (query_predictions - base_query) if accepted else base_query
    return {
        "perturbmap_reconstruction": prediction,
        "recipient_local_lowrank": base_query,
        "diagnostics": {
            "training_ids": [identities[i] for i in training],
            "paid_validation_ids": [identities[i] for i in validation],
            "missing_control_descriptors": missing,
            "control_anchor_genes": anchors,
            "paid_control_cells": len(control_cells),
            "basis_rank": int(np.linalg.matrix_rank(basis)),
            "basis_sha256": hashlib.sha256(basis.tobytes()).hexdigest(),
            "coordinate_mean_sha256": hashlib.sha256(center.tobytes()).hexdigest(),
            "ridge_grid": list(config.ridge_grid),
            "ridge_validation_mse": scores,
            "selected_ridge": selected,
            "ridge_energy_scale": eta,
            "alpha": alpha,
            "rho": rho,
            "route_accepted": accepted,
            "calibration_gain_scope": (
                "In-sample paid calibration improvement after early stopping, ridge selection "
                "and interpolation on the same validation set; not independent reliability"
            ),
            "base_validation_mse": base_mse,
            "proposal_validation_mse": route_mse,
            "base_fitting": fitting,
            "reconstruction_choices": [
                "Exact train-only PCA instead of covariance sketch",
                "NumPy AdamW; optimizer unspecified in article",
                "Single source",
                "Per-coordinate Gram energy ridge scaling",
                "Missing measured target-gene descriptors use zero vector and are reported",
            ],
        },
    }
