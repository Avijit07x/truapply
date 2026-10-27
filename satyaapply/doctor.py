import os
import sqlite3
import sys
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from functools import partial
from importlib import resources
from pathlib import Path

from satyaapply.ai.tasks import ping
from satyaapply.browser.chrome import browser_name
from satyaapply.core.clock import utc_now
from satyaapply.core.errors import (
    AppNotBuiltError,
    DatabaseBrokenError,
    DataFolderError,
    SatyaApplyError,
    ScheduleError,
)
from satyaapply.core.paths import Paths
from satyaapply.core.profile import Profile, load
from satyaapply.core.schedule import agents_dir, every, installed
from satyaapply.resume.master import load_resume, master_pdf
from satyaapply.store import usage
from satyaapply.store.db import connect

APP_PAGE = ("static", "index.html")
COUNT_JOBS = "select count(*) from jobs"


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""


def attempt(name: str, probe: Callable[[], str]) -> Check:
    try:
        return Check(name, True, probe())
    except SatyaApplyError as error:
        return Check(name, False, str(error), error.hint)


def folder(paths: Paths) -> str:
    if not paths.root.is_dir():
        raise DataFolderError(f"{paths.root} doesn't exist yet.")
    if not os.access(paths.root, os.W_OK | os.X_OK):
        raise DataFolderError(f"{paths.root} can't be written to.")
    return str(paths.root)


def database(paths: Paths) -> str:
    try:
        with closing(connect(paths.database)) as db:
            count: int = db.execute(COUNT_JOBS).fetchone()[0]
    except sqlite3.DatabaseError as error:
        raise DatabaseBrokenError(f"satyaapply.db can't be read: {error}") from error
    return f"{count:,} jobs saved"


def budget(paths: Paths, profile: Profile) -> str:
    with closing(connect(paths.database)) as db:
        used = usage.ai_calls_on(db, utc_now().astimezone().date())
    return f"{used} of {profile.settings.ai_calls_per_day} calls used today"


def claude() -> str:
    ping()
    return "installed and logged in"


def resume(paths: Paths, profile: Profile) -> str:
    rendered = master_pdf(paths, load_resume(profile))
    plural = "" if rendered.pages == 1 else "s"
    return f"{profile.resume.format} resume builds ({rendered.pages} page{plural})"


def app(page: Path | None = None) -> str:
    built = page or Path(str(resources.files("satyaapply.tracker").joinpath(*APP_PAGE)))
    if not built.is_file():
        raise AppNotBuiltError("The tracker page isn't built.")
    return "built"


def schedule(agents: Path) -> str:
    if sys.platform != "darwin":
        return "not checked here; see `crontab -l`"
    found = installed(agents)
    if found is None:
        return "not scheduled; run `satyaapply schedule` for automatic runs"
    if not found.program.exists():
        raise ScheduleError(f"The schedule runs {found.program}, which no longer exists.")
    return f"every {every(found.every_minutes)}"


def profile_checks(paths: Paths) -> list[Check]:
    try:
        profile = load(paths)
    except SatyaApplyError as error:
        return [Check("Profile", False, str(error), error.hint)]
    return [
        Check("Profile", True, str(paths.profile)),
        attempt("Resume", partial(resume, paths, profile)),
        attempt("Claude budget", partial(budget, paths, profile)),
    ]


def run_checks(paths: Paths) -> list[Check]:
    checks = [attempt("Data folder", partial(folder, paths))]
    if checks[0].ok:
        checks.append(attempt("Database", partial(database, paths)))
        if checks[-1].ok:
            checks.extend(profile_checks(paths))
    checks.append(attempt("Claude Code", claude))
    checks.append(attempt("Browser", browser_name))
    checks.append(attempt("Tracker page", app))
    checks.append(attempt("Schedule", partial(schedule, agents_dir())))
    return checks


def report(checks: list[Check]) -> int:
    for check in checks:
        print(f"{'✔' if check.ok else '✘'} {check.name}: {check.detail}")
        if check.fix:
            print(f"   → {check.fix}")
    return 0 if all(check.ok for check in checks) else 1
