import re
from http import HTTPStatus
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import PurePosixPath

from satyaapply.tracker.responses import TEXT, Response, not_found

ASSET = re.compile(r"^/assets/([A-Za-z0-9_-][A-Za-z0-9._-]*)$")
ROOT_FILES = frozenset({"/favicon.svg"})
TYPES = {
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".png": "image/png",
}
HTML = "text/html; charset=utf-8"
NOT_BUILT = (
    b"The tracker app isn't built yet. Build it once with:\n  cd web && npm ci && npm run build\n"
)


def _root() -> Traversable:
    return resources.files("satyaapply.tracker").joinpath("static")


def _file(file: Traversable, name: str, cacheable: bool) -> Response:
    kind = TYPES.get(PurePosixPath(name).suffix)
    if kind is None or not file.is_file():
        return not_found()
    return Response(HTTPStatus.OK, file.read_bytes(), kind, cacheable)


def app_page() -> Response:
    index = _root().joinpath("index.html")
    if not index.is_file():
        return Response(HTTPStatus.SERVICE_UNAVAILABLE, NOT_BUILT, TEXT)
    return Response(HTTPStatus.OK, index.read_bytes(), HTML)


def static_file(path: str) -> Response | None:
    if path in ROOT_FILES:
        return _file(_root().joinpath(path[1:]), path, cacheable=False)
    match = ASSET.match(path)
    if match is None:
        return None
    return _file(_root().joinpath("assets", match.group(1)), match.group(1), cacheable=True)
