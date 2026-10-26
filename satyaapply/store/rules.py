import sqlite3

SELECT_ACTIVE = "select text from rules where kind = ? and state = 'active' order by id"


def active_texts(db: sqlite3.Connection, kind: str) -> tuple[str, ...]:
    return tuple(row[0] for row in db.execute(SELECT_ACTIVE, (kind,)))
