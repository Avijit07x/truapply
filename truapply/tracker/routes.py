import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

from truapply.core.paths import Paths
from truapply.tracker.body import Body
from truapply.tracker.responses import Response

Handler = Callable[[sqlite3.Connection, Paths, re.Match[str], Body], Response]


@dataclass(frozen=True)
class Route:
    pattern: re.Pattern[str]
    handler: Handler


def route(pattern: str, handler: Handler) -> Route:
    return Route(re.compile(f"^/api{pattern}$"), handler)


@dataclass(frozen=True)
class Incoming:
    db: sqlite3.Connection
    paths: Paths
    path: str
    body: Body


def dispatch(routes: tuple[Route, ...], incoming: Incoming) -> Response | None:
    for item in routes:
        match = item.pattern.match(incoming.path)
        if match:
            return item.handler(incoming.db, incoming.paths, match, incoming.body)
    return None
