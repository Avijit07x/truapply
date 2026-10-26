import sqlite3
import threading
import urllib.request
from collections.abc import Iterator, Mapping
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode

import pytest

from satyaapply.core.forms import Sent
from satyaapply.core.models import Status
from satyaapply.core.paths import Paths
from satyaapply.store import answers, feedback, jobs, records
from satyaapply.store.db import connect
from satyaapply.store.feedback import FeedbackKind
from satyaapply.store.jobs import AttemptRecord, StatusChange
from satyaapply.tracker.server import TrackerServer
from tests.unit import samples

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
INJECTED = "<script>alert(1)</script>"
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
        jobs.set_status(db, 2, StatusChange(Status.NEEDS_INPUT, NOW, "needs you"))
        answers.open_questions(db, ["Do you hold a security clearance? *", INJECTED], 2, NOW)
        jobs.set_status(db, 3, StatusChange(Status.FINISH, NOW, "prove you're human"))
        jobs.set_status(db, 4, StatusChange(Status.SCORED, NOW, "good match"))
    server = TrackerServer(paths, 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
    server.server_close()


def database(server: TrackerServer) -> sqlite3.Connection:
    return connect(server.paths.database)


def post(server: TrackerServer, path: str, form: Mapping[str, str]) -> tuple[int, bytes]:
    request = urllib.request.Request(  # noqa: S310
        server.url + path,
        data=urlencode(form).encode(),
        headers={"Origin": server.url, "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
            return int(response.status), response.read()
    except HTTPError as error:
        return error.code, error.read()


def page(server: TrackerServer, path: str) -> bytes:
    with urllib.request.urlopen(server.url + path, timeout=5) as response:  # noqa: S310
        body: bytes = response.read()
        return body


def status_of(server: TrackerServer, job_id: int) -> Status:
    with closing(database(server)) as db:
        record = records.find(db, job_id)
    assert record is not None
    return record.job.status


def kinds(server: TrackerServer, job_id: int) -> list[tuple[FeedbackKind, str]]:
    with closing(database(server)) as db:
        return [(item.kind, item.value) for item in feedback.for_job(db, job_id)]


def test_each_status_shows_its_own_controls(tracker: TrackerServer) -> None:
    ready = page(tracker, "/jobs/1")
    assert b'action="/jobs/1/approve"' in ready
    assert b'name="a0"' in ready
    assert b'name="a2"' in ready
    assert b'name="a1"' not in ready
    asked = page(tracker, "/jobs/2")
    assert b'action="/jobs/2/questions"' in asked
    assert INJECTED.encode() not in asked
    finish = page(tracker, "/jobs/3")
    assert b'action="/jobs/3/finished"' in finish
    assert b"Open the form" in finish
    assert b'action="/jobs/4/approve"' not in page(tracker, "/jobs/4")
    assert b"Finish these" in page(tracker, "/")


def test_approving_marks_it_approved_and_counts_a_clean_approval(tracker: TrackerServer) -> None:
    code, body = post(tracker, "/jobs/1/approve", {})
    assert code == 200
    assert b"Approved, sends on the next run" in body
    assert status_of(tracker, 1) is Status.APPROVED
    assert kinds(tracker, 1) == [(FeedbackKind.APPROVE, "clean")]
    assert post(tracker, "/jobs/1/approve", {})[0] == 400


def test_an_edited_answer_is_saved_as_yours_and_used_next_time(tracker: TrackerServer) -> None:
    form = {"q0": "Why us?", "a0": "I use your product daily.", "q2": "Notice period"}
    form |= {"a2": "30 days", "q1": "Resume", "a1": "other.pdf", "zzz": "ignored"}
    assert post(tracker, "/jobs/1/answers", form)[0] == 200
    with closing(database(tracker)) as db:
        record = records.find(db, 1)
        saved = answers.all_answers(db)
    assert record is not None
    assert [item.answer for item in record.sent] == [
        "I use your product daily.",
        "Asha_Rao_Resume.pdf",
        "30 days",
    ]
    assert saved == {"why us": "I use your product daily."}
    assert kinds(tracker, 1) == [(FeedbackKind.EDIT, "Why us?")]
    post(tracker, "/jobs/1/approve", {})
    assert kinds(tracker, 1)[-1] == (FeedbackKind.APPROVE, "edited")


def test_a_stale_question_index_changes_nothing(tracker: TrackerServer) -> None:
    assert post(tracker, "/jobs/1/answers", {"q0": "Something else", "a0": "x"})[0] == 200
    assert kinds(tracker, 1) == []


def test_a_dismissed_job_is_never_applied(tracker: TrackerServer) -> None:
    assert post(tracker, "/jobs/4/dismiss", {"reason": "made up"})[0] == 400
    assert status_of(tracker, 4) is Status.SCORED
    assert post(tracker, "/jobs/4/dismiss", {"reason": "too senior"})[0] == 200
    assert status_of(tracker, 4) is Status.DISMISSED
    assert kinds(tracker, 4) == [(FeedbackKind.DISMISS, "too senior")]
    with closing(database(tracker)) as db:
        assert jobs.next_to_apply(db, 10) == []


def test_thumbs_are_saved_on_the_job(tracker: TrackerServer) -> None:
    assert post(tracker, "/jobs/4/thumbs", {"value": "2"})[0] == 400
    assert post(tracker, "/jobs/4/thumbs", {"value": "-1"})[0] == 200
    with closing(database(tracker)) as db:
        assert feedback.thumbs(db, 4) == -1
    assert kinds(tracker, 4) == [(FeedbackKind.THUMBS, "-1")]
    assert b'aria-pressed="true">\xf0\x9f\x91\x8e' in page(tracker, "/jobs/4")


def test_answering_questions_sends_the_job_back_to_be_filled(tracker: TrackerServer) -> None:
    with closing(database(tracker)) as db:
        asked = feedback.open_for_job(db, 2)
    form = {f"q{index}": item.question for index, item in enumerate(asked)}
    clearance = next(i for i, item in enumerate(asked) if "clearance" in item.question)
    form[f"a{clearance}"] = "No"
    assert post(tracker, "/jobs/2/questions", form)[0] == 200
    assert status_of(tracker, 2) is Status.SCORED
    with closing(database(tracker)) as db:
        left = feedback.open_for_job(db, 2)
        saved = answers.all_answers(db)
        assert sorted(job.id or 0 for job in jobs.next_to_apply(db, 10)) == [2, 4]
    assert saved == {"do you hold a security clearance": "No"}
    assert [item.label for item in left] == [INJECTED]
    assert kinds(tracker, 2) == [(FeedbackKind.ANSWER, "Do you hold a security clearance? *")]


def test_a_job_finished_by_hand_is_applied(tracker: TrackerServer) -> None:
    assert post(tracker, "/jobs/3/finished", {})[0] == 200
    with closing(database(tracker)) as db:
        row = db.execute("select status, applied_at from jobs where id = 3").fetchone()
    assert row["status"] == Status.APPLIED
    assert row["applied_at"]
    assert kinds(tracker, 3) == [(FeedbackKind.FINISHED, "")]


def test_skipping_a_job_to_finish_dismisses_it(tracker: TrackerServer) -> None:
    assert post(tracker, "/jobs/3/dismiss", {"reason": "other"})[0] == 200
    assert status_of(tracker, 3) is Status.DISMISSED


def test_unknown_jobs_are_not_found(tracker: TrackerServer) -> None:
    assert post(tracker, "/jobs/99/approve", {})[0] == 404
    assert post(tracker, "/jobs/99/thumbs", {"value": "1"})[0] == 404
