import numpy as np

from mlresearch.controls import transform_source
from mlresearch.episodes import PublicEpisode


def public():
    values = np.arange(24, dtype=float).reshape(4, 6)
    return PublicEpisode(
        ("a", "b", "c", "query"),
        ("query",),
        ("a", "b", "c"),
        tuple(f"g{i}" for i in range(6)),
        values,
        np.arange(1, 5, dtype=float),
        np.arange(1, 5, dtype=float),
        values.copy(),
    )


def test_identity_control_is_a_reproducible_derangement_of_source_tokens():
    source = public()
    transformed, record = transform_source(source, "identity_permutation", 32)
    order = record["identity_index_permutation"]
    assert all(index != value for index, value in enumerate(order))
    np.testing.assert_array_equal(transformed.source_effects, source.source_effects[order])
    np.testing.assert_array_equal(
        transformed.source_per_cell_variance, source.source_per_cell_variance[order]
    )
    assert transformed.query_ids == source.query_ids
    assert record["recipient_outcomes_accessed"] is False
    np.testing.assert_array_equal(
        transformed.source_effects,
        transform_source(source, "identity_permutation", 32)[0].source_effects,
    )


def test_query_coordinate_control_preserves_calibration_sources_and_gene_axis():
    source = public()
    transformed, record = transform_source(source, "query_gene_permutation", 11)
    np.testing.assert_array_equal(transformed.source_effects[:3], source.source_effects[:3])
    assert sorted(transformed.source_effects[3]) == sorted(source.source_effects[3])
    assert not np.array_equal(transformed.source_effects[3], source.source_effects[3])
    assert transformed.genes == source.genes
    assert not transformed.source_effects.flags.writeable
    assert record["recipient_outcomes_accessed"] is False
