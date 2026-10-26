from dataclasses import dataclass
from http import HTTPStatus

from satyaapply.tracker.html import page

HTML = "text/html; charset=utf-8"


@dataclass(frozen=True)
class Response:
    status: HTTPStatus
    body: bytes
    content_type: str
    location: str | None = None


def html(text: str, status: HTTPStatus = HTTPStatus.OK) -> Response:
    return Response(status, text.encode("utf-8"), HTML)


def not_found() -> Response:
    return html(page("Not found", "<h1>Not found</h1>"), HTTPStatus.NOT_FOUND)


def bad_request(text: str) -> Response:
    return html(page("Not accepted", f"<h1>Not accepted</h1><p>{text}</p>"), HTTPStatus.BAD_REQUEST)


def back_to(location: str) -> Response:
    return Response(HTTPStatus.SEE_OTHER, b"", "text/plain; charset=utf-8", location)
