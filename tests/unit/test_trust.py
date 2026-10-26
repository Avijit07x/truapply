import sqlite3
import threading
import urllib.request
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError

import pytest

from satyaapply.core import notify
from satyaapply.core.models import Status
from satyaapply.core.paths import Paths
from satyaapply.resume.contract import Rendered
from satyaapply.run.context import RunContext
from satyaapply.run.submitting import STOPPED_NOTE, recover
from satyaapply.store import jobs, records, trust
from satyaapply.store.db import connect
from satyaapply.store.jobs import StatusChange
from satyaapply.tracker.server import TrackerServer
from tests.unit import samples
from tests.unit.test_master import CountingResume

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
INSERT_FEEDBACK = "insert into feedback (job_id, kind, value, at) values (?, ?, ?, ?)"
moments = iter(NOW + timedelta(seconds=step) for step in range(100_000))


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(tmp_path / "test.db")
    yield connection
    connection.close()


def give(db: sqlite3.Connection, kind: str, value: str, times: int = 1) -> None:
    rows = [(None, kind, value, next(moments).isoformat()) for _ in range(times)]
    with db:
        db.executemany(INSERT_FEEDBACK, rows)


def test_clean_approvals_in_a_row_are_counted(db: sqlite3.Connection) -> None:
    give(db, "approve", "clean", 3)
    give(db, "dismiss", "")
    give(db, "thumbs", "1")
    give(db, "approve", "clean", 17)
    assert trust.trust_count(db) == trust.OFFER_AT


@pytest.mark.parametrize(("kind", "value"), [("edit", ""), ("approve", "edited"), ("thumbs", "-1")])
def test_an_edit_or_a_thumbs_down_starts_the_count_again(
    db: sqlite3.Connection, kind: str, value: str
) -> None:
    give(db, "approve", "clean", 25)
    give(db, kind, value)
    give(db, "approve", "clean", 2)
    assert trust.trust_count(db) == 2


def auto_sent(db: sqlite3.Connection, thumbs: list[int]) -> None:
    jobs.add_many(db, [samples.job(external_id=str(i)) for i in range(len(thumbs))], NOW)
    with db:
        db.executemany(
            "update jobs set auto_submitted = 1, feedback = ?, status_at = ? where key = ?",
            [
                (value, next(moments).isoformat(), samples.job(external_id=str(i)).key)
                for i, value in enumerate(thumbs)
            ],
        )


@pytest.fixture
def notices(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(notify, "send", lambda title, text: sent.append((title, text)))
    return sent


def test_two_thumbs_down_in_the_last_ten_turn_auto_submit_off(
    db: sqlite3.Connection, notices: list[tuple[str, str]]
) -> None:
    trust.set_auto_submit(db, True, NOW - timedelta(days=1))
    auto_sent(db, [0, -1, 0, 1, -1, 0])
    assert trust.review(db, NOW)
    assert not trust.auto_submit_on(db)
    assert len(notices) == 1
    assert not trust.review(db, NOW)


def test_thumbs_down_older_than_the_last_ten_do_not_count(
    db: sqlite3.Connection, notices: list[tuple[str, str]]
) -> None:
    trust.set_auto_submit(db, True, NOW - timedelta(days=1))
    auto_sent(db, [-1, -1, *[0] * 10])
    assert not trust.review(db, NOW)
    assert trust.auto_submit_on(db)
    assert notices == []


def test_one_thumbs_down_keeps_auto_submit_on(
    db: sqlite3.Connection, notices: list[tuple[str, str]]
) -> None:
    trust.set_auto_submit(db, True, NOW - timedelta(days=1))
    auto_sent(db, [0, -1, 0, 1])
    assert not trust.review(db, NOW)
    assert trust.auto_submit_on(db)
    assert notices == []


def test_old_thumbs_down_from_before_it_was_turned_on_again_do_not_count(
    db: sqlite3.Connection, notices: list[tuple[str, str]]
) -> None:
    auto_sent(db, [-1, -1])
    trust.set_auto_submit(db, True, NOW + timedelta(days=1))
    assert not trust.review(db, NOW + timedelta(days=1))
    assert notices == []


def test_a_send_cut_short_by_a_crash_is_marked_unconfirmed(
    db: sqlite3.Connection, tmp_path: Path
) -> None:
    jobs.add_many(db, [samples.job()], NOW)
    jobs.mark_submitting(db, 1, NOW, auto=False)
    run = RunContext(
        Paths(tmp_path),
        samples.profile(tmp_path / "master.tex"),
        CountingResume(),
        Rendered(tmp_path / "m.pdf", 1),
        lambda: NOW,
    )
    recover(db, run)
    record = records.find(db, 1)
    assert record is not None
    assert (record.job.status, record.note) == (Status.UNCONFIRMED, STOPPED_NOTE)
    assert jobs.next_approved(db, 5) == []


@pytest.fixture
def tracker(tmp_path: Path) -> Iterator[TrackerServer]:
    paths = Paths(tmp_path)
    paths.ensure()
    connect(paths.database).close()
    server = TrackerServer(paths, 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
    server.server_close()


def home(server: TrackerServer) -> str:
    with urllib.request.urlopen(server.url + "/", timeout=5) as response:  # noqa: S310
        return str(response.read().decode("utf-8"))


def switch(server: TrackerServer, on: str) -> int:
    request = urllib.request.Request(  # noqa: S310
        server.url + "/auto-submit",
        data=f"on={on}".encode(),
        headers={"Origin": server.url, "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
            return int(response.status)
    except HTTPError as error:
        return error.code


def test_auto_submit_is_offered_only_after_twenty_clean_approvals(tracker: TrackerServer) -> None:
    page = home(tracker)
    assert "0 clean approvals in a row. Auto-submit is offered at 20." in page
    assert "Turn on auto-submit" not in page
    assert switch(tracker, "1") == 400
    with connect(tracker.paths.database) as db:
        give(db, "approve", "clean", 20)
    db.close()
    assert "Turn on auto-submit" in home(tracker)
    assert switch(tracker, "1") == 200
    page = home(tracker)
    assert "Auto-submit is on." in page
    assert "Turn off" in page
    assert switch(tracker, "0") == 200
    with connect(tracker.paths.database) as db:
        assert not trust.auto_submit_on(db)
    db.close()


def test_the_switch_takes_only_on_or_off(tracker: TrackerServer) -> None:
    assert switch(tracker, "maybe") == 400


def test_approved_jobs_wait_in_the_send_queue(db: sqlite3.Connection) -> None:
    jobs.add_many(db, [samples.job()], NOW)
    jobs.set_status(db, 1, StatusChange(Status.APPROVED, NOW))
    assert [item.job.id for item in jobs.next_approved(db, 5)] == [1]
    assert jobs.next_approved(db, 0) == []
