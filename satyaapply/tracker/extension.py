import re
import sqlite3
from contextlib import suppress
from importlib import resources
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from satyaapply.ai.replies import Posting
from satyaapply.ai.tasks import answer_fields, read_posting
from satyaapply.apply.answering import FormReply, answer_form
from satyaapply.core.clock import utc_now
from satyaapply.core.codec import decode
from satyaapply.core.errors import DecodeError, SatyaApplyError
from satyaapply.core.forms import Field, FieldKind, FormContext, Sent
from satyaapply.core.models import Job, Source, Status
from satyaapply.core.paths import Paths
from satyaapply.core.profile import load
from satyaapply.resume.master import load_resume
from satyaapply.sources.ats import board_of
from satyaapply.sources.intake import take_in_link
from satyaapply.sources.pages import page_job
from satyaapply.store import answers, feedback, jobs, records
from satyaapply.store.answers import AnswerSource, SavedAnswer
from satyaapply.store.feedback import Feedback, FeedbackKind
from satyaapply.store.jobs import StatusChange
from satyaapply.store.records import JobRecord
from satyaapply.tracker import runs
from satyaapply.tracker.body import Body, text
from satyaapply.tracker.detail import job_row, resume_pdf
from satyaapply.tracker.responses import Response, bad_request, not_found, ok
from satyaapply.tracker.routes import Route, route

EXTENSION_ID = "fkmldodijflnecpkmmjhkpbpncgkpmkb"
EXTENSION_ORIGIN = f"chrome-extension://{EXTENSION_ID}"
URL_LIMIT = 2000
MOST_FIELDS = 200
MOST_TEXT = 5000
APPLIED_NOTE = "submitted by you in your Chrome"
NO_JOB = "Couldn't find a job on this page."
PAGE_RUN_LIMIT = 10
MOST_PAGE_JOBS = 100
WEB_PAGE = "http"
MOST_DESCRIPTION = 60_000
MOST_PAGE_TEXT = 30_000
POSTING_FIELDS = ("title", "company", "location", "description")
PREPARABLE = frozenset({Status.NEW, Status.SCORED, Status.SKIPPED})
NOT_LEARNED = frozenset({FieldKind.TEXTAREA, FieldKind.FILE})


def install_info() -> dict[str, object]:
    folder = Path(str(resources.files("satyaapply").joinpath("extension")))
    return {"folder": str(folder), "built": (folder / "manifest.json").is_file()}


def _keys(url: str) -> list[str]:
    page = page_job(url)
    keys = [f"{page.source}:{page.external_id}"]
    board = board_of(url)
    if board is None:
        return keys
    parts = urlsplit(url)
    ids = [*parts.path.split("/"), *(value for _, value in parse_qsl(parts.query))]
    return keys + [f"{Source.CAREER_PAGES}:{board.key}/{posting}" for posting in ids if posting]


def _at(db: sqlite3.Connection, url: str) -> JobRecord | None:
    return records.find_at(db, url, _keys(url)) if url else None


def _view(paths: Paths, record: JobRecord) -> dict[str, object]:
    pdf = resume_pdf(paths, record)
    return job_row(record) | {"resume": pdf.name if pdf else None}


def _job(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], body: Body) -> Response:
    found = _at(db, text(body, "url", URL_LIMIT))
    return ok({"job": _view(paths, found) if found else None})


def start_preparing(paths: Paths, job_id: int) -> bool:
    return runs.start(paths, runs.Choice(1, search=False, job=job_id)) is not None


def _posting(body: Body) -> Posting:
    raw = body.get("posting")
    given = raw if isinstance(raw, dict) else {}
    found = Posting(*(text(given, name, MOST_DESCRIPTION) for name in POSTING_FIELDS))
    page = text(body, "text", MOST_PAGE_TEXT)
    return found if (found.title and found.company) or not page else read_posting(page)


def _from_page(url: str, posting: Posting) -> Job:
    page = page_job(url)
    return Job(
        page.source,
        page.external_id,
        page.url,
        posting.company,
        posting.title,
        location=posting.location,
        description=posting.description,
        apply_url=page.url,
    )


def _new_job(db: sqlite3.Connection, url: str, body: Body) -> JobRecord | str:
    posting = _posting(body)
    if not posting.title or not posting.company:
        return NO_JOB
    jobs.add_many(db, [_from_page(url, posting)], utc_now())
    return _at(db, url) or NO_JOB


def _taken_in(db: sqlite3.Connection, paths: Paths, url: str, body: Body) -> JobRecord | str:
    if board_of(url) is not None:
        take_in_link(db, url, load(paths), utc_now())
    return _at(db, url) or _new_job(db, url, body)


