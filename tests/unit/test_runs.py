import json
import os
import sqlite3
import sys
import time
from collections.abc import Iterator
from contextlib import closing
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pytest

from truapply.core.models import RunStage
from truapply.core.paths import Paths
from truapply.run.lock import run_lock
from truapply.tracker import automatic, runs
from truapply.tracker.body import Body
from truapply.tracker.routes import Incoming, dispatch

PRINT = (sys.executable, "-c", "print('scoring 1 of 2')")
SLEEP = (sys.executable, "-c", "import time; time.sleep(5)")
CHOICE = {"limit": 2, "search": True}


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


def test_a_choice_needs_a_whole_number_and_a_true_or_false_search() -> None:
    assert runs.parse_choice({"limit": 500, "search": True}) == runs.Choice(50, True)
    assert runs.parse_choice({"limit": 0, "search": False}) == runs.Choice(1, False)
    assert runs.parse_choice({"limit": "3", "search": True}) is None
    assert runs.parse_choice({"limit": 3, "search": "on"}) is None
    assert runs.parse_choice({"limit": 3}) is None
    assert runs.parse_choice({"limit": True, "search": True}) is None


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
    assert state["limits"] == {"min": 1, "max": 50, "default": 5}
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


def test_a_job_you_added_gets_a_run_of_its_own() -> None:
    flags = runs.command(runs.Choice(1, search=False, job=7))[len(runs.COMMAND_PREFIX) :]
    assert flags == ["--job", "7"]


def test_a_run_for_jobs_you_brought_in_skips_finding_new_ones() -> None:
    flags = runs.command(runs.Choice(10, search=False, find=False))[len(runs.COMMAND_PREFIX) :]
    assert flags == ["--limit", "10", "--no-search", "--no-find"]


SHORT = (sys.executable, "-c", "import time; time.sleep(0.5)")


def test_scoring_while_a_run_is_going_waits_its_turn(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runs, "COMMAND_PREFIX", SHORT)
    assert runs.start(paths, runs.Choice(5, search=True)) is not None
    runs.score(paths, [3])
    runs.score(paths, [4, 3])
    assert runs.scoring_now() == [3, 4]
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        current = runs.REGISTRY.current
        if current is not None and current.choice.score:
            break
        time.sleep(0.05)
    current = runs.REGISTRY.current
    assert current is not None
    assert current.choice.score == (3, 4)
    assert runs.REGISTRY.waiting == set()


def test_stopping_drops_jobs_waiting_to_be_scored(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runs, "COMMAND_PREFIX", SLEEP)
    runs.start(paths, runs.Choice(5, search=True))
    runs.score(paths, [7])
    runs.stop()
    assert runs.scoring_now() == []


def test_recent_runs_say_how_they_started_newest_finish_first(paths: Paths) -> None:
    paths.runs.mkdir(parents=True, exist_ok=True)
    older = paths.runs / "20261027-110000-000000.log"
    newer = paths.runs / "20261027-100000-000000.log"
    older.write_text("Automatic run\nScoring …\n", encoding="utf-8")
    newer.write_text("Manual run\n", encoding="utf-8")
    old_log = paths.runs / "20261027-090000-000000.log"
    old_log.write_text("Checking company career pages …\n", encoding="utf-8")
    for log, finished in ((old_log, 1_000), (older, 2_000), (newer, 3_000)):
        os.utime(log, (finished, finished))
    shown = runs.state(paths)["logs"]
    assert isinstance(shown, list)
    assert [(item["name"], item["kind"]) for item in shown] == [
        (newer.name, "manual"),
        (older.name, "automatic"),
        (old_log.name, None),
    ]


def test_an_automatic_run_shows_as_running_with_its_log_but_cannot_be_stopped_here(
    paths: Paths,
) -> None:
    paths.runs.mkdir(parents=True, exist_ok=True)
    log = paths.runs / "20261027-144400-000000.log"
    log.write_text("Automatic run\nChecking company career pages …\n", encoding="utf-8")
    assert runs.state(paths)["running"] is False
    with run_lock(paths):
        going = runs.state(paths)
    assert going["running"] is True
    assert going["stoppable"] is False
    assert going["startedAt"] == "2026-10-27T14:44:00+00:00"
    assert going["log"] == ["Automatic run", "Checking company career pages …"]
    assert runs.state(paths)["running"] is False


def test_the_run_that_is_going_is_marked_in_recent_runs(paths: Paths) -> None:
    paths.runs.mkdir(parents=True, exist_ok=True)
    older = paths.runs / "20261027-100000-000000.log"
    going = paths.runs / "20261027-110000-000000.log"
    for log, finished in ((older, 1_000), (going, 2_000)):
        log.write_text("Manual run\n", encoding="utf-8")
        os.utime(log, (finished, finished))
    with run_lock(paths):
        shown = runs.state(paths)["logs"]
    assert isinstance(shown, list)
    assert [item["running"] for item in shown] == [True, False]
    after = runs.state(paths)["logs"]
    assert isinstance(after, list)
    assert not any(item["running"] for item in after)


def test_each_recent_run_says_how_it_ended(paths: Paths) -> None:
    paths.runs.mkdir(parents=True, exist_ok=True)
    endings = {
        "20261027-100000-000000.log": ("Manual run\n\nSummary\nBoards: 1 checked\n", "done"),
        "20261027-110000-000000.log": ("Automatic run\n✘ No profile yet.\n", "failed"),
        "20261027-120000-000000.log": ("Manual run\nScoring 3 jobs with AI …\n", "stopped"),
    }
    for name, (text, _) in endings.items():
        (paths.runs / name).write_text(text, encoding="utf-8")
    shown = runs.state(paths)["logs"]
    assert isinstance(shown, list)
    assert {item["name"]: item["outcome"] for item in shown} == {
        name: outcome for name, (_, outcome) in endings.items()
    }


def test_the_next_automatic_run_is_the_next_time_of_day_it_is_set_for(
    paths: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    on = {"supported": True, "on": True, "everyMinutes": 30}
    monkeypatch.setattr(automatic, "current", lambda: on)
    now = datetime(2026, 10, 27, 10, 40, tzinfo=UTC)
    monkeypatch.setattr(runs, "utc_now", lambda: now)
    upcoming = runs.state(paths)["nextAutomatic"]
    assert isinstance(upcoming, str)
    assert datetime.fromisoformat(upcoming) - now <= timedelta(minutes=30)
    assert datetime.fromisoformat(upcoming).astimezone().minute in {0, 30}
    monkeypatch.setattr(automatic, "current", lambda: on | {"on": False, "everyMinutes": None})
    assert runs.state(paths)["nextAutomatic"] is None


def test_a_run_can_be_started_for_one_step() -> None:
    choice = runs.parse_choice({"limit": 3, "search": True, "only": "score"})
    assert choice == runs.Choice(3, True, only=RunStage.SCORE)
    assert runs.command(choice)[-2:] == ["--only", "score"]
    assert runs.parse_choice({"limit": 3, "search": True, "only": "x"}) == runs.Choice(3, True)


def test_the_step_a_run_is_on_comes_from_its_latest_progress_line() -> None:
    lines = ["Manual run", "Checking company career pages …", "  40 open jobs", "Scoring 3 jobs"]
    assert runs.stage_of(lines) is RunStage.SCORE
    assert runs.stage_of(lines[:3]) is RunStage.FIND
    assert runs.stage_of(["Manual run"]) is None
