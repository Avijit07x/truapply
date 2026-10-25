import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from satyaapply.core.codec import encode
from satyaapply.core.forms import Sent
from satyaapply.core.models import ACTIVE_STATUSES, Job, Source, Status

INSERT_JOB = """
insert or ignore into jobs (
    key, dupe, source, url, apply_url, company, title, location, description,
    posted_at, found_at, status, status_at
) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""
SELECT_JOB = "select * from jobs where id = ?"
SELECT_TO_SCORE = """
select * from jobs where status = 'new'
order by posted_at is null, posted_at desc, found_at desc limit ?
"""
SELECT_TO_APPLY = """
select * from jobs where status = 'scored'
order by score desc, posted_at is null, posted_at desc limit ?
"""
UPDATE_STATUS = "update jobs set status = ?, status_at = ?, note = ? where id = ?"
UPDATE_SCORE = "update jobs set score = ?, status = ?, status_at = ?, note = ? where id = ?"
UPDATE_ATTEMPT = """
update jobs set status = ?, status_at = ?, note = ?, sent = ?, resume_pdf = ?,
    applied_at = case when ? = 'applied' then ? else applied_at end
where id = ?
"""
SELECT_ACTIVE_TWIN = (
    "select 1 from jobs where dupe = ? and key != ? and status in (?, ?, ?, ?, ?) limit 1"
)
COUNT_PREPARED = "select count(*) from jobs where status in (?, ?, ?, ?, ?) and status_at >= ?"
COUNT_PREPARED_ON = COUNT_PREPARED + " and source = ?"


@dataclass(frozen=True)
class StatusChange:
    status: Status
    at: datetime
    note: str | None = None


@dataclass(frozen=True)
class ScoreUpdate:
    score: int
    status: Status
    at: datetime
    note: str


@dataclass(frozen=True)
class AttemptRecord:
    status: Status
    at: datetime
    note: str
    sent: tuple[Sent, ...]
    resume_pdf: Path | None


def _row(job: Job, now: datetime) -> tuple[object, ...]:
    stamp = now.isoformat()
    return (
        job.key,
        job.dupe_key,
        job.source,
        job.url,
        job.apply_url or job.url,
        job.company,
        job.title,
        job.location,
        job.description,
        job.posted_at.isoformat() if job.posted_at else None,
        stamp,
        job.status,
        stamp,
    )


def _job(row: sqlite3.Row) -> Job:
    return Job(
        source=Source(row["source"]),
        external_id=row["key"].split(":", 1)[1],
        url=row["url"],
        company=row["company"],
        title=row["title"],
        location=row["location"],
        description=row["description"],
        apply_url=row["apply_url"],
        posted_at=datetime.fromisoformat(row["posted_at"]) if row["posted_at"] else None,
        status=Status(row["status"]),
        score=row["score"],
        id=row["id"],
    )


def add_many(db: sqlite3.Connection, jobs: Iterable[Job], now: datetime) -> int:
    with db:
        before = db.total_changes
        db.executemany(INSERT_JOB, (_row(job, now) for job in jobs))
        return db.total_changes - before


def find(db: sqlite3.Connection, job_id: int) -> Job | None:
    row = db.execute(SELECT_JOB, (job_id,)).fetchone()
    return _job(row) if row else None


def next_to_score(db: sqlite3.Connection, limit: int) -> list[Job]:
    return [_job(row) for row in db.execute(SELECT_TO_SCORE, (limit,))]


def next_to_apply(db: sqlite3.Connection, limit: int) -> list[Job]:
    return [_job(row) for row in db.execute(SELECT_TO_APPLY, (limit,))]


def set_status(db: sqlite3.Connection, job_id: int, change: StatusChange) -> None:
    with db:
        db.execute(UPDATE_STATUS, (change.status, change.at.isoformat(), change.note, job_id))


def save_score(db: sqlite3.Connection, job_id: int, update: ScoreUpdate) -> None:
    values = (update.score, update.status, update.at.isoformat(), update.note, job_id)
    with db:
        db.execute(UPDATE_SCORE, values)


def record_attempt(db: sqlite3.Connection, job_id: int, record: AttemptRecord) -> None:
    stamp = record.at.isoformat()
    sent = json.dumps(encode(record.sent), ensure_ascii=False)
    resume = str(record.resume_pdf) if record.resume_pdf else None
    with db:
        db.execute(
            UPDATE_ATTEMPT,
            (record.status, stamp, record.note, sent, resume, record.status, stamp, job_id),
        )


def is_duplicate(db: sqlite3.Connection, job: Job) -> bool:
    row = db.execute(SELECT_ACTIVE_TWIN, (job.dupe_key, job.key, *ACTIVE_STATUSES)).fetchone()
    return row is not None


def prepared_since(db: sqlite3.Connection, since: datetime, source: Source | None = None) -> int:
    values: tuple[object, ...] = (*ACTIVE_STATUSES, since.isoformat())
    query = COUNT_PREPARED if source is None else COUNT_PREPARED_ON
    count: int = db.execute(query, values if source is None else (*values, source)).fetchone()[0]
    return count
