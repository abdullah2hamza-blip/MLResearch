"""Finite-pool acquisition service with paid observations and a hash-chained ledger.

The service never receives recipient-query outcomes or assessment data. Policies
receive only copied public metadata and purchased observations, not the service's
cell pools. This is an experimental API boundary, not an OS sandbox for hostile code.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from mlresearch.linear import FloatArray
from mlresearch.provenance import object_hash

CONTROL = "__control__"


@dataclass(frozen=True)
class CellPool:
    cell_ids: tuple[str, ...]
    values: FloatArray

    def validate(self) -> None:
        if self.values.ndim != 2 or len(self.values) != len(self.cell_ids):
            raise ValueError("Cell identifiers and the expression matrix must align")
        if not np.all(np.isfinite(self.values)):
            raise ValueError("Cell pools must contain finite expression values")
        if len(set(self.cell_ids)) != len(self.cell_ids):
            raise ValueError("A cell identifier appears repeatedly within a pool")

    @property
    def dimensions(self) -> int:
        return int(self.values.shape[1])

    def read(self, start: int, stop: int) -> FloatArray:
        return np.asarray(self.values[start:stop], dtype=np.float64).copy()


class Pool(Protocol):
    @property
    def cell_ids(self) -> tuple[str, ...]: ...

    @property
    def dimensions(self) -> int: ...

    def validate(self) -> None: ...

    def read(self, start: int, stop: int) -> FloatArray: ...


@dataclass(frozen=True)
class IndexedCellPool:
    """Read purchased rows from a shared read-only memmap without copying every pool."""

    cell_ids: tuple[str, ...]
    matrix: np.ndarray
    rows: tuple[int, ...]
    columns: tuple[int, ...]

    @property
    def dimensions(self) -> int:
        return len(self.columns)

    def validate(self) -> None:
        if len(self.rows) != len(self.cell_ids) or len(set(self.cell_ids)) != len(self.cell_ids):
            raise ValueError("Invalid indexed cell identifiers")
        if len(set(self.rows)) != len(self.rows) or len(set(self.columns)) != len(self.columns):
            raise ValueError("Repeated indexed rows or columns")
        if not self.columns or any(row < 0 or row >= len(self.matrix) for row in self.rows):
            raise ValueError("Indexed cell row out of bounds")
        if any(column < 0 or column >= self.matrix.shape[1] for column in self.columns):
            raise ValueError("Indexed gene column out of bounds")

    def read(self, start: int, stop: int) -> FloatArray:
        values = np.asarray(
            self.matrix[np.ix_(self.rows[start:stop], self.columns)], dtype=np.float64
        )
        if not np.all(np.isfinite(values)):
            raise ValueError("Purchased expression contains nonfinite values")
        return values


@dataclass(frozen=True)
class Action:
    intervention: str
    cells: int


@dataclass(frozen=True)
class Purchase:
    intervention: str
    cell_ids: tuple[str, ...]
    values: FloatArray
    cost: int
    spent: int


def validate_disjoint_banks(
    acquisition: dict[str, CellPool], assessment: dict[str, CellPool]
) -> None:
    """Scoring controls and experimental cells must not reuse acquisition observations."""
    purchased_ids = {identifier for pool in acquisition.values() for identifier in pool.cell_ids}
    assessment_ids = {identifier for pool in assessment.values() for identifier in pool.cell_ids}
    if purchased_ids & assessment_ids:
        raise ValueError("Acquisition and assessment banks share cell identifiers")


class AcquisitionService:
    """Only authorized calibration identities can be purchased; queries are forbidden."""

    def __init__(
        self,
        pools: dict[str, Pool],
        query_ids: tuple[str, ...],
        *,
        budget: int,
        setup_cost: int = 0,
        cell_cost: int = 1,
        control_cell_cost: int = 1,
        ledger_path: Path | None = None,
    ) -> None:
        costs = (budget, setup_cost, cell_cost, control_cell_cost)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in costs):
            raise ValueError("Budget and costs must be integer abstract measurement units")
        if budget < 0 or setup_cost < 0 or min(cell_cost, control_cell_cost) < 1:
            raise ValueError("Invalid budget or acquisition costs")
        if CONTROL not in pools:
            raise ValueError("An independent acquisition control pool is required")
        if set(query_ids) & set(pools):
            raise ValueError("Recipient query outcomes cannot enter acquisition pools")
        if len(set(query_ids)) != len(query_ids) or CONTROL in query_ids:
            raise ValueError("Query identities must be unique non-control interventions")
        seen: set[str] = set()
        dimensions: set[int] = set()
        for pool in pools.values():
            pool.validate()
            if seen.intersection(pool.cell_ids):
                raise ValueError("Cell identifiers are reused across acquisition pools")
            seen.update(pool.cell_ids)
            dimensions.add(pool.dimensions)
        if len(dimensions) != 1:
            raise ValueError("All pools must have the same measured gene axis")
        self._pools = dict(pools)
        self._offsets = dict.fromkeys(pools, 0)
        self._query_ids = frozenset(query_ids)
        self._budget, self._spent = budget, 0
        self._setup_cost, self._cell_cost = setup_cost, cell_cost
        self._control_cell_cost = control_cell_cost
        self._events: list[dict[str, Any]] = []
        self._ledger_path = ledger_path
        if ledger_path is not None:
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            # A new run cannot silently replace or append to another run's ledger.
            ledger_path.open("x", encoding="utf-8").close()

    def public_state(self) -> dict[str, Any]:
        return {
            "budget": self._budget,
            "spent": self._spent,
            "remaining_budget": self._budget - self._spent,
            "counts": dict(self._offsets),
            "remaining_cells": {
                key: len(pool.cell_ids) - self._offsets[key] for key, pool in self._pools.items()
            },
            "setup_cost": self._setup_cost,
            "cell_cost": self._cell_cost,
            "control_cell_cost": self._control_cell_cost,
        }

    def price(self, action: Action) -> int:
        if action.intervention in self._query_ids:
            raise PermissionError("Recipient query outcomes are sealed")
        if action.intervention not in self._pools:
            raise ValueError("Unknown acquisition identity")
        if isinstance(action.cells, bool) or not isinstance(action.cells, int) or action.cells < 1:
            raise ValueError("An action must acquire a positive integer number of cells")
        start = self._offsets[action.intervention]
        if start + action.cells > len(self._pools[action.intervention].cell_ids):
            raise ValueError("Insufficient unused cells in the finite acquisition pool")
        control = action.intervention == CONTROL
        setup = self._setup_cost if not control and start == 0 else 0
        return setup + action.cells * (self._control_cell_cost if control else self._cell_cost)

    def buy(self, action: Action) -> Purchase:
        cost = self.price(action)
        if self._spent + cost > self._budget:
            raise ValueError("Acquisition would exceed the frozen budget")
        pool = self._pools[action.intervention]
        start = self._offsets[action.intervention]
        stop = start + action.cells
        cell_ids = pool.cell_ids[start:stop]
        values = pool.read(start, stop)
        if not np.all(np.isfinite(values)):
            raise ValueError("Purchased expression contains nonfinite values")
        event = {
            "sequence": len(self._events),
            "action": asdict(action),
            "cell_ids": cell_ids,
            "cost": cost,
            "spent": self._spent + cost,
            "previous_sha256": self._events[-1]["sha256"] if self._events else None,
        }
        event["sha256"] = object_hash(event)
        if self._ledger_path is not None:
            with self._ledger_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        self._events.append(event)
        self._offsets[action.intervention] = stop
        self._spent += cost
        return Purchase(action.intervention, cell_ids, values, cost, self._spent)

    def ledger(self) -> list[dict[str, Any]]:
        # Return a deep copy, so reporting cannot mutate the authoritative ledger.
        return json.loads(json.dumps(self._events))


def verify_ledger(
    events: list[dict[str, Any]],
    *,
    budget: int,
    setup_cost: int = 0,
    cell_cost: int = 1,
    control_cell_cost: int = 1,
    query_ids: tuple[str, ...] = (),
) -> None:
    """Validate accounting, ordering, chain integrity, and non-reuse independently."""
    spent, previous = 0, None
    seen: set[str] = set()
    opened: set[str] = set()
    for sequence, event in enumerate(events):
        payload = {key: value for key, value in event.items() if key != "sha256"}
        if event.get("sha256") != object_hash(payload):
            raise ValueError("Ledger content hash is invalid")
        if event["sequence"] != sequence or event["previous_sha256"] != previous:
            raise ValueError("Ledger sequence/chain is invalid")
        identifiers = event["cell_ids"]
        if len(set(identifiers)) != len(identifiers) or seen.intersection(identifiers):
            raise ValueError("Ledger contains repeated cell purchases")
        if len(identifiers) != event["action"]["cells"] or event["cost"] <= 0:
            raise ValueError("Ledger count or cost is invalid")
        identity = event["action"]["intervention"]
        if identity in query_ids:
            raise ValueError("Ledger contains sealed query observations")
        cells = event["action"]["cells"]
        expected_cost = cells * (control_cell_cost if identity == CONTROL else cell_cost)
        if identity != CONTROL and identity not in opened:
            expected_cost += setup_cost
        if event["cost"] != expected_cost:
            raise ValueError("Ledger does not match the frozen cost schedule")
        spent += event["cost"]
        if event["spent"] != spent or spent > budget:
            raise ValueError("Ledger budget accounting is invalid")
        seen.update(identifiers)
        opened.add(identity)
        previous = event["sha256"]
