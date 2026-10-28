import sqlite3

SELECT_VALUE = "select value from meta where key = ?"
UPSERT_VALUE = (
    "insert into meta (key, value) values (?, ?) "
    "on conflict (key) do update set value = excluded.value"
)


def get(db: sqlite3.Connection, key: str) -> str | None:
    row = db.execute(SELECT_VALUE, (key,)).fetchone()
    return str(row["value"]) if row else None


def put(db: sqlite3.Connection, key: str, value: str) -> None:
    with db:
        db.execute(UPSERT_VALUE, (key, value))
