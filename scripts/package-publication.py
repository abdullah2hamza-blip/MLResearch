"""Create manuscript-source and code/evidence ZIPs from explicit publication paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def archive(path: Path, members: dict[str, Path | bytes], kind: str) -> dict:
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
        info = zipfile.ZipInfo("CONTENTS.sha256.json", date_time=(2026, 10, 23, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        output.writestr(info, json.dumps(inventory, indent=2, sort_keys=True) + "\n")
    with zipfile.ZipFile(path) as check:
        if check.testzip() is not None or set(check.namelist()) != set(hashes) | {
            "CONTENTS.sha256.json"
        }:
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
    args = parser.parse_args()
    root = Path.cwd().resolve()
    destination = args.output.resolve()
    if not destination.is_relative_to(root):
        raise ValueError("Choose an output folder inside this checkout")
    names = [
        "manuscript-source-v0.2.0.zip",
        "code-and-evidence-v0.2.0.zip",
        "release-manifest-v0.2.0.json",
    ]
    if any((destination / name).exists() for name in names) and not args.replace:
        raise ValueError("Preserve the release, or explicitly use --replace after verification")
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
    manuscript = {
        path.relative_to("paper").as_posix(): path
        for path in Path("paper").rglob("*")
        if path.is_file() and path.suffix not in {".aux", ".log", ".out", ".blg"}
    }
    manuscript["main.bbl"] = bibliography
    manuscript["build-paper.py"] = Path("scripts/build-paper.py")
    manuscript["CODE-LICENSE"] = Path("LICENSE")
    manuscript["README.txt"] = (
        b"Manuscript and supplement, Abdullah Hamza, October 23, 2026.\n"
        b"License: CC BY 4.0; see LICENSE.\n"
        b"The build helper is MIT licensed; see CODE-LICENSE.\n"
        b"Compile: python build-paper.py --source main.tex --output joint-acquisition-study.pdf\n"
        b"Requires Tectonic or pdfLaTeX/BibTeX. TeX source needs no expression data.\n"
        b"Asset hashes verified; underlying evidence is in the separate code archive.\n"
        b"For arXiv upload archive contents and select main.tex. See current arXiv instructions.\n"
    )
    code = {}
    for directory in ("src", "tests", "scripts", "configs", "docs", "paper", ".github"):
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
    destination.mkdir(parents=True, exist_ok=True)
    print(
        f"Packing {len(manuscript)} manuscript and {len(code)} code/evidence payloads", flush=True
    )
    records = [
        archive(destination / names[0], manuscript, "manuscript-source"),
        archive(destination / names[1], code, "code-and-evidence"),
    ]
    manifest = {
        "state": "built_and_payload_verified",
        "version": "0.2.0",
        "packager_sha256": digest(Path(__file__).read_bytes()),
        "pdf": {
            "file": pdf.as_posix(),
            "sha256": digest(pdf.read_bytes()),
            "bytes": pdf.stat().st_size,
        },
        "archives": records,
        "qualification": (
            "Local submission artifacts; no public deposit, submission or DOI claimed."
        ),
    }
    (destination / names[2]).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("Both archives and exact member payloads verified", flush=True)


if __name__ == "__main__":
    main()
