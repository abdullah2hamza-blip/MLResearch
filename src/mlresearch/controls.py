"""Declared negative controls that transform public source information only."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from mlresearch.episodes import PublicEpisode
from mlresearch.provenance import object_hash

SOURCE_CONTROLS = ("none", "identity_permutation", "query_gene_permutation")


def transform_source(
    public: PublicEpisode, control: str, seed: int
) -> tuple[PublicEpisode, dict[str, Any]]:
    if control not in SOURCE_CONTROLS:
        raise ValueError("Unknown public-source permutation control")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("Source-control seed must be a nonnegative integer")
    record: dict[str, Any] = {
        "control": control,
        "seed": seed,
        "recipient_outcomes_accessed": False,
    }
    if control == "none":
        return public, record
    rng = np.random.default_rng(seed)
    if control == "identity_permutation":
        size = len(public.interventions)
        if size < 2:
            raise ValueError("Identity permutation requires at least two interventions")
        order = rng.permutation(size)
        for _ in range(100):
            if np.all(order != np.arange(size)):
                break
            order = rng.permutation(size)
        if np.any(order == np.arange(size)):
            order = np.roll(np.arange(size), 1)
        effects, half = (
            public.source_effects[order].copy(),
            public.source_half_difference[order].copy(),
        )
        variance = public.source_per_cell_variance[order].copy()
        mean_variance = public.source_effect_mean_variance[order].copy()
        record["identity_index_permutation"] = order.tolist()
    else:
        order = rng.permutation(len(public.genes))
        query = [public.index(key) for key in public.query_ids]
        effects, half = public.source_effects.copy(), public.source_half_difference.copy()
        effects[query] = effects[np.ix_(query, order)]
        half[query] = half[np.ix_(query, order)]
        variance, mean_variance = (
            public.source_per_cell_variance.copy(),
            public.source_effect_mean_variance.copy(),
        )
        record["query_gene_index_permutation_sha256"] = object_hash(order.tolist())
        record["definition"] = (
            "Only query source coordinates are permuted; calibration sources "
            "and recipient gene order stay fixed."
        )
    for array in (effects, half, variance, mean_variance):
        array.setflags(write=False)
    return replace(
        public,
        source_effects=effects,
        source_half_difference=half,
        source_per_cell_variance=variance,
        source_effect_mean_variance=mean_variance,
    ), record
