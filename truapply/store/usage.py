import sqlite3
from datetime import date

from truapply.store import meta

AI_CALLS = "ai_calls:"


def ai_calls_on(db: sqlite3.Connection, day: date) -> int:
    return int(meta.get(db, AI_CALLS + day.isoformat()) or 0)


def add_ai_calls(db: sqlite3.Connection, day: date, count: int) -> None:
    if count > 0:
        meta.put(db, AI_CALLS + day.isoformat(), str(ai_calls_on(db, day) + count))
