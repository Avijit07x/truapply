import re
import sqlite3
from collections.abc import Mapping, Sequence
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
from satyaapply.tracker import actions, learning, pages, trust
from satyaapply.tracker.plain import readable_changes
from satyaapply.tracker.responses import Response, html, not_found
from satyaapply.tracker.routes import Form, Incoming, Route, dispatch

JOB_PATH = re.compile(r"^/jobs/(\d+)(?:/(screenshot\.png|resume\.pdf))?$")
HOME_LIST_LIMIT = 10
RECENT_LIMIT = 15
LIST_LIMIT = 500

Query = Mapping[str, Sequence[str]]
FEATURES = (trust, actions, learning)
GET_ROUTES: tuple[Route, ...] = tuple(item for module in FEATURES for item in module.GET)
POST_ROUTES: tuple[Route, ...] = tuple(item for module in FEATURES for item in module.POST)


@cache
def _stylesheet() -> bytes:
    return resources.files("satyaapply.tracker").joinpath("style.css").read_bytes()


def _status(query: Query) -> Status | None:
    wanted = query.get("status", [""])[0]
    return Status(wanted) if wanted in {status.value for status in Status} else None


def _home(db: sqlite3.Connection, paths: Paths) -> Response:
    lists = {
        status: records.latest(db, status, HOME_LIST_LIMIT)
        for status in (Status.NEEDS_INPUT, Status.FINISH, Status.READY)
    }
    panels = [module.home_panel(db, paths) for module in FEATURES]
    recent = records.latest(db, None, RECENT_LIMIT)
    return html(pages.home(records.counts(db), lists, recent, panels))


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
    lines = changed_lines(original, resume.readable(tailored.read_text(encoding="utf-8")))
    return readable_changes(lines)


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
        controls = "".join(module.job_controls(db, record) for module in FEATURES)
        view = pages.JobView(
            record, _changes(paths, job_id), shot is not None, pdf is not None, controls
        )
        detail = pages.job_detail(view)
        return html(detail)
    file, kind = (shot, "image/png") if part == "screenshot.png" else (pdf, "application/pdf")
    return Response(HTTPStatus.OK, file.read_bytes(), kind) if file else not_found()


def respond_get(db: sqlite3.Connection, paths: Paths, path: str, query: Query) -> Response:
    if path == "/":
        return _home(db, paths)
    if path == "/jobs":
        return _jobs(db, query)
    if path == "/favicon.ico":
        return Response(HTTPStatus.NO_CONTENT, b"", "image/x-icon")
    if path == "/style.css":
        return Response(HTTPStatus.OK, _stylesheet(), "text/css; charset=utf-8")
    match = JOB_PATH.match(path)
    if match:
        return _job(db, paths, int(match.group(1)), match.group(2))
    return dispatch(GET_ROUTES, Incoming(db, paths, path, {})) or not_found()


def respond_post(db: sqlite3.Connection, paths: Paths, path: str, form: Form) -> Response:
    return dispatch(POST_ROUTES, Incoming(db, paths, path, form)) or not_found()
