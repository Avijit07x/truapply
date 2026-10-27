import re
import sqlite3
from datetime import datetime

from satyaapply.core.errors import SatyaApplyError
from satyaapply.core.models import LISTED_SOURCES, Source, Status
from satyaapply.core.paths import Paths
from satyaapply.core.profile import load
from satyaapply.store import browse, groups, records
from satyaapply.store.browse import NEWEST_FIRST, PAGE_SIZE, Browse, Sort
from satyaapply.store.groups import Group
from satyaapply.tracker import learning, runs
from satyaapply.tracker.body import Body, text
from satyaapply.tracker.detail import DISMISS_REASONS, DISMISSABLE, SCORABLE, job_detail, job_row
from satyaapply.tracker.responses import Response, bad_request, not_found, ok
from satyaapply.tracker.routes import Route, route

CARDS_PER_COLUMN = 8
SEARCH_LIMIT = 100
EVERYTHING = "all"
PAGE_NUMBER = re.compile(r"[1-9][0-9]{0,5}")
SCORE = re.compile(r"[0-9]{1,3}")
HIGHEST_SCORE = 100
ORDERS = {"asc": False, "desc": True}
COLUMNS = (Status.SCORED, Status.READY, Status.APPLIED)
STATUSES = frozenset(Status)
GROUPS = frozenset(Group)
SORTS = frozenset(Sort)
SOURCES = frozenset(Source)


def _sites_on(paths: Paths) -> list[Source]:
    try:
        wanted = load(paths).settings.wellfound
    except SatyaApplyError:
        return []
    return [Source.WELLFOUND] if wanted else []


def _site(db: sqlite3.Connection, source: Source) -> dict[str, object]:
    counts = records.counts(db, source)
    return {
        "source": source.value,
        "total": sum(counts.values()),
        "counts": {status.value: total for status, total in counts.items()},
    }


def _summary(db: sqlite3.Connection, paths: Paths, _match: re.Match[str], _body: Body) -> Response:
    counts = records.counts(db)
    learning.refresh_suggestions(db, paths)
    return ok(
        {
            "total": sum(counts.values()),
            "counts": {status.value: total for status, total in counts.items()},
            "sites": [_site(db, source) for source in _sites_on(paths)],
            "run": runs.state(paths),
            "suggestions": len(learning.pending(db)),
        }
    )


def _refused(body: Body) -> bool:
    status, group = text(body, "status", 40), text(body, "group", 40)
    order, score = text(body, "order", 20), text(body, "minScore", 20)
    source = text(body, "source", 40)
    return bool(
        (status and status not in STATUSES)
        or (group and group not in GROUPS)
        or (text(body, "sort", 20) or Sort.UPDATED) not in SORTS
        or (order and order not in ORDERS)
        or not PAGE_NUMBER.fullmatch(text(body, "page", 20) or "1")
        or (score and not (SCORE.fullmatch(score) and int(score) <= HIGHEST_SCORE))
        or text(body, "show", 20) not in ("", EVERYTHING)
        or (source and source not in SOURCES)
    )


def _browse(body: Body) -> Browse:
    status, group = text(body, "status", 40), text(body, "group", 40)
    sort, order = Sort(text(body, "sort", 20) or Sort.UPDATED), text(body, "order", 20)
    score, source = text(body, "minScore", 20), text(body, "source", 40)
    return Browse(
        status=Status(status) if status else None,
        group=Group(group) if group else None,
        search=text(body, "q", SEARCH_LIMIT),
        sort=sort,
        descending=ORDERS[order] if order else sort in NEWEST_FIRST,
        page=int(text(body, "page", 20) or "1"),
        company=text(body, "company", SEARCH_LIMIT),
        location=text(body, "location", SEARCH_LIMIT),
        min_score=int(score) if score else None,
        everything=text(body, "show", 20) == EVERYTHING,
        source=Source(source) if source else None,
    )


def _jobs(db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], body: Body) -> Response:
    if _refused(body):
        return bad_request("Unknown filter, sort or page.")
    found = browse.page(db, _browse(body))
    return ok(
        {
            "jobs": [job_row(item) for item in found.jobs],
            "total": found.total,
            "page": found.page,
            "pageSize": PAGE_SIZE,
            "dismissable": sorted(status.value for status in DISMISSABLE),
            "scorable": sorted(status.value for status in SCORABLE),
            "scoring": runs.scoring_now(),
            "dismissReasons": list(DISMISS_REASONS),
        }
    )


CAREER_TAB = "jobs"
TABS: dict[str, Source | None] = {CAREER_TAB: None} | {site.value: site for site in LISTED_SOURCES}
NOT_A_TIME = "Send each tab's last visit as an ISO time with its time zone."


def _since(value: str) -> datetime | None:
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo else None


def _new_jobs(db: sqlite3.Connection, _paths: Paths, _match: re.Match[str], body: Body) -> Response:
    asked = {tab: text(body, tab, 40) for tab in TABS if text(body, tab, 40)}
    since = {tab: moment for tab, value in asked.items() if (moment := _since(value))}
    if len(since) < len(asked):
        return bad_request(NOT_A_TIME)
    return ok({tab: records.found_after(db, moment, TABS[tab]) for tab, moment in since.items()})


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
    route("/new-jobs", _new_jobs),
)
POST: tuple[Route, ...] = ()
