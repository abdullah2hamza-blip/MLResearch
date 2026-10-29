import csv
import hashlib
import json
import runpy
from pathlib import Path

import pytest


@pytest.fixture
def notebook_case(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "matplotlib"))
    stage = runpy.run_path(str(root / "notebooks/prepare_saved_result_inputs.py"))["stage_inputs"]
    execute = runpy.run_path(str(root / "notebooks/validate_saved_results_notebook.py"))[
        "execute_notebook"
    ]
    inputs = tmp_path / "inputs"
    stage(root, inputs, "0" * 40, "local-validation")
    notebook = root / "notebooks/joint-acquisition-reanalysis.ipynb"
    return inputs, notebook, tmp_path / "outputs", execute


def test_notebook_reproduces_primary_and_all_robustness_results(notebook_case):
    inputs, notebook, output, execute = notebook_case
    result = execute(notebook, inputs, output)
    assert result["state"] == "passed_local_notebook_execution"
    report = result["verification"]
    assert (
        report["verification_category"]
        == "Re-analysis of saved outputs; not full experimental reproduction"
    )
    assert report["robustness_contrasts_recomputed"] == 32
    assert report["paired_query_rows_checked"] == 4192
    assert report["queries_per_robustness_contrast"] == 131
    assert report["maximum_absolute_paired_mean_discrepancy"] < 1e-14
    assert report["robustness_extension_lower_error_counts"] == {
        "original_grid/worst_query": 3,
        "original_grid/mean_query": 2,
        "full_grid/worst_query": 2,
        "full_grid/mean_query": 5,
    }
    with (output / "primary-comparisons.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    primary = {
        row["run"]: float(row["relative_change_percent"])
        for row in rows
        if row["reference"] == "worst_query"
    }
    assert primary["external-k562-to-rpe1-v1"] == pytest.approx(0.5650687, abs=1e-7)
    assert primary["external-rpe1-to-k562-v1"] == pytest.approx(0.0137794, abs=1e-7)
    for name, digest in report["output_sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    assert (output / "primary-curves.png").stat().st_size > 10000
    assert (output / "robustness-matrix.png").stat().st_size > 10000


def test_notebook_refuses_a_table_that_changed_after_release(notebook_case):
    inputs, notebook, output, execute = notebook_case
    path = inputs / "results/primary-curves.csv"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="Changed input table"):
        execute(notebook, inputs, output)
    assert not (output / "reanalysis-verification.json").exists()


def test_notebook_refuses_duplicate_queries_even_with_matching_checksum(notebook_case):
    inputs, notebook, output, execute = notebook_case
    path = inputs / "results/paired-query-areas.csv"
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    rows[1]["query"] = rows[0]["query"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest_path = inputs / "mlresearch-results-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["paired_query_areas"]["sha256"] = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="131 distinct query identities"):
        execute(notebook, inputs, output)
    assert json.loads((output / "reanalysis-verification.json").read_text())["state"] == "running"
