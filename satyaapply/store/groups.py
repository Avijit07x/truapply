import json
import sqlite3
from datetime import datetime
from enum import StrEnum

from satyaapply.core.models import LISTED_SOURCES, Status
from satyaapply.core.notes import (
    AI_RULE_NOTE,
    DEALBREAKER_PREFIX,
    DUPLICATE_NOTE,
    LOW_SCORE_PREFIX,
    SKIPPED_COMPANY_NOTE,
    TOO_OLD_NOTE,
    WRONG_PLACE_NOTE,
    WRONG_TITLE_NOTE,
)


class Group(StrEnum):
    FOUND = "found"
    WAITING_SCORE = "waiting_score"
    DUPLICATE = "duplicate"
    NO_AI = "no_ai"
    NOT_A_FIT = "not_a_fit"
    SKIPPED = "skipped"
    WRONG_TITLE = "wrong_title"
    WRONG_PLACE = "wrong_place"
    TOO_OLD = "too_old"
    SKIPPED_COMPANY = "skipped_company"
    SCORED = "scored"
    CLOSED = "closed"
    READY = "ready"
    DISMISSED = "dismissed"
    APPLIED = "applied"


PARAMS: dict[str, str] = {status.value: status.value for status in Status} | {
    "duplicate_note": DUPLICATE_NOTE,
    "no_ai_note": AI_RULE_NOTE,
    "dealbreaker_note": f"{DEALBREAKER_PREFIX}%",
    "low_score_note": f"{LOW_SCORE_PREFIX}%",
    "wrong_title_note": WRONG_TITLE_NOTE,
    "wrong_place_note": WRONG_PLACE_NOTE,
    "too_old_note": TOO_OLD_NOTE,
    "skipped_company_note": SKIPPED_COMPANY_NOTE,
    "listed": json.dumps(LISTED_SOURCES),
}
CAREER = "source not in (select value from json_each(:listed))"
FIT = "(coalesce(note, '') like :dealbreaker_note or coalesce(note, '') like :low_score_note)"
KNOWN_SKIP = f"(coalesce(note, '') in (:duplicate_note, :no_ai_note) or {FIT})"
CONDITIONS: dict[Group, str] = {
    Group.FOUND: "1",
    Group.WAITING_SCORE: "status = :new",
    Group.DUPLICATE: "status = :skipped and note = :duplicate_note",
    Group.NO_AI: "status = :skipped and note = :no_ai_note",
    Group.NOT_A_FIT: f"status = :skipped and {FIT}",
    Group.SKIPPED: f"status = :skipped and not {KNOWN_SKIP}",
    Group.WRONG_TITLE: "status = :skipped and note = :wrong_title_note",
    Group.WRONG_PLACE: "status = :skipped and note = :wrong_place_note",
    Group.TOO_OLD: "status = :skipped and note = :too_old_note",
    Group.SKIPPED_COMPANY: "status = :skipped and note = :skipped_company_note",
    Group.SCORED: "status = :scored",
    Group.CLOSED: "status = :closed",
    Group.READY: "status = :ready",
    Group.DISMISSED: "status = :dismissed",
    Group.APPLIED: "status = :applied",
}
TALLIES = ", ".join(
    f"coalesce(sum(case when {where} then 1 else 0 end), 0) as {group}"
    for group, where in CONDITIONS.items()
)
SELECT_COUNTS = f"select {TALLIES} from jobs where {CAREER}"  # noqa: S608
CHANGED_TALLIES = ", ".join(
    f"coalesce(sum(case when ({where}) and "
    f"{'found_at' if group is Group.FOUND else 'status_at'} >= :since then 1 else 0 end), 0)"
    f" as {group}"
    for group, where in CONDITIONS.items()
)
SELECT_CHANGED = f"select {CHANGED_TALLIES} from jobs where {CAREER}"  # noqa: S608


def counts(db: sqlite3.Connection) -> dict[Group, int]:
    row = db.execute(SELECT_COUNTS, PARAMS).fetchone()
    return {group: int(row[group]) for group in Group}


def changed_since(db: sqlite3.Connection, since: datetime) -> dict[Group, int]:
    row = db.execute(SELECT_CHANGED, PARAMS | {"since": since.isoformat()}).fetchone()
    return {group: int(row[group]) for group in Group}
