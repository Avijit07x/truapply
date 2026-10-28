import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.unit import samples
from truapply.core.errors import DatabaseTooNewError
from truapply.core.models import Source, Status
from truapply.store import jobs
from truapply.store.db import connect, migrate, schema_version
from truapply.store.jobs import StatusChange
from truapply.store.migrations import MIGRATIONS

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(tmp_path / "test.db")
    yield connection
    connection.close()


def test_new_database_runs_every_migration(db: sqlite3.Connection) -> None:
    assert schema_version(db) == len(MIGRATIONS)


def test_migrating_twice_changes_nothing(db: sqlite3.Connection) -> None:
    assert migrate(db) == len(MIGRATIONS)


def test_database_from_a_newer_version_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "new.db"
    with closing(sqlite3.connect(path)) as newer:
        newer.execute(f"pragma user_version = {len(MIGRATIONS) + 1}")
    with pytest.raises(DatabaseTooNewError):
        connect(path)


def test_the_same_posting_is_stored_once(db: sqlite3.Connection) -> None:
    assert jobs.add_many(db, [samples.job(), samples.job()], NOW) == 1
    assert jobs.add_many(db, [samples.job()], NOW) == 0


def test_stored_job_reads_back(db: sqlite3.Connection) -> None:
    jobs.add_many(db, [samples.job()], NOW)
    stored = jobs.find(db, 1)
    assert stored is not None
    assert (stored.key, stored.company, stored.status) == (
        "career_pages:42",
        "Northwind",
        Status.NEW,
    )


def test_same_job_on_a_second_site_is_a_duplicate_once_applied(db: sqlite3.Connection) -> None:
    twin = samples.job(source=Source.LINKEDIN, external_id="li-9", company="Northwind Inc.")
    jobs.add_many(db, [samples.job(), twin], NOW)
    assert not jobs.is_duplicate(db, twin)
    jobs.set_status(db, 1, StatusChange(Status.APPLIED, NOW))
    assert jobs.is_duplicate(db, twin)


def test_skipped_jobs_dont_block_their_twins(db: sqlite3.Connection) -> None:
    twin = samples.job(source=Source.LINKEDIN, external_id="li-9")
    jobs.add_many(db, [samples.job(), twin], NOW)
    jobs.set_status(db, 1, StatusChange(Status.SKIPPED, NOW, "low score"))
    assert not jobs.is_duplicate(db, twin)
