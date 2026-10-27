import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

import satyaapply.run as run_module
from satyaapply.ai.replies import Score
from satyaapply.core.models import Job, Status
from satyaapply.core.paths import Paths
from satyaapply.resume.contract import Rendered
from satyaapply.run import rescoring, scoring
from satyaapply.run.context import RunContext
from satyaapply.store import jobs
from satyaapply.store.db import connect
from satyaapply.store.jobs import StatusChange
from satyaapply.tracker import runs
from satyaapply.tracker.server import TrackerServer
from tests.unit import samples
from tests.unit.test_master import CountingResume
from tests.unit.tracker_api import get, post, running

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
        jobs.add_outside_search(db, [SENIOR], NOW)
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
        jobs.add_outside_search(db, [SENIOR], NOW)
        ready = rescoring.with_descriptions(db, run, [1])
        result = scoring.score_these(db, run, ready)
        found = jobs.find(db, 1)
    assert read_again == [SENIOR.url]
    assert (result.matched, result.skipped) == (1, 0)
    assert found is not None
    assert (found.status, found.score) == (Status.SCORED, 85)


def test_a_good_score_is_tailored_in_the_same_run_and_a_weak_one_is_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = RunContext(
        Paths(tmp_path),
        samples.profile(tmp_path / "master.tex"),
        CountingResume(),
        Rendered(tmp_path / "m.pdf", 1),
        lambda: NOW,
    )
    good = replace(samples.job(external_id="greenhouse/x/1"), title="Frontend Engineer")
    weak = replace(samples.job(external_id="greenhouse/x/2", company="Acme"), title="UI Dev")
    scores = {good.external_id: 88, weak.external_id: 40}
    tailored: list[str] = []

    def score(_profile: object, _resume: object, job: Job, _notes: object) -> Score:
        return Score(scores[job.external_id], "fit", None, False)

    def tailor(_db: object, _run: object, picks: list[Job]) -> list[object]:
        tailored.extend(job.title for job in picks)
        return []

    monkeypatch.setattr(scoring, "score_job", score)
    monkeypatch.setattr(run_module, "tailor_all", tailor)
    with closing(connect(tmp_path / "jobs.db")) as db:
        jobs.add_many(db, [good, weak], NOW)
        report = run_module._score_and_tailor(db, run, (1, 2))
    assert (report.scoring.matched, report.scoring.skipped) == (1, 1)
    assert tailored == ["Frontend Engineer"]


def test_only_good_matches_offer_tailoring(tracker: TrackerServer) -> None:
    with closing(connect(tracker.paths.database)) as db:
        jobs.set_status(db, 1, StatusChange(Status.SCORED, NOW, "fit"))
    assert "tailor" in get(tracker, "/api/jobs/1")[1]["actions"]
    assert "tailor" not in get(tracker, "/api/jobs/2")[1]["actions"]
