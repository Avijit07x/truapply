import re
import sqlite3

from truapply.core.clock import utc_now
from truapply.core.models import Board
from truapply.core.paths import Paths
from truapply.core.profile import load
from truapply.sources.intake import NOT_A_BOARD, take_in_link, take_in_names
from truapply.tracker.body import Body, text
from truapply.tracker.responses import Response, bad_request, ok
from truapply.tracker.routes import Route, route

LINK_LIMIT = 2000
NAMES_LIMIT = 5000


def _add(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], body: Body) -> Response:
    linked = take_in_link(db, text(body, "link", LINK_LIMIT), load(paths), utc_now())
    if linked is None:
        return bad_request(NOT_A_BOARD)
    board, intake = linked
    return ok(
        {
            "company": board.company or board.slug,
            "open": intake.found,
            "kept": intake.kept,
            "added": intake.added,
            "gone": intake.dead > 0,
        }
    )


def _companies(found: list[Board]) -> list[str]:
    return [board.company or board.slug for board in found]


def _add_names(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], body: Body) -> Response:
    named = take_in_names(db, text(body, "names", NAMES_LIMIT), load(paths), utc_now())
    return ok(
        {
            "added": _companies(named.added),
            "known": _companies(named.known),
            "missing": named.missing,
            "jobs": named.jobs,
        }
    )


GET: tuple[Route, ...] = ()
POST: tuple[Route, ...] = (route("/boards/link", _add), route("/boards/names", _add_names))
