import sqlite3
from enum import StrEnum

from satyaapply.core.models import Status
from satyaapply.core.notes import AI_RULE_NOTE, DEALBREAKER_PREFIX, DUPLICATE_NOTE, LOW_SCORE_PREFIX


class Group(StrEnum):
    FOUND = "found"
    WAITING_SCORE = "waiting_score"
    DUPLICATE = "duplicate"
    NO_AI = "no_ai"
    NOT_A_FIT = "not_a_fit"
    SKIPPED_OTHER = "skipped_other"
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
}
FIT = "(coalesce(note, '') like :dealbreaker_note or coalesce(note, '') like :low_score_note)"
KNOWN_SKIP = f"(coalesce(note, '') in (:duplicate_note, :no_ai_note) or {FIT})"
CONDITIONS: dict[Group, str] = {
    Group.FOUND: "1",
    Group.WAITING_SCORE: "status = :new",
    Group.DUPLICATE: "status = :skipped and note = :duplicate_note",
    Group.NO_AI: "status = :skipped and note = :no_ai_note",
    Group.NOT_A_FIT: f"status = :skipped and {FIT}",
    Group.SKIPPED_OTHER: f"status = :skipped and not {KNOWN_SKIP}",
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
SELECT_COUNTS = f"select {TALLIES} from jobs"  # noqa: S608


def counts(db: sqlite3.Connection) -> dict[Group, int]:
    row = db.execute(SELECT_COUNTS, PARAMS).fetchone()
    return {group: int(row[group]) for group in Group}
