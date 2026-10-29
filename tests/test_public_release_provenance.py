import hashlib
import json
import runpy
import shutil
import stat
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def public_release(tmp_path, monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    root = tmp_path / "clean-source"
    root.mkdir()

    def save(name, content):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode())
        return path

    save("README.md", "Small release fixture.\n")
    save("LICENSE", "MIT fixture notice.\n")
    save("pyproject.toml", '[project]\nname="mlresearch"\nversion="0.2.0"\n')
    save("uv.lock", "fixture locked environment\n")
    save("src/mlresearch/__init__.py", '__version__ = "0.2.0"\n')
    save(
        "src/mlresearch/datasets.json",
        json.dumps({"schema_version": 1, "datasets": [{"record": "fixture:record-v1"}]}),
    )
    save("paper/main.tex", "\\input{generated/numbers}\n")
    save("paper/references.bib", "% fixture references\n")
    save("paper/LICENSE", "CC BY 4.0 fixture notice.\n")
    numbers = save("paper/generated/numbers.tex", "% fixture derived table\n")
    save(
        "paper/generated/asset-manifest.json",
        json.dumps(
            {
                "state": "complete",
                "input_sha256": {},
                "output_sha256": {
                    "paper/generated/numbers.tex": hashlib.sha256(numbers.read_bytes()).hexdigest()
                },
            }
        ),
    )
    for name in ("build-paper.py", "package-publication.py"):
        destination = root / "scripts" / name
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(scripts / name, destination)
    for folder, version, evidence in (
        (
            "docs/results/external-evaluation-v1/runs/external-k562-to-rpe1-v1",
            "0.1.0",
            "docs/results/external-evaluation-v1/runs/external-k562-to-rpe1-v1/run-manifest.json",
        ),
        (
            "docs/results/publication-robustness-v1/frozen/suite",
            "0.2.0",
            "docs/evidence/publication-robustness-declaration-v1.json",
        ),
    ):
        snapshot = root / folder / "code.zip"
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(snapshot, "w") as archived:
            archived.writestr("pyproject.toml", f'[project]\nversion="{version}"\n')
        save(
            evidence,
            json.dumps(
                {
                    "environment": {
                        "git": {"revision": "1" * 40},
                        "source_tree_sha256": "2" * 64,
                    }
                }
            ),
        )
    pdf = save("output/pdf/joint-acquisition-study.pdf", b"%PDF-fixture\n" + b"0" * 2048)
    bibliography = save("output/pdf/main.bbl", "Compiled fixture bibliography.\n")
    build = runpy.run_path(str(root / "scripts/build-paper.py"))
    receipt = {
        "build_binding_schema": 1,
        "source": "main.tex",
        "pdf": pdf.name,
        "compiler": "tectonic",
        "compiler_version": "fixture-engine-1.0",
        "source_date_epoch": "1793145600",
        "manuscript_inputs_unchanged_during_build": True,
        "manuscript_inputs_sha256": build["manuscript_input_hashes"](root / "paper/main.tex", pdf),
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "bibliography_sha256": hashlib.sha256(bibliography.read_bytes()).hexdigest(),
        "asset_manifest_sha256": hashlib.sha256(
            (root / "paper/generated/asset-manifest.json").read_bytes()
        ).hexdigest(),
        "generated_asset_state": "complete",
        "evidence_input_hashes_checked": False,
        "unresolved_references": [],
        "overfull_boxes": [],
    }
    pdf.with_suffix(".build.json").write_text(json.dumps(receipt), encoding="utf-8")
    commit = "c" * 40
    exported = tmp_path / "tag-source.zip"
    with zipfile.ZipFile(exported, "w") as archive:
        archive.comment = commit.encode()
        for path in sorted(root.rglob("*")):
            if path.is_file() and ("output" not in path.relative_to(root).parts or path == pdf):
                archive.write(path, path.relative_to(root).as_posix())
    package = runpy.run_path(str(root / "scripts/package-publication.py"))

    def run(*extra):
        monkeypatch.chdir(root)
        monkeypatch.setattr(sys, "argv", ["package-publication.py", *extra])
        package["main"]()

    return SimpleNamespace(
        root=root,
        export=exported,
        commit=commit,
        receipt=receipt,
        package=package,
        run=run,
        save=save,
    )


def test_clean_public_release_has_explicit_provenance_and_non_circular_checksums(public_release):
    case = public_release
    assert not (case.root / ".git").exists()
    case.run(
        "--source-tag",
        "v0.2.0",
        "--source-commit",
        case.commit,
        "--source-export",
        str(case.export),
    )
    output = case.root / "output/release"
    manifest = json.loads((output / "release-manifest-v0.2.0.json").read_text())
    source = manifest["public_source"]
    assert source["tag"] == "v0.2.0"
    assert source["commit"] == source["export_commit_comment"] == case.commit
    assert source["export_sha256"] == hashlib.sha256(case.export.read_bytes()).hexdigest()
    environment = manifest["environment_and_scientific_provenance"]
    assert environment["package_version"] == "0.2.0"
    assert environment["scientific_snapshots"]["original_primary"]["package_version"] == "0.1.0"
    assert (
        environment["scientific_snapshots"]["post_primary_robustness"]["package_version"] == "0.2.0"
    )
    assert (
        environment["data_registry"]["sha256"]
        == hashlib.sha256((case.root / "src/mlresearch/datasets.json").read_bytes()).hexdigest()
    )
    assert environment["manuscript_build"]["compiler_version"] == "fixture-engine-1.0"
    assert environment["packaging_runtime"]["python"]
    expected = {
        "joint-acquisition-study.pdf",
        "manuscript-source-v0.2.0.zip",
        "code-and-evidence-v0.2.0.zip",
        "arxiv-source-v0.2.0.zip",
        "release-manifest-v0.2.0.json",
    }
    checksums = {}
    for line in (output / "SHA256SUMS").read_text().splitlines():
        actual, name = line.split("  ", 1)
        assert actual == hashlib.sha256((output / name).read_bytes()).hexdigest()
        checksums[name] = actual
    assert set(checksums) == expected
    assert {entry["file"] for entry in manifest["release_files"]} == expected | {"SHA256SUMS"}


