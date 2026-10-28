import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from truapply.core.models import Source, Status
from truapply.core.notes import AUTO_SENT_NOTE, HELD_NOTE, UNCONFIRMED_NOTE
from truapply.store import meta

SINCE_KEY = "auto_submit_since"
CLAIM_FOR = timedelta(minutes=15)
LAST_SENT = 10
TOO_MANY_DOWNS = 2
TIMED_OUT = "it didn't finish in time"

SENDABLE = "status = :ready and source = :source and resume_pdf is not null"
PICK_NEXT = f"""
select id, apply_url, url from jobs
where {SENDABLE} and score >= :score and (
  auto_send = :queued
  or (not :queued_only and auto_send is null and :since is not null and status_at >= :since)
)
order by auto_send = :queued desc, score desc, status_at
limit 1
"""  # noqa: S608
QUEUE = f"""
update jobs set auto_send = :queued
where {SENDABLE} and auto_send is null and score >= :score
"""  # noqa: S608
BELOW = f"select count(*) from jobs where {SENDABLE} and auto_send is null and score < :score"  # noqa: S608
CLAIM = "update jobs set auto_send = :claimed, auto_send_at = :now where id = :id"
IN_FLIGHT = "select count(*) from jobs where auto_send in (:claimed, :submitting)"
EXPIRE = """
update jobs set auto_send = :held, note = :note
where auto_send = :state and auto_send_at < :before
"""
MOVE = """
update jobs set auto_send = :to, auto_send_at = :now
where id = :id and auto_send = :from_state
"""
HOLD = """
update jobs set auto_send = :held, note = :note
where id = :id and auto_send in (:claimed, :submitting)
"""
STATE = "select auto_send from jobs where id = ?"
SENT = "update jobs set auto_submitted = 1, auto_send = :sent, note = :note where id = :id"
DOWNS = """
select count(*) from (
  select feedback from jobs where auto_submitted = 1 order by applied_at desc limit :last
) where feedback < 0
"""


class SendState(StrEnum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    SUBMITTING = "submitting"
    UNCONFIRMED = "unconfirmed"
    HELD = "held"
    SENT = "sent"


PRESSED = frozenset({SendState.SUBMITTING, SendState.UNCONFIRMED})


@dataclass(frozen=True)
class ToSend:
    id: int
    url: str


@dataclass(frozen=True)
class Queued:
    queued: int
    below: int


def turned_on(db: sqlite3.Connection, now: datetime) -> None:
    meta.put(db, SINCE_KEY, now.isoformat())


def _expire(db: sqlite3.Connection, now: datetime) -> None:
    before = (now - CLAIM_FOR).isoformat()
    timed_out = HELD_NOTE.format(why=TIMED_OUT)
    expired = (
        (SendState.CLAIMED, SendState.HELD, timed_out),
        (SendState.SUBMITTING, SendState.UNCONFIRMED, UNCONFIRMED_NOTE),
    )
    for state, to, note in expired:
        db.execute(EXPIRE, {"held": to, "note": note, "state": state, "before": before})


def queue_ready(db: sqlite3.Connection, min_score: int) -> Queued:
    chosen = {
        "ready": Status.READY,
        "source": Source.CAREER_PAGES,
        "score": min_score,
        "queued": SendState.QUEUED,
    }
    with db:
        queued = db.execute(QUEUE, chosen).rowcount
    return Queued(queued, db.execute(BELOW, chosen).fetchone()[0])


def claim_next(
    db: sqlite3.Connection, min_score: int, now: datetime, *, queued_only: bool = False
) -> ToSend | None:
    since = meta.get(db, SINCE_KEY)
    db.execute("begin immediate")
    try:
        found = _claim(db, min_score, None if queued_only else since, now)
    except sqlite3.Error:
        db.rollback()
        raise
    db.commit()
    return found


def _claim(
    db: sqlite3.Connection, min_score: int, since: str | None, now: datetime
) -> ToSend | None:
    _expire(db, now)
    flight = {"claimed": SendState.CLAIMED, "submitting": SendState.SUBMITTING}
    if db.execute(IN_FLIGHT, flight).fetchone()[0]:
        return None
    wanted = {
        "ready": Status.READY,
        "score": min_score,
        "source": Source.CAREER_PAGES,
        "since": since,
        "queued": SendState.QUEUED,
        "queued_only": since is None,
    }
    row = db.execute(PICK_NEXT, wanted).fetchone()
    if row is None:
        return None
    db.execute(CLAIM, {"claimed": SendState.CLAIMED, "now": now.isoformat(), "id": row["id"]})
    return ToSend(row["id"], row["apply_url"] or row["url"])


def submitting(db: sqlite3.Connection, job_id: int, now: datetime) -> bool:
    moved = {
        "to": SendState.SUBMITTING,
        "now": now.isoformat(),
        "id": job_id,
        "from_state": SendState.CLAIMED,
    }
    with db:
        return db.execute(MOVE, moved).rowcount == 1


def hold(db: sqlite3.Connection, job_id: int, why: str) -> None:
    pressed = state(db, job_id) is SendState.SUBMITTING
    note = UNCONFIRMED_NOTE if pressed else HELD_NOTE.format(why=why)
    held = {
        "held": SendState.UNCONFIRMED if pressed else SendState.HELD,
        "note": note,
        "id": job_id,
        "claimed": SendState.CLAIMED,
        "submitting": SendState.SUBMITTING,
    }
    with db:
        db.execute(HOLD, held)


def state(db: sqlite3.Connection, job_id: int) -> SendState | None:
    row = db.execute(STATE, (job_id,)).fetchone()
    return SendState(row[0]) if row and row[0] else None


def mark_sent(db: sqlite3.Connection, job_id: int) -> None:
    with db:
        db.execute(SENT, {"sent": SendState.SENT, "note": AUTO_SENT_NOTE, "id": job_id})


def lost_trust(db: sqlite3.Connection) -> bool:
    downs: int = db.execute(DOWNS, {"last": LAST_SENT}).fetchone()[0]
    return downs >= TOO_MANY_DOWNS
