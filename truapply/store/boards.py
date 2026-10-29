import sqlite3
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from truapply.core.models import Ats, Board, Source, Status
from truapply.core.profile import CompanySearch
from truapply.store import meta

LAST_SEARCH_KEY = "last_board_search"
SEARCH_EVERY = {CompanySearch.DAILY: timedelta(days=1), CompanySearch.WEEKLY: timedelta(weeks=1)}

INSERT_BOARD = """
insert or ignore into boards (ats, slug, company, origin, added_at) values (?, ?, ?, ?, ?)
"""
SELECT_ACTIVE = "select ats, slug, company from boards where dead = 0 order by ats, slug"
SELECT_KEYS = "select ats, slug from boards"
SELECT_BY_ORIGIN = (
    "select ats, slug, company from boards where origin = ? and not dead order by ats, slug"
)
SELECT_LISTED = """
select ats, slug, company, origin, added_at, checked_at, dead from boards
order by dead, lower(coalesce(nullif(company, ''), slug))
"""
SELECT_JOB_KEYS = "select key from jobs where source = ? and status not in (?, ?)"
UPDATE_CHECKED = "update boards set checked_at = ?, dead = ? where ats = ? and slug = ?"


class BoardOrigin(StrEnum):
    SHARED = "shared"
    SEARCH = "search"
    LINK = "link"
    NAME = "name"
    ARCHIVE = "archive"


def _board(row: sqlite3.Row) -> Board:
    return Board(Ats(row["ats"]), row["slug"], row["company"])


def add_many(
    db: sqlite3.Connection, boards: Iterable[Board], origin: BoardOrigin, now: datetime
) -> int:
    rows = ((board.ats, board.slug, board.company, origin, now.isoformat()) for board in boards)
    with db:
        before = db.total_changes
        db.executemany(INSERT_BOARD, rows)
        return db.total_changes - before


def active(db: sqlite3.Connection) -> list[Board]:
    return [_board(row) for row in db.execute(SELECT_ACTIVE)]


def known_keys(db: sqlite3.Connection) -> set[str]:
    return {f"{row['ats']}/{row['slug']}".lower() for row in db.execute(SELECT_KEYS)}


def by_origin(db: sqlite3.Connection, origin: BoardOrigin) -> list[Board]:
    return [_board(row) for row in db.execute(SELECT_BY_ORIGIN, (origin,))]


@dataclass(frozen=True)
class Listed:
    board: Board
    origin: BoardOrigin
    added_at: str
    checked_at: str | None
    dead: bool
    jobs: int


def _board_of(key: str) -> tuple[str, str]:
    ats, _, rest = key.partition(":")[2].partition("/")
    return ats, rest.partition("/")[0]


def listed(db: sqlite3.Connection) -> list[Listed]:
    shown = (Source.CAREER_PAGES, Status.SKIPPED, Status.CLOSED)
    counts = Counter(_board_of(row["key"]) for row in db.execute(SELECT_JOB_KEYS, shown))
    return [
        Listed(
            _board(row),
            BoardOrigin(row["origin"]),
            row["added_at"],
            row["checked_at"],
            bool(row["dead"]),
            counts[row["ats"], row["slug"]],
        )
        for row in db.execute(SELECT_LISTED)
    ]


def mark_checked(
    db: sqlite3.Connection, alive: Iterable[Board], dead: Iterable[Board], now: datetime
) -> None:
    stamp = now.isoformat()
    rows = [(stamp, 0, board.ats, board.slug) for board in alive]
    rows += [(stamp, 1, board.ats, board.slug) for board in dead]
    with db:
        db.executemany(UPDATE_CHECKED, rows)


def last_search(db: sqlite3.Connection) -> datetime | None:
    last = meta.get(db, LAST_SEARCH_KEY)
    return None if last is None else datetime.fromisoformat(last)


def next_search(db: sqlite3.Connection, every: CompanySearch) -> datetime | None:
    gap, last = SEARCH_EVERY.get(every), last_search(db)
    return None if gap is None or last is None else last + gap


def search_due(db: sqlite3.Connection, every: CompanySearch, now: datetime) -> bool:
    due = next_search(db, every)
    return every in SEARCH_EVERY and (due is None or now >= due)


def searched(db: sqlite3.Connection, now: datetime) -> None:
    meta.put(db, LAST_SEARCH_KEY, now.isoformat())
