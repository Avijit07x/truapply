import json
import sqlite3
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from satyaapply.core.forms import Sent
from satyaapply.core.models import Ats, Board, Source, Status
from satyaapply.store import answers, boards, jobs, meta, records
from satyaapply.store.answers import AnswerSource, SavedAnswer, question_key
from satyaapply.store.boards import BoardOrigin
from satyaapply.store.db import connect
from satyaapply.store.jobs import AttemptRecord, ScoreUpdate, StatusChange
from tests.unit import samples

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(tmp_path / "test.db")
    yield connection
    connection.close()


def test_boards_are_added_once_and_dead_ones_leave_the_active_list(db: sqlite3.Connection) -> None:
    northwind, gone = Board(Ats.GREENHOUSE, "northwind", "Northwind"), Board(Ats.LEVER, "gone")
    assert boards.add_many(db, [northwind, gone, northwind], BoardOrigin.SHARED, NOW) == 2
    boards.mark_checked(db, [northwind], [gone], NOW)
    assert boards.active(db) == [northwind]


def test_boards_remember_where_they_came_from(db: sqlite3.Connection) -> None:
    found = Board(Ats.ASHBY, "fabrikam")
    boards.add_many(db, [found], BoardOrigin.SEARCH, NOW)
    assert boards.by_origin(db, BoardOrigin.SEARCH) == [found]
    assert boards.by_origin(db, BoardOrigin.SHARED) == []


@pytest.mark.parametrize(
    ("label", "key"),
    [
        ("Notice period *", "notice period"),
        ("Phone (required)", "phone"),
        (
            "Are you legally authorized to work in India?",
            "are you legally authorized to work in india",
        ),
    ],
)
def test_questions_are_matched_without_punctuation_or_markers(label: str, key: str) -> None:
    assert question_key(label) == key


def test_your_answers_are_never_overwritten_by_the_ai(db: sqlite3.Connection) -> None:
    answers.save_many(db, [SavedAnswer("Notice period", "30 days", AnswerSource.USER)], NOW)
    answers.save_many(db, [SavedAnswer("Notice period *", "60 days", AnswerSource.AI)], NOW)
    answers.save_many(db, [SavedAnswer("Years of React", "2", AnswerSource.AI)], NOW)
    answers.save_many(db, [SavedAnswer("Years of React", "3", AnswerSource.USER)], NOW)
    assert answers.all_answers(db) == {"notice period": "30 days", "years of react": "3"}


def test_jobs_are_scored_newest_first_and_applied_best_first(db: sqlite3.Connection) -> None:
    old = replace(samples.job(external_id="old"), posted_at=NOW - timedelta(days=5))
    new = replace(samples.job(external_id="new", company="Contoso"), posted_at=NOW)
    undated = samples.job(external_id="undated", company="Fabrikam")
    jobs.add_many(db, [old, undated, new], NOW)
    assert [job.external_id for job in jobs.next_to_score(db, 10)] == ["new", "old", "undated"]
    for job_id, score in ((1, 70), (2, 90), (3, 80)):
        jobs.save_score(db, job_id, ScoreUpdate(score, Status.SCORED, NOW, "fit"))
    assert [job.score for job in jobs.next_to_apply(db, 10)] == [90, 80, 70]


def test_an_attempt_records_what_was_sent(db: sqlite3.Connection, tmp_path: Path) -> None:
    jobs.add_many(db, [samples.job()], NOW)
    sent = (Sent("Notice period", "30 days"),)
    jobs.record_attempt(
        db, 1, AttemptRecord(Status.READY, NOW, "dry run", sent, tmp_path / "r.pdf")
    )
    row = db.execute("select status, sent, resume_pdf, applied_at from jobs").fetchone()
    assert row["status"] == "ready"
    assert json.loads(row["sent"]) == [{"question": "Notice period", "answer": "30 days"}]
    assert row["applied_at"] is None


def test_prepared_today_counts_ready_and_applied_but_not_skipped(db: sqlite3.Connection) -> None:
    jobs.add_many(db, [samples.job(external_id=str(n), company=f"C{n}") for n in range(3)], NOW)
    jobs.set_status(db, 1, StatusChange(Status.READY, NOW))
    jobs.set_status(db, 2, StatusChange(Status.SKIPPED, NOW))
    jobs.set_status(db, 3, StatusChange(Status.APPLIED, NOW - timedelta(days=1)))
    assert jobs.prepared_since(db, NOW - timedelta(hours=1)) == 1
    assert jobs.prepared_since(db, NOW - timedelta(days=2)) == 2
    assert jobs.prepared_since(db, NOW - timedelta(days=2), Source.LINKEDIN) == 0


def test_meta_values_round_trip(db: sqlite3.Connection) -> None:
    assert meta.get(db, "last_board_search") is None
    meta.put(db, "last_board_search", "a")
    meta.put(db, "last_board_search", "b")
    assert meta.get(db, "last_board_search") == "b"


def test_records_show_counts_and_what_was_sent_newest_first(
    db: sqlite3.Connection, tmp_path: Path
) -> None:
    jobs.add_many(db, [samples.job(external_id=str(n), company=f"C{n}") for n in range(3)], NOW)
    sent = (Sent("Notice period", "30 days"),)
    later = NOW + timedelta(hours=1)
    jobs.record_attempt(
        db, 2, AttemptRecord(Status.READY, later, "filled", sent, tmp_path / "r.pdf")
    )
    assert records.counts(db) == {Status.NEW: 2, Status.READY: 1}
    ready = records.find(db, 2)
    assert ready is not None
    assert (ready.note, ready.sent, ready.resume_pdf) == ("filled", sent, tmp_path / "r.pdf")
    assert ready.updated_at == later
    assert [item.job.id for item in records.latest(db, None, 10)] == [2, 3, 1]
    assert [item.job.id for item in records.latest(db, Status.NEW, 1)] == [3]
    assert records.find(db, 99) is None


def test_the_score_reason_survives_later_steps(db: sqlite3.Connection, tmp_path: Path) -> None:
    jobs.add_many(db, [samples.job()], NOW)
    jobs.save_score(db, 1, ScoreUpdate(70, Status.SCORED, NOW, "React fits; Angular is a gap"))
    jobs.record_attempt(db, 1, AttemptRecord(Status.READY, NOW, "filled", (), tmp_path / "r.pdf"))
    found = records.find(db, 1)
    assert found is not None
    assert (found.reason, found.note) == ("React fits; Angular is a gap", "filled")
