import hashlib
import json
import runpy
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def build_case(tmp_path, monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    build = runpy.run_path(str(scripts / "build-paper.py"))
    package = runpy.run_path(str(scripts / "package-publication.py"))
    root = tmp_path / "original"
    paper = root / "paper"
    (paper / "generated").mkdir(parents=True)
    (paper / "sections").mkdir()
    source = paper / "main.tex"
    source.write_text("\\input{sections/body}\n", encoding="utf-8")
    (paper / "sections/body.tex").write_text("Original manuscript.\n", encoding="utf-8")
    (paper / "references.bib").write_text("% Bibliography source\n", encoding="utf-8")
    numbers = paper / "generated/numbers.tex"
    numbers.write_text("% Authenticated generated input\n", encoding="utf-8")
    (paper / "generated/asset-manifest.json").write_text(
        json.dumps(
            {
                "state": "complete",
                "input_sha256": {},
                "output_sha256": {
                    "paper/generated/numbers.tex": hashlib.sha256(numbers.read_bytes()).hexdigest()
                },
            }
        ),
        encoding="utf-8",
    )
    pdf = root / "output/pdf/study.pdf"
    behavior = SimpleNamespace(during_compile=None)

    def compile_stub(command, *, cwd, env, check):
        assert env["SOURCE_DATE_EPOCH"] == "1793145600"
        assert check is True
        destination = Path(command[command.index("--outdir") + 1])
        (destination / "main.pdf").write_bytes(b"%PDF-test-build\n" + b"0" * 2048)
        (destination / "main.bbl").write_text("Compiled bibliography.\n", encoding="utf-8")
        (destination / "main.log").write_text("", encoding="utf-8")
        if behavior.during_compile is not None:
            behavior.during_compile()

    monkeypatch.setattr(build["subprocess"], "run", compile_stub)

    def run(output=pdf):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "build-paper.py",
                "--source",
                str(source),
                "--output",
                str(output),
                "--compiler",
                "tectonic-test",
            ],
        )
        build["main"]()

    return SimpleNamespace(
        root=root,
        source=source,
        pdf=pdf,
        bibliography=pdf.parent / "main.bbl",
        build=build,
        validate=package["validate_build_receipt"],
        run=run,
        behavior=behavior,
    )


def test_build_binding_is_portable_to_a_relocated_tree(build_case, tmp_path):
    case = build_case
    case.run()
    original = case.validate(case.source, case.pdf, case.bibliography)
    relocated = tmp_path / "relocated"
    shutil.copytree(case.root, relocated)
    copied = case.validate(
        relocated / "paper/main.tex",
        relocated / "output/pdf/study.pdf",
        relocated / "output/pdf/main.bbl",
    )
    assert copied == original
    assert "sections/body.tex" in original["manuscript_inputs_sha256"]
    assert all(not Path(name).is_absolute() for name in original["manuscript_inputs_sha256"])


@pytest.mark.parametrize("change", ["edit", "delete", "add", "references", "figure"])
def test_packaging_refuses_changed_deleted_or_added_manuscript_inputs(build_case, change):
    case = build_case
    case.run()
    body = case.source.parent / "sections/body.tex"
    if change == "edit":
        body.write_text("Edited after compilation.\n", encoding="utf-8")
    elif change == "delete":
        body.unlink()
    elif change == "add":
        (body.parent / "new-section.tex").write_text("New source.\n", encoding="utf-8")
    elif change == "references":
        (case.source.parent / "references.bib").write_text("% New citations\n", encoding="utf-8")
    else:
        (case.source.parent / "new-figure.pdf").write_bytes(b"New figure input")
    with pytest.raises(ValueError, match="inputs changed after compilation"):
        case.validate(case.source, case.pdf, case.bibliography)


@pytest.mark.parametrize("changed", ["pdf", "bibliography"])
def test_packaging_refuses_changed_compiled_outputs(build_case, changed):
    case = build_case
    case.run()
    path = case.pdf if changed == "pdf" else case.bibliography
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="Compiled manuscript binding changed"):
        case.validate(case.source, case.pdf, case.bibliography)


@pytest.mark.parametrize("receipt_state", ["missing", "legacy"])
def test_packaging_requires_a_bound_build_receipt(build_case, receipt_state):
    case = build_case
    case.run()
    receipt = case.pdf.with_suffix(".build.json")
    if receipt_state == "missing":
        receipt.unlink()
    else:
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        payload.pop("build_binding_schema")
        receipt.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="[Mm]anuscript build receipt"):
        case.validate(case.source, case.pdf, case.bibliography)


def test_build_refuses_inputs_mutated_during_compilation(build_case):
    case = build_case
    case.behavior.during_compile = lambda: case.source.write_text("Changed during build.\n")
    with pytest.raises(SystemExit, match="inputs changed during compilation"):
        case.run()
    assert not case.pdf.with_suffix(".build.json").exists()


def test_source_only_build_can_rebuild_in_its_own_directory(build_case):
    case = build_case
    paper = case.source.parent
    destination = paper / "study.pdf"
    bibliography = paper / "main.bbl"
    bibliography.write_text("Supplied compiled bibliography.\n", encoding="utf-8")
    case.run(destination)
    first = case.validate(case.source, destination, bibliography)
    case.run(destination)
    second = case.validate(case.source, destination, bibliography)
    assert first["manuscript_inputs_sha256"] == second["manuscript_inputs_sha256"]
    assert "main.bbl" not in second["manuscript_inputs_sha256"]
    assert "study.pdf" not in second["manuscript_inputs_sha256"]
