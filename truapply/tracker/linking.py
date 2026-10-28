import re
import sqlite3

from truapply.core.clock import utc_now
from truapply.core.paths import Paths
from truapply.core.profile import load
from truapply.sources.intake import NOT_A_BOARD, take_in_link
from truapply.tracker.body import Body, text
from truapply.tracker.responses import Response, bad_request, ok
from truapply.tracker.routes import Route, route

LINK_LIMIT = 2000


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


GET: tuple[Route, ...] = ()
POST: tuple[Route, ...] = (route("/boards/link", _add),)
