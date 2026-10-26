import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from satyaapply.core.codec import encode
from satyaapply.core.forms import Sent
from satyaapply.core.models import Status
from satyaapply.store.jobs import StatusChange

INSERT_FEEDBACK = "insert into feedback (job_id, kind, value, at) values (?, ?, ?, ?)"
SELECT_FOR_JOB = "select kind, value, at from feedback where job_id = ? order by id"
UPDATE_SENT = "update jobs set sent = ? where id = ?"
UPDATE_THUMBS = "update jobs set feedback = ? where id = ?"
SELECT_THUMBS = "select feedback from jobs where id = ?"
UPDATE_APPLIED = "update jobs set status = ?, status_at = ?, note = ?, applied_at = ? where id = ?"
SELECT_OPEN = "select question, label from questions where job_id = ? order by asked_at, question"
DELETE_QUESTION = "delete from questions where question = ?"


class FeedbackKind(StrEnum):
    APPROVE = "approve"
    EDIT = "edit"
    DISMISS = "dismiss"
    THUMBS = "thumbs"
    ANSWER = "answer"
    FINISHED = "finished"


@dataclass(frozen=True)
class Feedback:
    kind: FeedbackKind
    value: str
    at: datetime


@dataclass(frozen=True)
class OpenQuestion:
    question: str
    label: str


def add(db: sqlite3.Connection, job_id: int, items: Iterable[Feedback]) -> None:
    rows = [(job_id, item.kind, item.value, item.at.isoformat()) for item in items]
    with db:
        db.executemany(INSERT_FEEDBACK, rows)


def for_job(db: sqlite3.Connection, job_id: int) -> tuple[Feedback, ...]:
    return tuple(
        Feedback(FeedbackKind(row["kind"]), row["value"], datetime.fromisoformat(row["at"]))
        for row in db.execute(SELECT_FOR_JOB, (job_id,))
    )


def save_sent(db: sqlite3.Connection, job_id: int, sent: tuple[Sent, ...]) -> None:
    with db:
        db.execute(UPDATE_SENT, (json.dumps(encode(sent), ensure_ascii=False), job_id))


def thumbs(db: sqlite3.Connection, job_id: int) -> int:
    row = db.execute(SELECT_THUMBS, (job_id,)).fetchone()
    return int(row[0]) if row else 0


def set_thumbs(db: sqlite3.Connection, job_id: int, value: int) -> None:
    with db:
        db.execute(UPDATE_THUMBS, (value, job_id))


def mark_applied(db: sqlite3.Connection, job_id: int, change: StatusChange) -> None:
    stamp = change.at.isoformat()
    with db:
        db.execute(UPDATE_APPLIED, (Status.APPLIED, stamp, change.note, stamp, job_id))


def open_for_job(db: sqlite3.Connection, job_id: int) -> tuple[OpenQuestion, ...]:
    return tuple(
        OpenQuestion(row["question"], row["label"]) for row in db.execute(SELECT_OPEN, (job_id,))
    )


def close_questions(db: sqlite3.Connection, questions: Iterable[str]) -> None:
    with db:
        db.executemany(DELETE_QUESTION, [(question,) for question in questions])
