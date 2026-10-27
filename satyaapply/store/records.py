import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from satyaapply.core.forms import Sent
from satyaapply.core.models import Job, Status
from satyaapply.store.jobs import from_row

SELECT_COUNTS = "select status, count(*) from jobs group by status"
SELECT_ONE = "select * from jobs where id = ?"
SELECT_STAMPS = """
select id, status_at from jobs where status in (select value from json_each(?))
order by status_at desc, id desc
"""
SELECT_IDS_IN = """
select id from jobs
where id in (select value from json_each(?)) and status in (select value from json_each(?))
order by id
"""
SELECT_AT = """
select * from jobs
where url = :url or apply_url = :url or lower(key) in (select value from json_each(:keys))
order by id desc limit 1
"""
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


def find_at(db: sqlite3.Connection, url: str, keys: Iterable[str]) -> JobRecord | None:
    chosen = json.dumps(sorted({key.lower() for key in keys}))
    row = db.execute(SELECT_AT, {"url": url, "keys": chosen}).fetchone()
    return to_record(row) if row else None


def ids_in(db: sqlite3.Connection, job_ids: Iterable[int], statuses: Iterable[Status]) -> list[int]:
    chosen = (json.dumps(sorted(set(job_ids))), json.dumps([str(status) for status in statuses]))
    return [int(row[0]) for row in db.execute(SELECT_IDS_IN, chosen)]


def stamps(db: sqlite3.Connection, statuses: Iterable[Status]) -> dict[int, str]:
    chosen = json.dumps([str(status) for status in statuses])
    return {int(row[0]): str(row[1]) for row in db.execute(SELECT_STAMPS, (chosen,))}


def latest_each(db: sqlite3.Connection, limit: int) -> dict[Status, list[JobRecord]]:
    found: dict[Status, list[JobRecord]] = {}
    for row in db.execute(SELECT_LATEST_EACH, (limit,)):
        record = to_record(row)
        found.setdefault(record.job.status, []).append(record)
    return found
