import h5py
import numpy as np
import pytest
from scipy import sparse

from mlresearch.prepare import PrepareConfig, prepare_h5ad, select_metadata
from mlresearch.provenance import read_json


def make_h5ad(path, matrix, encoding):
    with h5py.File(path, "w") as handle:
        obs, var = handle.create_group("obs"), handle.create_group("var")
        obs.attrs["_index"], var.attrs["_index"] = "_index", "_index"
        obs.create_dataset("_index", data=np.asarray(["c1", "c2", "c3", "c4"], dtype="S"))
        var.create_dataset("_index", data=np.asarray(["g1", "g2", "g3"], dtype="S"))
        obs.create_dataset("pert", data=np.asarray(["control", "A", "control", "A"], dtype="S"))
        obs.create_dataset(
            "context", data=np.asarray(["source", "source", "target", "target"], dtype="S")
        )
        if encoding == "dense":
            handle.create_dataset("X", data=matrix)
        else:
            expression = handle.create_group("X")
            expression.attrs["encoding-type"] = encoding
            expression.attrs["shape"] = matrix.shape
            sparse_matrix = (
                sparse.csr_matrix(matrix) if encoding == "csr_matrix" else sparse.csc_matrix(matrix)
            )
            for name in ("data", "indices", "indptr"):
                expression.create_dataset(name, data=getattr(sparse_matrix, name))


@pytest.mark.parametrize("encoding", ["dense", "csr_matrix", "csc_matrix"])
def test_streaming_preparation_preserves_full_gene_axis_and_correct_normalization(
    tmp_path, encoding
):
    matrix = np.array([[2, 0, 3], [0, 4, 1], [1, 2, 3], [4, 1, 0]], dtype=float)
    path = tmp_path / "input.h5ad"
    make_h5ad(path, matrix, encoding)
    output = tmp_path / "prepared"
    config = PrepareConfig(
        str(path),
        str(output),
        "pert",
        ["control"],
        "counts",
        context_column="context",
        column_block_size=1,
        row_block_size=1,
    )
    result = prepare_h5ad(config)
    assert result["state"] == "complete"
    assert result["shape"] == [4, 3]
    values = np.load(output / "values.npy", mmap_mode="r")
    np.testing.assert_allclose(
        values, np.log1p(matrix / matrix.sum(axis=1)[:, None] * 10000), rtol=1e-6
    )
    metadata = read_json(output / "metadata.json")
    assert metadata["genes"] == ["g1", "g2", "g3"]
    assert metadata["original_cell_ids"] == ["c1", "c2", "c3", "c4"]
    with pytest.raises(ValueError, match="already exists"):
        prepare_h5ad(config)


def test_fractional_expression_cannot_silently_be_normalized_as_counts(tmp_path):
    path = tmp_path / "input.h5ad"
    make_h5ad(path, np.full((4, 3), 0.25), "csc_matrix")
    output = tmp_path / "prepared"
    config = PrepareConfig(
        str(path), str(output), "pert", ["control"], "counts", context_column="context"
    )
    with pytest.raises(ValueError, match="fractional"):
        prepare_h5ad(config)
    assert read_json(output / "manifest.json")["state"] == "preparing"


def test_control_cap_is_shared_across_original_control_labels(tmp_path):
    path = tmp_path / "controls.h5ad"
    make_h5ad(path, np.ones((4, 3)), "dense")
    with h5py.File(path, "r+") as handle:
        handle["obs/pert"][:] = np.asarray(["ctrl1", "ctrl2", "ctrl1", "ctrl2"], dtype="S")
        handle["obs/context"][:] = np.asarray(["target"] * 4, dtype="S")
        config = PrepareConfig(
            str(path),
            str(tmp_path / "out"),
            "pert",
            ["ctrl1", "ctrl2"],
            "counts",
            context_column="context",
            max_control_cells_per_context=2,
        )
        metadata, selected = select_metadata(handle, config)
    assert len(selected) == 2
    assert sum(item["retained_cells"] for item in metadata["condition_inventory"]) == 2
    assert {item["intervention"] for item in metadata["condition_inventory"]} == {"ctrl1", "ctrl2"}
