import sqlite3

from satyaapply.core.models import Status
from satyaapply.run.context import RunContext
from satyaapply.store import jobs
from satyaapply.store.jobs import StatusChange

STOPPED_NOTE = (
    "the last run stopped while sending this application; check the site or your email "
    "before applying again"
)


def recover(db: sqlite3.Connection, run: RunContext) -> None:
    change = StatusChange(Status.UNCONFIRMED, run.clock(), STOPPED_NOTE)
    stopped = jobs.change_all(db, Status.SUBMITTING, change)
    if stopped:
        run.progress(f"  {stopped} unfinished send(s) from last time marked unconfirmed")
