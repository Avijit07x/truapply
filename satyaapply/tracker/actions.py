import sqlite3

from satyaapply.core.paths import Paths
from satyaapply.store.records import JobRecord
from satyaapply.tracker.routes import Route

GET: tuple[Route, ...] = ()
POST: tuple[Route, ...] = ()


def home_panel(_db: sqlite3.Connection, _paths: Paths) -> str:
    return ""


def job_controls(_db: sqlite3.Connection, _record: JobRecord) -> str:
    return ""
