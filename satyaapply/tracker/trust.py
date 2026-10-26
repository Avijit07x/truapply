import re
import sqlite3

from satyaapply.core.clock import utc_now
from satyaapply.core.paths import Paths
from satyaapply.store import trust
from satyaapply.store.records import JobRecord
from satyaapply.store.trust import AUTO_SUBMIT_SCORE, OFFER_AT
from satyaapply.tracker.html import e, section
from satyaapply.tracker.responses import Response, back_to, bad_request
from satyaapply.tracker.routes import Form, Route, route

RULE = (
    f"Auto-submit only sends strong matches (score {AUTO_SUBMIT_SCORE} or more) "
    "and turns itself off after 2 👎 in the last 10 it sent."
)
NOT_YET = f"Auto-submit is offered after {OFFER_AT} clean approvals in a row."
CHOICES = {"1": True, "0": False}


def _button(on: bool, label: str) -> str:
    kind = "" if on else ' class="secondary"'
    return (
        '<form method="post" action="/auto-submit" class="button-row">'
        f'<input type="hidden" name="on" value="{int(on)}">'
        f"<button{kind}>{e(label)}</button></form>"
    )


def _controls(on: bool, count: int) -> str:
    if on:
        status = "<p><strong>Auto-submit is on.</strong> Strong matches are sent for you.</p>"
        return status + _button(False, "Turn off")
    return _button(True, "Turn on auto-submit") if count >= OFFER_AT else ""


def home_panel(db: sqlite3.Connection, _paths: Paths) -> str:
    trust.review(db, utc_now())
    count = trust.trust_count(db)
    approvals = "approval" if count == 1 else "approvals"
    body = (
        f"<p>{e(count)} clean {approvals} in a row. Auto-submit is offered at {OFFER_AT}.</p>"
        f'<p class="muted">{e(RULE)}</p>'
        f"{_controls(trust.auto_submit_on(db), count)}"
    )
    return section("Auto-submit", body)


def job_controls(_db: sqlite3.Connection, _record: JobRecord) -> str:
    return ""


def _switch(db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], form: Form) -> Response:
    on = CHOICES.get(form.get("on", ""))
    if on is None:
        return bad_request("Choose on or off.")
    if on and trust.trust_count(db) < OFFER_AT:
        return bad_request(e(NOT_YET))
    trust.set_auto_submit(db, on, utc_now())
    return back_to("/")


GET: tuple[Route, ...] = ()
POST: tuple[Route, ...] = (route("/auto-submit", _switch),)
