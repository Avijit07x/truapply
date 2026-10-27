import sqlite3
import threading
from collections.abc import Iterator, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from satyaapply.ai.job_prompts import scoring as scoring_prompt
from satyaapply.ai.replies import Score
from satyaapply.core.errors import AIError, UsageLimitError
from satyaapply.core.models import Job, Source, Status
from satyaapply.core.notes import AI_RULE_NOTE, DUPLICATE_NOTE
from satyaapply.core.paths import Paths
from satyaapply.core.profile import Profile
from satyaapply.resume.contract import Rendered
from satyaapply.resume.tailor import Tailored, TailorRequest
from satyaapply.run import scoring, tailoring
from satyaapply.run.context import RunContext
from satyaapply.run.scoring import decide, score_pending
from satyaapply.run.tailoring import prepare_one
from satyaapply.store import jobs
from satyaapply.store.db import connect
from satyaapply.store.jobs import StatusChange
from tests.unit import samples
from tests.unit.test_master import CountingResume

NOW = datetime(2026, 10, 25, tzinfo=UTC)


@pytest.mark.parametrize(
    ("verdict", "status", "note"),
    [
        (Score(85, "great fit", None, False), Status.SCORED, "great fit"),
        (Score(55, "weak", None, False), Status.SKIPPED, "score 55: weak"),
        (
            Score(90, "fit", "needs US work visa", False),
            Status.SKIPPED,
            "deal-breaker: needs US work visa",
        ),
        (Score(95, "fit", None, True), Status.SKIPPED, AI_RULE_NOTE),
    ],
)
def test_decisions_follow_the_rules(verdict: Score, status: Status, note: str) -> None:
    assert decide(verdict, 60) == (status, note)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(tmp_path / "test.db")
    yield connection
    connection.close()


@pytest.fixture
def run(tmp_path: Path) -> RunContext:
    profile: Profile = samples.profile(tmp_path / "master.tex")
    return RunContext(
        Paths(tmp_path), profile, CountingResume(), Rendered(tmp_path / "m.pdf", 1), lambda: NOW
    )


