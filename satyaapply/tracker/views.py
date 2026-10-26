import re
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from http import HTTPStatus
from importlib import resources
from pathlib import Path

from satyaapply.core.errors import SatyaApplyError
from satyaapply.core.models import Status
from satyaapply.core.paths import Paths
from satyaapply.core.profile import load
from satyaapply.resume.diff import changed_lines
from satyaapply.resume.master import load_resume
from satyaapply.store import records
from satyaapply.tracker import pages
from satyaapply.tracker.html import page

JOB_PATH = re.compile(r"^/jobs/(\d+)(?:/(screenshot\.png|resume\.pdf))?$")
HOME_LIST_LIMIT = 10
RECENT_LIMIT = 15
LIST_LIMIT = 500
HTML = "text/html; charset=utf-8"

Query = Mapping[str, Sequence[str]]


@dataclass(frozen=True)
class Response:
    status: HTTPStatus
    body: bytes
    content_type: str


def html(text: str, status: HTTPStatus = HTTPStatus.OK) -> Response:
    return Response(status, text.encode("utf-8"), HTML)


def not_found() -> Response:
    return html(page("Not found", "<h1>Not found</h1>"), HTTPStatus.NOT_FOUND)


@cache
def _stylesheet() -> bytes:
    return resources.files("satyaapply.tracker").joinpath("style.css").read_bytes()


def _status(query: Query) -> Status | None:
    wanted = query.get("status", [""])[0]
    return Status(wanted) if wanted in {status.value for status in Status} else None


def _home(db: sqlite3.Connection) -> Response:
    lists = {
        status: records.latest(db, status, HOME_LIST_LIMIT)
        for status in (Status.NEEDS_INPUT, Status.READY)
    }
    return html(pages.home(records.counts(db), lists, records.latest(db, None, RECENT_LIMIT)))


def _jobs(db: sqlite3.Connection, query: Query) -> Response:
    status = _status(query)
    items = records.latest(db, status, LIST_LIMIT)
    return html(pages.jobs_list(records.counts(db), status, items))


def _changes(paths: Paths, job_id: int) -> list[str] | None:
    try:
        resume = load_resume(load(paths))
    except SatyaApplyError:
        return None
    tailored = paths.job_dir(job_id) / f"tailored{resume.suffix}"
    if not tailored.is_file():
        return None
    original = resume.readable(resume.source)
    return changed_lines(original, resume.readable(tailored.read_text(encoding="utf-8")))


def _inside(path: Path | None, root: Path) -> Path | None:
    if path is None or not path.is_file():
        return None
    return path if path.resolve().is_relative_to(root.resolve()) else None


def _job(db: sqlite3.Connection, paths: Paths, job_id: int, part: str | None) -> Response:
    record = records.find(db, job_id)
    if record is None:
        return not_found()
    shot = _inside(paths.shots / f"{job_id}.png", paths.root)
    pdf = _inside(record.resume_pdf, paths.root)
    if part is None:
        detail = pages.job_detail(
            record, _changes(paths, job_id), shot is not None, pdf is not None
        )
        return html(detail)
    file, kind = (shot, "image/png") if part == "screenshot.png" else (pdf, "application/pdf")
    return Response(HTTPStatus.OK, file.read_bytes(), kind) if file else not_found()


def respond_get(db: sqlite3.Connection, paths: Paths, path: str, query: Query) -> Response:
    if path == "/":
        return _home(db)
    if path == "/jobs":
        return _jobs(db, query)
    if path == "/favicon.ico":
        return Response(HTTPStatus.NO_CONTENT, b"", "image/x-icon")
    if path == "/style.css":
        return Response(HTTPStatus.OK, _stylesheet(), "text/css; charset=utf-8")
    match = JOB_PATH.match(path)
    if match:
        return _job(db, paths, int(match.group(1)), match.group(2))
    return not_found()
