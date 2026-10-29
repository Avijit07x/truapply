import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

import truapply.run as run_module
from tests.unit import samples
from tests.unit.test_master import CountingResume
from tests.unit.tracker_api import get, post, running
from truapply.ai.replies import Score
from truapply.core.models import RunStage, Status
from truapply.core.notes import WRONG_TITLE_NOTE
from truapply.core.paths import Paths
from truapply.resume.contract import Rendered
from truapply.run import rescoring, scoring
from truapply.run.context import RunContext
from truapply.store import jobs
from truapply.store.db import connect
from truapply.store.jobs import StatusChange
from truapply.tracker import runs
from truapply.tracker.server import TrackerServer

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
SENIOR = replace(
    samples.job(external_id="greenhouse/northwind/7"),
    title="Senior Frontend Engineer",
    url="https://job-boards.greenhouse.io/northwind/jobs/7",
)


@pytest.fixture
def started(monkeypatch: pytest.MonkeyPatch) -> list[list[int]]:
    seen: list[list[int]] = []
    monkeypatch.setattr(runs, "score", lambda _paths, job_ids: seen.append(job_ids))
    return seen


@pytest.fixture
def tracker(tmp_path: Path) -> Iterator[TrackerServer]:
    paths = Paths(tmp_path)
    paths.ensure()
    with closing(connect(paths.database)) as db:
        jobs.add_outside_search(db, [(SENIOR, WRONG_TITLE_NOTE)], NOW)
        jobs.add_many(db, [samples.job(external_id="greenhouse/northwind/8")], NOW)
        jobs.set_status(db, 2, StatusChange(Status.APPLIED, NOW, "submitted by you"))
    with running(paths) as server:
        yield server


def test_a_skipped_job_offers_score_this(tracker: TrackerServer) -> None:
    assert "score" in get(tracker, "/api/jobs/1")[1]["actions"]
    assert "score" not in get(tracker, "/api/jobs/2")[1]["actions"]


def test_score_this_starts_a_score_only_run(
    tracker: TrackerServer, started: list[list[int]]
) -> None:
    code, _ = post(tracker, "/api/jobs/1/score")
    assert code == 200
    assert started == [[1]]
    assert runs.command(runs.Choice(1, search=False, score=(1,)))[-2:] == ["--score", "1"]


def test_tailor_this_gets_that_one_job_ready_and_not_just_scored(
    tracker: TrackerServer, started: list[list[int]], monkeypatch: pytest.MonkeyPatch
) -> None:
    launched: list[runs.Choice] = []

    def launch(_paths: Paths, choice: runs.Choice) -> runs.Choice:
        launched.append(choice)
        return choice

    monkeypatch.setattr(runs, "_launch", launch)
    with closing(connect(tracker.paths.database)) as db:
        jobs.set_status(db, 1, StatusChange(Status.SCORED, NOW, "fit"))
    code, _ = post(tracker, "/api/jobs/1/tailor")
    assert code == 200
    assert started == []
    assert [choice.job for choice in launched] == [1]


def test_tailor_this_is_refused_while_a_run_is_going(
    tracker: TrackerServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runs, "start", lambda *_: None)
    with closing(connect(tracker.paths.database)) as db:
        jobs.set_status(db, 1, StatusChange(Status.SCORED, NOW, "fit"))
    code, answer = post(tracker, "/api/jobs/1/tailor")
    assert code == 400
    assert "run is going" in str(answer)


def test_scoring_many_keeps_only_scorable_jobs(
    tracker: TrackerServer, started: list[list[int]]
) -> None:
    code, answer = post(tracker, "/api/jobs/score", {"ids": [1, 2]})
    assert (code, answer) == (200, {"scoring": 1, "skipped": 1})
    assert started == [[1]]


def test_the_list_says_which_jobs_are_being_scored(
    tracker: TrackerServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runs, "scoring_now", lambda: [1])
    assert get(tracker, "/api/jobs?show=all")[1]["scoring"] == [1]


def test_a_job_without_its_description_is_read_again_then_scored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = RunContext(
        Paths(tmp_path),
        samples.profile(tmp_path / "master.tex"),
        CountingResume(),
        Rendered(tmp_path / "m.pdf", 1),
        lambda: NOW,
    )
    read_again: list[str] = []

    def refetched(db: sqlite3.Connection, link: str, *_: object) -> None:
        read_again.append(link)
        jobs.back_in_search(db, [SENIOR], NOW)

    monkeypatch.setattr(rescoring, "take_in_link", refetched)
    monkeypatch.setattr(scoring, "score_job", lambda *_: Score(85, "strong React fit", None, False))
    with closing(connect(tmp_path / "jobs.db")) as db:
        jobs.add_outside_search(db, [(SENIOR, WRONG_TITLE_NOTE)], NOW)
        ready = rescoring.with_descriptions(db, run, [1])
        result = scoring.score_these(db, run, ready)
        found = jobs.find(db, 1)
    assert read_again == [SENIOR.url]
    assert (result.matched, result.skipped) == (1, 0)
    assert found is not None
    assert (found.status, found.score) == (Status.SCORED, 85)


def test_only_good_matches_offer_tailoring(tracker: TrackerServer) -> None:
    with closing(connect(tracker.paths.database)) as db:
        jobs.set_status(db, 1, StatusChange(Status.SCORED, NOW, "fit"))
    assert "tailor" in get(tracker, "/api/jobs/1")[1]["actions"]
    assert "tailor" not in get(tracker, "/api/jobs/2")[1]["actions"]


@pytest.mark.parametrize(
    ("only", "done"),
    [
        (RunStage.FIND, ["find"]),
        (RunStage.SCORE, ["score"]),
        (RunStage.TAILOR, ["tailor"]),
        (None, ["find", "score", "tailor"]),
    ],
)
def test_a_run_can_do_just_one_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, only: RunStage | None, done: list[str]
) -> None:
    run = RunContext(
        Paths(tmp_path),
        samples.profile(tmp_path / "master.tex"),
        CountingResume(),
        Rendered(tmp_path / "m.pdf", 1),
        lambda: NOW,
    )
    seen: list[str] = []

    def step(name: str, result: object) -> Callable[..., object]:
        def ran(*_args: object) -> object:
            seen.append(name)
            return result

        return ran

    monkeypatch.setattr(run_module, "discover", step("find", run_module.NOTHING_FOUND))
    monkeypatch.setattr(run_module, "score_pending", step("score", run_module.NOTHING_SCORED))
    monkeypatch.setattr(run_module, "prepare", step("tailor", []))
    with closing(connect(tmp_path / "jobs.db")) as db:
        run_module._steps(db, run, run_module.RunOptions(search=False, only=only))
    assert seen == done
