import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from truapply.store.answers import AnswerSource, SavedAnswer

SELECT_ACTIVE = "select text from rules where kind = ? and state = 'active' order by id"
SELECT_KIND = "select id, kind, text, state from rules where kind = ? order by id"
SELECT_ONE = "select id, kind, text, state from rules where id = ?"
INSERT_RULE = "insert into rules (kind, text, state, at) values (?, ?, ?, ?)"
UPDATE_TEXT = "update rules set text = ? where id = ?"
UPDATE_STATE = "update rules set state = ? where id = ?"
DELETE_RULE = "delete from rules where id = ?"
SELECT_SAVED_ANSWERS = "select question, answer, source from answers order by question"
DELETE_ANSWER = "delete from answers where question = ?"
SELECT_FEEDBACK_TITLES = """
select distinct jobs.id, jobs.title from feedback join jobs on jobs.id = feedback.job_id
where feedback.kind = ? and feedback.value = ?
"""


class RuleKind(StrEnum):
    RULE = "rule"
    TAILORING_NOTE = "tailoring_note"
    SUGGESTION = "suggestion"


class RuleState(StrEnum):
    ACTIVE = "active"
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"


@dataclass(frozen=True)
class NewRule:
    kind: RuleKind
    text: str
    state: RuleState
    at: datetime


@dataclass(frozen=True)
class Rule:
    id: int
    kind: RuleKind
    text: str
    state: RuleState


def _rule(row: sqlite3.Row) -> Rule:
    return Rule(row["id"], RuleKind(row["kind"]), row["text"], RuleState(row["state"]))


def active_texts(db: sqlite3.Connection, kind: str) -> tuple[str, ...]:
    return tuple(row[0] for row in db.execute(SELECT_ACTIVE, (kind,)))


def add(db: sqlite3.Connection, rule: NewRule) -> int:
    with db:
        cursor = db.execute(INSERT_RULE, (rule.kind, rule.text, rule.state, rule.at.isoformat()))
    return int(cursor.lastrowid or 0)


def of_kind(db: sqlite3.Connection, kind: RuleKind) -> tuple[Rule, ...]:
    return tuple(_rule(row) for row in db.execute(SELECT_KIND, (kind,)))


def find(db: sqlite3.Connection, rule_id: int) -> Rule | None:
    row = db.execute(SELECT_ONE, (rule_id,)).fetchone()
    return _rule(row) if row else None


def edit(db: sqlite3.Connection, rule_id: int, text: str) -> None:
    with db:
        db.execute(UPDATE_TEXT, (text, rule_id))


def set_state(db: sqlite3.Connection, rule_id: int, state: RuleState) -> None:
    with db:
        db.execute(UPDATE_STATE, (state, rule_id))


def delete(db: sqlite3.Connection, rule_id: int) -> None:
    with db:
        db.execute(DELETE_RULE, (rule_id,))


def saved_answers(db: sqlite3.Connection) -> tuple[SavedAnswer, ...]:
    rows = db.execute(SELECT_SAVED_ANSWERS)
    return tuple(SavedAnswer(r["question"], r["answer"], AnswerSource(r["source"])) for r in rows)


def forget_answer(db: sqlite3.Connection, question: str) -> None:
    with db:
        db.execute(DELETE_ANSWER, (question,))


def feedback_titles(db: sqlite3.Connection, kind: str, value: str) -> tuple[str, ...]:
    return tuple(row["title"] for row in db.execute(SELECT_FEEDBACK_TITLES, (kind, value)))
