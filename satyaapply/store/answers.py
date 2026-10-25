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
INSERT_QUESTION = """
insert or ignore into questions (question, label, job_id, asked_at) values (?, ?, ?, ?)
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


def open_questions(
    db: sqlite3.Connection, labels: Iterable[str], job_id: int, now: datetime
) -> None:
    stamp = now.isoformat()
    rows = [(question_key(label), label, job_id, stamp) for label in labels]
    with db:
        db.executemany(INSERT_QUESTION, rows)
