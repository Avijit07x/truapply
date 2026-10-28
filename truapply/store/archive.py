import sqlite3
from collections.abc import Iterable
from datetime import datetime

from truapply.core.models import Board
from truapply.core.profile import CompanySearch
from truapply.store import meta
from truapply.store.boards import SEARCH_EVERY

LAST_CRAWL_KEY = "last_archive_crawl"
LAST_CHECK_KEY = "last_archive_check"

UPSERT_CHECKED = """
insert into archive_checked (ats, slug, checked_at) values (?, ?, ?)
on conflict (ats, slug) do update set checked_at = excluded.checked_at
"""
SELECT_CHECKED_SINCE = "select ats, slug from archive_checked where checked_at >= ?"


def checked_since(db: sqlite3.Connection, since: datetime) -> set[str]:
    rows = db.execute(SELECT_CHECKED_SINCE, (since.isoformat(),))
    return {f"{row['ats']}/{row['slug']}" for row in rows}


def mark_checked(db: sqlite3.Connection, boards: Iterable[Board], now: datetime) -> None:
    stamp = now.isoformat()
    with db:
        db.executemany(UPSERT_CHECKED, ((board.ats, board.slug, stamp) for board in boards))


def last_crawl(db: sqlite3.Connection) -> str | None:
    return meta.get(db, LAST_CRAWL_KEY)


def read_crawl(db: sqlite3.Connection, crawl: str) -> None:
    meta.put(db, LAST_CRAWL_KEY, crawl)


def last_check(db: sqlite3.Connection) -> datetime | None:
    last = meta.get(db, LAST_CHECK_KEY)
    return None if last is None else datetime.fromisoformat(last)


def checked(db: sqlite3.Connection, now: datetime) -> None:
    meta.put(db, LAST_CHECK_KEY, now.isoformat())


def check_due(db: sqlite3.Connection, every: CompanySearch, now: datetime) -> bool:
    gap, last = SEARCH_EVERY.get(every), last_check(db)
    return gap is not None and (last is None or now >= last + gap)
