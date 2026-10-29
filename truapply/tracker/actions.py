import re
import sqlite3
from collections.abc import Callable

from truapply.core.clock import utc_now
from truapply.core.errors import TruApplyError
from truapply.core.models import Status
from truapply.core.paths import Paths
from truapply.core.profile import load
from truapply.resume.master import load_resume, master_pdf
from truapply.resume.tailor import keep_original
from truapply.store import feedback, jobs, records
from truapply.store.feedback import Feedback, FeedbackKind
from truapply.store.jobs import StatusChange
from truapply.store.records import JobRecord
from truapply.tracker import autosend, runs
from truapply.tracker.body import Body, number, numbers, text
from truapply.tracker.detail import (
    ALLOWED,
    CLOSED_REASON,
    DISMISS_REASONS,
    DISMISSABLE,
    SCORABLE,
    Action,
    job_detail,
    job_id,
    resume_pdf,
)
from truapply.tracker.responses import Response, bad_request, not_found, ok
from truapply.tracker.routes import Handler, Route, route

MAX_TEXT = 5000
FINISHED_NOTE = "submitted by you"
RUN_GOING = "A run is going. Try again when it finishes."
CLOSED_NOTE = "closed: you said the job is closed"
REVERTED = "resume: reverted to your original"
MOVED_ON = "This job has moved on since you opened it. Reload to see where it is now."
NO_RESUME = "This job has no resume file to change yet."
PICK_REASON = "Pick a reason from the list."
PICK_JOBS = "Pick the jobs to dismiss."
PICK_TO_SCORE = "Pick the jobs to score."
BULK_LIMIT = 200
THUMBS = frozenset({1, -1})

Act = Callable[[sqlite3.Connection, Paths, JobRecord, Body], str | None]


def _note(db: sqlite3.Connection, record: JobRecord, item: Feedback) -> None:
    feedback.add(db, job_id(record), [item])


def dismiss_all(db: sqlite3.Connection, job_ids: list[int], reason: str) -> None:
    now = utc_now()
    if reason == CLOSED_REASON:
        jobs.set_status_many(db, job_ids, StatusChange(Status.CLOSED, now, CLOSED_NOTE))
        return
    jobs.set_status_many(db, job_ids, StatusChange(Status.DISMISSED, now, f"dismissed: {reason}"))
    feedback.add_each(db, [(item, Feedback(FeedbackKind.DISMISS, reason, now)) for item in job_ids])


def _dismiss(db: sqlite3.Connection, _paths: Paths, record: JobRecord, body: Body) -> str | None:
    reason = text(body, "reason", MAX_TEXT)
    if reason not in DISMISS_REASONS:
        return PICK_REASON
    dismiss_all(db, [job_id(record)], reason)
    return None


def _thumbs(db: sqlite3.Connection, paths: Paths, record: JobRecord, body: Body) -> str | None:
    value = number(body, "value")
    if value not in THUMBS or value is None:
        return "Pick thumbs up or thumbs down."
    now = utc_now()
    feedback.set_thumbs(db, job_id(record), value)
    _note(db, record, Feedback(FeedbackKind.THUMBS, str(value), now))
    if value < 0:
        autosend.keep_trust(db, paths)
    return None


def _finished(db: sqlite3.Connection, _paths: Paths, record: JobRecord, _body: Body) -> str | None:
    feedback.finished(db, job_id(record), StatusChange(Status.APPLIED, utc_now(), FINISHED_NOTE))
    return None


def _revert(db: sqlite3.Connection, paths: Paths, record: JobRecord, _body: Body) -> str | None:
    pdf = resume_pdf(paths, record)
    if pdf is None or pdf.parent.resolve() != paths.job_dir(job_id(record)).resolve():
        return NO_RESUME
    try:
        resume = load_resume(load(paths))
        keep_original(resume, pdf, master_pdf(paths, resume))
    except TruApplyError as error:
        return str(error)
    _note(db, record, Feedback(FeedbackKind.EDIT, REVERTED, utc_now()))
    return None


def _score(_db: sqlite3.Connection, paths: Paths, record: JobRecord, _body: Body) -> str | None:
    runs.score(paths, [job_id(record)])
    return None


def _get_ready(_db: sqlite3.Connection, paths: Paths, record: JobRecord, _body: Body) -> str | None:
    started = runs.start(paths, runs.Choice(1, search=False, job=job_id(record)))
    return None if started else RUN_GOING


ACTS: dict[Action, Act] = {
    Action.DISMISS: _dismiss,
    Action.THUMBS: _thumbs,
    Action.FINISHED: _finished,
    Action.REVERT: _revert,
    Action.SCORE: _score,
    Action.TAILOR: _get_ready,
}


def _handler(action: Action) -> Handler:
    def handle(db: sqlite3.Connection, paths: Paths, match: re.Match[str], body: Body) -> Response:
        found = records.find(db, int(match.group(1)))
        if found is None:
            return not_found("No such job.")
        if found.job.status not in ALLOWED[action]:
            return bad_request(MOVED_ON)
        problem = ACTS[action](db, paths, found, body)
        if problem:
            return bad_request(problem)
        updated = records.find(db, job_id(found)) or found
        return ok(job_detail(db, paths, updated))

    return handle


def _dismiss_many(
    db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], body: Body
) -> Response:
    given = numbers(body, "ids")
    if not given or len(given) > BULK_LIMIT:
        return bad_request(PICK_JOBS)
    reason = text(body, "reason", MAX_TEXT)
    if reason not in DISMISS_REASONS:
        return bad_request(PICK_REASON)
    chosen = records.ids_in(db, given, DISMISSABLE)
    dismiss_all(db, chosen, reason)
    return ok({"dismissed": len(chosen), "skipped": len(set(given)) - len(chosen)})


def _score_many(
    db: sqlite3.Connection, paths: Paths, _match: re.Match[str], body: Body
) -> Response:
    given = numbers(body, "ids")
    if not given or len(given) > BULK_LIMIT:
        return bad_request(PICK_TO_SCORE)
    chosen = records.ids_in(db, given, SCORABLE)
    if chosen:
        runs.score(paths, chosen)
    return ok({"scoring": len(chosen), "skipped": len(set(given)) - len(chosen)})


GET: tuple[Route, ...] = ()
POST: tuple[Route, ...] = (
    route(r"/jobs/dismiss", _dismiss_many),
    route(r"/jobs/score", _score_many),
    *(route(rf"/jobs/(\d+)/{action}", _handler(action)) for action in Action),
)
