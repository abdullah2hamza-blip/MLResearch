"""Execute the saved-result notebook top to bottom in a fresh Python process."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path


def execute_notebook(notebook: Path, inputs: Path, output: Path) -> dict:
    """Run ordinary Python cells; this is local validation, not a Kaggle execution."""
    import matplotlib

    matplotlib.use("Agg")
    document = json.loads(notebook.read_text(encoding="utf-8"))
    if document.get("nbformat") != 4:
        raise ValueError("Expected a version-four Jupyter notebook")
    previous = {
        key: os.environ.get(key) for key in ("MLRESEARCH_INPUT_ROOT", "MLRESEARCH_OUTPUT_ROOT")
    }
    os.environ["MLRESEARCH_INPUT_ROOT"] = str(inputs.resolve())
    os.environ["MLRESEARCH_OUTPUT_ROOT"] = str(output.resolve())
    namespace = {"__name__": "__main__"}
    started = time.perf_counter()
    count = 0
    try:
        for index, cell in enumerate(document["cells"]):
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"])
            exec(compile(source, f"{notebook.name}:cell-{index + 1}", "exec"), namespace)
            count += 1
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    report = json.loads((output / "reanalysis-verification.json").read_text(encoding="utf-8"))
    if report["state"] != "passed_saved_result_reanalysis":
        raise ValueError("Notebook did not produce its completed saved-result verification")
    return {
        "state": "passed_local_notebook_execution",
        "code_cells": count,
        "notebook_sha256": hashlib.sha256(notebook.read_bytes()).hexdigest(),
        "elapsed_seconds": time.perf_counter() - started,
        "verification": report,
        "qualification": "Fresh local top-to-bottom Python execution; not a hosted Kaggle run.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--notebook",
        type=Path,
        default=Path(__file__).with_name("joint-acquisition-reanalysis.ipynb"),
    )
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = execute_notebook(args.notebook, args.inputs, args.output)
    (args.output / "local-execution.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Executed {report['code_cells']} notebook cells from a fresh namespace")


if __name__ == "__main__":
    main()
