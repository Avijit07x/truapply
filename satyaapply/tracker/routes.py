import re
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from satyaapply.core.paths import Paths
from satyaapply.tracker.responses import Response

Form = Mapping[str, str]
Handler = Callable[[sqlite3.Connection, Paths, re.Match[str], Form], Response]


@dataclass(frozen=True)
class Route:
    pattern: re.Pattern[str]
    handler: Handler


def route(pattern: str, handler: Handler) -> Route:
    return Route(re.compile(f"^{pattern}$"), handler)


@dataclass(frozen=True)
class Incoming:
    db: sqlite3.Connection
    paths: Paths
    path: str
    form: Form


def dispatch(routes: tuple[Route, ...], incoming: Incoming) -> Response | None:
    for item in routes:
        match = item.pattern.match(incoming.path)
        if match:
            return item.handler(incoming.db, incoming.paths, match, incoming.form)
    return None
