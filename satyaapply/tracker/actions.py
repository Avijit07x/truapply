import re
import sqlite3
from collections.abc import Callable
from dataclasses import replace

from satyaapply.core.clock import utc_now
from satyaapply.core.forms import Sent
from satyaapply.core.models import Status
from satyaapply.core.paths import Paths
from satyaapply.store import feedback, jobs, records, trust
from satyaapply.store.answers import AnswerSource, SavedAnswer, save_many
from satyaapply.store.feedback import Feedback, FeedbackKind
from satyaapply.store.jobs import StatusChange
from satyaapply.store.records import JobRecord
from satyaapply.tracker.html import e, joined, outside_link, section
from satyaapply.tracker.responses import Response, back_to, bad_request, not_found
from satyaapply.tracker.routes import Form, Handler, Route, route

MAX_TEXT = 5000
APPROVED_NOTE = "approved by you; it's sent on the next run"
ANSWERED_NOTE = "answered by you; it's filled on the next run"
FINISHED_NOTE = "submitted by you"
REASONS = ("wrong role", "too senior", "too junior", "location", "salary", "company", "other")
THUMBS = {"1": 1, "-1": -1}
DISMISSABLE = frozenset(
    {
        Status.READY,
        Status.SCORED,
        Status.NEEDS_INPUT,
        Status.FINISH,
        Status.FAILED,
        Status.UNCONFIRMED,
        Status.EXTERNAL,
    }
)
FILE_ENDINGS = ("not uploaded)", ".pdf")
MOVED_ON = "This job has moved on since the page loaded. Go back and reload it."

Act = Callable[[sqlite3.Connection, JobRecord, Form], str | None]


def _text(form: Form, key: str) -> str:
    return form.get(key, "").strip()[:MAX_TEXT]


def _editable(item: Sent) -> bool:
    return not item.answer.endswith(FILE_ENDINGS)


def _job_id(record: JobRecord) -> int:
    return record.job.id or 0


def _note(db: sqlite3.Connection, record: JobRecord, item: Feedback) -> None:
    feedback.add(db, _job_id(record), [item])


def _approve(db: sqlite3.Connection, record: JobRecord, _form: Form) -> str | None:
    now = utc_now()
    edited = any(item.kind is FeedbackKind.EDIT for item in feedback.for_job(db, _job_id(record)))
    jobs.set_status(db, _job_id(record), StatusChange(Status.APPROVED, now, APPROVED_NOTE))
    _note(db, record, Feedback(FeedbackKind.APPROVE, "edited" if edited else "clean", now))
    return None


def _edits(record: JobRecord, form: Form) -> dict[int, str]:
    return {
        index: _text(form, f"a{index}")
        for index, item in enumerate(record.sent)
        if _editable(item)
        and form.get(f"q{index}") == item.question
        and _text(form, f"a{index}") not in {"", item.answer}
    }


def _edit(db: sqlite3.Connection, record: JobRecord, form: Form) -> str | None:
    edits = _edits(record, form)
    if not edits:
        return None
    now = utc_now()
    sent = tuple(
        replace(item, answer=edits[index]) if index in edits else item
        for index, item in enumerate(record.sent)
    )
    changed = [sent[index] for index in edits]
    save_many(db, [SavedAnswer(i.question, i.answer, AnswerSource.USER) for i in changed], now)
    feedback.save_sent(db, _job_id(record), sent)
    feedback.add(
        db, _job_id(record), [Feedback(FeedbackKind.EDIT, i.question, now) for i in changed]
    )
    return None


def _dismiss(db: sqlite3.Connection, record: JobRecord, form: Form) -> str | None:
    reason = form.get("reason", "")
    if reason not in REASONS:
        return "Pick a reason from the list."
    now = utc_now()
    jobs.set_status(
        db, _job_id(record), StatusChange(Status.DISMISSED, now, f"dismissed: {reason}")
    )
    _note(db, record, Feedback(FeedbackKind.DISMISS, reason, now))
    return None


def _thumbs(db: sqlite3.Connection, record: JobRecord, form: Form) -> str | None:
    value = THUMBS.get(form.get("value", ""))
    if value is None:
        return "Pick thumbs up or thumbs down."
    now = utc_now()
    feedback.set_thumbs(db, _job_id(record), value)
    _note(db, record, Feedback(FeedbackKind.THUMBS, str(value), now))
    if value < 0:
        trust.review(db, now)
    return None


def _answer(db: sqlite3.Connection, record: JobRecord, form: Form) -> str | None:
    labels = {item.question: item.label for item in feedback.open_for_job(db, _job_id(record))}
    given = {
        form[f"q{index}"]: _text(form, f"a{index}")
        for index in range(len(labels))
        if form.get(f"q{index}") in labels and _text(form, f"a{index}")
    }
    if not given:
        return None
    now = utc_now()
    save_many(db, [SavedAnswer(labels[q], a, AnswerSource.USER) for q, a in given.items()], now)
    feedback.close_questions(db, given)
    jobs.set_status(db, _job_id(record), StatusChange(Status.SCORED, now, ANSWERED_NOTE))
    feedback.add(
        db, _job_id(record), [Feedback(FeedbackKind.ANSWER, labels[q], now) for q in given]
    )
    return None


def _retry(db: sqlite3.Connection, record: JobRecord, _form: Form) -> str | None:
    jobs.set_status(db, _job_id(record), StatusChange(Status.SCORED, utc_now(), ANSWERED_NOTE))
    return None


