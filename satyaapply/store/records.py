import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from satyaapply.core.forms import Sent
from satyaapply.core.models import Job, Status
from satyaapply.store.jobs import from_row

SELECT_COUNTS = "select status, count(*) from jobs group by status"
SELECT_ONE = "select * from jobs where id = ?"
SELECT_LATEST = "select * from jobs order by status_at desc, id desc limit ?"
SELECT_LATEST_IN = "select * from jobs where status = ? order by status_at desc, id desc limit ?"
SELECT_LATEST_EACH = """
select * from (
    select *, row_number() over (
        partition by status order by status_at desc, id desc
    ) as place from jobs
) where place <= ? order by status_at desc, id desc
"""


@dataclass(frozen=True)
class JobRecord:
    job: Job
    note: str
    reason: str
    updated_at: datetime
    sent: tuple[Sent, ...]
    resume_pdf: Path | None


def _sent(raw: str | None) -> tuple[Sent, ...]:
    try:
        items = json.loads(raw) if raw else []
    except json.JSONDecodeError:
        return ()
    return tuple(
        Sent(str(item.get("question", "")), str(item.get("answer", "")))
        for item in items
        if isinstance(item, dict)
    )


def to_record(row: sqlite3.Row) -> JobRecord:
    return JobRecord(
        job=from_row(row),
        note=row["note"] or "",
        reason=row["reason"] or "",
        updated_at=datetime.fromisoformat(row["status_at"]),
        sent=_sent(row["sent"]),
        resume_pdf=Path(row["resume_pdf"]) if row["resume_pdf"] else None,
    )


def counts(db: sqlite3.Connection) -> dict[Status, int]:
    return {Status(status): total for status, total in db.execute(SELECT_COUNTS)}


def find(db: sqlite3.Connection, job_id: int) -> JobRecord | None:
    row = db.execute(SELECT_ONE, (job_id,)).fetchone()
    return to_record(row) if row else None


def latest(db: sqlite3.Connection, status: Status | None, limit: int) -> list[JobRecord]:
    rows = (
        db.execute(SELECT_LATEST, (limit,))
        if status is None
        else db.execute(SELECT_LATEST_IN, (status, limit))
    )
    return [to_record(row) for row in rows]


def latest_each(db: sqlite3.Connection, limit: int) -> dict[Status, list[JobRecord]]:
    found: dict[Status, list[JobRecord]] = {}
    for row in db.execute(SELECT_LATEST_EACH, (limit,)):
        record = to_record(row)
        found.setdefault(record.job.status, []).append(record)
    return found
