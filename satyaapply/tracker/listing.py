import re
import sqlite3

from satyaapply.core.models import Status
from satyaapply.core.paths import Paths
from satyaapply.store import groups, records
from satyaapply.store.groups import Group
from satyaapply.tracker import learning, runs, trust
from satyaapply.tracker.body import Body, text
from satyaapply.tracker.detail import DISMISS_REASONS, job_detail, job_row
from satyaapply.tracker.responses import Response, bad_request, not_found, ok
from satyaapply.tracker.routes import Route, route

LIST_LIMIT = 500
CARDS_PER_COLUMN = 8
COLUMNS = (
    Status.NEEDS_INPUT,
    Status.FINISH,
    Status.READY,
    Status.APPROVED,
    Status.APPLIED,
    Status.SCORED,
)
STATUSES = frozenset(Status)
GROUPS = frozenset(Group)


def _summary(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    counts = records.counts(db)
    learning.refresh_suggestions(db, paths)
    return ok(
        {
            "total": sum(counts.values()),
            "counts": {status.value: total for status, total in counts.items()},
            "trust": trust.state(db),
            "run": runs.state(paths),
            "suggestions": len(learning.pending(db)),
        }
    )


def _listed(db: sqlite3.Connection, status: str, group: str) -> tuple[list[records.JobRecord], int]:
    if group:
        chosen = Group(group)
        return groups.jobs_in(db, chosen, LIST_LIMIT), groups.counts(db)[chosen]
    counts = records.counts(db)
    if status:
        return records.latest(db, Status(status), LIST_LIMIT), counts.get(Status(status), 0)
    return records.latest(db, None, LIST_LIMIT), sum(counts.values())


def _jobs(db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], body: Body) -> Response:
    status, group = text(body, "status", 40), text(body, "group", 40)
    if (status and status not in STATUSES) or (group and group not in GROUPS):
        return bad_request("Unknown filter.")
    items, total = _listed(db, status, group)
    return ok({"jobs": [job_row(item) for item in items], "total": total})


def _board(db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    counts = records.counts(db)
    latest = records.latest_each(db, CARDS_PER_COLUMN)
    columns = [
        {
            "status": status.value,
            "total": counts.get(status, 0),
            "jobs": [job_row(item) for item in latest.get(status, [])],
        }
        for status in COLUMNS
    ]
    return ok({"columns": columns, "dismissReasons": list(DISMISS_REASONS)})


def _job(db: sqlite3.Connection, paths: Paths, match: re.Match[str], _body: Body) -> Response:
    record = records.find(db, int(match.group(1)))
    return ok(job_detail(db, paths, record)) if record else not_found("No such job.")


def _workflow(
    db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], _body: Body
) -> Response:
    return ok({"groups": {group.value: total for group, total in groups.counts(db).items()}})


GET: tuple[Route, ...] = (
    route("/summary", _summary),
    route("/jobs", _jobs),
    route("/board", _board),
    route(r"/jobs/(\d+)", _job),
    route("/workflow", _workflow),
)
POST: tuple[Route, ...] = ()
