import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from satyaapply.core.models import Board, Job
from satyaapply.core.profile import Profile
from satyaapply.sources.ats import boards_in, poll
from satyaapply.sources.filters import in_your_field, worth_scoring
from satyaapply.store import boards, jobs
from satyaapply.store.boards import BoardOrigin

NOT_A_BOARD = "That link isn't a Greenhouse, Lever or Ashby job or board."


Wanted = Callable[[Job], bool]


@dataclass(frozen=True)
class Wants:
    queue: Wanted
    keep: Wanted


@dataclass(frozen=True)
class Intake:
    found: int
    kept: int
    added: int
    dead: int
    unreachable: int


def _linked(job: Job, link: str) -> bool:
    return bool(link) and job.external_id.rsplit("/", 1)[-1] in urlsplit(link).path.split("/")


def take_in(
    db: sqlite3.Connection, checked: Sequence[Board], wants: Wants, now: datetime
) -> Intake:
    result = poll(checked)
    boards.mark_checked(db, result.alive, result.dead, now)
    kept: list[Job] = []
    outside: list[Job] = []
    for job in result.jobs:
        if wants.queue(job):
            kept.append(job)
        elif wants.keep(job):
            outside.append(job)
    added = jobs.add_many(db, kept, now) + jobs.back_in_search(db, kept, now)
    jobs.add_outside_search(db, outside, now)
    return Intake(len(result.jobs), len(kept), added, len(result.dead), len(result.unreachable))


def fits(profile: Profile, now: datetime) -> Wants:
    return Wants(
        queue=lambda job: worth_scoring(job, profile, now),
        keep=lambda job: in_your_field(job, profile),
    )


def take_in_link(
    db: sqlite3.Connection, link: str, profile: Profile, now: datetime
) -> tuple[Board, Intake] | None:
    found = boards_in([link])
    if not found:
        return None
    boards.add_many(db, found, BoardOrigin.LINK, now)
    usual = fits(profile, now)
    wants = Wants(lambda job: usual.queue(job) or _linked(job, link), usual.keep)
    return found[0], take_in(db, found[:1], wants, now)
