import numpy as np
import pytest

from mlresearch.acquisition import CONTROL, Action, Purchase
from mlresearch.episodes import PublicEpisode
from mlresearch.models import Observations, SourceCoordinates
from mlresearch.policies import Policy, PolicyConfig


@pytest.mark.parametrize("seed", range(6))
def test_mean_query_action_matches_dense_correlated_observation_covariance(seed):
    """Independent dense covariance inversion checks action, setup and control costs."""
    rng = np.random.default_rng(seed)
    identities = ("A", "B", "C", "D", "Q1", "Q2")
    features = np.column_stack([np.ones(6), [-1, 0, 1, 2, -0.3, 1.4]])
    public = PublicEpisode(
        identities,
        identities[-2:],
        identities[:4],
        ("g1", "g2"),
        rng.normal(size=(6, 2)),
        rng.uniform(0.3, 2, size=6),
        np.ones(6),
        np.zeros((6, 2)),
    )
    observations = Observations()
    counts = {CONTROL: 8, "A": 4, "B": 8, "C": 12, "D": 0}
    for identity, n in counts.items():
        if n:
            observations.update(
                Purchase(
                    identity,
                    tuple(f"{identity}-{i}" for i in range(n)),
                    rng.normal(scale=rng.uniform(0.3, 2), size=(n, 2)),
                    n,
                    n,
                )
            )
    state = {
        "setup_cost": 3,
        "cell_cost": 2,
        "control_cell_cost": 1,
        "spent": 65,
        "budget": 100,
        "counts": counts,
        "remaining_cells": dict.fromkeys(counts, 8),
    }
    x, query = features[:4], features[-2:]
    variance = np.array(
        [
            observations.moments[key].per_cell_variance
            if key in observations.moments
            else public.source_per_cell_variance[public.index(key)]
            for key in identities[:4]
        ]
    )
    control_variance = observations.moments[CONTROL].per_cell_variance

    def risk(n, c):
        opened = n > 0
        covariance = np.diag(variance[opened] / n[opened])
        covariance += control_variance / c
        information = x[opened].T @ np.linalg.solve(covariance, x[opened])
        return np.mean(
            np.sum(query * np.linalg.solve(information + 0.01 * np.eye(2), query.T).T, axis=1)
        )

    n = np.array([counts[key] for key in identities[:4]], dtype=float)
    before = risk(n, counts[CONTROL])
    choices, gains = [], []
    for key in sorted(counts):
        after = n.copy()
        c = counts[CONTROL]
        price = 4 if key == CONTROL else 8 + (3 if counts[key] == 0 else 0)
        if key == CONTROL:
            c += 4
        else:
            after[identities.index(key)] += 4
        choices.append(Action(key, 4))
        gains.append((before - risk(after, c)) / price)
    settings = PolicyConfig(
        rank=1, block_cells=4, pilot_controls=8, pilot_interventions=3, setup_cost=3, cell_cost=2
    )
    actual = Policy(
        "mean_query", public, SourceCoordinates(features, 1, 1, 0), settings, seed
    ).choose(state, observations, 100)
    assert actual == choices[int(np.argmax(gains))]