@pytest.mark.parametrize("commit", ["abc123", "z" * 40, "c" * 39])
def test_release_refuses_incomplete_or_nonhex_commit(public_release, commit):
    case = public_release
    with pytest.raises(ValueError, match="40-character"):
        case.package["validate_source_export"](case.root, case.export, "v0.2.0", commit)


def test_release_refuses_wrong_archive_commit(public_release):
    case = public_release
    with pytest.raises(ValueError, match="commit comment does not match"):
        case.package["validate_source_export"](case.root, case.export, "v0.2.0", "a" * 40)


def test_absent_export_comment_is_recorded_without_parent_git_inference(public_release):
    case = public_release
    with zipfile.ZipFile(case.export, "a") as archive:
        archive.comment = b""
    source = case.package["validate_source_export"](case.root, case.export, "v0.2.0", case.commit)
    assert source["commit"] == case.commit
    assert source["export_commit_comment"] is None


@pytest.mark.parametrize("change", ["edit", "delete"])
def test_release_refuses_changed_or_missing_exported_payload(public_release, change):
    case = public_release
    readme = case.root / "README.md"
    if change == "edit":
        readme.write_text("An uncommitted change after export.\n", encoding="utf-8")
    else:
        readme.unlink()
    with pytest.raises(ValueError, match="does not match the clean source root"):
        case.package["validate_source_export"](case.root, case.export, "v0.2.0", case.commit)


@pytest.mark.parametrize(
    "unsafe",
    ["../outside.txt", "C:/outside.txt", "paper\\section.tex", "paper/./x", "paper//x"],
)
def test_release_refuses_unsafe_export_paths(public_release, tmp_path, unsafe):
    case = public_release
    exported = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(exported, "w") as archive:
        archive.comment = case.commit.encode()
        archive.writestr(unsafe, b"unsafe")
    if "\\" in unsafe:
        # Windows' ZIP writer normalizes separators; test actual on-disk unsafe names.
        exported.write_bytes(
            exported.read_bytes().replace(unsafe.replace("\\", "/").encode(), unsafe.encode())
        )
    with pytest.raises(ValueError, match="Unsafe or duplicate"):
        case.package["validate_source_export"](case.root, exported, "v0.2.0", case.commit)


def test_release_refuses_archive_symlinks(public_release, tmp_path):
    case = public_release
    exported = tmp_path / "symlink.zip"
    with zipfile.ZipFile(exported, "w") as archive:
        archive.comment = case.commit.encode()
        member = zipfile.ZipInfo("link.txt")
        member.create_system = 3
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(member, "../outside.txt")
    with pytest.raises(ValueError, match="symlinks are not supported"):
        case.package["validate_source_export"](case.root, exported, "v0.2.0", case.commit)


def test_release_refuses_case_aliased_export_names(public_release, tmp_path):
    case = public_release
    exported = tmp_path / "aliased.zip"
    with zipfile.ZipFile(exported, "w") as archive:
        archive.comment = case.commit.encode()
        archive.writestr("README.md", (case.root / "README.md").read_bytes())
        archive.writestr("readme.md", (case.root / "README.md").read_bytes())
    with pytest.raises(ValueError, match="Unsafe or duplicate"):
        case.package["validate_source_export"](case.root, exported, "v0.2.0", case.commit)


def test_release_refuses_an_extra_first_party_notebook_before_writing_archives(public_release):
    case = public_release
    case.save("notebooks/unexported.ipynb", '{"cells": []}')
    with pytest.raises(ValueError, match="Unexported first-party release payload"):
        case.run(
            "--source-tag",
            "v0.2.0",
            "--source-commit",
            case.commit,
            "--source-export",
            str(case.export),
        )
    assert not (case.root / "output/release").exists()


def test_only_bound_unexported_compiler_products_are_allowed(public_release):
    case = public_release
    source = case.package["validate_source_export"](case.root, case.export, "v0.2.0", case.commit)
    payloads = {
        "paper/main.bbl": case.receipt["bibliography_sha256"],
        "output/pdf/joint-acquisition-study.pdf": case.receipt["pdf_sha256"],
    }
    case.package["validate_exported_code_payloads"](payloads, source, case.receipt)
    payloads["paper/main.bbl"] = "0" * 64
    with pytest.raises(ValueError, match="differs from its tagged source or bound build"):
        case.package["validate_exported_code_payloads"](payloads, source, case.receipt)


def test_public_output_does_not_silently_include_unlisted_files(public_release):
    case = public_release
    unexpected = case.save("output/release/unrelated.txt", "Do not publish this unrelated file.\n")
    with pytest.raises(ValueError, match="contains unlisted files"):
        case.run(
            "--source-tag",
            "v0.2.0",
            "--source-commit",
            case.commit,
            "--source-export",
            str(case.export),
            "--replace",
        )
    assert unexpected.read_text() == "Do not publish this unrelated file.\n"
    assert not (unexpected.parent / "SHA256SUMS").exists()


def test_public_mode_arguments_are_all_required_and_default_stays_available(public_release):
    case = public_release
    with pytest.raises(SystemExit):
        case.run("--source-tag", "v0.2.0")
    case.run()
    manifest = json.loads((case.root / "output/release/release-manifest-v0.2.0.json").read_text())
    assert "public_source" not in manifest
    assert (case.root / "output/release/SHA256SUMS").is_file()
