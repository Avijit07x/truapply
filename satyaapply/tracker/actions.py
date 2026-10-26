import re
import sqlite3
from collections.abc import Callable
from dataclasses import replace

from satyaapply.core.clock import utc_now
from satyaapply.core.errors import SatyaApplyError
from satyaapply.core.models import Status
from satyaapply.core.paths import Paths
from satyaapply.core.profile import load
from satyaapply.resume.master import load_resume, master_pdf
from satyaapply.resume.tailor import keep_original
from satyaapply.store import feedback, jobs, records, trust
from satyaapply.store.answers import AnswerSource, SavedAnswer, save_many
from satyaapply.store.feedback import Feedback, FeedbackKind
from satyaapply.store.jobs import StatusChange
from satyaapply.store.records import JobRecord
from satyaapply.tracker.body import Body, number, pairs, text
from satyaapply.tracker.detail import (
    ALLOWED,
    DISMISS_REASONS,
    Action,
    editable,
    job_detail,
    job_id,
    resume_pdf,
)
from satyaapply.tracker.responses import Response, bad_request, not_found, ok
from satyaapply.tracker.routes import Handler, Route, route

MAX_TEXT = 5000
APPROVED_NOTE = "approved by you; it's sent on the next run"
ANSWERED_NOTE = "answered by you; it's filled on the next run"
FINISHED_NOTE = "submitted by you"
REVERTED = "resume: reverted to your original"
MOVED_ON = "This job has moved on since you opened it. Reload to see where it is now."
NO_RESUME = "This job has no resume file to change yet."
THUMBS = frozenset({1, -1})

Act = Callable[[sqlite3.Connection, Paths, JobRecord, Body], str | None]


def _note(db: sqlite3.Connection, record: JobRecord, item: Feedback) -> None:
    feedback.add(db, job_id(record), [item])


def _approve(db: sqlite3.Connection, _paths: Paths, record: JobRecord, _body: Body) -> str | None:
    now = utc_now()
    edited = any(item.kind is FeedbackKind.EDIT for item in feedback.for_job(db, job_id(record)))
    jobs.set_status(db, job_id(record), StatusChange(Status.APPROVED, now, APPROVED_NOTE))
    _note(db, record, Feedback(FeedbackKind.APPROVE, "edited" if edited else "clean", now))
    return None


def _edit(db: sqlite3.Connection, _paths: Paths, record: JobRecord, body: Body) -> str | None:
    given = pairs(body, "answers", MAX_TEXT)
    edits = {
        index: given[item.question]
        for index, item in enumerate(record.sent)
        if editable(item) and given.get(item.question, "") not in {"", item.answer}
    }
    if not edits:
        return None
    now = utc_now()
    sent = tuple(
        replace(item, answer=edits[index]) if index in edits else item
        for index, item in enumerate(record.sent)
    )
    changed = [sent[index] for index in edits]
    save_many(db, [SavedAnswer(i.question, i.answer, AnswerSource.USER) for i in changed], now)
    feedback.save_sent(db, job_id(record), sent)
    feedback.add(
        db, job_id(record), [Feedback(FeedbackKind.EDIT, i.question, now) for i in changed]
    )
    return None


def _dismiss(db: sqlite3.Connection, _paths: Paths, record: JobRecord, body: Body) -> str | None:
    reason = text(body, "reason", MAX_TEXT)
    if reason not in DISMISS_REASONS:
        return "Pick a reason from the list."
    now = utc_now()
    change = StatusChange(Status.DISMISSED, now, f"dismissed: {reason}")
    jobs.set_status(db, job_id(record), change)
    _note(db, record, Feedback(FeedbackKind.DISMISS, reason, now))
    return None


def _thumbs(db: sqlite3.Connection, _paths: Paths, record: JobRecord, body: Body) -> str | None:
    value = number(body, "value")
    if value not in THUMBS or value is None:
        return "Pick thumbs up or thumbs down."
    now = utc_now()
    feedback.set_thumbs(db, job_id(record), value)
    _note(db, record, Feedback(FeedbackKind.THUMBS, str(value), now))
    if value < 0:
        trust.review(db, now)
    return None


def _answer(db: sqlite3.Connection, _paths: Paths, record: JobRecord, body: Body) -> str | None:
    labels = {item.question: item.label for item in feedback.open_for_job(db, job_id(record))}
    given = {q: a for q, a in pairs(body, "answers", MAX_TEXT).items() if q in labels and a}
    if not given:
        return "Answer at least one question."
    now = utc_now()
    save_many(db, [SavedAnswer(labels[q], a, AnswerSource.USER) for q, a in given.items()], now)
    feedback.close_questions(db, given)
    jobs.set_status(db, job_id(record), StatusChange(Status.SCORED, now, ANSWERED_NOTE))
    feedback.add(db, job_id(record), [Feedback(FeedbackKind.ANSWER, labels[q], now) for q in given])
    return None


def _retry(db: sqlite3.Connection, _paths: Paths, record: JobRecord, _body: Body) -> str | None:
    jobs.set_status(db, job_id(record), StatusChange(Status.SCORED, utc_now(), ANSWERED_NOTE))
    return None


def _finished(db: sqlite3.Connection, _paths: Paths, record: JobRecord, _body: Body) -> str | None:
    now = utc_now()
    feedback.mark_applied(db, job_id(record), StatusChange(Status.APPLIED, now, FINISHED_NOTE))
    _note(db, record, Feedback(FeedbackKind.FINISHED, "", now))
    return None


def _revert(db: sqlite3.Connection, paths: Paths, record: JobRecord, _body: Body) -> str | None:
    pdf = resume_pdf(paths, record)
    if pdf is None or pdf.parent.resolve() != paths.job_dir(job_id(record)).resolve():
        return NO_RESUME
    try:
        resume = load_resume(load(paths))
        keep_original(resume, pdf, master_pdf(paths, resume))
    except SatyaApplyError as error:
        return str(error)
    _note(db, record, Feedback(FeedbackKind.EDIT, REVERTED, utc_now()))
    return None


ACTS: dict[Action, Act] = {
    Action.APPROVE: _approve,
    Action.ANSWERS: _edit,
    Action.DISMISS: _dismiss,
    Action.THUMBS: _thumbs,
    Action.QUESTIONS: _answer,
    Action.RETRY: _retry,
    Action.FINISHED: _finished,
    Action.REVERT: _revert,
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


GET: tuple[Route, ...] = ()
POST: tuple[Route, ...] = tuple(
    route(rf"/jobs/(\d+)/{action}", _handler(action)) for action in Action
)
