import threading
from contextlib import closing
from pathlib import Path

from truapply.store.db import connect, schema_version
from truapply.store.migrations import MIGRATIONS

OPENERS = 8


def test_many_connections_opening_a_new_database_at_once_all_succeed(tmp_path: Path) -> None:
    path = tmp_path / "fresh.db"
    start = threading.Barrier(OPENERS)
    failures: list[BaseException] = []

    def open_it() -> None:
        start.wait()
        try:
            connect(path).close()
        except BaseException as error:
            failures.append(error)

    threads = [threading.Thread(target=open_it) for _ in range(OPENERS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert failures == []
    with closing(connect(path)) as db:
        assert schema_version(db) == len(MIGRATIONS)
