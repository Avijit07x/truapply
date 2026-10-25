import sqlite3
from collections.abc import Iterable
from datetime import datetime
from enum import StrEnum

from satyaapply.core.models import Ats, Board

INSERT_BOARD = """
insert or ignore into boards (ats, slug, company, origin, added_at) values (?, ?, ?, ?, ?)
"""
SELECT_ACTIVE = "select ats, slug, company from boards where dead = 0 order by ats, slug"
SELECT_BY_ORIGIN = "select ats, slug, company from boards where origin = ? order by ats, slug"
UPDATE_CHECKED = "update boards set checked_at = ?, dead = ? where ats = ? and slug = ?"


class BoardOrigin(StrEnum):
    SHARED = "shared"
    SEARCH = "search"
    LINK = "link"


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


def by_origin(db: sqlite3.Connection, origin: BoardOrigin) -> list[Board]:
    return [_board(row) for row in db.execute(SELECT_BY_ORIGIN, (origin,))]


def mark_checked(
    db: sqlite3.Connection, alive: Iterable[Board], dead: Iterable[Board], now: datetime
) -> None:
    stamp = now.isoformat()
    rows = [(stamp, 0, board.ats, board.slug) for board in alive]
    rows += [(stamp, 1, board.ats, board.slug) for board in dead]
    with db:
        db.executemany(UPDATE_CHECKED, rows)
