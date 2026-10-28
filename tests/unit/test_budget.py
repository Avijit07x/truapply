import shutil
import sqlite3
import subprocess
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import NoReturn

import pytest

from truapply.ai.budget import Budget, charge, metered
from truapply.ai.client import Request, ask
from truapply.ai.replies import Pong
from truapply.core.errors import DailyBudgetError, UsageLimitError
from truapply.store import usage
from truapply.store.db import connect

TODAY = date(2026, 10, 26)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(tmp_path / "test.db")) as connection:
        yield connection


def test_calls_stop_at_exactly_the_budget() -> None:
    budget = Budget(3)
    with metered(budget):
        for _ in range(3):
            charge()
        with pytest.raises(DailyBudgetError):
            charge()
    assert (budget.used, budget.left) == (3, 0)


def test_calls_outside_a_run_are_not_counted() -> None:
    charge()
    budget = Budget(1)
    with metered(budget):
        charge()
    charge()
    assert budget.used == 1


def test_parallel_calls_never_overspend() -> None:
    budget = Budget(50)

    def spend_twenty(_: int) -> int:
        spent = 0
        for _ in range(20):
            try:
                budget.spend()
            except DailyBudgetError:
                continue
            spent += 1
        return spent

    with metered(budget), ThreadPoolExecutor(8) as pool:
        total = sum(pool.map(spend_twenty, range(8)))
    assert total == budget.used == 50


def test_a_spent_budget_stops_the_claude_call_before_it_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def never(*_args: object, **_kwargs: object) -> NoReturn:
        raise AssertionError("Claude was called after the budget ran out")

    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/local/bin/claude")
    monkeypatch.setattr(subprocess, "run", never)
    with metered(Budget(0)), pytest.raises(UsageLimitError, match="budget"):
        ask(Pong, Request("Reply with ok = true.", "system"))


def test_todays_calls_add_up_across_runs(db: sqlite3.Connection) -> None:
    usage.add_ai_calls(db, TODAY, 5)
    usage.add_ai_calls(db, TODAY, 3)
    usage.add_ai_calls(db, TODAY, 0)
    assert usage.ai_calls_on(db, TODAY) == 8
    assert usage.ai_calls_on(db, date(2026, 10, 27)) == 0
