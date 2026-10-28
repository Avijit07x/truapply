import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.unit import samples
from tests.unit.tracker_api import get, post, running
from truapply.core.forms import Sent
from truapply.core.models import Status
from truapply.core.paths import Paths
from truapply.store import feedback, jobs, records
from truapply.store.db import connect
from truapply.store.feedback import FeedbackKind
from truapply.store.jobs import AttemptRecord, StatusChange
from truapply.tracker.actions import BULK_LIMIT, MOVED_ON, NO_RESUME
from truapply.tracker.detail import CLOSED_REASON
from truapply.tracker.server import TrackerServer

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
SENT = (
    Sent("Why us?", "Your dashboards match my work."),
    Sent("Resume", "Asha_Rao_Resume.pdf"),
    Sent("Notice period", "30 days"),
)


@pytest.fixture
def tracker(tmp_path: Path) -> Iterator[TrackerServer]:
    paths = Paths(tmp_path)
    paths.ensure()
    picks = [samples.job(external_id=str(index), company=f"C{index}") for index in range(4)]
    with closing(connect(paths.database)) as db:
        jobs.add_many(db, picks, NOW)
        jobs.record_attempt(db, 1, AttemptRecord(Status.READY, NOW, "filled", SENT, None))
        jobs.set_status(db, 2, StatusChange(Status.APPLIED, NOW, "submitted by you"))
        jobs.record_attempt(db, 3, AttemptRecord(Status.READY, NOW, "tailored", (), None))
        jobs.set_status(db, 4, StatusChange(Status.SCORED, NOW, "good match"))
    with running(paths) as server:
        yield server


def database(server: TrackerServer) -> sqlite3.Connection:
    return connect(server.paths.database)


def status_of(server: TrackerServer, job_id: int) -> Status:
    with closing(database(server)) as db:
        record = records.find(db, job_id)
    assert record is not None
    return record.job.status


def kinds(server: TrackerServer, job_id: int) -> list[tuple[FeedbackKind, str]]:
    with closing(database(server)) as db:
        return [(item.kind, item.value) for item in feedback.for_job(db, job_id)]


def test_each_status_offers_only_its_own_actions(tracker: TrackerServer) -> None:
    ready = get(tracker, "/api/jobs/1")[1]
    assert ready["actions"] == ["dismiss", "thumbs", "finished"]
    assert [item["answer"] for item in ready["sent"]] == [item.answer for item in SENT]
    assert get(tracker, "/api/jobs/2")[1]["actions"] == ["thumbs"]
    assert get(tracker, "/api/jobs/4")[1]["actions"] == ["dismiss", "thumbs", "tailor"]


def test_a_dismissed_job_is_never_applied(tracker: TrackerServer) -> None:
    assert post(tracker, "/api/jobs/4/dismiss", {"reason": "made up"})[0] == 400
    assert status_of(tracker, 4) is Status.SCORED
    code, job = post(tracker, "/api/jobs/4/dismiss", {"reason": "too senior"})
    assert (code, job["status"], job["actions"]) == (200, "dismissed", ["thumbs"])
    assert kinds(tracker, 4) == [(FeedbackKind.DISMISS, "too senior")]
    with closing(database(tracker)) as db:
        assert jobs.next_to_apply(db, 10) == []


def test_thumbs_are_saved_on_the_job(tracker: TrackerServer) -> None:
    assert post(tracker, "/api/jobs/4/thumbs", {"value": 2})[0] == 400
    assert post(tracker, "/api/jobs/4/thumbs", {"value": "-1"})[0] == 400
    assert post(tracker, "/api/jobs/4/thumbs", {"value": True})[0] == 400
    code, job = post(tracker, "/api/jobs/4/thumbs", {"value": -1})
    assert (code, job["feedback"]) == (200, -1)
    with closing(database(tracker)) as db:
        assert feedback.thumbs(db, 4) == -1
    assert kinds(tracker, 4) == [(FeedbackKind.THUMBS, "-1")]


