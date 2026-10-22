"""Read lifetime CPU times of this suite's exact Windows process, without controlling it."""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import UTC, datetime, timedelta
from pathlib import Path

from mlresearch.provenance import file_hash, read_json, utc_now, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("CPU observation exists")
    manifest = read_json(args.suite / "manifest.json")
    process_id = manifest["resources_start"]["process_id"]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4)]
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000 | 0x00100000, False, process_id)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    opened = utc_now()
    try:
        print(f"Observing CPU times for the suite process {process_id}", flush=True)
        while True:
            status = kernel.WaitForSingleObject(handle, 1000)
            if status == 0:
                break
            if status != 258:
                raise ctypes.WinError(ctypes.get_last_error())
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]):
            raise ctypes.WinError(ctypes.get_last_error())
        ticks = [(t.dwHighDateTime << 32) | t.dwLowDateTime for t in times]
        epoch = datetime(1601, 1, 1, tzinfo=UTC)
        write_json(
            args.output,
            {
                "analysis_source_sha256": file_hash(Path(__file__)),
                "process_id": process_id,
                "observer_opened_at": opened,
                "recorded_at": utc_now(),
                "created_at": (epoch + timedelta(microseconds=ticks[0] // 10)).isoformat(),
                "exited_at": (epoch + timedelta(microseconds=ticks[1] // 10)).isoformat(),
                "kernel_cpu_seconds": ticks[2] / 1e7,
                "user_cpu_seconds": ticks[3] / 1e7,
                "total_process_cpu_seconds": (ticks[2] + ticks[3]) / 1e7,
                "qualification": (
                    "Windows GetProcessTimes for the exact suite process over its lifetime; "
                    "sum of thread CPU times, distinct from elapsed time and exclusive "
                    "of child-process CPU."
                ),
            },
        )
        print("Suite process exited; lifetime CPU record retained", flush=True)
    finally:
        kernel.CloseHandle(handle)


if __name__ == "__main__":
    main()
