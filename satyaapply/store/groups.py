import sqlite3
from enum import StrEnum

from satyaapply.core.models import Status
from satyaapply.core.notes import AI_RULE_NOTE, DEALBREAKER_PREFIX, DUPLICATE_NOTE, LOW_SCORE_PREFIX
from satyaapply.store.records import JobRecord, to_record


class Group(StrEnum):
    FOUND = "found"
    WAITING_SCORE = "waiting_score"
    DUPLICATE = "duplicate"
    NO_AI = "no_ai"
    NOT_A_FIT = "not_a_fit"
    SKIPPED_OTHER = "skipped_other"
    SCORED = "scored"
    CLOSED = "closed"
    NEEDS_INPUT = "needs_input"
    FINISH = "finish"
    FAILED = "failed"
    EXTERNAL = "external"
    READY = "ready"
    AUTO_SENT = "auto_sent"
    APPROVED = "approved"
    DISMISSED = "dismissed"
    APPLIED = "applied"
    UNCONFIRMED = "unconfirmed"


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
    Group.NEEDS_INPUT: "status = :needs_input",
    Group.FINISH: "status = :finish",
    Group.FAILED: "status = :failed",
    Group.EXTERNAL: "status = :external",
    Group.READY: "status = :ready",
    Group.AUTO_SENT: "auto_submitted = 1",
    Group.APPROVED: "status = :approved or (status = :submitting and auto_submitted = 0)",
    Group.DISMISSED: "status = :dismissed",
    Group.APPLIED: "status = :applied",
    Group.UNCONFIRMED: "status = :unconfirmed",
}
TALLIES = ", ".join(
    f"coalesce(sum(case when {where} then 1 else 0 end), 0) as {group}"
    for group, where in CONDITIONS.items()
)
SELECT_COUNTS = f"select {TALLIES} from jobs"  # noqa: S608
SELECT_IN = "select * from jobs where {where} order by status_at desc, id desc limit :limit"


def counts(db: sqlite3.Connection) -> dict[Group, int]:
    row = db.execute(SELECT_COUNTS, PARAMS).fetchone()
    return {group: int(row[group]) for group in Group}


def jobs_in(db: sqlite3.Connection, group: Group, limit: int) -> list[JobRecord]:
    query = SELECT_IN.format(where=f"({CONDITIONS[group]})")
    return [to_record(row) for row in db.execute(query, {**PARAMS, "limit": limit})]
