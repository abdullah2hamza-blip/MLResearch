"""Bind four rebuilt episodes to a fresh reproduction of the frozen eight-run matrix."""

from __future__ import annotations

import argparse
import tomllib
import zipfile
from dataclasses import asdict, fields, replace
from pathlib import Path

from mlresearch.episodes import EpisodeConfig, load_public_episode
from mlresearch.experiment import RunConfig
from mlresearch.external import ExternalConfig
from mlresearch.identifiers import verify_identifier_record
from mlresearch.prepare import PrepareConfig
from mlresearch.provenance import (
    environment_record,
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json,
)

PUBLICATION_DECLARATION = Path("docs/evidence/publication-robustness-declaration-v1.json")
RETAINED_EPISODES = Path("docs/results/publication-robustness-v1/frozen/episodes")


def omit(value: dict, names: tuple[str, ...]) -> dict:
    return {key: item for key, item in value.items() if key not in names}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes-root", type=Path, default=Path("data/episodes"))
    parser.add_argument("--identifiers-23", type=Path, required=True)
    parser.add_argument("--identifiers-24", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument(
        "--template", type=Path, default=Path("configs/publication-robustness-v1.json")
    )
    args = parser.parse_args()
    if args.directory.exists():
        raise ValueError("Reproduction directory exists; preserve it and choose a fresh path")
    published = read_json(PUBLICATION_DECLARATION)
    template = ExternalConfig.load(args.template)
    if (
        object_hash(asdict(template)) != published["configuration_sha256"]
        or file_hash(args.template) != published["configuration_file_sha256"]
    ):
        raise ValueError("Reproduction template differs from the published frozen declaration")
    environment = environment_record()
    if (
        environment["source_tree_sha256"] != published["environment"]["source_tree_sha256"]
        or environment["packages"]["mlresearch"] != "0.2.0"
    ):
        raise ValueError("Use the fixed published version0.2.0 package source snapshot")
    snapshot = PUBLICATION_DECLARATION.with_suffix(".zip")
    if file_hash(snapshot) != published["code_snapshot"]["sha256"]:
        raise ValueError("Published source/dependency snapshot changed")
    with zipfile.ZipFile(snapshot) as archive:
        if Path("uv.lock").read_bytes() != archive.read("uv.lock"):
            raise ValueError("Use the published locked dependency specification")
        frozen_project = tomllib.loads(archive.read("pyproject.toml").decode("utf-8"))
        current_project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        packaging_changes = {}
        if current_project != frozen_project:
            files = current_project["project"].pop("license-files", None)
            if files != ["LICENSE"] or current_project != frozen_project:
                raise ValueError("Only the declared license-file packaging addition is allowed")
            packaging_changes["project.license-files"] = files
            packaging_changes["license_sha256"] = file_hash(Path("LICENSE"))
    identifier_paths = {20261023: args.identifiers_23, 20261024: args.identifiers_24}
    original_identifier_paths = {
        seed: Path(f"docs/evidence/publication-canonical-seed{seed}-v1.json")
        for seed in identifier_paths
    }
    original_identifiers, rebuilt_identifiers = {}, {}
    for seed, path in original_identifier_paths.items():
        if file_hash(path) != published["evidence_sha256"][path.as_posix()]:
            raise ValueError("Published canonical reference changed")
        original_identifiers[seed] = read_json(path)
        rebuilt_identifiers[seed] = read_json(identifier_paths[seed])
        reference, rebuilt = original_identifiers[seed], rebuilt_identifiers[seed]
        if rebuilt["state"] != "complete" or not rebuilt["metadata_only"]:
            raise ValueError("Supply complete metadata-only rebuilt canonical audits")
        for key in ("canonical_query_ids", "canonical_candidate_ids"):
            if set(reference[key]) != set(rebuilt[key]):
                raise ValueError("Rebuilt canonical target split differs from published split")
        for dataset in ("k562", "rpe1"):
            for key in (
                "raw_sha256",
                "eligible_target_to_canonical",
                "aligned_expression_gene_to_canonical",
                "eligible_target_guides",
            ):
                if rebuilt["datasets"][dataset][key] != reference["datasets"][dataset][key]:
                    raise ValueError("Rebuilt release identifiers or guide ownership changed")
    prepare_configs = {
        "K562": asdict(PrepareConfig.load(Path("configs/prepare-k562.json"))),
        "RPE1": asdict(PrepareConfig.load(Path("configs/prepare-rpe1.json"))),
    }
    archived_hashes = {
        Path(name.replace("\\", "/")).name: digest
        for name, digest in published["episode_manifests_sha256"].items()
    }
    episode_map, episodes, references, io_differences = {}, {}, {}, {}
    episode_ignored = ("source_prepared", "target_prepared", "output_directory")
    prepare_ignored = ("input_path", "output_directory", "row_block_size", "column_block_size")
    for seed in identifier_paths:
        for direction in ("k562-to-rpe1", "rpe1-to-k562"):
            name = f"publication-{direction}-seed{seed}-v1"
            reference_path = RETAINED_EPISODES / name / "manifest.json"
            if file_hash(reference_path) != archived_hashes[name]:
                raise ValueError("Published episode reference no longer matches declaration")
            archived = read_json(reference_path)
            expected = archived["configuration"]
            config_path = Path(f"configs/episode-{name}.json")
            configured = asdict(EpisodeConfig.load(config_path))
            if omit(configured, episode_ignored) != omit(expected, episode_ignored):
                raise ValueError("Published episode configuration changed scientifically")
            path = args.episodes_root / name
            manifest = read_json(path / "manifest.json")
            public = load_public_episode(path)
            if omit(manifest["configuration"], episode_ignored) != omit(expected, episode_ignored):
                raise ValueError("Rebuilt episode changed frozen scientific settings")
            verify_identifier_record(
                public,
                manifest,
                identifier_paths[seed],
                episode_sha256=file_hash(path / "manifest.json"),
            )
            mapping = original_identifiers[seed]["datasets"]["k562"]["eligible_target_to_canonical"]
            if {mapping[key] for key in public.query_ids} != set(
                original_identifiers[seed]["canonical_query_ids"]
            ) or {mapping[key] for key in public.candidate_ids} != set(
                original_identifiers[seed]["canonical_candidate_ids"]
            ):
                raise ValueError("Actual rebuilt canonical split differs from published split")
            for arm in ("source", "target"):
                context = expected[arm + "_context"]
                dataset = "k562" if context == "K562" else "rpe1"
                baseline = archived["prepared_inputs"][arm]
                prepared = manifest["prepared_inputs"][arm]
                if (
                    prepared["input_sha256"]
                    != original_identifiers[seed]["datasets"][dataset]["raw_sha256"]
                    or omit(prepared["configuration"], prepare_ignored)
                    != omit(baseline["configuration"], prepare_ignored)
                    or omit(prepare_configs[context], prepare_ignored)
                    != omit(baseline["configuration"], prepare_ignored)
                    or prepared["transformation"] != baseline["transformation"]
                    or prepared["shape"] != baseline["shape"]
                ):
                    raise ValueError(
                        "Rebuilt preparation changed raw input, cohort or transformation"
                    )
                io_differences[f"{name}:{arm}"] = {
                    field: {
                        "published": baseline["configuration"][field],
                        "rebuilt": prepared["configuration"][field],
                        "reproduction_config": prepare_configs[context][field],
                    }
                    for field in ("row_block_size", "column_block_size")
                    if len(
                        {
                            baseline["configuration"][field],
                            prepared["configuration"][field],
                            prepare_configs[context][field],
                        }
                    )
                    > 1
                }
            episode_map[expected["output_directory"]] = str(path.resolve())
            episodes[str(path.resolve())] = file_hash(path / "manifest.json")
            references[reference_path.as_posix()] = file_hash(reference_path)
    if len(episode_map) != 4:
        raise ValueError("Four distinct split/direction episode bindings are required")
    declaration = args.directory / "declaration.json"
    replacements = {
        path.as_posix(): str(identifier_paths[seed].resolve())
        for seed, path in original_identifier_paths.items()
    }
    replacements[PUBLICATION_DECLARATION.as_posix()] = str(declaration.resolve())
    evidence = [replacements.get(name, name) for name in template.evidence_files]
    evidence.extend(
        str(p.resolve())
        for p in (args.template, PUBLICATION_DECLARATION, *original_identifier_paths.values())
    )
    evidence.extend(str(Path(name).resolve()) for name in ("pyproject.toml", "uv.lock", "LICENSE"))
    evidence.extend(str(Path(path).resolve()) for path in references)
    evidence = list(
        {str(Path(path).resolve()): str(Path(path).resolve()) for path in evidence}.values()
    )
    runs = []
    ignored_run_fields = {"episode_directory", "output_directory", "identifier_record", "label"}
    for number, run in enumerate(template.runs):
        original_episode = next(
            path for path in episode_map if Path(path).name == Path(run.episode_directory).name
        )
        seed = read_json(Path(episode_map[original_episode]) / "manifest.json")["configuration"][
            "seed"
        ]
        rebuilt = replace(
            run,
            episode_directory=episode_map[original_episode],
            output_directory=str((args.directory / "experiments" / f"run-{number}").resolve()),
            identifier_record=str(identifier_paths[seed].resolve()),
            label="Published robustness reproduction: " + run.label,
        )
        for field in fields(RunConfig):
            if field.name not in ignored_run_fields and getattr(rebuilt, field.name) != getattr(
                run, field.name
            ):
                raise ValueError("A frozen scientific run setting changed")
        runs.append(rebuilt)
    config = ExternalConfig(str((args.directory / "suite").resolve()), runs, evidence)
    args.directory.mkdir(parents=True)
    write_json(args.directory / "configuration.json", asdict(config))
    write_json(
        declaration,
        {
            "state": "fresh_reproduction_binding_no_acquisition_or_scoring",
            "declared_at": utc_now(),
            "configuration_sha256": object_hash(asdict(config)),
            "published_configuration_sha256": published["configuration_sha256"],
            "source_specification": str(args.template),
            "source_specification_sha256": file_hash(args.template),
            "published_declaration_sha256": file_hash(PUBLICATION_DECLARATION),
            "episode_manifest_sha256": episodes,
            "published_episode_reference_sha256": references,
            "identifier_audit_sha256": {
                str(seed): file_hash(path) for seed, path in identifier_paths.items()
            },
            "preparation_io_differences": io_differences,
            "environment": environment,
            "scientific_settings_changed": False,
            "packaging_only_changes_from_frozen_project": packaging_changes,
            "run_count": len(runs),
            "prediction_checkpoints": 360,
            "analysis_source_sha256": file_hash(Path(__file__)),
            "evidence_sha256": {
                name: file_hash(Path(name))
                for name in evidence
                if Path(name).resolve() != declaration.resolve()
            },
            "qualification": (
                "Same released data, fixed splits/ranks/budgets/models/costs; no new untouched "
                "confirmation or biological replication. Fresh canonical audits bind rebuilt "
                "episode provenance. IO batching alone may differ; no predictions are acquired."
            ),
        },
    )
    print(args.directory / "configuration.json")


if __name__ == "__main__":
    main()
