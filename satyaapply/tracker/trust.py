import re
import sqlite3

from satyaapply.core.clock import utc_now
from satyaapply.core.paths import Paths
from satyaapply.store import trust
from satyaapply.store.trust import AUTO_SUBMIT_SCORE, OFFER_AT
from satyaapply.tracker.body import Body, flag
from satyaapply.tracker.responses import Response, bad_request, ok
from satyaapply.tracker.routes import Route, route

NOT_YET = f"Auto-submit is offered after {OFFER_AT} clean approvals in a row."


def state(db: sqlite3.Connection) -> dict[str, object]:
    trust.review(db, utc_now())
    return {
        "count": trust.trust_count(db),
        "offerAt": OFFER_AT,
        "autoSubmit": trust.auto_submit_on(db),
        "autoSubmitScore": AUTO_SUBMIT_SCORE,
    }


def _switch(db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], body: Body) -> Response:
    on = flag(body, "on")
    if on is None:
        return bad_request("Choose on or off.")
    if on and trust.trust_count(db) < OFFER_AT:
        return bad_request(NOT_YET)
    trust.set_auto_submit(db, on, utc_now())
    return ok(state(db))


GET: tuple[Route, ...] = ()
POST: tuple[Route, ...] = (route("/auto-submit", _switch),)
