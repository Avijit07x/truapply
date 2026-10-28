import sqlite3
from contextlib import closing
from datetime import datetime, timedelta

from truapply.core.archive_task import ALREADY_CHECKING
from truapply.core.clock import Clock, utc_now
from truapply.core.errors import ArchiveCheckGoingError
from truapply.core.locks import held
from truapply.core.paths import Paths
from truapply.core.profile import Profile, load
from truapply.sources import archive
from truapply.store import archive as archived
from truapply.store import boards
from truapply.store.boards import BoardOrigin
from truapply.store.db import connect

RECHECK_AFTER = timedelta(days=180)


def _new_boards(db: sqlite3.Connection, profile: Profile, now: datetime) -> int:
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


def check_now(paths: Paths, clock: Clock = utc_now) -> int:
    with (
        held(paths.archive_lock, ArchiveCheckGoingError(ALREADY_CHECKING)),
        closing(connect(paths.database)) as db,
    ):
        return _new_boards(db, load(paths), clock())


def due(db: sqlite3.Connection, profile: Profile, now: datetime) -> bool:
    return archived.check_due(db, profile.settings.company_search, now)
