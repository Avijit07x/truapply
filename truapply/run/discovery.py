import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from truapply.ai.tasks import find_posting_urls
from truapply.core.errors import AIError, UsageLimitError
from truapply.core.profile import Profile
from truapply.sources import archive
from truapply.sources.ats import boards_in
from truapply.sources.discover import shared_boards
from truapply.sources.intake import fits, take_in
from truapply.store import archive as archived
from truapply.store import boards
from truapply.store.boards import BoardOrigin

log = logging.getLogger(__name__)
RECHECK_AFTER = timedelta(days=180)


class CompanySearchNow(StrEnum):
    SKIP = "skip"
    WHEN_DUE = "when_due"
    NOW = "now"


@dataclass(frozen=True)
class Finding:
    search: CompanySearchNow
    archive_now: bool = False


@dataclass(frozen=True)
class Discovery:
    boards: int
    new_boards: int
    archived: int
    found: int
    kept: int
    added: int
    dead: int
    unreachable: int


def _search_boards(db: sqlite3.Connection, profile: Profile, now: datetime) -> int:
    try:
        urls = find_posting_urls(profile)
    except UsageLimitError:
        raise
    except AIError as error:
        log.warning("board search failed, trying again next run: %s", error)
        return 0
    boards.searched(db, now)
    return boards.add_many(db, boards_in(urls), BoardOrigin.SEARCH, now)


def _archive_boards(db: sqlite3.Connection, profile: Profile, now: datetime) -> int:
    archived.checked(db, now)
    crawl = archive.latest_crawl()
    if crawl is None or crawl == archived.last_crawl(db):
        return 0
    read = archive.read(crawl)
    skip = boards.known_keys(db) | archived.checked_since(db, now - RECHECK_AFTER)
    found = archive.check([board for board in read.boards if board.key not in skip], profile)
    archived.mark_checked(db, found.checked, now)
    if read.complete:
        archived.read_crawl(db, crawl)
    return boards.add_many(db, found.local, BoardOrigin.ARCHIVE, now)


def _archive_wanted(
    db: sqlite3.Connection, profile: Profile, now: datetime, finding: Finding
) -> bool:
    every = profile.settings.company_search
    return finding.archive_now or (
        finding.search != CompanySearchNow.SKIP and archived.check_due(db, every, now)
    )


def _wanted(
    db: sqlite3.Connection, profile: Profile, now: datetime, search: CompanySearchNow
) -> bool:
    every = profile.settings.company_search
    return search == CompanySearchNow.NOW or (
        search == CompanySearchNow.WHEN_DUE and boards.search_due(db, every, now)
    )


def discover(
    db: sqlite3.Connection, profile: Profile, now: datetime, finding: Finding
) -> Discovery:
    new_boards = boards.add_many(db, shared_boards(), BoardOrigin.SHARED, now)
    if _wanted(db, profile, now, finding.search):
        new_boards += _search_boards(db, profile, now)
    from_archive = 0
    if _archive_wanted(db, profile, now, finding):
        from_archive = _archive_boards(db, profile, now)
    active = boards.active(db)
    intake = take_in(db, active, fits(profile, now), now)
    return Discovery(
        boards=len(active),
        new_boards=new_boards + from_archive,
        archived=from_archive,
        found=intake.found,
        kept=intake.kept,
        added=intake.added,
        dead=intake.dead,
        unreachable=intake.unreachable,
    )
