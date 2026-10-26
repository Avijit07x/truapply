import sqlite3
from datetime import datetime

from satyaapply.core import notify
from satyaapply.store import meta

OFFER_AT = 20
AUTO_SUBMIT_SCORE = 80
LOSS_WINDOW = 10
LOSS_LIMIT = 2
AUTO_SUBMIT = "auto_submit"
AUTO_SUBMIT_SINCE = "auto_submit_since"
ON, OFF = "on", "off"
CLEAN = ("approve", "clean")
RESETS = frozenset({("approve", "edited"), ("thumbs", "-1")})
EDIT = "edit"
SELECT_FEEDBACK = "select kind, value from feedback order by at desc, id desc"
SELECT_RECENT_AUTO = """
select feedback from jobs where auto_submitted = 1 and status_at >= ?
order by status_at desc, id desc limit ?
"""
LOST_TITLE = "SatyaApply: auto-submit is off"
LOST_MESSAGE = (
    "2 of your last 10 auto-submitted applications got a 👎. "
    "Every application waits for your OK again."
)


def trust_count(db: sqlite3.Connection) -> int:
    count = 0
    for row in db.execute(SELECT_FEEDBACK):
        pair = (row["kind"], row["value"])
        if row["kind"] == EDIT or pair in RESETS:
            break
        count += pair == CLEAN
    return count


def auto_submit_on(db: sqlite3.Connection) -> bool:
    return meta.get(db, AUTO_SUBMIT) == ON


def set_auto_submit(db: sqlite3.Connection, on: bool, now: datetime) -> None:
    if on == auto_submit_on(db):
        return
    meta.put(db, AUTO_SUBMIT_SINCE, now.isoformat())
    meta.put(db, AUTO_SUBMIT, ON if on else OFF)


def review(db: sqlite3.Connection, now: datetime) -> bool:
    if not auto_submit_on(db):
        return False
    since = meta.get(db, AUTO_SUBMIT_SINCE) or ""
    rows = db.execute(SELECT_RECENT_AUTO, (since, LOSS_WINDOW)).fetchall()
    if sum(row["feedback"] == -1 for row in rows) < LOSS_LIMIT:
        return False
    set_auto_submit(db, False, now)
    notify.send(LOST_TITLE, LOST_MESSAGE)
    return True
