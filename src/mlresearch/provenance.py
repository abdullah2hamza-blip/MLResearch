"""Small, explicit provenance records and atomic JSON output."""

from __future__ import annotations

import ctypes
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def file_hash(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def object_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    """Replace one JSON file atomically; failed writes leave no partial final file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent, suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def environment_record() -> dict[str, Any]:
    packages: dict[str, str] = {}
    for name in ("mlresearch", "numpy", "scipy", "h5py", "matplotlib", "pytest"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    git: dict[str, Any] = {}
    for key, arguments in (
        ("revision", ["rev-parse", "HEAD"]),
        ("status", ["status", "--porcelain", "--untracked-files=no"]),
    ):
        try:
            result = subprocess.run(
                ["git", *arguments], capture_output=True, text=True, check=True, timeout=10
            )
            git[key] = result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            git[key] = None
    # The working revision is not a code-content hash; experiment manifests also hash sources.
    sources = sorted(
        path for path in Path(__file__).parent.iterdir() if path.suffix in (".py", ".json")
    )
    code = {path.name: file_hash(path) for path in sources}
    return {
        "recorded_at": utc_now(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
        "git": git,
        "source_hashes": code,
        "source_tree_sha256": object_hash(code),
    }


def snapshot_sources(output: Path, expected: dict[str, str]) -> dict[str, Any]:
    """Retain exact small source contents, including uncommitted experimental code."""
    package = Path(__file__).parent
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, checksum in sorted(expected.items()):
            source = package / name
            if Path(name).name != name or file_hash(source) != checksum:
                raise ValueError("Package source changed before provenance snapshot")
            archive.write(source, "mlresearch/" + name)
        project = Path(__file__).parents[2]
        for name in ("pyproject.toml", "uv.lock"):
            if (project / name).is_file():
                archive.write(project / name, name)
    return {
        "path": output.name,
        "sha256": file_hash(output),
        "purpose": "Exact package sources plus available project dependency specification.",
    }


def resource_record(path: Path) -> dict[str, Any]:
    disk = shutil.disk_usage(path.resolve())
    result: dict[str, Any] = {
        "recorded_at": utc_now(),
        "logical_cpus": os.cpu_count(),
        "disk_total_bytes": disk.total,
        "disk_free_bytes": disk.free,
    }
    if os.name == "nt":

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("load", ctypes.c_ulong),
                ("total", ctypes.c_ulonglong),
                ("available", ctypes.c_ulonglong),
                ("page_total", ctypes.c_ulonglong),
                ("page_available", ctypes.c_ulonglong),
                ("virtual_total", ctypes.c_ulonglong),
                ("virtual_available", ctypes.c_ulonglong),
                ("extended", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        windows = getattr(ctypes, "windll", None)
        if windows is not None and windows.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            result.update(ram_bytes=status.total, available_ram_bytes=status.available)
    else:
        try:
            sysconf = getattr(os, "sysconf", None)
            if sysconf is None:
                raise AttributeError("sysconf is unavailable")
            result["ram_bytes"] = sysconf("SC_PAGE_SIZE") * sysconf("SC_PHYS_PAGES")
            result["available_ram_bytes"] = sysconf("SC_PAGE_SIZE") * sysconf("SC_AVPHYS_PAGES")
        except (AttributeError, OSError, ValueError):
            result["ram_bytes"] = None
    return result