def _add(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], body: Body) -> Response:
    url = text(body, "url", URL_LIMIT)
    if not url.startswith(WEB_PAGE):
        return bad_request(NO_JOB)
    try:
        found = _at(db, url) or _taken_in(db, paths, url, body)
    except SatyaApplyError as error:
        return bad_request(str(error))
    if isinstance(found, str):
        return bad_request(found)
    job_id = found.job.id or 0
    preparing = found.job.status in PREPARABLE and start_preparing(paths, job_id)
    return ok({"job": _view(paths, found), "preparing": preparing})


def _fields(body: Body) -> list[Field] | None:
    raw = body.get("fields")
    if not isinstance(raw, list) or len(raw) > MOST_FIELDS:
        return None
    try:
        return [decode(Field, item) for item in raw]
    except DecodeError:
        return None


def _found(db: sqlite3.Connection, match: re.Match[str]) -> JobRecord | None:
    return records.find(db, int(match.group(1)))


def _reply(db: sqlite3.Connection, paths: Paths, record: JobRecord, body: Body) -> FormReply:
    fields = _fields(body) or []
    profile = load(paths)
    resume = load_resume(profile)
    context = FormContext(profile, resume.readable(resume.source), record.job)
    job_id = record.job.id or 0
    known = answers.for_job(db, job_id) | answers.all_answers(db)
    reply = answer_form(context, fields, known, None if body.get("ai") is False else answer_fields)
    now = utc_now()
    learned = [SavedAnswer(item.question, item.answer, AnswerSource.AI) for item in reply.learned]
    answers.save_many(db, learned, now)
    answers.keep_for_job(db, job_id, [(item.question, item.answer) for item in reply.from_ai])
    return reply


def _answers(db: sqlite3.Connection, paths: Paths, match: re.Match[str], body: Body) -> Response:
    record = _found(db, match)
    if record is None:
        return not_found("No such job.")
    if _fields(body) is None:
        return bad_request("Send the form's fields.")
    try:
        reply = _reply(db, paths, record, body)
    except SatyaApplyError as error:
        return bad_request(str(error))
    return ok(
        {
            "answers": [{"id": key, "value": value} for key, value in reply.answers.items()],
            "forYou": [{"id": i.id, "label": i.label, "why": i.why} for i in reply.for_you],
            "waiting": list(reply.waiting),
            "note": reply.note,
        }
    )


def _sent(body: Body) -> list[tuple[Sent, bool]]:
    raw = body.get("sent")
    found = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        sent = Sent(text(item, "question", MOST_TEXT), text(item, "answer", MOST_TEXT))
        kind = None
        with suppress(ValueError):
            kind = FieldKind(text(item, "kind", MOST_TEXT))
        learn = item.get("yours") is True and kind is not None and kind not in NOT_LEARNED
        if sent.question and sent.answer:
            found.append((sent, learn))
    return found[:MOST_FIELDS]


def _applied(db: sqlite3.Connection, _paths: Paths, match: re.Match[str], body: Body) -> Response:
    record = _found(db, match)
    if record is None:
        return not_found("No such job.")
    if record.job.status is Status.APPLIED:
        return ok({"applied": True})
    job_id, now = record.job.id or 0, utc_now()
    sent = _sent(body)
    yours = [item for item, learn in sent if learn]
    feedback.finished(db, job_id, StatusChange(Status.APPLIED, now, APPLIED_NOTE))
    feedback.save_sent(db, job_id, tuple(item for item, _ in sent))
    typed = [SavedAnswer(item.question, item.answer, AnswerSource.USER) for item in yours]
    answers.save_many(db, typed, now)
    feedback.add(db, job_id, [Feedback(FeedbackKind.EDIT, item.question, now) for item in yours])
    return ok({"applied": True})


def _listed(item: object) -> Job | None:
    given = item if isinstance(item, dict) else {}
    url = text(given, "url", URL_LIMIT)
    raw = given.get("posting")
    if not url.startswith(WEB_PAGE) or not isinstance(raw, dict):
        return None
    posting = Posting(*(text(raw, name, MOST_DESCRIPTION) for name in POSTING_FIELDS))
    return _from_page(url, posting) if posting.title and posting.company else None


def _add_many(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], body: Body) -> Response:
    raw = body.get("jobs")
    listed = [
        job for job in map(_listed, raw[:MOST_PAGE_JOBS] if isinstance(raw, list) else []) if job
    ]
    added = jobs.add_many(db, listed, utc_now())
    if added:
        runs.start(paths, runs.Choice(PAGE_RUN_LIMIT, search=False, find=False))
    return ok({"added": added, "known": len(listed) - added})


GET: tuple[Route, ...] = ()
POST: tuple[Route, ...] = (
    route(r"/extension/job", _job),
    route(r"/extension/add", _add),
    route(r"/extension/add-many", _add_many),
    route(r"/extension/jobs/(\d+)/answers", _answers),
    route(r"/extension/jobs/(\d+)/applied", _applied),
)
