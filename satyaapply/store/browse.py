import math
import sqlite3
from dataclasses import dataclass
from enum import StrEnum

from satyaapply.core.models import Status
from satyaapply.store.groups import CONDITIONS, PARAMS, Group
from satyaapply.store.records import JobRecord, to_record

PAGE_SIZE = 50
ACTIVE = "status != :skipped"
EVERY_JOB = "1 = 1"
MATCHES = "title like :search escape '\\' or company like :search escape '\\'"
COMPANY = "company like :company escape '\\'"
LOCATION = "location like :location escape '\\'"
SCORED_AT_LEAST = "score >= :min_score"


class Sort(StrEnum):
    UPDATED = "updated"
    SCORE = "score"
    TITLE = "title"
    COMPANY = "company"
    LOCATION = "location"


COLUMN: dict[Sort, str] = {
    Sort.UPDATED: "status_at",
    Sort.SCORE: "score",
    Sort.TITLE: "title collate nocase",
    Sort.COMPANY: "company collate nocase",
    Sort.LOCATION: "location collate nocase",
}
NEWEST_FIRST = frozenset({Sort.UPDATED, Sort.SCORE})


@dataclass(frozen=True)
class Browse:
    status: Status | None = None
    group: Group | None = None
    search: str = ""
    sort: Sort = Sort.UPDATED
    descending: bool = True
    page: int = 1
    company: str = ""
    location: str = ""
    min_score: int | None = None
    everything: bool = False


@dataclass(frozen=True)
class Page:
    jobs: list[JobRecord]
    total: int
    page: int


def _like(search: str) -> str:
    escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _chosen(browse: Browse) -> str:
    if browse.group:
        return CONDITIONS[browse.group]
    if browse.status:
        return f"status = :{browse.status.value}"
    return EVERY_JOB if browse.everything else ACTIVE


def _where(browse: Browse) -> str:
    narrowing = (
        (browse.search, MATCHES),
        (browse.company, COMPANY),
        (browse.location, LOCATION),
        (browse.min_score is not None, SCORED_AT_LEAST),
    )
    parts = [_chosen(browse), *(part for wanted, part in narrowing if wanted)]
    return " and ".join(f"({part})" for part in parts)


def _order(browse: Browse) -> str:
    column = COLUMN[browse.sort]
    direction = "desc" if browse.descending else "asc"
    return f"{column} is null, {column} {direction}, status_at desc, id desc"


def page(db: sqlite3.Connection, browse: Browse) -> Page:
    where = _where(browse)
    params: dict[str, object] = {
        **PARAMS,
        "search": _like(browse.search),
        "company": _like(browse.company),
        "location": _like(browse.location),
        "min_score": browse.min_score,
    }
    total = int(db.execute(f"select count(*) from jobs where {where}", params).fetchone()[0])  # noqa: S608
    shown = min(browse.page, max(1, math.ceil(total / PAGE_SIZE)))
    window = {"limit": PAGE_SIZE, "offset": (shown - 1) * PAGE_SIZE}
    order = _order(browse)
    query = f"select * from jobs where {where} order by {order} limit :limit offset :offset"  # noqa: S608
    rows = db.execute(query, params | window)
    return Page([to_record(row) for row in rows], total, shown)
