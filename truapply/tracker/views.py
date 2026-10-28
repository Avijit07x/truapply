import re
from contextlib import closing
from http import HTTPStatus

from truapply.core.paths import Paths
from truapply.store import records
from truapply.store.db import connect
from truapply.tracker import (
    actions,
    automatic,
    autosend,
    companies,
    extension,
    learning,
    linking,
    listing,
    resume_upload,
    runs,
    settings,
    static,
)
from truapply.tracker.body import Body
from truapply.tracker.detail import resume_pdf
from truapply.tracker.responses import Response, not_found
from truapply.tracker.routes import Incoming, Route, dispatch

API = "/api/"
PDF = "application/pdf"
JOB_FILE = re.compile(r"^/jobs/(\d+)/resume\.pdf$")
FEATURES = (
    listing,
    companies,
    actions,
    learning,
    linking,
    runs,
    settings,
    automatic,
    resume_upload,
    extension,
    autosend,
)
GET_ROUTES: tuple[Route, ...] = tuple(item for module in FEATURES for item in module.GET)
POST_ROUTES: tuple[Route, ...] = tuple(item for module in FEATURES for item in module.POST)


def _resume(paths: Paths, job_id: int) -> Response:
    with closing(connect(paths.database)) as db:
        record = records.find(db, job_id)
    file = resume_pdf(paths, record) if record else None
    return Response(HTTPStatus.OK, file.read_bytes(), PDF) if file else not_found()


def _api(routes: tuple[Route, ...], paths: Paths, path: str, body: Body) -> Response:
    with closing(connect(paths.database)) as db:
        return dispatch(routes, Incoming(db, paths, path, body)) or not_found()


def respond_get(paths: Paths, path: str, query: Body) -> Response:
    if path.startswith(API):
        return _api(GET_ROUTES, paths, path, query)
    match = JOB_FILE.match(path)
    if match:
        return _resume(paths, int(match.group(1)))
    return static.static_file(path) or static.app_page()


def respond_post(paths: Paths, path: str, body: Body) -> Response:
    return _api(POST_ROUTES, paths, path, body) if path.startswith(API) else not_found()
