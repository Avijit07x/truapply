import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from satyaapply.core.models import Job, Source, Status
from satyaapply.core.profile import Profile
from satyaapply.run.tailoring import allowance, within_site_caps
from satyaapply.store import jobs
from satyaapply.store.db import connect
from satyaapply.store.jobs import StatusChange
from tests.unit import samples

NOW = datetime(2026, 10, 26, 10, 0, tzinfo=UTC)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(tmp_path / "test.db")) as connection:
        yield connection


def profile(daily_cap: int | None = 3, linkedin_cap: int = 2) -> Profile:
    base = samples.profile(Path("master.tex"))
    return replace(
        base, daily_cap=daily_cap, settings=replace(base.settings, linkedin_cap=linkedin_cap)
    )


def prepare(db: sqlite3.Connection, picks: list[Job], at: datetime = NOW) -> list[Job]:
    start = db.execute("select count(*) from jobs").fetchone()[0]
    jobs.add_many(db, picks, at)
    for job_id in range(start + 1, start + len(picks) + 1):
        jobs.set_status(db, job_id, StatusChange(Status.READY, at, "filled"))
    return picks


def linkedin(name: str) -> Job:
    return samples.job(Source.LINKEDIN, external_id=name, company=f"LinkedIn {name}")


def test_the_daily_limit_stops_at_exactly_the_cap(db: sqlite3.Connection) -> None:
    capped = profile(daily_cap=3)
    assert allowance(db, capped, lambda: NOW, 5) == 3
    prepare(db, [samples.job(external_id="a"), samples.job(external_id="b")])
    assert allowance(db, capped, lambda: NOW, 5) == 1
    prepare(db, [samples.job(external_id="c")])
    assert allowance(db, capped, lambda: NOW, 5) == 0
    prepare(db, [samples.job(external_id="d")])
    assert allowance(db, capped, lambda: NOW, 5) == 0
    assert allowance(db, profile(daily_cap=None), lambda: NOW, 5) == 5


def test_yesterdays_applications_do_not_count(db: sqlite3.Connection) -> None:
    prepare(db, [samples.job(external_id=n) for n in "abc"], NOW - timedelta(days=1))
    assert allowance(db, profile(daily_cap=3), lambda: NOW, 5) == 3


def test_linkedin_stops_at_its_own_limit(db: sqlite3.Connection) -> None:
    capped = profile(linkedin_cap=2)
    prepare(db, [linkedin("done")])
    picks = [linkedin("a"), samples.job(external_id="x"), linkedin("b"), linkedin("c")]
    kept = within_site_caps(db, capped, lambda: NOW, picks)
    assert [job.external_id for job in kept] == ["a", "x"]
    prepare(db, [linkedin("second")])
    assert [job.external_id for job in within_site_caps(db, capped, lambda: NOW, picks)] == ["x"]
