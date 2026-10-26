import sqlite3
import sys
import time
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path

import pytest

from satyaapply.core.paths import Paths
from satyaapply.tracker import runs
from satyaapply.tracker.responses import Response
from satyaapply.tracker.routes import Form, Incoming, dispatch

PRINT = (sys.executable, "-c", "print('scoring 1 of 2')")
SLEEP = (sys.executable, "-c", "import time; time.sleep(5)")


@pytest.fixture
def paths(tmp_path: Path) -> Iterator[Paths]:
    yield Paths(tmp_path)
    runs.stop()
    runs.REGISTRY.current = None


def call(paths: Paths, path: str, form: Form | None = None) -> Response:
    table = runs.GET if form is None else runs.POST
    with sqlite3.connect(":memory:") as db:
        response = dispatch(table, Incoming(db, paths, path, form or {}))
    assert response is not None
    return response


def wait_until_done() -> None:
    run = runs.REGISTRY.current
    assert run is not None
    run.process.wait(10)


def test_command_adds_limit_and_skips_search_when_off() -> None:
    flags = runs.command(runs.Choice(3, search=False))[len(runs.COMMAND_PREFIX) :]
    assert flags == ["--limit", "3", "--no-search"]
    assert "--no-search" not in runs.command(runs.Choice(3, search=True))


def test_start_writes_the_output_to_a_log(paths: Paths, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runs, "COMMAND_PREFIX", PRINT)
    started = call(paths, "/runs/start", {"limit": "50", "search": "on"})
    assert (started.status, started.location) == (HTTPStatus.SEE_OTHER, "/runs")
    wait_until_done()
    body = call(paths, "/runs").body
    assert b"scoring 1 of 2" in body
    assert b"exit code 0" in body
    log = runs.recent_logs(paths)[0]
    assert b"scoring 1 of 2" in call(paths, f"/runs/log/{log.name}").body
    assert b"Last run finished" in runs.home_panel(sqlite3.connect(":memory:"), paths).encode()


def test_only_one_run_at_a_time_and_stop_ends_it(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runs, "COMMAND_PREFIX", SLEEP)
    assert call(paths, "/runs/start", {"limit": "2"}).status == HTTPStatus.SEE_OTHER
    second = call(paths, "/runs/start", {"limit": "2"})
    assert second.status == HTTPStatus.BAD_REQUEST
    assert runs.ALREADY_RUNNING.encode() in second.body
    running = call(paths, "/runs").body
    assert b"Running since" in running
    assert b'http-equiv="refresh"' in running
    began = time.monotonic()
    assert call(paths, "/runs/stop", {}).status == HTTPStatus.SEE_OTHER
    assert time.monotonic() - began < 5
    assert runs.REGISTRY.active() is None


def test_bad_limit_is_refused(paths: Paths) -> None:
    assert call(paths, "/runs/start", {"limit": "many"}).status == HTTPStatus.BAD_REQUEST
    assert call(paths, "/runs/start", {}).status == HTTPStatus.BAD_REQUEST
    assert runs.REGISTRY.current is None


def test_log_names_cannot_escape_the_runs_folder(paths: Paths) -> None:
    (paths.root / "profile.json").write_text("{}", encoding="utf-8")
    assert call(paths, "/runs/log/../profile.json").status == HTTPStatus.NOT_FOUND
    assert call(paths, "/runs/log/20260101-000000-000000.log").status == HTTPStatus.NOT_FOUND
    assert b"No runs yet" in runs.home_panel(sqlite3.connect(":memory:"), paths).encode()
