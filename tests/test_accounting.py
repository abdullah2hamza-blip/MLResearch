import json

import pytest

from mlresearch.accounting import account_development
from mlresearch.acquisition import CONTROL
from mlresearch.episodes import EpisodeConfig, build_episode, load_public_episode
from mlresearch.experiment import RunConfig, run_experiment
from mlresearch.policies import PolicyConfig
from mlresearch.provenance import read_json
from mlresearch.simulation import SimulationConfig, make_simulation


def test_unique_development_union_matches_manual_cells_and_rejects_bad_ledger(tmp_path):
    data, episode, run = tmp_path / "data", tmp_path / "episode", tmp_path / "run"
    make_simulation(
        data,
        SimulationConfig(
            interventions=8,
            genes=8,
            latent_rank=2,
            source_cells=4,
            acquisition_cells=4,
            assessment_cells=4,
            controls_each_bank=4,
        ),
    )
    build_episode(
        EpisodeConfig(
            str(data / "source"),
            str(data / "target"),
            "source",
            "target",
            str(episode),
            min_source_cells=4,
            acquisition_cells=4,
            assessment_cells=4,
            acquisition_controls=4,
            assessment_controls=4,
        )
    )
    run_experiment(
        RunConfig(
            str(episode),
            str(run),
            budgets=[24, 32],
            seeds=[0],
            policies=["worst_query", "bias_aware"],
            policy=PolicyConfig(
                rank=2, block_cells=4, pilot_controls=4, pilot_interventions=3, setup_cost=2
            ),
        )
    )
    first = account_development([run])
    repeated = account_development([run, run])
    assert first == repeated
    public = load_public_episode(episode)
    banks = read_json(episode / "private-banks.json")
    controls = set(banks["assessment_cell_ids"][CONTROL])
    perturbed = set()
    opened = set(public.query_ids)
    for identity in public.query_ids:
        perturbed.update(banks["assessment_cell_ids"][identity])
    for ledger in run.glob("seed-*/*/ledger.jsonl"):
        for line in ledger.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event["action"]["intervention"] == CONTROL:
                controls.update(event["cell_ids"])
            else:
                perturbed.update(event["cell_ids"])
                opened.add(event["action"]["intervention"])
    assert first["unique_resource_cost_units"] == len(controls) + len(perturbed) + 2 * len(opened)
    ledger = run / "seed-0/worst_query/ledger.jsonl"
    original = ledger.read_bytes()
    for truncated in [b"", b"".join(original.splitlines(keepends=True)[:-1])]:
        ledger.write_bytes(truncated)
        with pytest.raises(ValueError, match="truncated|checkpoint"):
            account_development([run])
    ledger.write_bytes(original)
    lines = ledger.read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[0])
    event["cost"] += 1
    lines[0] = json.dumps(event)
    ledger.write_text("\n".join(lines), encoding="utf-8")
    with pytest.raises(ValueError, match="content hash"):
        account_development([run])
