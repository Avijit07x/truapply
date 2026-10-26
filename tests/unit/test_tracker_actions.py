import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest

from satyaapply.core.forms import Sent
from satyaapply.core.models import Status
from satyaapply.core.paths import Paths
from satyaapply.store import answers, feedback, jobs, records
from satyaapply.store.db import connect
from satyaapply.store.feedback import FeedbackKind
from satyaapply.store.jobs import AttemptRecord, StatusChange
from satyaapply.tracker.actions import MOVED_ON, NO_RESUME
from satyaapply.tracker.server import TrackerServer
from tests.unit import samples
from tests.unit.tracker_api import get, post, running

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
    assert ready["actions"] == ["approve", "answers", "dismiss", "thumbs"]
    assert [item["editable"] for item in ready["sent"]] == [True, False, True]
    asked = get(tracker, "/api/jobs/2")[1]
    assert asked["actions"] == ["dismiss", "thumbs", "questions", "retry"]
    assert [item["label"] for item in asked["questions"]] == [
        "Do you hold a security clearance? *",
        INJECTED,
    ]
    assert get(tracker, "/api/jobs/3")[1]["actions"] == ["dismiss", "thumbs", "finished"]
    assert get(tracker, "/api/jobs/4")[1]["actions"] == ["dismiss", "thumbs"]


def test_approving_marks_it_approved_and_counts_a_clean_approval(tracker: TrackerServer) -> None:
    code, job = post(tracker, "/api/jobs/1/approve")
    assert (code, job["status"]) == (200, "approved")
    assert status_of(tracker, 1) is Status.APPROVED
    assert kinds(tracker, 1) == [(FeedbackKind.APPROVE, "clean")]
    assert post(tracker, "/api/jobs/1/approve") == (400, {"error": MOVED_ON})


def test_an_edited_answer_is_saved_as_yours_and_used_next_time(tracker: TrackerServer) -> None:
    edits = [
        {"question": "Why us?", "answer": "I use your product daily."},
        {"question": "Notice period", "answer": "30 days"},
        {"question": "Resume", "answer": "other.pdf"},
        {"question": "Made up", "answer": "ignored"},
    ]
    code, job = post(tracker, "/api/jobs/1/answers", {"answers": edits})
    assert code == 200
    assert [item["answer"] for item in job["sent"]] == [
        "I use your product daily.",
        "Asha_Rao_Resume.pdf",
        "30 days",
    ]
    with closing(database(tracker)) as db:
        assert answers.all_answers(db) == {"why us": "I use your product daily."}
    assert kinds(tracker, 1) == [(FeedbackKind.EDIT, "Why us?")]
    post(tracker, "/api/jobs/1/approve")
    assert kinds(tracker, 1)[-1] == (FeedbackKind.APPROVE, "edited")


def test_answers_for_other_questions_change_nothing(tracker: TrackerServer) -> None:
    stale = {"answers": [{"question": "Something else", "answer": "x"}]}
    assert post(tracker, "/api/jobs/1/answers", stale)[0] == 200
    assert post(tracker, "/api/jobs/1/answers", {"answers": "not a list"})[0] == 200
    assert kinds(tracker, 1) == []


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


def test_answering_questions_sends_the_job_back_to_be_filled(tracker: TrackerServer) -> None:
    questions = get(tracker, "/api/jobs/2")[1]["questions"]
    clearance = next(item["question"] for item in questions if "clearance" in item["label"])
    assert post(tracker, "/api/jobs/2/questions", {"answers": []})[0] == 400
    given = {"answers": [{"question": clearance, "answer": "No"}]}
    code, job = post(tracker, "/api/jobs/2/questions", given)
    assert (code, job["status"], job["questions"]) == (200, "scored", [])
    with closing(database(tracker)) as db:
        left = feedback.open_for_job(db, 2)
        saved = answers.all_answers(db)
        assert sorted(job.id or 0 for job in jobs.next_to_apply(db, 10)) == [2, 4]
    assert saved == {"do you hold a security clearance": "No"}
    assert [item.label for item in left] == [INJECTED]
    assert kinds(tracker, 2) == [(FeedbackKind.ANSWER, "Do you hold a security clearance? *")]


def test_a_job_whose_questions_are_answered_elsewhere_can_be_filled_again(
    tracker: TrackerServer,
) -> None:
    code, job = post(tracker, "/api/jobs/2/retry")
    assert (code, job["status"]) == (200, "scored")
    assert post(tracker, "/api/jobs/2/retry")[0] == 400


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
    assert post(tracker, "/api/jobs/99/approve")[0] == 404
    assert post(tracker, "/api/jobs/99/thumbs", {"value": 1})[0] == 404
    assert post(tracker, "/api/jobs/1/status", {"status": "applied"})[0] == 404
    assert post(tracker, "/api/jobs/1/note", {"text": "x"})[0] == 404
