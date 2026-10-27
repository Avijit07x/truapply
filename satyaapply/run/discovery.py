import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta

from satyaapply.ai.tasks import find_posting_urls
from satyaapply.core.errors import AIError, UsageLimitError
from satyaapply.core.profile import Profile
from satyaapply.sources.ats import boards_in
from satyaapply.sources.discover import shared_boards
from satyaapply.sources.intake import fits, take_in
from satyaapply.store import boards, meta
from satyaapply.store.boards import BoardOrigin

LAST_SEARCH_KEY = "last_board_search"
SEARCH_EVERY = timedelta(hours=24)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Discovery:
    boards: int
    new_boards: int
    found: int
    kept: int
    added: int
    dead: int
    unreachable: int


def _search_due(db: sqlite3.Connection, now: datetime) -> bool:
    last = meta.get(db, LAST_SEARCH_KEY)
    return last is None or now - datetime.fromisoformat(last) >= SEARCH_EVERY


def _search_boards(db: sqlite3.Connection, profile: Profile, now: datetime) -> int:
    try:
        urls = find_posting_urls(profile)
    except UsageLimitError:
        raise
    except AIError as error:
        log.warning("board search failed, trying again next run: %s", error)
        return 0
    meta.put(db, LAST_SEARCH_KEY, now.isoformat())
    return boards.add_many(db, boards_in(urls), BoardOrigin.SEARCH, now)


def discover(db: sqlite3.Connection, profile: Profile, now: datetime, search: bool) -> Discovery:
    new_boards = boards.add_many(db, shared_boards(), BoardOrigin.SHARED, now)
    if search and _search_due(db, now):
        new_boards += _search_boards(db, profile, now)
    active = boards.active(db)
    intake = take_in(db, active, fits(profile, now), now)
    return Discovery(
        boards=len(active),
        new_boards=new_boards,
        found=intake.found,
        kept=intake.kept,
        added=intake.added,
        dead=intake.dead,
        unreachable=intake.unreachable,
    )
