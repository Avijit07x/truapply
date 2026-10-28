import re
import sqlite3
from collections.abc import Callable
from pathlib import Path

from truapply.core import autorun, schedule
from truapply.core.errors import TruApplyError
from truapply.core.paths import Paths
from truapply.core.profile import load
from truapply.tracker.body import Body, flag
from truapply.tracker.responses import Response, bad_request, ok
from truapply.tracker.routes import Route, route

agents: Callable[[], Path] = autorun.folder
runner: schedule.Runner = autorun.runner()


def supported() -> bool:
    return autorun.SUPPORTED


def current() -> dict[str, object]:
    if not supported():
        return {"supported": False, "on": False, "everyMinutes": None}
    try:
        found = autorun.installed(agents())
    except TruApplyError:
        found = None
    return {
        "supported": True,
        "on": found is not None,
        "everyMinutes": found.every_minutes if found else None,
    }


def turn_on(paths: Paths, every_minutes: int) -> None:
    autorun.install(paths, schedule.Plan(every_minutes), agents(), runner)


def follow(paths: Paths, every_minutes: int) -> None:
    now = current()
    if now["on"] and now["everyMinutes"] != every_minutes:
        turn_on(paths, every_minutes)


def _set(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], body: Body) -> Response:
    wanted = flag(body, "on")
    if wanted is None:
        return bad_request("Say whether automatic runs should be on or off.")
    if not supported():
        return bad_request("Automatic runs from this page work on macOS and Windows for now.")
    try:
        if wanted:
            turn_on(paths, load(paths).settings.run_every_minutes)
        else:
            autorun.remove(agents(), runner)
    except TruApplyError as error:
        return bad_request(str(error))
    return ok(current())


GET: tuple[Route, ...] = ()
POST: tuple[Route, ...] = (route("/settings/automatic", _set),)
