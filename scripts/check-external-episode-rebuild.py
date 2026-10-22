"""Rebuild real external episodes from verified preparations and compare every public array."""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

from mlresearch.episodes import EpisodeConfig, build_episode
from mlresearch.provenance import file_hash, read_json, utc_now, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    if read_json(args.suite / "manifest.json")["state"] != "complete":
        raise ValueError("Complete the original suite before rebuilding source summaries")
    if args.directory.exists() or args.evidence.exists():
        raise ValueError("Rebuild/evidence output exists")
    records = []
    for name in ("k562-to-rpe1", "rpe1-to-k562"):
        config = EpisodeConfig.load(Path(f"configs/episode-{name}.json"))
        original = Path(config.output_directory)
        rebuilt = args.directory / name
        new_config = replace(config, output_directory=str(rebuilt.resolve()))
        write_json(args.directory / f"{name}-configuration.json", asdict(new_config))
        print("Rebuilding", name, flush=True)
        manifest = build_episode(new_config)
        if read_json(original / "public.json") != read_json(rebuilt / "public.json"):
            raise ValueError("Public identities, split or gene axis changed")
        a, b = read_json(original / "private-banks.json"), read_json(rebuilt / "private-banks.json")
        paths = {"target_prepared", "target_path_rule"}
        if {k: v for k, v in a.items() if k not in paths} != {
            k: v for k, v in b.items() if k not in paths
        }:
            raise ValueError("Paid/scorer/source cell maps or source counts changed")
        arrays = {}
        with (
            np.load(original / "source.npz", allow_pickle=False) as left,
            np.load(rebuilt / "source.npz", allow_pickle=False) as right,
        ):
            if set(left.files) != set(right.files):
                raise ValueError("Public source array inventory changed")
            for key in left.files:
                x, y = left[key], right[key]
                if x.shape != y.shape or x.dtype != y.dtype or x.tobytes() != y.tobytes():
                    raise ValueError("Public source numeric array changed: " + key)
                arrays[key] = {
                    "shape": list(x.shape),
                    "dtype": str(x.dtype),
                    "numeric_bytes_sha256": hashlib.sha256(x.tobytes()).hexdigest(),
                }
        records.append(
            {
                "direction": name,
                "configuration": asdict(new_config),
                "original_manifest_sha256": file_hash(original / "manifest.json"),
                "rebuilt_manifest_sha256": file_hash(rebuilt / "manifest.json"),
                "inventory": manifest["inventory"],
                "all_public_arrays_byte_equal": arrays,
                "public_metadata_and_all_private_cell_maps_equal": True,
            }
        )
    write_json(
        args.evidence,
        {
            "state": "passed",
            "recorded_at": utc_now(),
            "analysis_source_sha256": file_hash(Path(__file__)),
            "suite_manifest_sha256": file_hash(args.suite / "manifest.json"),
            "directions": records,
            "qualification": (
                "Fresh real episode outputs from the existing checksum-verified preparations. "
                "Every source numeric array, split/identity axis and bank map compared; "
                "not a second raw-matrix preparation or independent external replication."
            ),
        },
    )
    print("Both real episodes rebuilt exactly", flush=True)


if __name__ == "__main__":
    main()
