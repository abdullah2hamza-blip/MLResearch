import hashlib
import io

import h5py
import numpy as np
import pytest
from scipy import sparse

from mlresearch.data import (
    Dataset,
    audit_h5ad,
    fetch_dataset,
    read_column,
    read_columns,
    read_rows,
    verify_file,
)


@pytest.fixture
def h5ad(tmp_path):
    path = tmp_path / "fixture.h5ad"
    matrix = sparse.csr_matrix(np.array([[1, 0, 2], [0, 0, 3], [2, 4, 0]], dtype=float))
    with h5py.File(path, "w") as handle:
        obs, var = handle.create_group("obs"), handle.create_group("var")
        obs.attrs["_index"], var.attrs["_index"] = "_index", "_index"
        obs.create_dataset("_index", data=np.asarray(["c1", "c2", "c3"], dtype="S"))
        var.create_dataset("_index", data=np.asarray(["g1", "g2", "g3"], dtype="S"))
        group = obs.create_group("perturbation")
        group.attrs["encoding-type"] = "categorical"
        group.create_dataset("categories", data=np.asarray(["control", "A"], dtype="S"))
        group.create_dataset("codes", data=np.array([0, 1, -1]))
        expression = handle.create_group("X")
        expression.attrs["encoding-type"] = "csr_matrix"
        expression.attrs["shape"] = matrix.shape
        expression.create_dataset("data", data=matrix.data)
        expression.create_dataset("indices", data=matrix.indices)
        expression.create_dataset("indptr", data=matrix.indptr)
    return path


def test_sparse_h5ad_metadata_missing_categories_and_row_blocks(h5ad):
    audit = audit_h5ad(h5ad, sample_rows=2)
    assert audit["cells"] == 3
    assert audit["genes"] == 3
    assert audit["observation_columns"]["perturbation"]["missing_or_empty"] == 1
    with h5py.File(h5ad, "r") as handle:
        assert read_column(handle["obs"], "perturbation").tolist() == ["control", "A", ""]
        np.testing.assert_array_equal(
            read_rows(handle["X"], 1, 3).toarray(), np.array([[0, 0, 3], [2, 4, 0]])
        )
        with pytest.raises(ValueError, match="outside"):
            read_rows(handle["X"], 0, 4)


def test_audit_rejects_inconsistent_indices(h5ad):
    with h5py.File(h5ad, "a") as handle:
        handle["X"].attrs["shape"] = (3, 4)
    with pytest.raises(ValueError, match="dimensions"):
        audit_h5ad(h5ad)


def test_audit_rejects_invalid_category_codes(h5ad):
    with h5py.File(h5ad, "a") as handle:
        handle["obs/perturbation/codes"][0] = 4
    with pytest.raises(ValueError, match="categorical"):
        audit_h5ad(h5ad)


def test_csc_column_streaming_and_honest_audit_sampling(h5ad):
    expected = np.array([[1, 0, 2], [0, 0, 3], [2, 4, 0]], dtype=float)
    matrix = sparse.csc_matrix(expected)
    with h5py.File(h5ad, "a") as handle:
        del handle["X"]
        expression = handle.create_group("X")
        expression.attrs["encoding-type"] = "csc_matrix"
        expression.attrs["shape"] = matrix.shape
        for name in ("data", "indices", "indptr"):
            expression.create_dataset(name, data=getattr(matrix, name))
        np.testing.assert_array_equal(read_columns(expression, 1, 3).toarray(), expected[:, 1:3])
    audit = audit_h5ad(h5ad)
    assert audit["expression_sample"]["sampled_rows"] is None
    assert "CSC" in audit["expression_sample"]["sampling_axis"]


def dataset_for(payload):
    return Dataset(
        "fixture",
        "fixture.bin",
        len(payload),
        hashlib.md5(payload).hexdigest(),
        "https://zenodo.org/api/records/1/files/fixture.bin/content",
        "test",
        "test",
    )


class Response(io.BytesIO):
    def __init__(self, data, status=200, headers=None):
        super().__init__(data)
        self.status = status
        self.headers = headers or {}


def test_download_checks_hashes_and_resets_when_range_ignored(tmp_path, monkeypatch):
    payload = b"the complete public file"
    spec = dataset_for(payload)
    (tmp_path / "fixture.bin.part").write_bytes(payload[:6])
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response(payload))
    target = fetch_dataset(spec, tmp_path)
    assert target.read_bytes() == payload
    assert not (tmp_path / "fixture.bin.part").exists()
    assert (tmp_path / "fixture.bin.provenance.json").exists()
    assert verify_file(target, spec)["sha256"] == hashlib.sha256(payload).hexdigest()


def test_download_resumes_and_rejects_corrupt_or_oversized_response(tmp_path, monkeypatch):
    payload = b"the complete public file"
    spec = dataset_for(payload)
    partial = tmp_path / "fixture.bin.part"
    partial.write_bytes(payload[:6])

    def resume(request, **kwargs):
        assert request.headers["Range"] == "bytes=6-"
        return Response(
            payload[6:], 206, {"Content-Range": f"bytes 6-{len(payload) - 1}/{len(payload)}"}
        )

    monkeypatch.setattr("urllib.request.urlopen", resume)
    assert fetch_dataset(spec, tmp_path).read_bytes() == payload
    (tmp_path / "fixture.bin").unlink()
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *args, **kwargs: Response(b"x" * len(payload))
    )
    with pytest.raises(ValueError, match="MD5"):
        fetch_dataset(spec, tmp_path, restart=True)
    assert not (tmp_path / "fixture.bin").exists()


def test_dataset_paths_cannot_escape_download_directory(tmp_path):
    spec = Dataset("bad", "../escape", 4, "", "https://zenodo.org/api/records/1", "x", "x")
    with pytest.raises(ValueError, match="filename"):
        fetch_dataset(spec, tmp_path)
