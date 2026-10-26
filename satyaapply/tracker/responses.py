import json
from collections.abc import Sequence
from dataclasses import dataclass
from http import HTTPStatus

JSON = "application/json; charset=utf-8"
TEXT = "text/plain; charset=utf-8"


@dataclass(frozen=True)
class Response:
    status: HTTPStatus
    body: bytes
    content_type: str
    cacheable: bool = False


def ok(data: object) -> Response:
    return Response(HTTPStatus.OK, json.dumps(data, ensure_ascii=False).encode(), JSON)


def problem(status: HTTPStatus, text: str, problems: Sequence[str] = ()) -> Response:
    body: dict[str, object] = {"error": text}
    if problems:
        body["problems"] = list(problems)
    return Response(status, json.dumps(body, ensure_ascii=False).encode(), JSON)


def bad_request(text: str, problems: Sequence[str] = ()) -> Response:
    return problem(HTTPStatus.BAD_REQUEST, text, problems)


def not_found(text: str = "Not found.") -> Response:
    return problem(HTTPStatus.NOT_FOUND, text)


def forbidden() -> Response:
    return problem(HTTPStatus.FORBIDDEN, "Refused.")
