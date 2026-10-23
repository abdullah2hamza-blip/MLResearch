"""Build the manuscript using Tectonic or a conventional pdfLaTeX/BibTeX installation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("paper/main.tex"))
    parser.add_argument(
        "--output", type=Path, default=Path("output/pdf/joint-acquisition-study.pdf")
    )
    parser.add_argument(
        "--compiler", help="Path to tectonic or pdflatex; otherwise discover on PATH"
    )
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    destination = args.output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    asset_manifest = source.parent / "generated/asset-manifest.json"
    if not asset_manifest.is_file():
        raise SystemExit("Missing generated asset manifest; regenerate manuscript assets first")
    assets = json.loads(asset_manifest.read_text(encoding="utf-8"))
    if assets["state"] != "complete":
        raise SystemExit("Manuscript assets omit the completed robustness analysis")
    for relative, expected in assets["output_sha256"].items():
        local = source.parent / Path(relative).relative_to("paper")
        if hashlib.sha256(local.read_bytes()).hexdigest() != expected:
            raise SystemExit("Changed generated manuscript asset: " + relative)
    repository = source.parent.parent
    evidence_available = (repository / "src/mlresearch").is_dir()
    if evidence_available:
        for relative, expected in assets["input_sha256"].items():
            if hashlib.sha256((repository / relative).read_bytes()).hexdigest() != expected:
                raise SystemExit("Changed manuscript evidence input: " + relative)
    compiler = args.compiler or shutil.which("tectonic") or shutil.which("pdflatex")
    if compiler is None:
        raise SystemExit("Install Tectonic or pdfLaTeX/BibTeX, or pass --compiler PATH")
    executable = str(Path(compiler).resolve()) if Path(compiler).is_file() else compiler
    environment = dict(os.environ)
    environment["SOURCE_DATE_EPOCH"] = "1792713600"  # 2026-10-23, reproducible document date

    def run(command: list[str], cwd: Path) -> None:
        subprocess.run(command, cwd=cwd, env=environment, check=True)

    if "tectonic" in Path(executable).stem.lower():
        run(
            [
                executable,
                "--keep-logs",
                "--keep-intermediates",
                "--outdir",
                str(destination.parent),
                source.name,
            ],
            source.parent,
        )
        implementation = "tectonic"
    elif "pdflatex" in Path(executable).stem.lower():
        command = [
            executable,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-output-directory=" + str(destination.parent),
            source.name,
        ]
        run(command, source.parent)
        bibliography = shutil.which("bibtex")
        if bibliography is None:
            raise SystemExit("pdfLaTeX builds also require bibtex on PATH")
        environment["BIBINPUTS"] = (
            str(source.parent) + os.pathsep + environment.get("BIBINPUTS", "")
        )
        run([bibliography, source.stem], destination.parent)
        run(command, source.parent)
        run(command, source.parent)
        implementation = "pdflatex+bibtex"
    else:
        raise SystemExit("Supported compiler names contain tectonic or pdflatex")
    built = destination.parent / (source.stem + ".pdf")
    if not built.is_file() or built.stat().st_size < 1024:
        raise SystemExit("Compiler did not create a nonempty PDF")
    if built != destination:
        shutil.copy2(built, destination)
    log = destination.parent / (source.stem + ".log")
    log_text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    unresolved = [
        line
        for line in log_text.splitlines()
        if "undefined" in line.lower()
        and ("reference" in line.lower() or "citation" in line.lower())
    ]
    report = {
        "compiler": implementation,
        "source": source.name,
        "pdf": destination.name,
        "pdf_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "pdf_bytes": destination.stat().st_size,
        "unresolved_references": unresolved,
        "generated_asset_state": assets["state"],
        "evidence_input_hashes_checked": evidence_available,
        "overfull_boxes": [line for line in log_text.splitlines() if "Overfull" in line],
        "qualification": "TeX build evidence; visual inspection is a separate required check.",
    }
    destination.with_suffix(".build.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    if unresolved:
        raise SystemExit("Unresolved manuscript citations/references; see build JSON")
    print(f"Built {destination} ({report['pdf_bytes']} bytes)")


if __name__ == "__main__":
    main()
