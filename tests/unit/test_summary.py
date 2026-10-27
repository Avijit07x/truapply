import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from satyaapply.core import notify
from satyaapply.core.models import Status
from satyaapply.core.paths import Paths
from satyaapply.core.profile import Settings
from satyaapply.report.summary import QUIET, day_of, headline, markdown, summarize
from satyaapply.store import jobs, usage
from satyaapply.store.db import connect
from satyaapply.store.jobs import AttemptRecord, StatusChange
from tests.unit import samples

EVENING = datetime(2026, 10, 26, 20, 30).astimezone()
MORNING = EVENING.replace(hour=9)
SETTINGS = Settings(summary_hour=20, ai_calls_per_day=300)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(tmp_path / "test.db")) as connection:
        yield connection


@pytest.fixture
def notices(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(notify, "send", lambda title, text: sent.append((title, text)))
    return sent


def test_the_summary_shows_once_a_day_after_the_summary_hour(
    db: sqlite3.Connection, tmp_path: Path, notices: list[tuple[str, str]]
) -> None:
    paths = Paths(tmp_path)
    assert summarize(db, paths, MORNING, SETTINGS) is None
    written = summarize(db, paths, EVENING, SETTINGS)
    assert written == paths.summaries / "2026-10-26.md"
    assert summarize(db, paths, EVENING + timedelta(hours=2), SETTINGS) is None
    assert len(notices) == 1
    assert summarize(db, paths, EVENING + timedelta(days=1), SETTINGS) is not None
    assert len(notices) == 2


def test_the_summary_counts_what_happened_today(db: sqlite3.Connection) -> None:
    now = EVENING.astimezone(UTC)
    picks = [samples.job(external_id=str(n)) for n in range(5)]
    jobs.add_many(db, picks, now)
    jobs.record_attempt(db, 1, AttemptRecord(Status.APPLIED, now, "sent", (), None))
    jobs.set_status(db, 2, StatusChange(Status.READY, now, "filled"))
    jobs.set_status(db, 3, StatusChange(Status.READY, now, "filled"))
    jobs.set_status(db, 4, StatusChange(Status.DISMISSED, now, "dismissed: location"))
    usage.add_ai_calls(db, EVENING.date(), 37)
    day = day_of(db, EVENING, 300)
    assert headline(day) == "1 applied · 2 ready for you to apply"
    text = markdown(day)
    assert "- Applied today: 1" in text
    assert "- Prepared today: 3" in text
    assert "- Claude calls today: 37 of 300" in text


def test_a_quiet_day_says_so(db: sqlite3.Connection) -> None:
    assert headline(day_of(db, EVENING, 300)) == QUIET
