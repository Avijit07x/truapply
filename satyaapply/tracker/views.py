import re
from contextlib import closing
from http import HTTPStatus

from satyaapply.core.paths import Paths
from satyaapply.store import records
from satyaapply.store.db import connect
from satyaapply.tracker import (
    actions,
    automatic,
    extension,
    learning,
    linking,
    listing,
    resume_upload,
    runs,
    settings,
    static,
)
from satyaapply.tracker.body import Body
from satyaapply.tracker.detail import resume_pdf
from satyaapply.tracker.responses import Response, not_found
from satyaapply.tracker.routes import Incoming, Route, dispatch

API = "/api/"
PDF = "application/pdf"
JOB_FILE = re.compile(r"^/jobs/(\d+)/resume\.pdf$")
FEATURES = (
    listing,
    actions,
    learning,
    linking,
    runs,
    settings,
    automatic,
    resume_upload,
    extension,
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