def test_good_matches_are_queued_and_weak_ones_skipped(
    db: sqlite3.Connection, run: RunContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    jobs.add_many(
        db, [samples.job(external_id="a"), samples.job(external_id="b", company="C")], NOW
    )
    scores = {"a": Score(85, "fit", None, False), "b": Score(30, "weak", None, False)}
    monkeypatch.setattr(scoring, "score_job", lambda _p, _r, job, _f: scores[job.external_id])
    result = score_pending(db, run, 10)
    assert (result.matched, result.skipped, result.failed) == (1, 1, 0)
    assert [job.score for job in jobs.next_to_apply(db, 10)] == [85]


def test_a_duplicate_is_skipped_without_asking_the_ai(
    db: sqlite3.Connection, run: RunContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = samples.job()
    twin: Job = samples.job(source=Source.LINKEDIN, external_id="li-1")
    jobs.add_many(db, [first, twin], NOW)
    jobs.set_status(db, 1, StatusChange(Status.READY, NOW))

    def never(_p: Profile, _r: str, _j: Job, _f: Sequence[str]) -> Score:
        raise AssertionError

    monkeypatch.setattr(scoring, "score_job", never)
    result = score_pending(db, run, 10)
    assert result.skipped == 1
    twin_row = jobs.find(db, 2)
    assert twin_row is not None
    assert twin_row.status is Status.SKIPPED
    row = db.execute("select note from jobs where id = 2").fetchone()
    assert row["note"] == DUPLICATE_NOTE


def test_a_failed_score_is_retried_next_run(
    db: sqlite3.Connection, run: RunContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    jobs.add_many(db, [samples.job()], NOW)

    def broken(_p: Profile, _r: str, _j: Job, _f: Sequence[str]) -> Score:
        raise AIError("bad reply")

    monkeypatch.setattr(scoring, "score_job", broken)
    assert score_pending(db, run, 10).failed == 1
    assert [job.status for job in jobs.next_to_score(db, 10)] == [Status.NEW]


def test_a_usage_limit_stops_scoring(
    db: sqlite3.Connection, run: RunContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    jobs.add_many(db, [samples.job()], NOW)

    def limited(_p: Profile, _r: str, _j: Job, _f: Sequence[str]) -> Score:
        raise UsageLimitError("limit")

    monkeypatch.setattr(scoring, "score_job", limited)
    with pytest.raises(UsageLimitError):
        score_pending(db, run, 10)


def test_each_scored_job_is_reported_as_it_happens(
    db: sqlite3.Connection, run: RunContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    jobs.add_many(
        db, [samples.job(external_id="a"), samples.job(external_id="b", company="C")], NOW
    )
    scores = {"a": Score(85, "fit", None, False), "b": Score(30, "weak", "needs a US visa", False)}
    monkeypatch.setattr(scoring, "score_job", lambda _p, _r, job, _f: scores[job.external_id])
    said: list[str] = []
    score_pending(db, replace(run, progress=said.append), 10)
    assert said == [
        "Scoring 2 jobs with AI …",
        "  1/2 Northwind · Frontend Engineer: 85, good match",
        "  2/2 C · Frontend Engineer: skipped, deal-breaker: needs a US visa",
    ]


def test_jobs_are_scored_at_the_same_time(
    db: sqlite3.Connection, run: RunContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    jobs.add_many(
        db, [samples.job(external_id="a"), samples.job(external_id="b", company="C")], NOW
    )
    both_running = threading.Barrier(2, timeout=5)

    def score(_p: Profile, _r: str, _j: Job, _f: Sequence[str]) -> Score:
        both_running.wait()
        return Score(85, "fit", None, False)

    monkeypatch.setattr(scoring, "score_job", score)
    assert score_pending(db, run, 10).matched == 2


def test_a_twin_in_the_same_batch_waits_for_the_next_run(
    db: sqlite3.Connection, run: RunContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    jobs.add_many(db, [samples.job(), samples.job(source=Source.LINKEDIN, external_id="li")], NOW)
    monkeypatch.setattr(scoring, "score_job", lambda _p, _r, _j, _f: Score(30, "weak", None, False))
    assert score_pending(db, run, 10).skipped == 1
    assert len(jobs.next_to_score(db, 10)) == 1


def test_the_users_rules_reach_the_scoring_call(
    db: sqlite3.Connection, run: RunContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    jobs.add_many(db, [samples.job()], NOW)
    seen: list[Sequence[str]] = []

    def score(_p: Profile, _r: str, _j: Job, preferences: Sequence[str]) -> Score:
        seen.append(preferences)
        return Score(85, "fit", None, False)

    monkeypatch.setattr(scoring, "score_job", score)
    score_pending(db, replace(run, preferences=("no staffing agencies",)), 10)
    assert seen == [("no staffing agencies",)]


def test_the_scoring_prompt_shows_preferences_only_when_there_are_some(tmp_path: Path) -> None:
    profile = samples.profile(tmp_path / "master.tex")
    plain = scoring_prompt(profile, "resume", samples.job())
    ruled = scoring_prompt(profile, "resume", samples.job(), ("no staffing agencies",))
    assert "<preferences>" not in plain
    assert "<preferences>\n- no staffing agencies\n</preferences>" in ruled
    assert "They never add facts about the candidate." in ruled


@pytest.mark.parametrize(
    "case",
    [
        (Score(40, "weak React match", None, False), Status.READY),
        (Score(90, "fit", None, True), Status.SKIPPED),
    ],
)
def test_a_job_you_added_is_scored_and_tailored_on_its_own(
    db: sqlite3.Connection,
    run: RunContext,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[Score, Status],
) -> None:
    verdict, status = case
    jobs.add_many(
        db, [samples.job(external_id="a"), samples.job(external_id="b", company="C")], NOW
    )
    monkeypatch.setattr(scoring, "score_job", lambda *_args: verdict)
    tailored: list[str] = []

    def tailor(_resume: object, request: TailorRequest) -> Tailored:
        tailored.append(request.job.external_id)
        return Tailored(run.paths.root / "a.pdf", "", False, (), ())

    monkeypatch.setattr(tailoring, "tailor", tailor)
    prepare_one(db, run, 1)
    found = jobs.find(db, 1)
    assert found is not None
    assert (found.status, found.score) == (status, verdict.score)
    assert tailored == (["a"] if status is Status.READY else [])
    untouched = jobs.find(db, 2)
    assert untouched is not None
    assert untouched.status is Status.NEW


def test_pay_and_a_few_extra_years_only_lower_the_score(run: RunContext) -> None:
    prompt = scoring_prompt(run.profile, "resume", samples.job())
    assert "a stated salary is clearly below" not in prompt
    assert "never a dealbreaker" in prompt
    assert "more than about 4 years beyond" in prompt