def _finished(db: sqlite3.Connection, record: JobRecord, _form: Form) -> str | None:
    now = utc_now()
    feedback.mark_applied(db, _job_id(record), StatusChange(Status.APPLIED, now, FINISHED_NOTE))
    _note(db, record, Feedback(FeedbackKind.FINISHED, "", now))
    return None


def _action(allowed: frozenset[Status], act: Act) -> Handler:
    def handle(db: sqlite3.Connection, _paths: Paths, match: re.Match[str], form: Form) -> Response:
        job_id = int(match.group(1))
        record = records.find(db, job_id)
        if record is None:
            return not_found()
        if record.job.status not in allowed:
            return bad_request(MOVED_ON)
        problem = act(db, record, form)
        return bad_request(problem) if problem else back_to(f"/jobs/{job_id}")

    return handle


def _post(name: str, allowed: frozenset[Status], act: Act) -> Route:
    return route(rf"/jobs/(\d+)/{name}", _action(allowed, act))


GET: tuple[Route, ...] = ()
POST: tuple[Route, ...] = (
    _post("approve", frozenset({Status.READY}), _approve),
    _post("answers", frozenset({Status.READY}), _edit),
    _post("dismiss", DISMISSABLE, _dismiss),
    _post("thumbs", frozenset(Status), _thumbs),
    _post("questions", frozenset({Status.NEEDS_INPUT}), _answer),
    _post("retry", frozenset({Status.NEEDS_INPUT}), _retry),
    _post("finished", frozenset({Status.FINISH}), _finished),
)


def home_panel(_db: sqlite3.Connection, _paths: Paths) -> str:
    return ""


def _form(job_id: int, name: str, inner: str) -> str:
    return f'<form method="post" action="/jobs/{job_id}/{name}">{inner}</form>'


def _hidden(name: str, value: str) -> str:
    return f'<input type="hidden" name="{e(name)}" value="{e(value)}">'


def _approve_form(job_id: int) -> str:
    return _form(job_id, "approve", '<button type="submit">Approve</button>')


def _dismiss_form(job_id: int) -> str:
    options = joined(f'<option value="{e(reason)}">{e(reason)}</option>' for reason in REASONS)
    inner = (
        f'<label class="inline">Why not <select name="reason">{options}</select></label>'
        '<button type="submit" class="secondary">Dismiss</button>'
    )
    return _form(job_id, "dismiss", f'<div class="button-row">{inner}</div>')


def _thumb(value: str, symbol: str, label: str, chosen: bool) -> str:
    pressed = "true" if chosen else "false"
    return (
        f'<button type="submit" class="secondary" name="value" value="{value}" '
        f'aria-label="{label}" aria-pressed="{pressed}">{symbol}</button>'
    )


def _thumbs_form(job_id: int, current: int) -> str:
    buttons = _thumb("1", "👍", "Good job for me", current > 0) + _thumb(
        "-1", "👎", "Bad job for me", current < 0
    )
    return _form(job_id, "thumbs", f'<div class="button-row">{buttons}</div>')


def _finish_forms(record: JobRecord) -> str:
    job_id = _job_id(record)
    skip = _hidden("reason", "other") + '<button type="submit" class="secondary">Skip it</button>'
    return (
        outside_link(record.job.apply_url, "Open the form")
        + _form(job_id, "finished", '<button type="submit">I submitted it</button>')
        + _form(job_id, "dismiss", skip)
    )


def _answers_form(record: JobRecord) -> str:
    fields = joined(
        f"<label>{e(item.question)}"
        f'<textarea name="a{index}" rows="3" maxlength="{MAX_TEXT}">{e(item.answer)}</textarea>'
        f"</label>{_hidden(f'q{index}', item.question)}"
        for index, item in enumerate(record.sent)
        if _editable(item)
    )
    if not fields:
        return ""
    button = '<button type="submit" class="secondary">Save answers</button>'
    return "<h3>Change an answer</h3>" + _form(_job_id(record), "answers", fields + button)


def _questions_form(db: sqlite3.Connection, job_id: int) -> str:
    asked = feedback.open_for_job(db, job_id)
    if not asked:
        retry = '<button type="submit">Fill it again on the next run</button>'
        return (
            '<p class="muted">Its questions are already answered, maybe on another job.</p>'
            + _form(job_id, "retry", retry)
        )
    fields = joined(
        f'<label>{e(item.label)}<input type="text" name="a{index}" maxlength="{MAX_TEXT}">'
        f"</label>{_hidden(f'q{index}', item.question)}"
        for index, item in enumerate(asked)
    )
    button = '<button type="submit">Save my answers</button>'
    return "<h3>Answer these questions</h3>" + _form(job_id, "questions", fields + button)


def job_controls(db: sqlite3.Connection, record: JobRecord) -> str:
    job_id, status = _job_id(record), record.job.status
    row = [_thumbs_form(job_id, feedback.thumbs(db, job_id))]
    if status in DISMISSABLE:
        row.insert(0, _dismiss_form(job_id))
    extra = ""
    if status is Status.READY:
        row.insert(0, _approve_form(job_id))
        extra = _answers_form(record)
    if status is Status.FINISH:
        row.insert(0, _finish_forms(record))
    if status is Status.NEEDS_INPUT:
        extra = _questions_form(db, job_id)
    return section("What you can do", f'<div class="button-row">{joined(row)}</div>{extra}')
