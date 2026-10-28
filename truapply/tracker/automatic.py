import re
import sqlite3
import sys
from collections.abc import Callable
from pathlib import Path

from truapply.core import schedule
from truapply.core.errors import TruApplyError
from truapply.core.paths import Paths
from truapply.core.profile import load
from truapply.tracker.body import Body, flag
from truapply.tracker.responses import Response, bad_request, ok
from truapply.tracker.routes import Route, route

agents: Callable[[], Path] = schedule.agents_dir
runner: schedule.Runner = schedule.launchctl


def supported() -> bool:
    return sys.platform == "darwin"


def current() -> dict[str, object]:
    if not supported():
        return {"supported": False, "on": False, "everyMinutes": None}
    try:
        found = schedule.installed(agents())
    except TruApplyError:
        found = None
    return {
        "supported": True,
        "on": found is not None,
        "everyMinutes": found.every_minutes if found else None,
    }


def turn_on(paths: Paths, every_minutes: int) -> None:
    schedule.install(paths, schedule.Plan(every_minutes), agents(), runner)


def follow(paths: Paths, every_minutes: int) -> None:
    now = current()
    if now["on"] and now["everyMinutes"] != every_minutes:
        turn_on(paths, every_minutes)


def _set(_db: sqlite3.Connection, paths: Paths, _match: re.Match[str], body: Body) -> Response:
    wanted = flag(body, "on")
    if wanted is None:
        return bad_request("Say whether automatic runs should be on or off.")
    if not supported():
        return bad_request("Automatic runs from this page work on macOS only for now.")
    try:
        if wanted:
            turn_on(paths, load(paths).settings.run_every_minutes)
        else:
            schedule.remove(agents(), runner)
    except TruApplyError as error:
        return bad_request(str(error))
    return ok(current())


GET: tuple[Route, ...] = ()
POST: tuple[Route, ...] = (route("/settings/automatic", _set),)
