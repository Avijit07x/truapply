import sqlite3
import time
from pathlib import Path

from satyaapply.core.errors import DatabaseTooNewError
from satyaapply.store.migrations import MIGRATIONS

BUSY_TIMEOUT_S = 10.0
WAL_TRIES = 100
WAL_PAUSE_S = 0.02
WAL = "wal"


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
            stamp = f"pragma user_version = {version};"
            db.executescript(f"begin immediate;\n{script}\n{stamp}\ncommit;")
        except sqlite3.Error:
            db.rollback()
            if schema_version(db) < version:
                raise
    return schema_version(db)


def _share(db: sqlite3.Connection) -> None:
    for _ in range(WAL_TRIES):
        try:
            db.execute(f"pragma journal_mode = {WAL}")
        except sqlite3.OperationalError:
            time.sleep(WAL_PAUSE_S)
        else:
            return
    db.execute(f"pragma journal_mode = {WAL}")


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=BUSY_TIMEOUT_S)
    try:
        db.row_factory = sqlite3.Row
        _share(db)
        db.execute("pragma foreign_keys = on")
        migrate(db)
    except BaseException:
        db.close()
        raise
    return db
