import json

import numpy as np
import pytest

from mlresearch.acquisition import (
    CONTROL,
    AcquisitionService,
    Action,
    CellPool,
    validate_disjoint_banks,
    verify_ledger,
)


def pool(prefix, count=8):
    return CellPool(
        tuple(f"{prefix}-{index}" for index in range(count)),
        np.arange(count * 3, dtype=float).reshape(count, 3),
    )


def service(**kwargs):
    return AcquisitionService(
        {CONTROL: pool("control"), "a": pool("a")}, ("query",), budget=20, setup_cost=3, **kwargs
    )


def test_queries_cannot_be_purchased_or_injected_into_service():
    lab = service()
    with pytest.raises(PermissionError, match="sealed"):
        lab.buy(Action("query", 1))
    with pytest.raises(ValueError, match="query outcomes"):
        AcquisitionService({CONTROL: pool("c"), "query": pool("q")}, ("query",), budget=10)
    assert lab.public_state()["spent"] == 0


def test_budget_counts_control_pilots_setup_and_repeat_depth(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    lab = service(ledger_path=ledger_path)
    assert lab.buy(Action(CONTROL, 2)).cost == 2
    assert lab.buy(Action("a", 2)).cost == 5
    assert lab.buy(Action("a", 3)).cost == 3
    assert lab.public_state()["spent"] == 10
    verify_ledger(lab.ledger(), budget=20, setup_cost=3)
    on_disk = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    assert on_disk == lab.ledger()
    with pytest.raises(FileExistsError):
        service(ledger_path=ledger_path)


def test_purchases_never_repeat_cells_and_cannot_mutate_pool():
    lab = service()
    first, second = lab.buy(Action("a", 3)), lab.buy(Action("a", 4))
    assert not set(first.cell_ids) & set(second.cell_ids)
    first.values[:] = -1000
    with pytest.raises(ValueError, match="unused"):
        lab.buy(Action("a", 2))
    state = lab.public_state()
    state["counts"]["a"] = -1000
    assert lab.public_state()["counts"]["a"] == 7


def test_failed_actions_do_not_spend_or_write_ledger():
    lab = service()
    with pytest.raises(ValueError, match="integer"):
        lab.buy(Action("a", -1))
    with pytest.raises(ValueError, match="integer"):
        lab.buy(Action("a", True))
    lab.buy(Action("a", 8))
    lab.buy(Action(CONTROL, 8))
    before = lab.ledger()
    with pytest.raises(ValueError, match="exceed"):
        # A separate service gives enough available cells but too little money.
        AcquisitionService(
            {CONTROL: pool("c"), "a": pool("a")}, ("q",), budget=2, setup_cost=3
        ).buy(Action("a", 1))
    assert lab.ledger() == before


def test_duplicate_cells_and_reused_assessment_controls_are_rejected():
    with pytest.raises(ValueError, match="reused"):
        AcquisitionService({CONTROL: pool("c"), "a": pool("c")}, ("q",), budget=10)
    with pytest.raises(ValueError, match="assessment"):
        validate_disjoint_banks({CONTROL: pool("c")}, {CONTROL: pool("c")})
    validate_disjoint_banks({CONTROL: pool("c")}, {CONTROL: pool("independent-c")})


def test_hash_chain_detects_edited_costs_and_is_deterministic():
    labs = [service(), service()]
    for lab in labs:
        lab.buy(Action(CONTROL, 2))
        lab.buy(Action("a", 3))
    assert labs[0].ledger() == labs[1].ledger()
    events = labs[0].ledger()
    events[0]["cost"] = 0
    with pytest.raises(ValueError, match="hash"):
        verify_ledger(events, budget=20)


def test_independent_cost_recalculation_rejects_rehashed_undercharging():
    from mlresearch.provenance import object_hash

    lab = service()
    lab.buy(Action("a", 3))
    event = lab.ledger()[0]
    event["spent"] = event["cost"] = 3
    event["sha256"] = object_hash({key: value for key, value in event.items() if key != "sha256"})
    with pytest.raises(ValueError, match="cost schedule"):
        verify_ledger([event], budget=20, setup_cost=3)
