import sqlite3
from pathlib import Path

from satyaapply.core.errors import DatabaseTooNewError
from satyaapply.store.migrations import MIGRATIONS

BUSY_TIMEOUT_S = 10.0


def schema_version(db: sqlite3.Connection) -> int:
    version: int = db.execute("pragma user_version").fetchone()[0]
    return version


def migrate(db: sqlite3.Connection, migrations: tuple[str, ...] = MIGRATIONS) -> int:
    current = schema_version(db)
    if current > len(migrations):
        raise DatabaseTooNewError(
            f"The database is at schema {current}, but this version only knows {len(migrations)}."
        )
    for version, script in enumerate(migrations[current:], start=current + 1):
        try:
            db.executescript(f"begin;\n{script}\npragma user_version = {version};\ncommit;")
        except sqlite3.Error:
            db.rollback()
            raise
    return schema_version(db)


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=BUSY_TIMEOUT_S)
    try:
        db.row_factory = sqlite3.Row
        db.execute("pragma journal_mode = wal")
        db.execute("pragma foreign_keys = on")
        migrate(db)
    except BaseException:
        db.close()
        raise
    return db
