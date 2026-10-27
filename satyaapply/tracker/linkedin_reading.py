import re
import sqlite3

from satyaapply.core.clock import start_of_local_day, utc_now
from satyaapply.core.errors import SatyaApplyError
from satyaapply.core.models import Source
from satyaapply.core.paths import Paths
from satyaapply.core.profile import load
from satyaapply.sources.linkedin_search import search_urls
from satyaapply.store import jobs
from satyaapply.tracker.body import Body
from satyaapply.tracker.responses import Response, ok
from satyaapply.tracker.routes import Route, route

NOTHING = {"read": False, "searches": [], "left": 0}


def plan(db: sqlite3.Connection, paths: Paths) -> dict[str, object]:
    try:
        profile = load(paths)
    except SatyaApplyError:
        return NOTHING
    chosen = profile.settings
    if not chosen.linkedin_reading:
        return NOTHING
    today = jobs.found_since(db, Source.LINKEDIN, start_of_local_day(utc_now()))
    left = max(0, chosen.linkedin_reads_per_day - today)
    return {"read": left > 0, "searches": search_urls(profile), "left": left}


def _plan(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    return ok(plan(db, paths))


GET: tuple[Route, ...] = ()
POST: tuple[Route, ...] = (route(r"/extension/linkedin-plan", _plan),)
