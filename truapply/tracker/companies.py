import re
import sqlite3

from truapply.core import archive_task
from truapply.core.models import Ats
from truapply.core.paths import Paths
from truapply.core.profile import Profile, load
from truapply.store import archive as archived
from truapply.store import boards
from truapply.store.boards import Listed
from truapply.tracker import runs
from truapply.tracker.body import Body
from truapply.tracker.detail import iso
from truapply.tracker.responses import Response, bad_request, ok
from truapply.tracker.routes import Route, route

BOARD_PAGES = {
    Ats.GREENHOUSE: "https://job-boards.greenhouse.io/{}",
    Ats.LEVER: "https://jobs.lever.co/{}",
    Ats.ASHBY: "https://jobs.ashbyhq.com/{}",
}


def _row(item: Listed) -> dict[str, object]:
    board = item.board
    return {
        "key": board.key,
        "company": board.company or board.slug,
        "site": board.ats.value,
        "url": BOARD_PAGES[board.ats].format(board.slug),
        "origin": item.origin.value,
        "addedAt": item.added_at,
        "checkedAt": item.checked_at,
        "closed": item.dead,
        "jobs": item.jobs,
    }


def _search(db: sqlite3.Connection, profile: Profile) -> dict[str, object]:
    every = profile.settings.company_search
    last, upcoming = boards.last_search(db), boards.next_search(db, every)
    return {
        "every": every.value,
        "last": iso(last) if last else None,
        "next": iso(upcoming) if upcoming else None,
    }


def _archive_state(db: sqlite3.Connection, paths: Paths) -> dict[str, object]:
    last = archived.last_check(db)
    return {"going": archive_task.is_going(paths), "last": iso(last) if last else None}


def _show(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    return ok(
        {
            "companies": [_row(item) for item in boards.listed(db)],
            "search": _search(db, load(paths)),
            "archive": _archive_state(db, paths),
        }
    )


def _find(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    choice = runs.Choice(load(paths).settings.jobs_per_run, search=True, companies=True)
    if runs.start(paths, choice) is None:
        return bad_request(runs.ALREADY_RUNNING)
    return ok(runs.state(paths))


def _archive(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    if not archive_task.start_in_background(paths):
        return bad_request(archive_task.ALREADY_CHECKING)
    return ok({"going": True})


GET: tuple[Route, ...] = (route("/companies", _show),)
POST: tuple[Route, ...] = (route("/companies/find", _find), route("/companies/archive", _archive))
