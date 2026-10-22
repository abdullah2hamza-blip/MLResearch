"""Pinned downloads and bounded-memory inspection of H5AD files.

Metadata inspection does not certify assay compatibility. Matrix normalization
is never inferred automatically from a sample of expression values.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from mlresearch.provenance import read_json, utc_now, write_json


@dataclass(frozen=True)
class Dataset:
    key: str
    filename: str
    size: int
    md5: str
    url: str
    record: str
    license: str


def datasets() -> dict[str, Dataset]:
    registry = read_json(Path(__file__).with_name("datasets.json"))
    return {entry["key"]: Dataset(**entry) for entry in registry["datasets"]}


def verify_file(path: Path, expected: Dataset) -> dict[str, Any]:
    if path.stat().st_size != expected.size:
        raise ValueError(f"Wrong byte size for {path.name}; expected {expected.size}")
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            md5.update(block)
            sha256.update(block)
    if md5.hexdigest() != expected.md5:
        raise ValueError(f"Published MD5 mismatch for {path.name}; file is not accepted")
    return {
        "size_bytes": expected.size,
        "published_md5": expected.md5,
        "verified_md5": md5.hexdigest(),
        "sha256": sha256.hexdigest(),
    }


def fetch_dataset(expected: Dataset, directory: Path, *, restart: bool = False) -> Path:
    """Resume a partial HTTPS download and accept it only after size/hash checks."""
    if Path(expected.filename).name != expected.filename or expected.size <= 0:
        raise ValueError("Invalid dataset filename or size")
    if not expected.url.startswith("https://zenodo.org/api/records/"):
        raise ValueError("Downloads must use the pinned Zenodo API URLs")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / expected.filename
    partial = target.with_suffix(target.suffix + ".part")
    if target.exists():
        hashes = verify_file(target, expected)
    else:
        offset = partial.stat().st_size if partial.exists() and not restart else 0
        if offset > expected.size:
            raise ValueError("Partial file exceeds expected size; use --restart")
        if shutil.disk_usage(directory).free < expected.size - offset + 64 * 1024 * 1024:
            raise OSError("Insufficient free disk space for the dataset")
        if offset != expected.size:
            headers = {"User-Agent": "MLResearch/0.1 public-data-research"}
            if offset:
                headers["Range"] = f"bytes={offset}-"
            request = urllib.request.Request(expected.url, headers=headers)
            with urllib.request.urlopen(request, timeout=60) as response:
                status = getattr(response, "status", 200)
                if status == 206:
                    content_range = response.headers.get("Content-Range", "")
                    if not content_range.startswith(f"bytes {offset}-"):
                        raise ValueError("Server returned an unexpected resume range")
                elif status == 200:
                    offset = 0  # Server ignored Range; replace rather than corrupt the file.
                else:
                    raise OSError(f"Unexpected download status {status}")
                with partial.open("ab" if offset else "wb") as stream:
                    while block := response.read(4 * 1024 * 1024):
                        if stream.tell() + len(block) > expected.size:
                            raise ValueError("Download exceeded pinned dataset size")
                        stream.write(block)
                    stream.flush()
                    os.fsync(stream.fileno())
        hashes = verify_file(partial, expected)
        os.replace(partial, target)
    write_json(
        target.with_suffix(target.suffix + ".provenance.json"),
        {
            "schema_version": 1,
            "dataset": expected.key,
            "url": expected.url,
            "record": expected.record,
            "license": expected.license,
            "verified_at": utc_now(),
            **hashes,
        },
    )
    return target


def _text(value: Any) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def read_column(group: h5py.Group, name: str) -> np.ndarray:
    """Read one H5AD dataframe column, including categorical and nullable arrays."""
    item = group[name]
    if isinstance(item, h5py.Dataset):
        values = item[:]
        if values.dtype.kind in "OSU":
            return np.asarray([_text(value) for value in values], dtype=object)
        return np.asarray(values)
    encoding = _text(item.attrs.get("encoding-type", ""))
    if encoding == "categorical" or {"codes", "categories"}.issubset(item.keys()):
        codes = np.asarray(item["codes"][:], dtype=int)
        categories = np.asarray([_text(value) for value in item["categories"][:]], dtype=object)
        if np.any(codes < -1) or np.any(codes >= len(categories)):
            raise ValueError(f"Invalid categorical codes in {name}")
        result = np.full(len(codes), "", dtype=object)
        valid = codes >= 0
        result[valid] = categories[codes[valid]]
        return result
    if {"values", "mask"}.issubset(item.keys()):
        result = np.asarray(item["values"][:], dtype=object)
        result[np.asarray(item["mask"][:], dtype=bool)] = ""
        return result
    raise ValueError(f"Unsupported H5AD column encoding {encoding!r} for {name}")


def dataframe_index(group: h5py.Group) -> np.ndarray:
    key = _text(group.attrs.get("_index", "_index"))
    if key not in group:
        raise ValueError(f"No dataframe index {key!r} in {group.name}")
    return np.asarray([_text(value) for value in group[key][:]], dtype=object)


def matrix_shape(matrix: Any) -> tuple[int, int]:
    if isinstance(matrix, h5py.Dataset):
        shape = matrix.shape
    else:
        shape = matrix.attrs.get("shape")
    if shape is None or len(shape) != 2:
        raise ValueError("Expected a two-dimensional H5AD expression matrix")
    return int(shape[0]), int(shape[1])


def read_rows(matrix: Any, start: int, stop: int) -> Any:
    """Read a contiguous row block without materializing the full expression matrix."""
    from scipy import sparse

    rows, columns = matrix_shape(matrix)
    if not 0 <= start <= stop <= rows:
        raise ValueError("Row interval is outside the expression matrix")
    if isinstance(matrix, h5py.Dataset):
        return np.asarray(matrix[start:stop, :], dtype=np.float64)
    encoding = _text(matrix.attrs.get("encoding-type", ""))
    if encoding != "csr_matrix":
        raise ValueError(f"Row streaming requires dense or CSR encoding, got {encoding!r}")
    pointers = np.asarray(matrix["indptr"][start : stop + 1], dtype=np.int64)
    left, right = int(pointers[0]), int(pointers[-1])
    return sparse.csr_matrix(
        (
            np.asarray(matrix["data"][left:right], dtype=np.float64),
            np.asarray(matrix["indices"][left:right], dtype=np.int64),
            pointers - left,
        ),
        shape=(stop - start, columns),
    )


def read_columns(matrix: Any, start: int, stop: int) -> Any:
    """Read column blocks from CSC data without loading its full nonzero arrays."""
    from scipy import sparse

    rows, columns = matrix_shape(matrix)
    if not 0 <= start <= stop <= columns:
        raise ValueError("Column interval is outside the expression matrix")
    if isinstance(matrix, h5py.Dataset):
        return np.asarray(matrix[:, start:stop], dtype=np.float64)
    encoding = _text(matrix.attrs.get("encoding-type", ""))
    if encoding != "csc_matrix":
        raise ValueError(f"Column streaming requires dense or CSC encoding, got {encoding!r}")
    pointers = np.asarray(matrix["indptr"][start : stop + 1], dtype=np.int64)
    left, right = int(pointers[0]), int(pointers[-1])
    return sparse.csc_matrix(
        (
            np.asarray(matrix["data"][left:right], dtype=np.float64),
            np.asarray(matrix["indices"][left:right], dtype=np.int64),
            pointers - left,
        ),
        shape=(rows, stop - start),
    )


def audit_h5ad(path: Path, *, sample_rows: int = 32) -> dict[str, Any]:
    """Inspect metadata and a bounded expression sample; do not choose effect-size filters."""
    if sample_rows < 1 or sample_rows > 1024:
        raise ValueError("sample_rows must be between 1 and 1024")
    with h5py.File(path, "r") as handle:
        if not {"X", "obs", "var"}.issubset(handle.keys()):
            raise ValueError("H5AD must contain X, obs, and var")
        shape = matrix_shape(handle["X"])
        cells, genes = dataframe_index(handle["obs"]), dataframe_index(handle["var"])
        if shape != (len(cells), len(genes)):
            raise ValueError("Expression dimensions do not match obs/var indices")
        summaries: dict[str, Any] = {}
        observation_index = _text(handle["obs"].attrs.get("_index", "_index"))
        for key in handle["obs"]:
            if key == observation_index:
                continue
            values = read_column(handle["obs"], key)
            if len(values) != shape[0]:
                raise ValueError(f"Observation column {key} has inconsistent length")
            counts = Counter(_text(value) for value in values)
            summaries[key] = {
                "unique": len(counts),
                "missing_or_empty": counts.get("", 0) + counts.get("nan", 0),
                "most_common": counts.most_common(12),
                "dtype": str(values.dtype),
            }
        encoding = _text(handle["X"].attrs.get("encoding-type", "dense"))
        if encoding == "csc_matrix":
            # Sampling stored values is intentionally not called a sample of cells.
            entries = np.asarray(handle["X/data"][: sample_rows * 128], dtype=np.float64)
            sampling_axis = "leading stored values in CSC order; not a random cell sample"
            sampled_rows = None
        else:
            from scipy import sparse

            sample = read_rows(handle["X"], 0, min(sample_rows, shape[0]))
            entries = sample.data if sparse.issparse(sample) else sample.ravel()
            sampling_axis = "leading contiguous rows"
            sampled_rows = min(sample_rows, shape[0])
        expression = {
            "sampled_rows": sampled_rows,
            "sampling_axis": sampling_axis,
            "sampled_stored_values": len(entries),
            "sample_min": float(np.min(entries)) if len(entries) else None,
            "sample_max": float(np.max(entries)) if len(entries) else None,
            "fraction_near_integer_among_stored": (
                float(np.mean(np.isclose(entries, np.round(entries)))) if len(entries) else None
            ),
            "normalization": (
                "Unknown: inspect provenance; integer-like samples do not prove counts."
            ),
        }
        return {
            "schema_version": 1,
            "audited_at": utc_now(),
            "filename": path.name,
            "file_size_bytes": path.stat().st_size,
            "cells": shape[0],
            "genes": shape[1],
            "duplicate_cell_ids": len(cells) - len(set(cells)),
            "duplicate_gene_ids": len(genes) - len(set(genes)),
            "expression_encoding": _text(handle["X"].attrs.get("encoding-type", "dense")),
            "observation_columns": summaries,
            "variable_columns": list(handle["var"].keys()),
            "layers": list(handle["layers"].keys()) if "layers" in handle else [],
            "has_raw": "raw" in handle,
            "expression_sample": expression,
            "limitations": [
                "Technical cells are not assumed to be biological replicates.",
                "Metadata availability alone does not establish cross-context compatibility.",
                "This command is for raw-data auditing, never adaptive query-label access.",
            ],
        }
