import re
import sqlite3
from dataclasses import replace

from truapply.core.clock import utc_now
from truapply.core.errors import TruApplyError
from truapply.core.locks import is_held
from truapply.core.paths import Paths
from truapply.core.profile import load, save
from truapply.store import autosend, feedback
from truapply.store.feedback import Feedback, FeedbackKind
from truapply.tracker import runs
from truapply.tracker.body import Body, text
from truapply.tracker.responses import Response, bad_request, ok
from truapply.tracker.routes import Route, route

WHY_LIMIT = 300
TURN_ON = "Turn on auto-submit first: Settings, Applying tab, Auto-submit."
UNSAID = "something on the form needs you"


def _run_going(paths: Paths) -> bool:
    return runs.REGISTRY.active() is not None or is_held(paths.lock)


def _next(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    settings = load(paths).settings
    if not settings.auto_submit:
        return ok({"job": None})
    score, during_run = settings.auto_submit_score, _run_going(paths)
    found = autosend.claim_next(db, score, utc_now(), queued_only=during_run)
    return ok({"job": {"id": found.id, "url": found.url} if found else None})


def _submitting(
    db: sqlite3.Connection, paths: Paths, match: re.Match[str], _body: Body
) -> Response:
    allowed = load(paths).settings.auto_submit
    go = allowed and autosend.submitting(db, int(match.group(1)), utc_now())
    if not allowed:
        autosend.hold(db, int(match.group(1)), "auto-submit was turned off")
    return ok({"go": go})


def _queue(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    settings = load(paths).settings
    if not settings.auto_submit:
        return bad_request(TURN_ON)
    found = autosend.queue_ready(db, settings.auto_submit_score)
    return ok({"queued": found.queued, "below": found.below, "score": settings.auto_submit_score})


def _held(db: sqlite3.Connection, _paths: Paths, match: re.Match[str], body: Body) -> Response:
    job_id, why = int(match.group(1)), text(body, "why", WHY_LIMIT) or UNSAID
    autosend.hold(db, job_id, why)
    feedback.add(db, job_id, [Feedback(FeedbackKind.AUTO_HELD, why, utc_now())])
    return ok({"held": True})


def keep_trust(db: sqlite3.Connection, paths: Paths) -> bool:
    try:
        profile = load(paths)
    except TruApplyError:
        return False
    if not profile.settings.auto_submit or not autosend.lost_trust(db):
        return False
    save(paths, replace(profile, settings=replace(profile.settings, auto_submit=False)))
    return True


GET: tuple[Route, ...] = ()
POST: tuple[Route, ...] = (
    route(r"/extension/send/next", _next),
    route(r"/extension/jobs/(\d+)/submitting", _submitting),
    route(r"/extension/jobs/(\d+)/held", _held),
    route(r"/autosend/queue", _queue),
)