def test_a_job_finished_by_hand_is_applied(tracker: TrackerServer) -> None:
    assert post(tracker, "/api/jobs/3/finished")[1]["status"] == "applied"
    with closing(database(tracker)) as db:
        row = db.execute("select status, applied_at from jobs where id = 3").fetchone()
    assert row["status"] == Status.APPLIED
    assert row["applied_at"]
    assert kinds(tracker, 3) == [(FeedbackKind.FINISHED, "")]


def test_skipping_a_job_to_finish_dismisses_it(tracker: TrackerServer) -> None:
    assert post(tracker, "/api/jobs/3/dismiss", {"reason": "other"})[0] == 200
    assert status_of(tracker, 3) is Status.DISMISSED


def test_reverting_needs_a_tailored_resume_on_the_job(tracker: TrackerServer) -> None:
    assert post(tracker, "/api/jobs/1/revert") == (400, {"error": NO_RESUME})
    assert post(tracker, "/api/jobs/4/revert") == (400, {"error": MOVED_ON})
    assert kinds(tracker, 1) == []


def test_unknown_jobs_and_actions_are_not_found(tracker: TrackerServer) -> None:
    assert post(tracker, "/api/jobs/99/finished")[0] == 404
    assert post(tracker, "/api/jobs/1/approve")[0] == 404
    assert post(tracker, "/api/jobs/99/thumbs", {"value": 1})[0] == 404
    assert post(tracker, "/api/jobs/1/status", {"status": "applied"})[0] == 404
    assert post(tracker, "/api/jobs/1/note", {"text": "x"})[0] == 404


def test_many_jobs_are_dismissed_at_once_and_each_one_is_remembered(tracker: TrackerServer) -> None:
    code, result = post(tracker, "/api/jobs/dismiss", {"ids": [1, 3, 99], "reason": "company"})
    assert (code, result) == (200, {"dismissed": 2, "skipped": 1})
    assert [status_of(tracker, job_id) for job_id in (1, 2, 3)] == [
        Status.DISMISSED,
        Status.APPLIED,
        Status.DISMISSED,
    ]
    assert kinds(tracker, 1) == kinds(tracker, 3) == [(FeedbackKind.DISMISS, "company")]
    again = post(tracker, "/api/jobs/dismiss", {"ids": [1, 1], "reason": "company"})
    assert again == (200, {"dismissed": 0, "skipped": 1})
    assert kinds(tracker, 1) == [(FeedbackKind.DISMISS, "company")]


@pytest.mark.parametrize(
    "body",
    [
        {"ids": [], "reason": "company"},
        {"ids": "1", "reason": "company"},
        {"ids": [True], "reason": "company"},
        {"ids": ["1"], "reason": "company"},
        {"ids": list(range(1, BULK_LIMIT + 2)), "reason": "company"},
        {"ids": [1], "reason": "made up"},
        {"ids": [1]},
    ],
)
def test_a_bulk_dismiss_without_jobs_or_a_listed_reason_changes_nothing(
    tracker: TrackerServer, body: dict[str, object]
) -> None:
    assert post(tracker, "/api/jobs/dismiss", body)[0] == 400
    assert status_of(tracker, 1) is Status.READY
    assert kinds(tracker, 1) == []


def test_a_job_you_say_is_closed_is_closed_and_teaches_nothing(tracker: TrackerServer) -> None:
    code, job = post(tracker, "/api/jobs/4/dismiss", {"reason": CLOSED_REASON})
    assert (code, job["status"]) == (200, "closed")
    assert post(tracker, "/api/jobs/dismiss", {"ids": [1], "reason": CLOSED_REASON})[0] == 200
    assert status_of(tracker, 1) is Status.CLOSED
    assert kinds(tracker, 4) == kinds(tracker, 1) == []
