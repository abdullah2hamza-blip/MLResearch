"""Create fresh output/provenance paths without changing frozen scientific settings."""

from __future__ import annotations

import argparse
from dataclasses import asdict, fields, replace
from pathlib import Path

from mlresearch.episodes import EpisodeConfig, load_public_episode
from mlresearch.experiment import RunConfig
from mlresearch.external import ExternalConfig
from mlresearch.identifiers import verify_identifier_record
from mlresearch.prepare import PrepareConfig
from mlresearch.provenance import file_hash, object_hash, read_json, utc_now, write_json


def without_paths(value: dict, names: tuple[str, ...]) -> dict:
    return {key: item for key, item in value.items() if key not in names}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identifiers", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument(
        "--template", type=Path, default=Path("configs/external-evaluation-v1.json")
    )
    parser.add_argument("--forward", type=Path, default=Path("data/episodes/k562-to-rpe1-v1"))
    parser.add_argument("--reverse", type=Path, default=Path("data/episodes/rpe1-to-k562-v1"))
    args = parser.parse_args()
    if args.directory.exists():
        raise ValueError("Reproduction directory exists; preserve it and choose a fresh path")
    template = ExternalConfig.load(args.template)
    published_declaration = read_json(Path("docs/evidence/external-evaluation-declaration-v1.json"))
    if object_hash(asdict(template)) != published_declaration["configuration_sha256"]:
        raise ValueError("Reproduction template differs from the published frozen declaration")
    published = read_json(Path("docs/evidence/external-canonical-identifiers-v1.json"))
    raw = {
        "K562": published["datasets"]["k562"]["raw_sha256"],
        "RPE1": published["datasets"]["rpe1"]["raw_sha256"],
    }
    prepare = {
        "K562": asdict(PrepareConfig.load(Path("configs/prepare-k562.json"))),
        "RPE1": asdict(PrepareConfig.load(Path("configs/prepare-rpe1.json"))),
    }
    episode_map = {}
    episode_hashes = {}
    io_differences = {}
    for name, path in (("k562-to-rpe1", args.forward), ("rpe1-to-k562", args.reverse)):
        expected = asdict(EpisodeConfig.load(Path(f"configs/episode-{name}.json")))
        manifest = read_json(path / "manifest.json")
        public = load_public_episode(path)
        verify_identifier_record(
            public, manifest, args.identifiers, episode_sha256=file_hash(path / "manifest.json")
        )
        ignored = ("source_prepared", "target_prepared", "output_directory")
        if without_paths(expected, ignored) != without_paths(manifest["configuration"], ignored):
            raise ValueError("Rebuilt episode changed frozen scientific settings")
        for arm in ("source", "target"):
            context = expected[arm + "_context"]
            prepared = manifest["prepared_inputs"][arm]
            ignored_preparation = (
                "input_path",
                "output_directory",
                "row_block_size",
                "column_block_size",
            )
            io_differences[context] = {
                key: {
                    "prepared": prepared["configuration"][key],
                    "reproduction_config": prepare[context][key],
                }
                for key in ("row_block_size", "column_block_size")
                if prepared["configuration"][key] != prepare[context][key]
            }
            if prepared["input_sha256"] != raw[context] or without_paths(
                prepared["configuration"], ignored_preparation
            ) != without_paths(prepare[context], ignored_preparation):
                raise ValueError("Rebuilt preparation changed raw input or frozen transformation")
        mapping = published["datasets"]["k562"]["eligible_target_to_canonical"]
        if {mapping[key] for key in public.query_ids} != set(published["canonical_query_ids"]) or {
            mapping[key] for key in public.candidate_ids
        } != set(published["canonical_candidate_ids"]):
            raise ValueError("Rebuilt canonical split differs from the published split")
        episode_map[expected["output_directory"]] = str(path.resolve())
        episode_hashes[str(path.resolve())] = file_hash(path / "manifest.json")
    declaration = args.directory / "declaration.json"
    original_identifier = "docs/evidence/external-canonical-identifiers-v1.json"
    original_declaration = "docs/evidence/external-evaluation-declaration-v1.json"
    evidence = [
        str(args.identifiers.resolve())
        if p == original_identifier
        else str(declaration.resolve())
        if p == original_declaration
        else p
        for p in template.evidence_files
    ]
    evidence.append(str(args.template.resolve()))
    runs = []
    ignored_run_fields = {"episode_directory", "output_directory", "identifier_record", "label"}
    for number, run in enumerate(template.runs):
        rebuilt = replace(
            run,
            episode_directory=episode_map[run.episode_directory],
            output_directory=str((args.directory / "experiments" / f"run-{number}").resolve()),
            identifier_record=str(args.identifiers.resolve()),
            label="Published-specification reproduction: " + run.label,
        )
        for entry in fields(RunConfig):
            if entry.name not in ignored_run_fields and getattr(rebuilt, entry.name) != getattr(
                run, entry.name
            ):
                raise ValueError("A frozen scientific run setting changed")
        runs.append(rebuilt)
    config = ExternalConfig(str((args.directory / "suite").resolve()), runs, evidence)
    args.directory.mkdir(parents=True)
    write_json(args.directory / "configuration.json", asdict(config))
    write_json(
        declaration,
        {
            "declared_at": utc_now(),
            "state": "reproduction of the published specification",
            "configuration_sha256": object_hash(asdict(config)),
            "source_specification": str(args.template),
            "source_specification_sha256": file_hash(args.template),
            "episode_manifest_sha256": episode_hashes,
            "identifier_audit_sha256": file_hash(args.identifiers),
            "scientific_settings_changed": False,
            "preparation_io_differences": io_differences,
            "qualification": (
                "Reproduces released datasets; no new untouched external dataset "
                "or biological replication is claimed."
            ),
            "analysis_source_sha256": file_hash(Path(__file__)),
            "evidence_sha256": {
                name: file_hash(Path(name))
                for name in evidence
                if Path(name).resolve() != declaration.resolve()
            },
        },
    )
    print(args.directory / "configuration.json")


if __name__ == "__main__":
    main()
