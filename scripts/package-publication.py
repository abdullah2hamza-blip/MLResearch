"""Create manuscript-source and code/evidence ZIPs from explicit publication paths."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import runpy
import shutil
import stat
import tomllib
import zipfile
from pathlib import Path, PurePosixPath


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def validate_source_export(root: Path, source_export: Path, tag: str, commit: str) -> dict:
    """Bind release inputs to an explicit Git archive without discovering a parent Git repo."""
    if re.fullmatch(r"[0-9a-fA-F]{40}", commit) is None:
        raise ValueError("Source commit must be a complete 40-character hexadecimal Git commit")
    if not tag or tag.strip() != tag or any(ord(character) < 32 for character in tag):
        raise ValueError("Source tag must be a nonempty Git tag without control characters")
    root = root.resolve()
    hashes = {}
    seen = set()
    with zipfile.ZipFile(source_export) as exported:
        try:
            comment = exported.comment.decode("ascii").strip()
        except UnicodeDecodeError as error:
            raise ValueError("Source export commit comment is not ASCII") from error
        if comment and comment.lower() != commit.lower():
            raise ValueError("Source export commit comment does not match the declared commit")
        for member in exported.infolist():
            name = member.filename
            relative = PurePosixPath(name)
            parts = relative.parts
            if (
                not name
                or "\\" in name
                or "\\" in member.orig_filename
                or ":" in name
                or "\x00" in member.orig_filename
                or name.rstrip("/") != relative.as_posix()
                or relative.is_absolute()
                or ".." in parts
                or any(part.rstrip(" .").lower() == ".git" for part in parts)
                or name.rstrip("/").casefold() in seen
            ):
                raise ValueError("Unsafe or duplicate source export path: " + name)
            seen.add(name.rstrip("/").casefold())
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError("Source export symlinks are not supported: " + name)
            if member.is_dir():
                continue
            path = root.joinpath(*parts)
            if not path.resolve().is_relative_to(root) or path.is_symlink():
                raise ValueError(
                    "Source export path resolves outside the clean source root: " + name
                )
            payload_hash = digest(exported.read(member))
            if not path.is_file() or digest(path.read_bytes()) != payload_hash:
                raise ValueError(
                    "Source export payload does not match the clean source root: " + name
                )
            hashes[name] = payload_hash
    if not hashes:
        raise ValueError("Source export contains no tracked payloads")
    return {
        "tag": tag,
        "commit": commit.lower(),
        "export_file": source_export.name,
        "export_sha256": digest(source_export.read_bytes()),
        "export_commit_comment": comment.lower() or None,
        "tracked_payload_members": len(hashes),
        "tracked_payload_sha256": hashes,
        "qualification": "Explicit flat Git archive; no parent Git discovery. "
        "A present comment binds the declared commit. The supplied tag is checked at publication.",
    }


def validate_exported_code_payloads(
    code_hashes: dict[str, str], source: dict, receipt: dict
) -> None:
    """Only tagged first-party bytes and the two bound compiler products may be released."""
    exported = source["tracked_payload_sha256"]
    products = {
        "paper/main.bbl": receipt["bibliography_sha256"],
        "output/pdf/joint-acquisition-study.pdf": receipt["pdf_sha256"],
    }
    for name, payload_hash in code_hashes.items():
        expected = exported.get(name, products.get(name))
        if expected is None:
            raise ValueError("Unexported first-party release payload: " + name)
        if payload_hash != expected:
            raise ValueError(
                "Release payload differs from its tagged source or bound build: " + name
            )


def release_environment(root: Path, receipt: dict, *, require_scientific_inputs: bool) -> dict:
    """Report observed packaging/build environment and immutable scientific versions separately."""
    project_path = root / "pyproject.toml"
    project = tomllib.loads(project_path.read_text(encoding="utf-8"))["project"]
    packages = {}
    for name in ("mlresearch", "numpy", "scipy", "h5py", "matplotlib"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    snapshots = {}
    for name, snapshot_name, evidence_name in (
        (
            "original_primary",
            "docs/results/external-evaluation-v1/runs/external-k562-to-rpe1-v1/code.zip",
            "docs/results/external-evaluation-v1/runs/external-k562-to-rpe1-v1/run-manifest.json",
        ),
        (
            "post_primary_robustness",
            "docs/results/publication-robustness-v1/frozen/suite/code.zip",
            "docs/evidence/publication-robustness-declaration-v1.json",
        ),
    ):
        snapshot, evidence = root / snapshot_name, root / evidence_name
        if not snapshot.is_file() or not evidence.is_file():
            if require_scientific_inputs:
                raise ValueError("Missing scientific snapshot/evidence for public release: " + name)
            continue
        with zipfile.ZipFile(snapshot) as archived:
            specification = tomllib.loads(archived.read("pyproject.toml").decode("utf-8"))
        environment = json.loads(evidence.read_text(encoding="utf-8")).get("environment", {})
        snapshots[name] = {
            "snapshot": snapshot_name,
            "snapshot_sha256": digest(snapshot.read_bytes()),
            "package_version": specification["project"]["version"],
            "evidence": evidence_name,
            "evidence_sha256": digest(evidence.read_bytes()),
            "recorded_git_revision": environment.get("git", {}).get("revision"),
            "recorded_source_tree_sha256": environment.get("source_tree_sha256"),
            "qualification": "Recorded numerical source snapshot; the release commit is separate.",
        }
    registry_path = root / "src/mlresearch/datasets.json"
    if require_scientific_inputs and not registry_path.is_file():
        raise ValueError("Missing pinned data registry for public release")
    registry = (
        json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.is_file() else None
    )
    lock = root / "uv.lock"
    if require_scientific_inputs and not lock.is_file():
        raise ValueError("Missing locked environment for public release")
    return {
        "package_version": project["version"],
        "project_specification_sha256": digest(project_path.read_bytes()),
        "uv_lock_sha256": digest(lock.read_bytes()) if lock.is_file() else None,
        "scientific_snapshots": snapshots,
        "data_registry": {
            "file": "src/mlresearch/datasets.json",
            "sha256": digest(registry_path.read_bytes()) if registry is not None else None,
            "schema_version": registry.get("schema_version") if registry is not None else None,
            "upstream_records": sorted(
                {entry["record"] for entry in registry.get("datasets", []) if "record" in entry}
            )
            if registry is not None
            else [],
        },
        "packaging_runtime": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "logical_cpus": os.cpu_count(),
            "installed_package_versions": packages,
        },
        "manuscript_build": {
            "compiler": receipt["compiler"],
            "compiler_version": receipt.get("compiler_version"),
            "source_date_epoch": receipt.get("source_date_epoch"),
            "generated_asset_state": receipt["generated_asset_state"],
            "evidence_input_hashes_checked": receipt.get("evidence_input_hashes_checked"),
            "qualification": "Build receipt; unrecorded compiler versions are not inferred.",
        },
    }


def validate_build_receipt(source: Path, pdf: Path, bibliography: Path) -> dict:
    """Refuse a stale or unbound compiled manuscript before creating any archive."""
    receipt_path = pdf.with_suffix(".build.json")
    if not receipt_path.is_file():
        raise ValueError("Missing manuscript build receipt; rebuild before packaging")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (
        receipt.get("build_binding_schema") != 1
        or receipt.get("source") != source.name
        or receipt.get("pdf") != pdf.name
        or receipt.get("manuscript_inputs_unchanged_during_build") is not True
    ):
        raise ValueError("Unbound manuscript build receipt; rebuild before packaging")
    build = runpy.run_path(str(Path(__file__).with_name("build-paper.py")))
    current = build["manuscript_input_hashes"](source, pdf)
    if receipt.get("manuscript_inputs_sha256") != current:
        raise ValueError("Manuscript inputs changed after compilation; rebuild before packaging")
    expected = (
        (pdf, "pdf_sha256"),
        (bibliography, "bibliography_sha256"),
        (source.parent / "generated/asset-manifest.json", "asset_manifest_sha256"),
    )
    for path, key in expected:
        if not path.is_file() or digest(path.read_bytes()) != receipt.get(key):
            raise ValueError("Compiled manuscript binding changed: " + path.name)
    if (
        receipt.get("generated_asset_state") != "complete"
        or receipt.get("unresolved_references") != []
        or receipt.get("overfull_boxes") != []
    ):
        raise ValueError("Manuscript build has unresolved references or layout errors")
    return receipt


def archive(
    path: Path, members: dict[str, Path | bytes], kind: str, include_inventory: bool = True
) -> dict:
    hashes = {}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for name, source in sorted(members.items()):
            if not name.isascii() or name.startswith("/") or ".." in Path(name).parts:
                raise ValueError("Unsafe/nonportable archive path: " + name)
            payload = source if isinstance(source, bytes) else source.read_bytes()
            if re.search(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-proj-[A-Za-z0-9_-]{30,})", payload):
                raise ValueError("Possible secret requires inspection: " + name)
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            output.writestr(info, payload)
            hashes[name] = digest(payload)
        inventory = {
            "kind": kind,
            "version": "0.2.0",
            "sha256": hashes,
            "excluded": [
                "raw/prepared expression",
                "large prediction arrays",
                "credentials",
                "Git history",
                "machine caches and environments",
            ],
            "licenses": (
                "Original code MIT; manuscript CC BY 4.0; third parties retain their terms."
            ),
        }
        if include_inventory:
            info = zipfile.ZipInfo("CONTENTS.sha256.json", date_time=(2026, 10, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            output.writestr(info, json.dumps(inventory, indent=2, sort_keys=True) + "\n")
    with zipfile.ZipFile(path) as check:
        expected_names = set(hashes) | ({"CONTENTS.sha256.json"} if include_inventory else set())
        if check.testzip() is not None or set(check.namelist()) != expected_names:
            raise ValueError("Archive integrity or membership failure")
        for name, expected in hashes.items():
            if digest(check.read(name)) != expected:
                raise ValueError("Archive payload verification failed: " + name)
    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": digest(path.read_bytes()),
        "payload_members": len(hashes),
        "member_sha256": hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output/release"))
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--source-tag", help="Actual release tag represented by --source-export")
    parser.add_argument(
        "--source-commit", help="Complete 40-character commit represented by the export"
    )
    parser.add_argument(
        "--source-export", type=Path, help="Clean flat git archive ZIP for that tag"
    )
    args = parser.parse_args()
    source_arguments = (args.source_tag, args.source_commit, args.source_export)
    if any(value is not None for value in source_arguments) and not all(
        value is not None for value in source_arguments
    ):
        parser.error(
            "Public release mode requires --source-tag, --source-commit and --source-export"
        )
    root = Path.cwd().resolve()
    destination = args.output.resolve()
    if not destination.is_relative_to(root):
        raise ValueError("Choose an output folder inside this checkout")
    names = [
        "manuscript-source-v0.2.0.zip",
        "code-and-evidence-v0.2.0.zip",
        "arxiv-source-v0.2.0.zip",
        "release-manifest-v0.2.0.json",
    ]
    if (
        any(
            (destination / name).exists()
            for name in [*names, "joint-acquisition-study.pdf", "SHA256SUMS"]
        )
        and not args.replace
    ):
        raise ValueError("Preserve the release, or explicitly use --replace after verification")
    public_source = (
        validate_source_export(root, args.source_export, args.source_tag, args.source_commit)
        if args.source_export is not None
        else None
    )
    if public_source is not None and destination.exists():
        known_outputs = {*names, "joint-acquisition-study.pdf", "SHA256SUMS"}
        if any(path.name not in known_outputs or path.is_dir() for path in destination.iterdir()):
            raise ValueError("Public release output contains unlisted files; choose a fresh folder")
    assets = json.loads(Path("paper/generated/asset-manifest.json").read_text(encoding="utf-8"))
    if assets["state"] != "complete":
        raise ValueError("Incomplete manuscript assets")
    for relative, expected in assets["output_sha256"].items():
        if digest(Path(relative).read_bytes()) != expected:
            raise ValueError("Manuscript asset changed: " + relative)
    pdf = Path("output/pdf/joint-acquisition-study.pdf")
    bibliography = Path("output/pdf/main.bbl")
    if not pdf.is_file() or not bibliography.is_file():
        raise ValueError("Build the manuscript and compiled bibliography first")
    receipt = validate_build_receipt(Path("paper/main.tex"), pdf, bibliography)
    manuscript = {
        path.relative_to("paper").as_posix(): path
        for path in Path("paper").rglob("*")
        if path.is_file() and path.suffix not in {".aux", ".log", ".out", ".blg"}
    }
    manuscript["main.bbl"] = bibliography
    manuscript["build-paper.py"] = Path("scripts/build-paper.py")
    manuscript["CODE-LICENSE"] = Path("LICENSE")
    manuscript["README.txt"] = (
        b"Technical report and supplement, Abdullah Hamza, October 28, 2026.\n"
        b"License: CC BY 4.0; see LICENSE.\n"
        b"The build helper is MIT licensed; see CODE-LICENSE.\n"
        b"Compile: python build-paper.py --source main.tex --output joint-acquisition-study.pdf\n"
        b"Requires Tectonic or pdfLaTeX/BibTeX. TeX source needs no expression data.\n"
        b"Asset hashes verified; underlying evidence is in the separate code archive.\n"
        b"For arXiv upload arxiv-source-v0.2.0.zip and select main.tex; see current instructions.\n"
    )
    arxiv = {
        name: payload
        for name, payload in manuscript.items()
        if name.endswith(".tex")
        or name in {"references.bib", "main.bbl"}
        or (name.startswith("figures/") and name.endswith(".pdf"))
    }
    code = {}
    for directory in (
        "src",
        "tests",
        "scripts",
        "notebooks",
        "configs",
        "docs",
        "paper",
        ".github",
    ):
        for path in Path(directory).rglob("*"):
            if (
                path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix not in {".pyc", ".aux", ".log", ".out", ".blg"}
            ):
                code[path.as_posix()] = path
    for name in (
        "README.md",
        "LICENSE",
        "CITATION.cff",
        "pyproject.toml",
        "uv.lock",
        ".gitignore",
        ".gitattributes",
        ".python-version",
    ):
        if Path(name).is_file():
            code[name] = Path(name)
    code[pdf.as_posix()] = pdf
    code["paper/main.bbl"] = bibliography
    if public_source is not None:
        validate_exported_code_payloads(
            {name: digest(path.read_bytes()) for name, path in code.items()}, public_source, receipt
        )
    environment = (
        release_environment(root, receipt, require_scientific_inputs=True)
        if public_source is not None
        else None
    )
    destination.mkdir(parents=True, exist_ok=True)
    release_pdf = destination / pdf.name
    if release_pdf.resolve() != pdf.resolve():
        shutil.copyfile(pdf, release_pdf)
    print(
        f"Packing {len(manuscript)} manuscript and {len(code)} code/evidence payloads", flush=True
    )
    records = [
        archive(destination / names[0], manuscript, "manuscript-source"),
        archive(destination / names[1], code, "code-and-evidence"),
        archive(destination / names[2], arxiv, "arxiv-source", include_inventory=False),
    ]
    if public_source is not None:
        validate_exported_code_payloads(records[1]["member_sha256"], public_source, receipt)
    manifest = {
        "state": "built_and_payload_verified",
        "version": "0.2.0",
        "packager_sha256": digest(Path(__file__).read_bytes()),
        "build_receipt_sha256": digest(pdf.with_suffix(".build.json").read_bytes()),
        "pdf": {
            "file": pdf.as_posix(),
            "sha256": digest(pdf.read_bytes()),
            "bytes": pdf.stat().st_size,
        },
        "archives": records,
        "release_files": [
            {"file": pdf.name, "role": "technical report and supplement PDF"},
            *[
                {"file": record["file"], "role": role}
                for record, role in zip(
                    records,
                    (
                        "editable manuscript sources",
                        "code and retained evidence",
                        "minimal TeX upload",
                    ),
                    strict=True,
                )
            ],
            {"file": names[3], "role": "release manifest; checksum in SHA256SUMS"},
            {"file": "SHA256SUMS", "role": "checksums; its own hash intentionally excluded"},
        ],
        "qualification": (
            "Locally built artifacts; public hosting, peer review, submission and a DOI "
            "are not established by this manifest."
        ),
    }
    if public_source is not None:
        manifest["public_source"] = public_source
        manifest["environment_and_scientific_provenance"] = environment
    (destination / names[3]).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    checksum_files = [release_pdf, *(destination / name for name in names)]
    (destination / "SHA256SUMS").write_text(
        "".join(f"{digest(path.read_bytes())}  {path.name}\n" for path in sorted(checksum_files)),
        encoding="utf-8",
    )
    print("All three archives and exact member payloads verified", flush=True)


if __name__ == "__main__":
    main()
