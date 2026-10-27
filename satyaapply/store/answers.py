import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from satyaapply.core.models import normalize

TRAILING_MARKERS = re.compile(r"\s*\b(required|optional)\s*$")
UPSERT_ANSWER = """
insert into answers (question, answer, source, updated_at) values (?, ?, ?, ?)
on conflict (question) do update set
    answer = excluded.answer, source = excluded.source, updated_at = excluded.updated_at
where answers.source != 'user' or excluded.source = 'user'
"""
SELECT_ANSWERS = "select question, answer from answers"
SELECT_FOR_JOB = "select question, answer from job_answers where job_id = ?"
UPSERT_FOR_JOB = """
insert into job_answers (job_id, question, answer) values (?, ?, ?)
on conflict (job_id, question) do update set answer = excluded.answer
"""


class AnswerSource(StrEnum):
    USER = "user"
    AI = "ai"


@dataclass(frozen=True)
class SavedAnswer:
    question: str
    answer: str
    source: AnswerSource


def question_key(label: str) -> str:
    return TRAILING_MARKERS.sub("", normalize(label))


def all_answers(db: sqlite3.Connection) -> dict[str, str]:
    return {row["question"]: row["answer"] for row in db.execute(SELECT_ANSWERS)}


def save_many(db: sqlite3.Connection, answers: Iterable[SavedAnswer], now: datetime) -> None:
    stamp = now.isoformat()
    rows = [(question_key(a.question), a.answer, a.source, stamp) for a in answers]
    with db:
        db.executemany(UPSERT_ANSWER, rows)


def for_job(db: sqlite3.Connection, job_id: int) -> dict[str, str]:
    return {row["question"]: row["answer"] for row in db.execute(SELECT_FOR_JOB, (job_id,))}


def keep_for_job(db: sqlite3.Connection, job_id: int, answers: Iterable[tuple[str, str]]) -> None:
    rows = [(job_id, question_key(question), answer) for question, answer in answers]
    with db:
        db.executemany(UPSERT_FOR_JOB, rows)
