import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from satyaapply.core import notify
from satyaapply.core.clock import start_of_local_day
from satyaapply.core.models import Status
from satyaapply.core.paths import Paths
from satyaapply.core.profile import Settings
from satyaapply.store import jobs, meta, records, usage

LAST_SUMMARY = "last_summary"
TITLE = "SatyaApply today"
QUIET = "Nothing new today."


@dataclass(frozen=True)
class Day:
    day: date
    applied: int
    prepared: int
    ready: int
    ai_calls: int
    ai_budget: int


def due(db: sqlite3.Connection, now: datetime, hour: int) -> bool:
    local = now.astimezone()
    return local.hour >= hour and meta.get(db, LAST_SUMMARY) != local.date().isoformat()


def day_of(db: sqlite3.Connection, now: datetime, ai_budget: int) -> Day:
    since = start_of_local_day(now)
    counts = records.counts(db)
    today = now.astimezone().date()
    return Day(
        today,
        applied=jobs.applied_since(db, since),
        prepared=jobs.prepared_since(db, since),
        ready=counts.get(Status.READY, 0),
        ai_calls=usage.ai_calls_on(db, today),
        ai_budget=ai_budget,
    )


def headline(day: Day) -> str:
    parts = [
        (day.applied, "applied"),
        (day.ready, "ready for you to apply"),
    ]
    shown = [f"{count} {label}" for count, label in parts if count]
    return " · ".join(shown) or QUIET


def markdown(day: Day) -> str:
    lines = (
        f"# SatyaApply · {day.day.day} {day.day:%b %Y}",
        "",
        f"- Applied today: {day.applied}",
        f"- Prepared today: {day.prepared}",
        f"- Ready for you to apply: {day.ready}",
        f"- Claude calls today: {day.ai_calls} of {day.ai_budget}",
        "",
        "Open them from your tracker; the extension fills them in your Chrome.",
        "",
    )
    return "\n".join(lines)


def summarize(
    db: sqlite3.Connection, paths: Paths, now: datetime, settings: Settings
) -> Path | None:
    if not due(db, now, settings.summary_hour):
        return None
    day = day_of(db, now, settings.ai_calls_per_day)
    paths.summaries.mkdir(parents=True, exist_ok=True)
    written = paths.summaries / f"{day.day.isoformat()}.md"
    written.write_text(markdown(day), encoding="utf-8")
    meta.put(db, LAST_SUMMARY, day.day.isoformat())
    notify.send(TITLE, headline(day))
    return written
