import json
import sqlite3
import sys
import time
from collections.abc import Iterator
from contextlib import closing
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

from satyaapply.core.paths import Paths
from satyaapply.tracker import runs
from satyaapply.tracker.body import Body
from satyaapply.tracker.routes import Incoming, dispatch

PRINT = (sys.executable, "-c", "print('scoring 1 of 2')")
SLEEP = (sys.executable, "-c", "import time; time.sleep(5)")
CHOICE = {"limit": 2, "search": True, "send": False}


@pytest.fixture
def paths(tmp_path: Path) -> Iterator[Paths]:
    yield Paths(tmp_path)
    runs.stop()
    runs.REGISTRY.current = None


def call(paths: Paths, path: str, body: Body | None = None) -> tuple[HTTPStatus, Any]:
    table = runs.GET if body is None else runs.POST
    with closing(sqlite3.connect(":memory:")) as db:
        response = dispatch(table, Incoming(db, paths, f"/api{path}", body or {}))
    assert response is not None
    return response.status, json.loads(response.body)


def wait_until_done() -> None:
    run = runs.REGISTRY.current
    assert run is not None
    run.process.wait(10)


def test_command_adds_limit_and_skips_search_when_off() -> None:
    flags = runs.command(runs.Choice(3, search=False))[len(runs.COMMAND_PREFIX) :]
    assert flags == ["--limit", "3", "--no-search"]
    assert "--no-search" not in runs.command(runs.Choice(3, search=True))
    assert runs.command(runs.Choice(3, search=True, send=True))[-1] == "--send"
    assert "--send" not in runs.command(runs.Choice(3, search=True))


def test_a_choice_needs_a_whole_number_and_two_true_or_false_answers() -> None:
    assert runs.parse_choice({"limit": 50, "search": True, "send": False}) == runs.Choice(20, True)
    assert runs.parse_choice({"limit": 0, "search": False, "send": True}) == runs.Choice(
        1, False, True
    )
    assert runs.parse_choice({"limit": "3", "search": True, "send": False}) is None
    assert runs.parse_choice({"limit": 3, "search": "on", "send": False}) is None
    assert runs.parse_choice({"limit": 3, "search": True}) is None
    assert runs.parse_choice({"limit": True, "search": True, "send": False}) is None


def test_start_writes_the_output_to_a_log(paths: Paths, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runs, "COMMAND_PREFIX", PRINT)
    status, started = call(paths, "/runs/start", CHOICE)
    assert (status, started["running"]) == (HTTPStatus.OK, True)
    assert started["startedAt"]
    wait_until_done()
    status, state = call(paths, "/runs")
    assert status == HTTPStatus.OK
    assert (state["running"], state["exitCode"]) == (False, 0)
    assert state["log"] == ["scoring 1 of 2"]
    assert state["limits"] == {"min": 1, "max": 20, "default": 5}
    name = state["logs"][0]["name"]
    assert name == runs.recent_logs(paths)[0].name
    status, log = call(paths, f"/runs/log/{name}")
    assert (status, log["lines"]) == (HTTPStatus.OK, ["scoring 1 of 2"])


def test_only_one_run_at_a_time_and_stop_ends_it(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runs, "COMMAND_PREFIX", SLEEP)
    assert call(paths, "/runs/start", CHOICE)[0] == HTTPStatus.OK
    assert call(paths, "/runs/start", CHOICE) == (
        HTTPStatus.BAD_REQUEST,
        {"error": runs.ALREADY_RUNNING},
    )
    assert call(paths, "/runs")[1]["running"]
    began = time.monotonic()
    status, stopped = call(paths, "/runs/stop", {})
    assert (status, stopped["running"]) == (HTTPStatus.OK, False)
    assert stopped["exitCode"] < 0
    assert time.monotonic() - began < 5
    assert runs.REGISTRY.active() is None


def test_bad_choices_are_refused(paths: Paths) -> None:
    assert call(paths, "/runs/start", {"limit": "many"})[0] == HTTPStatus.BAD_REQUEST
    assert call(paths, "/runs/start", {})[0] == HTTPStatus.BAD_REQUEST
    assert runs.REGISTRY.current is None


def test_log_names_cannot_escape_the_runs_folder(paths: Paths) -> None:
    (paths.root / "profile.json").write_text("{}", encoding="utf-8")
    for name in ("profile.json", "..", "20260101-000000-000000.log.bak"):
        assert call(paths, f"/runs/log/{name}")[0] == HTTPStatus.NOT_FOUND
    assert call(paths, "/runs/log/20260101-000000-000000.log")[0] == HTTPStatus.NOT_FOUND
    status, state = call(paths, "/runs")
    assert (status, state["running"], state["logs"]) == (HTTPStatus.OK, False, [])
