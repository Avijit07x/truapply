import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from truapply.core.models import Board, Job
from truapply.core.profile import Profile
from truapply.sources.ats import boards_in, poll
from truapply.sources.filters import in_your_field, why_skipped
from truapply.store import boards, jobs
from truapply.store.boards import BoardOrigin

NOT_A_BOARD = "That link isn't a Greenhouse, Lever or Ashby job or board."


Wanted = Callable[[Job], bool]
Skip = Callable[[Job], str | None]


@dataclass(frozen=True)
class Wants:
    skip: Skip
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
    outside: list[tuple[Job, str]] = []
    for job in result.jobs:
        why = wants.skip(job)
        if why is None:
            kept.append(job)
        elif wants.keep(job):
            outside.append((job, why))
    added = jobs.add_many(db, kept, now) + jobs.back_in_search(db, kept, now)
    jobs.add_outside_search(db, outside, now)
    return Intake(len(result.jobs), len(kept), added, len(result.dead), len(result.unreachable))


def fits(profile: Profile, now: datetime) -> Wants:
    return Wants(
        skip=lambda job: why_skipped(job, profile, now),
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
    wants = Wants(lambda job: None if _linked(job, link) else usual.skip(job), usual.keep)
    return found[0], take_in(db, found[:1], wants, now)
